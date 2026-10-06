"""Sustainability assurance pack generator (Phase 17; ISSA 5000 framing v7 W4.6).

Builds the bundle an external assurer needs to issue a limited-assurance
opinion over an impact report: management assertion, subject matter,
criteria, evidence index, the signed-feed chain head and a register of
where AI was used for each figure.

ISSA 5000 (IAASB) is effective for periods beginning on or after
2026-12-15 and replaces ISAE 3000 / ISAE 3410 for sustainability
engagements; Hong Kong adopts it as HKSSA 5000 from the same date. The
generator stays framework-neutral — the same bundle works for:

* ISSA 5000 / HKSSA 5000 (default for periods from 2026-12-15)
* ISAE 3000 / ISAE 3410 (earlier periods only)
* AA1000AS v3 (AccountAbility)

It does not *perform* the assurance; it formalises the input pack so an
independent firm (Big-4 or boutique) can reach a documented opinion.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.ai_provenance import AIUseRecord


AssuranceLevel = Literal["limited", "reasonable", "agreed_upon"]
AssuranceStandard = Literal["ISSA5000", "HKSSA5000", "ISAE3000", "AA1000AS", "ISAE3410"]

ISSA_5000_EFFECTIVE = date(2026, 12, 15)


def recommended_assurance_standard(
    period_start: date | str | None = None,
    *,
    jurisdiction: str = "",
    climate_only: bool = False,
) -> AssuranceStandard:
    """Pick the assurance standard for a reporting period.

    Periods beginning on or after 2026-12-15 (or an unknown period, i.e. new
    work) use ISSA 5000, or HKSSA 5000 in Hong Kong. Earlier periods keep
    ISAE 3000, or ISAE 3410 for a GHG-statement-only scope.
    """
    if isinstance(period_start, str) and period_start:
        period_start = date.fromisoformat(period_start[:10])
    if period_start is None or period_start >= ISSA_5000_EFFECTIVE:  # type: ignore[operator]
        hk = jurisdiction.strip().casefold() in {"hk", "hong kong", "hong kong sar", "hksar"}
        return "HKSSA5000" if hk else "ISSA5000"
    return "ISAE3410" if climate_only else "ISAE3000"


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
    """Complete assurance input pack (ISSA 5000 by default)."""

    standard: AssuranceStandard = "ISSA5000"
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
    period_start: date | None = None
    ai_use: list[AIUseRecord] = Field(
        default_factory=list,
        description="Where AI was used per figure (extraction / calculation / tagging / drafting)",
    )


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
    standard: AssuranceStandard | None = None,
    level: AssuranceLevel = "limited",
    chain_head_hash: str = "",
    chain_length: int = 0,
    assurer: str = "",
    scope_boundaries: list[str] | None = None,
    exclusions: list[str] | None = None,
    period_start: date | str | None = None,
    jurisdiction: str = "",
    ai_use: list[AIUseRecord] | None = None,
) -> AssurancePack:
    """Return a ready-to-ship :class:`AssurancePack`.

    ``standard`` defaults to :func:`recommended_assurance_standard` for
    ``period_start`` / ``jurisdiction`` (ISSA 5000 for new periods).
    """
    if isinstance(period_start, str) and period_start:
        period_start = date.fromisoformat(period_start[:10])
    if not period_start:
        # "FY2025" / "2025" / "FY2026/27" → start of that year (calendar-year default).
        match = re.search(r"(?<!\d)(20\d{2})(?!\d)", reporting_period or "")
        period_start = date(int(match.group(1)), 1, 1) if match else None
    return AssurancePack(
        standard=standard or recommended_assurance_standard(period_start, jurisdiction=jurisdiction),
        period_start=period_start or None,
        ai_use=list(ai_use or []),
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
    if isinstance(assessment, dict) and "ai_use" in assessment:
        ai_use = [r if isinstance(r, dict) else r.model_dump(mode="json") for r in assessment["ai_use"]]
    elif isinstance(assessment, dict) and ("impact_claims" in assessment or "five_dimensions" in assessment):
        from openharness.impact.ai_provenance import ai_provenance_for_report

        ai_use = [r.model_dump(mode="json") for r in ai_provenance_for_report(assessment).records]
    else:
        ai_use = []
    core = {
        "standard": "ISSA 5000",
        "jurisdictional_equivalents": {"HK": "HKSSA 5000"},
        "effective_for_periods_beginning": "2026-12-15",
        "ai_use_register": ai_use,
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
    "ISSA_5000_EFFECTIVE",
    "recommended_assurance_standard",
    "ManagementAssertion",
    "SubjectMatter",
    "EvidenceEntry",
    "AssurancePack",
    "build_assurance_pack",
    "Assertion",
    "EvidenceSufficiency",
    "build_issa5000_pack",
]
