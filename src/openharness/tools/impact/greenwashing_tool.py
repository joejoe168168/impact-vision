"""Tool: Greenwashing / impact-washing risk detection."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.greenwashing import assess_greenwashing
from openharness.impact.models import Company
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sdg_goals
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class GreenwashingInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    company_description: str = Field(default="", description="Company description / pitch text")
    sector: str = Field(default="")
    geography: str = Field(default="", description="Country or region")
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    output_format: Literal["text", "json"] = Field(default="text")


class GreenwashingDetectorTool(BaseTool):
    name = "greenwashing_detect"
    description = (
        "Assess greenwashing / impact-washing risk for a company. "
        "Analyzes 5 dimensions: claim-metric gap, adverse omissions, language specificity, "
        "reporting selectivity, and verification signals. Returns a 0-100 risk score with classification."
    )
    input_model = GreenwashingInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, GreenwashingInput) else GreenwashingInput.model_validate(arguments)

        metrics, _ = normalize_metric_map(args.reported_metrics)
        sdg_claims, _ = normalize_sdg_goals(args.sdg_claims)

        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=args.sector,
            geography=args.geography,
            impact_themes=infer_themes(f"{args.company_description} {args.sector}", args.impact_themes),
            reported_metrics=metrics,
            sdg_claims=sdg_claims,
        )

        result = assess_greenwashing(company)
        payload = result.model_dump()

        if args.output_format == "json":
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

        return ToolResult(output="\n".join(lines), metadata=payload)
