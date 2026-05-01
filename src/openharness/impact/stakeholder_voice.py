"""Stakeholder voice as verified evidence (v3 Track 4).

Closes the v3 gap "beneficiary voice is *evidence*, not just intelligence."
The module provides:

* **Lean Data survey templates** — 60 Decibels-style 15-minute surveys
  with sector overlays.
* **GDPR/PDPA consent records** — per-respondent consent capture with
  lawful basis, retention, version pinning, and revocation.
* **Beneficiary feedback quality scoring** — completion rate, response
  depth, time on survey, demographic coverage.
* **Feedback-as-evidence linking** — emits :class:`EvidenceLink` rows
  that connect feedback themes / quotes to specific
  :class:`ImpactClaim` IDs, so the evidence graph rendered for
  assurance carries verified stakeholder voice.

The functions here are deterministic and offline-only; they don't call
any LLM or external service.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field

from openharness.impact.evidence_graph import (
    EvidenceGraph,
    EvidenceLink,
    EvidenceNode,
)
from openharness.impact.models import (
    BeneficiaryFeedback,
    ImpactClaim,
)


LawfulBasis = Literal[
    "consent",
    "contract",
    "legal_obligation",
    "vital_interests",
    "public_task",
    "legitimate_interests",
]
SurveyChannel = Literal["sms", "phone", "in_person", "web", "ivr", "kobo"]
QuestionType = Literal["likert_5", "nps", "yes_no", "multiselect", "open_text", "demographic"]


# ---------------------------------------------------------------------------
# Lean Data templates
# ---------------------------------------------------------------------------


class LeanDataQuestion(BaseModel):
    """One standardized question in a Lean Data survey."""

    question_id: str
    prompt: str
    type: QuestionType
    impact_dimension: Literal["who", "what", "how_much", "contribution", "risk"] = "what"
    options: list[str] = Field(default_factory=list)
    required: bool = True


class LeanDataTemplate(BaseModel):
    """A 60-Decibels-style standardized survey template."""

    template_id: str
    sector: str
    title: str
    description: str = ""
    target_minutes: int = Field(default=15, ge=1, le=60)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    questions: list[LeanDataQuestion] = Field(default_factory=list)
    version: str = "lean-data-2026"


def _core_lean_data_questions() -> list[LeanDataQuestion]:
    """Return the canonical 60 Decibels Lean Data core question set."""
    return [
        LeanDataQuestion(
            question_id="ld_q1_first_access",
            prompt="Before using this product/service, did you have access to a similar option?",
            type="yes_no",
            impact_dimension="contribution",
        ),
        LeanDataQuestion(
            question_id="ld_q2_alternative",
            prompt="What would you have used instead if this product/service did not exist?",
            type="open_text",
            impact_dimension="contribution",
        ),
        LeanDataQuestion(
            question_id="ld_q3_quality_of_life",
            prompt="Has your quality of life changed as a result of this product/service?",
            type="likert_5",
            impact_dimension="how_much",
            options=["Got worse", "Slightly worse", "No change", "Slightly improved", "Greatly improved"],
        ),
        LeanDataQuestion(
            question_id="ld_q4_primary_change",
            prompt="What is the most important change you have experienced?",
            type="open_text",
            impact_dimension="how_much",
        ),
        LeanDataQuestion(
            question_id="ld_q5_recommendation",
            prompt="On a scale of 0-10, how likely are you to recommend this product/service to a friend or family member?",
            type="nps",
            impact_dimension="who",
        ),
        LeanDataQuestion(
            question_id="ld_q6_challenges",
            prompt="What challenges have you experienced with this product/service?",
            type="multiselect",
            impact_dimension="risk",
            options=["Cost", "Reliability", "Quality", "Customer service", "Other", "None"],
        ),
        LeanDataQuestion(
            question_id="ld_q7_inclusion",
            prompt="Would you describe yourself as living below the local poverty line?",
            type="yes_no",
            impact_dimension="who",
        ),
        LeanDataQuestion(
            question_id="ld_q8_demographic_gender",
            prompt="What is your gender?",
            type="demographic",
            impact_dimension="who",
            options=["Female", "Male", "Non-binary", "Prefer not to say"],
            required=False,
        ),
    ]


_SECTOR_OVERLAYS: dict[str, list[LeanDataQuestion]] = {
    "energy": [
        LeanDataQuestion(
            question_id="ld_energy_q1_hours",
            prompt="How many additional hours of light/electricity per day has this product enabled?",
            type="open_text",
            impact_dimension="how_much",
        ),
        LeanDataQuestion(
            question_id="ld_energy_q2_kerosene",
            prompt="Has this product replaced kerosene, candles, diesel, or grid-firewood use?",
            type="yes_no",
            impact_dimension="how_much",
        ),
    ],
    "fintech": [
        LeanDataQuestion(
            question_id="ld_fin_q1_repeat",
            prompt="Have you successfully repaid any prior loan or used any prior savings product with this provider?",
            type="yes_no",
            impact_dimension="risk",
        ),
        LeanDataQuestion(
            question_id="ld_fin_q2_overindebted",
            prompt="In the past 12 months, did you borrow money from another source to repay this product?",
            type="yes_no",
            impact_dimension="risk",
        ),
    ],
    "healthcare": [
        LeanDataQuestion(
            question_id="ld_health_q1_visit_freq",
            prompt="In the past 6 months, how many times have you used this health service?",
            type="open_text",
            impact_dimension="how_much",
        ),
    ],
    "agriculture": [
        LeanDataQuestion(
            question_id="ld_ag_q1_yield",
            prompt="Has your yield (kg/acre or equivalent) changed since you started using this product/service?",
            type="likert_5",
            impact_dimension="how_much",
        ),
    ],
    "education": [
        LeanDataQuestion(
            question_id="ld_edu_q1_attendance",
            prompt="Has the learner's attendance changed since using this product/service?",
            type="likert_5",
            impact_dimension="how_much",
        ),
    ],
}


def build_lean_data_survey(
    *,
    sector: str,
    template_id: str | None = None,
    languages: Iterable[str] | None = None,
    target_minutes: int = 15,
    title: str | None = None,
) -> LeanDataTemplate:
    """Build a Lean Data template for a sector with the canonical core."""
    sector_key = sector.strip().lower().replace(" ", "_")
    overlay = _SECTOR_OVERLAYS.get(sector_key, [])
    questions = _core_lean_data_questions() + overlay
    return LeanDataTemplate(
        template_id=template_id or f"lean-data-{sector_key or 'generic'}",
        sector=sector_key or "generic",
        title=title or f"Lean Data Survey — {sector_key or 'generic'}",
        description="60 Decibels-style 15-minute Lean Data standardized survey.",
        target_minutes=target_minutes,
        languages=list(languages or ["en"]),
        questions=questions,
    )


# ---------------------------------------------------------------------------
# Consent management (GDPR / PDPA)
# ---------------------------------------------------------------------------


class ConsentRecord(BaseModel):
    """Per-respondent consent capture compliant with GDPR / PDPA."""

    consent_id: str
    respondent_id: str
    survey_id: str
    consent_text_version: str
    lawful_basis: LawfulBasis = "consent"
    retention_period_days: int = Field(default=730, ge=1)
    granted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    revoked_at: str = ""
    purpose: str = "Impact evaluation and reporting"
    data_categories: list[str] = Field(default_factory=lambda: ["survey_response"])
    transfer_jurisdictions: list[str] = Field(default_factory=list)
    notes: str = ""

    @property
    def is_active(self) -> bool:
        return not self.revoked_at


def revoke_consent(record: ConsentRecord, *, at: str | None = None) -> ConsentRecord:
    """Return a copy of ``record`` with ``revoked_at`` set."""
    return record.model_copy(update={
        "revoked_at": at or datetime.now(timezone.utc).isoformat(),
    })


def filter_active_responses(
    consents: dict[str, ConsentRecord],
    responses: dict[str, dict],
) -> dict[str, dict]:
    """Drop responses whose respondent has revoked consent."""
    return {
        respondent_id: response
        for respondent_id, response in responses.items()
        if respondent_id in consents and consents[respondent_id].is_active
    }


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------


class BeneficiaryFeedbackQuality(BaseModel):
    """Quality score for one beneficiary feedback dataset."""

    completion_rate_pct: float = Field(ge=0, le=100)
    response_depth_score: int = Field(ge=0, le=100)
    median_time_on_survey_seconds: float = Field(ge=0)
    demographic_coverage_pct: float = Field(ge=0, le=100)
    consent_active_pct: float = Field(ge=0, le=100, default=100.0)
    overall_score: int = Field(ge=0, le=100)
    quality_band: Literal["low", "moderate", "high"]
    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def score_feedback_quality(
    *,
    completed_responses: int,
    invited_responses: int,
    response_depth: dict[str, int] | None = None,
    response_durations_seconds: list[float] | None = None,
    demographic_segments_present: int = 0,
    demographic_segments_target: int = 4,
    active_consents: int | None = None,
) -> BeneficiaryFeedbackQuality:
    """Score a feedback dataset across the four v3 quality dimensions."""
    flags: list[str] = []
    recs: list[str] = []
    completed = max(0, completed_responses)
    invited = max(0, invited_responses)
    completion_raw = (
        100.0 * completed / invited
        if invited > 0
        else 0.0
    )
    completion = min(100.0, completion_raw)
    if completion_raw > 100:
        flags.append("completion_exceeds_invites")
        recs.append("Reconcile survey counts; completed responses exceed invitations.")
    if completion < 60:
        flags.append("low_completion_rate")
        recs.append("Push the completion rate above 60% before LP use; reissue invitations.")

    response_depth = response_depth or {}
    if response_depth:
        depth_total = sum(response_depth.values())
        depth_count = max(1, len(response_depth))
        depth_score = min(100, int(depth_total * 100 / max(1, 5 * depth_count)))
    else:
        depth_score = 30
        flags.append("response_depth_unknown")
    if depth_score < 50:
        flags.append("shallow_responses")
        recs.append("Add open-text follow-ups; track median word counts to push depth above 50.")

    durations = sorted(response_durations_seconds or [])
    if durations:
        midpoint = durations[len(durations) // 2]
    else:
        midpoint = 0.0
        flags.append("survey_duration_unknown")
    if 0 < midpoint < 120:
        flags.append("survey_too_short")
        recs.append("Median completion under 2 minutes is too short for Lean Data depth.")
    if midpoint > 60 * 25:
        flags.append("survey_too_long")
        recs.append("Surveys over 25 minutes routinely lose >40% of respondents.")

    coverage_raw = (
        100.0 * max(0, demographic_segments_present) / demographic_segments_target
        if demographic_segments_target > 0
        else 0.0
    )
    coverage = min(100.0, coverage_raw)
    if coverage < 50:
        flags.append("weak_demographic_coverage")
        recs.append("Cover at least 50% of target demographic segments to support disaggregation.")

    consent_raw = (
        100.0 * max(0, active_consents) / completed
        if active_consents is not None and completed > 0
        else 100.0
    )
    consent_pct = min(100.0, consent_raw)
    if consent_raw > 100:
        flags.append("consent_count_exceeds_completed")
        recs.append("Reconcile consent records; active consents exceed completed responses.")
    if consent_pct < 95:
        flags.append("consent_gap")
        recs.append("Missing consents must be re-collected before responses are used as evidence.")

    weighted = (
        0.30 * completion
        + 0.25 * depth_score
        + 0.15 * (100.0 if midpoint == 0 else min(100.0, max(0.0, 100 - abs(midpoint - 600) / 6)))
        + 0.20 * coverage
        + 0.10 * consent_pct
    )
    overall = max(0, min(100, int(round(weighted))))
    band: Literal["low", "moderate", "high"] = (
        "high" if overall >= 80 else "moderate" if overall >= 50 else "low"
    )
    return BeneficiaryFeedbackQuality(
        completion_rate_pct=round(completion, 2),
        response_depth_score=depth_score,
        median_time_on_survey_seconds=round(midpoint, 1),
        demographic_coverage_pct=round(coverage, 2),
        consent_active_pct=round(consent_pct, 2),
        overall_score=overall,
        quality_band=band,
        flags=flags,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Feedback as evidence
# ---------------------------------------------------------------------------


class FeedbackEvidenceLink(BaseModel):
    """One link from feedback (theme/quote) back to an impact claim."""

    feedback_node_id: str
    claim_node_id: str
    rationale: str
    confidence: float = Field(ge=0, le=1, default=0.5)


def _feedback_node_id(theme: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in theme).strip("-") or "theme"
    digest = hashlib.sha1(theme.encode("utf-8")).hexdigest()[:8]
    return f"feedback:{cleaned}-{digest}"


def link_feedback_to_claims(
    feedback: BeneficiaryFeedback,
    claims: list[ImpactClaim],
    *,
    existing_graph: EvidenceGraph | None = None,
    base_confidence: float = 0.55,
) -> EvidenceGraph:
    """Build (or extend) an :class:`EvidenceGraph` linking feedback to claims.

    Each theme and challenge becomes a feedback node; each link is a
    "supported_by" relationship from the matching claim node to the
    feedback node, weighted by simple keyword overlap so the lineage is
    explainable rather than magical.
    """
    nodes: dict[str, EvidenceNode] = {}
    links: list[EvidenceLink] = []
    if existing_graph is not None:
        for node in existing_graph.nodes:
            nodes[node.id] = node
        links.extend(existing_graph.links)

    quotes_by_theme: dict[str, list[str]] = {}
    for quote in feedback.quotes:
        words = {w.lower() for w in quote.split() if len(w) > 3}
        for theme in feedback.themes:
            if theme.lower() in quote.lower() or any(t in words for t in theme.lower().split()):
                quotes_by_theme.setdefault(theme, []).append(quote)

    for theme in feedback.themes + feedback.challenges:
        node_id = _feedback_node_id(theme)
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                id=node_id,
                type="evidence",
                label=theme[:120],
                data={
                    "kind": "beneficiary_feedback_theme",
                    "theme": theme,
                    "sample_size": feedback.sample_size,
                    "methodology": feedback.methodology,
                    "satisfaction_score": feedback.satisfaction_score,
                    "nps": feedback.nps,
                    "supporting_quotes": quotes_by_theme.get(theme, [])[:3],
                },
            )

    for idx, claim in enumerate(claims, start=1):
        claim_id = f"claim:{idx}"
        if claim_id not in nodes:
            nodes[claim_id] = EvidenceNode(
                id=claim_id,
                type="claim",
                label=claim.text[:120],
                data=claim.model_dump(mode="json"),
            )
        for theme in feedback.themes + feedback.challenges:
            node_id = _feedback_node_id(theme)
            tokens = {token.lower() for token in claim.text.split() if len(token) > 3}
            theme_tokens = {token.lower() for token in theme.split() if len(token) > 3}
            overlap = tokens & theme_tokens
            if not overlap:
                continue
            confidence = min(1.0, base_confidence + 0.05 * len(overlap))
            links.append(EvidenceLink(
                source=claim_id,
                target=node_id,
                type="supported_by",
                confidence=round(confidence, 2),
                rationale=(
                    f"Beneficiary feedback theme '{theme}' shares "
                    f"{len(overlap)} keyword(s) with the claim."
                ),
            ))

    return EvidenceGraph(nodes=list(nodes.values()), links=links)


__all__ = [
    "BeneficiaryFeedbackQuality",
    "ConsentRecord",
    "FeedbackEvidenceLink",
    "LawfulBasis",
    "LeanDataQuestion",
    "LeanDataTemplate",
    "QuestionType",
    "SurveyChannel",
    "build_lean_data_survey",
    "filter_active_responses",
    "link_feedback_to_claims",
    "revoke_consent",
    "score_feedback_quality",
]
