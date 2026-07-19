from __future__ import annotations
import json
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field
from openharness.impact.audit_trail import AuditTrail
from openharness.impact.evidence_graph import EvidenceGraph
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ContributionInput(BaseModel):
    action: Literal["register_claim", "log_activity", "scorecard", "attribution_check"]
    claim: dict = Field(default_factory=dict)
    activity: dict = Field(default_factory=dict)
    claims: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    records: list[dict] = Field(default_factory=list)
    company: str = ""
    investor_claims: list[dict] = Field(default_factory=list)
    as_of: str = ""


class ContributionTrackerTool(BaseTool):
    name = "contribution_tracker"
    description = "Pre-register investor-contribution claims, log evidence, grade monitoring practice, and detect attribution inflation."
    input_model = ContributionInput

    def __init__(self):
        self.graph = EvidenceGraph()
        self.trail = AuditTrail()

    def is_read_only(self, arguments: BaseModel) -> bool:
        return getattr(arguments, "action", "") in {"scorecard", "attribution_check"}

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        del context
        args = (
            arguments
            if isinstance(arguments, ContributionInput)
            else ContributionInput.model_validate(arguments)
        )
        try:
            from openharness.impact.contribution import (
                ContributionClaim,
                ContributionEvidence,
                attribution_sanity_check,
                contribution_scorecard,
                log_contribution_activity,
                register_contribution_claim,
            )
            from openharness.impact.models import MetricRecord

            if args.action == "register_claim":
                result = register_contribution_claim(
                    ContributionClaim.model_validate(args.claim), self.graph, self.trail
                )
            elif args.action == "log_activity":
                result = log_contribution_activity(
                    str(args.claim.get("claim_id", args.claim.get("id", ""))),
                    ContributionEvidence.model_validate(args.activity),
                    self.graph,
                    self.trail,
                )
            elif args.action == "attribution_check":
                result = attribution_sanity_check(args.company, args.investor_claims)
            else:
                result = contribution_scorecard(
                    [ContributionClaim.model_validate(x) for x in args.claims],
                    [ContributionEvidence.model_validate(x) for x in args.evidence],
                    [MetricRecord.model_validate(x) for x in args.records],
                    as_of=date.fromisoformat(args.as_of) if args.as_of else None,
                )
            return ToolResult(output=json.dumps(result, default=str), metadata=result)
        except Exception as exc:
            return ToolResult(output=f"contribution_tracker failed: {exc}", is_error=True)
