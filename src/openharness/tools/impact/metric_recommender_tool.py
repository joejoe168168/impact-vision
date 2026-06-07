"""Tool: Recommend IRIS+ metrics for a company/fund context."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.gap_analysis import CORE_METRIC_SET_IDS
from openharness.impact.toolbox import build_esg_workflow
from openharness.tools.impact.common import normalize_sdg_goals, normalize_str_list
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MetricRecommenderInput(BaseModel):
    company_name: str = Field(default="", description="Optional company name for workflow context.")
    sector: str = Field(default="", description="Sector/industry context.")
    geography: str = Field(default="", description="Country or region.")
    description: str = Field(default="", description="Company or thesis description.")
    company_description: str = Field(default="", description="Alias for description used by MCP/API callers.")
    impact_themes: list[str] = Field(default_factory=list, description="Impact themes.")
    sdg_goals: list[int] = Field(default_factory=list, description="Target SDG goals (1-17).")
    sdg_claims: list[int] = Field(default_factory=list, description="Alias for target SDG goals.")
    reported_metrics: dict[str, object] = Field(default_factory=dict, description="Existing reported metrics to crosswalk into ESG modules.")
    max_metrics: int = Field(default=20, ge=5, le=100, description="Maximum recommendations to return.")
    include_core_set: bool = Field(default=True, description="Prioritize IRIS+ core metric set entries.")
    output_format: Literal["text", "json"] = Field(default="text")
    optimize_for_sdg_coverage: bool = Field(
        default=False,
        description="If True, prioritize metrics that maximize portfolio-level SDG coverage",
    )
    current_portfolio_sdgs: list[int] = Field(
        default_factory=list,
        description="SDGs already covered by the portfolio (for optimization mode)",
    )


class MetricRecommenderTool(BaseTool):
    name = "impact_metric_recommender"
    description = (
        "Recommend high-relevance IRIS+ metrics using themes, SDG goals, sector, and description. "
        "Outputs a prioritized shortlist with rationale tags (theme/sdg/keyword/core-set)."
    )
    input_model = MetricRecommenderInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, MetricRecommenderInput) else MetricRecommenderInput.model_validate(arguments)
        themes = normalize_str_list(args.impact_themes)
        goals, _ = normalize_sdg_goals(args.sdg_goals or args.sdg_claims)
        description = args.description or args.company_description

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        if store.count == 0:
            return ToolResult(output="No IRIS+ catalog loaded.", is_error=True)

        metric_scores: dict[str, float] = defaultdict(float)
        reasons: dict[str, list[str]] = defaultdict(list)
        metric_map = {}

        if args.include_core_set:
            for metric_id in CORE_METRIC_SET_IDS:
                metric = store.get(metric_id)
                if metric is None:
                    continue
                metric_scores[metric.id] += 2.0
                reasons[metric.id].append("core-set")
                metric_map[metric.id] = metric

        for theme in themes:
            for metric in store.filter_by_theme(theme):
                metric_scores[metric.id] += 3.0
                reasons[metric.id].append(f"theme:{theme}")
                metric_map[metric.id] = metric

        for goal in goals:
            for metric in store.filter_by_sdg(goal):
                metric_scores[metric.id] += 2.5
                reasons[metric.id].append(f"sdg:{goal}")
                metric_map[metric.id] = metric

        text = f"{args.sector} {description}".strip()
        if text:
            for metric in store.search(text, limit=min(100, args.max_metrics * 4)):
                metric_scores[metric.id] += 1.5
                reasons[metric.id].append("keyword")
                metric_map[metric.id] = metric

        if args.optimize_for_sdg_coverage and args.current_portfolio_sdgs:
            covered = set(args.current_portfolio_sdgs)
            for metric_id, metric in metric_map.items():
                uncovered_sdgs = [g for g in metric.sdg_goals if g not in covered]
                if uncovered_sdgs:
                    metric_scores[metric_id] += 3.0 * len(uncovered_sdgs)
                    reasons[metric_id].append(f"fills-sdg-gap:{','.join(str(g) for g in uncovered_sdgs)}")

        ranked = sorted(
            metric_scores.items(),
            key=lambda item: (item[1], len(reasons[item[0]])),
            reverse=True,
        )[: args.max_metrics]

        recs = []
        for metric_id, score in ranked:
            metric = metric_map[metric_id]
            recs.append({
                "id": metric.id,
                "name": metric.name,
                "score": round(score, 2),
                "reasons": list(dict.fromkeys(reasons[metric.id])),
                "primary_impact_category": metric.primary_impact_category,
                "sdg_goals": metric.sdg_goals[:5],
            })

        payload = {
            "inputs": {"company_name": args.company_name, "sector": args.sector, "geography": args.geography, "themes": themes, "sdg_goals": goals},
            "recommendations": recs,
            "count": len(recs),
        }
        esg_workflow = build_esg_workflow(
            company_name=args.company_name,
            company_description=description,
            sector=args.sector,
            geography=args.geography,
            jurisdiction=args.geography,
            impact_themes=themes,
            reported_metrics=args.reported_metrics,
            document_text=description,
            country=args.geography,
            limit=5,
        )
        payload["esg_toolbox"] = esg_workflow.model_dump(mode="json")

        if args.output_format == "json":
            return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)

        if not recs:
            return ToolResult(output="No metric recommendations found. Provide more context (themes/SDGs/description).")

        lines = [
            "IRIS+ METRIC RECOMMENDATIONS",
            "=" * 50,
            f"Recommendations: {len(recs)}",
            "",
        ]
        for idx, rec in enumerate(recs, 1):
            lines.append(f"{idx}. {rec['id']}: {rec['name']} (score: {rec['score']})")
            lines.append(f"   Category: {rec['primary_impact_category'] or 'N/A'}")
            if rec["sdg_goals"]:
                lines.append(f"   SDGs: {', '.join(f'SDG {g}' for g in rec['sdg_goals'])}")
            lines.append(f"   Why: {', '.join(rec['reasons'])}")
            lines.append("")
        if esg_workflow.recommended_tools:
            lines.append("ESG TOOLBOX MODULES TO PAIR WITH THESE METRICS")
            lines.append("=" * 50)
            for item in esg_workflow.recommended_tools[:5]:
                lines.append(f"- {item.tool_id}: {item.title} ({item.readiness_score_pct}% readiness)")
                if item.reason:
                    lines.append(f"  Why: {item.reason}")
                if item.missing_inputs:
                    lines.append(f"  Missing inputs: {', '.join(item.missing_inputs[:3])}")
            if esg_workflow.next_questions:
                lines.append("")
                lines.append("Minimum follow-up questions:")
                lines.extend(f"- {question}" for question in esg_workflow.next_questions[:3])
        return ToolResult(output="\n".join(lines), metadata=payload)
