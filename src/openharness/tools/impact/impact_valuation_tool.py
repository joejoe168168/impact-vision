"""Tool: IFVI/VBA-style monetary impact valuation (impact accounting) — v5 Track B1."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.impact_valuation import (
    ImpactQuantity,
    ValueFactor,
    get_value_factors,
    impact_weighted_return,
    monetize_impacts,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ImpactValuationInput(BaseModel):
    action: Literal["list_factors", "monetize", "impact_weighted_return"] = "monetize"
    quantities: list[dict] = Field(
        default_factory=list,
        description="List of {pathway, amount, unit?, note?} physical impact quantities",
    )
    custom_factors: list[dict] = Field(
        default_factory=list,
        description="Optional ValueFactor overrides (use IFVI Global Value Factor DB values)",
    )
    financial_value_usd: float | None = Field(
        default=None, description="Invested capital / revenue / EBITDA for impact intensity"
    )
    financial_basis: str = ""
    financial_return_usd: float | None = Field(
        default=None, description="Financial return for impact_weighted_return action"
    )
    invested_capital_usd: float | None = None
    output_format: Literal["json", "text"] = "json"


class ImpactValuationTool(BaseTool):
    name = "impact_valuation"
    description = (
        "Monetary impact valuation (impact accounting, IFVI/VBA + Impact-Weighted "
        "Accounts lineage). Converts physical impact quantities (GHG, air/water "
        "pollution, land, waste, avoided emissions, living-wage uplift, jobs, "
        "beneficiaries, QALYs) into monetary benefits and costs using a value-factor "
        "catalogue, then computes net monetary impact, benefit/cost ratio, impact "
        "intensity per $ of capital, and an impact-weighted return / impact multiple "
        "of money. Actions: 'list_factors', 'monetize', 'impact_weighted_return'. "
        "Bundled value factors are illustrative defaults; override via custom_factors "
        "with IFVI Global Value Factor Database values for decision-grade output."
    )
    input_model = ImpactValuationInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, ImpactValuationInput)
            else ImpactValuationInput.model_validate(arguments)
        )

        if args.action == "list_factors":
            factors = [f.model_dump(mode="json") for f in get_value_factors()]
            payload = {"value_factors": factors, "count": len(factors)}
            if args.output_format == "text":
                lines = ["MONETARY VALUE FACTORS (illustrative USD defaults)", "=" * 50]
                for f in get_value_factors():
                    sign = "+" if f.direction == "benefit" else "-"
                    lines.append(f"  [{sign}] {f.pathway}: ${f.value_usd_per_unit:,.2f} / {f.unit} — {f.label}")
                return ToolResult(output="\n".join(lines), metadata=payload)
            return _ok(payload)

        try:
            quantities = [ImpactQuantity.model_validate(q) for q in args.quantities]
            custom = {
                f["pathway"]: ValueFactor.model_validate(f) for f in args.custom_factors
            } or None
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid input: {e}", is_error=True)

        valuation = monetize_impacts(
            quantities,
            financial_value_usd=args.financial_value_usd,
            financial_basis=args.financial_basis,
            custom_factors=custom,
        )

        if args.action == "impact_weighted_return":
            if args.financial_return_usd is None:
                return ToolResult(
                    output="financial_return_usd is required for impact_weighted_return",
                    is_error=True,
                )
            iwr = impact_weighted_return(
                financial_return_usd=args.financial_return_usd,
                valuation=valuation,
                invested_capital_usd=args.invested_capital_usd,
            )
            payload = {
                "valuation": valuation.model_dump(mode="json"),
                "impact_weighted_return": iwr.model_dump(mode="json"),
            }
            if args.output_format == "text":
                return ToolResult(output=_iwr_text(valuation, iwr), metadata=payload)
            return _ok(payload)

        payload = valuation.model_dump(mode="json")
        if args.output_format == "text":
            return ToolResult(output=_valuation_text(valuation), metadata=payload)
        return _ok(payload)


def _valuation_text(v) -> str:  # noqa: ANN001
    lines = [
        "MONETARY IMPACT VALUATION (impact accounting)",
        "=" * 50,
        f"Total benefit: ${v.total_benefit_usd:,.0f}",
        f"Total cost:    ${v.total_cost_usd:,.0f}",
        f"NET impact:    ${v.net_monetary_impact_usd:,.0f}",
    ]
    if v.benefit_cost_ratio is not None:
        lines.append(f"Benefit/cost ratio: {v.benefit_cost_ratio}")
    if v.impact_intensity is not None:
        lines.append(f"Impact intensity: {v.impact_intensity} net $ per $ {v.financial_basis or 'financial'}")
    lines.append("")
    for ln in v.lines:
        sign = "+" if ln.direction == "benefit" else "-"
        lines.append(f"  [{sign}] {ln.label}: {ln.amount:g} {ln.unit} -> ${ln.monetary_value_usd:,.0f}")
    if v.unpriced_pathways:
        lines.append(f"\nUnpriced: {', '.join(v.unpriced_pathways)}")
    return "\n".join(lines)


def _iwr_text(v, iwr) -> str:  # noqa: ANN001
    lines = [
        "IMPACT-WEIGHTED RETURN",
        "=" * 50,
        f"Financial return:    ${iwr.financial_return_usd:,.0f}",
        f"Net monetary impact: ${iwr.net_monetary_impact_usd:,.0f}",
        f"Impact-weighted:     ${iwr.impact_weighted_return_usd:,.0f}",
    ]
    if iwr.impact_multiple_of_money is not None:
        lines.append(f"Impact multiple of money (IMM): {iwr.impact_multiple_of_money}")
    return "\n".join(lines)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
