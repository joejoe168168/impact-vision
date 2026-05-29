"""Tool: AI governance artifact (model card / lineage / oversight) — v5 Track E2."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.ai_governance import (
    build_ai_governance_artifact,
    classify_ai_act_risk,
    default_model_card,
)
from openharness.impact.engagements.copilot import CopilotOutput
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class AIGovernanceToolInput(BaseModel):
    action: Literal["model_card", "classify_ai_act", "build_artifact"] = "build_artifact"
    subject: str = ""
    model: str = ""
    model_version: str = ""
    provider: str = ""
    purpose: str = ""
    copilot_outputs: list[dict] = Field(
        default_factory=list,
        description="CopilotOutput records (output_id, kind, prompt, response, model, "
        "source_refs, confidence, reviewer, decision, ...) to bundle into the artifact",
    )
    discloses_ai_use: bool = True
    # for classify_ai_act
    human_in_the_loop: bool = True
    keeps_records: bool = True
    output_format: Literal["json", "text"] = "json"


class AIGovernanceTool(BaseTool):
    name = "ai_governance"
    description = (
        "AI governance artifact for the fund's own AI extraction (EU AI Act-aware). "
        "Produces a model card, a per-artefact data-lineage record, and a "
        "human-oversight log assembled from the copilot review queue, plus an EU AI "
        "Act risk classification (unacceptable / high / limited / minimal) with the "
        "transparency, human-oversight and record-keeping obligation checklist. "
        "Impact Vision's claim-extraction copilot is a limited-risk transparency use; "
        "this tool makes that determination explicit and auditable. Actions: "
        "'model_card', 'classify_ai_act', 'build_artifact'."
    )
    input_model = AIGovernanceToolInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, AIGovernanceToolInput)
            else AIGovernanceToolInput.model_validate(arguments)
        )

        if args.action == "model_card":
            card = default_model_card(args.model, args.model_version, args.provider)
            if args.purpose:
                card.purpose = args.purpose
            payload = card.model_dump(mode="json")
            return _ok(payload)

        if args.action == "classify_ai_act":
            purpose = args.purpose or default_model_card().purpose
            assessment = classify_ai_act_risk(
                purpose,
                human_in_the_loop=args.human_in_the_loop,
                discloses_ai_use=args.discloses_ai_use,
                keeps_records=args.keeps_records,
            )
            payload = assessment.model_dump(mode="json")
            if args.output_format == "text":
                return ToolResult(output=_ai_act_text(assessment), metadata=payload)
            return _ok(payload)

        # build_artifact
        try:
            outputs = [CopilotOutput.model_validate(o) for o in args.copilot_outputs]
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid copilot_outputs: {e}", is_error=True)

        card = None
        if args.model or args.purpose or args.provider:
            card = default_model_card(args.model, args.model_version, args.provider)
            if args.purpose:
                card.purpose = args.purpose

        artifact = build_ai_governance_artifact(
            subject=args.subject,
            outputs=outputs,
            model_card=card,
            discloses_ai_use=args.discloses_ai_use,
        )
        payload = artifact.model_dump(mode="json")
        if args.output_format == "text":
            return ToolResult(output=_artifact_text(artifact), metadata=payload)
        return _ok(payload)


def _ai_act_text(a) -> str:  # noqa: ANN001
    lines = [
        "EU AI ACT CLASSIFICATION",
        "=" * 50,
        f"Risk tier: {a.risk_tier.upper()}",
        f"Rationale: {a.rationale}",
        "",
        f"Transparency met:    {a.transparency_obligation_met}",
        f"Human oversight met: {a.human_oversight_obligation_met}",
        f"Record-keeping met:  {a.record_keeping_obligation_met}",
    ]
    if a.gaps:
        lines.append("")
        lines.append("Gaps:")
        for g in a.gaps:
            lines.append(f"  - {g}")
    return "\n".join(lines)


def _artifact_text(a) -> str:  # noqa: ANN001
    lines = [
        f"AI GOVERNANCE ARTIFACT — {a.subject or a.model_card.name}",
        "=" * 50,
        f"Model: {a.model_card.name} {a.model_card.version}".strip(),
        f"EU AI Act tier: {a.ai_act.risk_tier.upper()}",
        f"Artefacts: {a.total_artifacts}  |  reviewed: {a.reviewed_artifacts} "
        f"({a.oversight_coverage_pct}% oversight coverage)",
        "",
        "Purpose: " + a.model_card.purpose,
    ]
    if a.ai_act.gaps:
        lines.append("")
        lines.append("AI Act gaps:")
        for g in a.ai_act.gaps:
            lines.append(f"  - {g}")
    return "\n".join(lines)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)


__all__ = ["AIGovernanceToolInput", "AIGovernanceTool"]
