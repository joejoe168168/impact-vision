"""Living-wage gap analysis with explicit benchmark provenance."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def _benchmark_path(path: str | Path | None = None) -> Path:
    if path:
        return Path(path)
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "data" / "living_wage_benchmarks.yaml",
        here.parents[2] / "_data" / "living_wage_benchmarks.yaml",
        Path("data/living_wage_benchmarks.yaml"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


@lru_cache(maxsize=4)
def _load_payload(path_key: str) -> dict:
    payload = yaml.safe_load(Path(path_key).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise TypeError(f"Living-wage benchmark file is not a mapping: {path_key}")
    return payload


def load_living_wage_benchmarks(path: str | Path | None = None) -> dict:
    return _load_payload(str(_benchmark_path(path)))


def list_geographies(path: str | Path | None = None) -> list[str]:
    payload = load_living_wage_benchmarks(path)
    return sorted(str(name) for name in (payload.get("benchmarks") or {}))


def _benchmark_annual_usd(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        value = raw.get("annual_usd", raw.get("annual", raw.get("usd")))
        return None if value is None else float(value)
    return float(raw)


def _lookup_name(token: str, by_lower: dict[str, str], aliases: dict[str, str]) -> str | None:
    if token in by_lower:
        return by_lower[token]
    if token in aliases:
        return aliases[token]
    return None


def resolve_geography(geography: str, payload: dict | None = None) -> tuple[str | None, float | None]:
    """Map a free-text geography onto a seeded benchmark.

    Matching order: exact (case-insensitive) → YAML aliases → comma-separated
    tokens (e.g. ``"Nairobi, Kenya"``) → longest contained benchmark name
    of at least 4 characters. Two-letter ISO aliases only match the full
    string so ``"us"`` does not hit inside ``"Atlantis"``.
    """
    payload = payload or load_living_wage_benchmarks()
    benchmarks = payload.get("benchmarks") or {}
    if not geography or not str(geography).strip():
        return None, None

    needle = " ".join(str(geography).split()).strip().lower()
    by_lower = {str(name).lower(): name for name in benchmarks}
    aliases = {
        str(k).lower(): str(v)
        for k, v in (payload.get("aliases") or {}).items()
        if str(v) in benchmarks
    }

    name = _lookup_name(needle, by_lower, aliases)
    if name is None:
        for token in (part.strip() for part in needle.replace("/", ",").split(",")):
            name = _lookup_name(token, by_lower, aliases)
            if name:
                break
    if name is None:
        contained: list[tuple[int, str]] = []
        for alias, target in aliases.items():
            if len(alias) >= 4 and alias in needle:
                contained.append((len(alias), target))
        for bench_name in benchmarks:
            lowered = str(bench_name).lower()
            if len(lowered) >= 4 and lowered in needle:
                contained.append((len(lowered), str(bench_name)))
        if contained:
            contained.sort(reverse=True)
            name = contained[0][1]
    if name is None:
        return None, None
    return name, _benchmark_annual_usd(benchmarks[name])


def _to_usd(value: float, currency: str, fx: Any) -> tuple[float | None, str | None]:
    currency = (currency or "USD").upper()
    if currency == "USD":
        return value, None
    converted: float | None = None
    if callable(fx):
        converted = fx(currency, "USD", value)
    elif isinstance(fx, dict) and currency in fx:
        converted = value * float(fx[currency])
    else:
        from openharness.impact.fx import convert as fx_convert

        converted = fx_convert(value, from_ccy=currency, to_ccy="USD")
    if converted is None:
        return None, currency
    return float(converted), None


def living_wage_gap(geography: str, wages: list[dict], fx=None) -> dict:
    payload = load_living_wage_benchmarks()
    resolved_name, benchmark = resolve_geography(geography, payload)
    if benchmark is None:
        return {
            "geography": geography,
            "resolved_geography": resolved_name,
            "status": "no_benchmark",
            "benchmark": None,
            "roles": [],
            "headcount_below": 0,
            "remediation_cost": None,
        }

    rows, below, cost, total_people, weighted_gap = [], 0, 0.0, 0, 0.0
    warnings: list[str] = []
    for wage in wages or []:
        value = float(wage["annual_wage"])
        currency = wage.get("currency", "USD")
        usd, missing_ccy = _to_usd(value, str(currency), fx)
        if usd is None:
            warnings.append(
                f"No FX rate for {missing_ccy}; role {wage.get('role', 'role')} excluded from gap math"
            )
            continue
        value = usd
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
                "annual_wage_usd": round(value, 2),
                "gap_pct": round(100 * gap / benchmark, 2),
                "remediation_cost_usd": round(gap * headcount, 2),
            }
        )
    return {
        "geography": geography,
        "resolved_geography": resolved_name,
        "status": "ok",
        "benchmark": benchmark,
        "benchmark_currency": payload.get("currency", "USD"),
        "as_of": payload.get("as_of"),
        "source": payload.get("source"),
        "disclaimer": payload.get("disclaimer", ""),
        "roles": rows,
        "headcount_below": below,
        "weighted_gap_pct": round(100 * weighted_gap / total_people, 2) if total_people else 0,
        "remediation_cost": round(cost, 2),
        "warnings": warnings,
    }


__all__ = [
    "list_geographies",
    "living_wage_gap",
    "load_living_wage_benchmarks",
    "resolve_geography",
]
