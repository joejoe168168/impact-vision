"""Injectable, review-gated regulatory change radar."""

from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from typing import Callable, Literal
from pydantic import BaseModel, Field
from openharness.impact.models import Company
from openharness.impact.evidence_workflow import ReviewQueue
from openharness.impact.roadmap_v2 import AIExtractionReview


_RADAR_REVIEW_QUEUE = ReviewQueue()


class TrackedStandard(BaseModel):
    standard_id: str
    watch_urls: list[str]
    last_seen_hash: str | None = None
    last_checked: str | None = None


class RadarFinding(BaseModel):
    standard_id: str
    change_kind: Literal["content_changed", "new_version", "deadline_changed", "manual_note"]
    summary: str
    detected_at: str
    affected_companies: list[str] = Field(default_factory=list)
    review_status: Literal["pending", "confirmed", "dismissed"] = "pending"
    review_item_id: str = ""


def _digest(content: str) -> str:
    return hashlib.sha256(" ".join(content.split()).encode()).hexdigest()


def check_tracked_standards(
    tracked: list[TrackedStandard], fetcher: Callable[[str], str]
) -> list[RadarFinding]:
    findings = []
    for standard in tracked:
        contents = []
        for url in standard.watch_urls:
            try:
                contents.append(fetcher(url))
            except Exception:
                continue
        if not contents:
            continue
        combined = "\n".join(contents)
        digest = _digest(combined)
        if standard.last_seen_hash and digest != standard.last_seen_hash:
            headings = re.findall(r"(?:^|\n)#{1,3}\s+(.+)", combined)[:3]
            finding = RadarFinding(
                standard_id=standard.standard_id,
                change_kind="content_changed",
                summary="Official-source content changed"
                + (f": {', '.join(headings)}" if headings else ""),
                detected_at=datetime.now(timezone.utc).isoformat(),
            )
            review = _RADAR_REVIEW_QUEUE.add(
                AIExtractionReview(
                    item_id=f"radar:{standard.standard_id}:{digest[:12]}",
                    extracted_text=finding.summary,
                    confidence=0.8,
                    rationale="Deterministic official-source hash change",
                    source_refs=list(standard.watch_urls),
                ),
                prompt_version="regulatory-radar-v1",
                model_version="deterministic",
            )
            finding.review_item_id = review.review.item_id
            findings.append(finding)
        standard.last_seen_hash = digest
        standard.last_checked = datetime.now(timezone.utc).isoformat()
    return findings


def portfolio_impact(finding: RadarFinding, companies: list[Company], packs=None) -> list[str]:
    del packs
    rules = {
        "SFDR": ("eu", "europe"),
        "ESRS": ("eu", "europe"),
        "SSE": ("china", "cn"),
        "CA_SB": ("california", "united states", "us"),
    }
    terms = next(
        (
            values
            for prefix, values in rules.items()
            if finding.standard_id.upper().startswith(prefix)
        ),
        (),
    )
    affected = [
        company.name
        for company in companies
        if any(term in company.geography.lower() for term in terms)
    ]
    finding.affected_companies = affected
    return affected


def suggest_registry_patch(finding: RadarFinding) -> dict:
    if finding.review_status != "confirmed":
        raise ValueError("Only confirmed findings can suggest a registry patch")
    return {
        "standard_id": finding.standard_id,
        "suggested_change": finding.summary,
        "requires_human_application": True,
    }


def decide_finding(
    finding: RadarFinding,
    status: Literal["confirmed", "dismissed"],
    *,
    reviewer: str = "human-reviewer",
) -> RadarFinding:
    """Synchronise a radar decision with the shared evidence review queue."""
    if finding.review_item_id:
        _RADAR_REVIEW_QUEUE.decide(
            finding.review_item_id,
            "approved" if status == "confirmed" else "rejected",
            reviewer=reviewer,
            rationale=f"Radar finding {status}",
        )
    finding.review_status = status
    return finding


__all__ = [
    "RadarFinding",
    "TrackedStandard",
    "check_tracked_standards",
    "decide_finding",
    "portfolio_impact",
    "suggest_registry_patch",
]
