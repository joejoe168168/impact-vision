"""AI-extraction review queue with policy and bulk operations (v3 Track 1.8).

The v3 roadmap requires every LLM-derived claim or extracted value to
expose a reviewer state, confidence threshold, and audit trail. v2
shipped a single :class:`AIExtractionReview` decision; v3 adds the
**queue-level** primitives a real review workflow needs:

* :class:`ExtractionReviewPolicy` — configurable confidence threshold,
  source-ref minimum, prompt-version pin, and auto-approve cap.
* :class:`ReviewQueueItem` — queue row including extraction metadata,
  policy verdict, current decision, and reviewer comments.
* :class:`ReviewQueue` — managed queue with triage helpers, batch
  decisions, audit-trail bridging, and a clean export shape for
  reviewer UIs.

The module is fully offline and storage-agnostic: it produces structured
events that callers can persist however they like (SQLite, FastAPI
state, an in-memory cache).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field, field_validator

from openharness.impact.audit_trail import AuditTrail
from openharness.impact.roadmap_v2 import AIExtractionReview, ReviewDecision


PolicyVerdict = Literal["auto_approve_eligible", "needs_review", "needs_evidence", "blocked"]


class ExtractionReviewPolicy(BaseModel):
    """Confidence-threshold and provenance policy applied to a queue."""

    min_confidence: float = Field(ge=0, le=1, default=0.5)
    min_source_refs: int = Field(ge=0, default=1)
    auto_approve_threshold: float = Field(ge=0, le=1, default=0.9)
    require_prompt_version: str = ""
    require_model_version: str = ""

    def evaluate(
        self,
        review: AIExtractionReview,
        *,
        prompt_version: str = "",
        model_version: str = "",
    ) -> PolicyVerdict:
        """Return the policy verdict for one extraction item."""
        if self.require_prompt_version and prompt_version != self.require_prompt_version:
            return "blocked"
        if self.require_model_version and model_version != self.require_model_version:
            return "blocked"
        if review.confidence < self.min_confidence:
            return "needs_review"
        if len(review.source_refs) < self.min_source_refs:
            return "needs_evidence"
        if review.confidence >= self.auto_approve_threshold and len(review.source_refs) >= self.min_source_refs:
            return "auto_approve_eligible"
        return "needs_review"


class ReviewQueueItem(BaseModel):
    """One reviewable extraction in a queue, with policy verdict."""

    review: AIExtractionReview
    prompt_version: str = ""
    model_version: str = ""
    verdict: PolicyVerdict = "needs_review"
    history: list[dict[str, Any]] = Field(default_factory=list)
    flagged_at: str = Field(default_factory=lambda: _now())

    @field_validator("history", mode="before")
    @classmethod
    def coerce_history(cls, value: Any) -> Any:
        return list(value or [])


class ReviewQueueSummary(BaseModel):
    """Aggregate counts across a review queue."""

    total: int
    pending: int
    approved: int
    rejected: int
    edit_required: int
    evidence_required: int
    auto_approve_eligible: int
    blocked: int


class ReviewQueueExport(BaseModel):
    """Serialization shape for reviewer UIs and stored audit logs."""

    policy: ExtractionReviewPolicy
    items: list[ReviewQueueItem]
    summary: ReviewQueueSummary


class ReviewQueue(BaseModel):
    """Managed AI-extraction review queue with policy and audit-trail bridging."""

    policy: ExtractionReviewPolicy = Field(default_factory=ExtractionReviewPolicy)
    items: list[ReviewQueueItem] = Field(default_factory=list)

    def add(
        self,
        review: AIExtractionReview,
        *,
        prompt_version: str = "",
        model_version: str = "",
    ) -> ReviewQueueItem:
        """Add an extraction to the queue and apply the policy."""
        verdict = self.policy.evaluate(
            review,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        item = ReviewQueueItem(
            review=review,
            prompt_version=prompt_version,
            model_version=model_version,
            verdict=verdict,
            history=[{
                "event": "queued",
                "at": _now(),
                "verdict": verdict,
            }],
        )
        self.items.append(item)
        return item

    def add_many(
        self,
        reviews: Iterable[AIExtractionReview],
        *,
        prompt_version: str = "",
        model_version: str = "",
    ) -> list[ReviewQueueItem]:
        return [
            self.add(review, prompt_version=prompt_version, model_version=model_version)
            for review in reviews
        ]

    def pending(self) -> list[ReviewQueueItem]:
        return [item for item in self.items if item.review.decision == "pending"]

    def needs_evidence(self) -> list[ReviewQueueItem]:
        return [item for item in self.items if item.verdict == "needs_evidence"]

    def auto_approve_eligible(self) -> list[ReviewQueueItem]:
        return [
            item
            for item in self.items
            if item.verdict == "auto_approve_eligible" and item.review.decision == "pending"
        ]

    def blocked(self) -> list[ReviewQueueItem]:
        return [item for item in self.items if item.verdict == "blocked"]

    def find(self, item_id: str) -> ReviewQueueItem:
        for item in self.items:
            if item.review.item_id == item_id:
                return item
        raise KeyError(f"Unknown review item: {item_id}")

    def decide(
        self,
        item_id: str,
        decision: ReviewDecision,
        *,
        reviewer: str,
        rationale: str = "",
        audit_trail: AuditTrail | None = None,
    ) -> ReviewQueueItem:
        """Apply a decision to one queue item and optionally append to the audit trail."""
        item = self.find(item_id)
        if decision == "approved" and item.verdict == "blocked":
            raise ValueError(
                f"Cannot approve item {item_id}: blocked by policy "
                f"(prompt/model version mismatch)"
            )
        if decision == "approved" and item.review.confidence < self.policy.min_confidence:
            raise ValueError(
                f"Cannot approve item {item_id}: confidence "
                f"{item.review.confidence:.2f} below policy minimum "
                f"{self.policy.min_confidence:.2f}"
            )
        if decision == "approved" and len(item.review.source_refs) < self.policy.min_source_refs:
            raise ValueError(
                f"Cannot approve item {item_id}: only "
                f"{len(item.review.source_refs)} source ref(s), policy requires "
                f"{self.policy.min_source_refs}"
            )
        new_review = item.review.model_copy(update={
            "decision": decision,
            "reviewer": reviewer,
        })
        new_history = list(item.history)
        new_history.append({
            "event": "decided",
            "decision": decision,
            "reviewer": reviewer,
            "rationale": rationale,
            "at": _now(),
        })
        index = self.items.index(item)
        updated = item.model_copy(update={
            "review": new_review,
            "history": new_history,
        })
        self.items[index] = updated
        if audit_trail is not None:
            audit_trail.record_event(
                event_type="ai_extraction.decision",
                payload={
                    "item_id": item.review.item_id,
                    "decision": decision,
                    "rationale": rationale,
                    "confidence": item.review.confidence,
                    "verdict": item.verdict,
                    "prompt_version": item.prompt_version,
                    "model_version": item.model_version,
                },
                actor=reviewer,
            )
        return updated

    def bulk_decide(
        self,
        item_ids: Iterable[str],
        decision: ReviewDecision,
        *,
        reviewer: str,
        rationale: str = "",
        audit_trail: AuditTrail | None = None,
    ) -> list[ReviewQueueItem]:
        """Apply a decision across many items in one call."""
        results: list[ReviewQueueItem] = []
        for item_id in item_ids:
            results.append(self.decide(
                item_id,
                decision,
                reviewer=reviewer,
                rationale=rationale,
                audit_trail=audit_trail,
            ))
        return results

    def auto_approve_high_confidence(
        self,
        *,
        reviewer: str = "auto-approver",
        audit_trail: AuditTrail | None = None,
    ) -> list[ReviewQueueItem]:
        """Approve every queue item that the policy marks auto-eligible."""
        results: list[ReviewQueueItem] = []
        for item in list(self.auto_approve_eligible()):
            results.append(self.decide(
                item.review.item_id,
                "approved",
                reviewer=reviewer,
                rationale="auto-approved: confidence >= auto_approve_threshold",
                audit_trail=audit_trail,
            ))
        return results

    def summary(self) -> ReviewQueueSummary:
        decisions = [item.review.decision for item in self.items]
        verdicts = [item.verdict for item in self.items]
        return ReviewQueueSummary(
            total=len(self.items),
            pending=sum(1 for d in decisions if d == "pending"),
            approved=sum(1 for d in decisions if d == "approved"),
            rejected=sum(1 for d in decisions if d == "rejected"),
            edit_required=sum(1 for d in decisions if d == "edit_required"),
            evidence_required=sum(1 for d in decisions if d == "evidence_required"),
            auto_approve_eligible=sum(1 for v in verdicts if v == "auto_approve_eligible"),
            blocked=sum(1 for v in verdicts if v == "blocked"),
        )

    def export(self) -> ReviewQueueExport:
        return ReviewQueueExport(
            policy=self.policy,
            items=list(self.items),
            summary=self.summary(),
        )


def build_review_item_from_extraction(
    *,
    item_id: str,
    extracted_text: str,
    confidence: float,
    rationale: str = "",
    source_refs: Iterable[str] | None = None,
    prompt_version: str = "",
    model_version: str = "",
    policy: ExtractionReviewPolicy | None = None,
) -> ReviewQueueItem:
    """Convenience wrapper to build one queue item without instantiating a queue."""
    review = AIExtractionReview(
        item_id=item_id,
        extracted_text=extracted_text,
        confidence=confidence,
        rationale=rationale,
        source_refs=list(source_refs or []),
    )
    queue = ReviewQueue(policy=policy or ExtractionReviewPolicy())
    return queue.add(review, prompt_version=prompt_version, model_version=model_version)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "ExtractionReviewPolicy",
    "PolicyVerdict",
    "ReviewQueue",
    "ReviewQueueExport",
    "ReviewQueueItem",
    "ReviewQueueSummary",
    "build_review_item_from_extraction",
]
