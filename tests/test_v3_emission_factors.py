"""Tests for the v3 versioned emission-factor catalog."""

from __future__ import annotations

import pytest

from openharness.impact.climate_accounting import ActivityData
from openharness.impact.emission_factors import (
    EmissionFactorCatalogV2,
    apply_catalog_to_inventory,
    default_factor_catalog,
    factor_sensitivity,
    summarise_sensitivity,
)


def test_default_catalog_has_expected_publishers() -> None:
    catalog = default_factor_catalog()
    assert "DEFRA" in catalog.list_publishers()
    assert "EPA" in catalog.list_publishers()
    assert "IEA" in catalog.list_publishers()
    assert "defra-2025" in catalog.list_catalog_versions()
    assert any(r.revision_id == "iea-2025-grid-global" for r in catalog.revisions)


def test_factor_sensitivity_flags_wide_band_or_unverified() -> None:
    catalog = default_factor_catalog()
    revision = catalog.get("iea-2025-grid-global")
    activity = ActivityData(
        activity_type="electricity",
        value=10_000.0,
        unit="kwh",
        scope="scope2",
        verified=False,
    )
    result = factor_sensitivity(activity, revision)
    assert result.publisher == "IEA"
    assert result.central_kg_co2e == pytest.approx(10_000 * revision.factor.kg_co2e_per_unit, rel=1e-6)
    assert result.flagged is True
    assert result.range_pct >= 0.0


def test_apply_catalog_to_inventory_uses_named_version() -> None:
    catalog = default_factor_catalog()
    activities = [
        ActivityData(
            activity_type="electricity",
            value=5_000,
            unit="kwh",
            scope="scope2",
            method="location_based",
            verified=True,
        ),
    ]
    inventory = apply_catalog_to_inventory(
        company_name="Demo",
        reporting_period="FY2026",
        activities=activities,
        catalog=catalog,
        catalog_version="iea-2025",
    )
    assert inventory.company_name == "Demo"
    assert inventory.scope2_location_based_tco2e > 0
    assert "iea-2025" in inventory.factor_version


def test_apply_catalog_rejects_missing_version() -> None:
    catalog = default_factor_catalog()
    with pytest.raises(ValueError):
        apply_catalog_to_inventory(
            company_name="Demo",
            reporting_period="FY2026",
            activities=[],
            catalog=catalog,
            catalog_version="bogus",
        )


def test_summarise_sensitivity_reports_coverage() -> None:
    catalog = default_factor_catalog()
    revision = catalog.get("defra-2025-natural-gas")
    activities = [
        ActivityData(
            activity_type="natural_gas",
            value=1_000,
            unit="kwh",
            scope="scope1",
            verified=True,
        ),
        ActivityData(
            activity_type="natural_gas",
            value=500,
            unit="kwh",
            scope="scope1",
            verified=False,
        ),
    ]
    coverage = summarise_sensitivity(activities, [revision, revision])
    assert coverage.total_activities == 2
    assert 0 <= coverage.flagged_activities <= 2
    assert coverage.weighted_range_pct >= 0.0


def test_catalog_rejects_duplicate_revisions() -> None:
    catalog = default_factor_catalog()
    payload = catalog.revisions[0].model_dump()
    with pytest.raises(ValueError):
        EmissionFactorCatalogV2(revisions=[catalog.revisions[0], payload])
