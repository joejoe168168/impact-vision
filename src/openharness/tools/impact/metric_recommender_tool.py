"""Tool: Recommend IRIS+ metrics for a company/fund context."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.gap_analysis import CORE_METRIC_SET_IDS
from openharness.tools.impact.common import normalize_sdg_goals, normalize_str_list
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MetricRecommenderInput(BaseModel):
    sector: str = Field(default="", description="Sector/industry context.")
    geography: str = Field(default="", description="Country or region.")
    description: str = Field(default="", description="Company or thesis description.")
    impact_themes: list[str] = Field(default_factory=list, description="Impact themes.")
    sdg_goals: list[int] = Field(default_factory=list, description="Target SDG goals (1-17).")
    max_metrics: int = Field(default=20, ge=5, le=100, description="Maximum recommendations to return.")
    include_core_set: bool = Field(default=True, description="Prioritize IRIS+ core metric set entries.")
    output_format: Literal["text", "json"] = Field(default="text")


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
        goals, _ = normalize_sdg_goals(args.sdg_goals)

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

        text = f"{args.sector} {args.description}".strip()
        if text:
            for metric in store.search(text, limit=min(100, args.max_metrics * 4)):
                metric_scores[metric.id] += 1.5
                reasons[metric.id].append("keyword")
                metric_map[metric.id] = metric

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
            "inputs": {"sector": args.sector, "themes": themes, "sdg_goals": goals},
            "recommendations": recs,
            "count": len(recs),
        }

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
        return ToolResult(output="\n".join(lines), metadata=payload)
