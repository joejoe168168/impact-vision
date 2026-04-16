"""Installer regressions for Windows command aliases."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib


def test_pyproject_exposes_console_scripts():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert scripts["impact-vision"] == "openharness.cli:app"
    assert scripts["iv"] == "openharness.cli:app"
