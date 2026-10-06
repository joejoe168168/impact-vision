"""Reference knowledge as versioned data (v7 W5.1).

Regulatory dates, jurisdiction profiles, regulatory packs, the standards
registry, benchmarks and the framework crosswalk live in YAML under
``data/``. Every file carries file-level provenance (``as_of`` and usually
``source_url`` / ``source``), and any row may override it. A row's
*effective* provenance is its own field, falling back to the file's.

:func:`freshness_report` is the CI gate: a row whose effective
``last_verified`` (or ``as_of`` when it was never verified) is older than
``max_age_days`` is *stale*. Rows explicitly marked
``data_status: illustrative`` are reported but never fail the gate. They are
seed data, not facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from typing import Any, Callable, Iterable

import yaml

from openharness.impact._paths import data_path

MAX_AGE_DAYS = 180
PROVENANCE_KEYS = ("as_of", "last_verified", "source_url", "source")


@lru_cache(maxsize=None)
def load_knowledge(relative_path: str) -> dict[str, Any]:
    """Load and cache one knowledge YAML file (path relative to ``data/``)."""
    text = data_path(*relative_path.split("/")).read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def clear_cache() -> None:
    load_knowledge.cache_clear()


def _rows(key: str) -> Callable[[dict], Iterable[dict]]:
    return lambda payload: payload.get(key) or []


def _jurisdiction_rows(payload: dict) -> Iterable[dict]:
    for profile in payload.get("jurisdictions") or []:
        yield {k: v for k, v in profile.items() if k != "obligations"}
        for ob in profile.get("obligations") or []:
            # Obligations inherit the profile's issuing authority as their source.
            yield {"source": profile.get("source"), **ob,
                   "_label": f"{profile['jurisdiction']}:{ob.get('obligation_id')}"}


def _pack_rows(payload: dict) -> Iterable[dict]:
    for pack in payload.get("packs") or []:
        yield {"source": pack.get("issuer"), **pack}


def _benchmark_rows(payload: dict) -> Iterable[dict]:
    for section in ("sector_5d", "kpi", "peer_percentiles", "sample_observations"):
        block = payload.get(section) or []
        meta: dict = {}
        if isinstance(block, dict):  # section-level provenance + rows
            meta = {k: v for k, v in block.items() if k not in ("rows", "dimensions")}
            block = block.get("rows") or []
        for row in block:
            yield {**meta, **row, "_section": section}
    if payload.get("giin_survey"):
        yield {**payload["giin_survey"], "_section": "giin_survey"}


# name -> (relative path, row iterator, label key)
KNOWLEDGE_FILES: dict[str, tuple[str, Callable[[dict], Iterable[dict]], str]] = {
    "watchlist": ("regulatory/watchlist.yaml", _rows("milestones"), "event"),
    "jurisdictions": ("regulatory/jurisdictions.yaml", _jurisdiction_rows, "jurisdiction"),
    "regulatory_packs": ("regulatory/packs.yaml", _pack_rows, "jurisdiction"),
    "standards_registry": ("standards_registry.yaml", _rows("standards"), "standard_id"),
    "issb_adoption": ("issb_adoption.yaml", _rows("jurisdictions"), "jurisdiction"),
    "benchmarks": ("benchmarks.yaml", _benchmark_rows, "sector"),
    "crosswalk": ("concordance.yaml", _rows("crosswalk"), "concept"),
    "concordance": ("concordance.yaml", _rows("entries"), "concept_id"),
    "esrs_revised": ("esrs_simplified_2026.yaml", _rows("datapoints"), "datapoint_id"),
    "hk_taxonomy": ("hk_taxonomy.yaml", _rows("activities"), "activity_id"),
    "sfdr2": ("regulatory/sfdr2.yaml", lambda p: [{"category": k, **v} for k, v in (p.get("categories") or {}).items()],
              "category"),
}


def effective_provenance(row: dict, payload: dict) -> dict[str, Any]:
    """Row provenance with file-level fallbacks."""
    out = {key: row.get(key) or payload.get(key) for key in PROVENANCE_KEYS}
    out["data_status"] = row.get("data_status") or payload.get("data_status") or "published"
    return out


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


@dataclass
class FreshnessIssue:
    file: str
    row: str
    problem: str


@dataclass
class FreshnessReport:
    today: date
    max_age_days: int
    rows_checked: int = 0
    verified: int = 0
    with_source_url: int = 0
    illustrative: int = 0
    stale: list[FreshnessIssue] = field(default_factory=list)
    missing: list[FreshnessIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.stale and not self.missing

    def summary(self) -> str:
        lines = [
            f"Knowledge freshness as of {self.today} (max age {self.max_age_days} days)",
            f"  rows checked: {self.rows_checked}; verified: {self.verified}; "
            f"with source_url: {self.with_source_url}; illustrative: {self.illustrative}",
            f"  stale: {len(self.stale)}; missing provenance: {len(self.missing)}",
        ]
        for issue in [*self.missing, *self.stale][:40]:
            lines.append(f"  - {issue.file}: {issue.row}: {issue.problem}")
        return "\n".join(lines)


def freshness_report(
    *, today: date | None = None, max_age_days: int = MAX_AGE_DAYS, names: Iterable[str] | None = None
) -> FreshnessReport:
    """Check every knowledge row for provenance and age."""
    ref = today or date.today()
    report = FreshnessReport(today=ref, max_age_days=max_age_days)
    for name in names or KNOWLEDGE_FILES:
        rel, iterator, label_key = KNOWLEDGE_FILES[name]
        payload = load_knowledge(rel)
        for index, row in enumerate(iterator(payload)):
            label = str(row.get("_label") or row.get(label_key) or f"row {index}")[:70]
            prov = effective_provenance(row, payload)
            report.rows_checked += 1
            if prov["source_url"]:
                report.with_source_url += 1
            if prov["last_verified"]:
                report.verified += 1
            if not prov["as_of"]:
                report.missing.append(FreshnessIssue(rel, label, "no as_of (row or file)"))
                continue
            if not (prov["source_url"] or prov["source"]):
                report.missing.append(FreshnessIssue(rel, label, "no source_url or source"))
            if prov["data_status"] == "illustrative":
                report.illustrative += 1
                continue
            basis = _as_date(prov["last_verified"]) or _as_date(prov["as_of"])
            if basis is None:
                report.missing.append(FreshnessIssue(rel, label, f"unparseable date {prov['as_of']!r}"))
            elif (ref - basis).days > max_age_days:
                kind = "last verified" if prov["last_verified"] else "as of (never verified)"
                report.stale.append(FreshnessIssue(rel, label, f"{kind} {basis} — {(ref - basis).days} days old"))
    return report


__all__ = [
    "KNOWLEDGE_FILES",
    "MAX_AGE_DAYS",
    "FreshnessIssue",
    "FreshnessReport",
    "clear_cache",
    "effective_provenance",
    "freshness_report",
    "load_knowledge",
]
