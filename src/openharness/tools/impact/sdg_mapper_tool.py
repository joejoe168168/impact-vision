"""Tool: Map a company to SDG Goals and Targets with alignment scoring."""

from __future__ import annotations


from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.models import Company
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sdg_goals
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class SdgMapperInput(BaseModel):
    company_name: str = Field(description="Name of the company to assess")
    company_description: str = Field(default="", description="Brief description of the company's activities")
    sector: str = Field(default="", description="Industry sector")
    impact_themes: list[str] = Field(default_factory=list, description="Impact themes claimed (e.g. 'Financial Inclusion')")
    reported_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="IRIS+ metric ID -> reported value (e.g. {'PI4060': '10000', 'PI9468': '$5M'})",
    )
    sdg_claims: list[int] = Field(default_factory=list, description="SDG goals the company claims (1-17)")
    sdg_goals: list[int] = Field(
        default_factory=list,
        description="Specific SDG goals to analyze (empty = all 17)",
    )


class SdgMapperTool(BaseTool):
    name = "sdg_mapper"
    description = (
        "Map a company's reported IRIS+ metrics and impact claims to UN SDG Goals and Targets. "
        "Returns per-goal alignment scores (0-100) based on metric coverage, theme relevance, "
        "and data depth. Provide company details and optionally specify which SDG goals to analyze."
    )
    input_model = SdgMapperInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, SdgMapperInput) else SdgMapperInput.model_validate(arguments)

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        reported_metrics, metric_warnings = normalize_metric_map(args.reported_metrics)
        sdg_claims, sdg_warnings = normalize_sdg_goals(args.sdg_claims)
        requested_goals, requested_warnings = normalize_sdg_goals(args.sdg_goals)

        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=args.sector,
            impact_themes=infer_themes(f"{args.company_description} {args.sector}", args.impact_themes),
            reported_metrics=reported_metrics,
            sdg_claims=sdg_claims,
        )

        alignments = map_sdg_alignment(
            company, store, goals=requested_goals or None
        )

        output_lines = [f"SDG Alignment Analysis: {company.name}\n"]
        output_lines.append("=" * 60)

        top = [a for a in alignments if a.score > 0]
        if not top:
            output_lines.append("No SDG alignments found. Consider reporting IRIS+ metrics to establish alignment.")
        else:
            for a in top:
                bar = _score_bar(a.score)
                output_lines.append(f"\nSDG {a.goal}: {a.goal_name}")
                output_lines.append(f"  Score: {a.score}/100 {bar} [{a.confidence} confidence]")
                if a.matched_metrics:
                    output_lines.append(f"  Matched metrics: {', '.join(a.matched_metrics[:5])}")
                if a.matched_targets:
                    output_lines.append(f"  Matched targets: {', '.join(a.matched_targets[:5])}")

        output_lines.append("\n" + "=" * 60)
        output_lines.append(f"Total SDGs with alignment: {len(top)}/17")
        warnings = metric_warnings + sdg_warnings + requested_warnings
        if warnings:
            output_lines.append("Warnings:")
            for warning in warnings[:8]:
                output_lines.append(f"  - {warning}")

        return ToolResult(
            output="\n".join(output_lines),
            metadata={"alignments": [a.model_dump() for a in alignments], "warnings": warnings},
        )


def _score_bar(score: float, width: int = 20) -> str:
    filled = int(score / 100 * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"
