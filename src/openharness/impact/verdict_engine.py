"""Fund-manager verdict cards for greenwashing review output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.greenwashing import GreenwashingScore
from openharness.impact.models import Company


GreenwashingVerdict = Literal["pass", "caution", "fail"]


class VerdictCard(BaseModel):
    """One-screen impact credibility verdict for IC gate decisions."""

    verdict: GreenwashingVerdict
    risk_score: int = Field(ge=0, le=100)
    summary: str
    top_3_findings: list[str] = Field(default_factory=list)
    top_3_strengths: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    override_rationale: str | None = None


def classify_greenwashing(score: float) -> GreenwashingVerdict:
    if score < 30:
        return "pass"
    if score <= 70:
        return "caution"
    return "fail"


def _subscores(score: GreenwashingScore) -> list[tuple[str, float]]:
    return [
        ("Claim-metric gap", score.claim_metric_gap),
        ("Adverse-impact omission", score.adverse_omission),
        ("Specificity", score.specificity),
        ("Selectivity", score.selectivity),
        ("Verification", score.verification),
    ]


def _findings(score: GreenwashingScore) -> list[str]:
    ranked = sorted(_subscores(score), key=lambda item: item[1], reverse=True)
    findings = [f"{name}: {value:.0f}/100 risk" for name, value in ranked if value >= 45]
    if score.flags:
        findings.extend(score.flags)
    return findings[:3] or ["No material greenwashing concern crossed the review threshold."]


def _strengths(company: Company, score: GreenwashingScore) -> list[str]:
    strengths: list[str] = []
    metric_count = len(company.reported_metrics)
    if metric_count:
        strengths.append(f"{metric_count} reported IRIS+ metric(s) available for review.")
    for name, value in sorted(_subscores(score), key=lambda item: item[1]):
        if value <= 35:
            strengths.append(f"{name}: low risk signal ({value:.0f}/100).")
    return strengths[:3] or ["No strong positive evidence signal was identified."]


def _next_steps(verdict: GreenwashingVerdict, score: GreenwashingScore) -> list[str]:
    if verdict == "pass":
        return [
            "Proceed to full due diligence with routine evidence checks.",
            "Keep source documents with the IC memo proof appendix.",
        ]
    if verdict == "caution":
        steps = score.recommendations[:2]
        steps.append("Resolve evidence gaps before final IC approval.")
        return steps
    steps = score.recommendations[:2]
    steps.append("Block IC approval until claims are quantified, sourced, and reviewed.")
    return steps


def build_verdict_card(
    company: Company,
    score: GreenwashingScore,
    *,
    override_rationale: str | None = None,
) -> VerdictCard:
    verdict = classify_greenwashing(score.overall_score)
    summary = (
        f"{company.name or 'Company'} receives a {verdict.upper()} impact credibility verdict "
        f"with greenwashing risk {score.overall_score:.1f}/100 ({score.classification})."
    )
    return VerdictCard(
        verdict=verdict,
        risk_score=int(round(score.overall_score)),
        summary=summary,
        top_3_findings=_findings(score),
        top_3_strengths=_strengths(company, score),
        next_steps=_next_steps(verdict, score),
        override_rationale=override_rationale,
    )


__all__ = [
    "GreenwashingVerdict",
    "VerdictCard",
    "build_verdict_card",
    "classify_greenwashing",
]
