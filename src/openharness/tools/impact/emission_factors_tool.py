"""Tool: List, select, and run sensitivity scenarios on emission-factor revisions (v3)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.climate_accounting import ActivityData
from openharness.impact.emission_factors import (
    apply_catalog_to_inventory,
    default_factor_catalog,
    factor_sensitivity,
    summarise_sensitivity,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class EmissionFactorsInput(BaseModel):
    action: Literal["list", "get", "sensitivity", "apply_catalog", "summary"] = Field(
        description="Action: list publishers/versions, get one revision, run a single sensitivity, recompute an inventory against a catalog version, or summarise activity sensitivities."
    )
    revision_id: str = Field(default="", description="Revision ID for 'get' or 'sensitivity'")
    catalog_version: str = Field(default="", description="Catalog version for 'apply_catalog'")
    activity: dict = Field(default_factory=dict, description="ActivityData payload for 'sensitivity'")
    activities: list[dict] = Field(default_factory=list, description="Activity payloads for 'apply_catalog'/'summary'")
    revision_ids: list[str] = Field(default_factory=list, description="Revision IDs aligned with activities for 'summary'")
    company_name: str = Field(default="Demo Co", description="Company name for 'apply_catalog'")
    reporting_period: str = Field(default="FY2026", description="Reporting period for 'apply_catalog'")
    output_format: Literal["json", "text"] = "json"


class EmissionFactorsTool(BaseTool):
    name = "emission_factors"
    description = (
        "Versioned emission-factor catalog (EPA / DEFRA / IEA / IPCC offline snapshots). "
        "Actions: 'list' / 'get' revisions, 'sensitivity' for one activity, "
        "'apply_catalog' to recompute an inventory against a named catalog version, "
        "and 'summary' for payload-level sensitivity coverage."
    )
    input_model = EmissionFactorsInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, EmissionFactorsInput) else EmissionFactorsInput.model_validate(arguments)
        catalog = default_factor_catalog()

        if args.action == "list":
            payload = {
                "publishers": catalog.list_publishers(),
                "catalog_versions": catalog.list_catalog_versions(),
                "revisions": [r.revision_id for r in catalog.revisions],
            }
            return _format(payload, args.output_format)

        if args.action == "get":
            if not args.revision_id:
                return ToolResult(output="revision_id is required for 'get'", is_error=True)
            try:
                revision = catalog.get(args.revision_id)
            except KeyError as e:
                return ToolResult(output=str(e), is_error=True)
            return _format(revision.model_dump(mode="json"), args.output_format)

        if args.action == "sensitivity":
            if not args.revision_id or not args.activity:
                return ToolResult(output="revision_id and activity are required", is_error=True)
            try:
                revision = catalog.get(args.revision_id)
                result = factor_sensitivity(args.activity, revision)
            except (KeyError, ValueError) as e:
                return ToolResult(output=str(e), is_error=True)
            return _format(result.model_dump(mode="json"), args.output_format)

        if args.action == "apply_catalog":
            if not args.catalog_version:
                return ToolResult(output="catalog_version is required", is_error=True)
            try:
                inventory = apply_catalog_to_inventory(
                    company_name=args.company_name,
                    reporting_period=args.reporting_period,
                    activities=[ActivityData.model_validate(a) for a in args.activities],
                    catalog=catalog,
                    catalog_version=args.catalog_version,
                )
            except ValueError as e:
                return ToolResult(output=str(e), is_error=True)
            return _format(inventory.model_dump(mode="json"), args.output_format)

        if args.action == "summary":
            if len(args.activities) != len(args.revision_ids):
                return ToolResult(
                    output="activities and revision_ids must have equal length",
                    is_error=True,
                )
            try:
                revisions = [catalog.get(rid) for rid in args.revision_ids]
            except KeyError as e:
                return ToolResult(output=str(e), is_error=True)
            summary = summarise_sensitivity(args.activities, revisions)
            return _format(summary.model_dump(mode="json"), args.output_format)

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)


def _format(payload: dict, format: str) -> ToolResult:
    if format == "text":
        return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)
    return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)
