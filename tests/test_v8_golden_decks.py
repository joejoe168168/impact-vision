"""v8 W0.8: plausibility goldens across sectors, regions and languages.

v7 was tuned on three sample decks. These ten more (four from the post-v7
product review, six written for v8, one of them in Traditional Chinese) guard
against the generalisation failures that review found: wrong sector or place,
irrelevant SDGs, advice from another sector, and missing data treated as
greenwashing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from impact_vision.impact.pipeline import SAMPLE_DECKS, assess_file, sample_deck_path

DECKS = Path(__file__).parent / "golden_decks"

# file → (sector, geography, an SDG that must be in the top 3 material goals)
EXPECTED = {
    "afyaplus_clinics.md": ("healthcare", "Kenya", 3),
    "agosto_water_ph.md": ("water", "Philippines", 6),
    "belajar_edtech.md": ("education", "Indonesia", 4),
    "creditopyme_co.md": ("fintech", "Colombia", 1),
    "hearthstone_housing_uk.md": ("real estate", "United Kingdom", 11),
    "jaldhara_irrigation_in.md": ("agriculture", "India", 2),
    "loopwear_hk.md": ("waste management", "Hong Kong", 12),
    "warmloop_heatpumps_nl.md": ("energy", "Netherlands", 7),
    "yikang_eldercare_hk.md": ("healthcare", "Hong Kong", 3),
}
SAMPLES = {"pig-farm": ("agriculture", 2), "solar": ("energy", 7), "microfinance": ("fintech", 1)}

# Metrics that belong to one kind of business; advice to anyone else is noise.
OFF_SECTOR = {
    "Client Protection Policy": {"fintech", "healthcare"},
    "Client Model": {"fintech"},
    "Revenue from Grants and Donations": set(),
    "Racial Equity": set(),
    "Adaptation Needs Assessment": set(),
}


@pytest.fixture(scope="module")
def bundles():
    out = {name: assess_file(DECKS / name) for name in [*EXPECTED, "greenvibe.md"]}
    out.update({key: assess_file(sample_deck_path(key)) for key in SAMPLE_DECKS})
    return out


def _top_material(bundle, n=3):
    return [a.goal for a in bundle.assessment.sdg_alignments if a.material][:n]


def _advice(bundle) -> str:
    data = bundle.report_data
    gaps = data.get("gap_analysis") or {}
    parts = [*(gaps.get("recommendations") or []),
             *(m.get("name", "") for m in gaps.get("suggested_metrics") or []),
             *(bundle.greenwashing.recommendations or [])]
    for sdg in data.get("sdg_alignments") or []:
        parts += sdg.get("recommendations") or []
    fd = bundle.assessment.five_dimensions
    for dim in (fd.what, fd.who, fd.how_much, fd.contribution, fd.risk):
        parts += dim.gaps[:3]
    return " | ".join(str(p) for p in parts)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sector_geography_and_lead_sdg(bundles, name):
    sector, geography, sdg = EXPECTED[name]
    bundle = bundles[name]
    assert bundle.company.sector == sector
    assert bundle.company.geography == geography
    assert sdg in _top_material(bundle), _top_material(bundle, 6)


@pytest.mark.parametrize("key", sorted(SAMPLES))
def test_sample_decks_lead_sdg(bundles, key):
    sector, sdg = SAMPLES[key]
    assert bundles[key].company.sector == sector
    assert sdg in _top_material(bundles[key])


@pytest.mark.parametrize("name", sorted([*EXPECTED, *SAMPLES]))
def test_no_advice_from_another_sector(bundles, name):
    bundle = bundles[name]
    advice = _advice(bundle)
    for metric, allowed in OFF_SECTOR.items():
        if bundle.company.sector not in allowed:
            assert metric not in advice, f"{name} ({bundle.company.sector}) was told: {metric}"


@pytest.mark.parametrize("name", sorted([*EXPECTED, *SAMPLES]))
def test_honest_companies_are_not_greenwashing_findings(bundles, name):
    bundle = bundles[name]
    assert not bundle.greenwashing.is_finding, (name, bundle.greenwashing.overall_score)
    assert bundle.scorecard.display_status != "FAIL"


def test_vague_deck_is_the_greenwashing_finding(bundles):
    gw = bundles["greenvibe.md"].greenwashing
    assert gw.is_finding and not gw.evidence_gap
    assert gw.classification in {"High Risk", "Probable Greenwashing"}


def test_edtech_missing_data_is_an_evidence_gap_not_a_fail(bundles):
    """The post-v7 review's worst case: a strong deck FAILed for missing data."""
    bundle = bundles["belajar_edtech.md"]
    assert bundle.greenwashing.evidence_gap or not bundle.greenwashing.is_finding
    assert bundle.scorecard.display_status != "FAIL"


def test_problem_statements_do_not_cost_risk(bundles):
    notes = bundles["solar"].assessment.five_dimensions.risk.notes
    assert "adverse impact penalty" not in notes


def test_fund_side_questions_are_not_asked_of_founders(bundles):
    dd = bundles["belajar_edtech.md"].dd
    asked = {q.id for q in dd.unanswered} | {m.question.id for m in dd.addressed}
    assert not asked & {"IT03", "IA03", "CO04", "IA02"}
    assert {q.id for q in dd.fund_questions} >= {"IT03", "IA03"}


@pytest.mark.parametrize("name,company", [
    ("loopwear_hk.md", "LoopWear Limited"), ("hearthstone_housing_uk.md", "Hearthstone Homes Ltd"),
    ("jaldhara_irrigation_in.md", "Jaldhara Agritech"), ("yikang_eldercare_hk.md", "頤康長者護理"),
])
def test_company_names_are_read_from_titles(bundles, name, company):
    assert bundles[name].company.name == company


def test_lowercase_title_words_still_give_a_name():
    from impact_vision.impact.pipeline import assess_document

    assert assess_document("# Sunlit Homes — Seed pitch\n\nSunlit Homes sells lanterns.").company.name == "Sunlit Homes"
