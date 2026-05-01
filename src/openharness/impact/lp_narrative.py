"""LP narrative + Q&A workspace (v3 Track 7.5 / 7.8).

Generates an audit-friendly LP-facing narrative without invoking an
LLM directly. The LP gets:

* a **deterministic Markdown narrative** with portfolio coverage,
  highlight metrics, GIIN-style peer benchmark commentary, and
  evidence manifest references;
* a **Q&A workspace** that answers LP follow-up questions strictly
  against approved (verified) :class:`MetricRecord` rows, returning
  citations and a hashed history.

Downstream code can pass the deterministic narrative to a governed LLM
(via :mod:`openharness.impact.evidence_workflow`) for stylistic
expansion, but the *factual* content lives here and is reproducible.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field

from openharness.impact.external_benchmarks import (
    DimensionKey,
    PeerContext,
    contextualise,
)
from openharness.impact.lp_portal import ImpactDashboardView
from openharness.impact.models import MetricRecord


NarrativeFormat = Literal["markdown", "json"]


class LPNarrativeRequest(BaseModel):
    """Inputs needed to generate an LP narrative."""

    fund_name: str
    reporting_period: str
    dashboard: ImpactDashboardView
    sector: str = "generic"
    peer_dimensions: list[DimensionKey] = Field(default_factory=list)
    evidence_manifest: dict[str, str] = Field(default_factory=dict)
    risk_callouts: list[str] = Field(default_factory=list)
    opportunity_callouts: list[str] = Field(default_factory=list)


class LPNarrativeReport(BaseModel):
    """Generated LP narrative output."""

    fund_name: str
    reporting_period: str
    generated_at: str = Field(default_factory=lambda: _now())
    headline: str
    coverage_summary: str
    peer_context: list[PeerContext] = Field(default_factory=list)
    key_metrics: list[str] = Field(default_factory=list)
    risk_callouts: list[str] = Field(default_factory=list)
    opportunity_callouts: list[str] = Field(default_factory=list)
    evidence_manifest_hash: str = ""
    markdown: str
    json_payload: dict[str, Any] = Field(default_factory=dict)


def generate_lp_narrative(request: LPNarrativeRequest) -> LPNarrativeReport:
    """Build a deterministic, audit-friendly LP narrative from the dashboard."""
    peer_contexts: list[PeerContext] = []
    for dimension in request.peer_dimensions:
        score = request.dashboard.five_dimensions.get(dimension)
        if score is None:
            continue
        ctx = contextualise(request.sector, dimension, score)
        if ctx is not None:
            peer_contexts.append(ctx)

    headline = (
        f"{request.fund_name} — {request.reporting_period}: "
        f"{request.dashboard.companies} companies covered "
        f"(coverage {request.dashboard.coverage_pct:.1f}%); "
        f"impact score {request.dashboard.portfolio_impact_score:.2f}/5."
    )

    coverage_summary = (
        f"Portfolio impact score {request.dashboard.portfolio_impact_score:.2f}/5 across "
        f"{request.dashboard.companies} companies, with top SDGs "
        f"{', '.join(request.dashboard.top_sdgs) or 'n/a'}. "
        f"Coverage of approved evidence: {request.dashboard.coverage_pct:.1f}%."
    )

    key_metrics = [
        f"{dim}: {score:.2f}/5"
        for dim, score in sorted(request.dashboard.five_dimensions.items())
    ]

    manifest_hash = ""
    if request.evidence_manifest:
        joined = "\n".join(
            f"{name}={digest}" for name, digest in sorted(request.evidence_manifest.items())
        )
        manifest_hash = hashlib.sha256(joined.encode("utf-8")).hexdigest()

    markdown_lines = [
        f"# {request.fund_name} — Impact Narrative",
        f"_Reporting period: **{request.reporting_period}**_",
        "",
        "## Headline",
        headline,
        "",
        "## Coverage",
        coverage_summary,
        "",
    ]
    if key_metrics:
        markdown_lines += ["## 5-Dimension scores"] + [f"- {item}" for item in key_metrics] + [""]
    if peer_contexts:
        markdown_lines += [f"## Peer context (sector: {request.sector})"]
        for ctx in peer_contexts:
            markdown_lines.append(
                f"- **{ctx.dimension}** — score {ctx.company_score:.2f}, "
                f"quartile {ctx.quartile}: {ctx.narrative}"
            )
        markdown_lines.append("")
    if request.dashboard.alerts:
        markdown_lines += ["## Active alerts"] + [f"- {alert}" for alert in request.dashboard.alerts] + [""]
    if request.risk_callouts:
        markdown_lines += ["## Risks"] + [f"- {risk}" for risk in request.risk_callouts] + [""]
    if request.opportunity_callouts:
        markdown_lines += ["## Opportunities"] + [f"- {item}" for item in request.opportunity_callouts] + [""]
    if manifest_hash:
        markdown_lines += [
            "## Evidence manifest",
            f"- Manifest hash: `{manifest_hash}`",
            f"- Sources counted: {len(request.evidence_manifest)}",
        ]

    markdown = "\n".join(markdown_lines).rstrip() + "\n"
    json_payload: dict[str, Any] = {
        "fund_name": request.fund_name,
        "reporting_period": request.reporting_period,
        "headline": headline,
        "coverage_summary": coverage_summary,
        "key_metrics": key_metrics,
        "peer_contexts": [ctx.model_dump(mode="json") for ctx in peer_contexts],
        "risk_callouts": list(request.risk_callouts),
        "opportunity_callouts": list(request.opportunity_callouts),
        "alerts": list(request.dashboard.alerts),
        "evidence_manifest": dict(request.evidence_manifest),
        "evidence_manifest_hash": manifest_hash,
    }
    return LPNarrativeReport(
        fund_name=request.fund_name,
        reporting_period=request.reporting_period,
        headline=headline,
        coverage_summary=coverage_summary,
        peer_context=peer_contexts,
        key_metrics=key_metrics,
        risk_callouts=list(request.risk_callouts),
        opportunity_callouts=list(request.opportunity_callouts),
        evidence_manifest_hash=manifest_hash,
        markdown=markdown,
        json_payload=json_payload,
    )


# ---------------------------------------------------------------------------
# LP Q&A workspace
# ---------------------------------------------------------------------------


class LPQuestion(BaseModel):
    """One LP question awaiting a sourced answer."""

    question_id: str
    text: str
    asked_by: str = ""
    asked_at: str = Field(default_factory=lambda: _now())


class LPAnswer(BaseModel):
    """Answer for an LP question with citations to approved evidence."""

    question_id: str
    answer: str
    citations: list[str] = Field(default_factory=list)
    metric_ids: list[str] = Field(default_factory=list)
    answered_by: str = ""
    answered_at: str = Field(default_factory=lambda: _now())
    answer_hash: str = ""


class LPQuestionWorkspace(BaseModel):
    """Q&A workspace constrained to verified metric records."""

    fund_name: str
    reporting_period: str
    approved_records: list[MetricRecord] = Field(default_factory=list)
    questions: list[LPQuestion] = Field(default_factory=list)
    answers: dict[str, LPAnswer] = Field(default_factory=dict)
    history_hashes: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        unverified = [r.metric_id for r in self.approved_records if not r.is_verified]
        if unverified:
            raise ValueError(
                "LP Q&A workspace only accepts verified records; "
                f"unverified: {', '.join(sorted(set(unverified)))}"
            )

    def ask(self, question: LPQuestion) -> LPQuestion:
        self.questions.append(question)
        return question

    def answer(
        self,
        *,
        question_id: str,
        answered_by: str,
        metric_ids: Iterable[str] | None = None,
        free_text: str = "",
    ) -> LPAnswer:
        question = self._find_question(question_id)
        ids = [m.strip().upper() for m in (metric_ids or []) if m.strip()]
        cited_records = [r for r in self.approved_records if r.metric_id in set(ids)]
        missing_ids = sorted(set(ids) - {r.metric_id for r in cited_records})
        if missing_ids:
            raise ValueError(
                f"No approved metric records found for citations: {', '.join(missing_ids)}"
            )
        if not ids:
            raise ValueError(
                "LP answers require at least one approved metric citation; "
                "free text may only provide context around cited records"
            )

        answer_text_parts: list[str] = []
        if free_text.strip():
            answer_text_parts.append(free_text.strip())
        if cited_records:
            for record in cited_records:
                answer_text_parts.append(
                    f"{record.metric_id} = {record.value} {record.unit} "
                    f"({record.period}, {record.verification_status})"
                )
        answer_text = "\n".join(answer_text_parts)
        citations = sorted({
            ref
            for record in cited_records
            for ref in record.evidence_refs
        })
        digest_input = "\n".join([
            question.question_id,
            answer_text,
            *citations,
        ])
        answer_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
        answer = LPAnswer(
            question_id=question.question_id,
            answer=answer_text,
            citations=citations,
            metric_ids=ids,
            answered_by=answered_by,
            answer_hash=answer_hash,
        )
        self.answers[question.question_id] = answer
        self.history_hashes.append(answer_hash)
        return answer

    def open_questions(self) -> list[LPQuestion]:
        return [q for q in self.questions if q.question_id not in self.answers]

    def export(self) -> dict[str, Any]:
        return {
            "fund_name": self.fund_name,
            "reporting_period": self.reporting_period,
            "questions": [q.model_dump(mode="json") for q in self.questions],
            "answers": {qid: ans.model_dump(mode="json") for qid, ans in self.answers.items()},
            "history_hashes": list(self.history_hashes),
        }

    def _find_question(self, question_id: str) -> LPQuestion:
        for question in self.questions:
            if question.question_id == question_id:
                return question
        raise KeyError(f"Unknown LP question: {question_id}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "LPAnswer",
    "LPNarrativeReport",
    "LPNarrativeRequest",
    "LPQuestion",
    "LPQuestionWorkspace",
    "NarrativeFormat",
    "generate_lp_narrative",
]
