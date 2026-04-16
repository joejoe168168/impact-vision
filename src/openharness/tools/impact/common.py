"""Shared helpers for impact tools input normalization."""

from __future__ import annotations

import re
from collections.abc import Iterable


METRIC_ID_PATTERN = re.compile(r"^(PI|OI|OD|FP|PD)\d{4}$", re.IGNORECASE)

_DEFAULTS_THEME_HINTS: dict[str, list[str]] = {
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


def _get_theme_hints() -> dict[str, list[str]]:
    """Load theme hints from scoring config, fall back to defaults."""
    try:
        from openharness.impact.five_dimensions import _load_scoring_config
        config = _load_scoring_config()
        return config.get("theme_hints", _DEFAULTS_THEME_HINTS)
    except Exception:
        return _DEFAULTS_THEME_HINTS


def normalize_str_list(values: Iterable[str] | None) -> list[str]:
    """Return a de-duplicated list of non-empty stripped strings, preserving order."""
    if not values:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join((str(value) or "").split()).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def normalize_metric_map(
    metrics: dict[str, str] | None,
) -> tuple[dict[str, str], list[str]]:
    """Normalize IRIS metric IDs (uppercase, stripped) and return warnings for invalid keys."""
    if not metrics:
        return {}, []
    normalized: dict[str, str] = {}
    warnings: list[str] = []
    for key, value in metrics.items():
        metric_id = (str(key) or "").strip().upper()
        if not metric_id:
            continue
        if not METRIC_ID_PATTERN.match(metric_id):
            warnings.append(f"Ignored invalid metric ID: {key}")
            continue
        normalized[metric_id] = "" if value is None else str(value).strip()
    return normalized, warnings


def normalize_metric_ids(values: Iterable[str] | None) -> tuple[list[str], list[str]]:
    """Normalize a list of metric ID strings. Returns (valid_ids, warnings)."""
    if not values:
        return [], []
    normalized: list[str] = []
    warnings: list[str] = []
    for value in values:
        metric_id = (str(value) or "").strip().upper()
        if not metric_id:
            continue
        if not METRIC_ID_PATTERN.match(metric_id):
            warnings.append(f"Ignored invalid metric ID: {value}")
            continue
        if metric_id not in normalized:
            normalized.append(metric_id)
    return normalized, warnings


def normalize_sdg_goals(values: Iterable[int] | None) -> tuple[list[int], list[str]]:
    """Return valid SDG goal numbers (1-17), de-duplicated. Returns (goals, warnings)."""
    if not values:
        return [], []
    out: list[int] = []
    warnings: list[str] = []
    seen: set[int] = set()
    for value in values or []:
        try:
            goal = int(value)
        except (TypeError, ValueError):
            continue
        if goal < 1 or goal > 17:
            warnings.append(f"Ignored invalid SDG goal: {goal} (valid range: 1-17)")
            continue
        if goal in seen:
            continue
        seen.add(goal)
        out.append(goal)
    return out, warnings


def infer_themes(text: str, existing: list[str] | None = None) -> list[str]:
    """Infer impact themes from free text and merge with existing themes."""
    themes = normalize_str_list(existing or [])
    lower = (text or "").lower()
    for keyword, hints in _get_theme_hints().items():
        if keyword in lower:
            for hint in hints:
                if hint.lower() not in {t.lower() for t in themes}:
                    themes.append(hint)
    return themes


def parse_od4091_targets(value: str) -> list[dict]:
    """Parse OD4091 (Social and Environmental Targets) into structured target dicts.

    Handles formats like:
    - "3 social targets, 2 environmental targets"
    - "Reduce CO2 by 50% by 2027; Reach 100,000 farmers by 2026"
    - "500 tCO2e by 2027"
    """
    if not value or not value.strip():
        return []

    targets: list[dict] = []

    parts = re.split(r"[;|\n]", value)
    for part in parts:
        part = part.strip()
        if not part:
            continue

        target: dict = {"description": part}

        year_match = re.search(r"\b(20\d{2})\b", part)
        if year_match:
            target["target_date"] = year_match.group(1)

        num_match = re.search(r"([\d,]+(?:\.\d+)?)\s*(%|tCO2e|tons?|kg|MWh|kWh|USD|EUR|people|farmers?|clients?|beneficiar)", part, re.IGNORECASE)
        if num_match:
            try:
                target["target_value"] = float(num_match.group(1).replace(",", ""))
                target["target_unit"] = num_match.group(2).strip()
            except ValueError:
                pass

        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", part)
        if pct_match and "target_value" not in target:
            target["target_value"] = float(pct_match.group(1))
            target["target_unit"] = "%"

        targets.append(target)

    return targets
