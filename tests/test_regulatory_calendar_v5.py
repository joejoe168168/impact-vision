"""Tests for v5 regulatory deadline calendar surface."""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from pathlib import Path

from openharness.impact.regulatory_calendar import build_regulatory_calendar, jurisdiction_options
from openharness.impact.sdk import ImpactVision
from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.regulatory_calendar_tool import (
    RegulatoryCalendarInput,
    RegulatoryCalendarTool,
)


def test_regulatory_calendar_flags_due_within_60_days() -> None:
    fy_end = date.today() - timedelta(days=40)  # annual obligations due in ~50 days
    calendar = build_regulatory_calendar(jurisdiction="EU", fiscal_year_end=fy_end)

    assert calendar.jurisdiction == "EU"
    assert "SFDR" in calendar.frameworks
    assert calendar.due_within_60_days_count > 0
    assert any(item.due_within_60_days for item in calendar.items)


def test_regulatory_calendar_lists_jurisdictions() -> None:
    options = jurisdiction_options()
    jurisdictions = {item["jurisdiction"] for item in options}
    assert {"EU", "UK", "US"} <= jurisdictions


def test_regulatory_calendar_tool_registered_and_json_executes() -> None:
    registry = create_default_tool_registry()
    assert "regulatory_calendar" in {tool.name for tool in registry.list_tools()}

    tool = RegulatoryCalendarTool()
    result = asyncio.run(tool.execute(
        RegulatoryCalendarInput(
            action="schedule",
            jurisdiction="UK",
            fiscal_year_end=(date.today() - timedelta(days=40)).isoformat(),
            output_format="json",
        ),
        ToolExecutionContext(cwd=Path(".")),
    ))

    assert not result.is_error
    payload = json.loads(result.output)
    assert payload["jurisdiction"] == "UK"
    assert payload["items"]
    assert payload["due_within_60_days_count"] >= 0


def test_sdk_exposes_regulatory_calendar() -> None:
    calendar = ImpactVision.build_regulatory_calendar(
        jurisdiction="EU",
        fiscal_year_end=(date.today() - timedelta(days=40)).isoformat(),
    )
    assert calendar.items
    assert calendar.due_within_60_days_count > 0
