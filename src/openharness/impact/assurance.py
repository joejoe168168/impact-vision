"""ISAE 3000 / AA1000 assurance pack generator (Phase 17).

Builds the bundle an external assurer needs to issue a limited-assurance
opinion over an impact report: management assertion, subject matter,
criteria, evidence index and the signed-feed chain head.

The generator is framework-neutral — the same bundle works for:

* ISAE 3000 (International Standard on Assurance Engagements)
* AA1000AS v3 (AccountAbility)
* ISAE 3410 (Greenhouse Gas Statements) — for climate-only scopes

It does not *perform* the assurance; it formalises the input pack so an
independent firm (Big-4 or boutique) can reach a documented opinion.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


AssuranceLevel = Literal["limited", "reasonable", "agreed_upon"]
AssuranceStandard = Literal["ISAE3000", "AA1000AS", "ISAE3410"]


class ManagementAssertion(BaseModel):
    """Statement prepared by fund management about the reported impact."""

    fund_name: str
    reporting_period: str
    assertion_text: str
    prepared_by: str
    prepared_at: date = Field(default_factory=date.today)


class SubjectMatter(BaseModel):
    """What exactly is being assured."""

    description: str
    scope_boundaries: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class EvidenceEntry(BaseModel):
    """One piece of supporting evidence."""

    entry_id: str
    description: str
    evidence_type: Literal["primary", "secondary", "third_party"] = "primary"
    document_ref: str = ""
    hash_ref: str = ""
    date_collected: date = Field(default_factory=date.today)


class AssurancePack(BaseModel):
    """Complete ISAE 3000 / AA1000 input pack."""

    standard: AssuranceStandard = "ISAE3000"
    level: AssuranceLevel = "limited"
    fund_name: str
    reporting_period: str
    assertion: ManagementAssertion
    subject_matter: SubjectMatter
    criteria: list[str] = Field(default_factory=list)
    evidence_index: list[EvidenceEntry] = Field(default_factory=list)
    chain_head_hash: str = ""
    chain_length: int = 0
    produced_at: date = Field(default_factory=date.today)
    assurer: str = ""
    limitations: list[str] = Field(default_factory=list)


def build_assurance_pack(
    *,
    fund_name: str,
    reporting_period: str,
    assertion_text: str,
    prepared_by: str,
    subject_description: str,
    metrics: list[str],
    criteria: list[str] | None = None,
    evidence: list[EvidenceEntry] | None = None,
    standard: AssuranceStandard = "ISAE3000",
    level: AssuranceLevel = "limited",
    chain_head_hash: str = "",
    chain_length: int = 0,
    assurer: str = "",
    scope_boundaries: list[str] | None = None,
    exclusions: list[str] | None = None,
) -> AssurancePack:
    """Return a ready-to-ship :class:`AssurancePack`."""
    return AssurancePack(
        standard=standard,
        level=level,
        fund_name=fund_name,
        reporting_period=reporting_period,
        assertion=ManagementAssertion(
            fund_name=fund_name,
            reporting_period=reporting_period,
            assertion_text=assertion_text,
            prepared_by=prepared_by,
        ),
        subject_matter=SubjectMatter(
            description=subject_description,
            scope_boundaries=list(scope_boundaries or []),
            metrics=list(metrics),
            exclusions=list(exclusions or []),
        ),
        criteria=list(
            criteria
            or [
                "GIIN IRIS+ 5.3 metric definitions",
                "IMP 5 Dimensions of Impact",
                "UN Sustainable Development Goals",
            ]
        ),
        evidence_index=list(evidence or []),
        chain_head_hash=chain_head_hash,
        chain_length=chain_length,
        assurer=assurer,
    )


class Assertion(BaseModel):
    assertion_id: str
    statement: str
    subject_matter: str
    criteria: str
    evidence_node_ids: list[str] = Field(default_factory=list)


class EvidenceSufficiency(BaseModel):
    assertion_id: str
    evidence_count: int
    independent_evidence: bool
    quality_band: Literal["high", "medium", "low"]
    sufficient_for: Literal["reasonable", "limited", "neither"]
    gaps: list[str] = Field(default_factory=list)


def _issa_sufficiency(assertion: Assertion, graph) -> EvidenceSufficiency:
    nodes = [node for node in graph.nodes if node.id in assertion.evidence_node_ids]
    independent = any(
        node.data.get("source_type")
        in {"audited_statement", "third_party", "registry_api", "remote_sensing"}
        or node.data.get("independent")
        for node in nodes
    )
    qualities = [int(node.data.get("quality_score", 50)) for node in nodes]
    average = sum(qualities) / len(qualities) if qualities else 0
    band = "high" if average >= 80 else "medium" if average >= 50 else "low"
    reasonable = len(nodes) >= 2 and independent and band == "high"
    limited = len(nodes) >= 1 and band in {"high", "medium"}
    gaps = []
    if len(nodes) < 2:
        gaps.append("reasonable assurance requires at least two evidence nodes")
    if not independent:
        gaps.append("reasonable assurance requires independent evidence")
    if band != "high":
        gaps.append("reasonable assurance requires high-quality evidence")
    if not nodes:
        gaps.append("limited assurance requires at least one evidence node")
    if band == "low":
        gaps.append("limited assurance requires medium-or-better quality")
    return EvidenceSufficiency(
        assertion_id=assertion.assertion_id,
        evidence_count=len(nodes),
        independent_evidence=independent,
        quality_band=band,
        sufficient_for="reasonable" if reasonable else "limited" if limited else "neither",
        gaps=gaps,
    )


def build_issa5000_pack(assessment, graph, trail, level: Literal["limited", "reasonable"]) -> dict:
    from openharness.impact.signed_feed import content_hash

    raw = (
        assessment.get("assertions", [])
        if isinstance(assessment, dict)
        else getattr(assessment, "assertions", [])
    )
    assertions = [
        item if isinstance(item, Assertion) else Assertion.model_validate(item) for item in raw
    ]
    sufficiency = [_issa_sufficiency(item, graph) for item in assertions]
    gaps = [
        {"assertion_id": row.assertion_id, "failed_rules": row.gaps}
        for row in sufficiency
        if row.sufficient_for != level
        and not (level == "limited" and row.sufficient_for == "reasonable")
    ]
    core = {
        "standard": "ISSA 5000",
        "effective_for_periods_beginning": "2026-12-15",
        "level": level,
        "assertions": [item.model_dump(mode="json") for item in assertions],
        "sufficiency": [item.model_dump(mode="json") for item in sufficiency],
        "limited_vs_reasonable_gap": gaps,
        "engagement_acceptance": {
            "criteria_suitable": all(item.criteria for item in assertions),
            "management_assertions_present": bool(assertions),
            "preconditions_met": bool(assertions) and not gaps,
        },
        "audit_trail_head": trail.head,
    }
    digest = content_hash(core)
    signature = trail.signer.sign(digest.encode())
    return {
        **core,
        "manifest": {"content_hash": digest, "signature": signature, "signer_id": trail.signer.id},
    }


__all__ = [
    "AssuranceLevel",
    "AssuranceStandard",
    "ManagementAssertion",
    "SubjectMatter",
    "EvidenceEntry",
    "AssurancePack",
    "build_assurance_pack",
    "Assertion",
    "EvidenceSufficiency",
    "build_issa5000_pack",
]
