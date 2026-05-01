"""Versioned emission-factor catalog (v3 Track 3.4, 3.8).

Builds on :mod:`openharness.impact.climate_accounting` by adding:

* a registry of named factor *revisions* with provenance metadata
  (publisher, vintage, geography, source URL),
* deterministic offline EPA / DEFRA / IEA snapshots so demos and tests
  work without network access,
* an uncertainty band (``low_kg_co2e_per_unit`` / ``high_kg_co2e_per_unit``)
  for sensitivity analysis,
* helpers to recompute an existing :class:`GHGInventory` against a
  specific catalog version and to flag scenarios where a meaningful
  share of the activity payload is unverified.

The module is intentionally pure-Python and dependency-light so it can
be embedded in CLI flows, FastAPI handlers, and MCP tool wrappers.
"""

from __future__ import annotations

from typing import Iterable, Literal

from pydantic import BaseModel, Field, field_validator

from openharness.impact.climate_accounting import (
    DEFAULT_EMISSION_FACTORS,
    ActivityData,
    EmissionFactor,
    GHGInventory,
    calculate_ghg_inventory,
)


Publisher = Literal["EPA", "DEFRA", "IEA", "IPCC", "OFFLINE_DEMO"]


class EmissionFactorRevision(BaseModel):
    """One emission factor in one catalog at one publisher version."""

    revision_id: str = Field(description="Stable ID, e.g. defra-2025-electricity-grid-uk")
    publisher: Publisher
    catalog_version: str = Field(description="Publisher catalog vintage, e.g. defra-2025")
    factor: EmissionFactor
    low_kg_co2e_per_unit: float = Field(ge=0, description="Lower uncertainty bound (kgCO2e/unit)")
    high_kg_co2e_per_unit: float = Field(ge=0, description="Upper uncertainty bound (kgCO2e/unit)")
    source_url: str = ""
    notes: str = ""

    @field_validator("revision_id")
    @classmethod
    def normalize_revision_id(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("revision_id is required")
        return cleaned

    def model_post_init(self, __context: object) -> None:
        if self.low_kg_co2e_per_unit > self.factor.kg_co2e_per_unit:
            raise ValueError(
                "low_kg_co2e_per_unit must be <= factor.kg_co2e_per_unit"
            )
        if self.high_kg_co2e_per_unit < self.factor.kg_co2e_per_unit:
            raise ValueError(
                "high_kg_co2e_per_unit must be >= factor.kg_co2e_per_unit"
            )


class EmissionFactorCatalogV2(BaseModel):
    """Versioned registry of :class:`EmissionFactorRevision` entries."""

    revisions: list[EmissionFactorRevision] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        ids = [r.revision_id for r in self.revisions]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"Duplicate revision_ids: {', '.join(duplicates)}")

    def list_publishers(self) -> list[Publisher]:
        return sorted({r.publisher for r in self.revisions})

    def list_catalog_versions(self) -> list[str]:
        return sorted({r.catalog_version for r in self.revisions})

    def by_publisher(self, publisher: Publisher) -> list[EmissionFactorRevision]:
        return [r for r in self.revisions if r.publisher == publisher]

    def get(self, revision_id: str) -> EmissionFactorRevision:
        normalized = revision_id.strip().lower()
        for revision in self.revisions:
            if revision.revision_id == normalized:
                return revision
        raise KeyError(f"Unknown emission-factor revision: {revision_id}")

    def factors_in_version(self, catalog_version: str) -> list[EmissionFactor]:
        target = catalog_version.strip().lower()
        return [r.factor for r in self.revisions if r.catalog_version.lower() == target]

    def add(self, revision: EmissionFactorRevision) -> None:
        if any(r.revision_id == revision.revision_id for r in self.revisions):
            raise ValueError(f"Revision already registered: {revision.revision_id}")
        self.revisions.append(revision)


# ---------------------------------------------------------------------------
# Offline catalog
# ---------------------------------------------------------------------------


def _r(
    revision_id: str,
    publisher: Publisher,
    catalog_version: str,
    base_factor_id: str,
    *,
    factor_kwargs: dict[str, str | float | int] | None = None,
    band_pct: float = 10.0,
    source_url: str = "",
) -> EmissionFactorRevision:
    """Build a revision off an existing :class:`EmissionFactor` template."""
    base = next(f for f in DEFAULT_EMISSION_FACTORS if f.factor_id == base_factor_id)
    payload = base.model_dump()
    if factor_kwargs:
        payload.update(factor_kwargs)
    factor = EmissionFactor.model_validate({
        **payload,
        "factor_id": f"{base.factor_id}::{catalog_version}",
        "version": catalog_version,
        "source": f"{publisher} {catalog_version} offline snapshot",
    })
    band = factor.kg_co2e_per_unit * band_pct / 100.0
    return EmissionFactorRevision(
        revision_id=revision_id,
        publisher=publisher,
        catalog_version=catalog_version,
        factor=factor,
        low_kg_co2e_per_unit=max(0.0, factor.kg_co2e_per_unit - band),
        high_kg_co2e_per_unit=factor.kg_co2e_per_unit + band,
        source_url=source_url,
        notes=f"Deterministic {publisher} offline snapshot for {catalog_version}.",
    )


