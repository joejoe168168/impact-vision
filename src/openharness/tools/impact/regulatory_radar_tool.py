from __future__ import annotations
import json
from typing import Literal
from pydantic import BaseModel, Field
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class RadarInput(BaseModel):
    action: Literal["check", "list_findings", "confirm", "dismiss", "impact"] = "list_findings"
    tracked: list[dict] = Field(default_factory=list)
    contents: dict[str, str] = Field(default_factory=dict)
    finding_index: int = 0
    companies: list[dict] = Field(default_factory=list)


class RegulatoryRadarTool(BaseTool):
    name = "regulatory_radar"
    description = "Review-gated radar for official sustainability-standard changes and portfolio applicability."
    input_model = RadarInput

    def __init__(self):
        self.findings = []

    def is_read_only(self, arguments: BaseModel) -> bool:
        return getattr(arguments, "action", "") in {"list_findings", "impact", "check"}

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        del context
        args = (
            arguments if isinstance(arguments, RadarInput) else RadarInput.model_validate(arguments)
        )
        try:
            from openharness.impact.regulatory_radar import (
                TrackedStandard,
                check_tracked_standards,
                decide_finding,
                portfolio_impact,
            )
            from openharness.impact.models import Company

            if args.action == "check":
                self.findings.extend(
                    check_tracked_standards(
                        [TrackedStandard.model_validate(x) for x in args.tracked],
                        lambda url: args.contents[url],
                    )
                )
                result = [x.model_dump() for x in self.findings]
            elif args.action in {"confirm", "dismiss"}:
                decide_finding(
                    self.findings[args.finding_index],
                    "confirmed" if args.action == "confirm" else "dismissed",
                )
                result = self.findings[args.finding_index].model_dump()
            elif args.action == "impact":
                result = {
                    "affected_companies": portfolio_impact(
                        self.findings[args.finding_index],
                        [Company.model_validate(x) for x in args.companies],
                    )
                }
            else:
                result = [x.model_dump() for x in self.findings]
            return ToolResult(
                output=json.dumps(result, default=str),
                metadata={"findings": result} if isinstance(result, list) else result,
            )
        except Exception as exc:
            return ToolResult(output=f"regulatory_radar failed: {exc}", is_error=True)
