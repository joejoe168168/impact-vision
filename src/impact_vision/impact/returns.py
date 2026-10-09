"""Multiple of Impact (MOI) and impact-adjusted IRR (Phase 15 leftover / 16).

These two measures let a GP report *impact* side-by-side with *financial*
performance in quarterly LP reports. They are designed to be boringly
transparent — every intermediate value is exposed so LPs (and auditors)
can reconstruct the number from raw inputs.

Core definitions
----------------
* **MOI (Multiple of Impact)** — analogous to financial MOIC.

    ``MOI = Σ impact_units_delivered / Σ capital_deployed``

  Units can be anything the GP's thesis prices in: t CO2e avoided,
  beneficiaries reached, hectares restored. The units *must* be
  homogeneous across the portfolio being rolled up — we don't mix
  beneficiaries and tonnes.

* **Impact-adjusted IRR** — a Newton-Raphson root of:

    ``0 = Σ cashflow_t / (1+r)^t + λ · Σ impact_units_t / (1+r)^t``

  where ``λ`` (``impact_price``) is the GP's chosen shadow price per
  unit (USD/beneficiary, USD/tCO2e, …). When ``λ = 0`` the result
  collapses to the ordinary IRR, which lets LPs compare the lift
  provided by the impact assumption directly.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Sequence

from pydantic import BaseModel


class ImpactCashflow(BaseModel):
    """One period of capital + impact flow on a position."""

    period: date
    capital_flow_usd: float
    """Negative for capital deployed, positive for distributions."""
    impact_units: float = 0.0
    """Impact delivered in this period (same units across the series)."""


class MOIResult(BaseModel):
    """MOI roll-up for a single position or a portfolio."""

    label: str = ""
    unit: str
    total_capital_deployed_usd: float = 0.0
    total_distributions_usd: float = 0.0
    total_impact_units: float = 0.0
    moic_financial: float = 0.0           # distributions / deployed
    moi_impact: float = 0.0               # impact_units / deployed
    notes: str = ""


class IRRResult(BaseModel):
    """Impact-adjusted IRR plus the vanilla IRR for comparison."""

    label: str = ""
    impact_price_usd_per_unit: float = 0.0
    irr_financial: float | None = None
    irr_impact_adjusted: float | None = None
    lift_bps: float | None = None
    """``(irr_impact_adjusted - irr_financial) * 10_000`` — in basis points."""
    converged: bool = True
    iterations: int = 0
    notes: str = ""


def compute_moi(cashflows: Iterable[ImpactCashflow], *, unit: str, label: str = "") -> MOIResult:
    cfs = list(cashflows)
    deployed = -sum(cf.capital_flow_usd for cf in cfs if cf.capital_flow_usd < 0)
    distributions = sum(cf.capital_flow_usd for cf in cfs if cf.capital_flow_usd > 0)
    impact = sum(cf.impact_units for cf in cfs)
    moic_fin = distributions / deployed if deployed > 0 else 0.0
    moi_imp = impact / deployed if deployed > 0 else 0.0
    return MOIResult(
        label=label,
        unit=unit,
        total_capital_deployed_usd=round(deployed, 2),
        total_distributions_usd=round(distributions, 2),
        total_impact_units=round(impact, 4),
        moic_financial=round(moic_fin, 4),
        moi_impact=round(moi_imp, 4),
    )


# ---------------------------------------------------------------------------
# IRR — deliberately vendor-free (no scipy / numpy dependency).
# ---------------------------------------------------------------------------

def _year_fraction(start: date, end: date) -> float:
    return (end - start).days / 365.2425


def _npv(rate: float, periods: Sequence[float], flows: Sequence[float]) -> float:
    out = 0.0
    for t, cf in zip(periods, flows):
        out += cf / ((1.0 + rate) ** t)
    return out


def _irr_newton(
    periods: Sequence[float],
    flows: Sequence[float],
    *,
    guess: float = 0.1,
    max_iter: int = 80,
    tol: float = 1e-7,
) -> tuple[float | None, int, bool]:
    """Newton-Raphson IRR. Returns (rate, iterations, converged)."""
    if len(periods) < 2 or all(abs(f) < 1e-12 for f in flows):
        return None, 0, False
    r = guess
    for i in range(1, max_iter + 1):
        npv = _npv(r, periods, flows)
        # Numerical derivative for robustness
        d = (_npv(r + 1e-6, periods, flows) - npv) / 1e-6
        if abs(d) < 1e-14:
            break
        step = npv / d
        r -= step
        if r <= -0.999:  # keep it in sane territory
            r = -0.99
        if abs(step) < tol:
            return r, i, True
    return r, max_iter, False


def compute_irr(
    cashflows: Iterable[ImpactCashflow],
    *,
    impact_price_usd_per_unit: float = 0.0,
    label: str = "",
) -> IRRResult:
    """Return financial IRR + impact-adjusted IRR side-by-side."""
    cfs = sorted(cashflows, key=lambda c: c.period)
    if not cfs:
        return IRRResult(label=label, impact_price_usd_per_unit=impact_price_usd_per_unit,
                         converged=False, notes="no cashflows")
    t0 = cfs[0].period
    periods = [_year_fraction(t0, c.period) for c in cfs]
    financial = [c.capital_flow_usd for c in cfs]
    impact_flows = [c.capital_flow_usd + c.impact_units * impact_price_usd_per_unit for c in cfs]

    irr_fin, it_fin, conv_fin = _irr_newton(periods, financial)
    irr_imp, it_imp, conv_imp = _irr_newton(periods, impact_flows, guess=irr_fin or 0.1)

    lift_bps: float | None = None
    if irr_fin is not None and irr_imp is not None:
        lift_bps = round((irr_imp - irr_fin) * 10_000, 1)

    return IRRResult(
        label=label,
        impact_price_usd_per_unit=impact_price_usd_per_unit,
        irr_financial=None if irr_fin is None else round(irr_fin, 6),
        irr_impact_adjusted=None if irr_imp is None else round(irr_imp, 6),
        lift_bps=lift_bps,
        converged=bool(conv_fin and conv_imp),
        iterations=max(it_fin, it_imp),
    )


__all__ = [
    "ImpactCashflow",
    "MOIResult",
    "IRRResult",
    "compute_moi",
    "compute_irr",
]


# ---------------------------------------------------------------------------
# Convenience constructor: build a cashflow series from common inputs
# ---------------------------------------------------------------------------

def cashflows_from_series(
    dates: Sequence[date],
    capital_flows: Sequence[float],
    impact_units: Sequence[float] | None = None,
) -> list[ImpactCashflow]:
    """Zip three parallel sequences into a :class:`list[ImpactCashflow]`."""
    if len(dates) != len(capital_flows):
        raise ValueError("dates and capital_flows must be the same length")
    impacts = list(impact_units) if impact_units is not None else [0.0] * len(dates)
    if len(impacts) != len(dates):
        raise ValueError("impact_units length must match dates")
    return [
        ImpactCashflow(period=d, capital_flow_usd=cf, impact_units=iu)
        for d, cf, iu in zip(dates, capital_flows, impacts)
    ]


__all__.append("cashflows_from_series")
__all__.append("ImpactCashflow")
