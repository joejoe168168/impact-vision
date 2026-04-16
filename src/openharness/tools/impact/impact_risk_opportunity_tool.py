"""Tool: Structured impact risk and opportunity assessment."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.models import Company
from openharness.impact.risk_opportunity import assess_impact_risk_opportunity
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sdg_goals
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ImpactRiskOpportunityInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    company_description: str = Field(default="", description="Brief company description")
    sector: str = Field(default="")
    geography: str = Field(default="", description="Country or region")
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    output_format: Literal["text", "json"] = Field(default="text")


class ImpactRiskOpportunityTool(BaseTool):
    name = "impact_risk_opportunity"
    description = (
        "Assess impact risks and opportunities for a company using keyword-based heuristics. "
        "Returns categorized risks with severity/mitigation and opportunities with time horizons."
    )
    input_model = ImpactRiskOpportunityInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ImpactRiskOpportunityInput) else ImpactRiskOpportunityInput.model_validate(arguments)

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

        result = assess_impact_risk_opportunity(company)

        if args.output_format == "json":
            return ToolResult(output=json.dumps(result, indent=2), metadata=result)

        lines = [
            f"IMPACT RISK & OPPORTUNITY: {company.name}",
            "=" * 50,
            f"Risk Score: {result['risk_score']}/100",
            f"Opportunity Score: {result['opportunity_score']}/100",
            "",
        ]

        if result["priority_risks"]:
            lines.append("Priority Risks:")
            for r in result["priority_risks"]:
                lines.append(f"  [{r.get('severity', 'medium').upper()}] {r['risk']}")
                lines.append(f"    Mitigation: {r.get('mitigation', 'N/A')}")
            lines.append("")

        if result["priority_opportunities"]:
            lines.append("Key Opportunities:")
            for o in result["priority_opportunities"]:
                lines.append(f"  [{o.get('time_horizon', 'mid_term')}] {o['opportunity']}")
            lines.append("")

        return ToolResult(output="\n".join(lines), metadata=result)
