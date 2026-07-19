from __future__ import annotations
import json
from typing import Literal
from pydantic import BaseModel, Field
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class CarbonCreditInput(BaseModel):
    action: Literal["screen", "list_programs", "screen_biodiversity"] = "screen"
    credits: list[dict] = Field(default_factory=list)
    claim_text: str = ""
    answers: dict[str, int] = Field(default_factory=dict)


class CarbonCreditIntegrityTool(BaseTool):
    name = "carbon_credit_integrity"
    description = "Screen carbon credits against ICVCM/VCMI integrity criteria or biodiversity credits against 21 high-level principles."
    input_model = CarbonCreditInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        del context
        args = (
            arguments
            if isinstance(arguments, CarbonCreditInput)
            else CarbonCreditInput.model_validate(arguments)
        )
        try:
            if args.action == "list_programs":
                from openharness.impact.carbon_credit_integrity import (
                    CCP_ELIGIBLE_PROGRAMS as result,
                )
            elif args.action == "screen_biodiversity":
                from openharness.impact.ecosystem_services import screen_biodiversity_credit

                result = screen_biodiversity_credit(args.answers)
            else:
                from openharness.impact.carbon_credit_integrity import CarbonCredit, screen_credits

                result = screen_credits(
                    [CarbonCredit.model_validate(x) for x in args.credits], args.claim_text or None
                ).model_dump(mode="json")
            return ToolResult(
                output=json.dumps(result, default=str),
                metadata=result if isinstance(result, dict) else {},
            )
        except Exception as exc:
            return ToolResult(output=f"carbon_credit_integrity failed: {exc}", is_error=True)
