"""Tests for v3 LP narrative + Q&A workspace."""

from __future__ import annotations

from datetime import date

import pytest

from openharness.impact.lp_narrative import (
    LPNarrativeRequest,
    LPQuestion,
    LPQuestionWorkspace,
    generate_lp_narrative,
)
from openharness.impact.lp_portal import ImpactDashboardView
from openharness.impact.models import MetricRecord


def _verified_record(metric_id: str = "OI4112", value: str = "150") -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        value=value,
        unit="tCO2e",
        period="FY2025",
        source="audited_workbook",
        owner="Acme",
        quality_score=92,
        verification_status="audited",
        evidence_refs=["evidence://workbook"],
        source_type="audited_statement",
    )


def _dashboard() -> ImpactDashboardView:
    return ImpactDashboardView(
        fund_name="Demo Fund",
        statement_date=date.today(),
        companies=10,
        portfolio_impact_score=3.4,
        coverage_pct=88.0,
        top_sdgs=["SDG 7", "SDG 13"],
        five_dimensions={"what": 3.5, "who": 3.0, "how_much": 3.2, "contribution": 2.8, "risk": 3.1},
    )


def test_generate_lp_narrative_includes_peer_context_and_manifest_hash() -> None:
    request = LPNarrativeRequest(
        fund_name="Demo Fund",
        reporting_period="Q1 2026",
        dashboard=_dashboard(),
        sector="energy",
        peer_dimensions=["what", "who", "how_much"],
        evidence_manifest={"workbook": "abc123", "deck": "def456"},
        risk_callouts=["climate"],
        opportunity_callouts=["scale"],
    )
    report = generate_lp_narrative(request)
    assert report.fund_name == "Demo Fund"
    assert report.headline.startswith("Demo Fund")
    assert report.evidence_manifest_hash
    assert report.peer_context, "peer context should be populated for the sector"
    assert "## Coverage" in report.markdown
    assert "Risks" in report.markdown
    assert "Opportunities" in report.markdown


def test_lp_qa_workspace_rejects_unverified_records() -> None:
    record = MetricRecord(
        metric_id="OI4112",
        value="100",
        unit="tCO2e",
        period="FY2025",
        source="self",
        owner="Acme",
        quality_score=50,
        verification_status="self_reported",
    )
    with pytest.raises(ValueError):
        LPQuestionWorkspace(
            fund_name="Demo Fund",
            reporting_period="Q1 2026",
            approved_records=[record],
        )


def test_lp_qa_workspace_answers_with_citations() -> None:
    workspace = LPQuestionWorkspace(
        fund_name="Demo Fund",
        reporting_period="Q1 2026",
        approved_records=[_verified_record()],
    )
    workspace.ask(LPQuestion(question_id="q1", text="What is FY2025 OI4112?"))
    answer = workspace.answer(
        question_id="q1",
        answered_by="fund_team",
        metric_ids=["OI4112"],
        free_text="FY2025 audited number",
    )
    assert "OI4112" in answer.answer
    assert "evidence://workbook" in answer.citations
    assert answer.answer_hash


def test_lp_qa_workspace_requires_text_or_citation() -> None:
    workspace = LPQuestionWorkspace(
        fund_name="Demo Fund",
        reporting_period="Q1 2026",
        approved_records=[_verified_record()],
    )
    workspace.ask(LPQuestion(question_id="q1", text="Tell me something."))
    with pytest.raises(ValueError):
        workspace.answer(question_id="q1", answered_by="fund_team")


def test_lp_qa_workspace_rejects_free_text_without_verified_citation() -> None:
    workspace = LPQuestionWorkspace(
        fund_name="Demo Fund",
        reporting_period="Q1 2026",
        approved_records=[_verified_record()],
    )
    workspace.ask(LPQuestion(question_id="q1", text="Coverage?"))
    with pytest.raises(ValueError, match="approved metric citation"):
        workspace.answer(
            question_id="q1",
            answered_by="ops",
            free_text="Coverage is 88%.",
        )


def test_lp_qa_workspace_export_keeps_history_hashes() -> None:
    workspace = LPQuestionWorkspace(
        fund_name="Demo Fund",
        reporting_period="Q1 2026",
        approved_records=[_verified_record()],
    )
    workspace.ask(LPQuestion(question_id="q1", text="Coverage?"))
    workspace.answer(
        question_id="q1",
        answered_by="ops",
        metric_ids=["OI4112"],
        free_text="Coverage is tied to the cited audited record.",
    )
    payload = workspace.export()
    assert payload["history_hashes"]
    assert "q1" in payload["answers"]
