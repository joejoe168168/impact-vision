"""Sector benchmark data for 5-Dimension scores and SDG alignment.

Based on aggregated data patterns from GIIN Annual Impact Investor Survey,
IRIS+ Core Metric Set adoption rates, and sector-level reporting norms.
These are indicative benchmarks for comparison, not precise values.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SectorBenchmark(BaseModel):
    sector: str
    sample_note: str = ""
    five_d_avg: dict[str, float] = Field(default_factory=dict)
    five_d_overall: float = 0.0
    sdg_primary: list[int] = Field(default_factory=list)
    core_metric_coverage_pct: float = 0.0
    typical_metrics_reported: int = 0


SECTOR_BENCHMARKS: dict[str, SectorBenchmark] = {
    "Financial Services": SectorBenchmark(
        sector="Financial Services",
        sample_note="Based on GIIN microfinance/fintech impact fund data",
        five_d_avg={"what": 3.2, "who": 3.5, "how_much": 2.8, "contribution": 2.5, "risk": 2.8},
        five_d_overall=2.96,
        sdg_primary=[1, 5, 8, 10],
        core_metric_coverage_pct=42.0,
        typical_metrics_reported=8,
    ),
    "Healthcare": SectorBenchmark(
        sector="Healthcare",
        sample_note="Based on GIIN health-focused impact fund data",
        five_d_avg={"what": 3.5, "who": 3.0, "how_much": 2.5, "contribution": 2.8, "risk": 3.0},
        five_d_overall=2.96,
        sdg_primary=[3, 6, 10],
        core_metric_coverage_pct=38.0,
        typical_metrics_reported=7,
    ),
    "Education": SectorBenchmark(
        sector="Education",
        sample_note="Based on GIIN education/workforce impact fund data",
        five_d_avg={"what": 3.0, "who": 3.3, "how_much": 2.2, "contribution": 2.0, "risk": 2.5},
        five_d_overall=2.6,
        sdg_primary=[4, 8, 10],
        core_metric_coverage_pct=35.0,
        typical_metrics_reported=6,
    ),
    "Agriculture": SectorBenchmark(
        sector="Agriculture",
        sample_note="Based on GIIN food/agriculture impact fund data",
        five_d_avg={"what": 3.0, "who": 3.2, "how_much": 2.5, "contribution": 2.3, "risk": 2.6},
        five_d_overall=2.72,
        sdg_primary=[1, 2, 12, 13, 15],
        core_metric_coverage_pct=30.0,
        typical_metrics_reported=5,
    ),
    "Energy": SectorBenchmark(
        sector="Energy",
        sample_note="Based on GIIN clean energy/climate impact fund data",
        five_d_avg={"what": 3.5, "who": 2.8, "how_much": 3.0, "contribution": 3.0, "risk": 3.2},
        five_d_overall=3.1,
        sdg_primary=[7, 13, 9, 11],
        core_metric_coverage_pct=45.0,
        typical_metrics_reported=9,
    ),
    "Technology": SectorBenchmark(
        sector="Technology",
        sample_note="General tech companies with social/environmental mission",
        five_d_avg={"what": 2.5, "who": 2.0, "how_much": 2.0, "contribution": 2.0, "risk": 2.2},
        five_d_overall=2.14,
        sdg_primary=[8, 9],
        core_metric_coverage_pct=25.0,
        typical_metrics_reported=4,
    ),
    "Real Estate": SectorBenchmark(
        sector="Real Estate",
        sample_note="Affordable housing and green buildings",
        five_d_avg={"what": 3.0, "who": 2.8, "how_much": 2.5, "contribution": 2.5, "risk": 2.8},
        five_d_overall=2.72,
        sdg_primary=[11, 7, 13],
        core_metric_coverage_pct=32.0,
        typical_metrics_reported=5,
    ),
    "Water & Sanitation": SectorBenchmark(
        sector="Water & Sanitation",
        sample_note="WASH-focused impact investments",
        five_d_avg={"what": 3.3, "who": 3.5, "how_much": 2.8, "contribution": 2.5, "risk": 2.5},
        five_d_overall=2.92,
        sdg_primary=[6, 3, 14],
        core_metric_coverage_pct=35.0,
        typical_metrics_reported=6,
    ),
}


def get_benchmark(sector: str) -> SectorBenchmark | None:
    """Get benchmark for a sector (case-insensitive fuzzy match)."""
    sector_lower = sector.lower()
    for name, bm in SECTOR_BENCHMARKS.items():
        if name.lower() == sector_lower or name.lower() in sector_lower or sector_lower in name.lower():
            return bm
    for name, bm in SECTOR_BENCHMARKS.items():
        for word in sector_lower.split():
            if word in name.lower():
                return bm
    return None


def get_all_benchmarks() -> dict[str, SectorBenchmark]:
    return SECTOR_BENCHMARKS


def compare_to_benchmark(
    sector: str,
    five_d_scores: dict[str, float],
    overall_score: float,
    coverage_pct: float,
) -> dict:
    """Compare a company's scores to sector benchmarks."""
    bm = get_benchmark(sector)
    if not bm:
        return {"benchmark_available": False, "sector": sector}

    dim_comparison = {}
    for dim in ["what", "who", "how_much", "contribution", "risk"]:
        actual = five_d_scores.get(dim, 0.0)
        benchmark = bm.five_d_avg.get(dim, 0.0)
        dim_comparison[dim] = {
            "actual": actual,
            "benchmark": benchmark,
            "delta": round(actual - benchmark, 1),
            "status": "above" if actual > benchmark else ("at" if actual == benchmark else "below"),
        }

    return {
        "benchmark_available": True,
        "sector": bm.sector,
        "sample_note": bm.sample_note,
        "overall": {
            "actual": overall_score,
            "benchmark": bm.five_d_overall,
            "delta": round(overall_score - bm.five_d_overall, 1),
            "status": "above" if overall_score > bm.five_d_overall else "below",
        },
        "dimensions": dim_comparison,
        "coverage": {
            "actual": coverage_pct,
            "benchmark": bm.core_metric_coverage_pct,
            "delta": round(coverage_pct - bm.core_metric_coverage_pct, 1),
        },
        "primary_sdgs": bm.sdg_primary,
    }
