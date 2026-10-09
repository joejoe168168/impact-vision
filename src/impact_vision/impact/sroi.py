"""SROI calculator (Phase 18).

Implements the Social Return on Investment framework defined by the
SROI Network / Social Value International, covering the seven
principles:

1. Involve stakeholders.
2. Understand what changes.
3. Value the things that matter.
4. Only include what is material.
5. Do not over-claim.
6. Be transparent.
7. Verify the result.

The core formula is::

    SROI = Σ present_value_of_outcomes / Σ investment

where each outcome's present value is adjusted for:

* **Deadweight** — what would have happened without the intervention.
* **Attribution** — fraction of the outcome caused by other actors.
* **Drop-off** — decay over time (applied per year after year 1).
* **Displacement** — portion of outcomes that displaced existing ones.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SROIOutcome(BaseModel):
    """One monetised outcome."""

    name: str
    stakeholder: str = ""
    financial_proxy: str = ""
    unit_value_usd: float = Field(ge=0)
    quantity_per_year: float = Field(ge=0)
    duration_years: int = Field(ge=1, default=1)
    deadweight_pct: float = Field(ge=0, le=100, default=0.0)
    attribution_pct: float = Field(ge=0, le=100, default=0.0)
    displacement_pct: float = Field(ge=0, le=100, default=0.0)
    drop_off_pct_per_year: float = Field(ge=0, le=100, default=0.0)


class SROIReport(BaseModel):
    project_name: str
    total_investment_usd: float = Field(ge=0)
    discount_rate: float = Field(ge=0, le=1, default=0.035)  # HMT Green Book
    outcomes: list[SROIOutcome]
    total_present_value_usd: float = 0.0
    sroi_ratio: float = 0.0
    net_present_value_usd: float = 0.0
    sensitivity: dict[str, float] = Field(default_factory=dict)
    principle_checklist: dict[str, Literal["yes", "no", "partial"]] = Field(default_factory=dict)


def compute_sroi(
    *,
    project_name: str,
    total_investment_usd: float,
    outcomes: list[SROIOutcome],
    discount_rate: float = 0.035,
    principle_checklist: dict[str, Literal["yes", "no", "partial"]] | None = None,
) -> SROIReport:
    pv_total = 0.0
    for o in outcomes:
        gross = o.unit_value_usd * o.quantity_per_year
        retained = (
            1.0
            - o.deadweight_pct / 100.0
            - o.attribution_pct / 100.0
            - o.displacement_pct / 100.0
        )
        retained = max(0.0, retained)
        for t in range(1, o.duration_years + 1):
            decay = (1.0 - o.drop_off_pct_per_year / 100.0) ** (t - 1)
            present_value = gross * retained * decay / ((1 + discount_rate) ** t)
            pv_total += present_value

    sroi_ratio = pv_total / total_investment_usd if total_investment_usd > 0 else 0.0
    npv = pv_total - total_investment_usd

    # Deterministic ±20% sensitivity on each lever.
    sens: dict[str, float] = {}
    for lever in ("deadweight", "attribution", "displacement", "drop_off"):
        alt_pv = 0.0
        for o in outcomes:
            bumped = {
                "deadweight":   min(100.0, o.deadweight_pct + 20.0),
                "attribution":  min(100.0, o.attribution_pct + 20.0),
                "displacement": min(100.0, o.displacement_pct + 20.0),
                "drop_off":     min(100.0, o.drop_off_pct_per_year + 20.0),
            }
            dead = bumped["deadweight"] if lever == "deadweight" else o.deadweight_pct
            attr = bumped["attribution"] if lever == "attribution" else o.attribution_pct
            disp = bumped["displacement"] if lever == "displacement" else o.displacement_pct
            drop = bumped["drop_off"] if lever == "drop_off" else o.drop_off_pct_per_year
            retained = max(0.0, 1 - dead/100 - attr/100 - disp/100)
            gross = o.unit_value_usd * o.quantity_per_year
            for t in range(1, o.duration_years + 1):
                decay = (1 - drop / 100) ** (t - 1)
                alt_pv += gross * retained * decay / ((1 + discount_rate) ** t)
        sens[f"sroi_{lever}_plus20pct"] = round(
            alt_pv / total_investment_usd if total_investment_usd > 0 else 0.0, 4
        )

    return SROIReport(
        project_name=project_name,
        total_investment_usd=total_investment_usd,
        discount_rate=discount_rate,
        outcomes=outcomes,
        total_present_value_usd=round(pv_total, 2),
        sroi_ratio=round(sroi_ratio, 4),
        net_present_value_usd=round(npv, 2),
        sensitivity=sens,
        principle_checklist=principle_checklist or {
            "involve_stakeholders": "partial",
            "understand_what_changes": "yes",
            "value_things_that_matter": "yes",
            "only_include_material": "yes",
            "do_not_overclaim": "yes",
            "be_transparent": "yes",
            "verify_the_result": "partial",
        },
    )


__all__ = ["SROIOutcome", "SROIReport", "compute_sroi"]
