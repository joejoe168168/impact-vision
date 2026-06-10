"""Runtime loader for reviewed ohESG source profiles."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from openharness.impact.toolbox.models import ToolboxSourceIndexRecord, ToolboxSourceProfile


SOURCE_PROFILE_DIR = Path(__file__).resolve().parents[4] / "data" / "raw" / "ohesg_toolbox"


@lru_cache(maxsize=1)
def list_source_profiles() -> tuple[ToolboxSourceProfile, ...]:
    """Load all reviewed per-tool ohESG source profiles."""
    if not SOURCE_PROFILE_DIR.exists():
        return ()
    profiles: list[ToolboxSourceProfile] = []
    for path in sorted(SOURCE_PROFILE_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        profiles.append(ToolboxSourceProfile.model_validate(payload))
    return tuple(profiles)


def get_source_profile(tool_id: str) -> ToolboxSourceProfile | None:
    """Return a source profile by tool ID."""
    key = tool_id.strip().lower().replace("_", "-")
    for profile in list_source_profiles():
        if profile.tool_id == key:
            return profile
    return None


def source_keyword_coverage(tool_id: str, runtime_terms: list[str]) -> dict[str, object]:
    """Compare source-profile keywords against runtime terms for audit tests."""
    profile = get_source_profile(tool_id)
    if profile is None:
        return {"tool_id": tool_id, "source_keyword_count": 0, "matched": [], "missing": []}

    runtime_haystack = " ".join(runtime_terms).lower()
    matched: list[str] = []
    missing: list[str] = []
    for keyword in profile.keywords:
        if keyword.lower() in runtime_haystack:
            matched.append(keyword)
        else:
            missing.append(keyword)
    return {
        "tool_id": profile.tool_id,
        "source_keyword_count": len(profile.keywords),
        "matched": matched,
        "missing": missing,
        "coverage_pct": round(len(matched) / max(len(profile.keywords), 1) * 100),
    }


def search_source_index(
    tool_id: str,
    query: str,
    *,
    record_types: tuple[str, ...] = (),
    limit: int = 10,
) -> list[ToolboxSourceIndexRecord]:
    """Search one module's archived ohESG dataset records by keyword overlap.

    Supports both Latin terms and CJK substrings so sector/topic lookups work
    with English company descriptions and the bilingual ohESG index.
    """
    # Imported lazily: registry loads snapshot data at import time and does not
    # depend on this module, so the lazy import avoids a cycle.
    from openharness.impact.toolbox.registry import get_toolbox_tool

    try:
        spec = get_toolbox_tool(tool_id)
    except KeyError:
        return []
    terms = [term for term in re.split(r"[^\w\u4e00-\u9fff.-]+", query.lower()) if len(term) >= 2]
    if not terms:
        return []
    scored: list[tuple[int, ToolboxSourceIndexRecord]] = []
    for record in spec.source_index:
        if record_types and record.record_type not in record_types:
            continue
        haystack = " ".join(
            [record.record_id, record.title, record.summary, record.category, record.record_type, *record.keywords]
        ).lower()
        score = sum(1 for term in terms if term in haystack)
        if score:
            scored.append((score, record))
    scored.sort(key=lambda item: (-item[0], item[1].record_id))
    return [record for _, record in scored[: max(1, limit)]]


__all__ = [
    "SOURCE_PROFILE_DIR",
    "get_source_profile",
    "list_source_profiles",
    "search_source_index",
    "source_keyword_coverage",
]
