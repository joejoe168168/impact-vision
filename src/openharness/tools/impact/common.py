"""Shared helpers for impact tools input normalization and summaries."""

from __future__ import annotations

from collections.abc import Iterable


def normalize_metric_map(metrics: dict[str, str] | None) -> dict[str, str]:
    """Normalize metric IDs and values for consistent downstream matching."""
    if not metrics:
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_val in metrics.items():
        key = str(raw_key or "").strip().upper()
        if not key:
            continue
        value = str(raw_val).strip() if raw_val is not None else ""
        if not value:
            continue
        normalized[key] = value
    return normalized


def normalize_str_list(values: Iterable[str] | None) -> list[str]:
    """Return a de-duplicated list of non-empty strings preserving order."""
    if not values:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def normalize_sdg_goals(values: Iterable[int] | None) -> list[int]:
    """Return valid SDG goal numbers (1-17), de-duplicated."""
    out: list[int] = []
    seen: set[int] = set()
    for value in values or []:
        try:
            goal = int(value)
        except (TypeError, ValueError):
            continue
        if goal < 1 or goal > 17 or goal in seen:
            continue
        seen.add(goal)
        out.append(goal)
    return out
