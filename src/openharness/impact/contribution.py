"""Investor Contribution 2.0 claim registration and monitoring.

Grades are deterministic: A requires all planned activities evidenced and the
latest activity within 90 days; B >=75%/180d; C >=50%/365d; D any evidence;
E none. Grades assess monitoring practice, never causal attribution.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from pydantic import BaseModel, Field

from openharness.impact.audit_trail import AuditTrail
from openharness.impact.evidence_graph import EvidenceGraph, EvidenceLink, EvidenceNode
from openharness.impact.models import MetricRecord


class ContributionChannel(str, Enum):
    CAPITAL_ADDITIONALITY = "capital_additionality"
    NON_FINANCIAL_SUPPORT = "non_financial_support"
    MARKET_SIGNAL = "market_signal"
    FLEXIBLE_TERMS = "flexible_terms"
    NEW_MARKET_CATALYSED = "new_market_catalysed"


class ContributionClaim(BaseModel):
    claim_id: str
    company: str
    channel: ContributionChannel
    narrative: str
    stated_at: str
    planned_activities: list[dict] = Field(default_factory=list)
    attribution_pct: float | None = Field(default=None, ge=0, le=100)
    evidence_node_ids: list[str] = Field(default_factory=list)


class ContributionEvidence(BaseModel):
    activity_id: str
    occurred_at: str
    description: str
    artifact_refs: list[str] = Field(default_factory=list)
    outcome_link: str | None = None


def register_contribution_claim(
    claim: ContributionClaim, graph: EvidenceGraph, trail: AuditTrail
) -> dict:
    node_id = f"claim:contribution:{claim.claim_id}"
    if node_id in graph.node_ids():
        raise ValueError(
            f"Contribution claim {claim.claim_id} already exists; stated_at is immutable"
        )
    graph.nodes.append(
        EvidenceNode(
            id=node_id,
            type="claim",
            label=claim.narrative[:120],
            data=claim.model_dump(mode="json"),
        )
    )
    event = trail.record_event(
        event_type="contribution.claim_registered",
        payload=claim.model_dump(mode="json"),
        actor="investor",
        period=claim.stated_at[:7],
    )
    return {"claim_node_id": node_id, "audit_hash": event.content_hash}


def log_contribution_activity(
    claim_id: str, evidence: ContributionEvidence, graph: EvidenceGraph, trail: AuditTrail
) -> dict:
    claim_node = f"claim:contribution:{claim_id}"
    if claim_node not in graph.node_ids():
        raise KeyError(f"Unknown contribution claim: {claim_id}")
    evidence_id = f"evidence:contribution:{claim_id}:{evidence.activity_id}:{evidence.occurred_at}"
    graph.nodes.append(
        EvidenceNode(
            id=evidence_id,
            type="evidence",
            label=evidence.description,
            data=evidence.model_dump(mode="json"),
        )
    )
    graph.links.append(
        EvidenceLink(
            source=claim_node,
            target=evidence_id,
            type="supported_by",
            rationale="Contribution activity evidence",
        )
    )
    if evidence.outcome_link:
        graph.links.append(
            EvidenceLink(
                source=claim_node,
                target=f"metric:{evidence.outcome_link.upper()}",
                type="measured_by",
                confidence=0.5,
                rationale="Plausible outcome link; not causal certification",
            )
        )
    event = trail.record_event(
        event_type="contribution.activity_logged",
        payload={"claim_id": claim_id, **evidence.model_dump(mode="json")},
        actor="investor",
        period=evidence.occurred_at[:7],
    )
    return {"evidence_node_id": evidence_id, "audit_hash": event.content_hash}


def _grade(coverage: float, stale_days: int | None, count: int) -> str:
    if count == 0:
        return "E"
    if coverage >= 1 and stale_days is not None and stale_days <= 90:
        return "A"
    if coverage >= 0.75 and stale_days is not None and stale_days <= 180:
        return "B"
    if coverage >= 0.5 and stale_days is not None and stale_days <= 365:
        return "C"
    return "D"


def contribution_scorecard(
    claims: list[ContributionClaim],
    evidence: list[ContributionEvidence],
    records: list[MetricRecord],
    *,
    as_of: date | None = None,
) -> dict:
    del records
    reference = as_of or date.today()
    rows, recent = [], 0
    for claim in claims:
        ids = {str(item.get("activity_id", "")) for item in claim.planned_activities}
        relevant = [item for item in evidence if item.activity_id in ids]
        covered = {item.activity_id for item in relevant}
        coverage = len(covered) / len(ids) if ids else 0.0
        last = max((date.fromisoformat(item.occurred_at[:10]) for item in relevant), default=None)
        stale = (reference - last).days if last else None
        recent += int(stale is not None and stale <= 365)
        rows.append(
            {
                "claim_id": claim.claim_id,
                "coverage_pct": round(100 * coverage, 1),
                "staleness_days": stale,
                "grade": _grade(coverage, stale, len(relevant)),
                "attribution_inflation": claim.attribution_pct is not None and len(relevant) < 2,
                "missing_activities": sorted(ids - covered),
            }
        )
    return {
        "claims": rows,
        "monitored_last_12m_pct": round(100 * recent / len(claims), 1) if claims else 0.0,
    }


def attribution_sanity_check(company: str, investor_claims: list[dict]) -> dict:
    total = sum(float(item.get("attribution_pct") or 0) for item in investor_claims)
    return {
        "company": company,
        "total_attribution_pct": total,
        "inflated": total > 100,
        "rewrite": "Use contribution language and evidence each investor role; do not allocate more than 100% across co-investors."
        if total > 100
        else "",
    }


__all__ = [
    "ContributionChannel",
    "ContributionClaim",
    "ContributionEvidence",
    "attribution_sanity_check",
    "contribution_scorecard",
    "log_contribution_activity",
    "register_contribution_claim",
]
