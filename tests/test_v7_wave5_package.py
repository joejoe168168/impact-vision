"""``impact_vision`` is the package (v8 W5.1 physical move); ``openharness`` is its alias."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    ("alias", "real"),
    [
        ("impact_vision.sdk", "impact_vision.impact.sdk"),
        ("impact_vision.frameworks.esrs", "impact_vision.impact.frameworks.esrs"),
        ("impact_vision.engagements.workspace", "impact_vision.impact.engagements.workspace"),
        ("impact_vision.tools.framework_tool", "impact_vision.tools.impact.framework_tool"),
        ("openharness.cli", "impact_vision.cli"),
        ("openharness.impact.models", "impact_vision.impact.models"),
        ("openharness.tools.impact.framework_tool", "impact_vision.tools.impact.framework_tool"),
    ],
)
def test_alias_is_the_same_module_object(alias: str, real: str) -> None:
    assert importlib.import_module(alias) is importlib.import_module(real)


def test_alias_keeps_the_real_spec() -> None:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        mod = importlib.import_module("openharness.config")
    assert mod.__spec__.name == mod.__name__ == "impact_vision.config"


def test_physical_top_level_names_win_over_short_names() -> None:
    plugins = importlib.import_module("impact_vision.plugins")
    assert plugins.__name__ == "impact_vision.plugins"  # not impact_vision.impact.plugins
    from impact_vision.tools import ImpactReportTool, create_default_tool_registry

    assert ImpactReportTool.__module__.startswith("impact_vision.tools.impact")
    assert callable(create_default_tool_registry)


def test_module_entry_points() -> None:
    import subprocess
    import sys

    for name in ("impact_vision", "openharness"):
        out = subprocess.run([sys.executable, "-m", name, "--version"], capture_output=True, text=True, timeout=120)
        assert out.returncode == 0, out.stderr[-400:]


def test_top_level_conveniences() -> None:
    import impact_vision
    from impact_vision import ImpactVision
    from impact_vision.impact.sdk import ImpactVision as Real

    assert ImpactVision is Real
    assert impact_vision.impact is importlib.import_module("impact_vision.impact")
    assert impact_vision.methodology.methodology_version()
    with pytest.raises(ImportError):
        importlib.import_module("impact_vision.does_not_exist")


def test_wheel_excludes_unused_subpackages() -> None:
    import tomllib
    from pathlib import Path

    cfg = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    root = Path(__file__).resolve().parents[1]
    # v8 W5.1: the unused chat-channel gateway, vim helpers and ohmo are gone.
    for gone in ("src/impact_vision/channels", "src/impact_vision/vim", "ohmo"):
        assert not (root / gone).exists(), gone
    assert cfg["project"]["scripts"]["impact-vision"] == "impact_vision.cli:app"
