"""Tests for impact tool enhancements: normalizers, new tools, format support."""

from __future__ import annotations

import asyncio
from pathlib import Path

from openharness.tools.impact.common import (
    infer_themes,
    normalize_metric_ids,
    normalize_metric_map,
    normalize_sdg_goals,
    normalize_str_list,
)


class TestNormalizers:
    def test_normalize_metric_map_uppercases(self):
        metrics, warnings = normalize_metric_map({"oi4112": "100", "pi4060": "200"})
        assert "OI4112" in metrics
        assert "PI4060" in metrics
        assert len(warnings) == 0

    def test_normalize_metric_map_rejects_invalid(self):
        metrics, warnings = normalize_metric_map({"OI4112": "100", "BAD_ID": "50", "": "x"})
        assert "OI4112" in metrics
        assert "BAD_ID" not in metrics
        assert len(warnings) == 1

    def test_normalize_metric_map_empty(self):
        metrics, warnings = normalize_metric_map(None)
        assert metrics == {}
        assert warnings == []

    def test_normalize_metric_ids(self):
        ids, warnings = normalize_metric_ids(["oi4112", "PI4060", "bad", "OI4112"])
        assert ids == ["OI4112", "PI4060"]
        assert len(warnings) == 1

    def test_normalize_sdg_goals(self):
        goals, warnings = normalize_sdg_goals([1, 17, 0, 18, 5, 1])
        assert 1 in goals
        assert 17 in goals
        assert 5 in goals
        assert 0 not in goals
        assert 18 not in goals
        assert len(warnings) == 2

    def test_normalize_str_list_deduplicates(self):
        result = normalize_str_list(["Health", "health", "  Health  ", "Energy", ""])
        assert result == ["Health", "Energy"]

    def test_infer_themes_from_text(self):
        themes = infer_themes("solar energy company in rural area")
        assert "Clean Energy" in themes
        assert "Energy Access" in themes

    def test_infer_themes_merges_existing(self):
        themes = infer_themes("healthcare company", ["Existing Theme"])
        assert "Existing Theme" in themes
        assert "Health" in themes


class TestNewTools:
    def test_data_quality_tool_import(self):
        from openharness.tools.impact.data_quality_tool import DataQualityTool
        tool = DataQualityTool()
        assert tool.name == "impact_data_quality"

    def test_metric_recommender_tool_import(self):
        from openharness.tools.impact.metric_recommender_tool import MetricRecommenderTool
        tool = MetricRecommenderTool()
        assert tool.name == "impact_metric_recommender"

    def test_risk_opportunity_tool_import(self):
        from openharness.tools.impact.impact_risk_opportunity_tool import ImpactRiskOpportunityTool
        tool = ImpactRiskOpportunityTool()
        assert tool.name == "impact_risk_opportunity"

    def test_risk_opportunity_engine(self):
        from openharness.impact.models import Company
        from openharness.impact.risk_opportunity import assess_impact_risk_opportunity

        company = Company(
            name="Test Farm",
            description="Agriculture with climate adaptation and waste management",
            sector="agriculture",
        )
        result = assess_impact_risk_opportunity(company)
        assert "risk_score" in result
        assert "opportunity_score" in result
        assert isinstance(result["risks"], list)
        assert isinstance(result["opportunities"], list)

    def test_data_quality_assess(self):
        from openharness.tools.impact.data_quality_tool import DataQualityTool, DataQualityInput
        from openharness.tools.base import ToolExecutionContext

        tool = DataQualityTool()
        args = DataQualityInput(
            reported_metrics={"OI4112": "1200 tCO2e", "BADID": "n/a", "PI4060": "TBD"},
        )
        ctx = ToolExecutionContext(cwd=Path("."))
        result = asyncio.run(tool.execute(args, ctx))
        assert not result.is_error
        assert "quality_score" in result.output.lower() or "quality" in result.output.lower()


class TestScoreProvenance:
    def test_provenance_estimated_when_no_metrics(self):
        from openharness.impact.database import get_metric_store
        from openharness.impact.five_dimensions import assess_five_dimensions
        from openharness.impact.models import Company

        store = get_metric_store()
        company = Company(name="Test Co", description="A fintech company", sector="fintech")
        result = assess_five_dimensions(company, store)
        assert result.overall_provenance == "estimated"
        for dim in [result.what, result.who, result.how_much, result.contribution, result.risk]:
            assert dim.provenance == "estimated"

    def test_provenance_partial_with_few_metrics(self):
        from openharness.impact.database import get_metric_store
        from openharness.impact.five_dimensions import assess_five_dimensions
        from openharness.impact.models import Company

        store = get_metric_store()
        company = Company(
            name="Test Co",
            description="A fintech company",
            sector="fintech",
            reported_metrics={"OI4112": "100"},
        )
        result = assess_five_dimensions(company, store)
        assert result.overall_provenance in ("partial", "estimated")


class TestNegationDetection:
    def test_negation_blocks_boost(self):
        from openharness.impact.five_dimensions import _keyword_not_negated

        assert _keyword_not_negated("we support women empowerment", "women") is True
        assert _keyword_not_negated("we do not target women", "women") is False
        assert _keyword_not_negated("without climate considerations", "climate") is False
        assert _keyword_not_negated("climate adaptation program", "climate") is True


