"""Meta-analysis library (Phase 18).

Schema + helpers for storing systematic-review evidence from J-PAL,
3ie's Impact Evaluation Repository and Cochrane. When a claim's stated
effect differs by more than **2σ** from the pooled effect across the
relevant meta-analysis, :func:`deviation_flag` flags it for review.

Uses inverse-variance weighting — the classical fixed-effect pooled
estimator. A random-effects extension (DerSimonian-Laird) is easy to
add but requires an iteration we skip for the deterministic default.
"""
from __future__ import annotations

import math
from typing import Iterable, Literal

from pydantic import BaseModel, Field


MetaLibrary = Literal["J-PAL", "3ie", "Cochrane", "IPAQI", "Other"]


class MetaStudy(BaseModel):
    """One study row in a meta-analysis."""

    study_id: str
    library: MetaLibrary = "Other"
    outcome_metric: str
    effect_size: float
    std_error: float = Field(gt=0)
    weight: float | None = None  # overrides inverse-variance when set
    publication_year: int | None = None


class PooledEffect(BaseModel):
    outcome_metric: str
    n_studies: int
    pooled_effect: float
    pooled_std_error: float
    heterogeneity_q: float = 0.0
    heterogeneity_i2_pct: float = 0.0


def pool_effects(studies: Iterable[MetaStudy]) -> PooledEffect:
    """Fixed-effect (inverse-variance) meta-analysis."""
    sl = list(studies)
    if not sl:
        return PooledEffect(outcome_metric="", n_studies=0,
                            pooled_effect=0.0, pooled_std_error=0.0)
    metric = sl[0].outcome_metric
    weights = [s.weight if s.weight is not None else 1.0 / (s.std_error ** 2) for s in sl]
    ws = sum(weights)
    pooled = sum(w * s.effect_size for w, s in zip(weights, sl)) / ws
    pooled_se = math.sqrt(1.0 / ws)
    # Cochran's Q for heterogeneity
    q = sum(w * (s.effect_size - pooled) ** 2 for w, s in zip(weights, sl))
    df = max(1, len(sl) - 1)
    i2 = max(0.0, (q - df) / q) * 100 if q > 0 else 0.0
    return PooledEffect(
        outcome_metric=metric,
        n_studies=len(sl),
        pooled_effect=round(pooled, 6),
        pooled_std_error=round(pooled_se, 6),
        heterogeneity_q=round(q, 4),
        heterogeneity_i2_pct=round(i2, 2),
    )


def deviation_flag(
    claim_effect: float,
    pooled: PooledEffect,
    *,
    sigma_threshold: float = 2.0,
) -> tuple[bool, float]:
    """Return (should_flag, z_score_abs)."""
    if pooled.pooled_std_error == 0:
        return False, 0.0
    z = (claim_effect - pooled.pooled_effect) / pooled.pooled_std_error
    return abs(z) > sigma_threshold, round(z, 3)


__all__ = [
    "MetaLibrary",
    "MetaStudy",
    "PooledEffect",
    "pool_effects",
    "deviation_flag",
]
