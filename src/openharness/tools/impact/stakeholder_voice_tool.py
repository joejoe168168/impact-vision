"""Tool: Build Lean Data surveys, manage consent, score quality, and link feedback to claims (v3)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.evidence_graph import EvidenceGraph
from openharness.impact.models import BeneficiaryFeedback, ImpactClaim
from openharness.impact.stakeholder_voice import (
    ConsentRecord,
    build_lean_data_survey,
    link_feedback_to_claims,
    revoke_consent,
    score_feedback_quality,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class StakeholderVoiceInput(BaseModel):
    action: Literal[
        "build_survey",
        "score_quality",
        "link_feedback",
        "consent_grant",
        "consent_revoke",
    ] = Field(description="Action to perform.")
    sector: str = Field(default="generic")
    languages: list[str] = Field(default_factory=lambda: ["en"])
    target_minutes: int = Field(default=15, ge=1, le=60)
    completed_responses: int = 0
    invited_responses: int = 0
    response_depth: dict[str, int] = Field(default_factory=dict)
    response_durations_seconds: list[float] = Field(default_factory=list)
    demographic_segments_present: int = 0
    demographic_segments_target: int = 4
    active_consents: int | None = None
    feedback: dict = Field(default_factory=dict, description="BeneficiaryFeedback payload")
    claims: list[dict] = Field(default_factory=list, description="ImpactClaim payloads")
    consent: dict = Field(default_factory=dict, description="ConsentRecord payload")
    consent_id: str = ""
    output_format: Literal["json", "text"] = "json"


class StakeholderVoiceTool(BaseTool):
    name = "stakeholder_voice"
    description = (
        "Lean Data 60-Decibels-style survey builder, GDPR/PDPA consent capture, "
        "beneficiary feedback quality scoring, and feedback-to-claim evidence linking. "
        "Actions: 'build_survey', 'score_quality', 'link_feedback', 'consent_grant', 'consent_revoke'."
    )
    input_model = StakeholderVoiceInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, StakeholderVoiceInput) else StakeholderVoiceInput.model_validate(arguments)

        if args.action == "build_survey":
            template = build_lean_data_survey(
                sector=args.sector,
                languages=args.languages,
                target_minutes=args.target_minutes,
            )
            return _ok(template.model_dump(mode="json"))

        if args.action == "score_quality":
            quality = score_feedback_quality(
                completed_responses=args.completed_responses,
                invited_responses=args.invited_responses,
                response_depth=args.response_depth or None,
                response_durations_seconds=args.response_durations_seconds or None,
                demographic_segments_present=args.demographic_segments_present,
                demographic_segments_target=args.demographic_segments_target,
                active_consents=args.active_consents,
            )
            return _ok(quality.model_dump(mode="json"))

        if args.action == "link_feedback":
            try:
                feedback = BeneficiaryFeedback.model_validate(args.feedback)
                claims = [ImpactClaim.model_validate(c) for c in args.claims]
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid input: {e}", is_error=True)
            graph: EvidenceGraph = link_feedback_to_claims(feedback, claims)
            return _ok(graph.model_dump(mode="json"))

        if args.action == "consent_grant":
            try:
                record = ConsentRecord.model_validate(args.consent)
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid consent payload: {e}", is_error=True)
            return _ok(record.model_dump(mode="json"))

        if args.action == "consent_revoke":
            if not args.consent:
                return ToolResult(output="consent payload required", is_error=True)
            try:
                record = ConsentRecord.model_validate(args.consent)
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid consent payload: {e}", is_error=True)
            revoked = revoke_consent(record)
            return _ok(revoked.model_dump(mode="json"))

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
