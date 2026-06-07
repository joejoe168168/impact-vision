"""Tool: Gap analysis comparing reported metrics against IRIS+ Core Metric Sets."""

from __future__ import annotations


from pydantic import BaseModel, Field

from openharness.impact.database import ensure_catalog_loaded
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.models import Company
from openharness.impact.toolbox import build_esg_workflow, crosswalk_reported_metrics
from openharness.tools.impact.common import normalize_metric_ids, normalize_metric_map, normalize_str_list
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class GapAnalysisInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    reported_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="IRIS+ metric ID -> value (e.g. {'PI4060': '10000', 'OI8869': '150'})",
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
            store = ensure_catalog_loaded()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        reported_metrics, metric_warnings = normalize_metric_map(args.reported_metrics)
        company = Company(
            name=args.company_name,
            reported_metrics=reported_metrics,
            impact_themes=normalize_str_list(args.impact_themes),
        )

        if args.custom_metric_set:
            normalized_custom, _ = normalize_metric_ids(args.custom_metric_set)
            core_set = set(normalized_custom) if normalized_custom else None
        else:
            core_set = None
        result = analyze_gaps(company, store, core_set=core_set)
        esg_crosswalk = crosswalk_reported_metrics(reported_metrics)
        esg_workflow = build_esg_workflow(
            company_name=args.company_name,
            impact_themes=company.impact_themes,
            reported_metrics=reported_metrics,
            limit=5,
        )
        result["esg_metric_crosswalk"] = esg_crosswalk
        result["esg_toolbox_recommendations"] = [
            item.model_dump(mode="json") for item in esg_workflow.recommended_tools[:5]
        ]
        result["esg_input_suggestions"] = [
            item.model_dump(mode="json") for item in esg_workflow.input_suggestions
        ]

        lines = [
            f"Gap Analysis: {result['company']}",
            "=" * 60,
            f"Core Metric Set: {result['core_metric_set_size']} metrics",
            f"Reported: {result['metrics_reported']} | Missing: {result['metrics_missing']}",
            f"Coverage: {result['coverage_percentage']}%",
            "",
        ]

        bar_width = 30
        coverage_pct = max(0.0, min(100.0, float(result.get("coverage_percentage", 0) or 0)))
        filled = int(coverage_pct / 100 * bar_width)
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
            extras = result["extra_metrics_reported"]
            shown = extras[:5]
            lines.append(f"Additional metrics reported ({len(extras)}):")
            for m in shown:
                lines.append(f"  * {m['id']}: {m['name']} = {m.get('value', 'N/A')}")
            if len(extras) > len(shown):
                lines.append(
                    f"  ... and {len(extras) - len(shown)} more (full list in result metadata)"
                )
            lines.append("")

        if esg_crosswalk:
            lines.append("ESG Framework Crosswalk:")
            for metric_id, refs in esg_crosswalk.items():
                lines.append(f"  - {metric_id}: {', '.join(refs)}")
            lines.append("")

        if esg_workflow.recommended_tools:
            lines.append("ESG Toolbox Leverage:")
            for item in esg_workflow.recommended_tools[:5]:
                missing = f" | missing: {', '.join(item.missing_inputs[:3])}" if item.missing_inputs else ""
                lines.append(
                    f"  - {item.tool_id}: {item.title} "
                    f"({item.readiness_score_pct}% readiness{missing})"
                )
            lines.append("")

        if result["recommendations"]:
            lines.append("Recommendations:")
            for rec in result["recommendations"]:
                lines.append(f"  > {rec}")

        if metric_warnings:
            warning_block = "⚠ Input warnings:\n" + "\n".join(f"  - {w}" for w in metric_warnings) + "\n"
            lines.insert(0, warning_block)

        return ToolResult(
            output="\n".join(lines),
            metadata={"gap_analysis": result},
        )
