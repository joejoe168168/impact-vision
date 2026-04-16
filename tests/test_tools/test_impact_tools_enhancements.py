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
