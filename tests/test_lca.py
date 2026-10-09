"""Tests for lifecycle assessment, LCSA, and life-cycle management helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from impact_vision.impact.lca import (
    LCAStudy,
    assess_lca_readiness,
    build_lcm_plan,
    calculate_lca,
    calculate_lcsa,
    run_lca_sensitivity,
)
from impact_vision.tools import create_default_tool_registry
from impact_vision.tools.base import ToolExecutionContext
from impact_vision.tools.impact.lca_tool import LCAAssessmentInput, LCAAssessmentTool


def _study(**overrides):
    payload = {
        "study_id": "demo-product",
        "product_system": "Demo product",
        "goal": "Compare two design options",
        "intended_application": "Procurement decision",
        "audience": ["procurement", "sustainability"],
        "functional_unit": "1 kg delivered product",
        "reference_flow": "1 product",
        "boundary": "cradle_to_grave",
        "excluded_processes": ["capital goods"],
    }
    payload.update(overrides)
    return payload


def _flows():
    return [
        {
            "flow_id": "paper-board-1",
            "name": "Paper board",
            "stage": "raw materials",
            "quantity": 2.0,
            "unit": "kg",
            "source": "supplier EPD",
            "verified": True,
            "data_quality_score": 4,
            "impact_factors": {"climate_change": 0.5, "water_use": 0.2},
        },
        {
            "flow_id": "factory-electricity",
            "name": "Factory electricity",
            "stage": "manufacturing",
            "quantity": 3.0,
            "unit": "kWh",
            "source": "meter",
            "data_quality_score": 3,
            "impact_factors": {"climate_change": 0.4, "energy_use": 3.6},
        },
        {
            "flow_id": "delivery-truck",
            "name": "Delivery transport",
            "stage": "distribution",
            "quantity": 10.0,
            "unit": "tkm",
            "source": "logistics record",
            "data_quality_score": 3,
            "impact_factors": {"climate_change": 0.1},
        },
    ]


def test_lca_rollup_normalises_to_functional_unit_and_finds_hotspots():
    result = calculate_lca(_study(reference_quantity=2), _flows())

    assert result.impacts["climate_change"] == pytest.approx(1.6)
    assert result.stage_impacts["raw_materials"]["climate_change"] == pytest.approx(0.5)
    climate_hotspot = next(item for item in result.hotspots if item.category == "climate_change")
    assert climate_hotspot.lifecycle_stage == "manufacturing"
    assert result.data_quality.characterization_coverage_pct == 100.0
    assert result.data_quality.evidence_coverage_pct == 100.0


def test_lca_rejects_flows_outside_declared_boundary():
    study = _study(boundary="cradle_to_gate")
    with pytest.raises(ValueError, match="outside the study boundary"):
        calculate_lca(study, _flows())


def test_sensitivity_preserves_hyphenated_flow_ids_and_flags_large_change():
    result = run_lca_sensitivity(
        _study(),
        _flows(),
        [
            {
                "scenario_id": "low-carbon-delivery",
                "label": "Lower-carbon delivery",
                "flow_multipliers": {"delivery-truck": 0.25},
            }
        ],
    )

    scenario = result.scenarios[0]
    assert scenario.impacts["climate_change"] < result.baseline_impacts["climate_change"]
    assert scenario.delta_pct_by_category["climate_change"] is not None
    assert result.robust_conclusion == "sensitive"


def test_lcsa_keeps_environmental_economic_and_social_units_separate():
    result = calculate_lcsa(
        _study(assessment_dimensions=["environmental", "economic", "social"]),
        _flows(),
        cost_lines=[
            {
                "line_id": "capex",
                "name": "Tooling",
                "stage": "manufacturing",
                "amount": 100,
                "currency": "USD",
                "source": "ledger",
            },
            {
                "line_id": "maintenance",
                "name": "Maintenance",
                "stage": "use",
                "amount": 20,
                "currency": "USD",
                "period_year": 2,
                "source": "service records",
            },
        ],
        social_indicators=[
            {
                "indicator_id": "worker-safety",
                "name": "Recordable incidents",
                "stakeholder_group": "workers",
                "stage": "manufacturing",
                "value": 1,
                "unit": "incidents",
                "direction": "negative",
                "source": "HSE register",
            }
        ],
        discount_rate=0.05,
    )

    assert result.dimensions_present == ["environmental", "economic", "social"]
    assert result.economic is not None
    assert result.economic.total_present_value < result.economic.total_nominal
    assert result.social is not None
    assert result.social.negative_hotspots
    assert any("different units" in flag for flag in result.decision_flags)


def test_readiness_and_lcm_plan_surface_next_actions():
    study = LCAStudy.model_validate(_study())
    result = calculate_lca(study, _flows())
    plan = build_lcm_plan(result, owners_by_stage={"manufacturing": "Operations"})
    readiness = assess_lca_readiness(
        study,
        _flows(),
        scenarios=[
            {
                "scenario_id": "s1",
                "label": "Stress test",
                "flow_multipliers": {"paper-board-1": 1.2},
            }
        ],
    )

    assert any(action.owner == "Operations" for action in plan.actions)
    assert plan.decision_gates
    assert readiness.score >= 65
    assert readiness.band in {"decision_ready", "assurance_prepared"}
    assert readiness.assessment_basis.startswith("Deterministic")


def test_lca_tool_and_registry_are_available():
    tool = LCAAssessmentTool()
    ctx = ToolExecutionContext(cwd=Path("."))
    result = asyncio.run(
        tool.execute(
            LCAAssessmentInput(action="list_methods"),
            ctx,
        )
    )
    registry = create_default_tool_registry()

    assert not result.is_error
    assert "recipe_2016_midpoint" in result.output
    assert registry.get("lca_assessment") is not None
