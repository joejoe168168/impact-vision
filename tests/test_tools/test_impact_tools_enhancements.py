"""Tests for impact tool enhancements: normalizers, new tools, format support."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from openharness.tools.impact.common import (
    infer_themes,
    normalize_impact_targets,
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

    def test_normalize_impact_targets_from_dict(self):
        from openharness.impact.models import ImpactTarget
        targets, warnings = normalize_impact_targets({"OI4112": "500 tCO2e by 2027", "PI4060": "1000 clients"})
        assert len(targets) == 2
        assert all(isinstance(t, ImpactTarget) for t in targets)
        assert targets[0].metric_id == "OI4112"
        assert targets[0].target_value == 500.0
        assert targets[0].target_unit == "tCO2e"
        assert targets[1].metric_id == "PI4060"
        assert targets[1].target_value == 1000.0

    def test_normalize_impact_targets_from_list(self):
        from openharness.impact.models import ImpactTarget
        targets, warnings = normalize_impact_targets([
            {"metric_id": "OI4112", "target_value": 500, "target_unit": "tCO2e"},
        ])
        assert len(targets) == 1
        assert isinstance(targets[0], ImpactTarget)
        assert targets[0].target_value == 500.0

    def test_normalize_impact_targets_empty(self):
        targets, warnings = normalize_impact_targets(None)
        assert targets == []
        assert warnings == []

    def test_normalize_impact_targets_invalid_id(self):
        targets, warnings = normalize_impact_targets({"BADID": "some target"})
        assert len(targets) == 0
        assert len(warnings) == 1

    def test_normalize_impact_targets_qualitative(self):
        targets, _ = normalize_impact_targets({"OI4112": "Implement recycling policy"})
        assert len(targets) == 1
        assert targets[0].target_value is None
        assert targets[0].description == "Implement recycling policy"


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

    def test_all_impact_tool_modules_are_registered(self):
        from openharness.tools import create_default_tool_registry

        registry = create_default_tool_registry()
        registered = {tool.name for tool in registry.list_tools()}

        expected = {
            "beneficiary_feedback",
            "cross_reference",
            "document_analysis",
            "dd_checklist",
            "exclusion_screening",
            "five_dimension_assess",
            "framework_assess",
            "gap_analysis",
            "greenwashing_detect",
            "guided_assessment",
            "impact_data_quality",
            "impact_metric_recommender",
            "impact_risk_opportunity",
            "impact_report",
            "improvement_advisor",
            "iris_catalog",
            "lp_ddq_export",
            "monitoring",
            "narrative",
            "pipeline",
            "pitch_deck_analyze",
            "portfolio_analyze",
            "product_passport",
            "sdg_mapper",
            "trend_analysis",
            "verification_prep",
        }

        assert expected <= registered

    def test_improvement_advisor_executes_with_sdg_claims(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.improvement_advisor_tool import (
            ImprovementAdvisorInput,
            ImprovementAdvisorTool,
        )

        tool = ImprovementAdvisorTool()
        args = ImprovementAdvisorInput(
            action="recommend",
            company_name="Solar Co",
            company_description="Solar energy access for rural households",
            sector="Energy",
            sdg_claims=[7, 13],
        )
        result = asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path("."))))

        assert not result.is_error
        assert "IMPROVEMENT RECOMMENDATIONS" in result.output

    def test_narrative_executes_with_sdg_claims(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.narrative_tool import NarrativeInput, NarrativeTool

        tool = NarrativeTool()
        args = NarrativeInput(
            action="executive_summary",
            company_name="Solar Co",
            company_description="Solar energy access for rural households",
            sector="Energy",
            sdg_claims=[7, 13],
        )
        result = asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path("."))))

        assert not result.is_error
        assert "EXECUTIVE SUMMARY PROMPT" in result.output

    def test_document_analysis_normalizes_metric_id_case(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.document_analysis_tool import DocumentAnalysisInput, DocumentAnalysisTool

        tool = DocumentAnalysisTool()
        args = DocumentAnalysisInput(
            action="compare_documents",
            company_name="Solar Co",
            documents=[
                {"name": "memo", "text": "Reports oi4112 and sdg 13."},
                {"name": "deck", "text": "Reports OI4112 plus pi4060 for SDG 13."},
            ],
        )
        result = asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path("."))))

        assert not result.is_error
        assert "Shared metrics across all docs: 1 (OI4112)" in result.output
        assert "PI4060" in result.output

    def test_beneficiary_feedback_preserves_zero_nps(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.beneficiary_feedback_tool import (
            BeneficiaryFeedbackInput,
            BeneficiaryFeedbackTool,
        )

        tool = BeneficiaryFeedbackTool()
        args = BeneficiaryFeedbackInput(
            action="import",
            company_name="Feedback Co",
            raw_data=json.dumps({"nps": 0, "satisfaction_score": 1, "sample_size": 12}),
        )
        result = asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path("."))))

        assert not result.is_error
        assert "NPS: 0" in result.output
        assert result.metadata["feedback"]["nps"] == 0

    def test_product_passport_rejects_non_object_json(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.product_passport_tool import ProductPassportInput, ProductPassportTool

        tool = ProductPassportTool()
        ctx = ToolExecutionContext(cwd=Path("."))

        imported = asyncio.run(tool.execute(ProductPassportInput(action="import", dpp_data="[]"), ctx))
        assessed = asyncio.run(tool.execute(ProductPassportInput(action="assess", dpp_data="[]"), ctx))

        assert imported.is_error
        assert assessed.is_error
        assert "JSON object" in imported.output
        assert "JSON object" in assessed.output

    def test_monitoring_normalizes_metric_ids_and_parses_units(self, tmp_path, monkeypatch):
        from openharness.impact import storage
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.monitoring_tool import MonitoringInput, MonitoringTool

        monkeypatch.setattr(storage, "_global_store", storage.AssessmentStore(tmp_path / "impact.db"))
        store = storage.get_assessment_store()
        store.save_assessment(
            company_name="Monitor Co",
            company_data={
                "name": "Monitor Co",
                "reported_metrics": {"OI4112": "100 tCO2e"},
            },
        )

        tool = MonitoringTool()
        ctx = ToolExecutionContext(cwd=Path("."))
        asyncio.run(tool.execute(
            MonitoringInput(
                action="set_schedule",
                company_name="Monitor Co",
                alert_thresholds={"oi4112": 0.1},
                watch_metrics=["oi4112"],
            ),
            ctx,
        ))
        result = asyncio.run(tool.execute(
            MonitoringInput(
                action="record_metric",
                company_name="Monitor Co",
                metric_id="oi4112",
                metric_value=150,
            ),
            ctx,
        ))

        assessment = store.get_assessment("Monitor Co")
        alerts = store.list_alerts(company_name="Monitor Co")
        schedule = store.get_monitoring_schedule("Monitor Co")

        assert not result.is_error
        assert "Alert(s) triggered" in result.output
        assert assessment["company"]["reported_metrics"]["OI4112"] == "150.0"
        assert schedule["watch_metrics"] == ["OI4112"]
        assert schedule["alert_thresholds"] == {"OI4112": 0.1}
        assert alerts[0]["metric_id"] == "OI4112"

    def test_product_passport_mcp_maps_product_data(self):
        from openharness.impact.mcp_server import product_passport

        output = asyncio.run(product_passport(
            action="assess",
            product_data={"product_name": "Battery", "carbon_footprint": "20 kgCO2e"},
            product_category="batteries",
        ))

        assert "DPP Completeness Assessment" in output
        assert "carbon_footprint" in output

    def test_mcp_pipeline_uses_stage_field(self, tmp_path, monkeypatch):
        from openharness.impact import storage
        from openharness.impact.mcp_server import pipeline

        monkeypatch.setattr(storage, "_global_store", storage.AssessmentStore(tmp_path / "impact.db"))
        asyncio.run(pipeline(
            action="add",
            company_name="Pipeline Co",
            stage="screening",
            sector="energy",
        ))

        entry = storage.get_assessment_store().get_pipeline_entry("Pipeline Co")
        assert entry["pipeline_stage"] == "screening"

    def test_mcp_monitoring_uses_metric_value_field(self, tmp_path, monkeypatch):
        from openharness.impact import storage
        from openharness.impact.mcp_server import monitoring

        monkeypatch.setattr(storage, "_global_store", storage.AssessmentStore(tmp_path / "impact.db"))
        store = storage.get_assessment_store()
        store.save_assessment(
            company_name="MCP Monitor Co",
            company_data={"name": "MCP Monitor Co", "reported_metrics": {"OI4112": "100"}},
        )

        asyncio.run(monitoring(action="set_schedule", company_name="MCP Monitor Co"))
        output = asyncio.run(monitoring(
            action="record_metric",
            company_name="MCP Monitor Co",
            metric_id="oi4112",
            value="125",
        ))

        assert "metric_value is required" not in output
        assert "Recorded OI4112 = 125.0" in output

    def test_mcp_beneficiary_feedback_maps_feedback_data(self):
        from openharness.impact.mcp_server import beneficiary_feedback

        output = asyncio.run(beneficiary_feedback(
            action="import",
            company_name="Feedback Co",
            feedback_data={"nps": 0, "satisfaction_score": 1, "sample_size": 5},
        ))

        assert "NPS: 0" in output
        assert "Sample size: 5" in output

    def test_mcp_cross_reference_supplies_required_action(self):
        from openharness.impact.mcp_server import cross_reference

        output = asyncio.run(cross_reference(metric_id="OI4112"))

        assert "Cross-references for 'OI4112'" in output

    def test_mcp_dd_checklist_maps_text_to_document_text(self):
        from openharness.impact.mcp_server import dd_checklist

        output = asyncio.run(dd_checklist(
            action="analyze",
            text="We document a theory of change and measure outcomes for customers.",
        ))

        assert "Provide document_text" not in output
        assert "DD Checklist Coverage Analysis" in output

    def test_mcp_narrative_maps_section_and_audience_aliases(self):
        from openharness.impact.mcp_server import narrative

        output = asyncio.run(narrative(
            section="executive_summary",
            audience="investor",
            company_name="Narrative Co",
            company_description="Solar energy access for rural households",
            sector="energy",
        ))

        assert "EXECUTIVE SUMMARY PROMPT" in output

    def test_mcp_portfolio_analyze_maps_action_alias(self):
        from openharness.impact.mcp_server import portfolio_analyze

        output = asyncio.run(portfolio_analyze(
            action="analyze",
            companies=[
                {
                    "name": "Portfolio Co",
                    "description": "Solar energy access",
                    "sector": "energy",
                    "reported_metrics": {"OI4112": "100"},
                },
            ],
        ))

        assert "validation" not in output.lower()
        assert "PORTFOLIO" in output.upper()

    def test_mcp_trend_analysis_flattens_metric_history(self):
        from openharness.impact.mcp_server import trend_analysis

        output = asyncio.run(trend_analysis(
            company_name="Trend Co",
            metric_history={
                "OI4112": [
                    {"value": "100", "period": "FY2024"},
                    {"value": "125", "period": "FY2025"},
                ],
            },
        ))

        assert "validation" not in output.lower()
        assert "TREND" in output.upper()

    def test_mcp_framework_assess_supplies_action(self):
        from openharness.impact.mcp_server import framework_assess

        output = asyncio.run(framework_assess(
            framework="opim",
            company_name="Framework Co",
            company_description="Impact thesis with SDG 7 theory of change and independent verification.",
            reported_metrics={"OI4112": "100", "PI4060": "200", "OI6697": "50"},
        ))

        assert "validation" not in output.lower()
        assert "IFC OPIM ALIGNMENT ASSESSMENT" in output

    def test_mcp_guided_assessment_list_templates_uses_default_template(self):
        from openharness.impact.mcp_server import guided_assessment

        output = asyncio.run(guided_assessment(action="list_templates"))

        assert "validation" not in output.lower()
        assert "ASSESSMENT TEMPLATES" in output

    def test_mcp_impact_report_passes_target_and_claim_inputs(self):
        from openharness.impact.mcp_server import impact_report

        output = asyncio.run(impact_report(
            company_name="Report Co",
            company_description="Solar energy access for rural households",
            sector="energy",
            reported_metrics={"OI4112": "150"},
            impact_targets={"OI4112": "200 tCO2e by 2027"},
            metric_history=[
                {"metric_id": "OI4112", "value": "100", "period": "FY2024"},
                {"metric_id": "OI4112", "value": "150", "period": "FY2025"},
            ],
            impact_claims=[
                {
                    "text": "Report Co reduces emissions for rural households.",
                    "mapped_metrics": ["OI4112"],
                    "category": "outcome",
                },
            ],
            report_type="target_progress",
        ))

        assert "validation" not in output.lower()
        assert "TARGET PROGRESS REPORT" in output
        assert "OI4112" in output

    def test_api_pipeline_and_monitoring_map_request_fields(self, tmp_path, monkeypatch):
        from openharness.api_gateway.router import MonitoringRequest, PipelineRequest, monitoring_endpoint, pipeline_endpoint
        from openharness.impact import storage

        monkeypatch.setattr(storage, "_global_store", storage.AssessmentStore(tmp_path / "impact.db"))
        store = storage.get_assessment_store()
        store.save_assessment(
            company_name="API Monitor Co",
            company_data={"name": "API Monitor Co", "reported_metrics": {"OI4112": "100"}},
        )

        asyncio.run(pipeline_endpoint(PipelineRequest(
            action="add",
            company_name="API Pipeline Co",
            stage="screening",
            priority="high",
            sdg_focus=[7],
        )))
        asyncio.run(monitoring_endpoint(MonitoringRequest(
            action="record_metric",
            company_name="API Monitor Co",
            metric_id="oi4112",
            value="125",
        )))

        pipeline_entry = store.get_pipeline_entry("API Pipeline Co")
        assessment = store.get_assessment("API Monitor Co")

        assert pipeline_entry["pipeline_stage"] == "screening"
        assert pipeline_entry["priority"] == "high"
        assert pipeline_entry["sdg_focus"] == [7]
        assert assessment["company"]["reported_metrics"]["OI4112"] == "125.0"

    def test_framework_opim_executes_current_framework_api(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.framework_tool import FrameworkInput, FrameworkTool

        tool = FrameworkTool()
        result = asyncio.run(tool.execute(
            FrameworkInput(
                action="assess",
                framework="opim",
                company_name="OPIM Co",
                description="Impact thesis with SDG 7 alignment, theory of change, exclusion screening, and independent verification.",
                reported_metrics={"OI4112": "100", "PI4060": "200", "OI6697": "50"},
            ),
            ToolExecutionContext(cwd=Path(".")),
        ))

        assert not result.is_error
        assert "IFC OPIM ALIGNMENT ASSESSMENT" in result.output
        assert "Principles addressed" in result.output

    def test_pitch_deck_analyze_accepts_raw_text(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.pitch_deck_analyze_tool import PitchDeckAnalyzeInput, PitchDeckAnalyzeTool

        tool = PitchDeckAnalyzeTool()
        result = asyncio.run(tool.execute(
            PitchDeckAnalyzeInput(text="Solar Co provides clean energy access to 10,000 rural households and reduces CO2 emissions."),
            ToolExecutionContext(cwd=Path(".")),
        ))

        assert not result.is_error
        assert "PITCH DECK / MEMO ANALYSIS" in result.output

    def test_pitch_deck_suggestions_are_not_reported_evidence(self, tmp_path):
        import yaml

        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.pitch_deck_analyze_tool import PitchDeckAnalyzeInput, PitchDeckAnalyzeTool

        out = tmp_path / "company.yaml"
        tool = PitchDeckAnalyzeTool()
        result = asyncio.run(tool.execute(
            PitchDeckAnalyzeInput(
                text=(
                    "Solar Co provides clean energy access to rural households and "
                    "supports SDG 7 with renewable energy services."
                ),
                save_company_yaml=str(out),
            ),
            ToolExecutionContext(cwd=Path(".")),
        ))

        assert not result.is_error
        company = result.metadata["extracted_company"]
        assert company["reported_metrics"] == {}
        assert result.metadata["suggested_metrics"]
        assert "suggested metrics are recommendations" in result.output

        saved = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert saved["reported_metrics"] == {}
        assert saved["metric_recommendations"]
        assert "not reported evidence" in saved["evidence_note"]


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
        assert company.impact_targets == []
        assert company.reporting_period == ""
        assert company.exclusion_flags == []
        assert company.metric_history == []

    def test_new_fields_set(self):
        from openharness.impact.models import Company, ImpactTarget, MetricValue

        company = Company(
            name="Test",
            geography="Kenya",
            stage="seed",
            founded_year=2020,
            employees=50,
            impact_targets=[
                ImpactTarget(
                    metric_id="OI4112",
                    target_value=500,
                    target_unit="tCO2e",
                    target_date="2027",
                    description="500 tCO2e by 2027",
                ),
            ],
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
            reported_metrics={
                "OI4112": "1200 tCO2e",
                "OI9604": "400 tCO2e",
                "PI4060": "25000",
                "OI0263": "500 ML",
            },
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


class TestSDGProvenance:
    def test_sdg_estimated_with_no_metrics(self):
        from openharness.impact.database import get_metric_store
        from openharness.impact.models import Company
        from openharness.impact.sdg_mapper import map_sdg_alignment

        store = get_metric_store()
        company = Company(
            name="Vague Inc",
            description="We work in healthcare and education",
            sector="healthcare",
            sdg_claims=[3],
        )
        alignments = map_sdg_alignment(company, store)
        for a in alignments:
            if a.score > 0:
                assert a.provenance in ("estimated", "partial")

    def test_sdg_provenance_field_exists(self):
        from openharness.impact.models import SDGAlignment
        a = SDGAlignment(goal=1, goal_name="No Poverty", score=50.0)
        assert a.provenance == "estimated"


class TestGeographyInTools:
    def test_sdg_mapper_has_geography(self):
        from openharness.tools.impact.sdg_mapper_tool import SdgMapperInput
        inp = SdgMapperInput(company_name="Test", geography="Kenya")
        assert inp.geography == "Kenya"

    def test_five_dimension_has_geography(self):
        from openharness.tools.impact.five_dimension_assess_tool import FiveDimensionInput
        inp = FiveDimensionInput(company_name="Test", geography="Southeast Asia")
        assert inp.geography == "Southeast Asia"

    def test_greenwashing_has_geography(self):
        from openharness.tools.impact.greenwashing_tool import GreenwashingInput
        inp = GreenwashingInput(company_name="Test", geography="Brazil")
        assert inp.geography == "Brazil"

    def test_report_has_geography(self):
        from openharness.tools.impact.impact_report_tool import ImpactReportInput
        inp = ImpactReportInput(company_name="Test", geography="India")
        assert inp.geography == "India"

    def test_risk_opportunity_has_geography(self):
        from openharness.tools.impact.impact_risk_opportunity_tool import ImpactRiskOpportunityInput
        inp = ImpactRiskOpportunityInput(company_name="Test", geography="Nigeria")
        assert inp.geography == "Nigeria"


class TestGreenwashingIntegration:
    def test_greenwashing_assess_returns_dict(self):
        from openharness.impact.greenwashing import assess_greenwashing
        from openharness.impact.models import Company

        company = Company(
            name="Test Co",
            description="We aim to build sustainable solutions for climate change",
            sector="energy",
        )
        result = assess_greenwashing(company)
        assert hasattr(result, "overall_score")
        assert hasattr(result, "classification")
        assert hasattr(result, "flags")

    def test_report_text_includes_greenwashing(self):
        from openharness.tools.impact.impact_report_tool import _to_text

        data = {
            "company": {"name": "Test Co", "sector": "energy", "description": ""},
            "generated_at": "2026-01-01",
            "catalog_version": "IRIS+ 5.3c",
            "greenwashing": {
                "overall_score": 45,
                "classification": "Moderate Risk",
                "sub_scores": {"claim_metric_gap": 50, "specificity": 40},
                "flags": ["Vague language detected"],
                "recommendations": ["Add concrete metrics"],
            },
        }
        output = _to_text(data)
        assert "GREENWASHING" in output
        assert "Moderate Risk" in output
        assert "Vague language detected" in output


class TestPortfolioTool:
    def test_portfolio_tool_import(self):
        from openharness.tools.impact.portfolio_tool import PortfolioTool
        tool = PortfolioTool()
        assert tool.name == "portfolio_analyze"


class TestTrendAnalysis:
    def test_trend_analysis_improving(self):
        from openharness.impact.models import MetricValue
        from openharness.impact.trend_analysis import analyze_metric_trend

        values = [
            MetricValue(metric_id="OI4112", value="100", period="FY2023"),
            MetricValue(metric_id="OI4112", value="200", period="FY2024"),
            MetricValue(metric_id="OI4112", value="350", period="FY2025"),
        ]
        result = analyze_metric_trend(values)
        assert result["direction"] == "improving"
        assert result["data_points"] == 3
        assert result["change_pct"] > 0

    def test_trend_analysis_insufficient(self):
        from openharness.impact.models import MetricValue
        from openharness.impact.trend_analysis import analyze_metric_trend

        values = [MetricValue(metric_id="PI4060", value="500", period="FY2025")]
        result = analyze_metric_trend(values)
        assert result["direction"] == "insufficient_data"

    def test_company_trends(self):
        from openharness.impact.models import Company, MetricValue
        from openharness.impact.trend_analysis import analyze_company_trends

        company = Company(
            name="Test Co",
            metric_history=[
                MetricValue(metric_id="OI4112", value="100", period="FY2023"),
                MetricValue(metric_id="OI4112", value="200", period="FY2024"),
                MetricValue(metric_id="PI4060", value="1000", period="FY2023"),
                MetricValue(metric_id="PI4060", value="1200", period="FY2024"),
            ],
        )
        result = analyze_company_trends(company)
        assert result["metrics_analyzed"] == 2
        assert result["overall_direction"] in ("mostly_improving", "mixed")

    def test_trend_tool_import(self):
        from openharness.tools.impact.trend_analysis_tool import TrendAnalysisTool
        tool = TrendAnalysisTool()
        assert tool.name == "trend_analysis"


class TestTargetTracking:
    def test_target_progress(self):
        from openharness.impact.models import Company, ImpactTarget
        from openharness.impact.trend_analysis import assess_target_progress

        company = Company(
            name="Target Co",
            impact_targets=[
                ImpactTarget(
                    metric_id="OI4112",
                    target_value=500,
                    target_unit="tCO2e",
                    target_date="2027",
                    description="500 tCO2e by 2027",
                ),
            ],
            reported_metrics={"OI4112": "350"},
        )
        result = assess_target_progress(company)
        assert result["total_targets"] == 1
        assert result["targets"][0]["status"] in ("on_track", "behind")
        assert result["targets"][0]["progress_pct"] == 70.0

    def test_target_exceeded(self):
        from openharness.impact.models import Company, ImpactTarget
        from openharness.impact.trend_analysis import assess_target_progress

        company = Company(
            name="Over Achiever",
            impact_targets=[
                ImpactTarget(
                    metric_id="PI4060",
                    target_value=1000,
                    target_unit="clients",
                    description="1000 clients",
                ),
            ],
            reported_metrics={"PI4060": "1500"},
        )
        result = assess_target_progress(company)
        assert result["targets"][0]["status"] == "exceeded"
        assert result["targets"][0]["progress_pct"] == 150.0


class TestISSBS1:
    def test_ifrs_s1_framework_structure(self):
        from openharness.impact.frameworks.issb_ifrs_s1 import get_ifrs_s1_framework

        fw = get_ifrs_s1_framework()
        assert len(fw.pillars) == 4
        total_disclosures = sum(len(p.disclosures) for p in fw.pillars)
        assert total_disclosures >= 12

    def test_ifrs_s1_readiness(self):
        from openharness.impact.frameworks.issb_ifrs_s1 import assess_ifrs_s1_readiness

        result = assess_ifrs_s1_readiness(
            description="The board oversees sustainability strategy and risk management",
            reported_metrics={"OI4112": "100"},
            targets_set=True,
        )
        assert "overall_readiness" in result
        assert result["overall_readiness"] > 0
        assert result["assessment_basis"] == "screening_readiness_not_compliance_opinion"
        assert len(result["pillar_scores"]) == 4

    def test_issb_framework_tool_handler(self):
        from openharness.tools.impact.framework_tool import FrameworkInput
        inp = FrameworkInput(framework="issb_s1", action="list")
        assert inp.framework == "issb_s1"


class TestSASBExpanded:
    def test_sasb_has_25_industries(self):
        from openharness.impact.frameworks.sasb import get_sasb_industries
        industries = get_sasb_industries()
        assert len(industries) >= 25


class TestDataQualityTool:
    def test_data_quality_input_model(self):
        from openharness.tools.impact.data_quality_tool import DataQualityInput
        inp = DataQualityInput(
            reported_metrics={"OI4112": "500", "PI4060": "n/a"},
            required_metrics=["OI4112", "OI9090"],
        )
        assert inp.action == "assess"
        assert "OI4112" in inp.reported_metrics
        assert "OI9090" in inp.required_metrics

    def test_data_quality_placeholder_detection(self):
        from openharness.tools.impact.data_quality_tool import _PLACEHOLDER_VALUES
        assert "n/a" in _PLACEHOLDER_VALUES
        assert "tbd" in _PLACEHOLDER_VALUES
        assert "none" in _PLACEHOLDER_VALUES

    def test_extract_number(self):
        from openharness.tools.impact.data_quality_tool import _extract_number
        assert _extract_number("500") == 500.0
        assert _extract_number("1,200.50 tons") == 1200.50
        assert _extract_number("not a number") is None
        assert _extract_number("") is None

    def test_looks_numeric_metric(self):
        from openharness.tools.impact.data_quality_tool import _looks_numeric_metric
        assert _looks_numeric_metric("number of employees") is True
        assert _looks_numeric_metric("USD amount") is True
        assert _looks_numeric_metric(None) is True


class TestImpactRiskOpportunityTool:
    def test_risk_input_has_geography(self):
        from openharness.tools.impact.impact_risk_opportunity_tool import ImpactRiskOpportunityInput
        inp = ImpactRiskOpportunityInput(
            company_name="Test",
            description="A test company",
            geography="Kenya",
        )
        assert inp.geography == "Kenya"

    def test_risk_tool_import(self):
        from openharness.tools.impact.impact_risk_opportunity_tool import ImpactRiskOpportunityTool
        tool = ImpactRiskOpportunityTool()
        assert tool.name == "impact_risk_opportunity"

    def test_risk_tool_includes_esg_toolbox_recommendations(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.impact_risk_opportunity_tool import (
            ImpactRiskOpportunityInput,
            ImpactRiskOpportunityTool,
        )

        tool = ImpactRiskOpportunityTool()
        result = asyncio.run(
            tool.execute(
                ImpactRiskOpportunityInput(
                    company_name="Carbon Export Co",
                    company_description="Steel manufacturer with Scope 1 and Scope 2 emissions, EU export customers, and supplier audits.",
                    sector="steel manufacturing",
                    geography="EU",
                    reported_metrics={"OI4112": "1200 tCO2e", "OI6697": "2600 MWh"},
                    output_format="json",
                ),
                ToolExecutionContext(cwd=Path(".")),
            )
        )

        assert not result.is_error
        assert "esg_toolbox_recommendations" in result.metadata
        tool_ids = {item["tool_id"] for item in result.metadata["esg_toolbox_recommendations"]}
        assert {"ghg", "cbam"} & tool_ids
        assert "esg_ui" in result.metadata


class TestGapAnalysisESGIntegration:
    def test_gap_analysis_includes_esg_crosswalk_and_recommendations(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.gap_analysis_tool import GapAnalysisInput, GapAnalysisTool

        tool = GapAnalysisTool()
        result = asyncio.run(
            tool.execute(
                GapAnalysisInput(
                    company_name="Carbon Metrics Co",
                    reported_metrics={"OI4112": "1200 tCO2e", "OI6697": "2600 MWh"},
                    impact_themes=["Climate"],
                ),
                ToolExecutionContext(cwd=Path(".")),
            )
        )

        assert not result.is_error
        gap = result.metadata["gap_analysis"]
        assert "OI4112" in gap["esg_metric_crosswalk"]
        assert gap["esg_toolbox_recommendations"]
        assert "ESG Framework Crosswalk" in result.output
        assert "ESG Toolbox Leverage" in result.output

    def test_gap_analysis_uses_company_context_for_esg_routing(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.gap_analysis_tool import GapAnalysisInput, GapAnalysisTool

        tool = GapAnalysisTool()
        result = asyncio.run(
            tool.execute(
                GapAnalysisInput(
                    company_name="EU Steel Export Co",
                    company_description="Steel manufacturer exporting covered goods to EU customers.",
                    sector="steel manufacturing",
                    geography="EU",
                    reported_metrics={"PI2822": "100"},
                    impact_themes=["Climate"],
                ),
                ToolExecutionContext(cwd=Path(".")),
            )
        )

        assert not result.is_error
        gap = result.metadata["gap_analysis"]
        tool_ids = {item["tool_id"] for item in gap["esg_toolbox_recommendations"]}
        assert {"cbam", "cbam-steel"} & tool_ids


class TestMetricRecommenderTool:
    def test_recommender_input_has_geography(self):
        from openharness.tools.impact.metric_recommender_tool import MetricRecommenderInput
        inp = MetricRecommenderInput(
            company_name="Test",
            description="A test company",
            sector="Healthcare",
            geography="India",
        )
        assert inp.geography == "India"
        assert inp.sector == "Healthcare"

    def test_recommender_tool_import(self):
        from openharness.tools.impact.metric_recommender_tool import MetricRecommenderTool
        tool = MetricRecommenderTool()
        assert tool.name == "impact_metric_recommender"

    def test_recommender_includes_esg_toolbox_guidance(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.metric_recommender_tool import MetricRecommenderInput, MetricRecommenderTool

        tool = MetricRecommenderTool()
        result = asyncio.run(
            tool.execute(
                MetricRecommenderInput(
                    company_name="Carbon Export Co",
                    sector="steel manufacturing",
                    geography="EU",
                    description="Steel manufacturer with Scope 1 and Scope 2 emissions and EU export customers.",
                    impact_themes=["Climate"],
                    sdg_goals=[13],
                    reported_metrics={"OI4112": "1200 tCO2e", "OI6697": "2600 MWh"},
                    output_format="json",
                ),
                ToolExecutionContext(cwd=Path(".")),
            )
        )

        assert not result.is_error
        assert "esg_toolbox" in result.metadata
        tool_ids = {item["tool_id"] for item in result.metadata["esg_toolbox"]["recommended_tools"]}
        assert {"ghg", "cbam"} & tool_ids


class TestImpactReportESGIntegration:
    def test_report_includes_esg_toolbox_section(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool

        tool = ImpactReportTool()
        result = asyncio.run(
            tool.execute(
                ImpactReportInput(
                    company_name="Carbon Report Co",
                    company_description="Steel manufacturer with Scope 1 and Scope 2 emissions, EU customers, and supplier audits.",
                    sector="steel manufacturing",
                    geography="EU",
                    reported_metrics={"OI4112": "1200 tCO2e", "OI6697": "2600 MWh"},
                    output_format="text",
                ),
                ToolExecutionContext(cwd=Path(".")),
            )
        )

        assert not result.is_error
        report_data = result.metadata["report_data"]
        assert report_data["esg_toolbox"]["recommended_tools"]
        assert "ESG TOOLBOX READINESS" in result.output

    def test_html_report_renders_esg_toolbox_cards(self):
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool

        tool = ImpactReportTool()
        result = asyncio.run(
            tool.execute(
                ImpactReportInput(
                    company_name="Carbon HTML Co",
                    company_description="Battery manufacturer exporting to the EU with Scope 1 and Scope 2 data.",
                    sector="battery manufacturing",
                    geography="EU",
                    reported_metrics={"OI4112": "1200 tCO2e"},
                    output_format="html",
                ),
                ToolExecutionContext(cwd=Path(".")),
            )
        )

        assert not result.is_error
        html = result.metadata["html"]
        assert 'id="sec-esg-toolbox"' in html
        assert "ESG Toolbox Readiness" in html


class TestPortfolioInput:
    def test_portfolio_input_has_geography(self):
        from openharness.tools.impact.portfolio_tool import PortfolioInput
        inp = PortfolioInput(
            action="analyze_companies",
            geography="Southeast Asia",
            companies=[{"name": "A", "sector": "Energy"}],
        )
        assert inp.geography == "Southeast Asia"

    def test_aggregate_empty(self):
        from openharness.tools.impact.portfolio_tool import _aggregate_results
        result = _aggregate_results([])
        assert result == {}

    def test_company_from_dict_with_geography(self):
        from openharness.tools.impact.portfolio_tool import _dict_to_company
        company = _dict_to_company({"name": "Test Co", "sector": "Energy", "geography": "Kenya"})
        assert company.geography == "Kenya"
        assert company.name == "Test Co"


class TestPitchDeckGeoDetection:
    def test_detect_geography_kenya(self):
        from openharness.tools.impact.pitch_deck_analyze_tool import _detect_geography
        text = "Our company is based in Nairobi, Kenya and serves rural communities in East Africa."
        result = _detect_geography(text)
        assert result == "Kenya"

    def test_detect_geography_southeast_asia(self):
        from openharness.tools.impact.pitch_deck_analyze_tool import _detect_geography
        text = "We operate across Southeast Asia with offices in Jakarta and Ho Chi Minh City."
        assert "Southeast Asia" in _detect_geography(text) or "Indonesia" in _detect_geography(text) or "Vietnam" in _detect_geography(text)

    def test_detect_geography_empty(self):
        from openharness.tools.impact.pitch_deck_analyze_tool import _detect_geography
        text = "A generic company with no location mentions."
        result = _detect_geography(text)
        assert result == ""

    def test_detect_geography_headquartered_pattern(self):
        from openharness.tools.impact.pitch_deck_analyze_tool import _detect_geography
        text = "The company is headquartered in Singapore and has been growing rapidly."
        result = _detect_geography(text)
        assert result != ""


class TestSDGGeoBoost:
    def test_geo_boost_applied(self):
        from openharness.impact.models import Company
        from openharness.impact.sdg_mapper import _infer_sdg_from_description
        company_no_geo = Company(
            name="Test",
            description="A farming company",
            sector="agriculture",
        )
        company_with_geo = Company(
            name="Test",
            description="A farming company",
            sector="agriculture",
            geography="Kenya",
        )
        scores_no_geo = _infer_sdg_from_description(company_no_geo)
        scores_with_geo = _infer_sdg_from_description(company_with_geo)
        assert scores_with_geo.get(1, 0) >= scores_no_geo.get(1, 0)


class TestSDGKeywordsYAML:
    def test_yaml_loader_returns_dict(self):
        from openharness.impact.sdg_mapper import _load_sdg_keywords_config
        config = _load_sdg_keywords_config()
        assert isinstance(config, dict)

    def test_get_keyword_sdg_map_has_entries(self):
        from openharness.impact.sdg_mapper import _get_keyword_sdg_map
        kw_map = _get_keyword_sdg_map()
        assert len(kw_map) > 20
        assert "poverty" in kw_map

    def test_get_sector_sdg_relevance(self):
        from openharness.impact.sdg_mapper import _get_sector_sdg_relevance
        sector_map = _get_sector_sdg_relevance()
        assert "agriculture" in sector_map
        assert 2 in sector_map["agriculture"]


class TestConfigurableThreshold:
    def test_min_metrics_threshold_loaded(self):
        from openharness.impact.five_dimensions import MIN_METRICS_FOR_ABOVE_BASELINE
        assert isinstance(MIN_METRICS_FOR_ABOVE_BASELINE, int)
        assert MIN_METRICS_FOR_ABOVE_BASELINE >= 1

    def test_scoring_config_has_threshold(self):
        from openharness.impact.five_dimensions import _load_scoring_config
        config = _load_scoring_config()
        assert "min_metrics_for_above_baseline" in config


class TestEdgeCases:
    def test_empty_company_five_dimensions(self):
        from openharness.impact.five_dimensions import assess_five_dimensions
        from openharness.impact.database import get_metric_store
        from openharness.impact.models import Company
        try:
            store = get_metric_store()
        except FileNotFoundError:
            return
        company = Company(name="", description="")
        result = assess_five_dimensions(company, store)
        assert result.overall_score >= 0
        assert result.overall_grade in ("A", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F")

    def test_empty_company_sdg_mapper(self):
        from openharness.impact.sdg_mapper import map_sdg_alignment
        from openharness.impact.database import get_metric_store
        from openharness.impact.models import Company
        try:
            store = get_metric_store()
        except FileNotFoundError:
            return
        company = Company(name="", description="")
        result = map_sdg_alignment(company, store)
        assert isinstance(result, list)

    def test_sdg_alignment_provenance_default(self):
        from openharness.impact.models import SDGAlignment
        alignment = SDGAlignment(goal=1, goal_name="No Poverty", score=25.0, confidence="low")
        assert alignment.provenance == "estimated"

    def test_company_geography_default(self):
        from openharness.impact.models import Company
        company = Company(name="Test")
        assert company.geography == ""
