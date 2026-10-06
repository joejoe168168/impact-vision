"""Transport-agnostic chat sessions for the Impact Vision web chat UI.

This module is the browser-facing sibling of :mod:`openharness.ui.backend_host`.
``ReactBackendHost`` drives the same runtime over stdin/stdout JSON lines for
the Ink/React terminal frontend; here we drive it over an in-memory pub/sub
fan-out so any number of WebSocket clients can watch (and steer) the same
conversation.

Design notes
------------
* **One runtime per conversation.** :class:`ChatSession` owns exactly one
  :class:`~openharness.ui.runtime.RuntimeBundle` — the same object the CLI and
  the terminal UI build — so slash commands, skills, hooks, MCP servers,
  permissions and the full impact toolbox behave identically in the browser.
* **Events are broadcast, not point-to-point.** Every subscriber gets its own
  ``asyncio.Queue``; closing a browser tab does not interrupt a running turn,
  and reopening it replays the stored transcript.
* **Transcripts are persisted** to ``~/.openharness/web-chat/`` so the sidebar
  survives a server restart. This is deliberately separate from the engine's
  own session snapshots (``openharness.services.session_storage``), which store
  raw model messages rather than UI-shaped rows.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable
from uuid import uuid4

from openharness.engine.stream_events import (
    AssistantTextDelta,
    AssistantTurnComplete,
    CompactProgressEvent,
    ErrorEvent,
    StatusEvent,
    StreamEvent,
    ToolExecutionCompleted,
    ToolExecutionStarted,
)
from openharness.tasks import get_task_manager
from openharness.ui.runtime import build_runtime, close_runtime, handle_line, start_runtime

log = logging.getLogger(__name__)

# Tools whose completion means "a file appeared on disk" — used to populate the
# artifact panel without polling the filesystem. Names match the registry in
# ``openharness.tools``; the CamelCase aliases cover MCP servers and plugins
# that follow the more common naming convention.
_WRITE_TOOLS = {
    "write_file",
    "edit_file",
    "notebook_edit",
    "impact_report",
    "lp_ddq_export",
    "ddq_responder",
    "Write",
    "Edit",
    "NotebookEdit",
}

_PATH_KEYS = ("output_path", "path", "file_path", "notebook_path", "filename")

# Impact tools report where they wrote to in prose, e.g.
# ``XLSX report saved to: /tmp/report.xlsx``. Catch that for any tool, so new
# report writers show up in the panel without being added to the allowlist.
_SAVED_TO = re.compile(r"saved to:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

_MAX_TRANSCRIPT_ROWS = 2000


def web_chat_dir() -> Path:
    """Return (and create) the directory holding persisted web transcripts."""
    root = Path(os.environ.get("IMPACT_VISION_WEB_HOME", Path.home() / ".openharness"))
    target = root / "web-chat"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _now() -> float:
    return time.time()


def _derive_title(text: str) -> str:
    """Turn the first user message into a sidebar title."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "New chat"
    if cleaned.startswith("/"):
        cleaned = cleaned.lstrip("/")
    return cleaned[:60] + ("…" if len(cleaned) > 60 else "")


@dataclass
class Artifact:
    """One file the agent produced during a conversation."""

    path: str
    name: str
    tool: str
    created_at: float

    def as_dict(self) -> dict[str, Any]:
        size: int | None = None
        exists = False
        with contextlib.suppress(OSError):
            stat = Path(self.path).stat()
            size = stat.st_size
            exists = True
        return {
            "path": self.path,
            "name": self.name,
            "tool": self.tool,
            "created_at": self.created_at,
            "size": size,
            "exists": exists,
        }


