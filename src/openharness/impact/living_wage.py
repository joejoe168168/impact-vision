"""Living-wage gap analysis with explicit benchmark provenance."""

from __future__ import annotations
from pathlib import Path
import yaml


def load_living_wage_benchmarks(path: str | Path | None = None) -> dict:
    data_path = (
        Path(path)
        if path
        else Path(__file__).resolve().parents[3] / "data" / "living_wage_benchmarks.yaml"
    )
    return yaml.safe_load(data_path.read_text(encoding="utf-8"))


def living_wage_gap(geography: str, wages: list[dict], fx=None) -> dict:
    payload = load_living_wage_benchmarks()
    benchmark = payload["benchmarks"].get(geography)
    if benchmark is None:
        return {
            "geography": geography,
            "status": "no_benchmark",
            "benchmark": None,
            "roles": [],
            "headcount_below": 0,
            "remediation_cost": None,
        }
    rows, below, cost, total_people, weighted_gap = [], 0, 0.0, 0, 0.0
    for wage in wages:
        value = float(wage["annual_wage"])
        currency = wage.get("currency", "USD")
        if currency != "USD":
            if fx is None:
                raise ValueError(f"FX conversion required for {currency}")
            value = float(
                fx(currency, "USD", value) if callable(fx) else value * float(fx[currency])
            )
        headcount = int(wage.get("headcount", 1))
        gap = max(0.0, benchmark - value)
        below += headcount if gap > 0 else 0
        cost += gap * headcount
        total_people += headcount
        weighted_gap += gap / benchmark * headcount
        rows.append(
            {
                "role": wage.get("role", "role"),
                "headcount": headcount,
                "annual_wage_usd": value,
                "gap_pct": round(100 * gap / benchmark, 2),
                "remediation_cost_usd": round(gap * headcount, 2),
            }
        )
    return {
        "geography": geography,
        "status": "ok",
        "benchmark": benchmark,
        "benchmark_currency": "USD",
        "as_of": payload["as_of"],
        "source": payload["source"],
        "roles": rows,
        "headcount_below": below,
        "weighted_gap_pct": round(100 * weighted_gap / total_people, 2) if total_people else 0,
        "remediation_cost": round(cost, 2),
    }


__all__ = ["living_wage_gap", "load_living_wage_benchmarks"]
