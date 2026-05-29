"""Tool: NGFS climate scenario risk screen — v5 Track E1."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.climate_scenario import (
    NGFS_SCENARIOS,
    ClimateScenarioInput,
    PortfolioHolding,
    assess_climate_scenarios,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ClimateScenarioToolInput(BaseModel):
    action: Literal["list_scenarios", "assess"] = "assess"
    holdings: list[dict] = Field(
        default_factory=list,
        description="Portfolio holdings: {name, sector, value_usd}",
    )
    scenario_keys: list[str] = Field(
        default_factory=list, description="Subset of NGFS scenario keys (empty = all)",
    )
    max_var_pct: float = Field(default=35.0, description="Illustrative max VaR at full severity")
    output_format: Literal["json", "text"] = "json"


class ClimateScenarioTool(BaseTool):
    name = "climate_scenario_risk"
    description = (
        "NGFS-style climate scenario risk screen for a portfolio. Combines NGFS "
        "scenario families (Orderly: Net Zero 2050 / Below 2°C; Disorderly: Delayed "
        "Transition / Divergent Net Zero; Hot house: NDCs / Current Policies; Too "
        "Little Too Late) with sector transition & physical sensitivities to produce "
        "portfolio-weighted transition-risk and physical-risk exposure, a combined "
        "score, and an illustrative value-at-risk haircut per scenario, plus the "
        "most-exposed holdings. Actions: 'list_scenarios', 'assess'. Coefficients are "
        "illustrative screening defaults — use NGFS Phase V + asset-level models for "
        "decision-grade climate VaR."
    )
    input_model = ClimateScenarioToolInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, ClimateScenarioToolInput)
            else ClimateScenarioToolInput.model_validate(arguments)
        )

        if args.action == "list_scenarios":
            payload = {"scenarios": [s.model_dump(mode="json") for s in NGFS_SCENARIOS.values()]}
            if args.output_format == "text":
                lines = ["NGFS SCENARIO FAMILIES", "=" * 50]
                for s in NGFS_SCENARIOS.values():
                    lines.append(f"  [{s.category}] {s.key}: {s.name} (~{s.temp_outcome_c}°C)")
                    lines.append(f"    transition {s.transition_severity} | physical {s.physical_severity} | carbon ${s.carbon_price_2030_usd:g}/t by 2030")
                    lines.append(f"    {s.description}")
                return ToolResult(output="\n".join(lines), metadata=payload)
            return _ok(payload)

        if not args.holdings:
            return ToolResult(output="holdings is required for assess", is_error=True)
        try:
            holdings = [PortfolioHolding.model_validate(h) for h in args.holdings]
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid holding input: {e}", is_error=True)

        result = assess_climate_scenarios(ClimateScenarioInput(
            holdings=holdings,
            scenario_keys=args.scenario_keys,
            max_var_pct=args.max_var_pct,
        ))
        payload = result.model_dump(mode="json")
        if args.output_format == "text":
            return ToolResult(output=_text(result), metadata=payload)
        return _ok(payload)


def _text(r) -> str:  # noqa: ANN001
    lines = [
        "NGFS CLIMATE SCENARIO RISK SCREEN",
        "=" * 50,
        f"Portfolio value: ${r.total_value_usd:,.0f}",
        f"Headline (worst) scenario: {r.headline_scenario}",
        "",
        "Scenario exposure (transition / physical / combined / VaR):",
    ]
    for e in r.scenario_exposures:
        lines.append(
            f"  {e.scenario_name}: {e.transition_exposure} / {e.physical_exposure} / "
            f"{e.combined_risk_score} → ~{e.estimated_var_pct}% (${e.estimated_var_usd:,.0f})"
        )
    if r.top_exposed_holdings:
        lines.append("")
        lines.append("Most exposed holdings:")
        for h in r.top_exposed_holdings[:5]:
            lines.append(f"  {h.name} ({h.sector}): worst {h.worst_combined_score} under {h.worst_scenario}")
    if r.recommendations:
        lines.append("")
        lines.append("Recommendations:")
        for rec in r.recommendations:
            lines.append(f"  - {rec}")
    return "\n".join(lines)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)


__all__ = ["ClimateScenarioToolInput", "ClimateScenarioTool"]
