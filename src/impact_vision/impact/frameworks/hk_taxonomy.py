"""Hong Kong Taxonomy for Sustainable Finance — eligibility and alignment screen.

Hong Kong is a core market for Impact Vision users. The HKMA taxonomy
(Phase 1 prototype May 2024; Phase 2A final 2026-01-22; Phase 2B prototype
consultation closed 2026-10-07) follows the same three-step logic as the EU
Taxonomy: substantial contribution, do no significant harm, minimum
safeguards. This module therefore *wraps*
:func:`impact_vision.impact.frameworks.eu_taxonomy.assess_taxonomy_alignment`
for the percentage maths and adds:

* the HK activity catalogue (``data/hk_taxonomy.yaml``),
* keyword-based eligibility candidates from document text, and
* phase / provenance metadata so callers know which taxonomy version applies.

Screening-grade: an activity is only *aligned* when the caller confirms the
technical screening criteria, DNSH and minimum safeguards for it.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml
from pydantic import BaseModel, Field

from impact_vision.impact._paths import data_path
from impact_vision.impact.frameworks.eu_taxonomy import (
    EconomicActivity,
    TaxonomyAlignmentResult,
    assess_taxonomy_alignment,
)


class HKTaxonomyActivity(BaseModel):
    activity_id: str
    sector: str
    name: str
    objective: str = "climate_mitigation"
    phase: str = "1"
    keywords: list[str] = Field(default_factory=list)


class HKTaxonomyCandidate(BaseModel):
    activity_id: str
    name: str
    sector: str
    phase: str
    matched_keywords: list[str] = Field(default_factory=list)


class HKTaxonomyScreen(BaseModel):
    company_name: str
    candidates: list[HKTaxonomyCandidate] = Field(default_factory=list)
    alignment: TaxonomyAlignmentResult | None = None
    phases: list[dict[str, Any]] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    source_url: str = ""
    as_of: str = ""


@lru_cache(maxsize=1)
def _catalogue() -> dict[str, Any]:
    return yaml.safe_load(data_path("hk_taxonomy.yaml").read_text(encoding="utf-8")) or {}


def list_hk_activities(sector: str = "") -> list[HKTaxonomyActivity]:
    rows = [HKTaxonomyActivity.model_validate(r) for r in _catalogue().get("activities", [])]
    if sector:
        needle = sector.strip().casefold()
        rows = [r for r in rows if needle in r.sector.casefold()]
    return rows


def hk_taxonomy_metadata() -> dict[str, Any]:
    cat = _catalogue()
    return {k: cat.get(k) for k in ("regime", "as_of", "last_verified", "phases", "source", "source_url")}


def find_hk_candidates(text: str) -> list[HKTaxonomyCandidate]:
    """Activities whose keywords appear in *text* (word-boundary match)."""
    padded = f" {text.lower()} "
    out: list[HKTaxonomyCandidate] = []
    for act in list_hk_activities():
        hits = []
        for kw in act.keywords:
            k = kw.lower()
            if k.strip() != k:  # padded keyword: plain substring on the padded text
                found = k in padded
            else:
                found = re.search(rf"\b{re.escape(k)}\b", padded) is not None
            if found:
                hits.append(kw.strip())
        if hits:
            out.append(HKTaxonomyCandidate(
                activity_id=act.activity_id, name=act.name, sector=act.sector,
                phase=act.phase, matched_keywords=hits,
            ))
    return out


def screen_hk_taxonomy(
    company_name: str,
    *,
    text: str = "",
    activities: list[EconomicActivity | dict] | None = None,
    minimum_safeguards_corporate: bool = True,
) -> HKTaxonomyScreen:
    """Screen a company against the Hong Kong Taxonomy.

    ``text`` yields eligibility *candidates*. ``activities`` (revenue / capex /
    opex shares with ``eligible`` / ``substantial_contribution`` / ``dnsh_pass``
    flags, as for the EU screen) yields alignment percentages.
    """
    meta = hk_taxonomy_metadata()
    candidates = find_hk_candidates(text) if text else []
    alignment = None
    if activities:
        acts = [a if isinstance(a, EconomicActivity) else EconomicActivity.model_validate(a) for a in activities]
        alignment = assess_taxonomy_alignment(
            company_name, acts, minimum_safeguards_corporate=minimum_safeguards_corporate
        )
        alignment.references = [
            "HKMA Hong Kong Taxonomy for Sustainable Finance (Phase 1, 2024; Phase 2A, 2026-01-22)",
        ]
        alignment.findings = [f.replace("EU Taxonomy", "Hong Kong Taxonomy") for f in alignment.findings]
    next_steps = []
    if candidates and not activities:
        next_steps.append(
            "Split revenue / capex / opex by candidate activity and confirm the technical "
            "screening criteria, DNSH and minimum safeguards to compute alignment."
        )
    if not candidates and not activities:
        next_steps.append("No Hong Kong Taxonomy activity signals found in the text.")
    next_steps.append("Phase 2B is a consultation prototype: do not claim alignment against it yet.")
    return HKTaxonomyScreen(
        company_name=company_name,
        candidates=candidates,
        alignment=alignment,
        phases=list(meta.get("phases") or []),
        next_steps=next_steps,
        source_url=str(meta.get("source_url") or ""),
        as_of=str(meta.get("as_of") or ""),
    )


__all__ = [
    "HKTaxonomyActivity",
    "HKTaxonomyCandidate",
    "HKTaxonomyScreen",
    "find_hk_candidates",
    "hk_taxonomy_metadata",
    "list_hk_activities",
    "screen_hk_taxonomy",
]
