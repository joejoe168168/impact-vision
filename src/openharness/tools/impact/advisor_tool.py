"""Tool: impact_advisor — route a free-text query to the right impact tools."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.tool_advisor import (
    TOOL_ROUTES,
    get_playbook,
    list_playbooks,
    route_query,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ImpactAdvisorInput(BaseModel):
    action: Literal["route", "playbook", "list_playbooks", "catalog"] = Field(
        default="route",
        description=(
            "'route': rank the most relevant tools (and a playbook) for a free-text query. "
            "'playbook': get the full step list for a playbook_id. "
            "'list_playbooks': list all multi-step playbooks. "
            "'catalog': list every routed tool grouped by category."
        ),
    )
    query: str = Field(
        default="",
        description="Free-text description of what the user wants to do (action='route').",
    )
    playbook_id: str = Field(default="", description="Playbook id (action='playbook').")
    limit: int = Field(default=5, description="Max tool recommendations to return.")
    output_format: Literal["text", "json"] = Field(default="text")


class ImpactAdvisorTool(BaseTool):
    name = "impact_advisor"
    description = (
        "Tool router for the Impact Vision suite. Given a free-text request "
        "(e.g. 'check this deck for greenwashing', 'what SFDR deadlines apply?'), "
        "recommends the most relevant tools with example calls, and suggests a "
        "multi-step playbook (deal screening, LP reporting, regulatory compliance, "
        "verification, portfolio review, supply-chain HRDD, carbon & climate, "
        "data collection, theory of change). Use this first when unsure which "
        "impact tool to call."
    )
    input_model = ImpactAdvisorInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ImpactAdvisorInput) else ImpactAdvisorInput.model_validate(arguments)

        if args.action == "route":
            if not args.query.strip():
                return ToolResult(output="Provide 'query' describing what you want to do.", is_error=True)
            payload = route_query(args.query, limit=args.limit)
            if args.output_format == "json":
                return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)
            return ToolResult(output=self._route_text(payload), metadata=payload)

        if args.action == "playbook":
            pb = get_playbook(args.playbook_id)
            if pb is None:
                known = ", ".join(p["playbook_id"] for p in list_playbooks())
                return ToolResult(output=f"Unknown playbook '{args.playbook_id}'. Known: {known}", is_error=True)
            payload = pb.model_dump(mode="json")
            if args.output_format == "json":
                return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)
            lines = [f"PLAYBOOK: {pb.name} ({pb.playbook_id})", f"When to use: {pb.when_to_use}", ""]
            for i, step in enumerate(pb.steps, 1):
                lines.append(f"  {i}. {step.tool} — {step.purpose}")
            return ToolResult(output="\n".join(lines), metadata=payload)

        if args.action == "list_playbooks":
            playbooks = list_playbooks()
            payload = {"playbooks": playbooks}
            if args.output_format == "json":
                return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)
            lines = ["AVAILABLE PLAYBOOKS", "=" * 40]
            for p in playbooks:
                lines.append(f"- {p['playbook_id']}: {p['name']}")
                lines.append(f"    {p['when_to_use']}")
                lines.append(f"    Steps: {' -> '.join(p['steps'])}")
            return ToolResult(output="\n".join(lines), metadata=payload)

        # catalog
        by_category: dict[str, list[dict]] = {}
        for route in TOOL_ROUTES:
            by_category.setdefault(route.category, []).append(
                {"tool": route.tool, "summary": route.summary}
            )
        payload = {"categories": by_category}
        if args.output_format == "json":
            return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)
        lines = ["IMPACT TOOL CATALOG", "=" * 40]
        for category, tools in by_category.items():
            lines.append(f"\n[{category.upper()}]")
            for t in tools:
                lines.append(f"  - {t['tool']}: {t['summary']}")
        return ToolResult(output="\n".join(lines), metadata=payload)

    @staticmethod
    def _route_text(payload: dict) -> str:
        lines = [f"TOOL ROUTING: {payload['query']}", "=" * 50]
        recs = payload["recommendations"]
        if not recs:
            lines.append("No direct tool match. Try action='catalog' to browse all tools.")
        for i, rec in enumerate(recs, 1):
            lines.append(f"\n{i}. {rec['tool']} (score {rec['score']:.0f}, {rec['category']})")
            lines.append(f"   {rec['summary']}")
            lines.append(f"   Matched: {', '.join(rec['matched_keywords'])}")
            if rec.get("example"):
                lines.append(f"   Example: {rec['example']}")
        pb = payload.get("playbook")
        if pb:
            lines.append(f"\nSUGGESTED PLAYBOOK: {pb['name']} ({pb['playbook_id']})")
            lines.append(f"  {pb['when_to_use']}")
            for i, step in enumerate(pb["steps"], 1):
                lines.append(f"  {i}. {step['tool']} — {step['purpose']}")
        return "\n".join(lines)
