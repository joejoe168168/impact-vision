"""Tool: EU Digital Product Passport (DPP) data import and IRIS+ mapping.

The EU Ecodesign for Sustainable Products Regulation (ESPR) introduces Digital
Product Passports containing product-level sustainability data. This tool
imports DPP data (JSON/CSV) and maps it to IRIS+ impact metrics for portfolio-
level impact assessment.

Reference: Regulation (EU) 2024/1781 (ESPR), adopted 2024-06-27.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


# DPP data categories as defined by the ESPR
DPP_CATEGORIES = {
    "durability": {
        "description": "Product lifetime, repairability, reliability",
        "iris_mappings": [],
        "esrs_mappings": ["E5-4", "E5-5"],
        "sdg_goals": [12],
    },
    "carbon_footprint": {
        "description": "Product carbon footprint across life cycle",
        "iris_mappings": ["OI4112", "OI1479"],
        "esrs_mappings": ["E1-6"],
        "sdg_goals": [13],
    },
    "recycled_content": {
        "description": "Percentage of recycled materials",
        "iris_mappings": [],
        "esrs_mappings": ["E5-4"],
        "sdg_goals": [12],
    },
    "energy_efficiency": {
        "description": "Energy consumption during use phase",
        "iris_mappings": ["OI4112"],
        "esrs_mappings": ["E1-5"],
        "sdg_goals": [7, 12],
    },
    "substances_of_concern": {
        "description": "Hazardous substances per REACH/CLP regulation",
        "iris_mappings": [],
        "esrs_mappings": ["E2-5"],
        "sdg_goals": [3, 12],
    },
    "end_of_life": {
        "description": "Recyclability, disposal instructions, take-back schemes",
        "iris_mappings": [],
        "esrs_mappings": ["E5-5"],
        "sdg_goals": [12],
    },
    "supply_chain": {
        "description": "Supply chain due diligence, origin of materials",
        "iris_mappings": [],
        "esrs_mappings": ["S2-1", "G1-2"],
        "sdg_goals": [8, 12],
    },
    "water_use": {
        "description": "Water consumption in production",
        "iris_mappings": [],
        "esrs_mappings": ["E3-4"],
        "sdg_goals": [6],
    },
}


class ProductPassportInput(BaseModel):
    action: Literal["import", "map", "assess"] = Field(
        description=(
            "'import': Parse DPP data from JSON. "
            "'map': Map DPP categories to IRIS+/ESRS metrics. "
            "'assess': Score DPP completeness and suggest missing data."
        )
    )
    dpp_data: str = Field(
        default="",
        description="DPP data as JSON string (for 'import' action)",
    )
    product_category: str = Field(
        default="",
        description="Product category (e.g. 'textiles', 'electronics', 'batteries')",
    )
    company_name: str = Field(default="", description="Company name for context")


class ProductPassportTool(BaseTool):
    name = "product_passport"
    description = (
        "EU Digital Product Passport (DPP) tool for the Ecodesign for Sustainable "
        "Products Regulation (ESPR). Import product-level sustainability data, "
        "map to IRIS+/ESRS metrics, and assess completeness."
    )
    input_model = ProductPassportInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ProductPassportInput) else ProductPassportInput.model_validate(arguments)

        if args.action == "import":
            return self._import_dpp(args)
        if args.action == "map":
            return self._map_categories(args)
        if args.action == "assess":
            return self._assess_completeness(args)
        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

    def _import_dpp(self, args: ProductPassportInput) -> ToolResult:
        if not args.dpp_data.strip():
            return ToolResult(
                output="Provide DPP data as a JSON string in 'dpp_data' field.",
                is_error=True,
            )
        try:
            data = json.loads(args.dpp_data)
        except json.JSONDecodeError as e:
            return ToolResult(output=f"Invalid JSON: {e}", is_error=True)

        product_name = data.get("product_name", data.get("name", "Unknown"))
        categories_found: list[str] = []
        mapped_metrics: dict[str, Any] = {}

        for cat_id, cat_info in DPP_CATEGORIES.items():
            if cat_id in data or any(k in data for k in cat_info["description"].lower().split()):
                categories_found.append(cat_id)
                val = data.get(cat_id)
                if val is not None:
                    for iris_id in cat_info["iris_mappings"]:
                        mapped_metrics[iris_id] = str(val)

        lines = [
            f"DPP Import: {product_name}",
            f"Categories found: {len(categories_found)}/{len(DPP_CATEGORIES)}",
            "",
        ]
        for cat in categories_found:
            info = DPP_CATEGORIES[cat]
            lines.append(f"  [{cat}] {info['description']}")
            if info["iris_mappings"]:
                lines.append(f"    -> IRIS+: {', '.join(info['iris_mappings'])}")

        if mapped_metrics:
            lines.append(f"\nMapped to {len(mapped_metrics)} IRIS+ metrics: {', '.join(mapped_metrics.keys())}")

        return ToolResult(
            output="\n".join(lines),
            metadata={"product": product_name, "categories": categories_found, "iris_metrics": mapped_metrics},
        )

    def _map_categories(self, args: ProductPassportInput) -> ToolResult:
        lines = [
            "DPP Category -> IRIS+ / ESRS / SDG Mapping",
            "=" * 50,
            "",
        ]
        for cat_id, info in DPP_CATEGORIES.items():
            lines.append(f"  {cat_id}: {info['description']}")
            if info["iris_mappings"]:
                lines.append(f"    IRIS+: {', '.join(info['iris_mappings'])}")
            if info["esrs_mappings"]:
                lines.append(f"    ESRS: {', '.join(info['esrs_mappings'])}")
            lines.append(f"    SDGs: {', '.join(str(g) for g in info['sdg_goals'])}")
            lines.append("")

        priority = _get_priority_categories(args.product_category)
        if priority:
            lines.append(f"Priority categories for '{args.product_category}': {', '.join(priority)}")

        return ToolResult(output="\n".join(lines))

    def _assess_completeness(self, args: ProductPassportInput) -> ToolResult:
        if not args.dpp_data.strip():
            return ToolResult(output="Provide DPP data as JSON for completeness assessment.", is_error=True)

        try:
            data = json.loads(args.dpp_data)
        except json.JSONDecodeError as e:
            return ToolResult(output=f"Invalid JSON: {e}", is_error=True)

        priority = _get_priority_categories(args.product_category)
        all_cats = list(DPP_CATEGORIES.keys())
        check_cats = priority if priority else all_cats

        present: list[str] = []
        missing: list[str] = []
        for cat in check_cats:
            if cat in data and data[cat] not in (None, "", "N/A"):
                present.append(cat)
            else:
                missing.append(cat)

        completeness = round(len(present) / max(1, len(check_cats)) * 100, 1)
        lines = [
            f"DPP Completeness Assessment ({args.product_category or 'general'})",
            "=" * 50,
            f"Score: {completeness}% ({len(present)}/{len(check_cats)} categories)",
            "",
        ]
        if present:
            lines.append("Present:")
            for c in present:
                lines.append(f"  [OK] {c}: {DPP_CATEGORIES[c]['description']}")
        if missing:
            lines.append("\nMissing:")
            for c in missing:
                lines.append(f"  [GAP] {c}: {DPP_CATEGORIES[c]['description']}")

        return ToolResult(
            output="\n".join(lines),
            metadata={"completeness_pct": completeness, "present": present, "missing": missing},
        )


_PRODUCT_CATEGORY_PRIORITIES: dict[str, list[str]] = {
    "textiles": ["carbon_footprint", "substances_of_concern", "recycled_content", "durability", "supply_chain", "water_use"],
    "electronics": ["carbon_footprint", "energy_efficiency", "durability", "recycled_content", "substances_of_concern", "end_of_life"],
    "batteries": ["carbon_footprint", "recycled_content", "substances_of_concern", "durability", "end_of_life", "supply_chain"],
    "furniture": ["durability", "recycled_content", "carbon_footprint", "substances_of_concern", "end_of_life"],
    "construction": ["carbon_footprint", "recycled_content", "energy_efficiency", "durability", "substances_of_concern"],
}


def _get_priority_categories(product_category: str) -> list[str]:
    if not product_category:
        return []
    cat_lower = product_category.lower()
    for key, priorities in _PRODUCT_CATEGORY_PRIORITIES.items():
        if key in cat_lower:
            return priorities
    return []
