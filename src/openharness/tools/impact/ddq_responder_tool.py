from __future__ import annotations
import base64
import json
from typing import Literal
from pydantic import BaseModel, Field
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class DDQResponderInput(BaseModel):
    action: Literal["list_questions", "draft", "export", "review_status"] = "list_questions"
    framework: str = ""
    fund_profile: dict = Field(default_factory=dict)
    records: list[dict] = Field(default_factory=list)
    answers: list[dict] = Field(default_factory=list)
    output_format: Literal["xlsx", "docx_outline", "json"] = "json"
    require_verified: bool = True


class DDQResponderTool(BaseTool):
    name = "ddq_responder"
    description = "Draft ILPA DDQ 2.0, PRI 2026, and climate-module answers from approved evidence only; export drafts for human review."
    input_model = DDQResponderInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        del context
        args = (
            arguments
            if isinstance(arguments, DDQResponderInput)
            else DDQResponderInput.model_validate(arguments)
        )
        try:
            from openharness.impact.ddq_responder import (
                draft_answers,
                export_ddq,
                load_ddq_bank,
                review_status,
            )
            from openharness.impact.models import MetricRecord
            from openharness.impact.portfolio_nlq import ApprovedDataPolicy

            questions = [
                q for q in load_ddq_bank() if not args.framework or q.framework == args.framework
            ]
            if args.action == "list_questions":
                result = {"questions": [q.model_dump() for q in questions], "count": len(questions)}
            elif args.action == "draft":
                rows = draft_answers(
                    questions,
                    args.fund_profile,
                    [MetricRecord.model_validate(x) for x in args.records],
                    ApprovedDataPolicy(require_verified=args.require_verified),
                )
                result = {"answers": rows, "count": len(rows)}
            elif args.action == "review_status":
                result = review_status()
            else:
                artifact = export_ddq(args.answers, args.output_format)
                result = {
                    "format": args.output_format,
                    "artifact": base64.b64encode(artifact).decode()
                    if isinstance(artifact, bytes)
                    else artifact,
                }
            return ToolResult(output=json.dumps(result, default=str), metadata=result)
        except Exception as exc:
            return ToolResult(output=f"ddq_responder failed: {exc}", is_error=True)
