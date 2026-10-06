"""W0.5: thin input yields 'insufficient evidence', never a false red flag or 0%."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from openharness.cli import app
from openharness.impact.dd_checklist import analyze_document_coverage
from openharness.impact.decision_workflow import assess_evidence_sufficiency
from openharness.impact.models import Company
from openharness.impact.sdk import ImpactVision

SOLAR = (
    "SunPath Energy sells pay-as-you-go solar home systems to off-grid households in rural "
    "Kenya. We have connected 42,000 households, replacing kerosene lamps and reducing "
    "household energy spend by 30%. Our systems avoided an estimated 20,000 tCO2e in 2024. "
    "We track customer repayment and satisfaction monthly through call-centre surveys."
)


def test_short_description_is_insufficient_not_red_flag():
    company = Company(name="SunPath", sector="energy", description="Solar for off-grid homes.")
    assert not assess_evidence_sufficiency(company).sufficient
    result = ImpactVision().quick_screen(company)
    assert result.classification == "insufficient_evidence"
    assert result.required_followups


def test_estimated_only_threshold_failures_are_not_red_flags():
    iv = ImpactVision()
    a = iv.assess_company_text("SunPath", text=SOLAR, sector="energy")
    result = iv.quick_screen(a.company, claims=[c.model_dump() for c in a.impact_claims])
    assert result.classification != "red_flag"


def test_exclusion_failure_is_still_a_red_flag():
    company = Company(name="X", sector="energy", description="Short.")
    assert ImpactVision().quick_screen(company, exclusion_pass=False).classification == "red_flag"


def test_dd_matching_handles_inflections_and_single_hits():
    result = analyze_document_coverage(SOLAR, sector="energy")
    assert result.coverage_pct > 10
    # "beneficiar" stem now matches "beneficiaries"
    hit = analyze_document_coverage(
        "Our beneficiaries are smallholder farmers living in poverty in rural areas.",
        sector="agriculture",
    )
    assert any(m.question.id == "WO01" for m in hit.addressed)


def test_cli_dd_analyze_sector_json_and_short_text_warning():
    runner = CliRunner()
    out = runner.invoke(app, ["dd", "analyze", SOLAR, "--sector", "energy", "--json"])
    assert out.exit_code == 0, out.output
    data = json.loads(out.output)
    assert data["total_questions"] < 122
    short = runner.invoke(app, ["dd", "analyze", "We sell solar."])
    assert "Insufficient text" in short.output
