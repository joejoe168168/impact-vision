"""Blended-finance instrument designer (Phase 16).

Templates + a deal-design helper for the three instruments most common
in impact / catalytic capital structures:

1. **Impact-Linked Loan (IL-Loan)** — interest rate steps down when an
   impact KPI is hit, or up if it's missed.
2. **Social Outcomes Contract (SOC) / Development Impact Bond (DIB)** —
   an outcome payer reimburses investors only when independently
   verified outcomes are achieved.
3. **Impact Carry** — GP carried interest is gated on a portfolio-level
   impact hurdle (e.g. 80% of capital deployed in verified-impact
   companies by exit).

The module returns deterministic, board-ready term sheets you can
serialise to JSON, YAML or the IC memo template.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


InstrumentType = Literal["il-loan", "soc", "impact-carry"]


class RateStep(BaseModel):
    """One node of an impact-linked step schedule."""

    kpi_threshold: float
    rate_bps: int
    direction: Literal["down", "up"] = "down"
    note: str = ""


class ILLoanTerms(BaseModel):
    """Impact-linked loan term sheet."""

    borrower: str
    principal_usd: float = Field(gt=0)
    base_rate_bps: int
    tenor_months: int = Field(gt=0)
    kpi_id: str
    kpi_description: str
    baseline: float
    target: float
    step_schedule: list[RateStep]
    cap_bps: int | None = None          # maximum step-down
    floor_bps: int | None = None        # maximum step-up
    reporting_cadence: Literal["quarterly", "annual"] = "annual"
    verification_party: str = "Independent assurer (ISAE 3000)"


class SOCTerms(BaseModel):
    """Social Outcomes Contract / Development Impact Bond term sheet."""

    project_name: str
    outcome_payer: str
    intermediary: str
    service_provider: str
    beneficiary_count_target: int
    outcome_metric: str
    unit_price_usd: float
    max_payment_usd: float
    tenor_months: int
    validation_methodology: str = "Third-party RCT or matched-control study"
    trigger_gates: list[str] = Field(default_factory=list)


class ImpactCarryTerms(BaseModel):
    """Impact-gated GP carry term sheet."""

    fund_name: str
    gp_carry_rate_pct: float = 20.0
    impact_hurdle_pct: float = 80.0
    hurdle_metric: str = "Capital deployed into verified-impact companies"
    verification_party: str = "Independent assurer (ISAE 3000)"
    clawback_window_years: int = 5


class BlendedFinanceDeal(BaseModel):
    """Aggregate container for a full deal package."""

    deal_name: str
    created_at: date = Field(default_factory=date.today)
    il_loan: ILLoanTerms | None = None
    soc: SOCTerms | None = None
    impact_carry: ImpactCarryTerms | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Helpers that design a "sensible default" deal from a minimal input set
# ---------------------------------------------------------------------------

def design_il_loan(
    *,
    borrower: str,
    principal_usd: float,
    base_rate_bps: int,
    tenor_months: int,
    kpi_id: str,
    kpi_description: str,
    baseline: float,
    target: float,
    step_bps: int = 50,
) -> ILLoanTerms:
    """Return an IL-Loan term sheet with a 3-step schedule around the target."""
    midpoint = (baseline + target) / 2.0
    steps = [
        RateStep(kpi_threshold=baseline, rate_bps=0, direction="down",
                 note="Baseline — no rate change."),
        RateStep(kpi_threshold=midpoint, rate_bps=step_bps, direction="down",
                 note="Midway between baseline and target."),
        RateStep(kpi_threshold=target, rate_bps=step_bps * 2, direction="down",
                 note="Full step-down on target achievement."),
    ]
    return ILLoanTerms(
        borrower=borrower,
        principal_usd=principal_usd,
        base_rate_bps=base_rate_bps,
        tenor_months=tenor_months,
        kpi_id=kpi_id,
        kpi_description=kpi_description,
        baseline=baseline,
        target=target,
        step_schedule=steps,
        cap_bps=step_bps * 2,
        floor_bps=step_bps,
    )


def design_soc(
    *,
    project_name: str,
    outcome_payer: str,
    intermediary: str,
    service_provider: str,
    beneficiary_count_target: int,
    outcome_metric: str,
    unit_price_usd: float,
    tenor_months: int = 36,
) -> SOCTerms:
    return SOCTerms(
        project_name=project_name,
        outcome_payer=outcome_payer,
        intermediary=intermediary,
        service_provider=service_provider,
        beneficiary_count_target=beneficiary_count_target,
        outcome_metric=outcome_metric,
        unit_price_usd=unit_price_usd,
        max_payment_usd=unit_price_usd * beneficiary_count_target * 1.2,  # 20% buffer
        tenor_months=tenor_months,
        trigger_gates=[
            "20% of target achieved at month 12",
            "55% of target achieved at month 24",
            "100% of target achieved at maturity",
        ],
    )


def design_impact_carry(
    *,
    fund_name: str,
    gp_carry_rate_pct: float = 20.0,
    impact_hurdle_pct: float = 80.0,
) -> ImpactCarryTerms:
    return ImpactCarryTerms(
        fund_name=fund_name,
        gp_carry_rate_pct=gp_carry_rate_pct,
        impact_hurdle_pct=impact_hurdle_pct,
    )


__all__ = [
    "InstrumentType",
    "RateStep",
    "ILLoanTerms",
    "SOCTerms",
    "ImpactCarryTerms",
    "BlendedFinanceDeal",
    "design_il_loan",
    "design_soc",
    "design_impact_carry",
]
