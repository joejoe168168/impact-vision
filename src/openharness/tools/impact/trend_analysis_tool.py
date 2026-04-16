"""Tool: Analyze metric trends over time for a company."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.models import Company, MetricValue
from openharness.impact.trend_analysis import analyze_company_trends, assess_target_progress
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class TrendAnalysisInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    company_description: str = Field(default="")
    sector: str = Field(default="")
    geography: str = Field(default="")
    metric_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of metric data points, each with keys: "
            "metric_id (str), value (number/str), period (str, e.g. 'FY2024'), "
            "optional: unit, source, verified (bool), notes"
        ),
    )
    impact_targets: dict[str, str] = Field(
        default_factory=dict,
        description="Metric ID -> target description (e.g. {'OI4112': '500 tCO2e by 2027'})",
    )
    reported_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="Current reported metric values (fallback if no metric_history)",
    )
    output_format: Literal["text", "json"] = Field(default="text")


class TrendAnalysisTool(BaseTool):
    name = "trend_analysis"
    description = (
        "Analyze metric trends over time for a company. "
        "Requires historical metric data (metric_history) with at least 2 data "
        "points per metric. Reports direction (improving/declining/stable), "
        "percentage change, volatility, and verification status."
    )
    input_model = TrendAnalysisInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, TrendAnalysisInput) else TrendAnalysisInput.model_validate(arguments)

        history = []
        for entry in args.metric_history:
            try:
                history.append(MetricValue(**entry))
            except Exception:
                continue

        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=args.sector,
            geography=args.geography,
            metric_history=history,
            impact_targets=args.impact_targets,
            reported_metrics=args.reported_metrics,
        )

        trend_result = analyze_company_trends(company)
        target_result = assess_target_progress(company) if company.impact_targets else None

        combined = {**trend_result}
        if target_result:
            combined["target_tracking"] = target_result

        if args.output_format == "json":
            return ToolResult(output=json.dumps(combined, indent=2), metadata=combined)

        lines = [
            f"TREND ANALYSIS: {company.name}",
            "=" * 60,
            trend_result["summary"],
            "",
        ]

        for trend in trend_result["trends"]:
            direction_icon = {
                "improving": "+",
                "declining": "!",
                "stable": "=",
                "insufficient_data": "?",
            }.get(trend["direction"], "?")

            lines.append(f"  [{direction_icon}] {trend['metric_id']}: {trend['direction']}")
            if trend["direction"] != "insufficient_data":
                lines.append(f"      {trend['first_value']} -> {trend['last_value']} ({trend['change_pct']:+.1f}%)")
                lines.append(f"      Period: {trend['first_period']} to {trend['last_period']} | Points: {trend['data_points']}")
                if trend.get("volatility_pct", 0) > 0:
                    lines.append(f"      Volatility: {trend['volatility_pct']:.1f}%")
                if trend.get("verified_count", 0) > 0:
                    lines.append(f"      Verified data points: {trend['verified_count']}/{trend['data_points']}")
            else:
                lines.append(f"      {trend['summary']}")
            lines.append("")

        if target_result and target_result["targets"]:
            lines.append("TARGET TRACKING")
            lines.append("-" * 40)
            lines.append(target_result["summary"])
            lines.append("")
            for t in target_result["targets"]:
                status_icon = {"exceeded": "+", "on_track": "=", "behind": "!", "at_risk": "!!", "no_data": "?"}.get(t["status"], "?")
                lines.append(f"  [{status_icon}] {t['summary']}")
            lines.append("")

        return ToolResult(output="\n".join(lines), metadata=combined)
