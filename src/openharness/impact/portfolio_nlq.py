"""Natural-language portfolio query engine (v3 Track 9.2).

Strict, **approved-data-only** query engine: every answer cites the
:class:`MetricRecord` rows it used and exposes the structured intent
that produced the answer, so the user can verify what was computed.

Supported intents:

* ``average`` — mean of a metric across approved records.
* ``total``   — sum of a metric across approved records.
* ``top_n``   — top-N companies/owners by a metric value.
* ``coverage``— share of approved records out of supplied corpora.
* ``compare`` — compare two metric IDs (mean/total).

The engine is offline / deterministic: it doesn't call an LLM. Higher
layers can wrap it in an LLM step under
:mod:`openharness.impact.evidence_workflow` review.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field

from openharness.impact.models import MetricRecord


QueryIntentType = Literal["average", "total", "top_n", "coverage", "compare", "unknown"]


class ApprovedDataPolicy(BaseModel):
    """Policy that gates which records the engine is allowed to use."""

    require_verified: bool = True
    minimum_quality_score: int = Field(ge=0, le=100, default=0)
    allow_unverified_with_warning: bool = False


class QueryIntent(BaseModel):
    """Structured intent extracted from a natural-language question."""

    type: QueryIntentType
    metric_id: str = ""
    secondary_metric_id: str = ""
    top_n: int = 0
    period: str = ""
    rationale: str = ""


class QueryAnswer(BaseModel):
    """Answer for a portfolio NL query, with citations."""

    question: str
    intent: QueryIntent
    answer_text: str
    numeric_answer: float | None = None
    citations: list[str] = Field(default_factory=list)
    metric_record_ids: list[str] = Field(default_factory=list)
    answered_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    governance_log_id: str = ""
    warnings: list[str] = Field(default_factory=list)


_METRIC_ID_RE = re.compile(r"\b(PI|OI|OD|FP|PD)\d{4}\b", re.IGNORECASE)
_TOP_N_RE = re.compile(r"top\s*(\d+)", re.IGNORECASE)
_PERIOD_RE = re.compile(r"(FY|CY|Q[1-4]\s*)?(20\d{2})")


def parse_intent(question: str) -> QueryIntent:
    """Parse a question into a structured :class:`QueryIntent`."""
    cleaned = question.strip()
    lowered = cleaned.lower()
    metric_ids = [m.group(0).upper() for m in _METRIC_ID_RE.finditer(cleaned)]
    primary = metric_ids[0] if metric_ids else ""
    secondary = metric_ids[1] if len(metric_ids) > 1 else ""
    period_match = _PERIOD_RE.search(cleaned)
    period = period_match.group(0) if period_match else ""

    intent: QueryIntent
    if "compare" in lowered and len(metric_ids) >= 2:
        intent = QueryIntent(
            type="compare",
            metric_id=primary,
            secondary_metric_id=secondary,
            period=period,
            rationale="Question contains 'compare' and two metric IDs.",
        )
    elif "coverage" in lowered:
        intent = QueryIntent(
            type="coverage",
            metric_id=primary,
            period=period,
            rationale="Question contains 'coverage'.",
        )
    elif "top" in lowered and primary:
        match = _TOP_N_RE.search(cleaned)
        n = int(match.group(1)) if match else 5
        intent = QueryIntent(
            type="top_n",
            metric_id=primary,
            top_n=n,
            period=period,
            rationale=f"Question requests top-{n} by metric.",
        )
    elif any(token in lowered for token in ("total", "sum")) and primary:
        intent = QueryIntent(
            type="total",
            metric_id=primary,
            period=period,
            rationale="Question contains a 'total' / 'sum' phrase.",
        )
    elif any(token in lowered for token in ("average", "mean", "avg")) and primary:
        intent = QueryIntent(
            type="average",
            metric_id=primary,
            period=period,
            rationale="Question contains 'average' / 'mean'.",
        )
    elif primary:
        intent = QueryIntent(
            type="average",
            metric_id=primary,
            period=period,
            rationale="Default to average when a single metric is referenced.",
        )
    else:
        intent = QueryIntent(
            type="unknown",
            rationale="Could not match a supported intent in the question.",
        )
    return intent


class PortfolioNLQEngine(BaseModel):
    """Approved-data-only NL query engine for a portfolio of metric records."""

    fund_name: str = "default"
    records: list[MetricRecord] = Field(default_factory=list)
    policy: ApprovedDataPolicy = Field(default_factory=ApprovedDataPolicy)

    def add_records(self, records: Iterable[MetricRecord]) -> None:
        self.records.extend(list(records))

    def _eligible(
        self,
        intent: QueryIntent,
        metric_id: str,
        *,
        include_unverified: bool = False,
    ) -> tuple[list[MetricRecord], list[str]]:
        warnings: list[str] = []
        candidates = [r for r in self.records if r.metric_id == metric_id]
        if intent.period:
            candidates = [r for r in candidates if intent.period.lower() in r.period.lower()]
        allow_unverified = (
            not self.policy.require_verified
            or (include_unverified and self.policy.allow_unverified_with_warning)
        )
        if self.policy.require_verified and not allow_unverified:
            verified = [r for r in candidates if r.is_verified]
            dropped = len(candidates) - len(verified)
            if dropped:
                warnings.append(
                    f"{dropped} unverified record(s) excluded by ApprovedDataPolicy"
                )
                if include_unverified and not self.policy.allow_unverified_with_warning:
                    warnings.append(
                        "include_unverified was ignored because "
                        "allow_unverified_with_warning is false"
                    )
            candidates = verified
        else:
            unverified = sum(1 for r in candidates if not r.is_verified)
            if unverified:
                warnings.append(
                    f"Answer includes {unverified} unverified record(s)"
                )
        if self.policy.minimum_quality_score:
            qualified = [r for r in candidates if r.quality_score >= self.policy.minimum_quality_score]
            dropped = len(candidates) - len(qualified)
            if dropped:
                warnings.append(
                    f"{dropped} record(s) below quality threshold "
                    f"{self.policy.minimum_quality_score}"
                )
            candidates = qualified
        return candidates, warnings

    def answer(
        self,
        question: str,
        *,
        include_unverified: bool = False,
        governance_log_id: str | None = None,
    ) -> QueryAnswer:
        intent = parse_intent(question)
        warnings: list[str] = []
        numeric_answer: float | None = None
        cited_records: list[MetricRecord] = []
        answer_text = ""

        if intent.type == "unknown":
            answer_text = "Unable to parse the question into a supported intent."
        elif intent.type == "coverage":
            total = len(self.records)
            verified = sum(1 for r in self.records if r.is_verified)
            if intent.metric_id:
                total = sum(1 for r in self.records if r.metric_id == intent.metric_id)
                verified = sum(
                    1
                    for r in self.records
                    if r.metric_id == intent.metric_id and r.is_verified
                )
            if total == 0:
                answer_text = "No records found for the requested coverage scope."
            else:
                numeric_answer = round(100.0 * verified / total, 2)
                answer_text = (
                    f"Approved-record coverage: {verified}/{total} "
                    f"({numeric_answer:.2f}%)."
                )
        elif intent.type == "compare" and intent.secondary_metric_id:
            primary, w1 = self._eligible(intent, intent.metric_id, include_unverified=include_unverified)
            secondary, w2 = self._eligible(intent, intent.secondary_metric_id, include_unverified=include_unverified)
            warnings.extend(w1 + w2)
            cited_records = primary + secondary
            primary_values = [_to_float(r.value) for r in primary]
            secondary_values = [_to_float(r.value) for r in secondary]
            primary_numeric = [v for v in primary_values if v is not None]
            secondary_numeric = [v for v in secondary_values if v is not None]
            if primary_numeric and secondary_numeric:
                primary_avg = mean(primary_numeric)
                secondary_avg = mean(secondary_numeric)
                numeric_answer = round(primary_avg - secondary_avg, 4)
                answer_text = (
                    f"Avg {intent.metric_id} = {primary_avg:.4f}; "
                    f"avg {intent.secondary_metric_id} = {secondary_avg:.4f}; "
                    f"delta = {numeric_answer:.4f}."
                )
            else:
                answer_text = "Insufficient numeric data to compare these metrics."
        else:
            cited_records, w = self._eligible(intent, intent.metric_id, include_unverified=include_unverified)
            warnings.extend(w)
            numeric_values = [_to_float(r.value) for r in cited_records]
            numeric = [v for v in numeric_values if v is not None]
            if intent.type == "average" and numeric:
                numeric_answer = round(mean(numeric), 4)
                answer_text = (
                    f"Average {intent.metric_id} across "
                    f"{len(cited_records)} approved record(s): {numeric_answer:.4f}."
                )
            elif intent.type == "total" and numeric:
                numeric_answer = round(sum(numeric), 4)
                answer_text = (
                    f"Total {intent.metric_id} across "
                    f"{len(cited_records)} approved record(s): {numeric_answer:.4f}."
                )
            elif intent.type == "top_n" and cited_records:
                ranked = sorted(
                    cited_records,
                    key=lambda r: _to_float(r.value) or float("-inf"),
                    reverse=True,
                )[: intent.top_n or 5]
                cited_records = ranked
                lines = [
                    f"{idx + 1}. {r.owner}: {r.value} {r.unit} ({r.period})"
                    for idx, r in enumerate(ranked)
                ]
                answer_text = (
                    f"Top {len(ranked)} owner(s) by {intent.metric_id}:\n"
                    + "\n".join(lines)
                )
            else:
                answer_text = (
                    f"No numeric approved data found for {intent.metric_id}"
                    f"{' in ' + intent.period if intent.period else ''}."
                )

        citations = sorted({
            ref
            for r in cited_records
            for ref in r.evidence_refs
        })
        digest = hashlib.sha256(
            f"{question}|{intent.model_dump_json()}|{answer_text}|{citations}".encode("utf-8")
        ).hexdigest()
        log_id = governance_log_id or f"nlq_{digest[:12]}"
        return QueryAnswer(
            question=question,
            intent=intent,
            answer_text=answer_text,
            numeric_answer=numeric_answer,
            citations=citations,
            metric_record_ids=[r.metric_id for r in cited_records],
            governance_log_id=log_id,
            warnings=warnings,
        )


def _to_float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


__all__ = [
    "ApprovedDataPolicy",
    "PortfolioNLQEngine",
    "QueryAnswer",
    "QueryIntent",
    "QueryIntentType",
    "parse_intent",
]
