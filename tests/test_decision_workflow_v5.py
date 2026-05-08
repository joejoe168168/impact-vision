"""Tests for v5 fund-manager decision workflows."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from openharness.impact.database import ensure_catalog_loaded
from openharness.impact.decision_workflow import (
    assess_lp_readiness,
    build_ic_workflow_summary,
    compare_deals,
    quick_screen,
)
from openharness.impact.fund_thesis import FundThesis
from openharness.impact.greenwashing import GreenwashingScore
from openharness.impact.models import Company, ImpactClaim, MetricRecord
from openharness.impact.verdict_engine import build_verdict_card, classify_greenwashing
from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.decision_workflow_tool import DecisionWorkflowInput, DecisionWorkflowTool


def _store():
    return ensure_catalog_loaded()


def _company(name: str = "Solar Co", metrics: dict[str, str] | None = None) -> Company:
    return Company(
        name=name,
        description="Solar energy access serving 5000 rural households with verified clean power.",
        sector="energy",
        impact_themes=["Clean Energy"],
        reported_metrics=metrics or {"OI4112": "100 tCO2e", "PI4060": "5000 people"},
        sdg_claims=[7, 13],
    )


def test_verdict_thresholds_are_pass_caution_fail() -> None:
    assert classify_greenwashing(29.9) == "pass"
    assert classify_greenwashing(30.0) == "caution"
    assert classify_greenwashing(70.0) == "caution"
    assert classify_greenwashing(70.1) == "fail"

    score = GreenwashingScore(
        overall_score=72,
        classification="High Risk",
        claim_metric_gap=80,
        adverse_omission=65,
        specificity=50,
        selectivity=30,
        verification=20,
    )
    card = build_verdict_card(_company(), score)
    assert card.verdict == "fail"
    assert card.top_3_findings[0].startswith("Claim-metric gap")
    assert "Block IC approval" in card.next_steps[-1]


def test_evidence_chain_and_proof_appendix_surface_reported_metric_and_claim_gap() -> None:
    claim = ImpactClaim(
        text="Served 5000 rural households with clean energy.",
        mapped_metrics=["PI4060"],
        mapped_sdg_targets=["7.1"],
        evidence_strength=3,
    )
    unmeasured = ImpactClaim(text="Eliminates energy poverty.", mapped_metrics=["OI9999"])
    record = MetricRecord(
        metric_id="PI4060",
        value="5000",
        unit="people",
        period="FY2025",
        source="meter workbook",
        owner="Solar Co",
        quality_score=85,
        verification_status="third_party_verified",
        evidence_refs=["evidence://meter"],
    )

    summary = build_ic_workflow_summary(
        _company(),
        _store(),
        FundThesis(),
        claims=[claim, unmeasured],
        metric_records=[record],
    )

    assert summary.evidence_chains["who"].metric_links
    assert summary.evidence_chains["who"].metric_links[0].metric_id == "PI4060"
    assert summary.evidence_chains["who"].metric_links[0].confidence == 0.85
    assert summary.proof_appendix.unmeasured_claims
    assert "Appendix A. Proof of Rigor" in summary.memo
    assert "PI4060" in summary.memo


def test_quick_screen_and_lp_readiness_are_decision_outputs() -> None:
    result = quick_screen(
        _company(metrics={}),
        _store(),
        FundThesis(),
        claims=[{"text": "We are green and sustainable.", "mapped_metrics": []}],
    )
    assert result.classification in {"misaligned_but_improvable", "red_flag"}
    assert result.reasons

    summary = build_ic_workflow_summary(_company(metrics={}), _store(), FundThesis())
    readiness = assess_lp_readiness(summary)
    assert readiness.status == "blocked"
    assert readiness.blockers
    assert readiness.badge_label == "Not LP-Ready"


def test_deal_comparison_returns_winner_and_tradeoffs() -> None:
    a = build_ic_workflow_summary(_company("A", {"OI4112": "100", "PI4060": "5000"}), _store(), FundThesis())
    b = build_ic_workflow_summary(_company("B", {}), _store(), FundThesis())
    comparison = compare_deals(a, b)
    assert comparison.winner in {"A", "B"}
    assert comparison.dimension_deltas
    assert comparison.greenwashing_risk["A"] >= 0
    assert comparison.tradeoffs


def test_decision_workflow_tool_is_registered_and_executes() -> None:
    registry = create_default_tool_registry()
    assert "decision_workflow" in {tool.name for tool in registry.list_tools()}

    tool = DecisionWorkflowTool()
    args = DecisionWorkflowInput(
        action="quick_screen",
        company_name="Solar Co",
        company_description="Solar energy access for rural households.",
        sector="energy",
        reported_metrics={"OI4112": "100 tCO2e"},
    )
    result = asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path("."))))
    assert not result.is_error
    payload = json.loads(result.output)
    assert payload["company_name"] == "Solar Co"
    assert payload["classification"] in {
        "aligned_and_credible",
        "misaligned_but_improvable",
        "red_flag",
    }
