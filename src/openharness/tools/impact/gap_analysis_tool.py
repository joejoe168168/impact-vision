"""Tool: Gap analysis comparing reported metrics against IRIS+ Core Metric Sets."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.models import Company
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class GapAnalysisInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    reported_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="IRIS+ metric ID -> value (e.g. {'PI4060': '10000', 'OI6024': '150'})",
    )
    impact_themes: list[str] = Field(default_factory=list)
    custom_metric_set: list[str] = Field(
        default_factory=list,
        description="Optional: custom set of required IRIS+ metric IDs (overrides Core Metric Set)",
    )


class GapAnalysisTool(BaseTool):
    name = "gap_analysis"
    description = (
        "Compare a company's reported metrics against the IRIS+ Core Metric Set requirements. "
        "Returns coverage percentage, missing metrics, and prioritized recommendations. "
        "Optionally specify a custom metric set to check against."
    )
    input_model = GapAnalysisInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, GapAnalysisInput) else GapAnalysisInput.model_validate(arguments)

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        company = Company(
            name=args.company_name,
            reported_metrics=args.reported_metrics,
            impact_themes=args.impact_themes,
        )

        core_set = set(args.custom_metric_set) if args.custom_metric_set else None
        result = analyze_gaps(company, store, core_set=core_set)

        lines = [
            f"Gap Analysis: {result['company']}",
            "=" * 60,
            f"Core Metric Set: {result['core_metric_set_size']} metrics",
            f"Reported: {result['metrics_reported']} | Missing: {result['metrics_missing']}",
            f"Coverage: {result['coverage_percentage']}%",
            "",
        ]

        bar_width = 30
        filled = int(result["coverage_percentage"] / 100 * bar_width)
        lines.append("[" + "#" * filled + "-" * (bar_width - filled) + f"] {result['coverage_percentage']}%")
        lines.append("")

        if result["missing"]:
            lines.append("Missing Metrics:")
            for m in result["missing"]:
                lines.append(f"  - {m['id']}: {m['name']}")
                if m.get("definition"):
                    lines.append(f"    {m['definition'][:100]}")
            lines.append("")

        if result["reported"]:
            lines.append("Reported Metrics:")
            for m in result["reported"]:
                lines.append(f"  + {m['id']}: {m['name']} = {m.get('value', 'N/A')}")
            lines.append("")

        if result.get("extra_metrics_reported"):
            lines.append(f"Additional metrics reported ({len(result['extra_metrics_reported'])}):")
            for m in result["extra_metrics_reported"][:5]:
                lines.append(f"  * {m['id']}: {m['name']} = {m.get('value', 'N/A')}")
            lines.append("")

        if result["recommendations"]:
            lines.append("Recommendations:")
            for rec in result["recommendations"]:
                lines.append(f"  > {rec}")

        return ToolResult(
            output="\n".join(lines),
            metadata={"gap_analysis": result},
        )