class TestCompanyModel:
    def test_new_fields_default(self):
        from openharness.impact.models import Company

        company = Company(name="Test")
        assert company.geography == ""
        assert company.stage == ""
        assert company.founded_year is None
        assert company.employees is None
        assert company.impact_targets == {}
        assert company.reporting_period == ""
        assert company.exclusion_flags == []
        assert company.metric_history == []

    def test_new_fields_set(self):
        from openharness.impact.models import Company, MetricValue

        company = Company(
            name="Test",
            geography="Kenya",
            stage="seed",
            founded_year=2020,
            employees=50,
            impact_targets={"OI4112": "500 tCO2e by 2027"},
            reporting_period="FY2025",
            exclusion_flags=["fossil_fuel"],
            metric_history=[
                MetricValue(metric_id="OI4112", value="100", period="FY2024"),
                MetricValue(metric_id="OI4112", value="200", period="FY2025"),
            ],
        )
        assert company.geography == "Kenya"
        assert company.stage == "seed"
        assert len(company.metric_history) == 2
        assert company.metric_history[1].value == "200"


class TestMetricValueModel:
    def test_metric_value_defaults(self):
        from openharness.impact.models import MetricValue

        mv = MetricValue(metric_id="OI4112", value="100 tCO2e")
        assert mv.metric_id == "OI4112"
        assert mv.unit == ""
        assert mv.period == ""
        assert mv.source == ""
        assert mv.verified is False

    def test_metric_value_full(self):
        from openharness.impact.models import MetricValue

        mv = MetricValue(
            metric_id="PI4060",
            value=25000,
            unit="count",
            period="Q1 2026",
            timestamp="2026-04-01",
            source="audited",
            verified=True,
            notes="Annual count",
        )
        assert mv.verified is True
        assert mv.period == "Q1 2026"


class TestGreenwashing:
    def test_greenwashing_tool_import(self):
        from openharness.tools.impact.greenwashing_tool import GreenwashingDetectorTool
        tool = GreenwashingDetectorTool()
        assert tool.name == "greenwashing_detect"

    def test_greenwashing_low_risk(self):
        from openharness.impact.greenwashing import assess_greenwashing
        from openharness.impact.models import Company

        company = Company(
            name="Verified Solar",
            description="We deployed 500MW solar capacity, measured and verified by third-party audit. Baseline established 2020.",
            sector="energy",
            reported_metrics={"OI4112": "1200 tCO2e", "PI4060": "25000", "OI9803": "500MW"},
            sdg_claims=[7, 13],
        )
        result = assess_greenwashing(company)
        assert result.overall_score < 50
        assert result.classification in ("Genuine Impact Leader", "Substantive with Gaps")

    def test_greenwashing_high_risk(self):
        from openharness.impact.greenwashing import assess_greenwashing
        from openharness.impact.models import Company

        company = Company(
            name="Vague Impact Co",
            description="We aspire to be sustainable and aim to contribute to a greener, more eco-friendly future. We believe in responsible investing.",
            sector="technology",
            sdg_claims=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        )
        result = assess_greenwashing(company)
        assert result.overall_score > 40
        assert len(result.flags) > 0

    def test_greenwashing_classification_range(self):
        from openharness.impact.greenwashing import _classify
        assert _classify(10) == "Genuine Impact Leader"
        assert _classify(30) == "Substantive with Gaps"
        assert _classify(50) == "Moderate Risk"
        assert _classify(70) == "High Risk"
        assert _classify(90) == "Probable Greenwashing"


class TestExclusionScreening:
    def test_exclusion_tool_import(self):
        from openharness.tools.impact.exclusion_screening_tool import ExclusionScreeningTool
        tool = ExclusionScreeningTool()
        assert tool.name == "exclusion_screening"

    def test_exclusion_pass(self):
        from openharness.tools.impact.exclusion_screening_tool import ExclusionScreeningTool, ExclusionScreeningInput
        from openharness.tools.base import ToolExecutionContext

        tool = ExclusionScreeningTool()
        args = ExclusionScreeningInput(
            company_name="Clean Fintech",
            company_description="Mobile banking for rural farmers in Kenya",
            sector="fintech",
        )
        ctx = ToolExecutionContext(cwd=Path("."))
        result = asyncio.run(tool.execute(args, ctx))
        assert not result.is_error
        assert "PASS" in result.output

    def test_exclusion_fail(self):
        from openharness.tools.impact.exclusion_screening_tool import ExclusionScreeningTool, ExclusionScreeningInput
        from openharness.tools.base import ToolExecutionContext

        tool = ExclusionScreeningTool()
        args = ExclusionScreeningInput(
            company_name="Bad Corp",
            company_description="Coal mining and oil exploration company",
            sector="energy",
        )
        ctx = ToolExecutionContext(cwd=Path("."))
        result = asyncio.run(tool.execute(args, ctx))
        assert not result.is_error
        assert "FAIL" in result.output
