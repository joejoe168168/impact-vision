"""A denied or merely planned evidence cue is not evidence.

"We have no control group yet" used to read as a controlled evaluation,
"has not been audited" lowered verification risk, and "we do not yet have a
client protection policy" marked the harm as controlled.
"""
from __future__ import annotations

import re

import pytest

from impact_vision.impact.extractors.regex_extractor import evidence_signals
from impact_vision.impact.greenwashing import _score_verification
from impact_vision.impact.negation import asserts, asserts_phrase
from impact_vision.impact.negative_impacts import assess_negative_impacts
from impact_vision.impact.pipeline import assess_document

CUE = re.compile(r"\bcontrol\s+group\b|\bRCTs?\b|\baudited\b|對照組", re.IGNORECASE)

BASE = """# Sunlit Homes — Seed pitch

Sunlit Homes sells solar lanterns to off-grid households in rural Uganda.

## Traction
- 12,000 households served in 2024.
- Household lighting costs fell 35% versus their previous kerosene spend {how}.

## Ask
USD 2m seed round.
"""


@pytest.mark.parametrize(("sentence", "expected"), [
    ("(we have no control group yet)", False),
    ("No RCT, control group or baseline exists.", False),
    ("A control group has not yet been established.", False),
    ("We plan to run an RCT in 2027.", False),
    ("We will be audited by KPMG next year.", False),
    ("Our accounts have not been audited and nothing is verified.", False),
    ("我們尚未設立對照組。", False),
    # Positive statements survive a negation elsewhere in the sentence.
    ("A study compared customers with a matched control group and found 18% higher study hours.", True),
    ("We have no debt, and an RCT showed a 12% income gain.", True),
    ("The control group did not receive the product.", True),
    ("Not only are our accounts audited by KPMG, they are published.", True),
    ("We serve customers who cannot get credit; results are audited by KPMG.", True),
    ("研究設有對照組，結果顯示收入增加。", True),
])
def test_asserts_reads_the_clause_around_the_cue(sentence: str, expected: bool) -> None:
    assert asserts(CUE, sentence) is expected


def test_denied_cues_are_not_evidence_signals() -> None:
    assert "controlled_evaluation" not in evidence_signals("Costs fell 35% (we have no control group yet).")
    assert "controlled_evaluation" not in evidence_signals("We plan to run a randomised trial in 2027.")
    assert "third_party_verified" not in evidence_signals("Our impact data is not independently verified.")
    assert "controlled_evaluation" in evidence_signals("Costs fell 35% versus a matched comparison group.")
    assert "third_party_verified" in evidence_signals("Our impact data is independently verified.")


def _people(how: str) -> tuple[dict, dict]:
    block = assess_document(BASE.format(how=how), name="Sunlit Homes").report_data["expected_impact"]
    return next(o for o in block["outcomes"] if o["kind"] == "people"), block


def test_a_denied_control_group_earns_no_evidence_credit() -> None:
    plain, plain_block = _people("(customer survey, before and after)")
    denied, denied_block = _people("(customer survey; we have no control group yet)")
    real, real_block = _people("(independent study versus a matched comparison group)")

    deadweight = {f["name"]: f["median"] for f in denied["factors"]}["Without deadweight"]
    assert deadweight < 1.0                                  # nothing was netted out
    assert denied["evidence_level"] <= plain["evidence_level"]
    assert denied_block["evidence_quality"]["score"] <= plain_block["evidence_quality"]["score"]
    assert denied_block["evidence_quality"]["score"] < real_block["evidence_quality"]["score"]
    assert denied["spread"] > real["spread"]


def test_denied_verification_does_not_lower_verification_risk() -> None:
    silent = _score_verification("We sell solar lanterns to rural households.", set())
    denied = _score_verification(
        "We sell solar lanterns. Our accounts have not been audited and nothing is verified.", set())
    stated = _score_verification("We sell solar lanterns. Our accounts are audited by KPMG.", set())
    assert denied == silent
    assert stated < silent


def test_a_denied_control_leaves_the_negative_impact_unmanaged() -> None:
    absent = assess_negative_impacts(
        "fintech", "We lend to market traders. We do not yet have a client protection policy.")
    present = assess_negative_impacts(
        "fintech", "We lend to market traders. Our client protection policy caps instalments at 30% of income.")
    stated = [r for r in present["items"] if r["controlled"]]
    assert stated, "fixture should describe at least one control"
    ids = {r["id"] for r in stated}
    for row in absent["items"]:
        if row["id"] in ids:
            assert not row["controlled"] and not row["evidence"]


def test_asserts_phrase_is_case_insensitive_and_boundary_aware() -> None:
    assert asserts_phrase("Audited", "accounts are audited by KPMG")
    assert not asserts_phrase("audit", "unaudited-looking but really auditorium", word_boundary=True)


def test_signal_levels_come_from_the_methodology_file(tmp_path, monkeypatch) -> None:
    import shutil

    import yaml

    from impact_vision.impact import _paths, expected_impact
    from impact_vision.impact.extractors.base import level_for_signals

    assert level_for_signals(["controlled_evaluation"]) == 3
    assert level_for_signals([], quantified=True) == 2 and level_for_signals([]) == 1
    copy = tmp_path / "data"
    shutil.copytree(_paths.data_path(), copy, ignore=shutil.ignore_patterns("raw", "processed", "calibration"))
    target = copy / "methodology" / "v2.yaml"
    doc = yaml.safe_load(target.read_text(encoding="utf-8"))
    doc["signal_levels"]["controlled_evaluation"] = 4
    target.write_text(yaml.safe_dump(doc), encoding="utf-8")
    monkeypatch.setattr(expected_impact, "data_path", lambda *parts: copy.joinpath(*parts))
    expected_impact._load.cache_clear()
    try:
        assert level_for_signals(["controlled_evaluation"]) == 4
    finally:
        monkeypatch.undo()
        expected_impact._load.cache_clear()
