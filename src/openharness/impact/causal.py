"""RCT / quasi-experiment ingest + counterfactual update (Phase 18).

Ingests experimental and quasi-experimental study results in a uniform
shape so the counterfactual estimator in
:mod:`openharness.impact.counterfactual` can lift / lower its prior
additionality estimate with actual causal evidence.

Supported designs:

* **RCT** — randomised controlled trial (gold-standard).
* **DID** — difference-in-differences.
* **RDD** — regression-discontinuity design.
* **IV**  — instrumental-variable design.
* **PSM** — propensity-score matching.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field


StudyDesign = Literal["RCT", "DID", "RDD", "IV", "PSM"]


class StudyResult(BaseModel):
    """One causal study result."""

    study_id: str
    design: StudyDesign
    outcome_metric: str
    treatment_effect: float
    """Signed effect size in the native unit of ``outcome_metric``."""
    std_error: float = Field(ge=0)
    n_treatment: int = Field(ge=0)
    n_control: int = Field(ge=0)
    p_value: float | None = None
    pre_registered: bool = False
    publication_year: int | None = None


def significance_z(result: StudyResult) -> float:
    """Return the z-score of the treatment effect."""
    if result.std_error <= 0:
        return 0.0
    return result.treatment_effect / result.std_error


def is_significant(result: StudyResult, *, alpha: float = 0.05) -> bool:
    """Two-sided test at ``alpha``."""
    z = abs(significance_z(result))
    # z > 1.96 ≈ p < 0.05 (two-sided, normal approx)
    crit = {0.01: 2.576, 0.05: 1.96, 0.10: 1.645}.get(alpha, 1.96)
    return z > crit


def update_counterfactual_prior(
    prior: float,
    result: StudyResult,
    *,
    weight_cap: float = 0.8,
) -> float:
    """Blend a prior additionality estimate with a study result.

    ``prior`` is the Impact Vision prior in [0, 1] (e.g. 0.5 = 50%
    additional). We compute the study's posterior weight from its design
    quality (RCT > RDD > DID > IV > PSM) and its sample size, then take
    the convex combination. The cap prevents any one study from fully
    overriding the prior.
    """
    design_weight = {
        "RCT": 1.0,
        "RDD": 0.85,
        "DID": 0.75,
        "IV":  0.70,
        "PSM": 0.55,
    }.get(result.design, 0.5)
    n = result.n_treatment + result.n_control
    # Saturating sample-size weight: 1_000 samples gets you ~0.87
    size_weight = 1.0 - math.exp(-n / 1000.0) if n > 0 else 0.0
    w = min(weight_cap, design_weight * size_weight)
    if not is_significant(result):
        # Non-significant studies pull less.
        w *= 0.35
    # Map the effect onto a [0, 1] likelihood: sign of effect moves prior up/down.
    effect_direction = 1.0 if result.treatment_effect > 0 else 0.0
    return max(0.0, min(1.0, (1 - w) * prior + w * effect_direction))


__all__ = [
    "StudyDesign",
    "StudyResult",
    "significance_z",
    "is_significant",
    "update_counterfactual_prior",
]
