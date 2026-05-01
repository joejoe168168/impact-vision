"""Tests for v3 AI-extraction review queue (policy + bulk decisions)."""

from __future__ import annotations

import pytest

from openharness.impact.audit_trail import AuditTrail
from openharness.impact.evidence_workflow import (
    ExtractionReviewPolicy,
    ReviewQueue,
    build_review_item_from_extraction,
)
from openharness.impact.roadmap_v2 import AIExtractionReview


def _review(item_id: str, *, confidence: float, source_refs: list[str] | None = None) -> AIExtractionReview:
    return AIExtractionReview(
        item_id=item_id,
        extracted_text=f"text-{item_id}",
        confidence=confidence,
        source_refs=source_refs or ["evidence://" + item_id],
    )


def test_policy_marks_high_confidence_as_auto_approve_eligible() -> None:
    queue = ReviewQueue(
        policy=ExtractionReviewPolicy(
            min_confidence=0.5, min_source_refs=1, auto_approve_threshold=0.8,
        ),
    )
    queue.add(_review("a", confidence=0.95))
    queue.add(_review("b", confidence=0.6))
    queue.add(_review("c", confidence=0.3))
    summary = queue.summary()
    assert summary.auto_approve_eligible == 1
    assert summary.pending == 3


def test_policy_blocks_on_prompt_version_mismatch() -> None:
    queue = ReviewQueue(
        policy=ExtractionReviewPolicy(
            min_confidence=0.5,
            min_source_refs=1,
            require_prompt_version="prompt-v1",
        ),
    )
    item = queue.add(_review("a", confidence=0.95), prompt_version="prompt-v2")
    assert item.verdict == "blocked"
    with pytest.raises(ValueError):
        queue.decide("a", "approved", reviewer="r")


def test_policy_requires_evidence() -> None:
    queue = ReviewQueue(policy=ExtractionReviewPolicy(min_confidence=0.4, min_source_refs=2))
    item = queue.add(_review("a", confidence=0.6, source_refs=["x"]))
    assert item.verdict == "needs_evidence"


def test_decide_rejects_approval_without_required_source_refs() -> None:
    queue = ReviewQueue(policy=ExtractionReviewPolicy(min_confidence=0.4, min_source_refs=2))
    queue.add(_review("a", confidence=0.95, source_refs=["x"]))
    with pytest.raises(ValueError, match="source ref"):
        queue.decide("a", "approved", reviewer="r")


def test_decide_records_audit_trail_and_history() -> None:
    queue = ReviewQueue(policy=ExtractionReviewPolicy(min_confidence=0.5))
    queue.add(_review("a", confidence=0.9))
    audit = AuditTrail()
    decided = queue.decide("a", "approved", reviewer="alice", rationale="ok", audit_trail=audit)
    assert decided.review.decision == "approved"
    assert decided.review.reviewer == "alice"
    assert any(event.get("event") == "decided" for event in decided.history)
    assert audit.length == 1


def test_bulk_decide_processes_all_items() -> None:
    queue = ReviewQueue(policy=ExtractionReviewPolicy(min_confidence=0.5))
    for index in range(3):
        queue.add(_review(f"i{index}", confidence=0.7))
    out = queue.bulk_decide(["i0", "i1", "i2"], "edit_required", reviewer="alice")
    assert all(item.review.decision == "edit_required" for item in out)


def test_auto_approve_high_confidence_skips_low_confidence() -> None:
    queue = ReviewQueue(policy=ExtractionReviewPolicy(min_confidence=0.5, auto_approve_threshold=0.85))
    queue.add(_review("a", confidence=0.9))
    queue.add(_review("b", confidence=0.7))
    approved = queue.auto_approve_high_confidence(reviewer="auto")
    assert len(approved) == 1
    assert approved[0].review.item_id == "a"


def test_decide_rejects_approval_below_min_confidence() -> None:
    queue = ReviewQueue(policy=ExtractionReviewPolicy(min_confidence=0.7))
    queue.add(_review("a", confidence=0.4))
    with pytest.raises(ValueError):
        queue.decide("a", "approved", reviewer="r")


def test_build_review_item_helper_returns_queue_item() -> None:
    item = build_review_item_from_extraction(
        item_id="x",
        extracted_text="some claim",
        confidence=0.9,
        source_refs=["evidence://1"],
    )
    assert item.review.item_id == "x"
    assert item.verdict in {"auto_approve_eligible", "needs_review"}
