"""Tests for Scope 1 and Scope 2 GHG accounting."""

from __future__ import annotations

import pytest

from openharness.impact.climate_accounting import (
    ActivityData,
    EmissionFactor,
    calculate_activity_emissions,
    calculate_ghg_inventory,
)


def test_calculate_scope1_activity_emissions_with_factor_metadata() -> None:
    result = calculate_activity_emissions({
        "activity_type": "diesel",
        "value": 1000,
        "unit": "litre",
        "scope": "scope1",
        "source": "fuel invoices",
        "evidence_refs": ["evidence://fuel"],
    })

    assert result.scope == "scope1"
    assert result.method == "direct_combustion"
    assert result.factor_id == "fuel:diesel:litre:global:2025"
    assert result.factor_source
    assert result.factor_year == 2025
    assert result.tco2e == pytest.approx(2.68)
    assert result.data_quality_score == 4
    assert result.evidence_refs == ["evidence://fuel"]


def test_calculate_scope2_location_and_market_inventory() -> None:
    inventory = calculate_ghg_inventory(
        company_name="ClimateCo",
        reporting_period="FY2025",
        activities=[
            {"activity_type": "natural_gas", "value": 10000, "unit": "kwh", "scope": "scope1"},
            {
                "activity_type": "electricity",
                "value": 20000,
                "unit": "kwh",
                "scope": "scope2",
                "method": "location_based",
                "source": "utility bill",
            },
            {
                "activity_type": "electricity",
                "value": 20000,
                "unit": "kwh",
                "scope": "scope2",
                "method": "market_based",
                "factor_id": "electricity:renewable:kwh:global:2025",
                "verified": True,
            },
        ],
    )

    assert inventory.company_name == "ClimateCo"
    assert inventory.scope1_tco2e == pytest.approx(1.84)
    assert inventory.scope2_location_based_tco2e == pytest.approx(8.4)
    assert inventory.scope2_market_based_tco2e == pytest.approx(0.0)
    assert inventory.total_scope1_2_location_based_tco2e == pytest.approx(10.24)
    assert inventory.total_scope1_2_market_based_tco2e == pytest.approx(1.84)
    assert inventory.weighted_data_quality_score > 0
    assert inventory.factor_version == "offline-demo-2026"


def test_custom_region_factor_is_preferred() -> None:
    custom = EmissionFactor(
        factor_id="electricity:grid:kwh:ke:2025",
        name="Kenya grid electricity",
        scope="scope2",
        activity_type="electricity",
        unit="kwh",
        kg_co2e_per_unit=0.1,
        source="Kenya grid factor",
        source_year=2025,
        region="ke",
        method="location_based",
    )
    result = calculate_activity_emissions(
        ActivityData(
            activity_type="electricity",
            value=1000,
            unit="kwh",
            scope="scope2",
            region="ke",
            method="location_based",
        ),
        factors=[custom],
    )

    assert result.factor_id == "electricity:grid:kwh:ke:2025"
    assert result.tco2e == pytest.approx(0.1)
    assert result.data_quality_score == 4


def test_unknown_factor_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown emission factor"):
        calculate_activity_emissions({
            "activity_type": "electricity",
            "value": 1,
            "unit": "kwh",
            "scope": "scope2",
            "factor_id": "missing",
        })


def test_missing_factor_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="No emission factor"):
        calculate_activity_emissions({
            "activity_type": "coal",
            "value": 1,
            "unit": "tonne",
            "scope": "scope1",
        })
