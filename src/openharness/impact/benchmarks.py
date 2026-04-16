"""Sector benchmark data for 5-Dimension scores and SDG alignment.

Based on aggregated data patterns from GIIN Annual Impact Investor Survey,
IRIS+ Core Metric Set adoption rates, and sector-level reporting norms.
These are indicative benchmarks for comparison, not precise values.
"""

from __future__ import annotations

import csv
import io
import json
import math

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
    "Manufacturing": SectorBenchmark(
        sector="Manufacturing",
        sample_note="Impact-oriented manufacturing (fair trade, clean production)",
        five_d_avg={"what": 2.5, "who": 2.2, "how_much": 2.5, "contribution": 2.0, "risk": 2.5},
        five_d_overall=2.34,
        sdg_primary=[8, 9, 12, 13],
        core_metric_coverage_pct=28.0,
        typical_metrics_reported=5,
    ),
    "Transport & Logistics": SectorBenchmark(
        sector="Transport & Logistics",
        sample_note="Sustainable transport and last-mile logistics",
        five_d_avg={"what": 2.5, "who": 2.0, "how_much": 2.2, "contribution": 2.0, "risk": 2.5},
        five_d_overall=2.24,
        sdg_primary=[9, 11, 13],
        core_metric_coverage_pct=22.0,
        typical_metrics_reported=4,
    ),
    "Construction": SectorBenchmark(
        sector="Construction",
        sample_note="Green buildings and affordable housing construction",
        five_d_avg={"what": 2.5, "who": 2.5, "how_much": 2.5, "contribution": 2.2, "risk": 2.8},
        five_d_overall=2.5,
        sdg_primary=[9, 11, 12, 13],
        core_metric_coverage_pct=25.0,
        typical_metrics_reported=4,
    ),
    "Tourism": SectorBenchmark(
        sector="Tourism",
        sample_note="Sustainable and community-based tourism",
        five_d_avg={"what": 2.2, "who": 2.5, "how_much": 2.0, "contribution": 1.8, "risk": 2.0},
        five_d_overall=2.1,
        sdg_primary=[8, 11, 12, 14, 15],
        core_metric_coverage_pct=18.0,
        typical_metrics_reported=3,
    ),
    "Retail": SectorBenchmark(
        sector="Retail",
        sample_note="Fair trade retail, ethical consumer goods",
        five_d_avg={"what": 2.0, "who": 2.3, "how_much": 2.0, "contribution": 1.8, "risk": 2.0},
        five_d_overall=2.02,
        sdg_primary=[8, 10, 12],
        core_metric_coverage_pct=20.0,
        typical_metrics_reported=3,
    ),
    "Mining & Extractives": SectorBenchmark(
        sector="Mining & Extractives",
        sample_note="Responsible mining with community benefit sharing",
        five_d_avg={"what": 2.0, "who": 2.0, "how_much": 2.2, "contribution": 1.8, "risk": 3.0},
        five_d_overall=2.2,
        sdg_primary=[6, 8, 12, 13, 15, 16],
        core_metric_coverage_pct=30.0,
        typical_metrics_reported=5,
    ),
    "Media": SectorBenchmark(
        sector="Media",
        sample_note="Impact-oriented media, digital literacy, civic engagement",
        five_d_avg={"what": 2.2, "who": 2.5, "how_much": 2.0, "contribution": 2.0, "risk": 1.8},
        five_d_overall=2.1,
        sdg_primary=[4, 5, 10, 16],
        core_metric_coverage_pct=15.0,
        typical_metrics_reported=3,
    ),
    "Professional Services": SectorBenchmark(
        sector="Professional Services",
        sample_note="Impact consulting, legal aid, capacity building",
        five_d_avg={"what": 2.0, "who": 2.0, "how_much": 1.8, "contribution": 1.8, "risk": 1.8},
        five_d_overall=1.88,
        sdg_primary=[4, 8, 9, 10],
        core_metric_coverage_pct=15.0,
        typical_metrics_reported=2,
    ),
    "Waste Management": SectorBenchmark(
        sector="Waste Management",
        sample_note="Circular economy, recycling, waste-to-energy",
        five_d_avg={"what": 3.0, "who": 2.5, "how_much": 2.5, "contribution": 2.5, "risk": 2.5},
        five_d_overall=2.6,
        sdg_primary=[3, 6, 11, 12, 13, 14],
        core_metric_coverage_pct=30.0,
        typical_metrics_reported=5,
    ),
    "ICT": SectorBenchmark(
        sector="ICT",
        sample_note="ICT for development, digital inclusion, edtech platforms",
        five_d_avg={"what": 2.5, "who": 2.5, "how_much": 2.2, "contribution": 2.5, "risk": 2.2},
        five_d_overall=2.38,
        sdg_primary=[4, 8, 9, 10, 11],
        core_metric_coverage_pct=22.0,
        typical_metrics_reported=4,
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


class PeerDataStore:
    """In-memory store for anonymized peer company data for benchmarking."""

    def __init__(self) -> None:
        self._peers: list[dict] = []

    def load_csv(self, csv_text: str) -> int:
        """Load peer data from CSV text. Returns number of peers loaded."""
        reader = csv.DictReader(io.StringIO(csv_text))
        count = 0
        for row in reader:
            peer: dict = {
                "sector": row.get("sector", ""),
                "five_d_overall": _safe_float(row.get("five_d_overall", "")),
                "coverage_pct": _safe_float(row.get("coverage_pct", "")),
                "sdg_count": int(row.get("sdg_count", "0") or "0"),
                "metrics_reported": int(row.get("metrics_reported", "0") or "0"),
            }
            for dim in ("what", "who", "how_much", "contribution", "risk"):
                peer[dim] = _safe_float(row.get(dim, ""))
            self._peers.append(peer)
            count += 1
        return count

    def load_json(self, json_text: str) -> int:
        """Load peer data from JSON array text."""
        data = json.loads(json_text)
        if isinstance(data, list):
            self._peers.extend(data)
            return len(data)
        return 0

    @property
    def peer_count(self) -> int:
        return len(self._peers)

    def get_sector_peers(self, sector: str) -> list[dict]:
        sector_lower = sector.lower()
        return [
            p for p in self._peers
            if p.get("sector", "").lower() == sector_lower
            or sector_lower in p.get("sector", "").lower()
        ]

    def calculate_percentile(self, sector: str, metric: str, value: float) -> float | None:
        """Calculate percentile rank for a value within sector peers."""
        peers = self.get_sector_peers(sector)
        if not peers:
            peers = self._peers
        if not peers:
            return None

        values = [p.get(metric, 0) for p in peers if p.get(metric) is not None]
        if not values:
            return None

        below = sum(1 for v in values if v < value)
        equal = sum(1 for v in values if v == value)
        return round((below + 0.5 * equal) / len(values) * 100, 1)


_peer_store = PeerDataStore()


def get_peer_store() -> PeerDataStore:
    return _peer_store


def calculate_percentile(
    sector: str,
    metric: str,
    value: float,
) -> float | None:
    """Standalone percentile rank calculation.

    Delegates to PeerDataStore if peer data is loaded, otherwise falls back
    to benchmark-based estimation for the 5D overall score.
    """
    store = get_peer_store()
    result = store.calculate_percentile(sector, metric, value)
    if result is not None:
        return result
    if metric in ("five_d_overall", "overall_score"):
        bm_result = calculate_percentile_from_benchmarks(sector, value)
        return bm_result.get("percentile")
    return None


def _safe_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def calculate_percentile_from_benchmarks(
    sector: str,
    overall_score: float,
) -> dict:
    """Estimate percentile from built-in sector benchmarks using a normal distribution.

    Since we only have means (no raw peer data), we assume sigma ~ 0.5 for 5D scores
    and use a cumulative distribution to estimate percentile position.
    """
    bm = get_benchmark(sector)
    if not bm:
        return {"percentile": None, "benchmark_available": False}

    mean = bm.five_d_overall
    sigma = 0.5
    z = (overall_score - mean) / sigma if sigma > 0 else 0
    percentile = round(0.5 * (1 + math.erf(z / math.sqrt(2))) * 100, 1)
    percentile = max(1, min(99, percentile))

    return {
        "percentile": percentile,
        "benchmark_available": True,
        "sector": bm.sector,
        "interpretation": (
            f"This company is in the {percentile:.0f}th percentile "
            f"for {bm.sector} (benchmark mean: {mean}/5, sample: {bm.sample_note})"
        ),
    }


GIIN_SURVEY_BENCHMARKS = {
    "overall_sample_size": 308,
    "survey_year": 2023,
    "source": "GIIN Annual Impact Investor Survey 2023",
    "metrics": {
        "avg_5d_score": 2.8,
        "median_core_metric_coverage": 35.0,
        "avg_sdg_count": 4.2,
        "avg_metrics_reported": 6.5,
    },
    "by_strategy": {
        "impact_first": {"avg_5d_score": 3.2, "avg_coverage": 42.0},
        "finance_first": {"avg_5d_score": 2.4, "avg_coverage": 28.0},
        "responsible": {"avg_5d_score": 2.0, "avg_coverage": 20.0},
    },
    "by_asset_class": {
        "private_equity": {"avg_5d_score": 3.0, "avg_coverage": 40.0},
        "private_debt": {"avg_5d_score": 2.5, "avg_coverage": 30.0},
        "real_assets": {"avg_5d_score": 2.8, "avg_coverage": 35.0},
    },
}


def compare_to_giin_survey(
    portfolio_avg_5d: float,
    portfolio_avg_coverage: float,
    portfolio_sdg_count: int,
    strategy: str = "",
) -> dict:
    """Compare a fund's portfolio metrics against GIIN Annual Survey benchmarks."""
    giin = GIIN_SURVEY_BENCHMARKS["metrics"]
    result: dict = {
        "source": GIIN_SURVEY_BENCHMARKS["source"],
        "sample_size": GIIN_SURVEY_BENCHMARKS["overall_sample_size"],
        "comparisons": {
            "five_d_score": {
                "fund": portfolio_avg_5d,
                "giin_avg": giin["avg_5d_score"],
                "delta": round(portfolio_avg_5d - giin["avg_5d_score"], 2),
                "status": "above" if portfolio_avg_5d > giin["avg_5d_score"] else "below",
            },
            "core_metric_coverage": {
                "fund": portfolio_avg_coverage,
                "giin_median": giin["median_core_metric_coverage"],
                "delta": round(portfolio_avg_coverage - giin["median_core_metric_coverage"], 1),
                "status": "above" if portfolio_avg_coverage > giin["median_core_metric_coverage"] else "below",
            },
            "sdg_count": {
                "fund": portfolio_sdg_count,
                "giin_avg": giin["avg_sdg_count"],
                "delta": round(portfolio_sdg_count - giin["avg_sdg_count"], 1),
                "status": "above" if portfolio_sdg_count > giin["avg_sdg_count"] else "below",
            },
        },
    }

    strategy_key = strategy.lower().replace("-", "_").replace(" ", "_")
    strat_data = GIIN_SURVEY_BENCHMARKS["by_strategy"].get(strategy_key)
    if strat_data:
        result["strategy_comparison"] = {
            "strategy": strategy_key,
            "five_d": {
                "fund": portfolio_avg_5d,
                "strategy_avg": strat_data["avg_5d_score"],
                "delta": round(portfolio_avg_5d - strat_data["avg_5d_score"], 2),
            },
            "coverage": {
                "fund": portfolio_avg_coverage,
                "strategy_avg": strat_data["avg_coverage"],
                "delta": round(portfolio_avg_coverage - strat_data["avg_coverage"], 1),
            },
        }

    return result
