"""Tool: List, select, and run sensitivity scenarios on emission-factor revisions (v3)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from impact_vision.impact.climate_accounting import ActivityData
from impact_vision.impact.emission_factors import (
    apply_catalog_to_inventory,
    default_factor_catalog,
    factor_sensitivity,
    summarise_sensitivity,
)
from impact_vision.tools.base import BaseTool, ToolExecutionContext, ToolResult


class EmissionFactorsInput(BaseModel):
    action: Literal[
        "list",
        "get",
        "sensitivity",
        "apply_catalog",
        "summary",
        "inventory",
        "trend",
        "scope1_mass_balance",
        "scope3",
        "energy_tce",
        "water",
    ] = Field(
        description="Action: list publishers/versions, get one revision, run a single sensitivity, recompute an inventory against a catalog version, or summarise activity sensitivities."
    )
    revision_id: str = Field(default="", description="Revision ID for 'get' or 'sensitivity'")
    catalog_version: str = Field(default="", description="Catalog version for 'apply_catalog'")
    activity: dict = Field(
        default_factory=dict, description="ActivityData payload for 'sensitivity'"
    )
    activities: list[dict] = Field(
        default_factory=list, description="Activity payloads for 'apply_catalog'/'summary'/'inventory'"
    )
    revision_ids: list[str] = Field(
        default_factory=list, description="Revision IDs aligned with activities for 'summary'"
    )
    company_name: str = Field(default="Demo Co", description="Company name for 'apply_catalog'")
    reporting_period: str = Field(
        default="FY2026", description="Reporting period for 'apply_catalog'"
    )
    output_format: Literal["json", "text"] = "json"
    annual_revenue_million_cny: float | None = Field(
        default=None, ge=0, description="Entity annual revenue in million CNY for intensity outputs"
    )
    certificates: list[dict] = Field(
        default_factory=list, description="Renewable certificate rows for certificate-adjusted market Scope 2"
    )
    scope3_categories: dict[int, dict] | None = Field(
        default=None,
        description="Scope 3 category payload; supports spend, T&D, tonne-km, waste, or activity-factor rows",
    )
    historical_years: list[dict] = Field(
        default_factory=list, description="Prior-year Scope 1/2/3 rows for comparable trend output"
    )
    scope2_electricity_mwh: float | None = Field(
        default=None, ge=0, description="Electricity consumption for automatic Scope 3 category 3 T&D"
    )
    td_loss_rate: float | None = Field(
        default=None, ge=0, le=1, description="Regional T&D loss rate; defaults to the versioned offline assumption"
    )
    grid_emission_factor_tco2e_per_mwh: float | None = Field(
        default=None, ge=0, description="Grid factor used for automatic Scope 3 category 3 T&D"
    )
    inputs: list[dict] = Field(default_factory=list)
    outputs: list[dict] = Field(default_factory=list)
    categories: dict[int, dict] = Field(default_factory=dict)
    energy_lines: list[dict] = Field(default_factory=list)
    withdrawals: list[dict] = Field(default_factory=list)
    discharge: float = 0.0


class EmissionFactorsTool(BaseTool):
    name = "emission_factors"
    description = (
        "Versioned emission-factor catalog (EPA / DEFRA / IEA / IPCC offline snapshots). "
        "Actions: 'list' / 'get' revisions, 'sensitivity' for one activity, "
        "'apply_catalog' to recompute an inventory against a named catalog version, "
        "'inventory' for an OHESG-style entity/Scope 1/2/selected Scope 3 carbon footprint, "
        "and 'summary' for payload-level sensitivity coverage."
    )
    input_model = EmissionFactorsInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, EmissionFactorsInput)
            else EmissionFactorsInput.model_validate(arguments)
        )
        catalog = default_factor_catalog()

        if args.action == "inventory":
            from impact_vision.impact.climate_accounting import calculate_ghg_inventory

            try:
                inventory = calculate_ghg_inventory(
                    company_name=args.company_name,
                    reporting_period=args.reporting_period,
                    activities=args.activities,
                    certificates=args.certificates,
                    annual_revenue_million_cny=args.annual_revenue_million_cny,
                    scope3_categories=args.scope3_categories,
                    historical_years=args.historical_years or None,
                )
            except (ValueError, KeyError) as exc:
                return ToolResult(output=f"Carbon inventory failed: {exc}", is_error=True)
            return _format(inventory.model_dump(mode="json"), args.output_format)

        if args.action == "trend":
            from impact_vision.impact.climate_accounting import three_year_comparison

            try:
                payload = three_year_comparison(args.historical_years)
            except (ValueError, KeyError, TypeError) as exc:
                return ToolResult(output=f"Trend comparison failed: {exc}", is_error=True)
            return _format(payload, args.output_format)

        if args.action in {"scope1_mass_balance", "scope3", "energy_tce", "water"}:
            from impact_vision.impact.climate_accounting import (
                energy_to_tce,
                scope1_mass_balance,
                scope3_estimate,
                water_balance,
            )

            try:
                payload = (
                    scope1_mass_balance(args.inputs, args.outputs)
                    if args.action == "scope1_mass_balance"
                    else scope3_estimate(
                        args.categories,
                        scope2_electricity_mwh=args.scope2_electricity_mwh,
                        td_loss_rate=args.td_loss_rate,
                        grid_emission_factor_tco2e_per_mwh=args.grid_emission_factor_tco2e_per_mwh,
                    )
                    if args.action == "scope3"
                    else energy_to_tce(args.energy_lines)
                    if args.action == "energy_tce"
                    else water_balance(args.withdrawals, args.discharge)
                )
                return _format(payload, args.output_format)
            except Exception as exc:
                return ToolResult(output=f"Climate calculator failed: {exc}", is_error=True)

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
