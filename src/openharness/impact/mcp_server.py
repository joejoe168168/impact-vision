"""MCP Server for Impact Vision — exposes all impact tools as MCP tools/resources.

Usage:
    impact-vision serve-mcp                  # stdio transport (default)
    impact-vision serve-mcp --transport sse  # SSE transport on port 8765
    python -m openharness.impact.mcp_server  # direct invocation
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Newer FastMCP releases dropped the `version` / `description` kwargs from the
# constructor in favour of deriving them from the server name + installed
# package metadata. We keep the fields handy as module attributes so the CLI
# (`impact-vision serve-mcp`) and docs can still surface them.
IMPACT_VISION_MCP_NAME = "Impact Vision"
IMPACT_VISION_MCP_VERSION = "0.7.0"
IMPACT_VISION_MCP_DESCRIPTION = (
    "AI-powered impact measurement and SDG alignment tools for "
    "VC and impact investment funds. Provides 26+ tools for "
    "5-Dimension scoring, SDG mapping, greenwashing detection, "
    "pipeline management, and comprehensive impact reporting."
)


def _init_fastmcp() -> FastMCP:
    """Instantiate FastMCP with graceful fallback for older/newer signatures."""
    for kwargs in (
        # New signature (no version/description kwargs)
        {},
        # Older signature (pre-0.3) accepted version+description
        {"version": IMPACT_VISION_MCP_VERSION, "description": IMPACT_VISION_MCP_DESCRIPTION},
    ):
        try:
            return FastMCP(IMPACT_VISION_MCP_NAME, **kwargs)
        except TypeError:
            continue
    # Last resort — positional only
    return FastMCP(IMPACT_VISION_MCP_NAME)


mcp = _init_fastmcp()


def _get_tool_context():
    """Lazy import to avoid circular imports at module level."""
    from openharness.tools.base import ToolExecutionContext

    return ToolExecutionContext(cwd=Path.cwd())


def _make_company_dict(**kwargs) -> dict[str, Any]:
    """Build a normalized company dict from keyword arguments."""
    return {k: v for k, v in kwargs.items() if v is not None}


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("impact://catalog/stats")
def catalog_stats() -> str:
    """IRIS+ catalog statistics — metric count, categories, themes."""
    try:
        from openharness.impact.database import get_metric_store

        store = get_metric_store()
        metrics = store.all_metrics()
        categories: set[str] = set()
        themes: set[str] = set()
        for m in metrics:
            if m.primary_impact_category:
                categories.add(m.primary_impact_category)
            for theme in m.impact_themes:
                if theme:
                    themes.add(theme)
        return json.dumps(
            {
                "total_metrics": len(metrics),
                "categories": sorted(categories),
                "themes": sorted(themes),
            },
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.resource("impact://dd-checklist/categories")
def dd_checklist_categories() -> str:
    """DD checklist categories and question counts."""
    try:
        from openharness.impact.dd_checklist import load_checklist

        questions = load_checklist()
        cats: dict[str, int] = {}
        for q in questions:
            cat = q.category or "Unknown"
            cats[cat] = cats.get(cat, 0) + 1
        return json.dumps({"categories": cats, "total_questions": len(questions)}, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.resource("impact://frameworks/list")
def framework_list() -> str:
    """Available ESG/sustainability frameworks."""
    frameworks = [
        {"id": "iris", "name": "IRIS+ 5.3c", "metrics": "~800"},
        {"id": "gri", "name": "GRI Universal + Topic Standards", "standards": 34},
        {"id": "sasb", "name": "SASB Industry-Specific", "industries": "77+"},
        {"id": "tcfd", "name": "TCFD / IFRS S2 Climate", "pillars": 4},
        {"id": "sfdr", "name": "SFDR PAI Indicators", "indicators": 14},
        {"id": "edci", "name": "EDCI PE/VC ESG", "metrics": 17},
        {"id": "unpri", "name": "UNPRI 6 Principles", "actions": 27},
        {"id": "issb_s1", "name": "ISSB IFRS S1 General", "pillars": 4},
        {"id": "issb_s2", "name": "ISSB IFRS S2 Climate", "pillars": 4},
        {"id": "esrs", "name": "EU CSRD/ESRS", "topics": "12+"},
        {"id": "opim", "name": "IFC Operating Principles", "principles": 9},
    ]
    return json.dumps({"frameworks": frameworks}, indent=2)


@mcp.resource("impact://cross-reference/{metric_id}")
def cross_reference_lookup(metric_id: str) -> str:
    """Cross-reference lookup for a metric ID across all frameworks.

    Tries IRIS+, GRI, EDCI, and SFDR-PAI indexes in order.
    """
    try:
        from openharness.impact.frameworks.cross_reference import (
            lookup_by_edci,
            lookup_by_gri,
            lookup_by_iris,
            lookup_by_sfdr,
        )

        refs = lookup_by_iris(metric_id) or lookup_by_gri(metric_id) or lookup_by_edci(metric_id)
        if not refs:
            try:
                refs = lookup_by_sfdr(int(metric_id))
            except (TypeError, ValueError):
                refs = []
        return json.dumps(
            {
                "metric_id": metric_id,
                "match_count": len(refs),
                "cross_references": [r.model_dump() for r in refs],
            },
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.resource("impact://sdg/goals")
def sdg_goals_list() -> str:
    """UN SDG 17 goals reference data."""
    try:
        from openharness.impact.sdg_taxonomy import get_sdg_goals

        goals = [
            {
                "goal": g.number,
                "name": g.name,
                "description": g.description,
                "target_count": len(g.targets),
            }
            for g in get_sdg_goals()
        ]
        return json.dumps({"goals": goals, "total": len(goals)}, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tools — 5-Dimension Assessment
# ---------------------------------------------------------------------------


@mcp.tool()
async def five_dimension_assess(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    geography: str = "",
    impact_themes: list[str] | None = None,
    reported_metrics: dict[str, str] | None = None,
    focus_theme: str = "",
) -> str:
    """Score a company on the 5 Dimensions of Impact (What, Who, How Much, Contribution, Risk).

    Returns dimension scores (0-5), gap identification, overall grade, and recommendations.
    """
    from openharness.tools.impact.five_dimension_assess_tool import FiveDimensionAssessTool, FiveDimensionInput

    tool = FiveDimensionAssessTool()
    args = FiveDimensionInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        geography=geography,
        impact_themes=impact_themes or [],
        reported_metrics=reported_metrics or {},
        focus_theme=focus_theme,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def sdg_mapper(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    geography: str = "",
    impact_themes: list[str] | None = None,
    reported_metrics: dict[str, str] | None = None,
    sdg_claims: list[int] | None = None,
    sdg_goals: list[int] | None = None,
) -> str:
    """Map a company to UN SDG Goals and Targets with alignment scoring (0-100).

    Analyzes metric coverage, theme relevance, and data depth for each SDG.
    """
    from openharness.tools.impact.sdg_mapper_tool import SdgMapperInput, SdgMapperTool

    tool = SdgMapperTool()
    args = SdgMapperInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        geography=geography,
        impact_themes=impact_themes or [],
        reported_metrics=reported_metrics or {},
        sdg_claims=sdg_claims or [],
        sdg_goals=sdg_goals or [],
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def greenwashing_detect(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    impact_themes: list[str] | None = None,
    reported_metrics: dict[str, str] | None = None,
    sdg_claims: list[int] | None = None,
) -> str:
    """Detect greenwashing risk with 5 sub-scores and classification.

    Analyzes claim-metric gaps, adverse omissions, specificity, selectivity, and verification.
    """
    from openharness.tools.impact.greenwashing_tool import GreenwashingDetectorTool, GreenwashingInput

    tool = GreenwashingDetectorTool()
    args = GreenwashingInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        impact_themes=impact_themes or [],
        reported_metrics=reported_metrics or {},
        sdg_claims=sdg_claims or [],
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def gap_analysis(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    impact_themes: list[str] | None = None,
    reported_metrics: dict[str, str] | None = None,
) -> str:
    """Analyze gaps between reported metrics and the IRIS+ Core Metric Set.

    Returns coverage percentage, missing metrics, and recommendations.
    """
    from openharness.tools.impact.gap_analysis_tool import GapAnalysisInput, GapAnalysisTool

    tool = GapAnalysisTool()
    args = GapAnalysisInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        impact_themes=impact_themes or [],
        reported_metrics=reported_metrics or {},
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def iris_catalog(
    action: str = "search",
    query: str = "",
    metric_id: str = "",
    category: str = "",
    theme: str = "",
) -> str:
    """Search and browse the IRIS+ metric catalog (~800 metrics).

    Actions: search (by query), get (by ID), list (by category/theme).
    """
    from openharness.tools.impact.iris_catalog_tool import IrisCatalogInput, IrisCatalogTool

    tool = IrisCatalogTool()
    args = IrisCatalogInput(
        action=action, query=query, metric_id=metric_id, category=category, theme=theme
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def dd_checklist(
    action: str = "list",
    category: str = "",
    text: str = "",
    sector: str = "",
) -> str:
    """Access the 96-question impact due diligence checklist.

    Actions: list, categories, analyze (text against checklist), suggest (questions for sector).
    """
    from openharness.tools.impact.dd_checklist_tool import DdChecklistInput, DdChecklistTool

    tool = DdChecklistTool()
    args = DdChecklistInput(action=action, category=category, text=text, sector=sector)
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def framework_assess(
    framework: str,
    company_name: str = "",
    company_description: str = "",
    sector: str = "",
    reported_metrics: dict[str, str] | None = None,
) -> str:
    """Assess a company against ESG/sustainability frameworks.

    Frameworks: gri, sasb, tcfd, sfdr, edci, unpri, issb_s1, issb_s2, esrs, opim, all.
    """
    from openharness.tools.impact.framework_tool import FrameworkInput, FrameworkTool

    tool = FrameworkTool()
    args = FrameworkInput(
        framework=framework,
        company_name=company_name,
        description=company_description,
        sector=sector,
        reported_metrics=reported_metrics or {},
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def cross_reference(
    metric_id: str = "",
    framework: str = "",
    concept: str = "",
) -> str:
    """Look up cross-framework metric mappings (40+ concepts across 7 frameworks).

    Search by metric ID, framework, or concept keyword.
    """
    from openharness.tools.impact.cross_reference_tool import CrossReferenceInput, CrossReferenceTool

    tool = CrossReferenceTool()
    args = CrossReferenceInput(metric_id=metric_id, framework=framework, concept=concept)
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def impact_report(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    geography: str = "",
    impact_themes: list[str] | None = None,
    reported_metrics: dict[str, str] | None = None,
    sdg_claims: list[int] | None = None,
    output_format: str = "text",
    report_type: str = "full",
) -> str:
    """Generate a comprehensive impact assessment report.

    Formats: text, html, csv, json, xlsx, pdf.
    Report types: full, target_progress, lp_ready.
    """
    from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool

    tool = ImpactReportTool()
    args = ImpactReportInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        geography=geography,
        impact_themes=impact_themes or [],
        reported_metrics=reported_metrics or {},
        sdg_claims=sdg_claims or [],
        output_format=output_format,
        report_type=report_type,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def impact_data_quality(
    company_name: str,
    reported_metrics: dict[str, str] | None = None,
    sector: str = "",
) -> str:
    """Assess the quality of reported impact metrics.

    Checks for unknown IDs, placeholder values, non-numeric data, and completeness.
    """
    from openharness.tools.impact.data_quality_tool import DataQualityInput, DataQualityTool

    tool = DataQualityTool()
    args = DataQualityInput(
        company_name=company_name,
        reported_metrics=reported_metrics or {},
        sector=sector,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def exclusion_screening(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    reported_metrics: dict[str, str] | None = None,
) -> str:
    """Screen a company against exclusion criteria (UNGC, controversial weapons, fossil fuel, etc.).

    Returns pass/fail with flagged categories and severity.
    """
    from openharness.tools.impact.exclusion_screening_tool import ExclusionScreeningInput, ExclusionScreeningTool

    tool = ExclusionScreeningTool()
    args = ExclusionScreeningInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        reported_metrics=reported_metrics or {},
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def pitch_deck_analyze(
    file_path: str = "",
    text: str = "",
    url: str = "",
) -> str:
    """Analyze a pitch deck / investment memo for impact claims, SDG alignment, and DD gaps.

    Accepts file path (PDF/TXT/MD), raw text, or URL.
    """
    from openharness.tools.impact.pitch_deck_analyze_tool import PitchDeckAnalyzeInput, PitchDeckAnalyzeTool

    tool = PitchDeckAnalyzeTool()
    args = PitchDeckAnalyzeInput(file_path=file_path, text=text, url=url)
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def lp_ddq_export(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    geography: str = "",
    impact_themes: list[str] | None = None,
    reported_metrics: dict[str, str] | None = None,
    sdg_claims: list[int] | None = None,
    template: str = "ilpa",
    output_format: str = "text",
) -> str:
    """Export LP DDQ (Due Diligence Questionnaire) responses.

    Templates: ilpa, giin, edci, custom. Formats: text, xlsx.
    """
    from openharness.tools.impact.lp_ddq_export_tool import LpDdqExportInput, LpDdqExportTool

    tool = LpDdqExportTool()
    args = LpDdqExportInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        geography=geography,
        impact_themes=impact_themes or [],
        reported_metrics=reported_metrics or {},
        sdg_claims=sdg_claims or [],
        template=template,
        output_format=output_format,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def portfolio_analyze(
    action: str = "analyze",
    companies: list[dict[str, Any]] | None = None,
    file_path: str = "",
) -> str:
    """Analyze a portfolio of companies — aggregate scoring, benchmarking, attribution.

    Actions: analyze, rollup, benchmark, lp_report, attribution, what_if.
    """
    from openharness.tools.impact.portfolio_tool import PortfolioInput, PortfolioTool

    tool = PortfolioTool()
    args = PortfolioInput(
        action=action,
        companies=companies or [],
        file_path=file_path,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def impact_risk_opportunity(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    reported_metrics: dict[str, str] | None = None,
) -> str:
    """Assess impact risks and opportunities with likelihood x severity matrix.

    Identifies concentration, regulatory, reputational, exit, and data integrity risks.
    """
    from openharness.tools.impact.impact_risk_opportunity_tool import (
        ImpactRiskOpportunityInput,
        ImpactRiskOpportunityTool,
    )

    tool = ImpactRiskOpportunityTool()
    args = ImpactRiskOpportunityInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        reported_metrics=reported_metrics or {},
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def impact_metric_recommender(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    impact_themes: list[str] | None = None,
    reported_metrics: dict[str, str] | None = None,
    sdg_claims: list[int] | None = None,
) -> str:
    """Recommend IRIS+ metrics to track based on company profile and gaps.

    Prioritizes Core Metric Set metrics, then theme/SDG-aligned metrics.
    """
    from openharness.tools.impact.metric_recommender_tool import MetricRecommenderInput, MetricRecommenderTool

    tool = MetricRecommenderTool()
    args = MetricRecommenderInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        impact_themes=impact_themes or [],
        reported_metrics=reported_metrics or {},
        sdg_claims=sdg_claims or [],
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def trend_analysis(
    company_name: str,
    metric_history: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    """Analyze metric trends over time — detect improvement, decline, and trajectory.

    Provide metric_history as {metric_id: [{value, period, ...}, ...]}.
    """
    from openharness.tools.impact.trend_analysis_tool import TrendAnalysisInput, TrendAnalysisTool

    tool = TrendAnalysisTool()
    args = TrendAnalysisInput(
        company_name=company_name,
        metric_history=metric_history or {},
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def beneficiary_feedback(
    action: str,
    company_name: str = "",
    feedback_data: dict[str, Any] | None = None,
) -> str:
    """Import and analyze beneficiary feedback data (60 Decibels Lean Data format).

    Actions: import, summary, integrate.
    """
    from openharness.tools.impact.beneficiary_feedback_tool import BeneficiaryFeedbackInput, BeneficiaryFeedbackTool

    tool = BeneficiaryFeedbackTool()
    args = BeneficiaryFeedbackInput(
        action=action,
        company_name=company_name,
        feedback_data=feedback_data or {},
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def verification_prep(
    company_name: str,
    company_description: str = "",
    sector: str = "",
    reported_metrics: dict[str, str] | None = None,
    framework: str = "opim",
) -> str:
    """Prepare for third-party verification (BlueMark, IFC OPIM).

    Organizes evidence, identifies gaps, and generates a readiness checklist.
    """
    from openharness.tools.impact.verification_prep_tool import VerificationPrepInput, VerificationPrepTool

    tool = VerificationPrepTool()
    args = VerificationPrepInput(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        reported_metrics=reported_metrics or {},
        framework=framework,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def product_passport(
    action: str = "assess",
    product_data: dict[str, Any] | None = None,
) -> str:
    """EU Digital Product Passport (ESPR) data import and IRIS+ metric mapping.

    Actions: assess, map_metrics.
    """
    from openharness.tools.impact.product_passport_tool import ProductPassportInput, ProductPassportTool

    tool = ProductPassportTool()
    args = ProductPassportInput(action=action, product_data=product_data or {})
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def pipeline(
    action: str,
    company_name: str = "",
    stage: str = "",
    sector: str = "",
    notes: str = "",
) -> str:
    """Manage the investment pipeline — stages, transitions, dashboard.

    Actions: add, update, list, get, delete, transition, history, summary, dashboard.
    """
    from openharness.tools.impact.pipeline_tool import PipelineInput, PipelineTool

    tool = PipelineTool()
    args = PipelineInput(
        action=action,
        company_name=company_name,
        stage=stage,
        sector=sector,
        notes=notes,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def monitoring(
    action: str,
    company_name: str = "",
    metric_id: str = "",
    value: str = "",
    frequency: str = "quarterly",
) -> str:
    """Continuous monitoring — schedules, metric updates, alerts, re-assessment.

    Actions: set_schedule, get_schedule, list_due, record_metric, check_alerts, reassess, dashboard.
    """
    from openharness.tools.impact.monitoring_tool import MonitoringInput, MonitoringTool

    tool = MonitoringTool()
    args = MonitoringInput(
        action=action,
        company_name=company_name,
        metric_id=metric_id,
        value=value,
        frequency=frequency,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def improvement_advisor(
    action: str = "recommend",
    company_name: str = "",
    company_description: str = "",
    sector: str = "",
    geography: str = "",
    reported_metrics: dict[str, str] | None = None,
    sdg_claims: list[int] | None = None,
) -> str:
    """LLM-guided impact improvement recommendations.

    Actions: recommend (dimension recs), peer_insights (sector comparison), sdg_opportunities.
    """
    from openharness.tools.impact.improvement_advisor_tool import ImprovementAdvisorInput, ImprovementAdvisorTool

    tool = ImprovementAdvisorTool()
    args = ImprovementAdvisorInput(
        action=action,
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        geography=geography,
        reported_metrics=reported_metrics or {},
        sdg_claims=sdg_claims or [],
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def narrative(
    section: str = "executive_summary",
    company_name: str = "",
    company_description: str = "",
    sector: str = "",
    reported_metrics: dict[str, str] | None = None,
    audience: str = "investor",
) -> str:
    """Generate LLM-ready narrative prompts for impact reports.

    Sections: executive_summary, key_findings, impact_narrative, case_study, full.
    """
    from openharness.tools.impact.narrative_tool import NarrativeInput, NarrativeTool

    tool = NarrativeTool()
    args = NarrativeInput(
        section=section,
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        reported_metrics=reported_metrics or {},
        audience=audience,
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def document_analysis(
    action: str = "compare",
    documents: list[dict[str, Any]] | None = None,
    claims: list[str] | None = None,
) -> str:
    """Smart multi-document analysis — compare, detect changes, verify claims.

    Actions: compare (consistency), detect_changes (diffs), verify_claims (evidence search).
    """
    from openharness.tools.impact.document_analysis_tool import DocumentAnalysisInput, DocumentAnalysisTool

    tool = DocumentAnalysisTool()
    args = DocumentAnalysisInput(
        action=action,
        documents=documents or [],
        claims=claims or [],
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


@mcp.tool()
async def guided_assessment(
    action: str = "list_templates",
    template: str = "",
    company_name: str = "",
    step_id: str = "",
    data: dict[str, Any] | None = None,
) -> str:
    """Structured step-by-step impact assessment workflow.

    Actions: list_templates, start, status, next_step, submit_data.
    Templates: screening, dd (due diligence), monitoring.
    """
    from openharness.tools.impact.guided_assessment_tool import GuidedAssessmentInput, GuidedAssessmentTool

    tool = GuidedAssessmentTool()
    args = GuidedAssessmentInput(
        action=action,
        template=template,
        company_name=company_name,
        step_id=step_id,
        data=data or {},
    )
    result = await tool.execute(args, _get_tool_context())
    return result.output


# ---------------------------------------------------------------------------
# Direct invocation
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
