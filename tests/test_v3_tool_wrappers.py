"""Smoke tests for v3 tool wrappers and registry registration."""

from __future__ import annotations

import asyncio
from pathlib import Path

from openharness.impact.assurance import build_assurance_pack
from openharness.impact.models import MetricRecord
from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext


def _run_tool(name: str, payload: dict):
    registry = create_default_tool_registry()
    tool = registry.get(name)
    assert tool is not None, f"{name} should be registered"
    args = tool.input_model.model_validate(payload)
    result = asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path.cwd())))
    assert result.is_error is False, result.output
    assert result.metadata
    return result


def test_v3_tools_are_registered() -> None:
    registry = create_default_tool_registry()
    names = {tool.name for tool in registry.list_tools()}
    assert {
        "emission_factors",
        "stakeholder_voice",
        "evidence_review",
        "verification_workspace",
        "lp_narrative",
        "portfolio_query",
        "exit_impact",
    }.issubset(names)
    # greenwashing_reviewer merged into greenwashing_detect (action='review_claims')
    assert "greenwashing_reviewer" not in names


def test_v3_tool_wrappers_execute_smoke_paths() -> None:
    _run_tool("emission_factors", {"action": "list"})
    _run_tool("stakeholder_voice", {"action": "build_survey", "sector": "energy"})
    _run_tool(
        "evidence_review",
        {
            "action": "build_item",
            "item_id": "claim-1",
            "extracted_text": "Reduced 100 tCO2e",
            "confidence": 0.9,
            "source_refs": ["evidence://deck"],
        },
    )

    pack = build_assurance_pack(
        fund_name="Demo Fund",
        reporting_period="FY2026",
        assertion_text="Management assertion",
        prepared_by="CFO",
        subject_description="Selected metrics",
        metrics=["OI4112"],
    )
    _run_tool(
        "verification_workspace",
        {"action": "open", "pack": pack.model_dump(mode="json")},
    )

    _run_tool(
        "lp_narrative",
        {
            "action": "generate",
            "fund_name": "Demo Fund",
            "reporting_period": "FY2026",
            "dashboard": {
                "fund_name": "Demo Fund",
                "statement_date": "2026-05-01",
                "companies": 2,
                "portfolio_impact_score": 3.2,
                "coverage_pct": 80,
                "top_sdgs": ["SDG 7"],
                "five_dimensions": {"what": 3.2},
            },
        },
    )

    _run_tool(
        "greenwashing_detect",
        {
            "action": "review_claims",
            "company_name": "DemoCo",
            "sector": "energy",
            "claims": [
                {
                    "text": "Reduced 100 tCO2e in FY2025",
                    "mapped_metrics": ["OI4112"],
                    "evidence_strength": 3,
                }
            ],
        },
    )

    record = MetricRecord(
        metric_id="OI4112",
        value="100",
        unit="tCO2e",
        period="FY2025",
        source="audited workbook",
        owner="DemoCo",
        quality_score=90,
        verification_status="audited",
        evidence_refs=["evidence://workbook"],
    )
    _run_tool(
        "portfolio_query",
        {
            "action": "answer",
            "question": "Average OI4112 in FY2025",
            "records": [record.model_dump(mode="json")],
        },
    )

    _run_tool(
        "exit_impact",
        {
            "action": "plan",
            "company": {"name": "DemoCo", "sector": "energy"},
            "exit_date": "2026-12-31",
        },
    )
