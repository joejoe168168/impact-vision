"""Bayesian evidence updater (Phase 18).

Per-claim beta-binomial posterior. Given a prior belief about the truth
probability of a claim and a stream of corroborating / contradicting
verifications, maintains an updated Beta(α, β) posterior and returns:

* posterior mean (point estimate)
* 95% credible interval
* posterior probability the claim is "true enough" (mean > threshold)

Deliberately dependency-free — no scipy, no numpy. All computations are
closed-form for the beta-binomial conjugate pair.
"""
from __future__ import annotations

import math
from typing import Iterable

from pydantic import BaseModel, Field


class BetaPosterior(BaseModel):
    """Conjugate beta-binomial posterior over a claim's truth probability."""

    alpha: float = Field(gt=0)
    beta: float = Field(gt=0)
    n_corroborating: int = Field(ge=0, default=0)
    n_contradicting: int = Field(ge=0, default=0)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / (((a + b) ** 2) * (a + b + 1))

    def credible_interval(self, level: float = 0.95) -> tuple[float, float]:
        """Equal-tailed credible interval via the normal approximation.

        For α, β > 10 this is within ~0.5% of the exact quantile function.
        We return the approximation because it needs zero external deps.
        """
        mu = self.mean
        sd = math.sqrt(self.variance)
        tail = (1 - level) / 2
        z = _approx_normal_quantile(1 - tail)
        lo = max(0.0, mu - z * sd)
        hi = min(1.0, mu + z * sd)
        return round(lo, 4), round(hi, 4)

    def probability_above(self, threshold: float) -> float:
        """P(θ > threshold) ≈ normal approx of the Beta CDF."""
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be in [0, 1]")
        mu = self.mean
        sd = math.sqrt(self.variance)
        if sd == 0:
            return 1.0 if mu > threshold else 0.0
        z = (threshold - mu) / sd
        return round(1 - _approx_normal_cdf(z), 4)


def update(prior: BetaPosterior, *, corroborating: int = 0, contradicting: int = 0) -> BetaPosterior:
    """Pure-function update — returns a new :class:`BetaPosterior`."""
    return BetaPosterior(
        alpha=prior.alpha + corroborating,
        beta=prior.beta + contradicting,
        n_corroborating=prior.n_corroborating + corroborating,
        n_contradicting=prior.n_contradicting + contradicting,
    )


def fold(prior: BetaPosterior, stream: Iterable[bool]) -> BetaPosterior:
    """Fold a stream of verification outcomes (True = corroborating)."""
    corr = sum(1 for v in stream if v)
    cont = sum(1 for v in stream if not v)
    return update(prior, corroborating=corr, contradicting=cont)


def default_prior(*, optimism: float = 0.5, strength: float = 4.0) -> BetaPosterior:
    """Build a sensible Beta(α, β) prior from two interpretable numbers.

    ``optimism`` ∈ [0, 1] — your prior belief the claim is true.
    ``strength`` > 0 — pseudo-count (higher = more confident in prior).
    """
    if not 0 <= optimism <= 1:
        raise ValueError("optimism must be in [0, 1]")
    if strength <= 0:
        raise ValueError("strength must be > 0")
    return BetaPosterior(alpha=max(1e-6, strength * optimism),
                         beta=max(1e-6, strength * (1 - optimism)))


# ---------------------------------------------------------------------------
# Normal approximation helpers — no scipy needed
# ---------------------------------------------------------------------------

def _approx_normal_cdf(z: float) -> float:
    """Abramowitz & Stegun 26.2.17 — max error ~7.5e-8."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _approx_normal_quantile(p: float) -> float:
    """Beasley-Springer / Moro approximation of the inverse-normal CDF."""
    if p <= 0 or p >= 1:
        raise ValueError("p must be in (0, 1)")
    # Acklam's algorithm — max rel err ~1.15e-9
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return ((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]
    if phigh < p:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5])
    q = p - 0.5
    r = q * q
    return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q \
           / (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)


__all__ = [
    "BetaPosterior",
    "default_prior",
    "update",
    "fold",
]
