"""Tool: GIIN-Impact-Lab-style welfare quantifier (QALYs / lives improved) — v5 Track B2."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.impact_quantifier import (
    GEOGRAPHY_NEED_MULTIPLIERS,
    THEME_WELFARE_WEIGHTS,
    ImpactQuantifierInput,
    quantify_welfare,
    rollup_welfare,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ImpactQuantifierToolInput(BaseModel):
    action: Literal["list_coefficients", "quantify", "portfolio_rollup"] = "quantify"
    intervention: dict = Field(
        default_factory=dict,
        description="A single intervention {label, theme, geography, breadth, depth, "
        "duration_years, counterfactual, invested_usd?} for action='quantify'",
    )
    interventions: list[dict] = Field(
        default_factory=list,
        description="List of interventions for action='portfolio_rollup'",
    )
    output_format: Literal["json", "text"] = "json"


class ImpactQuantifierTool(BaseTool):
    name = "impact_quantifier"
    description = (
        "Welfare quantifier (GIIN Impact Lab lineage). Converts "
        "breadth × depth × theme × geography × duration × additionality into a "
        "common human-welfare unit — Quality-Adjusted Life Years (QALYs) and "
        "'lives meaningfully improved' — so impact across very different sectors "
        "can be compared on one scale and rolled up to portfolio level (with "
        "QALYs-per-$ cost-effectiveness). Actions: 'list_coefficients', "
        "'quantify' (one intervention), 'portfolio_rollup' (many). Theme weights "
        "and geography multipliers are illustrative defaults — override with GIIN "
        "Impact Quantifier coefficients for decision-grade welfare estimates."
    )
    input_model = ImpactQuantifierToolInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, ImpactQuantifierToolInput)
            else ImpactQuantifierToolInput.model_validate(arguments)
        )

        if args.action == "list_coefficients":
            payload = {
                "theme_welfare_weights": THEME_WELFARE_WEIGHTS,
                "geography_need_multipliers": GEOGRAPHY_NEED_MULTIPLIERS,
                "note": "Illustrative defaults — replace with GIIN Impact Quantifier coefficients.",
            }
            if args.output_format == "text":
                lines = ["WELFARE COEFFICIENTS (illustrative)", "=" * 50, "Theme weights (QALYs/person-year @ full depth):"]
                for k, v in THEME_WELFARE_WEIGHTS.items():
                    lines.append(f"  {k}: {v}")
                lines.append("Geography need multipliers:")
                for k, v in GEOGRAPHY_NEED_MULTIPLIERS.items():
                    lines.append(f"  {k}: {v}")
                return ToolResult(output="\n".join(lines), metadata=payload)
            return _ok(payload)

        if args.action == "portfolio_rollup":
            if not args.interventions:
                return ToolResult(output="interventions is required for portfolio_rollup", is_error=True)
            try:
                inputs = [ImpactQuantifierInput.model_validate(i) for i in args.interventions]
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid intervention input: {e}", is_error=True)
            rollup = rollup_welfare(inputs)
            payload = rollup.model_dump(mode="json")
            if args.output_format == "text":
                return ToolResult(output=_rollup_text(rollup), metadata=payload)
            return _ok(payload)

        # quantify (single)
        if not args.intervention:
            return ToolResult(output="intervention is required for quantify", is_error=True)
        try:
            single = ImpactQuantifierInput.model_validate(args.intervention)
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid intervention input: {e}", is_error=True)
        result = quantify_welfare(single)
        payload = result.model_dump(mode="json")
        if args.output_format == "text":
            return ToolResult(output=_single_text(result), metadata=payload)
        return _ok(payload)


def _single_text(r) -> str:  # noqa: ANN001
    lines = [
        f"WELFARE QUANTIFICATION — {r.label or r.theme}",
        "=" * 50,
        f"Theme: {r.theme}  |  Geography: {r.geography}",
        f"Breadth: {r.breadth:g} people  |  Depth: {r.depth:g}  |  Duration: {r.duration_years:g}y",
        f"Theme weight: {r.theme_welfare_weight}  |  Geo multiplier: {r.geography_need_multiplier}",
        f"Counterfactual: {r.counterfactual:g} (additionality {1 - r.counterfactual:g})",
        "-" * 50,
        f"QALYs:           {r.qalys:,.2f}",
        f"Lives improved:  {r.lives_improved:,.0f}",
        f"Monetised welfare: ${r.monetised_welfare_usd:,.0f}",
    ]
    if r.cost_per_qaly_usd is not None:
        lines.append(f"Cost per QALY:   ${r.cost_per_qaly_usd:,.0f}")
    return "\n".join(lines)


def _rollup_text(rollup) -> str:  # noqa: ANN001
    lines = [
        "PORTFOLIO WELFARE ROLL-UP",
        "=" * 50,
        f"Total QALYs:          {rollup.total_qalys:,.2f}",
        f"Total lives improved: {rollup.total_lives_improved:,.0f}",
        f"Total invested:       ${rollup.total_invested_usd:,.0f}",
    ]
    if rollup.portfolio_cost_per_qaly_usd is not None:
        lines.append(f"Portfolio cost/QALY:  ${rollup.portfolio_cost_per_qaly_usd:,.0f}")
    lines.append("")
    lines.append("By theme (QALYs):")
    for k, v in sorted(rollup.by_theme_qalys.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {k}: {v:,.2f}")
    return "\n".join(lines)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)


__all__ = ["ImpactQuantifierToolInput", "ImpactQuantifierTool"]
