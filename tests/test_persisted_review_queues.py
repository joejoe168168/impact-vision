"""Persisted review queues feed the evidence_review tool and the portfolio home."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


@pytest.fixture()
def store():
    from impact_vision.impact import state_store

    mem = state_store.MemoryStateStore()
    state_store.set_state_store(mem)
    yield mem
    state_store.set_state_store(None)


def _ctx():
    from impact_vision.tools.base import ToolExecutionContext

    return ToolExecutionContext(cwd=Path.cwd())


def test_evidence_review_tool_accumulates_in_a_named_queue(store) -> None:
    from impact_vision.impact.evidence_workflow import list_review_queues
    from impact_vision.tools.impact.evidence_review_tool import EvidenceReviewInput, EvidenceReviewTool

    tool = EvidenceReviewTool()
    for n in (1, 2):
        out = asyncio.run(tool.execute(EvidenceReviewInput(
            action="triage", queue_name="deal:acme",
            extractions=[{"item_id": f"c{n}", "extracted_text": f"claim {n}", "confidence": 0.9,
                          "source_refs": ["deck.pdf#p3", "audit.pdf"]}],
        ), _ctx()))
        assert not out.is_error
    queue = list_review_queues()["deal:acme"]
    assert [i.review.item_id for i in queue.items] == ["c1", "c2"]

    asyncio.run(tool.execute(EvidenceReviewInput(
        action="bulk_decide", queue_name="deal:acme", item_ids=["c1"], decision="approved", reviewer="cl",
    ), _ctx()))
    decided = {i.review.item_id: i.review.decision for i in list_review_queues()["deal:acme"].items}
    assert decided == {"c1": "approved", "c2": "pending"}

    # stateless calls (no queue_name) still persist nothing
    asyncio.run(tool.execute(EvidenceReviewInput(
        action="triage", extractions=[{"item_id": "x", "extracted_text": "x", "confidence": 0.4}],
    ), _ctx()))
    assert set(list_review_queues()) == {"deal:acme"}


def test_portfolio_home_lists_pending_queue_items(store) -> None:
    from impact_vision.impact.ai_review import AIExtractionReview
    from impact_vision.impact.evidence_workflow import load_review_queue, save_review_queue, list_review_queues
    from impact_vision.impact.portfolio_home import build_portfolio_home, render_portfolio_home

    q = load_review_queue("regulatory_radar")
    q.add(AIExtractionReview(item_id="r1", extracted_text="ESRS page changed", confidence=0.8, source_refs=["u"]))
    q.add(AIExtractionReview(item_id="r2", extracted_text="Done already", confidence=0.8, source_refs=["u"],
                             decision="approved"))
    save_review_queue(q, "regulatory_radar")
    view = build_portfolio_home([], review_queues=list_review_queues())
    texts = [r["text"] for r in view["review"]]
    assert texts == ["ESRS page changed"] and view["review"][0]["company"] == "Regulatory radar"
    assert "ESRS page changed" in render_portfolio_home(view)
