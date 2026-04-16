"""Greenwashing / impact-washing detection engine.

Produces a composite greenwashing risk score (0-100) from 5 sub-scores:
1. Claim-Metric Gap: do SDG/theme claims have supporting metrics?
2. Adverse Omission: are negative-impact metrics missing for the sector?
3. Specificity: are claims concrete or vague?
4. Selectivity: is reporting balanced or cherry-picked?
5. Verification: is there evidence of measurement systems and auditing?
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.models import Company


_VAGUE_VERBS = {
    "aim", "aspire", "believe", "commit", "contribute", "dedicated", "endeavor",
    "expect", "hope", "intend", "plan", "pledge", "promise", "seek", "strive",
    "support", "try", "work toward", "working toward",
}

_CONCRETE_VERBS = {
    "achieved", "completed", "delivered", "deployed", "doubled", "eliminated",
    "generated", "grew", "halved", "implemented", "installed", "launched",
    "measured", "produced", "reached", "reduced", "saved", "served", "trained",
    "tripled", "verified",
}

_BUZZWORDS = {
    "sustainable", "sustainability", "esg", "green", "eco-friendly", "responsible",
    "ethical", "conscious", "purpose-driven", "impact-driven", "net-zero",
    "carbon-neutral", "climate-positive", "circular", "regenerative",
}

_ADVERSE_METRICS_BY_SECTOR: dict[str, list[str]] = {
    "fintech": ["PI4060", "OI1571"],
    "financial": ["PI4060", "OI1571"],
    "energy": ["OI4112", "OI9803"],
    "agriculture": ["OI4112", "PI3468"],
    "healthcare": ["PI4060"],
    "technology": ["PI4060"],
    "default": ["OI4112", "PI4060"],
}

_VERIFICATION_KEYWORDS = {
    "audit", "audited", "verified", "third-party", "third party",
    "assurance", "certification", "certified", "independently verified",
    "external review", "iso 14001", "b corp", "fair trade",
}

_MEASUREMENT_KEYWORDS = {
    "baseline", "benchmark", "data collection", "indicator", "kpi",
    "methodology", "monitoring", "reporting framework", "survey",
    "target", "tracking", "year-over-year",
}


class GreenwashingScore(BaseModel):
    """Composite greenwashing risk assessment."""

    overall_score: float = Field(ge=0, le=100, description="0=clean, 100=high greenwashing risk")
    classification: Literal[
        "Genuine Impact Leader",
        "Substantive with Gaps",
        "Moderate Risk",
        "High Risk",
        "Probable Greenwashing",
    ]

    claim_metric_gap: float = Field(ge=0, le=100, description="Unsubstantiated claims score")
    adverse_omission: float = Field(ge=0, le=100, description="Missing negative-impact metrics")
    specificity: float = Field(ge=0, le=100, description="Vagueness of language")
    selectivity: float = Field(ge=0, le=100, description="Cherry-picked positive reporting")
    verification: float = Field(ge=0, le=100, description="Lack of verification/audit signals")

    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def assess_greenwashing(
    company: Company,
    claims: list[dict[str, Any]] | None = None,
) -> GreenwashingScore:
    """Run greenwashing risk assessment for a company."""
    text = f"{company.description} {' '.join(company.impact_themes)}".lower()
    metrics = set(company.reported_metrics.keys())

    gap_score = _score_claim_metric_gap(company, metrics)
    omission_score = _score_adverse_omission(company, metrics)
    specificity_score = _score_specificity(text, claims)
    selectivity_score = _score_selectivity(company, metrics)
    verification_score = _score_verification(text, metrics)

    weights = {"gap": 0.30, "omission": 0.20, "specificity": 0.20, "selectivity": 0.15, "verification": 0.15}
    overall = (
        gap_score * weights["gap"]
        + omission_score * weights["omission"]
        + specificity_score * weights["specificity"]
        + selectivity_score * weights["selectivity"]
        + verification_score * weights["verification"]
    )
    overall = round(min(100, max(0, overall)), 1)

    classification = _classify(overall)
    flags = _generate_flags(gap_score, omission_score, specificity_score, selectivity_score, verification_score)
    recommendations = _generate_recommendations(gap_score, omission_score, specificity_score, selectivity_score, verification_score, company)

    return GreenwashingScore(
        overall_score=overall,
        classification=classification,
        claim_metric_gap=round(gap_score, 1),
        adverse_omission=round(omission_score, 1),
        specificity=round(specificity_score, 1),
        selectivity=round(selectivity_score, 1),
        verification=round(verification_score, 1),
        flags=flags,
        recommendations=recommendations,
    )


def _score_claim_metric_gap(company: Company, metrics: set[str]) -> float:
    """Score: do SDG claims and themes have supporting metrics?"""
    claims_count = len(company.sdg_claims) + len(company.impact_themes)
    if claims_count == 0:
        return 20.0

    if not metrics:
        return min(100, 40 + claims_count * 8)

    supported = 0
    for theme in company.impact_themes:
        theme_lower = theme.lower()
        if any(theme_lower in str(v).lower() for v in company.reported_metrics.values()):
            supported += 1

    support_ratio = (supported + len(metrics)) / max(1, claims_count * 3)
    return max(0, 80 - support_ratio * 100)


def _score_adverse_omission(company: Company, metrics: set[str]) -> float:
    """Score: are sector-appropriate negative-impact metrics missing?"""
    sector = company.sector.lower()
    required = _ADVERSE_METRICS_BY_SECTOR.get(sector, _ADVERSE_METRICS_BY_SECTOR["default"])

    if not required:
        return 20.0

    missing = [m for m in required if m not in metrics]
    return min(100, len(missing) / len(required) * 80 + 10)


def _score_specificity(text: str, claims: list[dict[str, Any]] | None) -> float:
    """Score: are claims vague or concrete?"""
    words = set(re.findall(r"\b\w+\b", text.lower()))

    vague_count = len(words & _VAGUE_VERBS)
    concrete_count = len(words & _CONCRETE_VERBS)
    buzzword_count = len(words & _BUZZWORDS)

    has_numbers = bool(re.search(r"\b\d+[%,.\d]*\b", text))

    score = 50.0
    score += vague_count * 5
    score -= concrete_count * 8
    score += buzzword_count * 4
    if has_numbers:
        score -= 15

    if claims:
        vague_claims = sum(1 for c in claims if c.get("category") in ("intent", "activity"))
        outcome_claims = sum(1 for c in claims if c.get("category") in ("outcome", "output"))
        if vague_claims > outcome_claims:
            score += 15

    return max(0, min(100, score))


def _score_selectivity(company: Company, metrics: set[str]) -> float:
    """Score: is reporting balanced or only positive metrics?"""
    if not metrics:
        return 60.0

    has_risk_metrics = any("risk" in str(v).lower() or mid.startswith("OI") for mid, v in company.reported_metrics.items())
    has_negative_metrics = any("OD" in mid or "negative" in str(v).lower() for mid, v in company.reported_metrics.items())
    total = len(metrics)

    score = 50.0
    if not has_risk_metrics:
        score += 20
    if not has_negative_metrics:
        score += 15
    if total < 5:
        score += 10

    return max(0, min(100, score))


def _score_verification(text: str, metrics: set[str]) -> float:
    """Score: does the company show verification/audit signals?"""
    text_lower = text.lower()
    verification_hits = sum(1 for kw in _VERIFICATION_KEYWORDS if kw in text_lower)
    measurement_hits = sum(1 for kw in _MEASUREMENT_KEYWORDS if kw in text_lower)

    score = 70.0
    score -= verification_hits * 12
    score -= measurement_hits * 8
    score -= len(metrics) * 2

    return max(0, min(100, score))


def _classify(score: float) -> str:
    if score <= 20:
        return "Genuine Impact Leader"
    if score <= 40:
        return "Substantive with Gaps"
    if score <= 60:
        return "Moderate Risk"
    if score <= 80:
        return "High Risk"
    return "Probable Greenwashing"


def _generate_flags(gap: float, omission: float, specificity: float, selectivity: float, verification: float) -> list[str]:
    flags = []
    if gap > 60:
        flags.append("HIGH_CLAIM_METRIC_GAP: SDG/theme claims lack supporting metric evidence")
    if omission > 60:
        flags.append("ADVERSE_OMISSION: Missing negative-impact metrics for sector")
    if specificity > 60:
        flags.append("VAGUE_LANGUAGE: Claims use aspirational language without concrete evidence")
    if selectivity > 60:
        flags.append("SELECTIVE_REPORTING: Reporting appears to cherry-pick positive metrics")
    if verification > 60:
        flags.append("NO_VERIFICATION: No evidence of third-party verification or auditing")
    return flags


def _generate_recommendations(
    gap: float, omission: float, specificity: float, selectivity: float, verification: float,
    company: Company,
) -> list[str]:
    recs = []
    if gap > 40:
        recs.append("Map each SDG claim to at least one IRIS+ metric with reported data")
    if omission > 40:
        sector = company.sector or "general"
        recs.append(f"Report adverse-impact metrics appropriate for {sector} sector (e.g., GHG emissions, client protection)")
    if specificity > 40:
        recs.append("Replace aspirational language with concrete, quantified outcome statements")
    if selectivity > 40:
        recs.append("Include risk-oriented and negative-impact metrics alongside positive outcomes")
    if verification > 40:
        recs.append("Obtain third-party verification or implement a recognized measurement framework")
    return recs
