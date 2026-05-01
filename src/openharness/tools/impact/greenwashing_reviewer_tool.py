"""Tool: Per-claim greenwashing reviewer with explainable output (v3 Track 9.3)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.greenwashing_reviewer import review_company_claims
from openharness.impact.models import Company, ImpactClaim
from openharness.tools.impact.common import (
    infer_themes,
    normalize_metric_map,
    normalize_sdg_goals,
    normalize_sector,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class GreenwashingReviewerInput(BaseModel):
    company_name: str
    company_description: str = ""
    sector: str = ""
    geography: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    claims: list[dict] = Field(default_factory=list, description="ImpactClaim payloads")
    prompt_version: str = "greenwashing-reviewer-v3-2026"
    model_version: str = "deterministic-rules-v1"
    output_format: Literal["json", "text"] = "json"


class GreenwashingReviewerTool(BaseTool):
    name = "greenwashing_reviewer"
    description = (
        "Per-claim greenwashing reviewer with specificity classification, evidence-gap rationale, "
        "selectivity / adverse-omission flags, suggested follow-up DD questions, and AI-governance "
        "metadata. Wraps the underlying greenwashing engine."
    )
    input_model = GreenwashingReviewerInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, GreenwashingReviewerInput) else GreenwashingReviewerInput.model_validate(arguments)

        metrics, metric_warnings = normalize_metric_map(args.reported_metrics)
        sdg_claims, sdg_warnings = normalize_sdg_goals(args.sdg_claims)
        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=normalize_sector(args.sector),
            geography=args.geography,
            impact_themes=infer_themes(f"{args.company_description} {args.sector}", args.impact_themes),
            reported_metrics=metrics,
            sdg_claims=sdg_claims,
        )
        try:
            claim_objects = [ImpactClaim.model_validate(c) for c in args.claims]
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid claim payloads: {e}", is_error=True)

        result = review_company_claims(
            company,
            claim_objects,
            prompt_version=args.prompt_version,
            model_version=args.model_version,
        )
        payload = result.model_dump(mode="json")
        warnings = metric_warnings + sdg_warnings
        if warnings:
            payload["input_warnings"] = warnings

        if args.output_format == "text":
            lines = [
                f"GREENWASHING REVIEWER: {company.name}",
                "=" * 55,
                f"Overall risk score: {result.overall.overall_score}/100 ({result.overall.classification})",
                f"Selectivity flag: {result.governance['selectivity_threshold_hit']}",
                f"Adverse omission flag: {result.governance['adverse_omission_threshold_hit']}",
                "",
                f"Per-claim review ({len(result.items)} claims):",
            ]
            for item in result.items:
                lines.append(
                    f"  - [{item.severity.upper()}] specificity={item.specificity}, "
                    f"evidence_gap={item.evidence_gap}, NESTA={item.nesta_evidence_strength}"
                )
                lines.append(f"    Claim: {item.claim_text[:140]}")
                if item.suggested_followup:
                    lines.append(f"    Followup: {item.suggested_followup}")
            return ToolResult(output="\n".join(lines), metadata=payload)

        return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
