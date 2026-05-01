"""Tool: Approved-data-only natural-language portfolio query engine (v3 Track 9.2)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.models import MetricRecord
from openharness.impact.portfolio_nlq import (
    ApprovedDataPolicy,
    PortfolioNLQEngine,
    parse_intent,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class PortfolioQueryInput(BaseModel):
    action: Literal["answer", "parse_intent"] = "answer"
    question: str
    fund_name: str = "default"
    records: list[dict] = Field(default_factory=list, description="MetricRecord payloads")
    policy: dict = Field(default_factory=dict)
    include_unverified: bool = False
    output_format: Literal["json", "text"] = "json"


class PortfolioQueryTool(BaseTool):
    name = "portfolio_query"
    description = (
        "Constrained natural-language portfolio query engine. Supports 'average', 'total', 'top_n', "
        "'coverage', and 'compare' intents over MetricRecord rows. Default policy answers from "
        "verified records only; every answer cites source evidence."
    )
    input_model = PortfolioQueryInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, PortfolioQueryInput) else PortfolioQueryInput.model_validate(arguments)

        if args.action == "parse_intent":
            return _ok(parse_intent(args.question).model_dump(mode="json"))

        try:
            records = [MetricRecord.model_validate(r) for r in args.records]
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid metric record: {e}", is_error=True)
        policy = ApprovedDataPolicy.model_validate(args.policy) if args.policy else ApprovedDataPolicy()
        engine = PortfolioNLQEngine(fund_name=args.fund_name, records=records, policy=policy)
        answer = engine.answer(args.question, include_unverified=args.include_unverified)
        payload = answer.model_dump(mode="json")
        if args.output_format == "text":
            return ToolResult(output=answer.answer_text, metadata=payload)
        return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
