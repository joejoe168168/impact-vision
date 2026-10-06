"""Roadmap v7 W5.5 — ``impact_vision`` is the supported import path."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    ("alias", "real"),
    [
        ("impact_vision.sdk", "openharness.impact.sdk"),
        ("impact_vision.frameworks.esrs", "openharness.impact.frameworks.esrs"),
        ("impact_vision.engagements.workspace", "openharness.impact.engagements.workspace"),
        ("impact_vision.tools", "openharness.tools.impact"),
        ("impact_vision.tools.framework_tool", "openharness.tools.impact.framework_tool"),
        ("impact_vision.cli", "openharness.cli"),
    ],
)
def test_alias_is_the_same_module_object(alias: str, real: str) -> None:
    assert importlib.import_module(alias) is importlib.import_module(real)


def test_top_level_conveniences() -> None:
    import impact_vision
    from impact_vision import ImpactVision
    from openharness.impact.sdk import ImpactVision as Real

    assert ImpactVision is Real
    assert impact_vision.impact is importlib.import_module("openharness.impact")
    assert impact_vision.methodology.methodology_version()
    with pytest.raises(ImportError):
        importlib.import_module("impact_vision.does_not_exist")


def test_wheel_excludes_unused_subpackages() -> None:
    import tomllib
    from pathlib import Path

    cfg = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    wheel = cfg["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert {"src/openharness/channels", "src/openharness/vim"} <= set(wheel["exclude"])
    assert cfg["project"]["scripts"]["impact-vision"] == "impact_vision.cli:app"
