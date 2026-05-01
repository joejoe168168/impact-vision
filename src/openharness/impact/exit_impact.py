"""Exit impact assessment workflow (v3 Track 5.6, OPIM Principle 8).

The Operating Principles for Impact Management Principle 8 requires that
investors "review, document, and improve decisions and processes based
on the achievement of impact and lessons learned." For impact funds at
exit, this translates to four concrete questions:

1. Does the impact persist after the fund's exit?
2. What durability risks (commercial, governance, regulatory) threaten
   the impact?
3. What post-exit follow-up actions has the GP committed to, and over
   what period?
4. How strong is the residual evidence (IRIS+ metrics, beneficiary
   feedback, contribution analysis)?

This module provides Pydantic models for each of those questions plus a
deterministic ``score_exit_impact()`` function that produces a 0-100
residual-impact score.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field

from openharness.impact.models import Company, ImpactClaim


RiskCategory = Literal[
    "commercial",
    "governance",
    "regulatory",
    "stakeholder",
    "macro",
    "supply_chain",
    "climate",
]
DurabilityLikelihood = Literal["unlikely", "possible", "likely", "very_likely"]
DurabilitySeverity = Literal["minor", "moderate", "major", "severe"]
FollowUpStatus = Literal["planned", "in_progress", "completed", "cancelled"]


_LIKELIHOOD_WEIGHT: dict[DurabilityLikelihood, int] = {
    "unlikely": 1,
    "possible": 2,
    "likely": 3,
    "very_likely": 4,
}
_SEVERITY_WEIGHT: dict[DurabilitySeverity, int] = {
    "minor": 1,
    "moderate": 2,
    "major": 3,
    "severe": 4,
}


class ExitDurabilityRisk(BaseModel):
    """One risk to post-exit impact persistence."""

    risk_id: str
    category: RiskCategory
    description: str
    likelihood: DurabilityLikelihood = "possible"
    severity: DurabilitySeverity = "moderate"
    mitigation: str = ""
    mitigation_owner: str = ""
    accepted: bool = False

    @property
    def score(self) -> int:
        """0-16 product of likelihood and severity weights."""
        return _LIKELIHOOD_WEIGHT[self.likelihood] * _SEVERITY_WEIGHT[self.severity]


class PostExitFollowUp(BaseModel):
    """Scheduled post-exit follow-up checkpoint."""

    follow_up_id: str
    description: str
    period: str = Field(description="Reporting period for the follow-up, e.g. 12m, 24m, 36m")
    metric_ids: list[str] = Field(default_factory=list)
    owner: str = ""
    status: FollowUpStatus = "planned"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExitImpactPlan(BaseModel):
    """Full exit-impact plan rolled up around one company."""

    company: Company
    exit_date: str = ""
    durability_risks: list[ExitDurabilityRisk] = Field(default_factory=list)
    post_exit_follow_ups: list[PostExitFollowUp] = Field(default_factory=list)
    impact_claims: list[ImpactClaim] = Field(default_factory=list)
    contribution_summary: str = ""
    counterfactual_summary: str = ""
    opim_principle: str = "OPIM Principle 8"
    notes: str = ""


class ExitImpactScore(BaseModel):
    """Deterministic 0-100 residual-impact score."""

    company_name: str
    residual_score: int = Field(ge=0, le=100)
    band: Literal["weak", "moderate", "strong"]
    risk_score: int = Field(ge=0, le=100)
    follow_up_score: int = Field(ge=0, le=100)
    evidence_score: int = Field(ge=0, le=100)
    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def score_exit_impact(plan: ExitImpactPlan) -> ExitImpactScore:
    """Compute a residual-impact score for an exit plan."""
    flags: list[str] = []
    recs: list[str] = []

    if plan.durability_risks:
        weighted = sum(
            risk.score * (1 if not risk.accepted else 0.5)
            for risk in plan.durability_risks
        )
        max_per = max(_LIKELIHOOD_WEIGHT.values()) * max(_SEVERITY_WEIGHT.values())
        risk_raw = 100 - 100 * weighted / (len(plan.durability_risks) * max_per)
        risk_score = max(0, min(100, int(round(risk_raw))))
        unmitigated = [r for r in plan.durability_risks if not r.mitigation]
        if unmitigated:
            flags.append("unmitigated_risks")
            recs.append(
                f"Document mitigations for {len(unmitigated)} unmitigated durability risk(s)."
            )
    else:
        risk_score = 60
        flags.append("no_risks_documented")
        recs.append("Document at least three durability risks (commercial, governance, regulatory).")

    if plan.post_exit_follow_ups:
        with_owner = sum(1 for f in plan.post_exit_follow_ups if f.owner)
        completed = sum(1 for f in plan.post_exit_follow_ups if f.status == "completed")
        coverage = with_owner / len(plan.post_exit_follow_ups)
        completion = completed / len(plan.post_exit_follow_ups)
        follow_up_score = int(round(100 * (0.5 * coverage + 0.5 * completion)))
        if coverage < 1.0:
            flags.append("follow_up_owner_missing")
            recs.append("Assign an owner to every post-exit follow-up.")
    else:
        follow_up_score = 30
        flags.append("no_follow_ups_planned")
        recs.append(
            "Schedule at least 12-month and 24-month follow-up checkpoints with metric IDs."
        )

    if plan.impact_claims:
        evidence_levels = [claim.evidence_strength for claim in plan.impact_claims]
        if evidence_levels:
            evidence_score = int(round(100 * sum(evidence_levels) / (5 * len(evidence_levels))))
        else:
            evidence_score = 30
        weak_claims = [c for c in plan.impact_claims if c.evidence_strength <= 2]
        if weak_claims:
            flags.append("weak_residual_evidence")
            recs.append(
                f"Strengthen residual evidence for {len(weak_claims)} claim(s) "
                "(target NESTA level 3+)."
            )
    else:
        evidence_score = 30
        flags.append("no_residual_evidence")
        recs.append("Attach residual impact claims with NESTA evidence strength.")

    residual = int(round(0.4 * risk_score + 0.3 * follow_up_score + 0.3 * evidence_score))
    band: Literal["weak", "moderate", "strong"] = (
        "strong" if residual >= 75 else "moderate" if residual >= 45 else "weak"
    )
    if band == "weak":
        recs.append(
            "Consider postponing exit reporting until residual-impact score reaches 'moderate' (>=45)."
        )
    return ExitImpactScore(
        company_name=plan.company.name,
        residual_score=residual,
        band=band,
        risk_score=risk_score,
        follow_up_score=follow_up_score,
        evidence_score=evidence_score,
        flags=flags,
        recommendations=recs,
    )


def build_exit_plan(
    *,
    company: Company,
    exit_date: str,
    risks: Iterable[ExitDurabilityRisk] | None = None,
    follow_ups: Iterable[PostExitFollowUp] | None = None,
    claims: Iterable[ImpactClaim] | None = None,
    contribution_summary: str = "",
    counterfactual_summary: str = "",
    notes: str = "",
) -> ExitImpactPlan:
    """Convenience constructor for an :class:`ExitImpactPlan`."""
    return ExitImpactPlan(
        company=company,
        exit_date=exit_date,
        durability_risks=list(risks or []),
        post_exit_follow_ups=list(follow_ups or []),
        impact_claims=list(claims or []),
        contribution_summary=contribution_summary,
        counterfactual_summary=counterfactual_summary,
        notes=notes,
    )


__all__ = [
    "DurabilityLikelihood",
    "DurabilitySeverity",
    "ExitDurabilityRisk",
    "ExitImpactPlan",
    "ExitImpactScore",
    "FollowUpStatus",
    "PostExitFollowUp",
    "RiskCategory",
    "build_exit_plan",
    "score_exit_impact",
]
