"""Tool: Build Lean Data surveys, manage consent, score quality, and link feedback to claims (v3)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from impact_vision.impact.evidence_graph import EvidenceGraph
from impact_vision.impact.models import BeneficiaryFeedback, ImpactClaim
from impact_vision.impact.stakeholder_voice import (
    ConsentRecord,
    build_lean_data_survey,
    link_feedback_to_claims,
    revoke_consent,
    score_feedback_quality,
)
from impact_vision.tools.impact.common import list_state, load_state, save_state
from impact_vision.tools.base import BaseTool, ToolExecutionContext, ToolResult


class StakeholderVoiceInput(BaseModel):
    action: Literal[
        "build_survey",
        "score_quality",
        "link_feedback",
        "consent_grant",
        "consent_revoke",
        "consent_list",
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
    tenant_id: str = "default"
    output_format: Literal["json", "text"] = "json"


class StakeholderVoiceTool(BaseTool):
    name = "stakeholder_voice"
    description = (
        "Lean Data 60-Decibels-style survey builder, GDPR/PDPA consent capture, "
        "beneficiary feedback quality scoring, and feedback-to-claim evidence linking. "
        "Actions: 'build_survey', 'score_quality', 'link_feedback', 'consent_grant', 'consent_revoke', "
        "'consent_list'. Consents are kept in a register (granted and revoked records)."
    )
    input_model = StakeholderVoiceInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return getattr(arguments, "action", "") not in {"consent_grant", "consent_revoke"}

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
            save_state(args.tenant_id, "consent", record.consent_id, record.model_dump(mode="json"))
            return _ok(record.model_dump(mode="json"))

        if args.action == "consent_revoke":
            payload = args.consent or (load_state(args.tenant_id, "consent", args.consent_id)
                                       if args.consent_id else None)
            if not payload:
                return ToolResult(output="consent payload or a registered consent_id is required", is_error=True)
            try:
                record = ConsentRecord.model_validate(payload)
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid consent payload: {e}", is_error=True)
            revoked = revoke_consent(record)
            save_state(args.tenant_id, "consent", revoked.consent_id, revoked.model_dump(mode="json"))
            return _ok(revoked.model_dump(mode="json"))

        if args.action == "consent_list":
            records = [ConsentRecord.model_validate(r) for r in list_state(args.tenant_id, "consent")]
            return _ok({"consents": [r.model_dump(mode="json") for r in records],
                        "active": sum(1 for r in records if r.is_active),
                        "revoked": sum(1 for r in records if not r.is_active)})

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
