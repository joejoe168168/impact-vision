"""Agent tool: Theory of Change canvas + KPI framework builder (v4 Track 2).

Wraps :mod:`openharness.impact.engagements.toc_builder` so an LLM agent
can drive the whole Track 2 flow with one tool:

* ``draft_canvas`` — deterministically sketch a canvas from structured
  intake (problem / stakeholders / inputs / activities / outputs / outcomes
  / impact / assumptions / risks). Consultants are expected to then run
  ``attach_canvas`` against an existing engagement and start reviewing.
* ``attach_canvas`` — persist the canvas on an engagement.
* ``validate`` — run the rules-based logic-chain validator.
* ``generate_kpi`` — generate a multi-framework KPI framework.
* ``lock_kpi`` — freeze the framework so downstream tools treat it as
  immutable.
* ``render_markdown`` / ``render_mermaid`` — render the canvas for reports.

The tool operates on the same module-level
:class:`~openharness.impact.engagements.EngagementWorkspace` singleton the
``engagement_workspace`` tool uses, so the two can be composed in a single
agent session without any explicit glue.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.engagements import toc_builder as _toc
from openharness.impact.engagements.toc_builder import ToCCanvas
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.tools.impact.engagement_workspace_tool import _workspace


ToCAction = Literal[
    "draft_canvas",
    "attach_canvas",
    "get_canvas",
    "validate",
    "mark_node_reviewed",
    "generate_kpi",
    "lock_kpi",
    "promote_kpis",
    "get_kpi",
    "render_markdown",
    "render_mermaid",
]


class ToCBuilderInput(BaseModel):
    """Input schema for the ToC builder tool — fields are action-scoped."""

    action: ToCAction
    engagement_id: str = ""

    # draft_canvas
    name: str = ""
    problem_statement: str = ""
    stakeholders: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    activities: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    impact: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    ai_confidence: float = 0.6

    # attach_canvas / render / validate
    canvas: dict[str, Any] = Field(default_factory=dict)
    """When provided, overrides the engagement's stored canvas (useful for
    applying consultant edits in a single round-trip)."""

    # mark_node_reviewed
    node_id: str = ""
    reviewed: bool = True

    # generate_kpi
    sector: str = ""
    geography: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    sdg_goals: list[int] = Field(default_factory=list)
    per_outcome_limit: int = 3
    include_core_set: bool = True
    target_by_period: str = ""
    target_condition_kind: Literal["condition_precedent", "covenant", "aspiration"] = "covenant"

    # shared
    actor: str = ""
    direction: Literal["LR", "TD", "RL", "BT"] = "LR"
    output_format: Literal["json", "text"] = "json"


class ToCBuilderTool(BaseTool):
    name = "toc_builder"
    description = (
        "Theory of Change canvas + KPI framework builder (roadmap-v4 Track 2). "
        "Draft a ToC canvas from structured intake, attach it to an "
        "engagement, run the rules-based logic-chain validator (missing "
        "assumptions, weak links, unmeasured outcomes, risk blind spots), "
        "generate a KPI framework mapped across IRIS+, SDG, GRI, EDCI, ESRS, "
        "ISSB, TCFD, and SFDR PAI, and render the canvas as Mermaid/Markdown. "
        "Every state-changing action routes through the engagement audit trail."
    )
    input_model = ToCBuilderInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = (
            arguments
            if isinstance(arguments, ToCBuilderInput)
            else (ToCBuilderInput.model_validate(arguments))
        )
        return args.action in {
            "draft_canvas",
            "get_canvas",
            "validate",
            "get_kpi",
            "promote_kpis",
            "render_markdown",
            "render_mermaid",
        }

    async def execute(
        self,
        arguments: BaseModel,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context
        args = (
            arguments
            if isinstance(arguments, ToCBuilderInput)
            else ToCBuilderInput.model_validate(arguments)
        )
        workspace = _workspace()

        try:
            payload = self._dispatch(args, workspace)
        except (KeyError, ValueError) as exc:
            return ToolResult(output=str(exc), is_error=True)

        if args.output_format == "text" and args.action in {
            "render_mermaid",
            "render_markdown",
        }:
            return ToolResult(output=payload["rendered"], metadata=payload)
        return ToolResult(
            output=json.dumps(payload, indent=2, default=str),
            metadata=payload,
        )

    def _dispatch(self, args: ToCBuilderInput, workspace) -> dict[str, Any]:
        if args.action == "draft_canvas":
            canvas = _toc.draft_toc_from_intake(
                name=args.name or "Theory of Change",
                engagement_id=args.engagement_id,
                problem_statement=args.problem_statement,
                stakeholders=args.stakeholders,
                inputs=args.inputs,
                activities=args.activities,
                outputs=args.outputs,
                outcomes=args.outcomes,
                impact=args.impact,
                assumptions=args.assumptions,
                risks=args.risks,
                ai_confidence=args.ai_confidence,
            )
            return {"canvas": canvas.model_dump(mode="json")}

        if args.action == "attach_canvas":
            if not args.engagement_id:
                raise ValueError("engagement_id is required")
            if not args.canvas:
                raise ValueError("canvas payload is required for attach_canvas")
            canvas = ToCCanvas.model_validate(args.canvas)
            stored = workspace.attach_toc_canvas(
                args.engagement_id,
                canvas,
                actor=args.actor or "consultant",
            )
            return {"canvas": stored.model_dump(mode="json")}

        if args.action == "get_canvas":
            canvas = workspace.get_toc_canvas(args.engagement_id)
            return {"canvas": canvas.model_dump(mode="json")}

        if args.action == "validate":
            if args.canvas:
                canvas = ToCCanvas.model_validate(args.canvas)
                report = _toc.validate_toc_canvas(canvas)
            else:
                report = workspace.validate_toc(args.engagement_id)
            return {"report": report.model_dump(mode="json")}

        if args.action == "mark_node_reviewed":
            if not args.engagement_id or not args.node_id:
                raise ValueError("engagement_id and node_id are required")
            canvas = workspace.mark_toc_node_reviewed(
                args.engagement_id,
                args.node_id,
                actor=args.actor or "consultant",
                reviewed=args.reviewed,
            )
            return {"canvas": canvas.model_dump(mode="json")}

        if args.action == "generate_kpi":
            framework = workspace.generate_kpi_framework_for(
                args.engagement_id,
                sector=args.sector,
                geography=args.geography,
                impact_themes=args.impact_themes or None,
                sdg_goals=args.sdg_goals or None,
                per_outcome_limit=args.per_outcome_limit,
                include_core_set=args.include_core_set,
                actor=args.actor or "system",
            )
            return {"framework": framework.model_dump(mode="json")}

        if args.action == "lock_kpi":
            framework = workspace.lock_kpi_framework_for(
                args.engagement_id,
                actor=args.actor or "consultant",
            )
            return {"framework": framework.model_dump(mode="json")}

        if args.action == "get_kpi":
            framework = workspace.get_kpi_framework(args.engagement_id)
            return {"framework": framework.model_dump(mode="json")}

        if args.action == "promote_kpis":
            framework = workspace.get_kpi_framework(args.engagement_id)
            targets = _toc.promote_kpis_to_conditions(
                framework,
                by_period=args.target_by_period or None,
                condition_kind=args.target_condition_kind,
            )
            return {"target_conditions": [item.model_dump(mode="json") for item in targets]}

        if args.action == "render_mermaid":
            canvas = (
                ToCCanvas.model_validate(args.canvas)
                if args.canvas
                else workspace.get_toc_canvas(args.engagement_id)
            )
            return {
                "rendered": _toc.render_canvas_mermaid(canvas, direction=args.direction),
                "canvas_id": canvas.canvas_id,
            }

        if args.action == "render_markdown":
            canvas = (
                ToCCanvas.model_validate(args.canvas)
                if args.canvas
                else workspace.get_toc_canvas(args.engagement_id)
            )
            return {
                "rendered": _toc.render_canvas_markdown(canvas, direction=args.direction),
                "canvas_id": canvas.canvas_id,
            }

        raise ValueError(f"Unknown toc_builder action: {args.action}")


__all__ = ["ToCBuilderTool"]
