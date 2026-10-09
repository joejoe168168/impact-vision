"""Tests for Scope 1 and Scope 2 GHG accounting."""

from __future__ import annotations

import pytest

from impact_vision.impact.climate_accounting import (
    ActivityData,
    EmissionFactor,
    calculate_activity_emissions,
    calculate_ghg_inventory,
    energy_to_tce,
    scope3_estimate,
    three_year_comparison,
    water_balance,
    scope1_mass_balance,
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


def test_verified_activity_with_explicit_factor_scores_high_quality() -> None:
    result = calculate_activity_emissions({
        "activity_type": "electricity",
        "value": 1000,
        "unit": "kwh",
        "scope": "scope2",
        "method": "market_based",
        "factor_id": "electricity:renewable:kwh:global:2025",
        "verified": True,
    })
    assert result.data_quality_score == 5


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


def test_ohesg_style_inventory_adds_certificates_scope3_intensity_and_categories() -> None:
    inventory = calculate_ghg_inventory(
        company_name="ManufacturingCo",
        reporting_period="FY2025",
        annual_revenue_million_cny=100,
        activities=[
            {
                "activity_type": "diesel",
                "activity_category": "mobile_combustion",
                "value": 1000,
                "unit": "litre",
                "scope": "scope1",
            },
            {
                "activity_type": "electricity",
                "activity_category": "purchased_electricity",
                "value": 2000,
                "unit": "kwh",
                "scope": "scope2",
                "method": "location_based",
            },
        ],
        certificates=[
            {
                "certificate_type": "i-rec",
                "quantity_mwh": 1,
                "verification_status": "valid",
            }
        ],
        scope3_categories={
            1: {"spend": 100_000, "factor": 0.0001, "factor_id": "eeio-1"},
            4: {"rows": [{"weight_tonnes": 2, "distance_km": 100, "factor": 0.001}]},
            5: {"rows": [{"quantity_tonnes": 3, "factor": 0.05}]},
            9: {"rows": [{"weight_tonnes": 1, "distance_km": 50, "factor": 0.001}]},
        },
    )

    assert inventory.scope1_by_category == {"mobile_combustion": 2.68}
    assert inventory.valid_certificate_coverage_mwh == pytest.approx(1)
    assert inventory.scope2_location_based_tco2e == pytest.approx(0.84)
    assert inventory.scope2_market_based_tco2e == pytest.approx(0.42)
    assert inventory.scope3_by_category["1"] == pytest.approx(10)
    assert inventory.scope3_by_category["3"] == pytest.approx(0.0252)
    assert inventory.scope3_tco2e == pytest.approx(10.4252)
    assert inventory.total_carbon_footprint_market_based_tco2e == pytest.approx(13.5252)
    assert inventory.carbon_intensity_market_based_tco2e_per_million_cny == pytest.approx(0.1353)


def test_scope3_manufacturing_rows_and_auto_td_loss_are_provenanced() -> None:
    result = scope3_estimate(
        {
            1: {"spend": 10_000, "factor": 0.001},
            4: {"rows": [{"weight_tonnes": 4, "distance_km": 25, "factor": 0.002}]},
            5: {"rows": [{"quantity_tonnes": 2, "factor": 0.1}]},
        },
        scope2_electricity_mwh=100,
        grid_emission_factor_tco2e_per_mwh=0.5,
    )

    assert result["category_count"] == 15
    assert result["categories"][0]["method"] == "eeio_spend"
    assert result["categories"][2]["tco2e"] == pytest.approx(1.5)
    assert "world-bank-td-loss-rate" in result["factors_used"]
    assert any("World Bank" in source for source in result["sources"])


def test_three_year_comparison_calculates_totals_and_yoy_change() -> None:
    result = three_year_comparison(
        [
            {"year": 2023, "scope1": 10, "scope2": 20, "scope3": 30},
            {"year": 2024, "scope1": 20, "scope2": 20, "scope3": 20},
            {"year": 2025, "scope1": 10, "scope2": 15, "scope3": 15},
        ]
    )

    assert result["current_year"] == 2025
    assert result["years"][0]["total_tco2e"] == 40
    assert result["years"][0]["yoy_change_pct"] == pytest.approx(-33.33)
    assert result["years"][2]["yoy_change_pct"] is None


def test_mass_balance_supports_mixed_gases_and_rejects_unknown_gases() -> None:
    result = scope1_mass_balance(
        [{"mass": 12, "carbon_content": 1, "gas": "CO2"}, {"mass": 1, "carbon_content": 1, "gas": "CH4"}],
        [],
    )
    assert result["net_carbon_mass_by_gas"] == {"CH4": 1.0, "CO2": 12.0}
    with pytest.raises(ValueError, match="Unsupported AR6 gas"):
        scope1_mass_balance([{"mass": 1, "carbon_content": 1, "gas": "HFC"}], [])


def test_calculator_input_validation_is_explicit() -> None:
    with pytest.raises(ValueError, match="Unknown GB/T 2589 fuel"):
        energy_to_tce([{"fuel": "unknown", "quantity_kg": 1}])
    with pytest.raises(ValueError, match="Withdrawal volumes"):
        water_balance([{"source_type": "rain", "volume": -1}], 0)
