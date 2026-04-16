"""Tool: Cross-reference lookup between sustainability frameworks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.tools.impact.common import normalize_metric_ids
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class CrossReferenceInput(BaseModel):
    action: Literal["lookup", "search", "list"] = Field(
        description=(
            "'lookup': Find equivalents for a specific metric ID. "
            "'search': Search cross-references by concept name. "
            "'list': Show all cross-reference mappings."
        )
    )
    standard: Literal["iris", "gri", "edci", "sfdr", "any"] = Field(
        default="any",
        description="Which standard the metric_id belongs to. Use 'any' to search across all.",
    )
    metric_id: str = Field(
        default="",
        description="Metric/disclosure ID to look up (e.g., 'OI4112' for IRIS+, '305-1' for GRI, 'EDCI-E1' for EDCI, or a SFDR PAI number like '1').",
    )
    query: str = Field(
        default="",
        description="Concept name to search for (e.g., 'GHG emissions', 'gender', 'energy').",
    )


class CrossReferenceTool(BaseTool):
    name = "cross_reference"
    description = (
        "Look up equivalent metrics across sustainability frameworks. "
        "Given a metric in one standard (IRIS+, GRI, EDCI, SFDR PAI, TCFD, SASB), "
        "find the corresponding metrics in all other standards.\n\n"
        "Covers 40+ concepts including: GHG emissions, energy, water, waste, biodiversity, "
        "workforce diversity, governance, social impact, and more.\n\n"
        "Use 'lookup' with a metric ID, 'search' with a concept keyword, or 'list' to see all mappings."
    )
    input_model = CrossReferenceInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, CrossReferenceInput) else CrossReferenceInput.model_validate(arguments)

        from openharness.impact.frameworks.cross_reference import (
            format_cross_reference,
            get_all_cross_references,
            lookup_by_edci,
            lookup_by_gri,
            lookup_by_iris,
            lookup_by_sfdr,
            search_cross_references,
        )

        if args.action == "list":
            refs = get_all_cross_references()
            lines = [f"Cross-Reference Map ({len(refs)} concepts):", "=" * 60, ""]
            for xref in refs:
                lines.append(format_cross_reference(xref))
                lines.append("")
            return ToolResult(output="\n".join(lines))

        if args.action == "search":
            if not args.query:
                return ToolResult(output="Provide a 'query' for search action", is_error=True)
            results = search_cross_references(args.query)
            if not results:
                return ToolResult(output=f"No cross-references found for: {args.query}")
            lines = [f"Cross-references matching '{args.query}' ({len(results)} found):", ""]
            for xref in results:
                lines.append(format_cross_reference(xref))
                lines.append("")
            return ToolResult(output="\n".join(lines))

        if args.action == "lookup":
            if not args.metric_id:
                return ToolResult(output="Provide a 'metric_id' for lookup action", is_error=True)

            results = []
            mid = args.metric_id.strip().upper()

            if args.standard in ("iris", "any"):
                results.extend(lookup_by_iris(mid))
            if args.standard in ("gri", "any"):
                results.extend(lookup_by_gri(mid))
            if args.standard in ("edci", "any"):
                results.extend(lookup_by_edci(mid))
            if args.standard in ("sfdr", "any"):
                try:
                    sfdr_id = int(mid.replace("PAI", "").strip())
                    results.extend(lookup_by_sfdr(sfdr_id))
                except ValueError:
                    pass

            if not results and args.standard == "any":
                normalized_ids, _ = normalize_metric_ids([mid])
                for normalized_id in normalized_ids:
                    results.extend(lookup_by_iris(normalized_id))
                results.extend(search_cross_references(mid))

            seen = set()
            deduped = []
            for r in results:
                if r.concept not in seen:
                    seen.add(r.concept)
                    deduped.append(r)

            if not deduped:
                return ToolResult(output=f"No cross-references found for metric: {mid}")

            lines = [f"Cross-references for '{mid}':", ""]
            for xref in deduped:
                lines.append(format_cross_reference(xref))
                lines.append("")
            return ToolResult(output="\n".join(lines))

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)