@dataclass
class SessionOptions:
    """Runtime knobs applied when a conversation's engine is constructed."""

    model: str | None = None
    max_turns: int | None = None
    base_url: str | None = None
    system_prompt: str | None = None
    api_key: str | None = None
    api_format: str | None = None
    active_profile: str | None = None
    permission_mode: str | None = None
    cwd: str | None = None
    extra_skill_dirs: tuple[str, ...] = ()
    extra_plugin_roots: tuple[str, ...] = ()
    # Web chat is for fund managers / consultants: impact tools only, no shell
    # or file writes. IMPACT_VISION_TOOL_PROFILE=developer restores everything.
    tool_profile: str | None = field(
        default_factory=lambda: os.environ.get("IMPACT_VISION_TOOL_PROFILE") or "fund"
    )
    # Injected client — used by tests and by embedders that already hold a
    # configured API client. Never persisted.
    api_client: Any = None


class ChatSession:
    """One browser conversation backed by a full OpenHarness runtime."""

    def __init__(
        self,
        *,
        session_id: str | None = None,
        options: SessionOptions | None = None,
        title: str = "New chat",
    ) -> None:
        self.session_id = session_id or uuid4().hex[:12]
        self.options = options or SessionOptions()
        self.title = title
        self.created_at = _now()
        self.updated_at = self.created_at
        self.transcript: list[dict[str, Any]] = []
        self.artifacts: list[Artifact] = []

        self._bundle: Any = None
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._permission_requests: dict[str, asyncio.Future[bool]] = {}
        self._question_requests: dict[str, asyncio.Future[str]] = {}
        self._turn_task: asyncio.Task[Any] | None = None
        self._start_lock = asyncio.Lock()
        self._last_tool_inputs: dict[str, dict[str, Any]] = {}
        self._pending_modals: dict[str, dict[str, Any]] = {}
        self.started = False
        self.busy = False
        self.closed = False
        self.startup_error: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def ensure_started(self) -> None:
        """Build the runtime on first use. Safe to call repeatedly."""
        async with self._start_lock:
            if self.started or self.closed:
                return
            opts = self.options
            try:
                self._bundle = await build_runtime(
                    model=opts.model,
                    max_turns=opts.max_turns,
                    base_url=opts.base_url,
                    system_prompt=opts.system_prompt,
                    api_key=opts.api_key,
                    api_format=opts.api_format,
                    active_profile=opts.active_profile,
                    api_client=opts.api_client,
                    cwd=opts.cwd or os.getcwd(),
                    permission_prompt=self._ask_permission,
                    ask_user_prompt=self._ask_question,
                    permission_mode=opts.permission_mode,
                    extra_skill_dirs=opts.extra_skill_dirs or None,
                    extra_plugin_roots=opts.extra_plugin_roots or None,
                    tool_profile=opts.tool_profile,
                )
                await start_runtime(self._bundle)
            except SystemExit as exc:
                # ``_resolve_api_client_from_settings`` exits the process when no
                # credentials are configured. In a long-lived server that must
                # become a recoverable, user-visible error instead.
                self.startup_error = (
                    "No API credentials configured. Open Settings (top right) to add a provider "
                    "key (Anthropic, OpenAI, OpenRouter or a local Ollama), or run "
                    "impact-vision setup in a terminal."
                )
                log.warning("Session %s failed to start: %s", self.session_id, exc)
                await self._emit({"type": "error", "message": self.startup_error})
                return
            except Exception as exc:  # noqa: BLE001 - surfaced to the browser
                self.startup_error = f"Failed to start session: {exc}"
                log.exception("Session %s failed to start", self.session_id)
                await self._emit({"type": "error", "message": self.startup_error})
                return

            self.started = True
            self.startup_error = None
            await self._emit(self._ready_event())

    def _ready_event(self) -> dict[str, Any]:
        commands: list[dict[str, str]] = []
        state: dict[str, Any] = {}
        if self._bundle is not None:
            with contextlib.suppress(Exception):
                commands = [
                    {"name": f"/{command.name}", "description": getattr(command, "description", "")}
                    for command in self._bundle.commands.list_commands()
                ]
            with contextlib.suppress(Exception):
                from openharness.ui.protocol import _state_payload

                state = _state_payload(self._bundle.app_state.get())
        return {
            "type": "ready",
            "session_id": self.session_id,
            "title": self.title,
            "state": state,
            "commands": commands,
            "busy": self.busy,
        }

    async def close(self) -> None:
        """Cancel any running turn and tear down the runtime."""
        self.closed = True
        await self.cancel()
        if self._bundle is not None:
            with contextlib.suppress(Exception):
                await close_runtime(self._bundle)
            self._bundle = None
        self.started = False
        await self._emit({"type": "closed", "session_id": self.session_id})

    # ------------------------------------------------------------------
    # Pub/sub
    # ------------------------------------------------------------------

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        """Yield a queue receiving every event emitted while subscribed."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=4096)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    async def _emit(self, event: dict[str, Any]) -> None:
        event.setdefault("session_id", self.session_id)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover - slow client
                log.warning("Dropping event for a slow web client on %s", self.session_id)

    def _record(self, row: dict[str, Any]) -> None:
        """Append a transcript row that will be replayed on reconnect."""
        row.setdefault("ts", _now())
        self.transcript.append(row)
        if len(self.transcript) > _MAX_TRANSCRIPT_ROWS:
            del self.transcript[: len(self.transcript) - _MAX_TRANSCRIPT_ROWS]
        self.updated_at = row["ts"]

    def snapshot(self) -> dict[str, Any]:
        """Full replay payload sent to a client that just connected."""
        return {
            "type": "snapshot",
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "transcript": self.transcript,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "busy": self.busy,
            "started": self.started,
            "startup_error": self.startup_error,
            "pending_modals": list(self._pending_modals.values()),
        }

    def meta(self) -> dict[str, Any]:
        """Compact record used by the conversation sidebar."""
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": sum(1 for row in self.transcript if row.get("role") in ("user", "assistant")),
            "busy": self.busy,
            "model": self.options.model,
        }

    # ------------------------------------------------------------------
    # Turn handling
    # ------------------------------------------------------------------

    async def submit(self, line: str) -> None:
        """Queue a user line for processing. Returns as soon as the turn starts."""
        text = (line or "").strip()
        if not text:
            return
        if self.busy:
            await self._emit({"type": "error", "message": "This conversation is already running a turn."})
            return
        await self.ensure_started()
        if not self.started:
            return
        if self.title in ("", "New chat") and not text.startswith("/"):
            self.title = _derive_title(text)
            await self._emit({"type": "title", "title": self.title})

        self.busy = True
        await self._emit({"type": "busy", "busy": True})
        self._turn_task = asyncio.create_task(self._run_turn(text))

    async def _run_turn(self, text: str) -> None:
        row = {"role": "user", "text": text}
        self._record(row)
        await self._emit({"type": "transcript_item", "item": row})
        try:
            should_continue = await handle_line(
                self._bundle,
                text,
                print_system=self._print_system,
                render_event=self._render_event,
                clear_output=self._clear_output,
            )
            if not should_continue:
                await self._emit({"type": "exit_requested"})
        except asyncio.CancelledError:
            note = {"role": "system", "text": "⏹ Stopped by user."}
            self._record(note)
            await self._emit({"type": "transcript_item", "item": note})
            raise
        except Exception as exc:  # noqa: BLE001 - keep the server alive
            log.exception("Turn failed on session %s", self.session_id)
            await self._emit({"type": "error", "message": f"Turn failed: {exc}"})
        finally:
            self.busy = False
            self._turn_task = None
            self._fail_pending_modals()
            with contextlib.suppress(Exception):
                await self._emit(self._status_event())
            await self._emit({"type": "busy", "busy": False})
            await self._emit({"type": "turn_complete"})
            self.persist()

    async def cancel(self) -> None:
        """Interrupt the in-flight turn, if any."""
        task = self._turn_task
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self._fail_pending_modals()
        self.busy = False

    def _fail_pending_modals(self) -> None:
        for request_id, future in list(self._permission_requests.items()):
            if not future.done():
                future.set_result(False)
            self._permission_requests.pop(request_id, None)
        for request_id, future in list(self._question_requests.items()):
            if not future.done():
                future.set_result("")
            self._question_requests.pop(request_id, None)
        self._pending_modals.clear()

    # ------------------------------------------------------------------
    # Runtime callbacks
    # ------------------------------------------------------------------

    async def _print_system(self, message: str) -> None:
        row = {"role": "system", "text": message}
        self._record(row)
        await self._emit({"type": "transcript_item", "item": row})

    async def _clear_output(self) -> None:
        self.transcript.clear()
        self.artifacts.clear()
        await self._emit({"type": "clear_transcript"})

    async def _render_event(self, event: StreamEvent) -> None:
        if isinstance(event, AssistantTextDelta):
            await self._emit({"type": "assistant_delta", "text": event.text})
            return

        if isinstance(event, AssistantTurnComplete):
            text = event.message.text.strip()
            usage = getattr(event, "usage", None)
            row: dict[str, Any] = {"role": "assistant", "text": text}
            if usage is not None:
                row["usage"] = {
                    "input_tokens": getattr(usage, "input_tokens", None),
                    "output_tokens": getattr(usage, "output_tokens", None),
                }
            self._record(row)
            await self._emit({"type": "assistant_complete", "item": row})
            return

        if isinstance(event, ToolExecutionStarted):
            self._last_tool_inputs[event.tool_name] = event.tool_input or {}
            row = {
                "role": "tool",
                "tool_name": event.tool_name,
                "tool_input": event.tool_input,
                "text": "",
            }
            self._record(row)
            await self._emit({"type": "tool_started", "item": row})
            return

        if isinstance(event, ToolExecutionCompleted):
            row = {
                "role": "tool_result",
                "tool_name": event.tool_name,
                "text": event.output,
                "is_error": bool(event.is_error),
            }
            self._record(row)
            await self._emit({"type": "tool_completed", "item": row})
            if not event.is_error:
                self._maybe_record_artifact(event.tool_name, event.output)
            await self._emit_tasks()
            return

        if isinstance(event, CompactProgressEvent):
            await self._emit(
                {
                    "type": "compact_progress",
                    "phase": event.phase,
                    "trigger": event.trigger,
                    "message": event.message,
                    "attempt": event.attempt,
                }
            )
            return

        if isinstance(event, ErrorEvent):
            row = {"role": "system", "text": event.message, "is_error": True}
            self._record(row)
            await self._emit({"type": "error", "message": event.message})
            await self._emit({"type": "transcript_item", "item": row})
            return

        if isinstance(event, StatusEvent):
            await self._print_system(event.message)

    def _maybe_record_artifact(self, tool_name: str, output: str = "") -> None:
        """Record files a tool just produced.

        Two signals, both gated on the file actually existing so a reader tool
        can never masquerade as a writer: a path argument on an allow-listed
        write tool, and a ``saved to: <path>`` line in any tool's output.
        """
        candidates: list[str] = []
        if tool_name in _WRITE_TOOLS:
            tool_input = self._last_tool_inputs.get(tool_name) or {}
            candidates.extend(
                str(tool_input[key]) for key in _PATH_KEYS if isinstance(tool_input.get(key), str) and tool_input[key]
            )
        candidates.extend(match.group(1) for match in _SAVED_TO.finditer(output or ""))

        for raw_path in candidates:
            try:
                path = Path(raw_path.strip().strip("\"'")).expanduser()
                if not path.is_file():
                    continue
                resolved = str(path.resolve())
            except (OSError, ValueError):
                continue
            if any(existing.path == resolved for existing in self.artifacts):
                continue
            self.artifacts.append(
                Artifact(path=resolved, name=path.name, tool=tool_name, created_at=_now())
            )

    async def _emit_tasks(self) -> None:
        with contextlib.suppress(Exception):
            tasks = [
                {
                    "id": task.id,
                    "type": task.type,
                    "status": task.status,
                    "description": task.description,
                }
                for task in get_task_manager().list_tasks()
            ]
            await self._emit({"type": "tasks", "tasks": tasks})

    def _status_event(self) -> dict[str, Any]:
        from openharness.ui.protocol import _state_payload

        state: dict[str, Any] = {}
        mcp: list[dict[str, Any]] = []
        if self._bundle is not None:
            with contextlib.suppress(Exception):
                state = _state_payload(self._bundle.app_state.get())
            with contextlib.suppress(Exception):
                mcp = [
                    {
                        "name": status.name,
                        "state": status.state,
                        "tool_count": len(status.tools),
                    }
                    for status in self._bundle.mcp_manager.list_statuses()
                ]
        return {"type": "state", "state": state, "mcp_servers": mcp}

    # ------------------------------------------------------------------
    # Interactive prompts
    # ------------------------------------------------------------------

    async def _ask_permission(self, tool_name: str, reason: str) -> bool:
        request_id = uuid4().hex
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self._permission_requests[request_id] = future
        modal = {
            "kind": "permission",
            "request_id": request_id,
            "tool_name": tool_name,
            "reason": reason,
        }
        self._pending_modals[request_id] = modal
        await self._emit({"type": "modal_request", "modal": modal})
        try:
            return await asyncio.wait_for(future, timeout=600)
        except asyncio.TimeoutError:
            log.warning("Permission request %s timed out", request_id)
            return False
        finally:
            self._permission_requests.pop(request_id, None)
            self._pending_modals.pop(request_id, None)
            await self._emit({"type": "modal_resolved", "request_id": request_id})

    async def _ask_question(self, question: str) -> str:
        request_id = uuid4().hex
        future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        self._question_requests[request_id] = future
        modal = {"kind": "question", "request_id": request_id, "question": question}
        self._pending_modals[request_id] = modal
        await self._emit({"type": "modal_request", "modal": modal})
        try:
            return await future
        finally:
            self._question_requests.pop(request_id, None)
            self._pending_modals.pop(request_id, None)
            await self._emit({"type": "modal_resolved", "request_id": request_id})

    def resolve_permission(self, request_id: str, allowed: bool) -> bool:
        future = self._permission_requests.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(bool(allowed))
        return True

    def resolve_question(self, request_id: str, answer: str) -> bool:
        future = self._question_requests.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(answer or "")
        return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _store_path(self) -> Path:
        return web_chat_dir() / f"{self.session_id}.json"

    def persist(self) -> None:
        """Write the transcript to disk so it survives a server restart."""
        payload = {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "transcript": self.transcript,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "options": {
                "model": self.options.model,
                "active_profile": self.options.active_profile,
                "permission_mode": self.options.permission_mode,
                "cwd": self.options.cwd,
            },
        }
        try:
            tmp = self._store_path().with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
            tmp.replace(self._store_path())
        except OSError as exc:  # pragma: no cover - disk issues
            log.warning("Could not persist web chat %s: %s", self.session_id, exc)

    def delete_stored(self) -> None:
        with contextlib.suppress(OSError):
            self._store_path().unlink()

    @classmethod
    def from_stored(cls, payload: dict[str, Any]) -> "ChatSession":
        stored_options = payload.get("options") or {}
        session = cls(
            session_id=payload.get("session_id") or uuid4().hex[:12],
            title=payload.get("title") or "New chat",
            options=SessionOptions(
                model=stored_options.get("model"),
                active_profile=stored_options.get("active_profile"),
                permission_mode=stored_options.get("permission_mode"),
                cwd=stored_options.get("cwd"),
            ),
        )
        session.created_at = float(payload.get("created_at") or _now())
        session.updated_at = float(payload.get("updated_at") or session.created_at)
        session.transcript = list(payload.get("transcript") or [])
        for raw in payload.get("artifacts") or []:
            session.artifacts.append(
                Artifact(
                    path=raw.get("path", ""),
                    name=raw.get("name", ""),
                    tool=raw.get("tool", ""),
                    created_at=float(raw.get("created_at") or session.created_at),
                )
            )
        return session


@dataclass
class ChatSessionManager:
    """Registry of live conversations plus the on-disk transcript archive."""

    default_options: SessionOptions = field(default_factory=SessionOptions)
    sessions: dict[str, ChatSession] = field(default_factory=dict)
    _loaded_archive: bool = False

    # -- creation -------------------------------------------------------

    def create(self, *, title: str = "New chat", overrides: dict[str, Any] | None = None) -> ChatSession:
        options = SessionOptions(**{**self.default_options.__dict__, **(overrides or {})})
        session = ChatSession(options=options, title=title)
        self.sessions[session.session_id] = session
        session.persist()
        return session

    def get(self, session_id: str) -> ChatSession | None:
        session = self.sessions.get(session_id)
        if session is not None:
            return session
        restored = self._load_from_disk(session_id)
        if restored is not None:
            self.sessions[restored.session_id] = restored
        return restored

    def get_or_create(self, session_id: str | None) -> ChatSession:
        if session_id:
            found = self.get(session_id)
            if found is not None:
                return found
        return self.create()

    async def delete(self, session_id: str) -> bool:
        session = self.sessions.pop(session_id, None)
        if session is not None:
            await session.close()
            session.delete_stored()
            return True
        path = web_chat_dir() / f"{session_id}.json"
        if path.exists():
            with contextlib.suppress(OSError):
                path.unlink()
            return True
        return False

    def rename(self, session_id: str, title: str) -> bool:
        session = self.get(session_id)
        if session is None:
            return False
        session.title = title.strip()[:120] or "New chat"
        session.persist()
        return True

    # -- listing --------------------------------------------------------

    def list_sessions(self) -> list[dict[str, Any]]:
        """Live sessions merged over the on-disk archive, newest first."""
        merged: dict[str, dict[str, Any]] = {}
        for payload in self._archive_payloads():
            merged[payload["session_id"]] = {
                "session_id": payload["session_id"],
                "title": payload.get("title") or "New chat",
                "created_at": payload.get("created_at", 0),
                "updated_at": payload.get("updated_at", 0),
                "message_count": sum(
                    1 for row in payload.get("transcript") or [] if row.get("role") in ("user", "assistant")
                ),
                "busy": False,
                "model": (payload.get("options") or {}).get("model"),
            }
        for session in self.sessions.values():
            merged[session.session_id] = session.meta()
        return sorted(merged.values(), key=lambda item: item.get("updated_at") or 0, reverse=True)

    def _archive_payloads(self) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for path in web_chat_dir().glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and payload.get("session_id"):
                payloads.append(payload)
        return payloads

    def _load_from_disk(self, session_id: str) -> ChatSession | None:
        path = web_chat_dir() / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        session = ChatSession.from_stored(payload)
        # Archived sessions inherit the server's current runtime defaults so a
        # restored conversation still points at a working provider.
        session.options = SessionOptions(
            **{
                **self.default_options.__dict__,
                **{k: v for k, v in session.options.__dict__.items() if v},
            }
        )
        return session

    async def shutdown(self) -> None:
        for session in list(self.sessions.values()):
            with contextlib.suppress(Exception):
                session.persist()
                await session.close()
        self.sessions.clear()


_MANAGER: ChatSessionManager | None = None


def get_session_manager(factory: Callable[[], ChatSessionManager] | None = None) -> ChatSessionManager:
    """Return the process-wide session manager, creating it on first use."""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = factory() if factory else ChatSessionManager()
    return _MANAGER


def reset_session_manager() -> None:
    """Drop the global manager. Used by tests."""
    global _MANAGER
    _MANAGER = None


__all__ = [
    "Artifact",
    "ChatSession",
    "ChatSessionManager",
    "SessionOptions",
    "get_session_manager",
    "reset_session_manager",
    "web_chat_dir",
]
