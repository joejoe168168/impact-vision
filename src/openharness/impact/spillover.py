"""Spillover / leakage modelling per ToC node (Phase 18).

Applies a simple displacement-correction to outcomes reported along a
Theory of Change. Two effects are supported:

1. **Leakage** — project activities that displace counterfactual
   activity elsewhere (e.g. fencing a forest leads to clearance
   next door). Modelled as a shrinkage factor ``1 - leakage_rate``.

2. **Spillover** — project activities that *create* additional
   positive outcomes beyond the target population (e.g. a microgrid
   that lets a neighbouring village tap into reliable power).
   Modelled as an uplift factor ``1 + spillover_rate``.

Rates are proportions in [0, 1] (leakage) and [0, 3] (spillover). The
helper :func:`adjust_node` applies both in the canonical order
"leakage first, then spillover" recommended by the GHG Protocol Project
Accounting guidance.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SpilloverAssumption(BaseModel):
    """Per-outcome leakage + spillover assumption."""

    toc_node_id: str
    outcome_metric: str
    raw_value: float
    unit: str = ""
    leakage_rate: float = Field(ge=0, le=1, default=0.0)
    spillover_rate: float = Field(ge=0, le=3, default=0.0)
    rationale: str = ""


class AdjustedOutcome(BaseModel):
    toc_node_id: str
    outcome_metric: str
    raw_value: float
    after_leakage: float
    adjusted_value: float
    unit: str = ""
    leakage_rate: float
    spillover_rate: float
    net_adjustment_pct: float


def adjust_node(assumption: SpilloverAssumption) -> AdjustedOutcome:
    after_leakage = assumption.raw_value * (1 - assumption.leakage_rate)
    adjusted = after_leakage * (1 + assumption.spillover_rate)
    net_pct = 0.0 if assumption.raw_value == 0 else round(
        100.0 * (adjusted - assumption.raw_value) / assumption.raw_value, 2
    )
    return AdjustedOutcome(
        toc_node_id=assumption.toc_node_id,
        outcome_metric=assumption.outcome_metric,
        raw_value=assumption.raw_value,
        after_leakage=round(after_leakage, 6),
        adjusted_value=round(adjusted, 6),
        unit=assumption.unit,
        leakage_rate=assumption.leakage_rate,
        spillover_rate=assumption.spillover_rate,
        net_adjustment_pct=net_pct,
    )


__all__ = ["SpilloverAssumption", "AdjustedOutcome", "adjust_node"]
