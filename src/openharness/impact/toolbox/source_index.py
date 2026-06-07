"""Runtime loader for reviewed ohESG source profiles."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from openharness.impact.toolbox.models import ToolboxSourceProfile


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


__all__ = ["SOURCE_PROFILE_DIR", "get_source_profile", "list_source_profiles", "source_keyword_coverage"]
