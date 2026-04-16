"""Shared helpers for impact tools."""

from __future__ import annotations

import re


METRIC_ID_PATTERN = re.compile(r"^(PI|OI|OD|FP|PD)\d{4}$", re.IGNORECASE)

_THEME_HINTS: dict[str, list[str]] = {
    "climate": ["Climate Mitigation", "Climate Adaptation"],
    "carbon": ["Climate Mitigation"],
    "emission": ["Climate Mitigation"],
    "energy": ["Clean Energy", "Energy Access"],
    "solar": ["Clean Energy", "Energy Access"],
    "education": ["Education", "Quality Education"],
    "health": ["Health"],
    "water": ["Water", "Sustainable Water Management"],
    "sanitation": ["Water", "Sustainable Water Management"],
    "finance": ["Financial Inclusion"],
    "fintech": ["Financial Inclusion"],
    "agri": ["Smallholder Agriculture", "Food Security"],
    "agriculture": ["Smallholder Agriculture", "Food Security"],
    "gender": ["Gender Equality"],
    "women": ["Gender Equality"],
}


def normalize_text_list(values: list[str]) -> list[str]:
    """Strip/compact and deduplicate text values while preserving order."""
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        clean = " ".join((value or "").split()).strip()
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(clean)
    return output


def normalize_metric_map(values: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Normalize IRIS metric IDs and return warnings for invalid keys."""
    normalized: dict[str, str] = {}
    warnings: list[str] = []
    for key, value in values.items():
        metric_id = (key or "").strip().upper()
        if not metric_id:
            continue
        if not METRIC_ID_PATTERN.match(metric_id):
            warnings.append(f"Ignored invalid metric ID: {key}")
            continue
        normalized[metric_id] = "" if value is None else str(value).strip()
    return normalized, warnings


def normalize_metric_ids(values: list[str]) -> tuple[list[str], list[str]]:
    normalized: list[str] = []
    warnings: list[str] = []
    for value in values:
        metric_id = (value or "").strip().upper()
        if not metric_id:
            continue
        if not METRIC_ID_PATTERN.match(metric_id):
            warnings.append(f"Ignored invalid metric ID: {value}")
            continue
        if metric_id not in normalized:
            normalized.append(metric_id)
    return normalized, warnings


def normalize_sdg_goals(values: list[int]) -> tuple[list[int], list[str]]:
    normalized: list[int] = []
    warnings: list[str] = []
    for goal in values:
        if 1 <= goal <= 17:
            if goal not in normalized:
                normalized.append(goal)
            continue
        warnings.append(f"Ignored invalid SDG goal: {goal} (valid range: 1-17)")
    return normalized, warnings


def infer_themes(text: str, existing: list[str] | None = None) -> list[str]:
    """Infer useful impact themes from free text and merge with existing themes."""
    themes = normalize_text_list(existing or [])
    lower = (text or "").lower()
    for keyword, hints in _THEME_HINTS.items():
        if keyword in lower:
            for hint in hints:
                if hint.lower() not in {t.lower() for t in themes}:
                    themes.append(hint)
    return themes
