"""Tool: Greenwashing / impact-washing risk detection and per-claim review."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.greenwashing import assess_greenwashing
from openharness.impact.models import Company, ImpactClaim
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sdg_goals, normalize_sector
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class GreenwashingInput(BaseModel):
    action: Literal["detect", "review_claims"] = Field(
        default="detect",
        description=(
            "'detect': company-level 0-100 risk score across 5 sub-dimensions. "
            "'review_claims': per-claim explainable review with specificity, evidence gaps, "
            "and suggested follow-up DD questions (requires 'claims')."
        ),
    )
    company_name: str = Field(description="Name of the company")
    company_description: str = Field(default="", description="Company description / pitch text")
    sector: str = Field(default="")
    geography: str = Field(default="", description="Country or region")
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    claims: list[dict] = Field(
        default_factory=list,
        description="ImpactClaim payloads for action='review_claims' (e.g. from pitch_deck_analyze).",
    )
    prompt_version: str = Field(default="greenwashing-reviewer-v3-2026")
    model_version: str = Field(default="deterministic-rules-v1")
    output_format: Literal["text", "json"] = Field(default="text")


class GreenwashingDetectorTool(BaseTool):
    name = "greenwashing_detect"
    description = (
        "Assess greenwashing / impact-washing risk for a company. "
        "action='detect' analyzes 5 dimensions: claim-metric gap, adverse omissions, language "
        "specificity, reporting selectivity, and verification signals; returns a 0-100 risk score "
        "with classification. action='review_claims' runs the per-claim explainable reviewer "
        "(specificity classification, evidence-gap rationale, selectivity/adverse-omission flags, "
        "suggested follow-up DD questions, AI-governance metadata)."
    )
    input_model = GreenwashingInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, GreenwashingInput) else GreenwashingInput.model_validate(arguments)

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

        if args.action == "review_claims":
            return self._review_claims(args, company, metric_warnings + sdg_warnings)

        result = assess_greenwashing(company)
        payload = result.model_dump()

        all_warnings = metric_warnings + sdg_warnings

        if args.output_format == "json":
            if all_warnings:
                payload["warnings"] = all_warnings
            return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)

        lines = [
            f"GREENWASHING RISK ASSESSMENT: {company.name}",
            "=" * 55,
            f"Overall Risk Score: {result.overall_score}/100",
            f"Classification: {result.classification}",
            "",
            "Sub-scores:",
            f"  Claim-Metric Gap:   {result.claim_metric_gap}/100",
            f"  Adverse Omission:   {result.adverse_omission}/100",
            f"  Language Specificity: {result.specificity}/100",
            f"  Reporting Selectivity: {result.selectivity}/100",
            f"  Verification Signals: {result.verification}/100",
        ]

        if result.flags:
            lines.append("")
            lines.append("Flags:")
            for flag in result.flags:
                lines.append(f"  - {flag}")

        if result.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for i, rec in enumerate(result.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        if all_warnings:
            warning_block = "⚠ Input warnings:\n" + "\n".join(f"  - {w}" for w in all_warnings) + "\n\n"
            lines.insert(0, warning_block)

        return ToolResult(output="\n".join(lines), metadata=payload)

    @staticmethod
    def _review_claims(args: GreenwashingInput, company: Company, warnings: list[str]) -> ToolResult:
        from openharness.impact.greenwashing_reviewer import review_company_claims

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
        if warnings:
            payload["input_warnings"] = warnings

        if args.output_format == "json":
            return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)

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
