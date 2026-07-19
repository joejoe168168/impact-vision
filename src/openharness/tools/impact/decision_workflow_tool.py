"""Tool: Fund-manager decision workflows for screening and IC outputs."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.database import ensure_catalog_loaded
from openharness.impact.deal_gate import TargetCondition, gate_with_targets
from openharness.impact.decision_workflow import (
    assess_lp_readiness,
    build_ic_workflow_summary,
    compare_deals,
    quick_screen,
)
from openharness.impact.fund_thesis import load_fund_thesis
from openharness.impact.impact_target_setter import TargetSetterInput, set_impact_targets
from openharness.impact.engagements.toc_builder import KPIFramework, promote_kpis_to_conditions
from openharness.impact.models import Company
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.tools.impact.common import (
    infer_themes,
    normalize_metric_map,
    normalize_sdg_goals,
    normalize_sector,
)


class DecisionWorkflowInput(BaseModel):
    action: Literal[
        "quick_screen",
        "ic_workflow",
        "deal_compare",
        "lp_readiness",
        "set_targets",
        "gate_with_targets",
        "promote_kpis",
    ] = Field(
        description=(
            "'quick_screen': 60-second Aligned/Improvable/Red Flag screen. "
            "'ic_workflow': full IC summary with memo, verdict, and proof appendix. "
            "'deal_compare': compare company_a and company_b. "
            "'lp_readiness': LP-ready badge and blockers. "
            "'set_targets': context-driven impact-target ranges from theme/geography/capital."
            " 'gate_with_targets': require binding targets before a positive gate."
            " 'promote_kpis': convert a locked ToC KPI framework into deal conditions."
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
    # Target-setter (action='set_targets')
    target_theme: str = Field(
        default="", description="Impact theme for set_targets (e.g. 'financial_inclusion')"
    )
    target_capital_usd: float = Field(default=0.0, description="Capital to deploy for set_targets")
    target_horizon_years: int = Field(default=5, description="Time horizon (years) for set_targets")
    target_ambition: Literal["conservative", "base", "stretch"] = "base"
    deal: dict = Field(default_factory=dict)
    target_conditions: list[dict] = Field(default_factory=list)
    kpi_framework_id: str = ""
    kpi_framework: dict = Field(default_factory=dict)
    target_by_period: str = ""
    target_condition_kind: Literal["condition_precedent", "covenant", "aspiration"] = "covenant"
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
        "deal comparison, LP readiness badge, and context-driven impact target setting "
        "(theme/geography/capital -> conservative/base/stretch IRIS+/SDG target ranges). "
        "Uses existing 5D, SDG, greenwashing, and IC gates."
    )
    input_model = DecisionWorkflowInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, DecisionWorkflowInput)
            else DecisionWorkflowInput.model_validate(arguments)
        )

        if args.action == "set_targets":
            theme = args.target_theme or (
                args.impact_themes[0] if args.impact_themes else "general"
            )
            result = set_impact_targets(
                TargetSetterInput(
                    theme=theme,
                    geography=args.geography or "unknown",
                    capital_usd=args.target_capital_usd,
                    time_horizon_years=args.target_horizon_years,
                    ambition=args.target_ambition,
                )
            )
            return _result(result.model_dump(mode="json"), args.output_format)

        if args.action == "gate_with_targets":
            targets = [TargetCondition.model_validate(item) for item in args.target_conditions]
            return _result(gate_with_targets(args.deal, targets), args.output_format)

        if args.action == "promote_kpis":
            framework: str | KPIFramework
            if args.kpi_framework:
                framework = KPIFramework.model_validate(args.kpi_framework)
            elif args.kpi_framework_id:
                framework = args.kpi_framework_id
            else:
                return ToolResult(
                    output="kpi_framework or kpi_framework_id is required",
                    is_error=True,
                )
            try:
                targets = promote_kpis_to_conditions(
                    framework,
                    by_period=args.target_by_period or None,
                    condition_kind=args.target_condition_kind,
                )
            except (KeyError, ValueError) as exc:
                return ToolResult(output=str(exc), is_error=True)
            return _result(
                {"target_conditions": [item.model_dump(mode="json") for item in targets]},
                args.output_format,
            )

        try:
            store = ensure_catalog_loaded()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)
        thesis = load_fund_thesis(args.thesis_path or None)

        if args.action == "deal_compare":
            if not args.company_a or not args.company_b:
                return ToolResult(
                    output="company_a and company_b are required for deal_compare", is_error=True
                )
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
            target_conditions=[
                TargetCondition.model_validate(item) for item in args.target_conditions
            ],
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
