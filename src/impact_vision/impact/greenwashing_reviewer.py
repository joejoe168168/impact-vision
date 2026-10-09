"""Explainable per-claim greenwashing reviewer (v3 Track 9.3).

Wraps :mod:`impact_vision.impact.greenwashing` (which produces aggregate
0-100 sub-scores plus flags) into a per-claim reviewer output that is
actually **decision-useful**:

* one :class:`ClaimReviewItem` per impact claim with specificity flags,
  evidence-gap rationale, selectivity / adverse-impact omission tags,
  and a suggested follow-up question;
* AI-governance metadata on every output (prompt version, model
  version, confidence, NESTA evidence-strength tag) so the reviewer's
  output can flow through :mod:`impact_vision.impact.evidence_workflow`
  and the audit trail.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from impact_vision.impact.greenwashing import (
    GreenwashingScore,
    assess_greenwashing,
)
from impact_vision.impact.models import Company, ImpactClaim
from impact_vision.impact.verdict_engine import VerdictCard, build_verdict_card


SpecificityLabel = Literal["concrete", "mixed", "vague", "buzzword_only"]
ReviewerSeverity = Literal["info", "low", "medium", "high"]


class ClaimReviewItem(BaseModel):
    """Per-claim greenwashing review output."""

    claim_text: str
    specificity: SpecificityLabel
    severity: ReviewerSeverity
    evidence_gap: bool
    evidence_gap_rationale: str = ""
    selectivity_flag: bool = False
    adverse_omission_flag: bool = False
    suggested_followup: str = ""
    nesta_evidence_strength: int = Field(ge=1, le=5, default=1)
    confidence: float = Field(ge=0, le=1, default=0.5)


class GreenwashingReviewerOutput(BaseModel):
    """Composite greenwashing reviewer output for one company."""

    company_name: str
    reviewed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    overall: GreenwashingScore
    verdict_card: VerdictCard | None = None
    items: list[ClaimReviewItem] = Field(default_factory=list)
    governance: dict[str, Any] = Field(default_factory=dict)


_VAGUE_TOKENS = {
    "sustainable",
    "eco-friendly",
    "green",
    "responsible",
    "ethical",
    "purpose-driven",
    "impact-driven",
    "best-in-class",
    "world-class",
    "leading",
}

_BUZZWORDS_ONLY = _VAGUE_TOKENS | {"esg", "csr"}

_CONCRETE_NUMERIC_TOKENS = {
    "%",
    "tco2e",
    "kwh",
    "mwh",
    "usd",
    "eur",
    "kg",
    "tons",
    "tonnes",
    "households",
    "people",
    "beneficiaries",
    "students",
    "patients",
    "farmers",
    "ha",
    "litres",
    "gallons",
}


def _has_concrete_unit(lowered: str) -> bool:
    """Return True when the text contains an explicit unit token (word-aware)."""
    if "%" in lowered:
        return True
    tokens = set(re.findall(r"[a-z0-9]+", lowered))
    return any(token in _CONCRETE_NUMERIC_TOKENS for token in tokens)


def _classify_specificity(text: str) -> SpecificityLabel:
    lowered = text.lower()
    has_number = any(ch.isdigit() for ch in text)
    has_concrete_unit = _has_concrete_unit(lowered)
    has_vague = any(token in lowered for token in _VAGUE_TOKENS)
    only_buzz = (
        not has_number
        and not has_concrete_unit
        and any(token in lowered for token in _BUZZWORDS_ONLY)
        and len(lowered.split()) <= 6
    )
    if only_buzz:
        return "buzzword_only"
    if has_number and has_concrete_unit and not has_vague:
        return "concrete"
    if has_number or has_concrete_unit:
        return "mixed"
    return "vague"


def _severity(specificity: SpecificityLabel, evidence_gap: bool) -> ReviewerSeverity:
    if specificity == "buzzword_only":
        return "high"
    if specificity == "vague" and evidence_gap:
        return "high"
    if specificity == "vague":
        return "medium"
    if specificity == "mixed" and evidence_gap:
        return "medium"
    if evidence_gap:
        return "medium"
    return "low"


def _suggested_followup(
    claim: ImpactClaim,
    specificity: SpecificityLabel,
    evidence_gap: bool,
) -> str:
    if specificity == "buzzword_only":
        return (
            "Replace the buzzword phrasing with a measurable target: "
            "what numeric outcome, by when, for which population?"
        )
    if specificity == "vague" and evidence_gap:
        return (
            "Provide a quantified output and link to the IRIS+ metric "
            "and source document supporting the claim."
        )
    if evidence_gap:
        return "Attach the source document or system export that supports the figure."
    if claim.evidence_strength <= 2:
        return (
            "Move the evidence up the NESTA ladder: pre/post or DID, "
            "or third-party evaluation."
        )
    return ""


def review_company_claims(
    company: Company,
    claims: list[ImpactClaim],
    *,
    prompt_version: str = "greenwashing-reviewer-v3-2026",
    model_version: str = "deterministic-rules-v1",
    base_confidence: float = 0.65,
) -> GreenwashingReviewerOutput:
    """Run the per-claim reviewer over a company's claims."""
    overall = assess_greenwashing(company, [c.model_dump(mode="json") for c in claims])
    selectivity_flag = overall.selectivity >= 50
    adverse_flag = overall.adverse_omission >= 50

    items: list[ClaimReviewItem] = []
    for claim in claims:
        specificity = _classify_specificity(claim.text)
        evidence_gap = len(claim.mapped_metrics) == 0 or claim.evidence_strength <= 1
        rationale_parts: list[str] = []
        if not claim.mapped_metrics:
            rationale_parts.append("No IRIS+ metric mapped.")
        if not any(ch.isdigit() for ch in claim.text):
            rationale_parts.append("No quantitative figure in the claim text.")
        if claim.evidence_strength <= 1:
            rationale_parts.append("NESTA evidence level 1 (narrative only).")

        items.append(ClaimReviewItem(
            claim_text=claim.text,
            specificity=specificity,
            severity=_severity(specificity, evidence_gap),
            evidence_gap=evidence_gap,
            evidence_gap_rationale=" ".join(rationale_parts),
            selectivity_flag=selectivity_flag,
            adverse_omission_flag=adverse_flag,
            suggested_followup=_suggested_followup(claim, specificity, evidence_gap),
            nesta_evidence_strength=claim.evidence_strength,
            confidence=round(min(1.0, max(0.0, base_confidence + 0.05 * len(rationale_parts))), 2),
        ))

    governance = {
        "prompt_version": prompt_version,
        "model_version": model_version,
        "company": company.name,
        "claims_reviewed": len(items),
        "selectivity_threshold_hit": selectivity_flag,
        "adverse_omission_threshold_hit": adverse_flag,
    }

    return GreenwashingReviewerOutput(
        company_name=company.name,
        overall=overall,
        verdict_card=build_verdict_card(company, overall),
        items=items,
        governance=governance,
    )


