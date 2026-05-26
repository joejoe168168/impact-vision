"""Tool: Fund-manager decision workflows for screening and IC outputs."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.database import ensure_catalog_loaded
from openharness.impact.decision_workflow import (
    assess_lp_readiness,
    build_ic_workflow_summary,
    compare_deals,
    quick_screen,
)
from openharness.impact.fund_thesis import load_fund_thesis
from openharness.impact.models import Company
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sdg_goals, normalize_sector


class DecisionWorkflowInput(BaseModel):
    action: Literal["quick_screen", "ic_workflow", "deal_compare", "lp_readiness"] = Field(
        description=(
            "'quick_screen': 60-second Aligned/Improvable/Red Flag screen. "
            "'ic_workflow': full IC summary with memo, verdict, and proof appendix. "
            "'deal_compare': compare company_a and company_b. "
            "'lp_readiness': LP-ready badge and blockers."
        )
    )
    company_name: str = ""
    company_description: str = ""
    sector: str = ""
    geography: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    claims: list[dict] = Field(default_factory=list)
    metric_records: list[dict] = Field(default_factory=list)
    company_a: dict = Field(default_factory=dict)
    company_b: dict = Field(default_factory=dict)
    thesis_path: str = ""
    dd_coverage_pct: float | None = None
    exclusion_pass: bool | None = None
    memo_format: Literal["markdown", "html"] = "markdown"
    output_format: Literal["json", "text"] = "json"


def _company_from_fields(args: DecisionWorkflowInput) -> Company:
    metrics, _ = normalize_metric_map(args.reported_metrics)
    sdgs, _ = normalize_sdg_goals(args.sdg_claims)
    return Company(
        name=args.company_name,
        description=args.company_description,
        sector=normalize_sector(args.sector),
        geography=args.geography,
        impact_themes=infer_themes(f"{args.company_description} {args.sector}", args.impact_themes),
        reported_metrics=metrics,
        sdg_claims=sdgs,
    )


def _company_from_dict(data: dict) -> Company:
    metrics, _ = normalize_metric_map(data.get("reported_metrics", {}))
    sdgs, _ = normalize_sdg_goals(data.get("sdg_claims", []))
    description = data.get("description", data.get("company_description", ""))
    sector = data.get("sector", "")
    return Company(
        name=data.get("name", data.get("company_name", "")),
        description=description,
        sector=normalize_sector(sector),
        geography=data.get("geography", ""),
        impact_themes=infer_themes(f"{description} {sector}", data.get("impact_themes", [])),
        reported_metrics=metrics,
        sdg_claims=sdgs,
    )


class DecisionWorkflowTool(BaseTool):
    name = "decision_workflow"
    description = (
        "Fund-manager decision workflows: quick screen, IC workflow summary with proof appendix, "
        "deal comparison, and LP readiness badge. Uses existing 5D, SDG, greenwashing, and IC gates."
    )
    input_model = DecisionWorkflowInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, DecisionWorkflowInput) else DecisionWorkflowInput.model_validate(arguments)
        try:
            store = ensure_catalog_loaded()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)
        thesis = load_fund_thesis(args.thesis_path or None)

        if args.action == "deal_compare":
            if not args.company_a or not args.company_b:
                return ToolResult(output="company_a and company_b are required for deal_compare", is_error=True)
            a = build_ic_workflow_summary(_company_from_dict(args.company_a), store, thesis)
            b = build_ic_workflow_summary(_company_from_dict(args.company_b), store, thesis)
            payload = compare_deals(a, b).model_dump(mode="json")
            return _result(payload, args.output_format)

        company = _company_from_fields(args)
        if not company.name:
            return ToolResult(output="company_name is required", is_error=True)

        if args.action == "quick_screen":
            payload = quick_screen(
                company,
                store,
                thesis,
                claims=args.claims,
                dd_coverage_pct=args.dd_coverage_pct,
                exclusion_pass=args.exclusion_pass,
            ).model_dump(mode="json")
            return _result(payload, args.output_format)

        summary = build_ic_workflow_summary(
            company,
            store,
            thesis,
            claims=args.claims,
            metric_records=args.metric_records,
            dd_coverage_pct=args.dd_coverage_pct,
            exclusion_pass=args.exclusion_pass,
            memo_format=args.memo_format,
        )
        if args.action == "ic_workflow":
            return _result(summary.model_dump(mode="json"), args.output_format)
        if args.action == "lp_readiness":
            return _result(assess_lp_readiness(summary).model_dump(mode="json"), args.output_format)
        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)


def _result(payload: dict, output_format: str) -> ToolResult:
    if output_format == "text":
        # Render scalar/list/dict fields first, then append the memo block at
        # the bottom so a CLI consumer of ic_workflow gets the full IC memo
        # (which is usually the primary deliverable). Earlier versions
        # silently dropped 'memo' under output_format='text', which made the
        # tool effectively useless for CLI workflows.
        lines: list[str] = []
        memo: object | None = None
        for key, value in payload.items():
            if key == "memo":
                memo = value
                continue
            lines.append(f"{key}: {value}")
        if memo:
            lines.append("")
            lines.append("=" * 50)
            lines.append("MEMO")
            lines.append("=" * 50)
            if isinstance(memo, dict):
                for sub_key, sub_value in memo.items():
                    lines.append(f"\n[{sub_key}]")
                    lines.append(str(sub_value))
            else:
                lines.append(str(memo))
        return ToolResult(output="\n".join(lines), metadata=payload)
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)


__all__ = ["DecisionWorkflowInput", "DecisionWorkflowTool"]
