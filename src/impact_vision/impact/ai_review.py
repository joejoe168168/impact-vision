"""AI-extraction review records, metric harmonisation and governance log (moved from roadmap_v2, v7 W5.4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from impact_vision.impact._util import _to_float
from impact_vision.impact.investee_collection import (
    CollectionSubmission,
    InvesteeQuestionnaireSchema,
    validate_collection_submission,
)

ReviewDecision = Literal["pending", "approved", "rejected", "edit_required", "evidence_required"]


class ReviewQueueItem(BaseModel):
    """Analyst review queue item with anomaly flags."""

    submission_id: str
    company_name: str
    status: str
    flags: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)


def build_review_queue(
    submissions: list[CollectionSubmission],
    schema_by_submission: dict[str, InvesteeQuestionnaireSchema],
    *,
    previous_values: dict[tuple[str, str], float] | None = None,
    anomaly_threshold_pct: float = 50.0,
) -> list[ReviewQueueItem]:
    """Create a review queue with missing-data and period-over-period anomaly flags."""
    previous_values = previous_values or {}
    queue: list[ReviewQueueItem] = []
    for sub in submissions:
        schema = schema_by_submission[sub.submission_id]
        validation = validate_collection_submission(sub, schema)
        flags: list[str] = []
        comments: list[str] = []
        for field_name in (
            "missing_required",
            "unknown_metrics",
            "evidence_missing",
            "unit_mismatches",
            "duplicate_metrics",
        ):
            values = getattr(validation, field_name)
            if values:
                flags.append(field_name)
                comments.append(f"{field_name}: {', '.join(values)}")
        for response in sub.responses:
            key = (sub.company_name, response.metric_id.strip().upper())
            prev = previous_values.get(key)
            current = _to_float(response.value)
            if prev is not None and current is not None:
                if prev == 0:
                    if current != 0:
                        flags.append("period_anomaly")
                        comments.append(
                            f"{response.metric_id}: changed from zero baseline to {current}"
                        )
                else:
                    change = abs(current - prev) / abs(prev) * 100
                    if change > anomaly_threshold_pct:
                        flags.append("period_anomaly")
                        comments.append(f"{response.metric_id}: {change:.1f}% change from prior period")
        if flags or sub.status != "approved":
            queue.append(ReviewQueueItem(
                submission_id=sub.submission_id,
                company_name=sub.company_name,
                status=sub.status,
                flags=sorted(set(flags)),
                comments=comments,
            ))
    return queue


class AIExtractionReview(BaseModel):
    """Review gate for an AI-extracted claim or value."""

    item_id: str
    extracted_text: str
    confidence: float = Field(ge=0, le=1)
    rationale: str = ""
    source_refs: list[str] = Field(default_factory=list)
    decision: ReviewDecision = "pending"
    reviewer: str = ""


def decide_ai_extraction(review: AIExtractionReview, decision: ReviewDecision, reviewer: str) -> AIExtractionReview:
    """Approve, reject, edit-require, or request evidence for AI extraction."""
    if decision == "approved" and review.confidence < 0.5:
        raise ValueError("Low-confidence AI output cannot be approved without editing or more evidence")
    if decision == "approved" and not review.source_refs:
        raise ValueError("AI output cannot be approved without at least one source reference")
    return review.model_copy(update={"decision": decision, "reviewer": reviewer})


class AIMetricMapping(BaseModel):
    """AI-assisted mapping to a canonical metric."""

    source_column: str
    canonical_metric_id: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    review_state: ReviewDecision = "pending"


def harmonize_uploaded_metrics(upload_columns: list[str], metric_dictionary: dict[str, str]) -> list[AIMetricMapping]:
    """Map messy uploaded metric columns to canonical metric IDs with confidence."""
    mappings: list[AIMetricMapping] = []
    for column in upload_columns:
        lower = column.lower()
        best_metric = ""
        best_score = 0.0
        for metric_id, label in metric_dictionary.items():
            tokens = {token for token in label.lower().replace("_", " ").split() if len(token) > 2}
            score = sum(1 for token in tokens if token in lower) / max(1, len(tokens))
            if score > best_score:
                best_metric = metric_id
                best_score = score
        mappings.append(AIMetricMapping(
            source_column=column,
            canonical_metric_id=best_metric,
            confidence=round(best_score, 3),
            rationale="Token overlap with canonical metric label.",
        ))
    return mappings


class AIGovernanceLog(BaseModel):
    """Governance log for AI outputs."""

    output_id: str
    prompt_version: str
    model_version: str
    source_refs: list[str]
    human_reviewer: str
    confidence: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)

    @property
    def policy_passed(self) -> bool:
        return bool(self.human_reviewer) and self.confidence >= self.threshold and bool(self.source_refs)


__all__ = [
    "ReviewDecision",
    "ReviewQueueItem",
    "build_review_queue",
    "AIExtractionReview",
    "decide_ai_extraction",
    "AIMetricMapping",
    "harmonize_uploaded_metrics",
    "AIGovernanceLog",
]
