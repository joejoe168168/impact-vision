from __future__ import annotations
import json
from typing import Literal
from pydantic import BaseModel, Field
from openharness.impact.audit_trail import AuditTrail
from openharness.impact.evidence_graph import EvidenceGraph
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class SurveyDeliveryInput(BaseModel):
    action: Literal["render", "dispatch", "ingest", "status", "response_rates"]
    survey: dict = Field(default_factory=dict)
    channel_id: str = "web_link"
    language: str = "en"
    respondent_ref: str = ""
    consent: dict = Field(default_factory=dict)
    dispatch: dict = Field(default_factory=dict)
    raw_response: dict = Field(default_factory=dict)


class SurveyDeliveryTool(BaseTool):
    name = "survey_delivery"
    description = "Render and track consent-gated WhatsApp, SMS, voice, or web survey delivery and normalize responses."
    input_model = SurveyDeliveryInput

    def __init__(self):
        self.dispatches = []
        self.graph = EvidenceGraph()
        self.trail = AuditTrail()

    def is_read_only(self, arguments: BaseModel) -> bool:
        return getattr(arguments, "action", "") in {"render", "status", "response_rates"}

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        del context
        args = (
            arguments
            if isinstance(arguments, SurveyDeliveryInput)
            else SurveyDeliveryInput.model_validate(arguments)
        )
        try:
            from openharness.impact.stakeholder_voice import ConsentRecord
            from openharness.impact.survey_delivery import (
                SurveyDispatch,
                build_webhook_payload_parser,
                create_dispatch,
                ingest_response,
                render_survey,
                response_rates,
            )

            if args.action == "render":
                result = {"messages": render_survey(args.survey, args.channel_id, args.language)}
            elif args.action == "dispatch":
                dispatch = create_dispatch(
                    str(args.survey.get("survey_id", args.survey.get("id", "survey"))),
                    args.channel_id,
                    args.respondent_ref,
                    ConsentRecord.model_validate(args.consent),
                )
                self.dispatches.append(dispatch)
                result = dispatch.model_dump()
            elif args.action == "ingest":
                dispatch = SurveyDispatch.model_validate(args.dispatch)
                consent = ConsentRecord.model_validate(args.consent)
                parsed = build_webhook_payload_parser(dispatch.channel_id)(args.raw_response)
                result = ingest_response(dispatch, parsed, self.graph, self.trail, consent)
            elif args.action == "response_rates":
                result = response_rates(self.dispatches)
            else:
                result = {"dispatches": [d.model_dump() for d in self.dispatches]}
            return ToolResult(output=json.dumps(result, default=str), metadata=result)
        except Exception as exc:
            return ToolResult(output=f"survey_delivery failed: {exc}", is_error=True)
