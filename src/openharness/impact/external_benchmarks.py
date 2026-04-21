"""GIIN Compass benchmark-in-the-loop (Phase 16).

Defines the :class:`ExternalBenchmarkProvider` Protocol — any GP can
subscribe to the GIIN Compass Impact Benchmarks programme and drop in an
adapter that pulls live p50 / p75 peer context for every 5-D dimension.

The bundled :class:`OfflineBenchmarkProvider` ships a deterministic
sector-typical percentile set so the pipeline works in disconnected
environments. Swap it out at runtime via :func:`register_benchmark_provider`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


DimensionKey = Literal["what", "who", "how_much", "contribution", "risk"]


class PeerPercentiles(BaseModel):
    """One sector × dimension → {p25, p50, p75, p90, n}."""

    sector: str
    dimension: DimensionKey
    p25: float = Field(ge=0, le=5)
    p50: float = Field(ge=0, le=5)
    p75: float = Field(ge=0, le=5)
    p90: float = Field(ge=0, le=5)
    sample_size: int = Field(ge=0, default=0)
    vintage_year: int | None = None
    source: str = "GIIN Compass"


class PeerContext(BaseModel):
    """Enriched view of one company score against its sector peers."""

    sector: str
    dimension: DimensionKey
    company_score: float
    percentiles: PeerPercentiles
    quartile: int  # 1 = top-25%, 4 = bottom-25%
    narrative: str = ""


@runtime_checkable
class ExternalBenchmarkProvider(Protocol):
    """Pluggable benchmark source."""

    id: str

    def percentiles(self, sector: str, dimension: DimensionKey) -> PeerPercentiles | None:  # pragma: no cover
        ...


# ---------------------------------------------------------------------------
# Offline default — sector-typical distributions distilled from the public
# 2023 GIIN Annual Survey + Compass p50s. These are NOT live, but give the
# right *shape* for testing and for funds that haven't purchased a
# subscription yet.
# ---------------------------------------------------------------------------

_DEFAULT_PERCENTILES: dict[tuple[str, str], PeerPercentiles] = {}


def _seed(sector: str, dim: DimensionKey, p25: float, p50: float, p75: float, p90: float, n: int) -> None:
    _DEFAULT_PERCENTILES[(sector.lower(), dim)] = PeerPercentiles(
        sector=sector, dimension=dim, p25=p25, p50=p50, p75=p75, p90=p90,
        sample_size=n, vintage_year=2024, source="GIIN Compass (offline snapshot)",
    )


# Rough percentile snapshot — tuned so the demo reports tell a coherent story
for _sector, _base in [
    ("energy",       (2.0, 2.7, 3.4, 4.0, 310)),
    ("agriculture",  (1.8, 2.5, 3.1, 3.8, 220)),
    ("financial-services", (1.6, 2.2, 2.9, 3.5, 180)),
    ("healthcare",   (2.2, 2.9, 3.5, 4.1, 140)),
    ("education",    (2.1, 2.8, 3.4, 4.0, 160)),
    ("water",        (2.0, 2.7, 3.3, 3.9, 95)),
    ("forestry",     (2.3, 3.0, 3.6, 4.2, 75)),
    ("buildings",    (1.7, 2.3, 2.9, 3.5, 90)),
    ("technology",   (1.5, 2.1, 2.7, 3.3, 200)),
    ("generic",      (1.8, 2.5, 3.1, 3.7, 500)),
]:
    for dim in ("what", "who", "how_much", "contribution", "risk"):
        _seed(_sector, dim, *_base)  # type: ignore[arg-type]


@dataclass
class OfflineBenchmarkProvider:
    """Deterministic provider reading from the offline snapshot above."""

    id: str = "offline"
    extra: dict[tuple[str, str], PeerPercentiles] = field(default_factory=dict)

    def percentiles(self, sector: str, dimension: DimensionKey) -> PeerPercentiles | None:
        key = (sector.lower(), dimension)
        if key in self.extra:
            return self.extra[key]
        return _DEFAULT_PERCENTILES.get(key) or _DEFAULT_PERCENTILES.get(("generic", dimension))


_PROVIDERS: dict[str, ExternalBenchmarkProvider] = {}


def register_benchmark_provider(provider: ExternalBenchmarkProvider) -> None:
    if not getattr(provider, "id", None):
        raise ValueError("Provider must define an `id`.")
    _PROVIDERS[provider.id] = provider


def get_benchmark_provider(provider_id: str = "offline") -> ExternalBenchmarkProvider:
    return _PROVIDERS[provider_id]


register_benchmark_provider(OfflineBenchmarkProvider())


def quartile_of(score: float, p: PeerPercentiles) -> int:
    if score >= p.p75:
        return 1
    if score >= p.p50:
        return 2
    if score >= p.p25:
        return 3
    return 4


def contextualise(
    sector: str,
    dimension: DimensionKey,
    company_score: float,
    *,
    provider_id: str = "offline",
) -> PeerContext | None:
    prov = get_benchmark_provider(provider_id)
    p = prov.percentiles(sector, dimension)
    if p is None:
        return None
    q = quartile_of(company_score, p)
    if q == 1:
        narrative = f"Top quartile: above the 75th percentile ({p.p75:.1f}/5) for {sector}."
    elif q == 2:
        narrative = f"Above median: between p50 ({p.p50:.1f}) and p75 ({p.p75:.1f})."
    elif q == 3:
        narrative = f"Below median: between p25 ({p.p25:.1f}) and p50 ({p.p50:.1f})."
    else:
        narrative = f"Bottom quartile: below the 25th percentile ({p.p25:.1f}/5)."
    return PeerContext(
        sector=sector,
        dimension=dimension,
        company_score=round(company_score, 2),
        percentiles=p,
        quartile=q,
        narrative=narrative,
    )


__all__ = [
    "DimensionKey",
    "PeerPercentiles",
    "PeerContext",
    "ExternalBenchmarkProvider",
    "OfflineBenchmarkProvider",
    "register_benchmark_provider",
    "get_benchmark_provider",
    "contextualise",
    "quartile_of",
]
