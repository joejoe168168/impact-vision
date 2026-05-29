"""AI governance artifact for Impact Vision's own AI extraction (v5 Track E2).

Produces the governance documentation a fund needs when it puts an LLM in the
loop of an impact assessment: a **model card**, a **data-lineage** record for
each AI-derived artefact, and a **human-oversight log** — assembled from the
existing copilot review queue (:mod:`openharness.impact.engagements.copilot`).

It is **EU AI Act-aware**: it classifies the use against the Act's risk tiers
(unacceptable / high / limited / minimal) and checks the transparency,
human-oversight and record-keeping obligations that attach to it. Impact
Vision's claim-extraction copilot is a *limited-risk* transparency use (not an
Annex III high-risk system), but the artifact makes that determination explicit
and auditable.

Deterministic and offline — it documents governance, it does not call a model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field

from openharness.impact.engagements.copilot import CopilotOutput, CopilotReviewQueue


AIActRiskTier = Literal["unacceptable", "high", "limited", "minimal"]


class ModelCard(BaseModel):
    """A model card for an AI component used in an assessment."""

    name: str
    version: str = ""
    provider: str = ""
    purpose: str = ""
    intended_use: str = ""
    out_of_scope_use: list[str] = Field(default_factory=list)
    inputs: str = ""
    outputs: str = ""
    limitations: list[str] = Field(default_factory=list)
    training_data_note: str = (
        "Foundation model; training data per provider documentation. Impact Vision "
        "does not fine-tune on client data."
    )
    human_oversight: str = (
        "All AI outputs pass a human review gate (evidence_workflow / copilot review "
        "queue) before they inform a decision or client deliverable."
    )
    evaluation_notes: str = ""


class DataLineageRecord(BaseModel):
    """Provenance for one AI-derived artefact."""

    artifact_id: str
    artifact_kind: str = ""
    source_refs: list[str] = Field(default_factory=list)
    extraction_method: str = ""
    model: str = ""
    model_version: str = ""
    prompt_version: str = ""
    confidence: float = 0.0
    reviewed: bool = False
    review_decision: str = "pending"
    created_at: str = ""


class OversightLogEntry(BaseModel):
    """One human-oversight event derived from a copilot review decision."""

    artifact_id: str
    kind: str = ""
    reviewer: str = ""
    decision: str = "pending"
    decided_at: str = ""
    had_source_refs: bool = False
    reviewer_edits: str = ""


class AIActAssessment(BaseModel):
    """EU AI Act risk classification + obligation checklist."""

    risk_tier: AIActRiskTier
    rationale: str = ""
    transparency_obligation_met: bool = False
    human_oversight_obligation_met: bool = False
    record_keeping_obligation_met: bool = False
    obligations: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class AIGovernanceArtifact(BaseModel):
    """Bundled AI governance artifact for an assessment / engagement."""

    subject: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_card: ModelCard
    ai_act: AIActAssessment
    data_lineage: list[DataLineageRecord] = Field(default_factory=list)
    oversight_log: list[OversightLogEntry] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_artifacts(self) -> int:
        return len(self.data_lineage)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reviewed_artifacts(self) -> int:
        return sum(1 for r in self.data_lineage if r.reviewed)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def oversight_coverage_pct(self) -> float:
        if not self.data_lineage:
            return 0.0
        return round(self.reviewed_artifacts / self.total_artifacts * 100, 1)


# Annex III high-risk areas (abbreviated) — used to flag if a stated purpose
# strays into high-risk territory and therefore needs the full Article 9-15 regime.
_HIGH_RISK_HINTS = (
    "creditworthiness", "credit scoring", "recruitment", "hiring", "employment decision",
    "biometric", "law enforcement", "essential public service eligibility", "insurance pricing",
)
_PROHIBITED_HINTS = ("social scoring", "subliminal manipulation", "predictive policing")


def classify_ai_act_risk(
    purpose: str,
    *,
    human_in_the_loop: bool,
    discloses_ai_use: bool,
    keeps_records: bool,
) -> AIActAssessment:
    """Classify an AI use against the EU AI Act risk tiers + obligations."""
    low = purpose.lower()
    if any(h in low for h in _PROHIBITED_HINTS):
        tier: AIActRiskTier = "unacceptable"
        rationale = "Stated purpose resembles an EU AI Act prohibited practice — do not deploy."
    elif any(h in low for h in _HIGH_RISK_HINTS):
        tier = "high"
        rationale = (
            "Stated purpose may fall under an Annex III high-risk area — the full "
            "Article 9-15 regime (risk management, data governance, logging, human "
            "oversight, accuracy/robustness) would apply."
        )
    else:
        tier = "limited"
        rationale = (
            "Impact-claim extraction / summarisation is a limited-risk use: subject to "
            "transparency obligations (Article 50), not the high-risk regime."
        )

    obligations = [
        "Disclose to users that content is AI-generated/assisted (transparency).",
        "Maintain meaningful human oversight over AI outputs.",
        "Keep records of prompts, models, versions and review decisions.",
    ]
    gaps: list[str] = []
    if not discloses_ai_use:
        gaps.append("AI use is not disclosed in the deliverable (transparency gap).")
    if not human_in_the_loop:
        gaps.append("No human-in-the-loop review gate is recorded (oversight gap).")
    if not keeps_records:
        gaps.append("Prompt/model/version/decision records are incomplete (record-keeping gap).")

    return AIActAssessment(
        risk_tier=tier,
        rationale=rationale,
        transparency_obligation_met=discloses_ai_use,
        human_oversight_obligation_met=human_in_the_loop,
        record_keeping_obligation_met=keeps_records,
        obligations=obligations,
        gaps=gaps,
    )


def default_model_card(model: str = "", version: str = "", provider: str = "") -> ModelCard:
    """A sensible default model card for Impact Vision's extraction copilot."""
    return ModelCard(
        name=model or "Impact Vision extraction copilot",
        version=version,
        provider=provider,
        purpose="Extract impact claims, map them to IRIS+/SDGs, and draft assessment narratives.",
        intended_use="Decision-support for impact due diligence under human review.",
        out_of_scope_use=[
            "Automated investment decisions without human sign-off.",
            "Any Annex III high-risk use (credit scoring, hiring, biometrics, etc.).",
        ],
        inputs="Pitch decks, investment memos, investee disclosures (text).",
        outputs="Structured impact claims, framework mappings, draft narratives — all flagged for review.",
        limitations=[
            "May miss or over-attribute claims; confidence scores are heuristic.",
            "No guarantee of factual accuracy — every output requires human verification.",
        ],
    )


