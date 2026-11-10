"""Do the documents give two different figures for the same thing?

When a deck states "42,000 households" on one page and "24,000 households" on
another, the first value used to win and the second vanished. A reviewer
looks for exactly this, so :func:`find_conflicts` keeps every reported value
per IRIS+ metric and reports the ones that disagree.

Two figures are a conflict when they map to the same metric, differ by more
than the tolerance in ``methodology/v2.yaml`` (``consistency``), and are not
explained by time: when the two sentences name different years, or only one
names a year ("24,000 in 2023" against "42,000 households"), the difference
reads as growth, not a contradiction. Targets and derived values are never
compared.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def _claim(claim: Any) -> tuple[str, str, int | None]:
    get = claim.get if isinstance(claim, dict) else lambda k, d=None: getattr(claim, k, d)
    return str(get("text", "") or ""), str(get("category", "") or ""), get("source_page")


def find_conflicts(claims: Iterable[Any]) -> list[dict[str, Any]]:
    """Metrics the documents report with materially different values."""
    from impact_vision.impact.claim_metric_mapper import map_claim_metrics
    from impact_vision.impact.expected_impact import params

    cfg = params().get("consistency") or {}
    tolerance = float(cfg.get("tolerance", 0.10))
    seen: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        text, category, page = _claim(claim)
        if not text or category in {"commitment", "intent"}:
            continue
        for mapping in map_claim_metrics(text):
            if mapping.derived:
                continue
            rows = seen.setdefault(mapping.metric_id, [])
            if all(r["sentence"] != text.strip(" -•*\t") for r in rows):
                rows.append({"value": float(mapping.value), "display": mapping.display,
                             "sentence": text.strip(" -•*\t"),
                             "page": page, "years": set(_YEAR.findall(text))})

    conflicts = []
    for metric_id, rows in seen.items():
        if len(rows) < 2:
            continue
        low, high = min(rows, key=lambda r: r["value"]), max(rows, key=lambda r: r["value"])
        if high["value"] <= 0 or (high["value"] - low["value"]) / high["value"] <= tolerance:
            continue
        if low["years"] != high["years"]:
            continue  # a dated figure against another period (or an undated one): growth, not a contradiction
        conflicts.append({
            "metric_id": metric_id,
            "values": [low["display"], high["display"]],
            "difference_pct": round(100 * (high["value"] - low["value"]) / high["value"]),
            "sources": [{"value": r["display"], "sentence": r["sentence"], "page": r["page"]} for r in (low, high)],
        })
    conflicts.sort(key=lambda c: -c["difference_pct"])
    return conflicts[: int(cfg.get("max_items", 5))]


def plan_items(conflicts: list[dict[str, Any]], names: dict[str, str] | None = None) -> list[dict[str, str]]:
    """Evidence-plan entry for the largest conflict: settle it before anything else."""
    names = names or {}
    out = []
    for c in conflicts[:1]:
        label = names.get(c["metric_id"]) or c["metric_id"]
        out.append({
            "action": f"Reconcile the two figures given for {label}: {c['values'][0]} and {c['values'][1]}.",
            "why": f"The documents disagree by {c['difference_pct']}%, so every number built on this one is in doubt.",
            "kind": "reconcile",
        })
    return out


__all__ = ["find_conflicts", "plan_items"]
