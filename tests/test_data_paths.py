"""Bundled reference data must resolve for source checkouts and installed wheels."""

from __future__ import annotations

from pathlib import Path

from openharness.impact import _paths
from openharness.impact.storage import _default_db_path


def test_data_path_resolves_repo_data():
    assert _paths.data_path("scoring_config.yaml").is_file()
    assert _paths.data_path("dd_checklist.yaml").is_file()


def test_env_override_wins(tmp_path, monkeypatch):
    (tmp_path / "scoring_config.yaml").write_text("x: 1\n")
    monkeypatch.setenv(_paths.ENV_VAR, str(tmp_path))
    assert _paths.data_path("scoring_config.yaml") == tmp_path / "scoring_config.yaml"
    # Files missing from the override fall through to the next root.
    assert _paths.data_path("dd_checklist.yaml").parent != tmp_path


def test_wheel_layout_is_a_fallback(tmp_path, monkeypatch):
    wheel_data = tmp_path / "_data"
    wheel_data.mkdir()
    (wheel_data / "only_in_wheel.yaml").write_text("a: 1\n")
    monkeypatch.setattr(_paths, "_WHEEL_DATA", wheel_data)
    monkeypatch.setattr(_paths, "_REPO_DATA", tmp_path / "missing")
    assert _paths.data_dir() == wheel_data
    assert _paths.data_path("only_in_wheel.yaml").is_file()


def test_no_loader_hardcodes_repo_relative_data():
    src = Path(_paths.__file__).resolve().parents[1]
    offenders = []
    for py in src.rglob("*.py"):
        if py.name == "_paths.py":
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        if 'parents[3] / "data"' in text or 'parent.parent.parent.parent / "data"' in text:
            offenders.append(str(py.relative_to(src)))
    assert offenders == []


def test_default_db_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("IMPACT_VISION_DB", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert _default_db_path() == tmp_path / "home" / ".impact-vision" / "impact_vision.db"
    monkeypatch.setenv("IMPACT_VISION_DB", str(tmp_path / "x.db"))
    assert _default_db_path() == tmp_path / "x.db"