def build_ai_governance_artifact(
    *,
    subject: str = "",
    review_queue: CopilotReviewQueue | None = None,
    outputs: Iterable[CopilotOutput] | None = None,
    model_card: ModelCard | None = None,
    discloses_ai_use: bool = True,
) -> AIGovernanceArtifact:
    """Assemble a governance artifact from copilot outputs / review queue."""
    items: list[CopilotOutput] = list(outputs or [])
    if review_queue is not None:
        items.extend(review_queue.items)

    lineage: list[DataLineageRecord] = []
    oversight: list[OversightLogEntry] = []
    any_reviewed = False
    all_records_complete = True

    for o in items:
        any_reviewed = any_reviewed or (o.decision in {"approved", "approved_with_edits"})
        if not (o.model and o.prompt_version):
            all_records_complete = False
        lineage.append(DataLineageRecord(
            artifact_id=o.output_id,
            artifact_kind=o.kind,
            source_refs=list(o.source_refs),
            extraction_method="LLM-assisted (copilot)",
            model=o.model,
            model_version=o.model_version,
            prompt_version=o.prompt_version,
            confidence=o.confidence,
            reviewed=o.decision in {"approved", "approved_with_edits"},
            review_decision=o.decision,
            created_at=o.created_at,
        ))
        oversight.append(OversightLogEntry(
            artifact_id=o.output_id,
            kind=o.kind,
            reviewer=o.reviewer,
            decision=o.decision,
            decided_at=o.decided_at,
            had_source_refs=bool(o.source_refs),
            reviewer_edits=o.reviewer_edits,
        ))

    card = model_card or default_model_card()
    ai_act = classify_ai_act_risk(
        card.purpose,
        human_in_the_loop=any_reviewed or not items,
        discloses_ai_use=discloses_ai_use,
        keeps_records=all_records_complete,
    )

    return AIGovernanceArtifact(
        subject=subject,
        model_card=card,
        ai_act=ai_act,
        data_lineage=lineage,
        oversight_log=oversight,
    )


__all__ = [
    "AIActRiskTier",
    "ModelCard",
    "DataLineageRecord",
    "OversightLogEntry",
    "AIActAssessment",
    "AIGovernanceArtifact",
    "classify_ai_act_risk",
    "default_model_card",
    "build_ai_governance_artifact",
]
