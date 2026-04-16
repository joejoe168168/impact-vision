"""Tool: Assess impact risks/opportunities for diligence and reporting."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.models import Company
from openharness.impact.risk_opportunity import assess_impact_risk_opportunity
from openharness.tools.impact.common import normalize_metric_map, normalize_sdg_goals, normalize_str_list
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ImpactRiskOpportunityInput(BaseModel):
    company_name: str = Field(description="Company name")
    company_description: str = Field(default="", description="Company description")
    sector: str = Field(default="", description="Company sector")
    impact_themes: list[str] = Field(default_factory=list, description="Impact themes")
    reported_metrics: dict[str, str] = Field(default_factory=dict, description="Reported IRIS+ metrics")
    sdg_claims: list[int] = Field(default_factory=list, description="Claimed SDG goals")
    output_format: Literal["text", "json"] = Field(default="text")


class ImpactRiskOpportunityTool(BaseTool):
    name = "impact_risk_opportunity"
    description = (
        "Assess likely impact risks and opportunities with severity/category signals and "
        "priority actions for due diligence and reporting narratives."
    )
    input_model = ImpactRiskOpportunityInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ImpactRiskOpportunityInput) else ImpactRiskOpportunityInput.model_validate(arguments)
        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=args.sector,
            impact_themes=normalize_str_list(args.impact_themes),
            reported_metrics=normalize_metric_map(args.reported_metrics),
            sdg_claims=normalize_sdg_goals(args.sdg_claims),
        )

        result = assess_impact_risk_opportunity(company)
        if args.output_format == "json":
            return ToolResult(output=json.dumps(result, indent=2), metadata=result)

        lines = [
            f"IMPACT RISK & OPPORTUNITY: {company.name}",
            "=" * 60,
            f"Risk score: {result['risk_score']}/100",
            f"Opportunity score: {result['opportunity_score']}/100",
            "",
            "Priority Risks:",
        ]
        if result["priority_risks"]:
            for risk in result["priority_risks"]:
                lines.append(f"  - [{risk.get('severity', 'medium').upper()}] {risk.get('risk')}")
                if risk.get("mitigation"):
                    lines.append(f"    Mitigation: {risk['mitigation']}")
        else:
            lines.append("  - No major impact risks detected from available data.")

        lines.append("")
        lines.append("Priority Opportunities:")
        if result["priority_opportunities"]:
            for opp in result["priority_opportunities"]:
                lines.append(f"  - {opp.get('opportunity')} ({opp.get('category')})")
        else:
            lines.append("  - No concrete opportunities identified from available data.")

        return ToolResult(output="\n".join(lines), metadata=result)