def default_factor_catalog() -> EmissionFactorCatalogV2:
    """Return the offline EPA/DEFRA/IEA-style catalog used for demos and tests."""
    return EmissionFactorCatalogV2(revisions=[
        _r(
            "defra-2025-natural-gas",
            "DEFRA",
            "defra-2025",
            "fuel:natural_gas:kwh:global:2025",
            band_pct=8.0,
            source_url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
        ),
        _r(
            "defra-2025-diesel",
            "DEFRA",
            "defra-2025",
            "fuel:diesel:litre:global:2025",
            band_pct=10.0,
            source_url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
        ),
        _r(
            "epa-2025-natural-gas",
            "EPA",
            "epa-2025",
            "fuel:natural_gas:kwh:global:2025",
            factor_kwargs={"kg_co2e_per_unit": 0.181},
            band_pct=12.0,
            source_url="https://www.epa.gov/climateleadership/ghg-emission-factors-hub",
        ),
        _r(
            "ipcc-ar6-r410a",
            "IPCC",
            "ipcc-ar6",
            "refrigerant:r410a:kg:global:2025",
            factor_kwargs={"kg_co2e_per_unit": 1923.0},
            band_pct=15.0,
            source_url="https://www.ipcc.ch/assessment-report/ar6/",
        ),
        _r(
            "iea-2025-grid-global",
            "IEA",
            "iea-2025",
            "electricity:grid:kwh:global:2025",
            band_pct=10.0,
            source_url="https://www.iea.org/data-and-statistics",
        ),
        _r(
            "iea-2024-grid-global",
            "IEA",
            "iea-2024",
            "electricity:grid:kwh:global:2025",
            factor_kwargs={"kg_co2e_per_unit": 0.45, "source_year": 2024},
            band_pct=12.0,
            source_url="https://www.iea.org/data-and-statistics",
        ),
        _r(
            "iea-2025-renewable-market",
            "IEA",
            "iea-2025",
            "electricity:renewable:kwh:global:2025",
            band_pct=5.0,
            source_url="https://www.iea.org/data-and-statistics",
        ),
        _r(
            "offline-demo-2026-natural-gas",
            "OFFLINE_DEMO",
            "offline-demo-2026",
            "fuel:natural_gas:kwh:global:2025",
            band_pct=20.0,
        ),
    ])


# ---------------------------------------------------------------------------
# Sensitivity analysis
# ---------------------------------------------------------------------------


class FactorSensitivityResult(BaseModel):
    """Sensitivity output for one activity row."""

    revision_id: str
    publisher: Publisher
    catalog_version: str
    activity_value: float
    activity_unit: str
    central_kg_co2e: float
    low_kg_co2e: float
    high_kg_co2e: float
    range_pct: float = Field(description="(high-low)/central * 100")
    flagged: bool = Field(description="True when the band exceeds 20% of central or unverified")


def factor_sensitivity(
    activity: ActivityData | dict,
    revision: EmissionFactorRevision,
    *,
    flag_threshold_pct: float = 20.0,
) -> FactorSensitivityResult:
    """Compute the ±band emissions and flag wide / unverified results."""
    row = activity if isinstance(activity, ActivityData) else ActivityData.model_validate(activity)
    central = row.value * revision.factor.kg_co2e_per_unit
    low = row.value * revision.low_kg_co2e_per_unit
    high = row.value * revision.high_kg_co2e_per_unit
    range_pct = 0.0 if central == 0 else round((high - low) / central * 100, 2)
    flagged = range_pct >= flag_threshold_pct or not row.verified
    return FactorSensitivityResult(
        revision_id=revision.revision_id,
        publisher=revision.publisher,
        catalog_version=revision.catalog_version,
        activity_value=row.value,
        activity_unit=row.unit,
        central_kg_co2e=round(central, 4),
        low_kg_co2e=round(low, 4),
        high_kg_co2e=round(high, 4),
        range_pct=range_pct,
        flagged=flagged,
    )


def apply_catalog_to_inventory(
    *,
    company_name: str,
    reporting_period: str,
    activities: Iterable[ActivityData | dict],
    catalog: EmissionFactorCatalogV2,
    catalog_version: str,
) -> GHGInventory:
    """Recompute a GHG inventory using all factors in a named catalog version."""
    factors = catalog.factors_in_version(catalog_version)
    if not factors:
        raise ValueError(f"No factors registered for catalog version: {catalog_version}")
    return calculate_ghg_inventory(
        company_name=company_name,
        reporting_period=reporting_period,
        activities=list(activities),
        factors=factors,
    )


class SensitivityCoverage(BaseModel):
    """Aggregate sensitivity coverage across an activity payload."""

    total_activities: int
    flagged_activities: int
    flagged_pct: float
    weighted_range_pct: float


def summarise_sensitivity(
    activities: Iterable[ActivityData | dict],
    revisions: Iterable[EmissionFactorRevision],
    *,
    flag_threshold_pct: float = 20.0,
) -> SensitivityCoverage:
    """Roll factor sensitivities up to a payload-level coverage view."""
    pairs = list(zip(list(activities), list(revisions), strict=True))
    if not pairs:
        return SensitivityCoverage(
            total_activities=0,
            flagged_activities=0,
            flagged_pct=0.0,
            weighted_range_pct=0.0,
        )
    results = [factor_sensitivity(a, r, flag_threshold_pct=flag_threshold_pct) for a, r in pairs]
    total = len(results)
    flagged = sum(1 for r in results if r.flagged)
    weight_sum = sum(r.central_kg_co2e for r in results)
    if weight_sum > 0:
        weighted = sum(r.range_pct * r.central_kg_co2e for r in results) / weight_sum
    else:
        weighted = sum(r.range_pct for r in results) / total
    return SensitivityCoverage(
        total_activities=total,
        flagged_activities=flagged,
        flagged_pct=round(100 * flagged / total, 2),
        weighted_range_pct=round(weighted, 2),
    )


__all__ = [
    "EmissionFactorCatalogV2",
    "EmissionFactorRevision",
    "FactorSensitivityResult",
    "Publisher",
    "SensitivityCoverage",
    "apply_catalog_to_inventory",
    "default_factor_catalog",
    "factor_sensitivity",
    "summarise_sensitivity",
]
