"""Agent tool for lifecycle assessment, LCSA, and life-cycle management."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from impact_vision.impact.lca import (
    assess_lca_readiness,
    build_lcm_plan,
    calculate_lca,
    calculate_lcsa,
    list_lcia_methods,
    run_lca_sensitivity,
)
from impact_vision.tools.base import BaseTool, ToolExecutionContext, ToolResult


class LCAAssessmentInput(BaseModel):
    """Input contract for the LCA/LCM tool."""

    action: Literal["assess", "readiness", "sensitivity", "management_plan", "lcsa", "list_methods"] = "assess"
    study: dict[str, Any] = Field(default_factory=dict, description="Goal/scope and functional-unit payload")
    flows: list[dict[str, Any]] = Field(default_factory=list, description="LCI flows with characterization factors")
    scenarios: list[dict[str, Any]] = Field(default_factory=list, description="Explicit what-if sensitivity scenarios")
    cost_lines: list[dict[str, Any]] = Field(default_factory=list, description="Lifecycle cost lines for LCC/LCSA")
    social_indicators: list[dict[str, Any]] = Field(default_factory=list, description="Disaggregated S-LCA indicators")
    discount_rate: float = Field(default=0.0, ge=0, description="LCC discount rate as a decimal")
    owners_by_stage: dict[str, str] = Field(default_factory=dict)
    due_period_by_stage: dict[str, str] = Field(default_factory=dict)
    output_format: Literal["json", "text"] = "json"


class LCAAssessmentTool(BaseTool):
    """ISO-aligned, provenance-aware LCA plus lifecycle-management action planning."""

    name = "lca_assessment"
    description = (
        "Run a transparent lifecycle assessment and management workflow: define goal/scope, "
        "functional unit, boundary, LCI and caller-supplied LCIA factors; inspect hotspots, "
        "data quality, sensitivity, LCC/S-LCA dimensions, readiness, and management actions. "
        "This is not a bundled ecoinvent/ReCiPe database."
    )
    input_model = LCAAssessmentInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        del context
        args = arguments if isinstance(arguments, LCAAssessmentInput) else LCAAssessmentInput.model_validate(arguments)
        if args.action == "list_methods":
            payload = {"methods": list_lcia_methods(), "note": "Metadata only; factors must be supplied or licensed separately."}
            return _format_result(args.action, payload, args.output_format)
        if not args.study:
            return ToolResult(output="study is required for this LCA action", is_error=True)
        try:
            if args.action == "assess":
                payload = calculate_lca(args.study, args.flows).model_dump(mode="json")
            elif args.action == "sensitivity":
                payload = run_lca_sensitivity(args.study, args.flows, args.scenarios).model_dump(mode="json")
            elif args.action == "readiness":
                payload = assess_lca_readiness(
                    args.study,
                    args.flows,
                    scenarios=args.scenarios,
                    cost_lines=args.cost_lines,
                    social_indicators=args.social_indicators,
                ).model_dump(mode="json")
            elif args.action == "management_plan":
                result = calculate_lca(args.study, args.flows)
                payload = build_lcm_plan(
                    result,
                    owners_by_stage=args.owners_by_stage,
                    due_period_by_stage=args.due_period_by_stage,
                ).model_dump(mode="json")
            elif args.action == "lcsa":
                payload = calculate_lcsa(
                    args.study,
                    args.flows,
                    cost_lines=args.cost_lines,
                    social_indicators=args.social_indicators,
                    discount_rate=args.discount_rate,
                ).model_dump(mode="json")
            else:  # pragma: no cover - Literal validation keeps this unreachable
                return ToolResult(output=f"Unknown action: {args.action}", is_error=True)
        except (TypeError, ValueError) as exc:
            return ToolResult(output=f"LCA assessment failed: {exc}", is_error=True)
        return _format_result(args.action, payload, args.output_format)


def _format_result(action: str, payload: dict[str, Any], output_format: str) -> ToolResult:
    if output_format == "text":
        return ToolResult(output=_render_text(action, payload), metadata=payload)
    return ToolResult(output=json.dumps(payload, ensure_ascii=False, indent=2), metadata=payload)


def _render_text(action: str, payload: dict[str, Any]) -> str:
    if action == "assess":
        impacts = payload.get("impacts", {})
        hotspots = payload.get("hotspots", [])
        lines = [
            "LCA ASSESSMENT",
            f"Study: {payload.get('study_id', '')}",
            f"Functional unit: {payload.get('functional_unit', '')}",
            "Impacts:",
            *[f"- {category}: {value} {payload.get('impact_units', {}).get(category, '')}" for category, value in impacts.items()],
            "Hotspots:",
            *[
                f"- {item['lifecycle_stage']} / {item['category']}: {item['share_pct']}%"
                for item in hotspots[:5]
            ],
        ]
        return "\n".join(lines)
    if action == "management_plan":
        lines = ["LIFE-CYCLE MANAGEMENT PLAN", payload.get("objective", ""), "Actions:"]
        lines.extend(
            f"- [{item['priority']}] {item['lifecycle_stage']}: {item['recommended_action']}"
            for item in payload.get("actions", [])
        )
        return "\n".join(lines)
    if action == "readiness":
        lines = [
            "LCA READINESS",
            f"Score: {payload.get('score', 0)}/100 ({payload.get('band', '')})",
            "Gaps:",
            *[f"- {gap}" for gap in payload.get("gaps", [])],
        ]
        return "\n".join(lines)
    return json.dumps(payload, ensure_ascii=False, indent=2)


__all__ = ["LCAAssessmentInput", "LCAAssessmentTool"]
