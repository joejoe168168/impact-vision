"""C8: the readiness gate can say "ready"; completeness is a note, not a condition."""

from __future__ import annotations

from impact_vision.impact.expected_impact import _gate

GOOD = {"score": 70, "label": "good"}
WEAK = {"score": 40, "label": "limited"}


def _outcome(level: int = 3, spread: float = 5.0) -> dict:
    return {"kind": "people", "unit": "person-years", "p50": 100.0, "evidence_level": level, "spread": spread}


def _state(outcomes, eq, completeness):
    return _gate(outcomes, eq, completeness, None, [], [])


def test_ready_with_good_evidence_and_low_completeness():
    gate = _state([_outcome()], GOOD, 6.0)
    assert gate["state"] == "ready"
    assert "6%" in gate["note"]


def test_ready_without_note_when_completeness_is_fine():
    gate = _state([_outcome()], GOOD, 80.0)
    assert gate["state"] == "ready" and "note" not in gate


def test_unverified_count_is_an_evidence_plan():
    gate = _state([_outcome(level=1)], GOOD, 80.0)
    assert gate["state"] == "evidence_plan"
    assert any("evidence level 1" in r for r in gate["reasons"])


def test_wide_range_is_an_evidence_plan():
    gate = _state([_outcome(spread=20.0)], GOOD, 80.0)
    assert gate["state"] == "evidence_plan"
    assert any("range" in r for r in gate["reasons"])


def test_core_metrics_do_not_make_weak_evidence_ready():
    assert _state([_outcome()], WEAK, 100.0)["state"] == "evidence_plan"
    assert _state([], GOOD, 100.0)["state"] == "evidence_plan"
