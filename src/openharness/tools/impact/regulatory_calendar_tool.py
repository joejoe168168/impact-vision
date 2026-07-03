"""Tool: Regulatory deadline calendar for fund and LP reporting teams."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.engagements.regulatory import Jurisdiction
from openharness.impact.regulatory_calendar import (
    build_regulatory_calendar,
    jurisdiction_options,
    render_regulatory_calendar_text,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class RegulatoryCalendarInput(BaseModel):
    action: Literal["schedule", "list_jurisdictions"] = "schedule"
    jurisdiction: Jurisdiction = Field(default="EU")
    fiscal_year_end: str = Field(
        default="",
        description="Fiscal year end in YYYY-MM-DD format. Defaults to Dec 31 of the current year.",
    )
    engagement_id: str = ""
    owner: str = ""
    output_format: Literal["json", "text"] = "text"


class RegulatoryCalendarTool(BaseTool):
    name = "regulatory_calendar"
    description = (
        "Build a jurisdiction-specific regulatory deadline calendar for SFDR/CSRD/ISSB, "
        "UK SDR, California SB 253/261, and other supported regimes. Flags overdue and due-in-60-day items."
    )
    input_model = RegulatoryCalendarInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, RegulatoryCalendarInput) else RegulatoryCalendarInput.model_validate(arguments)

        if args.action == "list_jurisdictions":
            payload = {"jurisdictions": jurisdiction_options()}
            if args.output_format == "json":
                return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)
            lines = ["Supported regulatory jurisdictions:"]
            for item in payload["jurisdictions"]:
                lines.append(
                    f"- {item['jurisdiction']}: {', '.join(item['frameworks'])} "
                    f"({item['obligations']} obligations)"
                )
            return ToolResult(output="\n".join(lines), metadata=payload)

        # Validate the FY-end early so users get a friendly error instead of a
        # raw ``ValueError`` from deep inside the engine when they pass
        # "31/12/2026" or similar.
        if args.fiscal_year_end:
            try:
                from datetime import date as _date

                _date.fromisoformat(args.fiscal_year_end[:10])
            except ValueError:
                return ToolResult(
                    output=(
                        "fiscal_year_end must be in ISO format (YYYY-MM-DD). "
                        f"Got: {args.fiscal_year_end!r}. Examples: '2026-12-31', '2027-03-31'."
                    ),
                    is_error=True,
                )
        calendar = build_regulatory_calendar(
            jurisdiction=args.jurisdiction,
            fiscal_year_end=args.fiscal_year_end or None,
            engagement_id=args.engagement_id,
            owner=args.owner,
        )
        payload = calendar.model_dump(mode="json")
        if args.output_format == "json":
            return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)
        return ToolResult(output=render_regulatory_calendar_text(calendar), metadata=payload)


__all__ = ["RegulatoryCalendarInput", "RegulatoryCalendarTool"]
