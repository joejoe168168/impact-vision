"""Tool: Manage AI-extraction review queues with policy and bulk decisions (v3)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class EvidenceReviewInput(BaseModel):
    action: Literal[
        "queue_summary",
        "triage",
        "bulk_decide",
        "auto_approve",
        "build_item",
    ] = Field(description="Action to perform.")
    items: list[dict] = Field(default_factory=list, description="Review items (queue rows)")
    extractions: list[dict] = Field(default_factory=list, description="AIExtractionReview payloads to enqueue")
    item_ids: list[str] = Field(default_factory=list, description="Item IDs for bulk_decide")
    decision: Literal["pending", "approved", "rejected", "edit_required", "evidence_required"] = "pending"
    reviewer: str = "reviewer"
    rationale: str = ""
    policy: dict = Field(default_factory=dict, description="ExtractionReviewPolicy overrides")
    prompt_version: str = ""
    model_version: str = ""
    extracted_text: str = ""
    confidence: float = 0.0
    source_refs: list[str] = Field(default_factory=list)
    item_id: str = ""


class EvidenceReviewTool(BaseTool):
    name = "evidence_review"
    description = (
        "AI-extraction review queue with policy, batch decisions, and audit-trail bridging. "
        "Actions: 'queue_summary', 'triage' (apply policy to extractions), "
        "'bulk_decide' (approve/reject/edit_required/evidence_required across items), "
        "'auto_approve' (apply policy auto-approval), and 'build_item' (one-off queue item)."
    )
    input_model = EvidenceReviewInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        try:
            args = (
                arguments
                if isinstance(arguments, EvidenceReviewInput)
                else EvidenceReviewInput.model_validate(arguments)
            )
        except Exception:
            return False
        return args.action == "queue_summary"

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        # Imports are local to break a circular import: metric_records.py loads
        # tools.impact.common which loads tools.impact/__init__ which loads this
        # module. Doing the heavy v3 imports inside execute() keeps the package
        # import graph acyclic.
        from openharness.impact.evidence_workflow import (
            ExtractionReviewPolicy,
            ReviewQueue,
            build_review_item_from_extraction,
        )
        from openharness.impact.roadmap_v2 import AIExtractionReview

        args = arguments if isinstance(arguments, EvidenceReviewInput) else EvidenceReviewInput.model_validate(arguments)
        policy = ExtractionReviewPolicy.model_validate(args.policy) if args.policy else ExtractionReviewPolicy()
        queue = ReviewQueue(policy=policy)
        for item in args.items:
            try:
                queue.items.append(_load_item(item))
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid queue item: {e}", is_error=True)

        if args.action == "build_item":
            try:
                item = build_review_item_from_extraction(
                    item_id=args.item_id or args.extracted_text[:32] or "extraction",
                    extracted_text=args.extracted_text,
                    confidence=args.confidence,
                    rationale=args.rationale,
                    source_refs=args.source_refs,
                    prompt_version=args.prompt_version,
                    model_version=args.model_version,
                    policy=policy,
                )
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Build failed: {e}", is_error=True)
            return _ok(item.model_dump(mode="json"))

        if args.extractions:
            for payload in args.extractions:
                review = AIExtractionReview.model_validate(payload)
                queue.add(
                    review,
                    prompt_version=args.prompt_version,
                    model_version=args.model_version,
                )

        if args.action == "queue_summary":
            return _ok(queue.export().model_dump(mode="json"))

        if args.action == "triage":
            return _ok({
                "policy": policy.model_dump(mode="json"),
                "items": [item.model_dump(mode="json") for item in queue.items],
                "summary": queue.summary().model_dump(mode="json"),
            })

        if args.action == "bulk_decide":
            try:
                decisions = queue.bulk_decide(
                    args.item_ids,
                    decision=args.decision,
                    reviewer=args.reviewer,
                    rationale=args.rationale,
                )
            except (KeyError, ValueError) as e:
                return ToolResult(output=str(e), is_error=True)
            return _ok({
                "decided": [item.model_dump(mode="json") for item in decisions],
                "summary": queue.summary().model_dump(mode="json"),
            })

        if args.action == "auto_approve":
            try:
                approved = queue.auto_approve_high_confidence(reviewer=args.reviewer)
            except (KeyError, ValueError) as e:
                return ToolResult(output=str(e), is_error=True)
            return _ok({
                "approved": [item.model_dump(mode="json") for item in approved],
                "summary": queue.summary().model_dump(mode="json"),
            })

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)


def _load_item(payload: dict):
    from openharness.impact.evidence_workflow import ReviewQueueItem

    return ReviewQueueItem.model_validate(payload)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
