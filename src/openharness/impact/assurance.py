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
        criteria=list(criteria or [
            "GIIN IRIS+ 5.3 metric definitions",
            "IMP 5 Dimensions of Impact",
            "UN Sustainable Development Goals",
        ]),
        evidence_index=list(evidence or []),
        chain_head_hash=chain_head_hash,
        chain_length=chain_length,
        assurer=assurer,
    )


__all__ = [
    "AssuranceLevel",
    "AssuranceStandard",
    "ManagementAssertion",
    "SubjectMatter",
    "EvidenceEntry",
    "AssurancePack",
    "build_assurance_pack",
]
