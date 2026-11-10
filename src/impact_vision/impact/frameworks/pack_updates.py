"""Sourced updates to the GRI, SBTi and EU Taxonomy packs (R6 / R7).

Dates, version numbers and thresholds live in ``data/frameworks/updates.yaml`` with
their source; nothing here is hard-coded. A row marked ``verified: unverified`` is a
watchlist item and is never used in a check.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

import yaml

from impact_vision.impact._paths import data_path


@lru_cache(maxsize=1)
def load_updates() -> dict[str, Any]:
    with open(data_path("frameworks", "updates.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _day(value: str) -> date:
    parts = [int(p) for p in str(value).split("-")]
    return date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)


def gri_successor(code: str, on: date | None = None) -> dict[str, Any] | None:
    """The topic standard that replaces *code* ("GRI 304", "305-1") on the given day, if any.

    Before the successor's effective date the old standard or disclosure is still the
    one to report against, so this returns ``None``.
    """
    on = on or date.today()
    code = code.strip()
    for row in load_updates()["gri"]["topic_standards"]:
        if row.get("verified") == "unverified" or code not in row.get("supersedes", []):
            continue
        if on >= _day(row["effective_date"]):
            return row
    return None


def gri_upcoming(code: str, on: date | None = None) -> dict[str, Any] | None:
    """A published replacement for *code* that is not yet in force on the given day."""
    on = on or date.today()
    for row in load_updates()["gri"]["topic_standards"]:
        if code.strip() in row.get("supersedes", []) and on < _day(row["effective_date"]):
            return row
    return None


def gri_sector_standards() -> list[dict[str, Any]]:
    return list(load_updates()["gri"]["sector_standards"]["published"])


def sbti_standard_in_force(on: date | None = None) -> list[dict[str, Any]]:
    """Net-zero standard versions a company may submit targets under on the given day."""
    on = on or date.today()
    out = []
    for row in load_updates()["sbti"]["standards"]:
        if row.get("verified") == "unverified" or not row["id"].startswith("CNZS"):
            continue
        if "usable_from" in row and on < _day(row["usable_from"]):
            continue
        if "usable_until" in row and on > _day(row["usable_until"]):
            continue
        out.append(row)
    return out


def taxonomy_non_material(shares_pct: dict[str, float]) -> bool:
    """True when activities may be reported as non-material under (EU) 2026/73.

    *shares_pct* is the activities' combined share of each KPI (turnover / capex / opex).
    """
    limit = float(load_updates()["eu_taxonomy"]["simplification"]["materiality_threshold_pct"])
    return bool(shares_pct) and all(v < limit for v in shares_pct.values())


def taxonomy_references() -> list[str]:
    return [f"{row['id']} — {row['title']} (in force {row['in_force']})"
            for row in load_updates()["eu_taxonomy"]["delegated_acts"]]
