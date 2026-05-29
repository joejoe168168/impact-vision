"""Tool registry helpers and top-level tool exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from .base import ToolRegistry

if TYPE_CHECKING:
    from openharness.mcp.client import McpClientManager


def _register_if_available(registry: ToolRegistry, module_name: str, class_name: str) -> None:
    """Register a tool class when its dependencies are importable."""
    try:
        module = import_module(f"openharness.tools.{module_name}")
        tool_cls = getattr(module, class_name)
    except Exception:
        return
    registry.register(tool_cls())


def create_default_tool_registry(mcp_manager: McpClientManager | None = None) -> ToolRegistry:
    """Build a default tool registry with built-in tools and optional MCP tools."""
    registry = ToolRegistry()

    core_tools: tuple[tuple[str, str], ...] = (
        ("bash_tool", "BashTool"),
        ("glob_tool", "GlobTool"),
        ("grep_tool", "GrepTool"),
        ("file_read_tool", "FileReadTool"),
        ("file_write_tool", "FileWriteTool"),
        ("file_edit_tool", "FileEditTool"),
        ("notebook_edit_tool", "NotebookEditTool"),
        ("lsp_tool", "LspTool"),
        ("tool_search_tool", "ToolSearchTool"),
        ("config_tool", "ConfigTool"),
        ("skill_tool", "SkillTool"),
        ("todo_write_tool", "TodoWriteTool"),
        ("brief_tool", "BriefTool"),
        ("web_fetch_tool", "WebFetchTool"),
        ("web_search_tool", "WebSearchTool"),
        ("sleep_tool", "SleepTool"),
        ("ask_user_question_tool", "AskUserQuestionTool"),
        ("enter_worktree_tool", "EnterWorktreeTool"),
        ("exit_worktree_tool", "ExitWorktreeTool"),
        ("enter_plan_mode_tool", "EnterPlanModeTool"),
        ("exit_plan_mode_tool", "ExitPlanModeTool"),
        ("task_create_tool", "TaskCreateTool"),
        ("task_get_tool", "TaskGetTool"),
        ("task_list_tool", "TaskListTool"),
        ("task_output_tool", "TaskOutputTool"),
        ("task_stop_tool", "TaskStopTool"),
        ("task_update_tool", "TaskUpdateTool"),
        ("agent_tool", "AgentTool"),
        ("send_message_tool", "SendMessageTool"),
        ("cron_create_tool", "CronCreateTool"),
        ("cron_list_tool", "CronListTool"),
        ("cron_delete_tool", "CronDeleteTool"),
        ("cron_toggle_tool", "CronToggleTool"),
        ("remote_trigger_tool", "RemoteTriggerTool"),
        ("team_create_tool", "TeamCreateTool"),
        ("team_delete_tool", "TeamDeleteTool"),
        ("mcp_auth_tool", "McpAuthTool"),
    )
    for module_name, class_name in core_tools:
        _register_if_available(registry, module_name, class_name)

    impact_tools: tuple[tuple[str, str], ...] = (
        ("impact.beneficiary_feedback_tool", "BeneficiaryFeedbackTool"),
        ("impact.iris_catalog_tool", "IrisCatalogTool"),
        ("impact.sdg_mapper_tool", "SdgMapperTool"),
        ("impact.five_dimension_assess_tool", "FiveDimensionAssessTool"),
        ("impact.gap_analysis_tool", "GapAnalysisTool"),
        ("impact.dd_checklist_tool", "DdChecklistTool"),
        ("impact.document_analysis_tool", "DocumentAnalysisTool"),
        ("impact.exclusion_screening_tool", "ExclusionScreeningTool"),
        ("impact.pitch_deck_analyze_tool", "PitchDeckAnalyzeTool"),
        ("impact.greenwashing_tool", "GreenwashingDetectorTool"),
        ("impact.guided_assessment_tool", "GuidedAssessmentTool"),
        ("impact.hrdd_tool", "HRDDTool"),
        ("impact.impact_quantifier_tool", "ImpactQuantifierTool"),
        ("impact.impact_risk_opportunity_tool", "ImpactRiskOpportunityTool"),
        ("impact.impact_report_tool", "ImpactReportTool"),
        ("impact.impact_valuation_tool", "ImpactValuationTool"),
        ("impact.framework_tool", "FrameworkTool"),
        ("impact.improvement_advisor_tool", "ImprovementAdvisorTool"),
        ("impact.cross_reference_tool", "CrossReferenceTool"),
        ("impact.data_quality_tool", "DataQualityTool"),
        ("impact.decision_workflow_tool", "DecisionWorkflowTool"),
        ("impact.lp_ddq_export_tool", "LpDdqExportTool"),
        ("impact.metric_recommender_tool", "MetricRecommenderTool"),
        ("impact.monitoring_tool", "MonitoringTool"),
        ("impact.narrative_tool", "NarrativeTool"),
        ("impact.pipeline_tool", "PipelineTool"),
        ("impact.portfolio_tool", "PortfolioTool"),
        ("impact.product_passport_tool", "ProductPassportTool"),
        ("impact.regulatory_calendar_tool", "RegulatoryCalendarTool"),
        ("impact.trend_analysis_tool", "TrendAnalysisTool"),
        ("impact.verification_prep_tool", "VerificationPrepTool"),
        # v3 tools (0.15.0): trust infrastructure
        ("impact.emission_factors_tool", "EmissionFactorsTool"),
        ("impact.evidence_review_tool", "EvidenceReviewTool"),
        ("impact.exit_impact_tool", "ExitImpactTool"),
        ("impact.greenwashing_reviewer_tool", "GreenwashingReviewerTool"),
        ("impact.lp_narrative_tool", "LPNarrativeTool"),
        ("impact.portfolio_query_tool", "PortfolioQueryTool"),
        ("impact.stakeholder_voice_tool", "StakeholderVoiceTool"),
        ("impact.verification_workspace_tool", "VerificationWorkspaceTool"),
        # v4 tools (Wave 1): consultant engagement workspace
        ("impact.engagement_workspace_tool", "EngagementWorkspaceTool"),
        # v4 tools (Wave 2): ToC canvas + KPI framework builder (Track 2)
        ("impact.toc_builder_tool", "ToCBuilderTool"),
        # v4 tools (Tracks 3-10): consolidated engagement suite
        ("impact.engagement_suite_tool", "EngagementSuiteTool"),
        # v5 tools: frontier measurement, HRDD, climate scenarios, AI governance, investee portal
        ("impact.climate_scenario_tool", "ClimateScenarioTool"),
        ("impact.ai_governance_tool", "AIGovernanceTool"),
        ("impact.investee_portal_tool", "InvesteePortalTool"),
    )
    for module_name, class_name in impact_tools:
        _register_if_available(registry, module_name, class_name)

    if mcp_manager is not None:
        from .list_mcp_resources_tool import ListMcpResourcesTool
        from .mcp_tool import McpToolAdapter
        from .read_mcp_resource_tool import ReadMcpResourceTool

        registry.register(ListMcpResourcesTool(mcp_manager))
        registry.register(ReadMcpResourceTool(mcp_manager))
        for mcp_tool in mcp_manager.list_tools():
            registry.register(McpToolAdapter(mcp_manager, mcp_tool))

    return registry


__all__ = ["ToolRegistry", "create_default_tool_registry"]
