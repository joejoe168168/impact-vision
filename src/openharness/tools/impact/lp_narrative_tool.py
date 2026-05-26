"""Tool: LP narrative generator + Q&A workspace (v3 Track 7)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class LPNarrativeInput(BaseModel):
    action: Literal["generate", "qa_ask", "qa_answer", "qa_export"] = Field(
        description="Action: 'generate' (deterministic LP narrative), or Q&A workspace operations."
    )
    fund_name: str = "Demo Fund"
    reporting_period: str = "Q1 2026"
    sector: str = "generic"
    dashboard: dict = Field(default_factory=dict, description="ImpactDashboardView payload")
    peer_dimensions: list[str] = Field(default_factory=list)
    evidence_manifest: dict[str, str] = Field(default_factory=dict)
    risk_callouts: list[str] = Field(default_factory=list)
    opportunity_callouts: list[str] = Field(default_factory=list)
    workspace: dict = Field(default_factory=dict)
    approved_records: list[dict] = Field(default_factory=list, description="MetricRecord payloads (verified only)")
    question: dict = Field(default_factory=dict, description="LPQuestion payload")
    question_id: str = ""
    answered_by: str = "fund_team"
    metric_ids: list[str] = Field(default_factory=list)
    free_text: str = ""


class LPNarrativeTool(BaseTool):
    name = "lp_narrative"
    description = (
        "Generate audit-friendly LP narratives and run an LP Q&A workspace constrained to "
        "approved (verified) metric records. Actions: 'generate', 'qa_ask', 'qa_answer', 'qa_export'."
    )
    input_model = LPNarrativeInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        try:
            args = (
                arguments
                if isinstance(arguments, LPNarrativeInput)
                else LPNarrativeInput.model_validate(arguments)
            )
        except Exception:
            return False
        return args.action in {"generate", "qa_export"}

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        # Local imports keep the package import graph acyclic.
        from openharness.impact.lp_narrative import (
            LPNarrativeRequest,
            LPQuestion,
            generate_lp_narrative,
        )
        from openharness.impact.lp_portal import ImpactDashboardView

        args = arguments if isinstance(arguments, LPNarrativeInput) else LPNarrativeInput.model_validate(arguments)

        if args.action == "generate":
            try:
                dashboard = ImpactDashboardView.model_validate(args.dashboard)
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid dashboard: {e}", is_error=True)
            request = LPNarrativeRequest(
                fund_name=args.fund_name,
                reporting_period=args.reporting_period,
                dashboard=dashboard,
                sector=args.sector,
                peer_dimensions=[d for d in args.peer_dimensions if d in {"what", "who", "how_much", "contribution", "risk"}],  # type: ignore[list-item]
                evidence_manifest=args.evidence_manifest,
                risk_callouts=args.risk_callouts,
                opportunity_callouts=args.opportunity_callouts,
            )
            report = generate_lp_narrative(request)
            return _ok(report.model_dump(mode="json"))

        try:
            workspace = self._load_workspace(args)
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid workspace state: {e}", is_error=True)

        try:
            if args.action == "qa_ask":
                if not args.question:
                    return ToolResult(output="question payload required", is_error=True)
                question = LPQuestion.model_validate(args.question)
                workspace.ask(question)
            elif args.action == "qa_answer":
                workspace.answer(
                    question_id=args.question_id,
                    answered_by=args.answered_by,
                    metric_ids=args.metric_ids,
                    free_text=args.free_text,
                )
            elif args.action == "qa_export":
                pass
            else:
                return ToolResult(output=f"Unknown action: {args.action}", is_error=True)
        except (KeyError, ValueError) as e:
            return ToolResult(output=str(e), is_error=True)

        return _ok(workspace.export())

    def _load_workspace(self, args: LPNarrativeInput):
        from openharness.impact.lp_narrative import LPQuestionWorkspace
        from openharness.impact.models import MetricRecord

        if args.workspace:
            return LPQuestionWorkspace.model_validate(args.workspace)
        records = [MetricRecord.model_validate(r) for r in args.approved_records]
        return LPQuestionWorkspace(
            fund_name=args.fund_name,
            reporting_period=args.reporting_period,
            approved_records=records,
        )


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
