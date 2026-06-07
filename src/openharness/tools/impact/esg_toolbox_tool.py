"""Tool: Unified ESG/sustainability toolbox."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.toolbox import (
    TOOLBOX_CATEGORIES,
    assess_tool_readiness,
    build_esg_workflow,
    build_toolbox_input_plan,
    build_toolbox_workflow_plan,
    build_tool_checklist,
    crosswalk_reported_metrics,
    get_source_profile,
    get_toolbox_tool,
    list_toolbox_tools,
    search_toolbox_tools,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ESGToolboxInput(BaseModel):
    action: Literal[
        "list",
        "get",
        "search",
        "assess",
        "checklist",
        "methodology",
        "crosswalk",
        "source_profile",
        "workflow",
        "input_plan",
        "recommend",
    ] = Field(
        description="Action to run against the ESG toolbox registry."
    )
    tool_id: str = Field(default="", description="Tool ID or alias, e.g. 'cbam', 'gri', 'ecovadis', 'ghg'.")
    category: Literal["all", "disclosure", "rating", "export", "supplier", "carbon"] = "all"
    query: str = Field(default="", description="Search query for action='search'.")
    sector: str = Field(default="", description="Company sector or industry context.")
    jurisdiction: str = Field(default="", description="Jurisdiction or export market context.")
    company_description: str = Field(default="", description="Company description for readiness assessment.")
    document_text: str = Field(default="", description="Document text to check for evidence coverage.")
    reported_metrics: dict[str, object] = Field(default_factory=dict, description="Reported metric ID -> value.")
    product_code: str = Field(default="", description="CN/HS/product code for export-compliance modules.")
    country: str = Field(default="", description="Relevant country for export/import or supplier context.")
    supplier_profile: str = Field(default="", description="Supplier profile or audit context.")
    output_format: Literal["text", "json"] = "text"


class ESGToolboxTool(BaseTool):
    name = "esg_toolbox"
    description = (
        "Unified ESG/sustainability toolbox covering the 33 ohESG-inspired modules: "
        "disclosure standards, ESG ratings, export compliance, supplier ESG, and carbon accounting. "
        "Use it to list/search modules, inspect methodology and sources, build checklists, run readiness "
        "assessments, inspect scraped ohESG source profiles, and crosswalk Impact Vision metrics to sustainability frameworks."
    )
    input_model = ESGToolboxInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ESGToolboxInput) else ESGToolboxInput.model_validate(arguments)

        try:
            if args.action == "list":
                return self._list(args)
            if args.action == "search":
                return self._search(args)
            if args.action == "get":
                return self._get(args)
            if args.action == "methodology":
                return self._methodology(args)
            if args.action == "checklist":
                return self._checklist(args)
            if args.action == "assess":
                return self._assess(args)
            if args.action == "crosswalk":
                return self._crosswalk(args)
            if args.action == "source_profile":
                return self._source_profile(args)
            if args.action == "workflow":
                return self._workflow(args)
            if args.action == "input_plan":
                return self._input_plan(args)
            if args.action == "recommend":
                return self._recommend(args)
        except KeyError as e:
            return ToolResult(output=str(e), is_error=True)

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

    def _list(self, args: ESGToolboxInput) -> ToolResult:
        tools = list_toolbox_tools(None if args.category == "all" else args.category)
        payload = {
            "categories": TOOLBOX_CATEGORIES,
            "count": len(tools),
            "tools": [_tool_summary(tool) for tool in tools],
        }
        if args.output_format == "json":
            return _json(payload)

        lines = [f"ESG Toolbox modules ({payload['count']}):"]
        for tool in tools:
            lines.append(f"- {tool.tool_id}: {tool.title} [{', '.join(tool.categories)}]")
            lines.append(f"  {tool.description}")
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _search(self, args: ESGToolboxInput) -> ToolResult:
        tools = search_toolbox_tools(args.query, None if args.category == "all" else args.category)
        payload = {"query": args.query, "count": len(tools), "tools": [_tool_summary(tool) for tool in tools]}
        if args.output_format == "json":
            return _json(payload)
        lines = [f"ESG Toolbox search results for {args.query!r} ({len(tools)}):"]
        lines.extend(f"- {tool.tool_id}: {tool.title} [{', '.join(tool.categories)}]" for tool in tools)
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _get(self, args: ESGToolboxInput) -> ToolResult:
        if not args.tool_id:
            return ToolResult(output="tool_id is required for action='get'.", is_error=True)
        tool = get_toolbox_tool(args.tool_id)
        payload = tool.model_dump(mode="json")
        if args.output_format == "json":
            return _json(payload)
        lines = [
            f"{tool.title} ({tool.tool_id})",
            tool.description,
            f"ohESG source title: {tool.source_title or 'n/a'}",
            f"ohESG source description: {tool.source_description or 'n/a'}",
            f"Categories: {', '.join(tool.categories)}",
            f"Tags: {', '.join(tool.tags)}",
            f"ohESG tags: {', '.join(tool.source_tags) or 'n/a'}",
            f"Supported actions: {', '.join(tool.supported_actions)}",
            f"Requirements: {len(tool.requirements)}",
            f"ohESG embedded records indexed: {len(tool.source_index)}",
            "",
            "Sources:",
        ]
        lines.extend(f"- {source.title}: {source.url}" for source in tool.sources)
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _methodology(self, args: ESGToolboxInput) -> ToolResult:
        if not args.tool_id:
            return ToolResult(output="tool_id is required for action='methodology'.", is_error=True)
        tool = get_toolbox_tool(args.tool_id)
        payload = {
            "tool": _tool_summary(tool),
            "requirements": [req.model_dump(mode="json") for req in tool.requirements],
            "methods": [method.model_dump(mode="json") for method in tool.methods],
            "sources": [source.model_dump(mode="json") for source in tool.sources],
            "source_index_count": len(tool.source_index),
            "source_index_sample": [record.model_dump(mode="json") for record in tool.source_index[:20]],
            "source_policy": "ohESG is treated as a curated secondary source; official sources take precedence for compliance-sensitive use.",
        }
        if args.output_format == "json":
            return _json(payload)
        lines = [
            f"Methodology: {tool.title}",
            "Source policy: official sources take precedence for compliance-sensitive use; ohESG is a curated secondary quick-reference.",
            "",
            "Requirements:",
        ]
        for req in tool.requirements:
            lines.append(f"- {req.id}: {req.title}")
            if req.description:
                lines.append(f"  {req.description}")
        lines.append("\nSources:")
        lines.extend(f"- {source.publisher or source.title}: {source.url}" for source in tool.sources)
        if tool.source_index:
            lines.append("\nohESG embedded source records:")
            for record in tool.source_index[:12]:
                detail = f" [{record.category}]" if record.category else ""
                lines.append(f"- {record.record_id}: {record.title}{detail}")
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _checklist(self, args: ESGToolboxInput) -> ToolResult:
        if not args.tool_id:
            return ToolResult(output="tool_id is required for action='checklist'.", is_error=True)
        tool = get_toolbox_tool(args.tool_id)
        checklist = build_tool_checklist(tool)
        payload = {"tool": _tool_summary(tool), "questions": [q.model_dump(mode="json") for q in checklist]}
        if args.output_format == "json":
            return _json(payload)
        lines = [f"Checklist: {tool.title}"]
        for question in checklist:
            lines.append(f"- [{question.requirement_id}] {question.question}")
            if question.evidence_examples:
                lines.append(f"  Evidence: {', '.join(question.evidence_examples[:3])}")
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _assess(self, args: ESGToolboxInput) -> ToolResult:
        if not args.tool_id:
            return ToolResult(output="tool_id is required for action='assess'.", is_error=True)
        tool = get_toolbox_tool(args.tool_id)
        description = " ".join(part for part in [args.company_description, args.sector, args.jurisdiction] if part)
        result = assess_tool_readiness(
            tool,
            company_description=description,
            document_text=args.document_text,
            reported_metrics=args.reported_metrics,
            product_code=args.product_code,
            country=args.country,
            supplier_profile=args.supplier_profile,
        )
        payload = result.model_dump(mode="json")
        if args.output_format == "json":
            return _json(payload)
        lines = [
            f"{result.title} readiness: {result.score_pct}%",
            f"Confidence: {result.confidence}",
            f"Matched requirements: {', '.join(result.matched_requirement_ids) or 'none'}",
            f"Gaps: {', '.join(result.gap_requirement_ids) or 'none'}",
        ]
        if result.evidence_gaps:
            lines.append("\nEvidence gaps:")
            lines.extend(f"- {gap}" for gap in result.evidence_gaps[:8])
        if result.recommendations:
            lines.append("\nRecommendations:")
            lines.extend(f"- {rec}" for rec in result.recommendations[:8])
        lines.append("\nSources:")
        lines.extend(f"- {url}" for url in result.source_urls)
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _crosswalk(self, args: ESGToolboxInput) -> ToolResult:
        if not args.reported_metrics:
            return ToolResult(output="reported_metrics is required for action='crosswalk'.", is_error=True)
        mappings = crosswalk_reported_metrics(
            args.reported_metrics,
            tool_id=args.tool_id,
            category="" if args.category == "all" else args.category,
        )
        payload = {"reported_metrics": args.reported_metrics, "mappings": mappings}
        if args.output_format == "json":
            return _json(payload)
        lines = ["ESG toolbox metric crosswalk:"]
        if not mappings:
            lines.append("- No built-in crosswalk mappings found for the provided metric IDs.")
        for metric_id, refs in mappings.items():
            lines.append(f"- {metric_id}: {', '.join(refs)}")
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _source_profile(self, args: ESGToolboxInput) -> ToolResult:
        if not args.tool_id:
            return ToolResult(output="tool_id is required for action='source_profile'.", is_error=True)
        tool = get_toolbox_tool(args.tool_id)
        profile = get_source_profile(tool.tool_id)
        if profile is None:
            return ToolResult(output=f"No source profile found for {tool.tool_id}.", is_error=True)
        payload = profile.model_dump(mode="json")
        if args.output_format == "json":
            return _json(payload)
        lines = [
            f"ohESG source profile: {profile.source_title} ({profile.tool_id})",
            f"Impact Vision title: {tool.title}",
            f"Impact Vision description: {tool.description}",
            f"ohESG source description: {profile.source_description}",
            f"URL: {profile.url}",
            f"Page title: {profile.page_title or 'n/a'}",
            f"Meta description: {profile.meta_description or 'n/a'}",
            f"English/runtime tags: {', '.join(tool.tags) or 'n/a'}",
            f"Tags: {', '.join(profile.source_tags) or 'n/a'}",
            f"Embedded datasets: {', '.join(profile.embedded_data_keys) or 'none'}",
            "",
            "Top source keywords:",
            "- " + ", ".join(profile.keywords[:40]) if profile.keywords else "- none",
        ]
        if tool.source_index:
            lines.append("\nIndexed source records:")
            for record in tool.source_index[:12]:
                label = f"{record.title}"
                if record.summary:
                    label += f" - {record.summary[:140]}"
                lines.append(f"- {label}")
        if profile.headings:
            lines.append("\nPage headings:")
            lines.extend(f"- {heading}" for heading in profile.headings[:12])
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _workflow(self, args: ESGToolboxInput) -> ToolResult:
        if not args.tool_id:
            return ToolResult(output="tool_id is required for action='workflow'.", is_error=True)
        plan = build_toolbox_workflow_plan(
            args.tool_id,
            company_description=args.company_description,
            sector=args.sector,
            jurisdiction=args.jurisdiction,
            document_text=args.document_text,
            reported_metrics=args.reported_metrics,
            product_code=args.product_code,
            country=args.country,
            supplier_profile=args.supplier_profile,
        )
        payload = plan.model_dump(mode="json")
        if args.output_format == "json":
            return _json(payload)
        lines = [
            f"Workflow plan: {plan.title} ({plan.tool_id})",
            f"Input completion: {plan.input_plan.completion_pct}%",
            f"Primary UX view: {plan.output_blueprint.primary_view}",
            "",
            "Improves existing Impact Vision tools:",
        ]
        for rec in plan.improves_impact_tools:
            lines.append(f"- [{rec.priority}] {rec.impact_tool}: {rec.improvement}")
            lines.append(f"  Handoff: {rec.handoff}")
        lines.append("\nSuggested sequence:")
        lines.extend(f"- {step}" for step in plan.suggested_sequence)
        lines.append("\nRecommended output widgets:")
        lines.extend(f"- {widget}" for widget in plan.output_blueprint.widgets)
        if plan.input_plan.next_questions:
            lines.append("\nAsk only these next questions:")
            lines.extend(f"- {question}" for question in plan.input_plan.next_questions)
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _input_plan(self, args: ESGToolboxInput) -> ToolResult:
        if not args.tool_id:
            return ToolResult(output="tool_id is required for action='input_plan'.", is_error=True)
        plan = build_toolbox_input_plan(
            args.tool_id,
            company_description=args.company_description,
            sector=args.sector,
            jurisdiction=args.jurisdiction,
            document_text=args.document_text,
            reported_metrics=args.reported_metrics,
            product_code=args.product_code,
            country=args.country,
            supplier_profile=args.supplier_profile,
        )
        payload = plan.model_dump(mode="json")
        if args.output_format == "json":
            return _json(payload)
        lines = [f"Minimal input plan: {plan.title} ({plan.tool_id})", f"Completion: {plan.completion_pct}%", ""]
        lines.append("Minimum fields:")
        for field in plan.minimum_fields:
            suffix = f" - {field.value_preview}" if field.value_preview else ""
            lines.append(f"- [{field.status}] {field.label}: {field.reason}{suffix}")
        if plan.next_questions:
            lines.append("\nNext questions:")
            lines.extend(f"- {question}" for question in plan.next_questions)
        lines.append("\nAI assist steps:")
        lines.extend(f"- {step}" for step in plan.ai_assist_steps)
        return ToolResult(output="\n".join(lines), metadata=payload)

    def _recommend(self, args: ESGToolboxInput) -> ToolResult:
        workflow = build_esg_workflow(
            company_description=args.company_description,
            sector=args.sector,
            geography=args.country,
            jurisdiction=args.jurisdiction,
            impact_themes=[],
            reported_metrics=args.reported_metrics,
            document_text=args.document_text,
            product_code=args.product_code,
            country=args.country,
            supplier_profile=args.supplier_profile,
            query=args.query,
            category=args.category,
            limit=8,
        )
        payload = workflow.model_dump(mode="json")
        if args.output_format == "json":
            return _json(payload)

        lines = ["Recommended ESG toolbox modules:"]
        if not workflow.recommended_tools:
            lines.append("- No high-confidence modules found. Add sector, geography, metrics, product, or supplier context.")
        for item in workflow.recommended_tools:
            lines.append(f"- {item.tool_id}: {item.title} ({item.readiness_score_pct}% readiness)")
            lines.append(f"  {item.reason}")
            if item.missing_inputs:
                lines.append(f"  Missing inputs: {', '.join(item.missing_inputs)}")
        if workflow.input_suggestions:
            lines.append("\nAI-assisted input reduction:")
            for suggestion in workflow.input_suggestions:
                value = f" = {suggestion.value}" if suggestion.value else ""
                lines.append(f"- {suggestion.field}{value}: {suggestion.reason}")
        if workflow.next_questions:
            lines.append("\nAsk only these next questions:")
            lines.extend(f"- {question}" for question in workflow.next_questions)
        lines.append("\nUI output:")
        summary = workflow.ui.get("summary", {})
        lines.append(f"- Recommended cards: {summary.get('recommended_count', 0)}")
        for card in workflow.ui.get("cards", [])[:6]:
            lines.append(f"- [{card['priority']}] {card['title']}: {card['status']}")
        return ToolResult(output="\n".join(lines), metadata=payload)


def _tool_summary(tool: object) -> dict[str, object]:
    return {
        "tool_id": tool.tool_id,
        "title": tool.title,
        "description": tool.description,
        "url": tool.url,
        "categories": tool.categories,
        "tags": tool.tags,
        "source_title": getattr(tool, "source_title", ""),
        "source_description": getattr(tool, "source_description", ""),
        "source_tags": getattr(tool, "source_tags", []),
        "source_index_count": len(getattr(tool, "source_index", [])),
        "as_of": tool.as_of,
    }


def _json(payload: dict[str, object]) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)


__all__ = ["ESGToolboxInput", "ESGToolboxTool"]
