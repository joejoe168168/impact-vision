"""Small shared helpers (formerly private to roadmap_v2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: str) -> datetime:
    """Parse ISO datetimes and normalize naive values to UTC."""
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _to_float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: float, denominator: float | int | None) -> float | None:
    if denominator is None or denominator == 0:
        return None
    return round(numerator / denominator, 6)
