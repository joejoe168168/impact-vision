"""Exclusion screening runs inside `assess`: involvement fails the gate, a mention is a question."""
from __future__ import annotations

import pytest

from impact_vision.impact.exclusions import screen_exclusions
from impact_vision.impact.pipeline import assess_document, assess_file, sample_deck_path
from impact_vision.impact.report_templates.decision_report import render_decision_report

DECK = """# SunPath Energy

SunPath sells pay-as-you-go solar home systems to off-grid households in rural Kenya.

## Traction
- We have connected 42,000 households across 14 counties.
- Household energy spend fell 30% versus a matched comparison group.
{extra}
"""


@pytest.mark.parametrize(("sentence", "passed", "kind"), [
    ("We also operate a coal mining subsidiary in Mpumalanga.", False, "involvement"),
    ("Revenue comes from oil drilling services.", False, "involvement"),
    ("We distribute cigarettes and snacks through 400 kiosks.", False, "involvement"),
    ("We do not finance coal mining.", True, "mention"),
    ("We lend to tobacco farmers switching to vegetables.", True, "mention"),
    ("Forced labour risk in the polysilicon supply chain: we audit suppliers yearly.", True, "mention"),
    ("Corruption is widespread in the region.", True, "mention"),     # never self-declared
    ("Over-indebtedness;", True, "mention"),                          # a heading states nothing
])
def test_involvement_fails_and_a_mention_is_a_question(sentence: str, passed: bool, kind: str) -> None:
    result = screen_exclusions(sentence)
    assert result["passed"] is passed
    assert [h["kind"] for h in result["hits"]] == [kind]
    assert bool(result["failures"]) is (not passed)


@pytest.mark.parametrize("sentence", [
    "Our no-tobacco policy applies to all outlets.",
    "All staff receive anti-bribery training.",
    "Our lamps replace kerosene and petroleum lamps.",
    "Petroleum jelly is our main input.",
])
def test_lookalike_words_do_not_match(sentence: str) -> None:
    assert screen_exclusions(sentence)["hits"] == []


def test_only_mandatory_involvement_fails() -> None:
    casino = screen_exclusions("We run an online casino for mobile users.")          # severity: common
    assert casino["passed"] and casino["questions"][0]["kind"] == "involvement"


def test_an_excluded_activity_fails_the_gate_and_quotes_the_sentence() -> None:
    clean = assess_document(DECK.format(extra=""), name="SunPath Energy")
    dirty = assess_document(DECK.format(extra="- We also operate a coal mining subsidiary in Mpumalanga."),
                            name="SunPath Energy")
    assert clean.report_data["expected_impact"]["gate"]["state"] != "fails_thesis"
    gate = dirty.report_data["expected_impact"]["gate"]
    assert gate["state"] == "fails_thesis"
    assert any("Fossil Fuel" in r and "coal mining subsidiary" in r for r in gate["reasons"])
    assert dirty.summary()["exclusions"] == {"passed": False, "failures": ["Fossil Fuel Exposure"]}
    assert dirty.summary()["suggested_conditions"] == []          # conditions do not cure an exclusion
    html = render_decision_report(dirty.report_data)
    assert "coal mining subsidiary" in html


def test_a_denial_changes_nothing_but_is_listed_to_confirm() -> None:
    clean = assess_document(DECK.format(extra=""), name="SunPath Energy")
    denied = assess_document(DECK.format(extra="- We do not finance coal mining."), name="SunPath Energy")
    assert denied.report_data["expected_impact"]["gate"]["state"] == clean.report_data["expected_impact"]["gate"]["state"]
    assert denied.report_data["exclusions"]["passed"]
    html = render_decision_report(denied.report_data)
    assert "Exclusion-list topics the documents mention" in html and "We do not finance coal mining" in html
    assert "排除清單議題" in render_decision_report(denied.report_data, lang="zh-HK")
    assert "Exclusion-list topics" not in render_decision_report(clean.report_data)


def test_sample_decks_pass_the_screen() -> None:
    for deck in ("solar", "microfinance", "pig-farm"):
        bundle = assess_file(sample_deck_path(deck))
        assert bundle.report_data["exclusions"]["passed"], deck
        assert bundle.report_data["expected_impact"]["gate"]["state"] != "fails_thesis"


def test_criteria_are_sourced_hashed_and_shared_with_the_agent_tool() -> None:
    from impact_vision.impact import methodology
    from impact_vision.impact.exclusions import criteria
    from impact_vision.impact.knowledge import freshness_report
    from impact_vision.tools.impact.exclusion_screening_tool import _load_exclusion_criteria

    assert "exclusion_criteria.yaml" in methodology.HASHED_FILES
    assert freshness_report(names=["exclusion_criteria"]).ok
    assert _load_exclusion_criteria() is criteria() or _load_exclusion_criteria() == criteria()
