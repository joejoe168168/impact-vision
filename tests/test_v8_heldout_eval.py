"""Held-out evaluation must not regress (roadmap v8 W2.4).

The baseline is the first run on decks the engine had never seen. Improving
a number means fixing the engine on *other* documents; then raise the
baseline here. Lowering it needs a reason in the commit message.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from impact_vision.impact.heldout_eval import evaluate, to_markdown

HELDOUT = Path(__file__).parent / "golden" / "heldout"
TOLERANCE = 0.02


@pytest.fixture(scope="module")
def result():
    return evaluate(HELDOUT)


def test_the_set_is_broad_enough():
    labels = yaml.safe_load((HELDOUT / "labels.yaml").read_text(encoding="utf-8"))["decks"]
    assert len(labels) >= 30
    assert len({v["sector"] for v in labels.values()}) >= 10
    assert len({v["geography"] for v in labels.values()}) >= 6
    assert {"en", "zh-HK", "zh-CN"} <= {v["lang"] for v in labels.values()}
    assert sum(v["greenwash"] for v in labels.values()) >= 4
    assert all((HELDOUT / name).is_file() for name in labels)


def test_no_regression_against_the_baseline(result):
    baseline = json.loads((HELDOUT / "baseline.json").read_text())["summary"]
    worse = {k: (result["summary"][k], v) for k, v in baseline.items() if result["summary"][k] < v - TOLERANCE}
    assert not worse, f"held-out metrics fell below the baseline: {worse}\n{to_markdown(result)}"


def test_report_renders(result):
    md = to_markdown(result)
    assert "Fact F1" in md and md.count("\n| ") >= 30
