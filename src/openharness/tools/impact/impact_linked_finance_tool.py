from __future__ import annotations
import json
from typing import Any, Literal
from pydantic import BaseModel, Field
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ImpactLinkedFinanceInput(BaseModel):
    action: Literal[
        "score_kpi",
        "track_pbr",
        "simulate_carry",
        "simulate_safi",
        "design_loan",
        "design_soc",
        "design_carry",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)
    records: list[dict] = Field(default_factory=list)
    scenarios: list[dict] = Field(default_factory=list)


class ImpactLinkedFinanceTool(BaseTool):
    name = "impact_linked_finance"
    description = "Design impact-linked finance instruments, score KPI credibility, verify PbR milestones, and simulate carry or SAFI economics."
    input_model = ImpactLinkedFinanceInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        del context
        args = (
            arguments
            if isinstance(arguments, ImpactLinkedFinanceInput)
            else ImpactLinkedFinanceInput.model_validate(arguments)
        )
        try:
            from openharness.impact import blended_finance as bf
            from openharness.impact.models import MetricRecord

            records = [MetricRecord.model_validate(x) for x in args.records]
            if args.action == "score_kpi":
                result = bf.score_kpi_credibility(
                    args.payload.get("kpi", args.payload),
                    args.payload.get("toc_outcomes", []),
                    args.payload.get("benchmark"),
                ).model_dump()
            elif args.action == "track_pbr":
                result = bf.track_payment_by_results(
                    args.payload.get("deal_terms", {}),
                    [bf.PbRMilestone.model_validate(x) for x in args.payload.get("milestones", [])],
                    records,
                )
            elif args.action == "simulate_carry":
                result = bf.simulate_carry(
                    bf.CarryStructure.model_validate(args.payload), args.scenarios
                )
            elif args.action == "simulate_safi":
                result = bf.simulate_safi(bf.SAFITerms.model_validate(args.payload), records)
            elif args.action == "design_loan":
                result = bf.design_il_loan(**args.payload).model_dump()
            elif args.action == "design_soc":
                result = bf.design_soc(**args.payload).model_dump()
            else:
                result = bf.design_impact_carry(**args.payload).model_dump()
            return ToolResult(output=json.dumps(result, default=str), metadata=result)
        except Exception as exc:
            return ToolResult(output=f"impact_linked_finance failed: {exc}", is_error=True)
