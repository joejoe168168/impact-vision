from __future__ import annotations

import json
import asyncio

from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.common import normalize_metric_map, normalize_sdg_goals, normalize_str_list
from openharness.tools.impact.data_quality_tool import DataQualityInput, DataQualityTool
from openharness.tools.impact.dd_checklist_tool import _flatten_json_text
from openharness.tools.impact.metric_recommender_tool import MetricRecommenderInput, MetricRecommenderTool
from openharness.tools.impact.impact_risk_opportunity_tool import (
    ImpactRiskOpportunityInput,
    ImpactRiskOpportunityTool,
)
from openharness.tools.impact.lp_ddq_export_tool import LpDdqExportInput, LpDdqExportTool
from openharness.tools.impact.pitch_deck_analyze_tool import PitchDeckAnalyzeInput, PitchDeckAnalyzeTool
from openharness.tools.impact.portfolio_tool import _load_portfolio_file


def test_common_normalizers() -> None:
    assert normalize_metric_map({" pi4060 ": " 100 ", "": "x", "oi1479": ""}) == {"PI4060": "100"}
    assert normalize_sdg_goals([1, 1, 18, 7, "3"]) == [1, 7, 3]
    assert normalize_str_list([" Health ", "", "health", "Climate"]) == ["Health", "Climate"]


def test_lp_ddq_supports_csv_output(tmp_path) -> None:
    tool = LpDdqExportTool()
    ctx = ToolExecutionContext(cwd=tmp_path)
    result = asyncio.run(
        tool.execute(
            LpDdqExportInput(
                template="giin_iris",
                action="generate",
                company_name="Acme Impact",
                sector="Fintech",
                reported_metrics={"pi4060": "1000"},
                output_format="csv",
            ),
            ctx,
        )
    )
    assert result.is_error is False
    assert "Section ID,Question,Response" in result.output
    assert "giin-1" in result.output


def test_pitch_deck_supports_markdown_input(tmp_path) -> None:
    path = tmp_path / "memo.md"
    path.write_text("# Memo\nWe support financial inclusion and SDG 1.", encoding="utf-8")

    tool = PitchDeckAnalyzeTool()
    ctx = ToolExecutionContext(cwd=tmp_path)
    result = asyncio.run(
        tool.execute(
            PitchDeckAnalyzeInput(file_path="memo.md", include_dd_checklist=False),
            ctx,
        )
    )
    assert result.is_error is False
    assert "Detected SDGs: SDG 1" in result.output


def test_portfolio_loader_supports_json(tmp_path) -> None:
    data = {
        "companies": [
            {
                "name": "A",
                "sector": "Energy",
                "impact_themes": [" Clean Energy ", "clean energy"],
                "reported_metrics": {"pi4060": "4"},
                "sdg_claims": [7, 7, 99],
            }
        ]
    }
    path = tmp_path / "portfolio.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    companies = _load_portfolio_file(str(path), ToolExecutionContext(cwd=tmp_path))
    assert not isinstance(companies, str)
    assert companies[0].impact_themes == ["Clean Energy"]
    assert companies[0].reported_metrics == {"PI4060": "4"}
    assert companies[0].sdg_claims == [7]


def test_flatten_json_text_extracts_values() -> None:
    raw = {"company": {"name": "Acme", "claims": ["SDG 1", "SDG 7"]}}
    flat = _flatten_json_text(raw)
    assert "Acme" in flat
    assert "SDG 7" in flat


def test_impact_data_quality_tool_flags_issues(tmp_path) -> None:
    tool = DataQualityTool()
    ctx = ToolExecutionContext(cwd=tmp_path)
    result = asyncio.run(
        tool.execute(
            DataQualityInput(
                reported_metrics={"pi4060": "N/A", "BAD123": "10", "OI1479": "many"},
                required_metrics=["PI4060", "OI1479", "OI2913"],
            ),
            ctx,
        )
    )
    assert result.is_error is False
    assert "Quality score:" in result.output
    assert "Unknown metric IDs" in result.output
    assert "Missing required metrics" in result.output


def test_impact_data_quality_tool_json_output(tmp_path) -> None:
    tool = DataQualityTool()
    ctx = ToolExecutionContext(cwd=tmp_path)
    result = asyncio.run(
        tool.execute(
            DataQualityInput(
                reported_metrics={"PI4060": "100"},
                output_format="json",
            ),
            ctx,
        )
    )
    payload = json.loads(result.output)
    assert payload["quality_score"] >= 90
    assert payload["metrics_provided"] == 1


def test_metric_recommender_returns_results(tmp_path) -> None:
    tool = MetricRecommenderTool()
    ctx = ToolExecutionContext(cwd=tmp_path)
    result = asyncio.run(
        tool.execute(
            MetricRecommenderInput(
                sector="Fintech",
                impact_themes=["Financial Inclusion"],
                sdg_goals=[1, 8],
                max_metrics=10,
            ),
            ctx,
        )
    )
    assert result.is_error is False
    assert "IRIS+ METRIC RECOMMENDATIONS" in result.output
    assert result.metadata is not None
    assert result.metadata["count"] > 0


def test_impact_risk_opportunity_tool_returns_scores(tmp_path) -> None:
    tool = ImpactRiskOpportunityTool()
    ctx = ToolExecutionContext(cwd=tmp_path)
    result = asyncio.run(
        tool.execute(
            ImpactRiskOpportunityInput(
                company_name="RiskyCo",
                company_description="Climate fintech platform with strong focus on financial inclusion and data privacy.",
                sector="Fintech",
                impact_themes=["Financial Inclusion", "Climate"],
                reported_metrics={"PI4060": "1000"},
                sdg_claims=[1, 8, 13],
            ),
            ctx,
        )
    )
    assert result.is_error is False
    assert "Risk score:" in result.output
    assert "Opportunity score:" in result.output
