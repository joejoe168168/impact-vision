"""Figures that cannot be right are flagged, widen the range and lead the evidence plan."""
from __future__ import annotations

import pytest

from impact_vision.impact.consistency import population_of
from impact_vision.impact.expected_impact import suggest_conditions
from impact_vision.impact.pipeline import assess_document, assess_file, sample_deck_path
from impact_vision.impact.report_templates.decision_report import render_decision_report

DECK = """# BrightLamp

BrightLamp sells solar lanterns in Kenya.

## Traction
- We have reached {reach} people in Kenya.
- Household income rose {pct}% after one year.
- Our lanterns avoided {tonnes} tCO2e in 2025.

## Ask
USD 1m seed round.
"""


def _block(reach: str = "120,000", pct: str = "30", tonnes: str = "9,000") -> dict:
    deck = DECK.format(reach=reach, pct=pct, tonnes=tonnes)
    return assess_document(deck, name="BrightLamp", geography="Kenya").report_data["expected_impact"]


def test_population_lookup_knows_countries_regions_and_aliases() -> None:
    name, people, year = population_of("Kenya")
    assert name == "Kenya" and 50_000_000 < people < 65_000_000 and year >= 2023
    assert population_of("rural Kenya")[0] == "Kenya"
    assert population_of("Hong Kong")[0].startswith("Hong Kong") and population_of("香港")[0].startswith("Hong Kong")
    assert population_of("Vietnam")[1] > 90_000_000
    assert population_of("Sub-Saharan Africa")[1] > 1_000_000_000
    assert population_of("Kenya and Uganda") is None           # two places: no single population
    assert population_of("") is None and population_of("Atlantis") is None


def test_a_plausible_deck_has_no_flags() -> None:
    assert _block()["plausibility"] == []
    for deck in ("solar", "microfinance", "pig-farm"):
        assert assess_file(sample_deck_path(deck)).report_data["expected_impact"]["plausibility"] == [], deck


def test_reach_above_the_population_is_flagged_and_widens_the_range() -> None:
    plain = _block(reach="12 million")
    wild = _block(reach="120 million")
    (flag,) = wild["plausibility"]
    assert flag["kind"] == "reach_exceeds_population" and flag["severity"] == "doubt"
    assert flag["value"] == 120_000_000 and flag["place"] == "Kenya" and "120 million people" in flag["sentence"]
    people = lambda block: next(o for o in block["outcomes"] if o["kind"] == "people")  # noqa: E731
    assert people(wild)["spread"] > people(plain)["spread"]              # an implausible figure, a wider range
    reach = lambda block: next(f for f in people(block)["factors"] if f["name"] == "Reach")  # noqa: E731
    assert reach(wild)["sigma"] == pytest.approx(reach(plain)["sigma"] * 1.5)
    first = wild["evidence_plan"][0]
    assert first["kind"] == "plausibility" and "more than the population of Kenya" in first["action"]
    assert next(c for c in suggest_conditions(wild) if c["text"] == first["action"])["type"] == "condition_precedent"


def test_a_change_above_100_percent_is_noted_not_doubted() -> None:
    block = _block(pct="150")
    (flag,) = block["plausibility"]
    assert flag["kind"] == "depth_capped" and flag["severity"] == "note" and flag["value"] == pytest.approx(1.5)
    depth = next(f for o in block["outcomes"] if o["kind"] == "people" for f in o["factors"]
                 if f["name"] == "Depth of change")
    assert depth["median"] == 1.0                                         # still capped in the calculation
    assert all(item["kind"] != "plausibility" for item in block["evidence_plan"])


def test_tonnes_out_of_proportion_to_the_raise_are_flagged() -> None:
    assert _block(tonnes="150,000")["plausibility"] == []
    (flag,) = _block(tonnes="900,000")["plausibility"]
    assert flag["kind"] == "tonnes_per_usd" and flag["value"] == pytest.approx(900_000)


def test_report_lists_the_figures_to_check_in_every_language() -> None:
    data = assess_document(DECK.format(reach="120 million", pct="150", tonnes="9,000"), name="BrightLamp",
                           geography="Kenya").report_data
    en = render_decision_report(data)
    assert "Figures to check" in en and "more than the population of Kenya (56," in en
    assert "the calculation counts it as 100%" in en
    zh = render_decision_report(data, lang="zh-HK")
    assert "需要核對的數字" in zh and "核對覆蓋數字" in zh and "按 100% 處理" in zh
    assert "Figures to check" not in render_decision_report(
        assess_document(DECK.format(reach="120,000", pct="30", tonnes="9,000"), name="BrightLamp",
                        geography="Kenya").report_data)


def test_population_data_is_sourced_and_in_the_freshness_gate() -> None:
    from impact_vision.impact.knowledge import freshness_report

    report = freshness_report(names=["population"])
    assert report.ok and report.rows_checked > 200, report.summary()
