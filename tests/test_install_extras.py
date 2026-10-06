"""W1.6: optional surfaces fail with install hints instead of tracebacks."""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from openharness.cli import app

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_core_dependencies_exclude_optional_surfaces():
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    core = " ".join(project["dependencies"]).lower()
    for heavy in ("streamlit", "fastapi", "pandas", "plotly", "textual"):
        assert heavy not in core
    extras = project["optional-dependencies"]
    assert {"web", "dashboard", "office", "tui", "all", "dev"} <= set(extras)
    assert "impact-vision[all]" in extras["dev"]


def _hide(monkeypatch, *missing: str):
    real = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util, "find_spec", lambda name, *a: None if name in missing else real(name, *a)
    )


def test_serve_web_without_extra_gives_hint(monkeypatch):
    _hide(monkeypatch, "fastapi")
    result = runner.invoke(app, ["serve-web"])
    assert result.exit_code == 1
    assert "impact-vision[web]" in result.output


def test_dashboard_without_extra_gives_hint(monkeypatch):
    _hide(monkeypatch, "streamlit")
    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 1
    assert "impact-vision[dashboard]" in result.output


def test_terminal_ui_without_node_explains_alternatives(monkeypatch):
    import asyncio

    from openharness.ui import react_launcher

    monkeypatch.setattr(react_launcher.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit) as exc:
        asyncio.run(react_launcher.launch_react_tui())
    message = str(exc.value)
    assert "Node.js" in message and "impact-vision demo" in message
