"""Scope 1 and Scope 2 GHG accounting helpers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


Scope = Literal["scope1", "scope2"]
Scope2Method = Literal["location_based", "market_based"]


class EmissionFactor(BaseModel):
    """One emission factor in kgCO2e per activity unit."""

    factor_id: str
    name: str
    scope: Scope
    activity_type: str
    unit: str
    kg_co2e_per_unit: float = Field(ge=0)
    source: str
    source_year: int
    region: str = "global"
    method: Scope2Method | Literal["direct_combustion", "fugitive"] = "direct_combustion"
    version: str = "offline-demo-2026"


class ActivityData(BaseModel):
    """Activity data used to calculate Scope 1 or Scope 2 emissions."""

    activity_type: str
    value: float = Field(ge=0)
    unit: str
    scope: Scope
    region: str = "global"
    factor_id: str = ""
    source: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    verified: bool = False
    method: Scope2Method | Literal["direct_combustion", "fugitive"] | None = None

    @field_validator("activity_type", "unit", "region")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return str(value).strip().lower()


class EmissionResult(BaseModel):
    """Calculated emissions for one activity row."""

    activity_type: str
    scope: Scope
    method: str
    activity_value: float
    activity_unit: str
    factor_id: str
    factor_source: str
    factor_year: int
    factor_version: str
    kg_co2e: float
    tco2e: float
    data_quality_score: int = Field(ge=1, le=5)
    evidence_refs: list[str] = Field(default_factory=list)


class GHGInventory(BaseModel):
    """Scope 1/2 emissions rollup."""

    company_name: str
    reporting_period: str
    results: list[EmissionResult] = Field(default_factory=list)
    scope1_tco2e: float = 0.0
    scope2_location_based_tco2e: float = 0.0
    scope2_market_based_tco2e: float = 0.0
    total_scope1_2_location_based_tco2e: float = 0.0
    total_scope1_2_market_based_tco2e: float = 0.0
    weighted_data_quality_score: float = 0.0
    factor_version: str = ""


DEFAULT_EMISSION_FACTORS: list[EmissionFactor] = [
    EmissionFactor(
        factor_id="fuel:natural_gas:kwh:global:2025",
        name="Natural gas combustion",
        scope="scope1",
        activity_type="natural_gas",
        unit="kwh",
        kg_co2e_per_unit=0.184,
        source="UK DEFRA-style offline factor snapshot",
        source_year=2025,
    ),
    EmissionFactor(
        factor_id="fuel:diesel:litre:global:2025",
        name="Diesel combustion",
        scope="scope1",
        activity_type="diesel",
        unit="litre",
        kg_co2e_per_unit=2.68,
        source="EPA/DEFRA-style offline factor snapshot",
        source_year=2025,
    ),
    EmissionFactor(
        factor_id="refrigerant:r410a:kg:global:2025",
        name="R410A fugitive refrigerant",
        scope="scope1",
        activity_type="r410a",
        unit="kg",
        kg_co2e_per_unit=2088.0,
        source="IPCC AR4-style GWP snapshot",
        source_year=2025,
        method="fugitive",
    ),
    EmissionFactor(
        factor_id="electricity:grid:kwh:global:2025",
        name="Grid electricity location-based",
        scope="scope2",
        activity_type="electricity",
        unit="kwh",
        kg_co2e_per_unit=0.42,
        source="IEA-style global grid average offline snapshot",
        source_year=2025,
        method="location_based",
    ),
    EmissionFactor(
        factor_id="electricity:renewable:kwh:global:2025",
        name="Contracted renewable electricity market-based",
        scope="scope2",
        activity_type="electricity",
        unit="kwh",
        kg_co2e_per_unit=0.0,
        source="Market-based renewable contract placeholder",
        source_year=2025,
        method="market_based",
    ),
]


def _factor_index(factors: list[EmissionFactor] | None = None) -> dict[str, EmissionFactor]:
    return {factor.factor_id: factor for factor in (factors or DEFAULT_EMISSION_FACTORS)}


def _find_factor(activity: ActivityData, factors: list[EmissionFactor] | None = None) -> EmissionFactor:
    by_id = _factor_index(factors)
    if activity.factor_id:
        factor = by_id.get(activity.factor_id)
        if factor is None:
            raise ValueError(f"Unknown emission factor: {activity.factor_id}")
        return factor

    candidates = [
        factor for factor in (factors or DEFAULT_EMISSION_FACTORS)
        if factor.scope == activity.scope
        and factor.activity_type == activity.activity_type
        and factor.unit == activity.unit
        and (activity.method is None or factor.method == activity.method)
        and factor.region in {activity.region, "global"}
    ]
    if not candidates:
        raise ValueError(
            f"No emission factor for {activity.scope}/{activity.activity_type}/{activity.unit}"
        )
    candidates.sort(key=lambda factor: (factor.region == activity.region, factor.source_year), reverse=True)
    return candidates[0]


def _data_quality_score(activity: ActivityData, factor: EmissionFactor) -> int:
    score = 5
    if activity.verified:
        score -= 2
    elif activity.source or activity.evidence_refs:
        score -= 1
    if factor.region == activity.region and activity.region != "global":
        score -= 1
    if activity.factor_id:
        score -= 1
    return max(1, min(5, score))


def calculate_activity_emissions(
    activity: ActivityData | dict,
    *,
    factors: list[EmissionFactor] | None = None,
) -> EmissionResult:
    """Calculate emissions for one Scope 1 or Scope 2 activity."""
    row = activity if isinstance(activity, ActivityData) else ActivityData.model_validate(activity)
    factor = _find_factor(row, factors)
    kg = row.value * factor.kg_co2e_per_unit
    return EmissionResult(
        activity_type=row.activity_type,
        scope=row.scope,
        method=str(row.method or factor.method),
        activity_value=row.value,
        activity_unit=row.unit,
        factor_id=factor.factor_id,
        factor_source=factor.source,
        factor_year=factor.source_year,
        factor_version=factor.version,
        kg_co2e=round(kg, 4),
        tco2e=round(kg / 1000, 4),
        data_quality_score=_data_quality_score(row, factor),
        evidence_refs=row.evidence_refs,
    )


def calculate_ghg_inventory(
    *,
    company_name: str,
    reporting_period: str,
    activities: list[ActivityData | dict],
    factors: list[EmissionFactor] | None = None,
) -> GHGInventory:
    """Calculate a Scope 1/2 GHG inventory from activity rows."""
    results = [calculate_activity_emissions(activity, factors=factors) for activity in activities]
    scope1 = round(sum(r.tco2e for r in results if r.scope == "scope1"), 4)
    scope2_location = round(sum(
        r.tco2e for r in results
        if r.scope == "scope2" and r.method == "location_based"
    ), 4)
    scope2_market = round(sum(
        r.tco2e for r in results
        if r.scope == "scope2" and r.method == "market_based"
    ), 4)
    total_tco2e = sum(r.tco2e for r in results)
    weighted_dqs = 0.0
    if total_tco2e > 0:
        weighted_dqs = round(sum(r.data_quality_score * r.tco2e for r in results) / total_tco2e, 2)
    elif results:
        weighted_dqs = round(sum(r.data_quality_score for r in results) / len(results), 2)
    versions = sorted({r.factor_version for r in results})
    return GHGInventory(
        company_name=company_name,
        reporting_period=reporting_period,
        results=results,
        scope1_tco2e=scope1,
        scope2_location_based_tco2e=scope2_location,
        scope2_market_based_tco2e=scope2_market,
        total_scope1_2_location_based_tco2e=round(scope1 + scope2_location, 4),
        total_scope1_2_market_based_tco2e=round(scope1 + scope2_market, 4),
        weighted_data_quality_score=weighted_dqs,
        factor_version=", ".join(versions),
    )


__all__ = [
    "ActivityData",
    "DEFAULT_EMISSION_FACTORS",
    "EmissionFactor",
    "EmissionResult",
    "GHGInventory",
    "calculate_activity_emissions",
    "calculate_ghg_inventory",
]
