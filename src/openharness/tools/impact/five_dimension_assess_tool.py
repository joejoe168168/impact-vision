"""Tool: 5-Dimension Impact Assessment (What/Who/How Much/Contribution/Risk)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.impact.database import ensure_catalog_loaded
from openharness.impact.decision_workflow import render_evidence_chains
from openharness.impact.five_dimensions import assess_five_dimensions, assess_additionality
from openharness.impact.models import Assessment, Company
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sector
from openharness.tools.impact.exclusion_screening_tool import quick_exclusion_check
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class FiveDimensionInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    company_description: str = Field(default="", description="Brief company description")
    sector: str = Field(default="")
    geography: str = Field(default="", description="Country or region (e.g. 'Kenya', 'Southeast Asia')")
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
            store = ensure_catalog_loaded()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        reported_metrics, warnings = normalize_metric_map(args.reported_metrics)
        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=normalize_sector(args.sector),
            geography=args.geography,
            impact_themes=infer_themes(f"{args.company_description} {args.sector}", args.impact_themes),
            reported_metrics=reported_metrics,
        )

        exclusion = quick_exclusion_check(company.name, company.description, company.sector)

        result = assess_five_dimensions(
            company, store, theme=args.focus_theme or None
        )
        assessment = Assessment(company=company, five_dimensions=result)
        evidence_chains = render_evidence_chains(assessment, store)

        prov_label = {"evidence-based": "Evidence-based", "partial": "Partially evidenced", "estimated": "Estimated (no metrics reported)"}
        lines = [
            f"5-Dimension Impact Assessment: {company.name}",
            "=" * 60,
        ]
        if not exclusion["passed"]:
            lines.append("⛔ EXCLUSION SCREENING WARNING")
            lines.append(f"  Flagged: {'; '.join(exclusion['flags'][:3])}")
            lines.append("  Run `exclusion_screening` tool for full details before proceeding.")
            lines.append("")

        lines.extend([
            f"Impact Theme: {result.impact_theme or 'General'}",
            f"Overall Grade: {result.overall_grade} ({result.overall_score}/5.0)",
            f"Confidence: {prov_label.get(result.overall_provenance, result.overall_provenance)}",
            "",
        ])
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

        additionality = assess_additionality(company)
        if additionality["signals_found"]:
            lines.append(f"Additionality: {additionality['assessment']} ({additionality['signal_count']} signals)")
            lines.append(f"  Signals: {', '.join(additionality['signals_found'][:5])}")
            lines.append("")
        if result.contribution.score < 3.0:
            lines.append("Counterfactual Review (flag for human review):")
            lines.append(f"  {additionality['counterfactual_prompt']}")
            lines.append("")

        if result.recommendations:
            lines.append("Recommendations:")
            for i, rec in enumerate(result.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        if warnings:
            warning_block = "⚠ Input warnings:\n" + "\n".join(f"  - {w}" for w in warnings) + "\n\n"
            lines.insert(0, warning_block)

        return ToolResult(
            output="\n".join(lines),
            metadata={
                "assessment": result.model_dump(),
                "evidence_chains": {
                    key: value.model_dump(mode="json")
                    for key, value in evidence_chains.items()
                },
                "additionality": additionality,
            },
        )


def _dim_bar(score: float, width: int = 15) -> str:
    filled = int(score / 5.0 * width)
    return "[" + "=" * filled + " " * (width - filled) + "]"
