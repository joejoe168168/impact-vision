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
        ("impact.iris_catalog_tool", "IrisCatalogTool"),
        ("impact.sdg_mapper_tool", "SdgMapperTool"),
        ("impact.five_dimension_assess_tool", "FiveDimensionAssessTool"),
        ("impact.gap_analysis_tool", "GapAnalysisTool"),
        ("impact.dd_checklist_tool", "DdChecklistTool"),
        ("impact.pitch_deck_analyze_tool", "PitchDeckAnalyzeTool"),
        ("impact.impact_report_tool", "ImpactReportTool"),
        ("impact.framework_tool", "FrameworkTool"),
        ("impact.cross_reference_tool", "CrossReferenceTool"),
        ("impact.data_quality_tool", "DataQualityTool"),
        ("impact.lp_ddq_export_tool", "LpDdqExportTool"),
        ("impact.metric_recommender_tool", "MetricRecommenderTool"),
        ("impact.portfolio_tool", "PortfolioTool"),
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
