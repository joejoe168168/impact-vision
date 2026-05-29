"""GIIN Impact Performance Benchmarks (v5 Track C1).

The GIIN publishes **Impact Performance Benchmarks** for a set of impact
sectors (agriculture, clean energy, financial inclusion, forestry, healthcare).
Unlike the 5-Dimension percentile context in
:mod:`openharness.impact.external_benchmarks`, these are **KPI-level** peer
distributions (e.g. "smallholder farmers reached", "tCO2e avoided",
"% women clients") that also frame a company's contribution against the *scale
of the underlying social/environmental need* (SDG-need contextualisation).

This module ships a small, clearly-labelled **offline snapshot** of sector KPI
quartiles plus:

* :func:`contextualise_kpi` — place a company KPI value in its peer quartile
  with an SDG-need narrative.
* :class:`GIINImpactBenchmarkProvider` — an adapter that satisfies the
  engagement-suite ``BenchmarkProvider`` protocol so the existing peer
  dashboard can be powered by GIIN-shaped data.

The bundled numbers are illustrative distributions tuned to the *shape* of the
GIIN Annual Impact Investor Survey / Impact Performance Benchmarks. Replace with
a licensed GIIN data feed for decision-grade peer context.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Direction = Literal["higher_better", "lower_better"]


class KpiBenchmark(BaseModel):
    """One sector × KPI peer distribution."""

    sector: str
    metric_id: str
    metric_label: str
    unit: str
    p25: float
    p50: float
    p75: float
    p90: float
    sample_size: int = 0
    vintage_year: int = 2024
    sdg: list[int] = Field(default_factory=list)
    need_context: str = ""
    direction: Direction = "higher_better"
    source: str = "GIIN Impact Performance Benchmarks (offline snapshot)"


class KpiBenchmarkContext(BaseModel):
    """A company KPI value placed against its GIIN peer distribution."""

    sector: str
    metric_id: str
    metric_label: str
    unit: str
    company_value: float
    quartile: int  # 1 = top-25%, 4 = bottom-25%
    percentile_estimate: float
    benchmark: KpiBenchmark
    narrative: str = ""
    need_context: str = ""


def _b(
    sector: str, metric_id: str, label: str, unit: str,
    p25: float, p50: float, p75: float, p90: float, n: int,
    sdg: list[int], need: str, direction: Direction = "higher_better",
) -> KpiBenchmark:
    return KpiBenchmark(
        sector=sector, metric_id=metric_id, metric_label=label, unit=unit,
        p25=p25, p50=p50, p75=p75, p90=p90, sample_size=n, sdg=sdg,
        need_context=need, direction=direction,
    )


# ---------------------------------------------------------------------------
# Seeded benchmark catalogue (offline snapshot — illustrative distributions).
# ---------------------------------------------------------------------------

_BENCHMARKS: list[KpiBenchmark] = [
    # Agriculture
    _b("agriculture", "farmers_reached", "Smallholder farmers reached", "farmers",
       1500, 6000, 18000, 45000, 180, [1, 2, 8],
       "~500M smallholder farms worldwide; the majority earn below a living income."),
    _b("agriculture", "yield_increase_pct", "Crop yield increase", "%",
       8, 18, 32, 50, 120, [2],
       "Smallholder yield gaps of 50%+ vs. potential are common."),
    _b("agriculture", "income_increase_pct", "Farmer income increase", "%",
       10, 22, 40, 65, 110, [1, 8],
       "Closing the smallholder living-income gap is a core SDG 1 target."),
    # Clean energy
    _b("energy", "ghg_avoided_tco2e", "GHG emissions avoided", "tCO2e",
       2000, 12000, 45000, 120000, 140, [7, 13],
       "Power sector is ~25% of global emissions; rapid decarbonisation required."),
    _b("energy", "energy_access_people", "People with new/improved energy access", "people",
       5000, 25000, 90000, 250000, 130, [7],
       "~675M people still lack electricity access (SDG 7)."),
    _b("energy", "clean_energy_mwh", "Clean energy generated", "MWh",
       3000, 15000, 60000, 180000, 120, [7, 13],
       "Tripling renewables capacity by 2030 is the global benchmark."),
    # Financial inclusion
    _b("financial services", "active_clients", "Active clients reached", "clients",
       5000, 30000, 120000, 400000, 200, [1, 8, 10],
       "~1.4B adults remain unbanked (Global Findex)."),
    _b("financial services", "pct_women_clients", "Share of women clients", "%",
       35, 52, 68, 80, 180, [5, 8],
       "Women are disproportionately financially excluded; gender gap persists."),
    _b("financial services", "pct_rural_clients", "Share of rural clients", "%",
       20, 40, 60, 78, 150, [8, 10],
       "Rural and last-mile populations face the largest access gaps."),
    # Forestry
    _b("forestry", "hectares_sustainable", "Hectares under sustainable management", "ha",
       1000, 8000, 30000, 90000, 70, [13, 15],
       "Forests absorb ~16 Gt CO2/yr; sustainable management is critical for SDG 15."),
    _b("forestry", "tco2e_sequestered", "Carbon sequestered", "tCO2e",
       3000, 20000, 75000, 200000, 65, [13, 15],
       "Nature-based removals are a key net-zero lever."),
    # Healthcare
    _b("healthcare", "patients_served", "Patients / clients served", "patients",
       8000, 40000, 150000, 450000, 130, [3],
       "~4.5B people lack full coverage of essential health services."),
    _b("healthcare", "pct_low_income_patients", "Share of low-income patients", "%",
       30, 50, 70, 85, 110, [1, 3, 10],
       "Reaching underserved, low-income populations is the SDG 3 equity test."),
]

# Sector aliases → canonical sector keys.
_SECTOR_ALIASES: dict[str, str] = {
    "agriculture": "agriculture", "agri": "agriculture", "food": "agriculture",
    "energy": "energy", "clean energy": "energy", "clean-energy": "energy",
    "renewables": "energy", "renewable energy": "energy",
    "financial services": "financial services", "financial inclusion": "financial services",
    "fintech": "financial services", "microfinance": "financial services",
    "forestry": "forestry", "forests": "forestry", "land": "forestry",
    "healthcare": "healthcare", "health": "healthcare",
}


def _canonical_sector(sector: str) -> str:
    return _SECTOR_ALIASES.get(sector.strip().lower(), sector.strip().lower())


def list_giin_benchmarks(sector: str | None = None) -> list[KpiBenchmark]:
    """Return the seeded GIIN KPI benchmarks, optionally filtered by sector."""
    if sector:
        canon = _canonical_sector(sector)
        return [b for b in _BENCHMARKS if b.sector == canon]
    return list(_BENCHMARKS)


def get_giin_benchmark(sector: str, metric_id: str) -> KpiBenchmark | None:
    """Look up one benchmark by sector + metric id."""
    canon = _canonical_sector(sector)
    mid = metric_id.strip().lower()
    for b in _BENCHMARKS:
        if b.sector == canon and b.metric_id == mid:
            return b
    return None


def _quartile(value: float, b: KpiBenchmark) -> int:
    higher = b.direction == "higher_better"
    if higher:
        if value >= b.p75:
            return 1
        if value >= b.p50:
            return 2
        if value >= b.p25:
            return 3
        return 4
    # lower_better: invert
    if value <= b.p25:
        return 1
    if value <= b.p50:
        return 2
    if value <= b.p75:
        return 3
    return 4


def _percentile_estimate(value: float, b: KpiBenchmark) -> float:
    """Piecewise-linear percentile estimate across the p25/p50/p75/p90 markers."""
    markers = [(b.p25, 25.0), (b.p50, 50.0), (b.p75, 75.0), (b.p90, 90.0)]
    if b.direction == "higher_better":
        if value <= b.p25:
            return round(max(1.0, 25.0 * (value / b.p25)) if b.p25 else 1.0, 1)
        if value >= b.p90:
            return 95.0
        for (v0, pct0), (v1, pct1) in zip(markers, markers[1:]):
            if v0 <= value <= v1 and v1 != v0:
                return round(pct0 + (pct1 - pct0) * (value - v0) / (v1 - v0), 1)
        return 50.0
    # lower_better: smaller value → higher percentile
    if value <= b.p25:
        return 90.0
    if value >= b.p90:
        return 5.0
    for (v0, pct0), (v1, pct1) in zip(markers, markers[1:]):
        if v0 <= value <= v1 and v1 != v0:
            inv = 100.0 - (pct0 + (pct1 - pct0) * (value - v0) / (v1 - v0))
            return round(inv, 1)
    return 50.0


def contextualise_kpi(sector: str, metric_id: str, value: float) -> KpiBenchmarkContext | None:
    """Place a company KPI value in its GIIN peer quartile with an SDG-need narrative."""
    b = get_giin_benchmark(sector, metric_id)
    if b is None:
        return None
    q = _quartile(value, b)
    pct = _percentile_estimate(value, b)
    if q == 1:
        narrative = (
            f"Top quartile: {value:g} {b.unit} is at/above the 75th percentile "
            f"({b.p75:g}) for {b.sector} (n={b.sample_size})."
        )
    elif q == 2:
        narrative = (
            f"Above median: between p50 ({b.p50:g}) and p75 ({b.p75:g})."
        )
    elif q == 3:
        narrative = (
            f"Below median: between p25 ({b.p25:g}) and p50 ({b.p50:g})."
        )
    else:
        narrative = (
            f"Bottom quartile: below the 25th percentile ({b.p25:g} {b.unit})."
        )
    return KpiBenchmarkContext(
        sector=b.sector, metric_id=b.metric_id, metric_label=b.metric_label,
        unit=b.unit, company_value=value, quartile=q, percentile_estimate=pct,
        benchmark=b, narrative=narrative, need_context=b.need_context,
    )


class GIINImpactBenchmarkProvider:
    """Adapter satisfying the engagement-suite ``BenchmarkProvider`` protocol.

    ``fetch`` returns a :class:`BenchmarkResult` synthesised from the GIIN KPI
    percentile markers so the existing peer dashboard can consume GIIN-shaped
    data. ``query.metric_id`` is matched against the benchmark ``metric_id``.
    """

    name = "giin_impact_performance"

    def fetch(self, query):  # noqa: ANN001, ANN201 - structural protocol match
        # Lazy import to avoid import-time coupling with the engagements package.
        from openharness.impact.engagements.value_creation import (
            BenchmarkObservation,
            BenchmarkResult,
        )

        b = get_giin_benchmark(query.sector, query.metric_id)
        if b is None:
            return BenchmarkResult(query=query, sample_size=0, provider=self.name)
        observations = [
            BenchmarkObservation(entity_alias="peer-p25", value=b.p25, unit=b.unit),
            BenchmarkObservation(entity_alias="peer-p50", value=b.p50, unit=b.unit),
            BenchmarkObservation(entity_alias="peer-p75", value=b.p75, unit=b.unit),
            BenchmarkObservation(entity_alias="peer-p90", value=b.p90, unit=b.unit),
        ]
        return BenchmarkResult(
            query=query,
            sample_size=b.sample_size,
            mean_value=round((b.p25 + b.p50 + b.p75 + b.p90) / 4, 2),
            median_value=b.p50,
            min_value=b.p25,
            max_value=b.p90,
            observations=observations,
            provider=self.name,
        )


__all__ = [
    "Direction",
    "KpiBenchmark",
    "KpiBenchmarkContext",
    "list_giin_benchmarks",
    "get_giin_benchmark",
    "contextualise_kpi",
    "GIINImpactBenchmarkProvider",
]