# --------------------------------------------------------------------------- 2.0
# Greenwashing 2.0 (roadmap v8 W1.9): judge the claims, not the gaps.
#   claim risk = 100 × specificity × evidence × materiality
# The company score is the mean of its three riskiest claims, so one sound
# claim can't hide a misleading one, and missing data alone scores nothing.
_SPECIFICITY_W = {"concrete": 0.2, "mixed": 0.5, "vague": 0.8, "buzzword_only": 1.0}
_EVIDENCE_W = {1: 1.0, 2: 0.7, 3: 0.4, 4: 0.25, 5: 0.15}
# Generic environmental claims are what the EU ECGT Directive bans without
# recognised excellence or proof, so they weigh most.
_GENERIC_ENV = ("eco-friendly", "eco friendly", "green", "sustainable", "carbon neutral", "carbon-neutral",
                "net zero", "net-zero", "climate positive", "climate-positive", "environmentally friendly",
                "planet-positive", "nature positive", "100% renewable", "zero waste", "zero-waste")


def claim_risk(claim: ImpactClaim) -> dict[str, Any]:
    """One claim's greenwashing risk (0–100) with the reasons."""
    specificity = _classify_specificity(claim.text)
    signals = set((claim.entities or {}).get("evidence", []) or [])
    verified = bool(signals & {"third_party_verified", "audited", "certified"})
    evidence = _EVIDENCE_W.get(int(claim.evidence_strength or 1), 1.0) * (0.7 if verified else 1.0)
    lowered = claim.text.lower()
    generic = [g for g in _GENERIC_ENV if re.search(r"(?<![\w-])" + re.escape(g) + r"(?![\w-])", lowered)]
    if generic and specificity == "mixed" and not re.search(r"\d[\d,.]*\s*(?!%)[a-z]", lowered):
        specificity = "vague"  # "100% green" — a percentage on an adjective is not a measurement
    materiality = 1.0 if generic else 0.8 if claim.category in {"outcome", "output"} else 0.6
    risk = round(100 * _SPECIFICITY_W[specificity] * evidence * materiality)
    reasons = [f"{specificity.replace('_', ' ')} wording", f"NESTA {claim.evidence_strength}"
               + (", verified" if verified else "")]
    if generic:
        reasons.append("generic environmental claim (" + ", ".join(generic[:2]) + ")")
    return {"text": claim.text, "risk": risk, "specificity": specificity, "evidence_level": claim.evidence_strength,
            "verified": verified, "generic_environmental": bool(generic), "reasons": reasons,
            "followup": _suggested_followup(claim, specificity, not claim.mapped_metrics or claim.evidence_strength <= 1)
            or ("Name the recognised standard or proof behind the claim (EU ECGT)." if generic else "")}


def review_claims_v2(claims: list[ImpactClaim], *, text: str = "", top: int = 3) -> dict[str, Any]:
    """Company-level greenwashing 2.0: the riskiest claims drive the score.

    Sentences in *text* that make a generic environmental claim are reviewed
    too: the claim extractor looks for quantified statements and misses
    exactly the unquantified ones that matter here.
    """
    claims = list(claims)
    seen = {c.text.strip().lower()[:60] for c in claims}
    for sentence in re.split(r"(?<=[.!?。])\s+|\n+", text or ""):
        sentence = sentence.strip(" -•*\t")
        low = sentence.lower()
        if len(sentence) < 12 or low[:60] in seen or not any(
                re.search(r"(?<![\w-])" + re.escape(g) + r"(?![\w-])", low) for g in _GENERIC_ENV):
            continue
        seen.add(low[:60])
        claims.append(ImpactClaim(text=sentence, category="intent", evidence_strength=1))
    rows = sorted((claim_risk(c) for c in claims if c.text.strip()), key=lambda r: -r["risk"])
    if not rows:
        return {"score": None, "claims": [], "flagged": 0, "method": "greenwashing-2.0"}
    worst = rows[:top]
    score = round(sum(r["risk"] for r in worst) / len(worst))
    return {"score": score, "claims": rows[:8], "flagged": sum(1 for r in rows if r["risk"] >= 60),
            "reviewed": len(rows), "method": "greenwashing-2.0"}


__all__ = [
    "claim_risk",
    "review_claims_v2",
    "ClaimReviewItem",
    "GreenwashingReviewerOutput",
    "ReviewerSeverity",
    "SpecificityLabel",
    "review_company_claims",
]
