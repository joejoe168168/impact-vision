"""Tool: Search and browse the IRIS+ 5.3c metric catalog."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.tools.impact.common import normalize_str_list
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class IrisCatalogInput(BaseModel):
    action: Literal["search", "get", "filter_sdg", "filter_theme", "filter_dimension", "stats"] = Field(
        description="Action to perform on the IRIS+ catalog"
    )
    query: str = Field(
        default="",
        description="Search query (for 'search'), metric ID (for 'get'), theme name (for 'filter_theme'), dimension name (for 'filter_dimension')",
    )
    sdg_goal: int | None = Field(default=None, description="SDG goal number (1-17) for 'filter_sdg'")
    sdg_target: str | None = Field(default=None, description="SDG target ID like '1.1' for more specific SDG filter")
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return")


class IrisCatalogTool(BaseTool):
    name = "iris_catalog"
    description = (
        "Search, filter, and browse the IRIS+ 5.3c Catalog of Metrics (~787 metrics). "
        "Actions: 'search' (keyword search), 'get' (by metric ID), 'filter_sdg' (by SDG goal/target), "
        "'filter_theme' (by impact theme), 'filter_dimension' (by dimension of impact), 'stats' (catalog summary). "
        "The catalog maps metrics to SDG targets and 5 Dimensions of Impact."
    )
    input_model = IrisCatalogInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, IrisCatalogInput) else IrisCatalogInput.model_validate(arguments)

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        if store.count == 0:
            return ToolResult(
                output="IRIS+ catalog is empty. Run 'impact-vision catalog load' to load it from Excel.",
                is_error=True,
            )

        if args.action == "stats":
            stats = store.stats()
            return ToolResult(output=json.dumps(stats, indent=2))

        if args.action == "get":
            metric = store.get(args.query.strip().upper())
            if metric is None:
                fallback = store.search(args.query, limit=5)
                if fallback:
                    return ToolResult(
                        output=f"Metric '{args.query}' not found.\n\nClosest matches:\n{_format_metric_list(fallback, 5)}",
                        is_error=True,
                    )
                return ToolResult(output=f"Metric '{args.query}' not found", is_error=True)
            return ToolResult(output=json.dumps(metric.model_dump(), indent=2))

        if args.action == "search":
            results = store.search(args.query, limit=args.limit)
            return ToolResult(output=_format_metric_list(results, args.limit))

        if args.action == "filter_sdg":
            if args.sdg_goal is None:
                return ToolResult(output="sdg_goal is required for filter_sdg action", is_error=True)
            results = store.filter_by_sdg(args.sdg_goal, args.sdg_target)
            return ToolResult(output=_format_metric_list(results, args.limit))

        if args.action == "filter_theme":
            theme = normalize_str_list([args.query])[0] if args.query.strip() else args.query
            results = store.filter_by_theme(theme)
            return ToolResult(output=_format_metric_list(results, args.limit))

        if args.action == "filter_dimension":
            results = store.filter_by_dimension(args.query)
            return ToolResult(output=_format_metric_list(results, args.limit))

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)


def _format_metric_list(metrics: list, limit: int) -> str:
    total = len(metrics)
    shown = metrics[:limit]
    lines = [f"Found {total} metrics (showing {len(shown)}):\n"]
    for m in shown:
        sdgs = ", ".join(f"SDG {g}" for g in m.sdg_goals[:5]) if m.sdg_goals else "No SDG mapping"
        dims = ", ".join(m.dimensions.active_dimensions[:3]) if m.dimensions.active_dimensions else "No dimensions"
        lines.append(f"  {m.id}: {m.name}")
        lines.append(f"    Category: {m.primary_impact_category} | SDGs: {sdgs} | Dims: {dims}")
        if m.definition:
            lines.append(f"    Def: {m.definition[:120]}...")
        lines.append("")
    return "\n".join(lines)
