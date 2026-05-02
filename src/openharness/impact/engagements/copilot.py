"""AI consultant copilot with governance (roadmap-v4 Track 8).

Provides the governance scaffolding needed to put an LLM on top of the
engagement workspace **safely**: deterministic structure for the copilot's
question / challenge / draft / answer flows, plus an AI-output review queue
with prompt + model + reviewer metadata on every artefact.

The module deliberately avoids calling an LLM directly. Impact Vision's v3
governance rule (see :mod:`openharness.impact.evidence_workflow`) is that
every AI claim has to pass a human review gate; the copilot routes its
outputs through that gate by recording a :class:`CopilotOutput` which the
consultant then approves / rejects / edits.

Where the actual LLM lives is a wiring concern for the agent layer
(`impact_copilot_tool`) — the module here only requires the caller to
supply the result and its provenance.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field


OutputKind = Literal[
    "engagement_qa",
    "challenge",
    "proposal_draft",
    "sow_draft",
    "meeting_note_summary",
    "claim_draft",
    "value_creation_suggestion",
]

ReviewDecision = Literal[
    "pending",
    "approved",
    "approved_with_edits",
    "rejected",
    "needs_more_evidence",
]


class CopilotOutput(BaseModel):
    """One AI output recorded with full provenance (Track 8.5)."""

    output_id: str = Field(default_factory=lambda: f"co_{secrets.token_hex(6)}")
    engagement_id: str = ""
    kind: OutputKind
    prompt: str
    response: str
    model: str = ""
    model_version: str = ""
    prompt_version: str = ""
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reviewer: str = ""
    decision: ReviewDecision = "pending"
    decided_at: str = ""
    reviewer_edits: str = ""
    created_at: str = Field(default_factory=lambda: _now())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def policy_passed(self) -> bool:
        """True when the output has a reviewer, source refs, and a positive decision."""
        return (
            bool(self.reviewer)
            and bool(self.source_refs)
            and self.decision in {"approved", "approved_with_edits"}
        )


class CopilotReviewQueue(BaseModel):
    """In-memory AI-output review queue (Track 8.5)."""

    queue_id: str = Field(default_factory=lambda: f"q_{secrets.token_hex(4)}")
    items: list[CopilotOutput] = Field(default_factory=list)

    def enqueue(self, output: CopilotOutput) -> CopilotOutput:
        self.items.append(output)
        return output

    def pending(self) -> list[CopilotOutput]:
        return [o for o in self.items if o.decision == "pending"]

    def decide(
        self,
        output_id: str,
        *,
        decision: ReviewDecision,
        reviewer: str,
        reviewer_edits: str = "",
    ) -> CopilotOutput:
        for output in self.items:
            if output.output_id != output_id:
                continue
            if decision == "approved" and output.confidence < 0.5:
                raise ValueError(
                    "Low-confidence AI output cannot be approved without "
                    "'approved_with_edits' and an explanation."
                )
            if decision == "approved" and not output.source_refs:
                raise ValueError(
                    "AI output cannot be approved without at least one source_ref."
                )
            output.decision = decision
            output.reviewer = reviewer
            output.decided_at = _now()
            if reviewer_edits:
                output.reviewer_edits = reviewer_edits
            return output
        raise KeyError(f"Unknown copilot output {output_id!r}")


# --------------------------------------------------------------- QA scaffolding


class EngagementQuery(BaseModel):
    """A question the consultant asks across engagement docs / metrics / notes."""

    query_id: str = Field(default_factory=lambda: f"qry_{secrets.token_hex(4)}")
    engagement_id: str
    question: str
    approved_only: bool = True
    """Client-safe mode: only approved evidence may inform the answer."""


class CopilotAnswer(BaseModel):
    """Structured answer from the engagement copilot."""

    query_id: str
    answer: str
    citations: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    confidence: float = 0.0


def answer_from_approved_evidence(
    query: EngagementQuery,
    *,
    approved_claims: Iterable[dict],
    approved_metrics: Iterable[dict],
    gaps: Iterable[str] | None = None,
) -> CopilotAnswer:
    """Client-safe answer (Track 8.6): only surfaces approved data.

    The caller supplies lists of approved claim / metric payloads; the
    function never synthesises new statements from those payloads — it just
    cites the matching ones. This keeps the output auditable.
    """
    needle = query.question.lower()
    matching_claims = [
        c for c in approved_claims
        if any(tok in str(c.get("text", "")).lower() for tok in needle.split() if len(tok) > 3)
    ]
    matching_metrics = [
        m for m in approved_metrics
        if any(tok in str(m.get("name", "")).lower() for tok in needle.split() if len(tok) > 3)
    ]
    citations = [
        *(f"claim:{c.get('claim_id', c.get('id', ''))}" for c in matching_claims),
        *(f"metric:{m.get('metric_id', m.get('id', ''))}" for m in matching_metrics),
    ]
    citations = [c for c in citations if c not in {"claim:", "metric:"}]
    if not matching_claims and not matching_metrics:
        return CopilotAnswer(
            query_id=query.query_id,
            answer=(
                "No approved data matched this question. Escalate to the "
                "consultant before drafting a client response."
            ),
            gaps=list(gaps or []) + ["No approved evidence matched the question"],
            confidence=0.0,
        )

    summary_parts: list[str] = []
    for claim in matching_claims[:3]:
        summary_parts.append(f"- Claim: {claim.get('text')}")
    for metric in matching_metrics[:3]:
        summary_parts.append(
            f"- Metric {metric.get('metric_id', metric.get('id'))}: "
            f"{metric.get('value', '?')} {metric.get('unit', '')}"
        )

    answer = (
        "Based on approved evidence only:\n" + "\n".join(summary_parts)
    )
    confidence = min(
        1.0, 0.4 + 0.1 * (len(matching_claims) + len(matching_metrics))
    )
    return CopilotAnswer(
        query_id=query.query_id,
        answer=answer,
        citations=citations,
        gaps=list(gaps or []),
        confidence=round(confidence, 3),
    )


# ------------------------------------------------------------ challenge mode


class ChallengeFinding(BaseModel):
    """One 'challenge mode' critique (Track 8.2)."""

    finding_id: str = Field(default_factory=lambda: f"ch_{secrets.token_hex(4)}")
    category: Literal[
        "unsupported_claim",
        "weak_toc_link",
        "missing_stakeholder",
        "missing_evidence",
        "unclear_baseline",
    ]
    message: str
    target_ref: str = ""
    severity: Literal["low", "medium", "high"] = "medium"


def run_challenge(
    *,
    claims: Iterable[dict],
    toc_validation_findings: Iterable[dict] | None = None,
    stakeholder_voice_present: bool = False,
) -> list[ChallengeFinding]:
    """Deterministic challenge pass."""
    findings: list[ChallengeFinding] = []
    for claim in claims:
        if not claim.get("evidence_refs"):
            findings.append(
                ChallengeFinding(
                    category="unsupported_claim",
                    message=(
                        f"Claim '{claim.get('text', '')}' lacks evidence references."
                    ),
                    target_ref=str(claim.get("claim_id", claim.get("id", ""))),
                    severity="high",
                )
            )
    for toc_finding in toc_validation_findings or []:
        if toc_finding.get("code") == "causal_strength":
            findings.append(
                ChallengeFinding(
                    category="weak_toc_link",
                    message=toc_finding.get("message", "Weak causal link detected."),
                    severity=toc_finding.get("severity", "low"),
                )
            )
        elif toc_finding.get("code") == "outcomes_have_indicators":
            findings.append(
                ChallengeFinding(
                    category="missing_evidence",
                    message=toc_finding.get("message", "Outcome lacks indicators."),
                    severity=toc_finding.get("severity", "medium"),
                )
            )
    if not stakeholder_voice_present:
        findings.append(
            ChallengeFinding(
                category="missing_stakeholder",
                message="No stakeholder voice instrument attached to this engagement.",
                severity="medium",
            )
        )
    return findings


# ----------------------------------------------------- meeting note ingestion


class MeetingNoteIngestion(BaseModel):
    """Track 8.4: structured output from a meeting-note ingestion pass."""

    note_id: str = Field(default_factory=lambda: f"mn_{secrets.token_hex(4)}")
    engagement_id: str = ""
    decisions: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


def extract_meeting_notes(*, raw_text: str, engagement_id: str = "") -> MeetingNoteIngestion:
    """Heuristic extraction — decisions / actions / risks by prefix.

    The parser treats lines starting with a verb tag (Decision:, Action:,
    Risk:) as structured; Track 8 will later layer an LLM. The deterministic
    backbone is enough to seed the engagement audit log today.
    """
    decisions: list[str] = []
    actions: list[str] = []
    risks: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip("-• ").strip()
        if not stripped:
            continue
        low = stripped.lower()
        if low.startswith("decision:"):
            decisions.append(stripped.split(":", 1)[1].strip())
        elif low.startswith(("action:", "todo:", "to do:")):
            actions.append(stripped.split(":", 1)[1].strip())
        elif low.startswith("risk:"):
            risks.append(stripped.split(":", 1)[1].strip())
    return MeetingNoteIngestion(
        engagement_id=engagement_id,
        decisions=decisions,
        action_items=actions,
        risks=risks,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "ChallengeFinding",
    "CopilotAnswer",
    "CopilotOutput",
    "CopilotReviewQueue",
    "EngagementQuery",
    "MeetingNoteIngestion",
    "OutputKind",
    "ReviewDecision",
    "answer_from_approved_evidence",
    "extract_meeting_notes",
    "run_challenge",
]
