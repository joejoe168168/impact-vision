"""Sector benchmark data for 5-Dimension scores and SDG alignment.

Every benchmark row carries an explicit `source` and `source_year`. Where the
underlying number is a directional / order-of-magnitude estimate rather than a
peer-reviewed published statistic, `confidence` is set to "indicative" so that
LP-facing reports can flag it appropriately.

Primary sources used:
  - GIIN, *Annual Impact Investor Survey* 2023 (n=308) and 2024 (n=305).
  - GIIN, *State of the Market* (Energy 2022, Agriculture 2022, Health 2023).
  - IRIS+ Core Metric Set v5.3c adoption rate (GIIN reporting platform 2023).
  - 60 Decibels, *MFI Index* 2023 (financial services).
  - Where no public source exists for a sub-sector mean, the value is marked
    `indicative` and computed as the cross-sector mean +/- a sector adjustment
    consistent with the qualitative GIIN Compass reports.
"""

from __future__ import annotations

import csv
import io
import json
import math
from typing import Literal

from pydantic import BaseModel, Field


class SectorBenchmark(BaseModel):
    sector: str
    sample_note: str = ""
    five_d_avg: dict[str, float] = Field(default_factory=dict)
    five_d_overall: float = 0.0
    sdg_primary: list[int] = Field(default_factory=list)
    core_metric_coverage_pct: float = 0.0
    typical_metrics_reported: int = 0
    source: str = ""
    source_year: int = 0
    confidence: Literal["high", "medium", "indicative"] = "indicative"


def _benchmark_data() -> dict:
    from openharness.impact.knowledge import load_knowledge

    return load_knowledge("benchmarks.yaml")


SECTOR_BENCHMARKS: dict[str, SectorBenchmark] = {
    row["sector"]: SectorBenchmark.model_validate(row) for row in _benchmark_data().get("sector_5d", [])
}


def get_benchmark(sector: str) -> SectorBenchmark | None:
    """Get benchmark for a sector (case-insensitive fuzzy match).

    Accepts both GIIN display names (``Financial Services``) and canonical
    engine keys (``fintech``) produced by ``Company.sector`` normalisation.
    """
    if not sector:
        return None
    from openharness.tools.impact.common import benchmark_sector_name, normalize_sector

    display = benchmark_sector_name(sector)
    if display in SECTOR_BENCHMARKS:
        return SECTOR_BENCHMARKS[display]
    sector_lower = normalize_sector(sector) or sector.lower()
    display_lower = display.lower()
    for name, bm in SECTOR_BENCHMARKS.items():
        name_lower = name.lower()
        if name_lower in {sector_lower, display_lower}:
            return bm
        if name_lower in sector_lower or sector_lower in name_lower:
            return bm
        if name_lower in display_lower or display_lower in name_lower:
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
        "source": bm.source,
        "source_year": bm.source_year,
        "confidence": bm.confidence,
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


GIIN_SURVEY_BENCHMARKS = dict(_benchmark_data().get("giin_survey", {}))


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
