"""Shared shell and subprocess helpers."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path

from openharness.config import Settings, load_settings
from openharness.platforms import PlatformName, get_platform
from openharness.sandbox import wrap_command_for_sandbox


def resolve_shell_command(
    command: str,
    *,
    platform_name: PlatformName | None = None,
    prefer_pty: bool = False,
) -> list[str]:
    """Return argv for the best available shell on the current platform."""
    resolved_platform = platform_name or get_platform()
    if resolved_platform == "windows":
        bash = shutil.which("bash")
        if bash:
            return [bash, "-lc", command]
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell:
            return [powershell, "-NoLogo", "-NoProfile", "-Command", command]
        return [shutil.which("cmd.exe") or "cmd.exe", "/d", "/s", "/c", command]

    bash = shutil.which("bash")
    if bash:
        argv = [bash, "-lc", command]
        if prefer_pty:
            wrapped = _wrap_command_with_script(argv)
            if wrapped is not None:
                return wrapped
        return argv
    shell = shutil.which("sh") or os.environ.get("SHELL") or "/bin/sh"
    argv = [shell, "-lc", command]
    if prefer_pty:
        wrapped = _wrap_command_with_script(argv)
        if wrapped is not None:
            return wrapped
    return argv


async def create_shell_subprocess(
    command: str,
    *,
    cwd: str | Path,
    settings: Settings | None = None,
    prefer_pty: bool = False,
    stdin: int | None = None,
    stdout: int | None = None,
    stderr: int | None = None,
    env: Mapping[str, str] | None = None,
) -> asyncio.subprocess.Process:
    """Spawn a shell command with platform-aware shell selection and sandboxing."""
    resolved_settings = settings or load_settings()

    # Docker backend: route through docker exec
    if resolved_settings.sandbox.enabled and resolved_settings.sandbox.backend == "docker":
        from openharness.sandbox.session import get_docker_sandbox

        session = get_docker_sandbox()
        if session is not None and session.is_running:
            argv = resolve_shell_command(command)
            return await session.exec_command(
                argv,
                cwd=cwd,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                env=dict(env) if env is not None else None,
            )
        if resolved_settings.sandbox.fail_if_unavailable:
            from openharness.sandbox import SandboxUnavailableError

            raise SandboxUnavailableError("Docker sandbox session is not running")

    # Existing srt path
    argv = resolve_shell_command(command, prefer_pty=prefer_pty)

    # On Windows with bash, write the command to a temp script file so that
    # bash reads it directly. This avoids Windows command-line quoting
    # (list2cmdline) which mangles POSIX single quotes from shlex.quote and
    # can break $variable expansion inside -lc arguments.
    win_script_path: Path | None = None
    if get_platform() == "windows" and len(argv) >= 3 and argv[1] in ("-lc", "-c"):
        fd, script_file = tempfile.mkstemp(suffix=".sh", prefix="oh_cmd_")
        win_script_path = Path(script_file)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(command + "\n")
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            win_script_path.unlink(missing_ok=True)
            win_script_path = None
            raise
        bash_path = _windows_to_bash_path(str(win_script_path))
        login = "-l" if "l" in argv[1] else ""
        argv = [argv[0]] + ([login] if login else []) + [bash_path]

    argv, cleanup_path = wrap_command_for_sandbox(argv, settings=resolved_settings)

    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(Path(cwd).resolve()),
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=dict(env) if env is not None else None,
        )
    except Exception:
        if cleanup_path is not None:
            cleanup_path.unlink(missing_ok=True)
        if win_script_path is not None:
            win_script_path.unlink(missing_ok=True)
        raise

    if cleanup_path is not None:
        asyncio.create_task(_cleanup_after_exit(process, cleanup_path))
    if win_script_path is not None:
        asyncio.create_task(_cleanup_after_exit(process, win_script_path))
    return process


def _windows_to_bash_path(windows_path: str) -> str:
    """Convert a Windows path to a form bash can access.

    WSL bash needs ``/mnt/c/...`` while Git Bash accepts ``/c/...`` or
    forward-slash Windows paths. We try ``/mnt/c/`` first (works for WSL)
    and fall back to ``/c/`` (Git Bash / MSYS2).
    """
    p = windows_path.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].lower()
        rest = p[2:]
        return f"/mnt/{drive}{rest}"
    return p


def _wrap_command_with_script(argv: list[str]) -> list[str] | None:
    script = shutil.which("script")
    if script is None:
        return None
    if len(argv) >= 3 and argv[1] == "-lc":
        return [script, "-qefc", argv[2], "/dev/null"]
    return None


async def _cleanup_after_exit(process: asyncio.subprocess.Process, cleanup_path: Path) -> None:
    try:
        await process.wait()
    finally:
        cleanup_path.unlink(missing_ok=True)
