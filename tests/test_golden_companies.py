"""W0.9: golden companies — outputs a domain expert would sign off on.

These are plausibility tests, not snapshot tests: they pin the behaviours the
v7 review found broken (dropped claims, sector-blind DD, implausible SDGs,
false red flags) on three realistic companies.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from impact_vision.impact.models import Company
from impact_vision.impact.sdk import ImpactVision
from impact_vision.tools.impact.impact_report_tool import _to_html

REPO = Path(__file__).resolve().parents[1]

SOLAR_DECK = (
    "SunPath Energy sells pay-as-you-go solar home systems to off-grid households in rural "
    "Kenya. We have connected 42,000 households, replacing kerosene lamps and reducing "
    "household energy spend by 30%. Our systems avoided an estimated 20,000 tCO2e in 2024. "
    "We track customer repayment and satisfaction monthly through call-centre surveys, and "
    "62% of our customers live below the national poverty line according to the Poverty "
    "Probability Index. A 2025 study by an independent evaluator compared customers with a "
    "matched control group and found 18% higher evening study hours for children."
)


@pytest.fixture(scope="module")
def pig_farm() -> dict:
    sys.path.insert(0, str(REPO / "examples"))
    try:
        from generate_pig_farm_reports import assess_and_assemble
    finally:
        sys.path.pop(0)
    profile = json.loads((REPO / "demo" / "pig_farm_profile.json").read_text(encoding="utf-8"))
    return assess_and_assemble(profile)


@pytest.fixture(scope="module")
def brightpath():
    data = yaml.safe_load((REPO / "examples" / "sample_company.yaml").read_text(encoding="utf-8"))
    return ImpactVision().assess_company(Company(**data["company"]))


# --- Pig farm (agriculture, evidence-rich pitch, no IRIS+ IDs) -------------


def test_pig_farm_claims_are_tracked_as_evidence(pig_farm):
    claims = pig_farm["assess"].impact_claims
    assert len(claims) >= 5
    assert any(c.evidence_strength >= 3 for c in claims)  # RCT / SIRIM-verified
    html = _to_html(pig_farm["report_data"])
    assert 'id="sec-claims"' in html
    assert "Third-party verified" in html


def test_pig_farm_is_not_flagged_unverified(pig_farm):
    assert not any(f.startswith("NO_VERIFICATION") for f in pig_farm["gw"].flags)


def test_pig_farm_dd_and_metrics_are_agricultural(pig_farm):
    dd = pig_farm["dd"]
    sector_cats = {q.category for q in dd.unanswered + [m.question for m in dd.addressed]
                   if q.category.startswith("sector_")}
    assert sector_cats <= {"sector_agriculture"}
    assert dd.coverage_pct > 20
    gaps = pig_farm["report_data"]["gap_analysis"]
    assert gaps["core_metric_set_basis"] == "agriculture"
    missing = {m["name"] for m in gaps["missing"]}
    assert "Client Protection Policy" not in missing
    assert "Revenue from Grants and Donations" not in missing


def test_pig_farm_risks_come_from_the_pitch(pig_farm):
    risks = pig_farm["report_data"]["impact_analysis"]["risks"]
    assert risks[0].startswith("Disclosed:")
    assert not any("energy projects" in r for r in risks)


def test_pig_farm_dd_report_has_no_unrelated_sector_risks(pig_farm):
    profile = json.loads((REPO / "demo" / "pig_farm_profile.json").read_text(encoding="utf-8"))
    html = ImpactVision().render_dd_report_html(
        profile["pitch_text"], company_name=profile["name"], sector="agriculture"
    )
    for unrelated in ("Fintech", "Health", "Mining"):
        assert f"Sector \u2014 {unrelated}" not in html
    assert "Sector \u2014 Agriculture" in html


# --- BrightPath (microfinance, many reported metrics) -----------------------


def test_brightpath_sdgs_are_plausible(brightpath):
    by_goal = {a.goal: a for a in brightpath.sdg_alignments}
    assert by_goal[14].confidence == "low" and not by_goal[14].material
    for claimed in (1, 5, 8, 10):
        assert by_goal[claimed].material
    for a in brightpath.sdg_alignments:
        assert all(t.startswith(f"{a.goal}.") for t in a.matched_targets)


# --- Solar (energy, quantified deck, no IRIS+ IDs) --------------------------


def test_solar_deck_is_not_a_red_flag():
    iv = ImpactVision()
    assessment = iv.assess_company_text("SunPath Energy", text=SOLAR_DECK, sector="energy")
    values = {c.text.split()[0] for c in assessment.impact_claims}
    assert values  # claims extracted
    units = {(c.metric_value, c.metric_unit) for c in iv.extract_claims(SOLAR_DECK)}
    assert (42000.0, "households") in units
    assert (20000.0, "tCO2e") in units

    screen = iv.quick_screen(
        assessment.company, claims=[c.model_dump() for c in assessment.impact_claims]
    )
    assert screen.classification != "red_flag"
    assert iv.run_dd_coverage(SOLAR_DECK, sector="energy").coverage_pct > 10


def test_pig_farm_numbers_reach_the_engines(pig_farm):
    # W0.10: quantified claims become IRIS+ metrics without the pitch citing IDs.
    metrics = pig_farm["assess"].company.reported_metrics
    assert {"OI2496", "OI2764", "OI8869", "PI9991"} <= set(metrics)
    assert pig_farm["assess"].five_dimensions.overall_provenance != "estimated"
    assert pig_farm["gw"].overall_score < 60


def test_pig_farm_gate_says_insufficient_evidence_not_block(pig_farm):
    from impact_vision.impact.ic_memo import render_ic_memo

    scorecard = pig_farm["scorecard"]
    assert scorecard.display_status == "INSUFFICIENT EVIDENCE"
    html = str(render_ic_memo(
        pig_farm["assess"], scorecard, pig_farm["thesis"], output_format="html"
    ))
    assert "BLOCK IC submission" not in html
