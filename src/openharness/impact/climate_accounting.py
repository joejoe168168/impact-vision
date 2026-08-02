"""Scope 1 and Scope 2 GHG accounting helpers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Scope = Literal["scope1", "scope2"]
Scope2Method = Literal["location_based", "market_based"]
CertificateStatus = Literal["valid", "invalid", "pending", "unknown"]


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
    activity_category: str = ""
    facility: str = ""

    @field_validator("activity_type", "unit", "region", "activity_category", "facility")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return str(value).strip().lower()


class RenewableCertificate(BaseModel):
    """A renewable-energy certificate used for market-based Scope 2 reporting."""

    certificate_type: str
    quantity_mwh: float = Field(ge=0)
    verification_status: CertificateStatus = "unknown"
    region: str = "global"
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("certificate_type", "region")
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
    activity_category: str = ""
    facility: str = ""


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
    scope1_by_category: dict[str, float] = Field(default_factory=dict)
    scope2_by_category: dict[str, float] = Field(default_factory=dict)
    scope3_by_category: dict[str, float] = Field(default_factory=dict)
    scope3_tco2e: float = 0.0
    total_carbon_footprint_location_based_tco2e: float = 0.0
    total_carbon_footprint_market_based_tco2e: float = 0.0
    annual_revenue_million_cny: float | None = Field(default=None, ge=0)
    carbon_intensity_location_based_tco2e_per_million_cny: float | None = None
    carbon_intensity_market_based_tco2e_per_million_cny: float | None = None
    valid_certificate_coverage_mwh: float = 0.0
    comparable_years: list[dict[str, Any]] = Field(default_factory=list)


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


def _find_factor(
    activity: ActivityData, factors: list[EmissionFactor] | None = None
) -> EmissionFactor:
    by_id = _factor_index(factors)
    if activity.factor_id:
        factor = by_id.get(activity.factor_id)
        if factor is None:
            raise ValueError(f"Unknown emission factor: {activity.factor_id}")
        return factor

    candidates = [
        factor
        for factor in (factors or DEFAULT_EMISSION_FACTORS)
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
    candidates.sort(
        key=lambda factor: (factor.region == activity.region, factor.source_year), reverse=True
    )
    return candidates[0]


def _data_quality_score(activity: ActivityData, factor: EmissionFactor) -> int:
    score = 3
    if activity.verified:
        score += 1
    elif activity.source or activity.evidence_refs:
        score += 1
    if factor.region == activity.region and activity.region != "global":
        score += 1
    if activity.factor_id:
        score += 1
    return max(1, min(5, score))


def _to_mwh(value: float, unit: str) -> float:
    """Convert an electricity activity value to MWh."""
    normalized = unit.strip().lower()
    if normalized == "mwh":
        return float(value)
    if normalized == "kwh":
        return float(value) / 1000
    raise ValueError(f"Electricity activity must use kwh or mwh, not {unit}")


def _year_from_period(reporting_period: str) -> int | None:
    import re

    match = re.search(r"(19|20)\d{2}", reporting_period)
    return int(match.group(0)) if match else None


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
        activity_category=row.activity_category,
        facility=row.facility,
    )


def calculate_ghg_inventory(
    *,
    company_name: str,
    reporting_period: str,
    activities: list[ActivityData | dict],
    factors: list[EmissionFactor] | None = None,
    certificates: list[RenewableCertificate | dict] | None = None,
    annual_revenue_million_cny: float | None = None,
    scope3_categories: dict[int, dict] | None = None,
    historical_years: list[dict] | None = None,
) -> GHGInventory:
    """Calculate a Scope 1/2 inventory, with optional OHESG-style extensions.

    The original Scope 1/2 behaviour remains available.  Passing
    ``scope3_categories`` adds selected Scope 3 categories, ``certificates``
    calculates a certificate-adjusted market-based Scope 2 result, and
    ``annual_revenue_million_cny`` adds a revenue intensity denominator.
    """
    if annual_revenue_million_cny is not None and annual_revenue_million_cny < 0:
        raise ValueError("annual_revenue_million_cny cannot be negative")

    rows = [
        activity if isinstance(activity, ActivityData) else ActivityData.model_validate(activity)
        for activity in activities
    ]
    results = [calculate_activity_emissions(activity, factors=factors) for activity in rows]
    scope1 = round(sum(r.tco2e for r in results if r.scope == "scope1"), 4)
    scope2_location = round(
        sum(r.tco2e for r in results if r.scope == "scope2" and r.method == "location_based"), 4
    )
    explicit_scope2_market = round(
        sum(r.tco2e for r in results if r.scope == "scope2" and r.method == "market_based"), 4
    )

    scope1_by_category: dict[str, float] = {}
    scope2_by_category: dict[str, float] = {}
    for row, result in zip(rows, results, strict=True):
        if result.scope == "scope1":
            category = row.activity_category or row.activity_type
            scope1_by_category[category] = round(scope1_by_category.get(category, 0.0) + result.tco2e, 4)
        elif result.scope == "scope2":
            category = row.activity_category or row.activity_type
            scope2_by_category[category] = round(scope2_by_category.get(category, 0.0) + result.tco2e, 4)

    location_electricity = [
        (row, result)
        for row, result in zip(rows, results, strict=True)
        if row.scope == "scope2"
        and row.activity_type == "electricity"
        and result.method == "location_based"
    ]
    location_electricity_mwh = sum(_to_mwh(row.value, row.unit) for row, _ in location_electricity)
    location_electricity_tco2e = sum(result.tco2e for _, result in location_electricity)
    non_electricity_location_tco2e = round(
        sum(
            result.tco2e
            for row, result in zip(rows, results, strict=True)
            if row.scope == "scope2"
            and result.method == "location_based"
            and row.activity_type != "electricity"
        ),
        4,
    )
    explicit_market_rows = any(
        row.scope == "scope2" and result.method == "market_based"
        for row, result in zip(rows, results, strict=True)
    )

    certificate_rows = [
        certificate
        if isinstance(certificate, RenewableCertificate)
        else RenewableCertificate.model_validate(certificate)
        for certificate in (certificates or [])
    ]
    valid_certificate_coverage = round(
        min(
            location_electricity_mwh,
            sum(
                certificate.quantity_mwh
                for certificate in certificate_rows
                if certificate.verification_status == "valid"
            ),
        ),
        4,
    )
    if certificate_rows and location_electricity_mwh > 0:
        average_grid_factor = location_electricity_tco2e / location_electricity_mwh
        adjusted_electricity = max(
            0.0, location_electricity_tco2e - valid_certificate_coverage * average_grid_factor
        )
        scope2_market = round(
            explicit_scope2_market + non_electricity_location_tco2e + adjusted_electricity, 4
        )
    elif explicit_market_rows:
        # Preserve the pre-existing contract when the caller supplies an
        # explicit market-based activity row (for example, a supplier factor).
        scope2_market = round(explicit_scope2_market + non_electricity_location_tco2e, 4)
    else:
        # With no market-based row, the location result is the best available
        # market proxy rather than silently reporting zero.
        scope2_market = round(scope2_location, 4)

    scope3_payload: dict[str, Any] | None = None
    if scope3_categories is not None:
        electricity_rows = [
            (row, result)
            for row, result in zip(rows, results, strict=True)
            if row.scope == "scope2" and row.activity_type == "electricity"
        ]
        if location_electricity:
            electricity_rows = location_electricity
        scope2_electricity_mwh = sum(_to_mwh(row.value, row.unit) for row, _ in electricity_rows)
        grid_factor = (
            location_electricity_tco2e / location_electricity_mwh
            if location_electricity_mwh > 0
            else None
        )
        scope3_payload = scope3_estimate(
            scope3_categories,
            scope2_electricity_mwh=scope2_electricity_mwh if scope2_electricity_mwh > 0 else None,
            grid_emission_factor_tco2e_per_mwh=grid_factor,
        )
    scope3_total = float(scope3_payload["total_tco2e"]) if scope3_payload else 0.0

    inventory_tco2e = sum(r.tco2e for r in results)
    weighted_dqs = 0.0
    if inventory_tco2e > 0:
        weighted_dqs = round(
            sum(r.data_quality_score * r.tco2e for r in results) / inventory_tco2e, 2
        )
    elif results:
        weighted_dqs = round(sum(r.data_quality_score for r in results) / len(results), 2)
    versions = sorted({r.factor_version for r in results})
    total_location = round(scope1 + scope2_location + scope3_total, 4)
    total_market = round(scope1 + scope2_market + scope3_total, 4)
    intensity_location = (
        round(total_location / annual_revenue_million_cny, 4)
        if annual_revenue_million_cny
        else None
    )
    intensity_market = (
        round(total_market / annual_revenue_million_cny, 4)
        if annual_revenue_million_cny
        else None
    )
    comparable = []
    if historical_years:
        current_year = _year_from_period(reporting_period)
        comparison_rows = list(historical_years)
        if current_year is not None:
            comparison_rows.append(
                {
                    "year": current_year,
                    "scope1_tco2e": scope1,
                    "scope2_tco2e": scope2_market,
                    "scope3_tco2e": scope3_total,
                }
            )
        comparable = three_year_comparison(comparison_rows)["years"]

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
        scope1_by_category=scope1_by_category,
        scope2_by_category=scope2_by_category,
        scope3_by_category=(
            {str(row["category"]): row["tco2e"] for row in scope3_payload["categories"]}
            if scope3_payload
            else {}
        ),
        scope3_tco2e=round(scope3_total, 4),
        total_carbon_footprint_location_based_tco2e=total_location,
        total_carbon_footprint_market_based_tco2e=total_market,
        annual_revenue_million_cny=annual_revenue_million_cny,
        carbon_intensity_location_based_tco2e_per_million_cny=intensity_location,
        carbon_intensity_market_based_tco2e_per_million_cny=intensity_market,
        valid_certificate_coverage_mwh=valid_certificate_coverage,
        comparable_years=comparable,
    )


def scope1_mass_balance(inputs: list[dict], outputs: list[dict], gwp: str = "AR6") -> dict:
    from openharness.impact.emission_factors import AR6_GWP, AR6_GWP_PROVENANCE

    if gwp != "AR6":
        raise ValueError("Only the version-pinned AR6 GWP set is supported")

    def carbon_by_gas(rows: list[dict]) -> dict[str, float]:
        balances: dict[str, float] = {}
        for row in rows:
            mass = float(row.get("mass", 0))
            carbon_content = float(row.get("carbon_content", 0))
            if mass < 0 or carbon_content < 0:
                raise ValueError("Mass and carbon_content must be non-negative")
            gas = str(row.get("gas", "CO2")).upper()
            if gas not in AR6_GWP:
                raise ValueError(f"Unsupported AR6 gas: {gas}")
            balances[gas] = balances.get(gas, 0.0) + mass * carbon_content
        return balances

    input_carbon = carbon_by_gas(inputs)
    output_carbon = carbon_by_gas(outputs)
    gases = sorted(set(input_carbon) | set(output_carbon))
    net_by_gas = {
        gas: input_carbon.get(gas, 0.0) - output_carbon.get(gas, 0.0) for gas in gases
    }
    net_carbon = sum(net_by_gas.values())
    emissions = sum(net_by_gas[gas] * 44 / 12 * AR6_GWP[gas] for gas in gases)
    return {
        "emissions_tco2e": round(emissions, 6),
        "net_carbon_mass": net_carbon,
        "net_carbon_mass_by_gas": net_by_gas,
        "formula": "(sum(M_in*CC_in)-sum(M_out*CC_out))*44/12*GWP",
        "streams": {"inputs": inputs, "outputs": outputs},
        "factors_used": [AR6_GWP_PROVENANCE],
        "sources": [AR6_GWP_PROVENANCE["source"]],
    }


def _scope3_factor_ids(item: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    if item.get("factor_id"):
        ids.append(str(item["factor_id"]))
    for row in item.get("rows", []):
        if row.get("factor_id"):
            ids.append(str(row["factor_id"]))
    return ids or ["caller-supplied"]


def _scope3_item_value(
    category: int,
    item: dict[str, Any],
    *,
    default_td_loss_rate: float,
) -> tuple[float, str, str]:
    """Return tCO2e, method, and the formula used for one Scope 3 category."""
    if category == 1 and "spend" in item:
        value = float(item.get("spend", 0)) * float(item.get("factor", 0))
        return value, "eeio_spend", "spend * emission factor (tCO2e/CNY)"

    if category == 3 and "electricity_mwh" in item:
        loss_rate = float(
            item.get("loss_rate", item.get("td_loss_rate", default_td_loss_rate))
        )
        if not 0 <= loss_rate <= 1:
            raise ValueError("Scope 3 category 3 loss_rate must be between 0 and 1")
        value = (
            float(item.get("electricity_mwh", 0))
            * loss_rate
            * float(item.get("grid_factor", item.get("factor", 0)))
        )
        return value, "td_loss", "electricity_mwh * T&D loss rate * grid emission factor"

    if category in {4, 9} and "rows" in item:
        value = sum(
            float(row.get("weight_tonnes", row.get("weight", 0)))
            * float(row.get("distance_km", row.get("distance", 0)))
            * float(row.get("factor", 0))
            for row in item.get("rows", [])
        )
        return value, "tonne_km", "weight_tonnes * distance_km * emission factor"

    if category == 5 and "rows" in item:
        value = sum(
            float(row.get("quantity_tonnes", row.get("quantity", 0)))
            * float(row.get("factor", 0))
            for row in item.get("rows", [])
        )
        return value, "waste_quantity", "waste_tonnes * emission factor"

    value = float(item.get("activity", 0)) * float(item.get("factor", 0))
    return value, str(item.get("method", "activity_factor")), "activity * emission factor"


def scope3_estimate(
    categories: dict[int, dict] | None = None,
    *,
    scope2_electricity_mwh: float | None = None,
    td_loss_rate: float | None = None,
    grid_emission_factor_tco2e_per_mwh: float | None = None,
) -> dict:
    """Estimate all 15 GHG Protocol Scope 3 categories.

    The original ``activity * factor`` payload remains supported.  The
    manufacturing-oriented rows used by the OH ESG calculator are also
    supported: category 1 spend, category 3 electricity T&D losses, category
    4/9 tonne-km transport, and category 5 waste quantity.
    """
    from openharness.impact.emission_factors import DEFAULT_TD_LOSS_RATE

    categories = categories or {}
    effective_td_loss_rate = DEFAULT_TD_LOSS_RATE if td_loss_rate is None else float(td_loss_rate)
    normalized_categories = {int(category): item for category, item in categories.items()}
    invalid = sorted(set(normalized_categories) - set(range(1, 16)))
    if invalid:
        raise ValueError(f"Scope 3 categories must be 1..15: {invalid}")
    if scope2_electricity_mwh is not None and scope2_electricity_mwh < 0:
        raise ValueError("scope2_electricity_mwh cannot be negative")
    if grid_emission_factor_tco2e_per_mwh is not None and grid_emission_factor_tco2e_per_mwh < 0:
        raise ValueError("grid_emission_factor_tco2e_per_mwh cannot be negative")

    auto_category_3 = (
        scope2_electricity_mwh is not None
        and grid_emission_factor_tco2e_per_mwh is not None
        and 3 not in normalized_categories
    )
    if auto_category_3:
        normalized_categories[3] = {
            "electricity_mwh": scope2_electricity_mwh,
            "loss_rate": effective_td_loss_rate,
            "grid_factor": grid_emission_factor_tco2e_per_mwh,
            "factor_id": "world-bank-td-loss-plus-grid-factor",
        }

    rows = []
    factor_ids: list[str] = []
    for category in range(1, 16):
        item = normalized_categories.get(category, {})
        value, method, formula = _scope3_item_value(
            category, item, default_td_loss_rate=effective_td_loss_rate
        )
        if category in normalized_categories:
            factor_ids.extend(_scope3_factor_ids(item))
        rows.append(
            {
                "category": category,
                "tco2e": round(value, 6),
                "method": method,
                "formula": formula,
                "reported": category in normalized_categories,
            }
        )

    sources = ["GHG Protocol Scope 3 Standard"]
    if auto_category_3:
        from openharness.impact.emission_factors import TD_LOSS_PROVENANCE

        factor_ids.append(TD_LOSS_PROVENANCE["id"])
        sources.append(TD_LOSS_PROVENANCE["source"])
    return {
        "categories": rows,
        "total_tco2e": round(sum(row["tco2e"] for row in rows), 6),
        "formula": "category-specific activity data * emission factor",
        "category_count": 15,
        "factors_used": sorted(set(factor_ids)),
        "sources": sources,
    }


def three_year_comparison(years: list[dict]) -> dict:
    """Build comparable annual Scope 1/2/3 totals and YoY changes."""
    normalized: list[dict[str, Any]] = []
    seen_years: set[int] = set()
    for item in years:
        year = int(item["year"])
        if year in seen_years:
            raise ValueError(f"Duplicate comparison year: {year}")
        seen_years.add(year)
        scope1 = float(item.get("scope1_tco2e", item.get("scope1", 0)))
        scope2 = float(item.get("scope2_tco2e", item.get("scope2", 0)))
        scope3 = float(item.get("scope3_tco2e", item.get("scope3", 0)))
        total = float(item.get("total_tco2e", scope1 + scope2 + scope3))
        if min(scope1, scope2, scope3, total) < 0:
            raise ValueError("Comparable emissions cannot be negative")
        normalized.append(
            {
                "year": year,
                "scope1_tco2e": round(scope1, 6),
                "scope2_tco2e": round(scope2, 6),
                "scope3_tco2e": round(scope3, 6),
                "total_tco2e": round(total, 6),
                "yoy_change_pct": None,
            }
        )
    normalized.sort(key=lambda row: row["year"], reverse=True)
    for index, row in enumerate(normalized[:-1]):
        prior = normalized[index + 1]["total_tco2e"]
        row["yoy_change_pct"] = round(
            ((row["total_tco2e"] - prior) / prior) * 100, 2
        ) if prior else None
    return {
        "years": normalized,
        "current_year": normalized[0]["year"] if normalized else None,
        "year_count": len(normalized),
        "sources": ["GHG Protocol Corporate Standard", "ISO 14064-1"],
    }


def energy_to_tce(energy_lines: list[dict]) -> dict:
    from openharness.impact.emission_factors import GBT_2589_NCV_KJ_PER_KG, GBT_2589_PROVENANCE

    rows = []
    total = clean = 0.0
    for item in energy_lines:
        fuel = str(item["fuel"]).strip().lower()
        try:
            ncv = float(item.get("ncv_kj_per_kg", GBT_2589_NCV_KJ_PER_KG[fuel]))
        except KeyError as exc:
            raise ValueError(f"Unknown GB/T 2589 fuel: {fuel}") from exc
        quantity = float(item.get("quantity_kg", item.get("quantity", 0)))
        if quantity < 0 or ncv < 0:
            raise ValueError("Energy quantity and NCV must be non-negative")
        tce = quantity * ncv / 29307.6 / 1000
        total += tce
        clean += tce if item.get("clean_energy", False) else 0
        rows.append({"fuel": fuel, "tce": round(tce, 6), "ncv": ncv})
    denominator = float(
        next(
            (
                item.get("revenue", item.get("output", 0))
                for item in energy_lines
                if item.get("revenue") or item.get("output")
            ),
            0,
        )
    )
    return {
        "lines": rows,
        "total_tce": round(total, 6),
        "clean_energy_share_pct": round(100 * clean / total, 2) if total else 0,
        "intensity": round(total / denominator, 6) if denominator else None,
        "formula": "quantity_kg * NCV / 29307.6 / 1000",
        "factors_used": [GBT_2589_PROVENANCE],
        "sources": [GBT_2589_PROVENANCE["source"]],
    }


def water_balance(withdrawals: list[dict], discharge: float) -> dict:
    volumes = []
    for item in withdrawals:
        volume = float(item.get("volume", 0))
        if volume < 0:
            raise ValueError("Withdrawal volumes must be non-negative")
        volumes.append((item, volume))
    discharge = float(discharge)
    if discharge < 0:
        raise ValueError("discharge must be non-negative")
    total = sum(volume for _, volume in volumes)
    consumption = total - discharge
    if consumption < 0:
        raise ValueError("discharge cannot exceed withdrawals")
    non_conventional_types = {"reclaimed", "rain", "desalinated", "mine"}
    non_conventional = sum(
        volume
        for item, volume in volumes
        if str(item.get("source_type", "")).strip().lower() in non_conventional_types
    )
    reused = sum(volume for item, volume in volumes if item.get("reused"))
    denominator = float(
        next(
            (
                item.get("revenue", item.get("output", 0))
                for item in withdrawals
                if item.get("revenue") or item.get("output")
            ),
            0,
        )
    )
    return {
        "withdrawal": total,
        "discharge": float(discharge),
        "consumption": consumption,
        "conventional": total - non_conventional,
        "non_conventional": non_conventional,
        "reuse_rate_pct": round(100 * reused / total, 2) if total else 0,
        "intensity": round(total / denominator, 6) if denominator else None,
        "formula": "consumption = sum(withdrawals) - discharge",
        "factors_used": [],
        "sources": ["GRI 303 water balance"],
    }


__all__ = [
    "ActivityData",
    "DEFAULT_EMISSION_FACTORS",
    "EmissionFactor",
    "EmissionResult",
    "GHGInventory",
    "RenewableCertificate",
    "calculate_activity_emissions",
    "calculate_ghg_inventory",
    "scope1_mass_balance",
    "scope3_estimate",
    "three_year_comparison",
    "energy_to_tce",
    "water_balance",
]
