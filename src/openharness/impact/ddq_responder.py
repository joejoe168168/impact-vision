"""Approved-data-only ILPA DDQ 2.0 / PRI 2026 response drafting."""

from __future__ import annotations
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import yaml
from openpyxl import Workbook
from pydantic import BaseModel, Field
from openharness.impact.concordance import load_concordance
from openharness.impact.models import MetricRecord
from openharness.impact.portfolio_nlq import ApprovedDataPolicy
from openharness.impact.evidence_workflow import ExtractionReviewPolicy, ReviewQueue
from openharness.impact.roadmap_v2 import AIExtractionReview


class DDQQuestion(BaseModel):
    qid: str
    framework: Literal["ilpa_ddq2", "pri_2026", "ilpa_climate_module"]
    section: str
    text: str
    answer_kind: Literal["narrative", "metric", "boolean", "attachment"]
    maps_to: list[str] = Field(default_factory=list)
    source: str = ""


def load_ddq_bank() -> list[DDQQuestion]:
    path = Path(__file__).resolve().parents[3] / "data/ddq_bank.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    questions = []
    concepts = payload["metric_concepts"]
    for framework, count in payload["framework_counts"].items():
        for i in range(1, int(count) + 1):
            is_metric = i % 4 == 0
            questions.append(
                DDQQuestion(
                    qid=f"{framework}-{i:02d}",
                    framework=framework,
                    section="climate" if "climate" in framework else "responsible investment",
                    text=f"Describe the fund's {'verified performance for ' + concepts[(i // 4 - 1) % len(concepts)] if is_metric else 'policy, governance and implementation evidence'} (intent {i}).",
                    answer_kind="metric" if is_metric else "narrative",
                    maps_to=[concepts[(i // 4 - 1) % len(concepts)]]
                    if is_metric
                    else ["fund_profile"],
                    source=payload["sources"][framework],
                )
            )
    return questions


_DRAFT_REVIEW_QUEUE = ReviewQueue(
    policy=ExtractionReviewPolicy(min_source_refs=0, auto_approve_threshold=1.0)
)


def draft_answers(
    questions: list[DDQQuestion],
    fund_profile: dict,
    records: list[MetricRecord],
    policy: ApprovedDataPolicy,
) -> list[dict]:
    concordance = load_concordance()
    approved = [
        record
        for record in records
        if record.quality_score >= policy.minimum_quality_score
        and (record.is_verified or not policy.require_verified)
    ]
    answers = []
    for question in questions:
        citations = []
        answer = ""
        confidence = 0.0
        gap = ""
        if question.answer_kind == "metric":
            matches = [
                record
                for record in approved
                if (entry := concordance.lookup("iris", record.metric_id))
                and entry.concept_id in question.maps_to
            ]
            if matches:
                answer = "; ".join(
                    f"{r.metric_id}: {r.value} {r.unit} ({r.period})" for r in matches
                )
                citations = [ref for r in matches for ref in (r.evidence_refs or [r.source])]
                confidence = min(r.quality_score for r in matches) / 100
            else:
                gap = "No approved/verified MetricRecord maps to this question"
        else:
            answer = str(fund_profile.get(question.section, fund_profile.get("narrative", "")))
            confidence = 0.5 if answer else 0
            gap = "" if answer else "Fund profile lacks an approved narrative input"
        row = {
            "qid": question.qid,
            "question": question.text,
            "draft_answer": answer,
            "evidence_citations": citations,
            "confidence": confidence,
            "needs_human": question.answer_kind == "narrative" or not answer,
            "gap": gap,
            "review_status": "pending",
            "drafted_at": datetime.now(timezone.utc).isoformat(),
        }
        review_item = _DRAFT_REVIEW_QUEUE.add(
            AIExtractionReview(
                item_id=f"ddq:{question.qid}:{len(_DRAFT_REVIEW_QUEUE.items)}",
                extracted_text=answer or gap,
                confidence=confidence,
                rationale="Approved-data-only DDQ draft",
                source_refs=citations,
            ),
            prompt_version="ddq-responder-v1",
            model_version="deterministic",
        )
        row["review_item_id"] = review_item.review.item_id
        answers.append(row)
    return answers


def export_ddq(answers, format: Literal["xlsx", "docx_outline", "json"]):
    if format == "json":
        return json.dumps(answers, indent=2, default=str)
    if format == "docx_outline":
        return "\n\n".join(
            f"{row['qid']} {row['question']}\nDRAFT: {row['draft_answer'] or '[GAP]'}"
            for row in answers
        )
    wb = Workbook()
    ws = wb.active
    ws.title = "DDQ Draft"
    ws.append(["Question ID", "Question", "Draft answer", "Citations", "Review status"])
    for row in answers:
        ws.append(
            [
                row["qid"],
                row["question"],
                row["draft_answer"],
                "; ".join(row["evidence_citations"]),
                row["review_status"],
            ]
        )
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def review_status() -> dict:
    exported = _DRAFT_REVIEW_QUEUE.export()
    return {
        "total": exported.summary.total,
        "pending": exported.summary.pending,
        "items": [item.model_dump(mode="json") for item in exported.items],
    }


__all__ = ["DDQQuestion", "draft_answers", "export_ddq", "load_ddq_bank", "review_status"]
