"""Smoke tests for v5 public MCP and REST surfaces."""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta

from openharness.api_gateway.router import (
    DecisionWorkflowRequest,
    RegulatoryCalendarRequest,
    decision_workflow_endpoint,
    regulatory_calendar_endpoint,
)


def test_rest_decision_workflow_endpoint_returns_metadata() -> None:
    payload = asyncio.run(decision_workflow_endpoint(
        DecisionWorkflowRequest(
            action="quick_screen",
            company_name="API Solar",
            company_description="Solar energy access for rural households.",
            sector="energy",
            reported_metrics={"OI4112": "100 tCO2e"},
        )
    ))

    assert "metadata" in payload
    assert payload["metadata"]["company_name"] == "API Solar"
    assert payload["metadata"]["classification"] in {
        "aligned_and_credible",
        "misaligned_but_improvable",
        "red_flag",
    }


def test_rest_regulatory_calendar_endpoint_returns_items() -> None:
    payload = asyncio.run(regulatory_calendar_endpoint(
        RegulatoryCalendarRequest(
            action="schedule",
            jurisdiction="EU",
            fiscal_year_end=(date.today() - timedelta(days=40)).isoformat(),
            output_format="json",
        )
    ))

    assert payload["metadata"]["jurisdiction"] == "EU"
    assert payload["metadata"]["items"]
    assert json.loads(payload["result"])["items"]


def test_mcp_decision_workflow_and_regulatory_calendar_execute() -> None:
    from openharness.impact.mcp_server import decision_workflow, regulatory_calendar

    decision = asyncio.run(decision_workflow(
        action="quick_screen",
        company_name="MCP Solar",
        company_description="Solar energy access for rural households.",
        sector="energy",
        reported_metrics={"OI4112": "100 tCO2e"},
    ))
    assert "MCP Solar" in decision
    assert "classification" in decision

    calendar = asyncio.run(regulatory_calendar(
        action="schedule",
        jurisdiction="UK",
        fiscal_year_end=(date.today() - timedelta(days=40)).isoformat(),
        output_format="json",
    ))
    parsed = json.loads(calendar)
    assert parsed["jurisdiction"] == "UK"
    assert parsed["items"]
