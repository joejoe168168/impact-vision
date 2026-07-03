"""Decision-useful evidence chains for 5-Dimension scores.

The core 5D scorer intentionally stays compact: it returns scores, gaps,
notes, and provenance. Fund managers need a second view that explains why the
score was produced and which claims/metrics support it. This module builds
that view without changing the scoring algorithm.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.database import MetricStore
from openharness.impact.models import Assessment, DimensionScore, ImpactClaim, MetricRecord


ScoreProvenance = Literal["evidence-based", "partial", "estimated"]


class MetricLink(BaseModel):
    """Metric evidence feeding one 5D dimension."""

    metric_id: str
    metric_name: str = ""
    value: str = ""
    unit: str = ""
    source: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    verification_status: str = "unverified"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    is_estimate: bool = False
    estimate_note: str = Field(
        default="",
        description="Estimate-disclosure badge (methodology) when the value is modelled, not measured",
    )


class ClaimLink(BaseModel):
    """Claim evidence feeding one 5D dimension."""

    text: str
    source_page: int | None = None
    mapped_metrics: list[str] = Field(default_factory=list)
    sdg_targets: list[str] = Field(default_factory=list)
    evidence_level: int = Field(ge=1, le=5, default=1)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    supported_by_reported_metric: bool = False


class EvidenceChainNode(BaseModel):
    """Portable explanation node for one 5D dimension."""

    dimension: str
    score: float
    score_pct: int = Field(ge=0, le=100)
    provenance: ScoreProvenance
    metric_links: list[MetricLink] = Field(default_factory=list)
    claim_links: list[ClaimLink] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    explanation: str = ""
    alternatives_considered: str = ""


_DIMENSION_FIELDS: dict[str, tuple[str, ...]] = {
    "what": ("what",),
    "who": ("who",),
    "how_much": ("how_much_scale", "how_much_depth", "how_much_duration"),
    "contribution": ("contribution_depth", "contribution_duration"),
    "risk": ("risk",),
}


def _metric_value_as_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return str(value)
    return "" if value is None else str(value)


def _record_index(metric_records: list[MetricRecord | dict[str, Any]] | None) -> dict[str, MetricRecord]:
    indexed: dict[str, MetricRecord] = {}
    for item in metric_records or []:
        try:
            record = item if isinstance(item, MetricRecord) else MetricRecord.model_validate(item)
        except Exception:
            continue
        indexed[record.metric_id] = record
    return indexed


def _claim_objects(claims: list[ImpactClaim | dict[str, Any]] | None) -> list[ImpactClaim]:
    out: list[ImpactClaim] = []
    for item in claims or []:
        try:
            out.append(item if isinstance(item, ImpactClaim) else ImpactClaim.model_validate(item))
        except Exception:
            continue
    return out


def _dimension_metric_ids(store: MetricStore, dimension_key: str) -> set[str]:
    ids: set[str] = set()
    for field_name in _DIMENSION_FIELDS[dimension_key]:
        metrics = [m for m in store.all_metrics() if getattr(m.dimensions, field_name, False)]
        ids.update(m.id for m in metrics)
    return ids


def _metric_link(metric_id: str, value: Any, store: MetricStore, records: dict[str, MetricRecord]) -> MetricLink:
    metric = store.get(metric_id)
    record = records.get(metric_id)
    if record is not None:
        from openharness.impact.metric_records import estimate_disclosure_label

        return MetricLink(
            metric_id=metric_id,
            metric_name=metric.name if metric else metric_id,
            value=_metric_value_as_text(record.value),
            unit=record.unit,
            source=record.source,
            evidence_refs=record.evidence_refs,
            verification_status=record.verification_status,
            confidence=round(record.quality_score / 100, 2),
            is_estimate=record.is_estimate,
            estimate_note=estimate_disclosure_label(record),
        )
    return MetricLink(
        metric_id=metric_id,
        metric_name=metric.name if metric else metric_id,
        value=_metric_value_as_text(value),
        source="reported_metrics",
        verification_status="unverified",
        confidence=0.55,
    )


def _claim_link(claim: ImpactClaim, reported_ids: set[str]) -> ClaimLink:
    mapped = [m for m in claim.mapped_metrics if m in reported_ids]
    return ClaimLink(
        text=claim.text,
        source_page=claim.source_page,
        mapped_metrics=claim.mapped_metrics,
        sdg_targets=claim.mapped_sdg_targets,
        evidence_level=claim.evidence_strength,
        confidence=claim.confidence,
        supported_by_reported_metric=bool(mapped),
    )


def _dimension_score(assessment: Assessment, dimension_key: str) -> DimensionScore:
    fd = assessment.five_dimensions
    if fd is None:
        raise ValueError("assessment must include five_dimensions")
    return {
        "what": fd.what,
        "who": fd.who,
        "how_much": fd.how_much,
        "contribution": fd.contribution,
        "risk": fd.risk,
    }[dimension_key]


def _explanation(score: DimensionScore, metric_count: int, claim_count: int) -> str:
    if metric_count:
        return (
            f"{score.dimension} scored {score.score}/5 based on {metric_count} reported "
            f"metric(s), {claim_count} linked claim(s), and the current scoring gaps."
        )
    return (
        f"{score.dimension} scored {score.score}/5 from sector and description signals only; "
        "no reported metric directly supports this dimension."
    )


def _alternatives(score: DimensionScore) -> str:
    if score.gaps:
        return "Score could improve by reporting and evidencing: " + "; ".join(score.gaps[:3])
    if score.provenance != "evidence-based":
        return "Score could improve with third-party verified metric records and stronger source evidence."
    return "No higher-scoring alternative identified from the available inputs."


class EvidenceChainRenderer:
    """Render 5D evidence chains from an assessment and optional source records."""

    def __init__(self, store: MetricStore) -> None:
        self.store = store

    def render_dimension(
        self,
        dimension_key: str,
        assessment: Assessment,
        *,
        claims: list[ImpactClaim | dict[str, Any]] | None = None,
        metric_records: list[MetricRecord | dict[str, Any]] | None = None,
    ) -> EvidenceChainNode:
        score = _dimension_score(assessment, dimension_key)
        records = _record_index(metric_records)
        reported = assessment.company.reported_metrics
        reported_ids = set(reported.keys())
        dimension_ids = _dimension_metric_ids(self.store, dimension_key)

        metric_links = [
            _metric_link(metric_id, value, self.store, records)
            for metric_id, value in sorted(reported.items())
            if metric_id in dimension_ids
        ]
        claim_links = [
            _claim_link(claim, reported_ids)
            for claim in _claim_objects(claims or assessment.impact_claims)
            if set(claim.mapped_metrics) & dimension_ids or dimension_key == "risk" and claim.category == "risk"
        ]
        return EvidenceChainNode(
            dimension=score.dimension,
            score=score.score,
            score_pct=int(round(score.score / 5 * 100)),
            provenance=score.provenance,
            metric_links=metric_links,
            claim_links=claim_links,
            gaps=score.gaps,
            explanation=_explanation(score, len(metric_links), len(claim_links)),
            alternatives_considered=_alternatives(score),
        )

    def render_as_tree_json(
        self,
        assessment: Assessment,
        *,
        claims: list[ImpactClaim | dict[str, Any]] | None = None,
        metric_records: list[MetricRecord | dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        return {
            key: self.render_dimension(
                key,
                assessment,
                claims=claims,
                metric_records=metric_records,
            ).model_dump(mode="json")
            for key in ("what", "who", "how_much", "contribution", "risk")
        }


__all__ = [
    "ClaimLink",
    "EvidenceChainNode",
    "EvidenceChainRenderer",
    "MetricLink",
    "ScoreProvenance",
]
