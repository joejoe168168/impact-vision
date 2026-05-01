"""Tool: OPIM Principle 8 exit-impact assessment (v3 Track 5.6)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.exit_impact import (
    ExitDurabilityRisk,
    ExitImpactPlan,
    PostExitFollowUp,
    build_exit_plan,
    score_exit_impact,
)
from openharness.impact.models import Company, ImpactClaim
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ExitImpactInput(BaseModel):
    action: Literal["plan", "score"] = "plan"
    company: dict = Field(default_factory=dict, description="Company payload")
    exit_date: str = ""
    durability_risks: list[dict] = Field(default_factory=list)
    post_exit_follow_ups: list[dict] = Field(default_factory=list)
    impact_claims: list[dict] = Field(default_factory=list)
    contribution_summary: str = ""
    counterfactual_summary: str = ""
    notes: str = ""
    plan: dict = Field(default_factory=dict, description="ExitImpactPlan payload (for 'score')")
    output_format: Literal["json", "text"] = "json"


class ExitImpactTool(BaseTool):
    name = "exit_impact"
    description = (
        "OPIM Principle 8 exit-impact assessment. Build a plan with durability risks, "
        "post-exit follow-ups, and residual impact claims, then compute a deterministic "
        "0-100 residual-impact score with band classification and recommendations."
    )
    input_model = ExitImpactInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ExitImpactInput) else ExitImpactInput.model_validate(arguments)

        if args.action == "plan":
            try:
                company = Company.model_validate(args.company)
                risks = [ExitDurabilityRisk.model_validate(r) for r in args.durability_risks]
                follow_ups = [PostExitFollowUp.model_validate(f) for f in args.post_exit_follow_ups]
                claims = [ImpactClaim.model_validate(c) for c in args.impact_claims]
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid input: {e}", is_error=True)
            plan = build_exit_plan(
                company=company,
                exit_date=args.exit_date,
                risks=risks,
                follow_ups=follow_ups,
                claims=claims,
                contribution_summary=args.contribution_summary,
                counterfactual_summary=args.counterfactual_summary,
                notes=args.notes,
            )
            return _ok(plan.model_dump(mode="json"))

        if args.action == "score":
            try:
                plan = ExitImpactPlan.model_validate(args.plan) if args.plan else _build_from_args(args)
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid plan: {e}", is_error=True)
            score = score_exit_impact(plan)
            payload = score.model_dump(mode="json")
            if args.output_format == "text":
                lines = [
                    f"EXIT IMPACT SCORE: {score.company_name}",
                    f"Residual impact: {score.residual_score}/100 ({score.band})",
                    f"  Risk: {score.risk_score}/100",
                    f"  Follow-up: {score.follow_up_score}/100",
                    f"  Evidence: {score.evidence_score}/100",
                ]
                if score.flags:
                    lines.append("Flags:")
                    lines += [f"  - {flag}" for flag in score.flags]
                if score.recommendations:
                    lines.append("Recommendations:")
                    lines += [f"  - {rec}" for rec in score.recommendations]
                return ToolResult(output="\n".join(lines), metadata=payload)
            return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)


def _build_from_args(args: ExitImpactInput) -> ExitImpactPlan:
    company = Company.model_validate(args.company)
    risks = [ExitDurabilityRisk.model_validate(r) for r in args.durability_risks]
    follow_ups = [PostExitFollowUp.model_validate(f) for f in args.post_exit_follow_ups]
    claims = [ImpactClaim.model_validate(c) for c in args.impact_claims]
    return build_exit_plan(
        company=company,
        exit_date=args.exit_date,
        risks=risks,
        follow_ups=follow_ups,
        claims=claims,
        contribution_summary=args.contribution_summary,
        counterfactual_summary=args.counterfactual_summary,
        notes=args.notes,
    )


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
