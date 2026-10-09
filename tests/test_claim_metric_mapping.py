"""W0.10: claim quantities map to IRIS+ IDs; data gaps don't BLOCK the IC gate."""

from __future__ import annotations

import pytest
import yaml

from impact_vision.impact._paths import data_path
from impact_vision.impact.claim_metric_mapper import map_claim_metrics
from impact_vision.impact.database import get_metric_store
from impact_vision.impact.deal_gate import evaluate_deal
from impact_vision.impact.fund_thesis import FundThesis
from impact_vision.impact.ic_memo import render_ic_memo
from impact_vision.impact.models import Company
from impact_vision.impact.sdk import ImpactVision


def _ids(sentence: str) -> dict[str, str]:
    return {m.metric_id: m.display for m in map_claim_metrics(sentence)}


def test_every_rule_targets_a_real_iris_metric():
    cfg = yaml.safe_load(data_path("claim_metric_map.yaml").read_text(encoding="utf-8"))
    store = get_metric_store()
    ids = {r["metric_id"] for r in cfg["rules"]} | {d["metric_id"] for d in cfg["derived"]}
    assert [i for i in sorted(ids) if store.get(i) is None] == []


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        (
            "Our biogas plant generates 1.8 GWh of electricity per year, replacing ~920 "
            "tonnes CO2e of grid emissions.",
            {"OI2496": "1,800 MWh", "OI2764": "920 tCO2e"},
        ),
        ("Our systems avoided an estimated 20,000 tCO2e in 2024.", {"OI2764": "20,000 tCO2e"}),
        ("Our solar farm generated and sold 12 GWh to the grid.", {"PI5842": "12,000 MWh"}),
        ("We have connected 42,000 households to solar power.", {"PI7954": "42,000"}),
        (
            "We run an outgrower programme with 18 smallholder piggeries.",
            {"PI9991": "18"},
        ),
    ],
)
def test_quantities_map_to_metrics(sentence, expected):
    assert _ids(sentence) == expected


def test_emitted_and_avoided_in_one_sentence_stay_separate():
    assert _ids("We emitted 1,200 tCO2e and avoided 3,000 tCO2e through our products.") == {
        "OI1479": "1,200 tCO2e",
        "OI2764": "3,000 tCO2e",
    }


def test_female_share_is_derived_and_labelled():
    mapped = _ids("We employ 142 staff, of whom 38% are women.")
    assert mapped["OI8869"] == "142"
    assert mapped["OI6213"].startswith("54 (derived: 38% of 142)")


@pytest.mark.parametrize(
    "sentence",
    [
        "We will avoid 5,000 tCO2e by 2030.",  # target, not a reported value
        "A pilot compared 120 households to a matched control group.",  # study sample
        "We trained 300 farmers in our programme.",  # ambiguous: no client/supplier role
        "Revenue grew 40% year on year.",
    ],
)
def test_no_mapping_for_targets_samples_or_ambiguity(sentence):
    assert "PI7954" not in _ids(sentence)
    assert "OI2764" not in _ids(sentence)
    assert "PI9991" not in _ids(sentence)


def test_sdk_feeds_mapped_metrics_without_overriding_explicit_ones():
    iv = ImpactVision()
    text = "Our systems avoided an estimated 20,000 tCO2e in 2024. We employ 50 staff."
    assessment = iv.assess_company_text("SunPath", text=text, sector="energy")
    assert assessment.company.reported_metrics["OI2764"] == "20,000 tCO2e"
    assert any("OI2764" in c.mapped_metrics for c in assessment.impact_claims)


# --- IC gate: data gaps vs findings -----------------------------------------


def _assessment(**company):
    return ImpactVision().assess_company(Company(name="Co", **company))


def test_data_gap_failures_are_insufficient_evidence_not_block():
    sc = evaluate_deal(
        _assessment(sector="energy", description="Solar for off-grid homes."),
        FundThesis(),
        dd_coverage_pct=20.0,
        greenwashing_score=45.0,
    )
    assert sc.overall_status == "fail"  # still not eligible for IC
    assert sc.evidence_status == "insufficient"
    assert sc.display_status == "INSUFFICIENT EVIDENCE"
    assert "BLOCK" not in sc.recommendation


def test_real_findings_still_block():
    sc = evaluate_deal(
        _assessment(sector="energy", description="Solar for off-grid homes."),
        FundThesis(),
        dd_coverage_pct=20.0,
        greenwashing_score=75.0,  # High Risk: a finding, not a gap
    )
    assert sc.evidence_status == "sufficient"
    assert sc.display_status == "FAIL"
    assert sc.recommendation.startswith("BLOCK")


def test_ic_memo_shows_insufficient_evidence():
    assessment = _assessment(sector="energy", description="Solar for off-grid homes.")
    sc = evaluate_deal(assessment, FundThesis(), dd_coverage_pct=20.0, greenwashing_score=45.0)
    html = str(render_ic_memo(assessment, sc, output_format="html"))
    assert "INSUFFICIENT EVIDENCE" in html
    assert "BLOCK IC submission" not in html
