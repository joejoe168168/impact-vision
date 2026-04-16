"""Tool: 5-Dimension Impact Assessment (What/Who/How Much/Contribution/Risk)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.models import Company
from openharness.tools.impact.common import infer_themes, normalize_metric_map
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class FiveDimensionInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    company_description: str = Field(default="", description="Brief company description")
    sector: str = Field(default="")
    impact_themes: list[str] = Field(default_factory=list, description="Impact themes (e.g. 'Health', 'Climate')")
    reported_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="IRIS+ metric ID -> value pairs the company has reported",
    )
    focus_theme: str = Field(
        default="",
        description="Specific impact theme to focus the assessment on",
    )


class FiveDimensionAssessTool(BaseTool):
    name = "five_dimension_assess"
    description = (
        "Score a company on the 5 Dimensions of Impact (What, Who, How Much, Contribution, Risk) "
        "using GIIN's IRIS+ framework. Returns dimension-by-dimension scores (0-5), gap identification, "
        "an overall letter grade, and recommendations. Provide the company's reported IRIS+ metrics."
    )
    input_model = FiveDimensionInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, FiveDimensionInput) else FiveDimensionInput.model_validate(arguments)

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        reported_metrics, warnings = normalize_metric_map(args.reported_metrics)
        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=args.sector,
            impact_themes=infer_themes(f"{args.company_description} {args.sector}", args.impact_themes),
            reported_metrics=reported_metrics,
        )

        result = assess_five_dimensions(
            company, store, theme=args.focus_theme or None
        )

        prov_label = {"evidence-based": "Evidence-based", "partial": "Partially evidenced", "estimated": "Estimated (no metrics reported)"}
        lines = [
            f"5-Dimension Impact Assessment: {company.name}",
            "=" * 60,
            f"Impact Theme: {result.impact_theme or 'General'}",
            f"Overall Grade: {result.overall_grade} ({result.overall_score}/5.0)",
            f"Confidence: {prov_label.get(result.overall_provenance, result.overall_provenance)}",
            "",
        ]
        if result.overall_provenance != "evidence-based":
            lines.append("⚠ Scores below are estimated from sector baselines and description keywords.")
            lines.append("  Report IRIS+ metrics to upgrade to evidence-based scoring.")
            lines.append("")

        for dim in [result.what, result.who, result.how_much, result.contribution, result.risk]:
            bar = _dim_bar(dim.score)
            prov_tag = f" [{dim.provenance}]" if dim.provenance != "evidence-based" else ""
            lines.append(f"{dim.dimension}: {dim.score}/5.0 {bar}{prov_tag}")
            lines.append(f"  {dim.notes}")
            if dim.gaps:
                lines.append(f"  Gaps: {', '.join(dim.gaps[:3])}")
            lines.append("")

        if result.recommendations:
            lines.append("Recommendations:")
            for i, rec in enumerate(result.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        return ToolResult(
            output="\n".join(lines),
            metadata={"assessment": result.model_dump()},
        )


def _dim_bar(score: float, width: int = 15) -> str:
    filled = int(score / 5.0 * width)
    return "[" + "=" * filled + " " * (width - filled) + "]"
