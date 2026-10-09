"""Tool registry helpers and top-level tool exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from .base import ToolRegistry

if TYPE_CHECKING:
    from impact_vision.mcp.client import McpClientManager


def _register_if_available(registry: ToolRegistry, module_name: str, class_name: str) -> None:
    """Register a tool class when its dependencies are importable."""
    try:
        module = import_module(f"impact_vision.tools.{module_name}")
        tool_cls = getattr(module, class_name)
    except Exception:
        return
    registry.register(tool_cls())


# Tool profiles (v7 W1.4). "developer" is the full coding-agent surface; "fund"
# is what a fund manager / consultant needs: the impact tools plus safe helpers
# to read uploaded files, research the web and ask questions — no shell, file
# writes, worktrees, agent orchestration or schedulers.
TOOL_PROFILES = ("developer", "fund")
TOOL_PROFILE_ENV = "IMPACT_VISION_TOOL_PROFILE"
_FUND_CORE_TOOLS = frozenset({
    "glob_tool",
    "grep_tool",
    "file_read_tool",
    "tool_search_tool",
    "skill_tool",
    "todo_write_tool",
    "web_fetch_tool",
    "web_search_tool",
    "ask_user_question_tool",
})


def resolve_tool_profile(profile: str | None = None) -> str:
    """Explicit *profile* → ``IMPACT_VISION_TOOL_PROFILE`` → ``developer``."""
    import os

    value = (profile or os.environ.get(TOOL_PROFILE_ENV) or "developer").strip().lower()
    if value not in TOOL_PROFILES:
        raise ValueError(f"Unknown tool profile {value!r}; choose from {', '.join(TOOL_PROFILES)}")
    return value


def create_default_tool_registry(
    mcp_manager: McpClientManager | None = None,
    *,
    profile: str | None = None,
) -> ToolRegistry:
    """Build a default tool registry with built-in tools and optional MCP tools.

    ``profile="fund"`` exposes only the impact tools plus safe read/research
    helpers (see ``TOOL_PROFILES``); the default ``developer`` profile keeps the
    full coding-agent surface.
    """
    profile = resolve_tool_profile(profile)
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
        if profile == "fund" and module_name not in _FUND_CORE_TOOLS:
            continue
        _register_if_available(registry, module_name, class_name)

    impact_tools: tuple[tuple[str, str], ...] = (
        ("impact.advisor_tool", "ImpactAdvisorTool"),
        ("impact.assess_deal_tool", "AssessDealTool"),
        # beneficiary_feedback merged into stakeholder_voice (v7 W1.5; deprecated alias in developer profile)
        ("impact.iris_catalog_tool", "IrisCatalogTool"),
        ("impact.sdg_mapper_tool", "SdgMapperTool"),
        ("impact.five_dimension_assess_tool", "FiveDimensionAssessTool"),
        ("impact.gap_analysis_tool", "GapAnalysisTool"),
        ("impact.dd_checklist_tool", "DdChecklistTool"),
        # document_analysis merged into pitch_deck_analyze (v7 W1.5; deprecated alias in developer profile)
        ("impact.exclusion_screening_tool", "ExclusionScreeningTool"),
        ("impact.merged_tools", "PitchDeckAnalyzeTool"),  # v7 W1.5 merged tool
        ("impact.greenwashing_tool", "GreenwashingDetectorTool"),
        # guided_assessment merged into pipeline (v7 W1.5; deprecated alias in developer profile)
        ("impact.hrdd_tool", "HRDDTool"),
        ("impact.impact_quantifier_tool", "ImpactQuantifierTool"),
        ("impact.impact_risk_opportunity_tool", "ImpactRiskOpportunityTool"),
        ("impact.impact_report_tool", "ImpactReportTool"),
        ("impact.impact_valuation_tool", "ImpactValuationTool"),
        ("impact.esg_toolbox_tool", "ESGToolboxTool"),
        ("impact.framework_tool", "FrameworkTool"),
        ("impact.improvement_advisor_tool", "ImprovementAdvisorTool"),
        ("impact.cross_reference_tool", "CrossReferenceTool"),
        ("impact.data_quality_tool", "DataQualityTool"),
        ("impact.decision_workflow_tool", "DecisionWorkflowTool"),
        # lp_ddq_export merged into ddq_responder (v7 W1.5; deprecated alias in developer profile)
        ("impact.metric_recommender_tool", "MetricRecommenderTool"),
        ("impact.monitoring_tool", "MonitoringTool"),
        # narrative merged into impact_report (narrative_mode + narrative_section)
        ("impact.merged_tools", "PipelineTool"),  # v7 W1.5 merged tool
        ("impact.portfolio_tool", "PortfolioTool"),
        ("impact.product_passport_tool", "ProductPassportTool"),
        ("impact.merged_tools", "RegulatoryCalendarTool"),  # v7 W1.5 merged tool
        ("impact.trend_analysis_tool", "TrendAnalysisTool"),
        # verification_prep merged into verification_workspace (prep actions)
        # v3 tools (0.15.0): trust infrastructure
        ("impact.emission_factors_tool", "EmissionFactorsTool"),
        ("impact.lca_tool", "LCAAssessmentTool"),
        ("impact.evidence_review_tool", "EvidenceReviewTool"),
        ("impact.exit_impact_tool", "ExitImpactTool"),
        # greenwashing_reviewer merged into greenwashing_detect (action='review_claims')
        ("impact.lp_narrative_tool", "LPNarrativeTool"),
        ("impact.portfolio_query_tool", "PortfolioQueryTool"),
        ("impact.merged_tools", "StakeholderVoiceTool"),  # v7 W1.5 merged tool
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
        # v6 tools: comparable, assured, connected
        ("impact.carbon_credit_tool", "CarbonCreditIntegrityTool"),
        ("impact.contribution_tool", "ContributionTrackerTool"),
        ("impact.merged_tools", "DDQResponderTool"),  # v7 W1.5 merged tool
        ("impact.dmrv_tool", "DMRVEvidenceTool"),
        ("impact.impact_linked_finance_tool", "ImpactLinkedFinanceTool"),
        # regulatory_radar merged into regulatory_calendar (v7 W1.5; deprecated alias in developer profile)
        ("impact.survey_delivery_tool", "SurveyDeliveryTool"),
    )
    for module_name, class_name in impact_tools:
        _register_if_available(registry, module_name, class_name)

    if profile == "developer":
        # One-release compatibility for tool names merged in v7 W1.5.
        try:
            from impact_vision.tools.impact.merged_tools import DEPRECATED_TOOLS
        except Exception:  # noqa: BLE001 - optional like every impact tool
            DEPRECATED_TOOLS = {}
        for alias_cls, _replacement in DEPRECATED_TOOLS.values():
            registry.register(alias_cls())

    if mcp_manager is not None:
        from .list_mcp_resources_tool import ListMcpResourcesTool
        from .mcp_tool import McpToolAdapter
        from .read_mcp_resource_tool import ReadMcpResourceTool

        registry.register(ListMcpResourcesTool(mcp_manager))
        registry.register(ReadMcpResourceTool(mcp_manager))
        for mcp_tool in mcp_manager.list_tools():
            registry.register(McpToolAdapter(mcp_manager, mcp_tool))

    return registry


__all__ = [
    "TOOL_PROFILES",
    "TOOL_PROFILE_ENV",
    "ToolRegistry",
    "create_default_tool_registry",
    "resolve_tool_profile",
]


def __getattr__(name: str):  # noqa: ANN201
    """``from impact_vision.tools import ImpactReportTool``: impact tool classes, lazily (0.17 API)."""
    impact_tools = import_module("impact_vision.tools.impact")
    try:
        return getattr(impact_tools, name)
    except AttributeError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
