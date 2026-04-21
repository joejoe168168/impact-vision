"""Marketplace of impact theses (Phase 16).

A lightweight, in-memory publish-subscribe registry that lets GPs
publish their anonymised ``fund_thesis.yaml`` so LPs can:

* compare mandates across managers in the same sector
* discover co-investment opportunities
* see which GPs share an SDG / geographic focus

No authentication / billing is included — this is the plumbing layer.
Persistence can be added by subclassing :class:`ThesisMarketplace` and
overriding ``publish`` / ``list`` to talk to Postgres, S3, Supabase, etc.

The comparison routine is deliberately structural (not NLP) so it's
deterministic and cheap.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from pydantic import BaseModel, Field

from openharness.impact.fund_thesis import FundThesis


class ThesisListing(BaseModel):
    """One published thesis."""

    listing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    gp_name: str
    thesis: FundThesis
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    anonymised: bool = True
    visibility: str = "public"  # "public" | "private" | "lp-only"


class ThesisMatch(BaseModel):
    """Similarity score between two listings."""

    listing_a: str
    listing_b: str
    score: float = Field(ge=0, le=1)
    overlap_sdgs: list[int] = Field(default_factory=list)
    overlap_sectors: list[str] = Field(default_factory=list)
    overlap_geographies: list[str] = Field(default_factory=list)


@dataclass
class ThesisMarketplace:
    """In-memory pub-sub for impact theses. Thread-unsafe by design."""

    listings: dict[str, ThesisListing] = field(default_factory=dict)

    def publish(self, gp_name: str, thesis: FundThesis, *, visibility: str = "public") -> ThesisListing:
        listing = ThesisListing(gp_name=gp_name, thesis=thesis, visibility=visibility)
        self.listings[listing.listing_id] = listing
        return listing

    def list_public(self) -> list[ThesisListing]:
        return [lst for lst in self.listings.values() if lst.visibility == "public"]

    def search(
        self,
        *,
        sdg: int | None = None,
        sector: str | None = None,
        geography: str | None = None,
    ) -> list[ThesisListing]:
        out = self.list_public()
        if sdg is not None:
            out = [lst for lst in out if (lst.thesis.sdg_weights or {}).get(sdg, 0) > 0]
        if sector is not None:
            out = [lst for lst in out if sector.lower() in lst.thesis.strategy.lower()]
        if geography is not None:
            out = [
                lst for lst in out
                if geography.upper() in [g.upper() for g in (lst.thesis.geography_focus or [])]
            ]
        return out

    def compare(self, listing_a: str, listing_b: str) -> ThesisMatch | None:
        a = self.listings.get(listing_a)
        b = self.listings.get(listing_b)
        if not a or not b:
            return None
        a_sdgs = {k for k, v in (a.thesis.sdg_weights or {}).items() if v > 0}
        b_sdgs = {k for k, v in (b.thesis.sdg_weights or {}).items() if v > 0}
        a_sec = {a.thesis.strategy.lower()}
        b_sec = {b.thesis.strategy.lower()}
        a_geo = {g.upper() for g in (a.thesis.geography_focus or [])}
        b_geo = {g.upper() for g in (b.thesis.geography_focus or [])}
        score = (
            _jaccard(a_sdgs, b_sdgs) * 0.45
            + _jaccard(a_sec, b_sec) * 0.35
            + _jaccard(a_geo, b_geo) * 0.20
        )
        return ThesisMatch(
            listing_a=listing_a,
            listing_b=listing_b,
            score=round(score, 3),
            overlap_sdgs=sorted(a_sdgs & b_sdgs),
            overlap_sectors=sorted(a_sec & b_sec),
            overlap_geographies=sorted(a_geo & b_geo),
        )

    def top_matches(self, listing_id: str, *, k: int = 5) -> list[ThesisMatch]:
        matches: list[ThesisMatch] = []
        for other_id in self.listings:
            if other_id == listing_id:
                continue
            m = self.compare(listing_id, other_id)
            if m and m.score > 0:
                matches.append(m)
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:k]


def _jaccard(a: Iterable, b: Iterable) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


__all__ = [
    "ThesisListing",
    "ThesisMatch",
    "ThesisMarketplace",
]
