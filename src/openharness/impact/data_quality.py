"""Reusable data-quality scoring for canonical impact metric records."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.models import MetricRecord


DataQualityDimension = Literal[
    "completeness",
    "recency",
    "consistency",
    "source_type",
    "verification_level",
]

_PLACEHOLDER_VALUES = {"n/a", "na", "none", "unknown", "tbd", "-", "--"}
_NUMERIC_RE = re.compile(r"-?\d+(?:\.\d+)?")


class DataQualityDimensionScore(BaseModel):
    """One dimension of the data-quality rubric."""

    dimension: DataQualityDimension
    score: int = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    rationale: str
    flags: list[str] = Field(default_factory=list)


class DataQualityAssessment(BaseModel):
    """Weighted quality score and diagnostics for a canonical metric record."""

    metric_id: str
    overall_score: int = Field(ge=0, le=100)
    quality_band: Literal["low", "moderate", "high"]
    dimension_scores: list[DataQualityDimensionScore]
    recommendations: list[str] = Field(default_factory=list)

    def score_for(self, dimension: DataQualityDimension) -> int:
        """Return the score for one rubric dimension."""
        for item in self.dimension_scores:
            if item.dimension == dimension:
                return item.score
        raise KeyError(dimension)


DEFAULT_RUBRIC_WEIGHTS: dict[DataQualityDimension, float] = {
    "completeness": 0.30,
    "recency": 0.20,
    "consistency": 0.20,
    "source_type": 0.15,
    "verification_level": 0.15,
}


def assess_metric_record_quality(
    record: MetricRecord,
    *,
    current_year: int | None = None,
    weights: dict[DataQualityDimension, float] | None = None,
) -> DataQualityAssessment:
    """Assess data quality for a canonical metric record.

    The rubric scores completeness, recency, consistency, source provenance,
    and verification level, then returns a weighted 0-100 score.
    """
    active_weights = _normalize_weights(weights or DEFAULT_RUBRIC_WEIGHTS)
    current_year = current_year or datetime.now(timezone.utc).year
    dimensions = [
        _score_completeness(record, active_weights["completeness"]),
        _score_recency(record, current_year, active_weights["recency"]),
        _score_consistency(record, active_weights["consistency"]),
        _score_source_type(record, active_weights["source_type"]),
        _score_verification_level(record, active_weights["verification_level"]),
    ]
    overall = round(sum(item.score * item.weight for item in dimensions))
    recommendations = _recommendations(dimensions)
    return DataQualityAssessment(
        metric_id=record.metric_id,
        overall_score=overall,
        quality_band=_quality_band(overall),
        dimension_scores=dimensions,
        recommendations=recommendations,
    )


def apply_quality_assessment(
    record: MetricRecord,
    *,
    current_year: int | None = None,
    weights: dict[DataQualityDimension, float] | None = None,
) -> MetricRecord:
    """Return a copy of ``record`` with ``quality_score`` set by the rubric."""
    assessment = assess_metric_record_quality(
        record,
        current_year=current_year,
        weights=weights,
    )
    return record.model_copy(update={"quality_score": assessment.overall_score})


def _normalize_weights(weights: dict[DataQualityDimension, float]) -> dict[DataQualityDimension, float]:
    missing = [key for key in DEFAULT_RUBRIC_WEIGHTS if key not in weights]
    if missing:
        raise ValueError(f"Missing data-quality rubric weights: {', '.join(missing)}")
    total = sum(float(weights[key]) for key in DEFAULT_RUBRIC_WEIGHTS)
    if total <= 0:
        raise ValueError("Data-quality rubric weights must sum to a positive value")
    return {key: float(weights[key]) / total for key in DEFAULT_RUBRIC_WEIGHTS}


def _score_completeness(record: MetricRecord, weight: float) -> DataQualityDimensionScore:
    flags: list[str] = []
    score = 100
    if record.unit.lower() in {"unspecified", "unknown", "n/a", "na"}:
        score -= 25
        flags.append("unit_unspecified")
    if not record.evidence_refs:
        score -= 30
        flags.append("missing_evidence")
    if record.source_type == "proxy_estimate" or record.verification_status == "proxy_estimate":
        score -= 15
        flags.append("proxy_value")
    return DataQualityDimensionScore(
        dimension="completeness",
        score=max(0, score),
        weight=weight,
        rationale="Required fields, explicit units, evidence references, and proxy status.",
        flags=flags,
    )


def _score_recency(record: MetricRecord, current_year: int, weight: float) -> DataQualityDimensionScore:
    years = [int(match) for match in re.findall(r"(?:FY|CY|Q[1-4]\s*)?(20\d{2})", record.period)]
    if not years:
        return DataQualityDimensionScore(
            dimension="recency",
            score=45,
            weight=weight,
            rationale="Reporting period does not include a recognizable year.",
            flags=["period_year_missing"],
        )
    age = max(0, current_year - max(years))
    if age == 0:
        score = 100
    elif age == 1:
        score = 85
    elif age == 2:
        score = 65
    elif age <= 4:
        score = 40
    else:
        score = 20
    flags = ["stale_period"] if age >= 2 else []
    return DataQualityDimensionScore(
        dimension="recency",
        score=score,
        weight=weight,
        rationale=f"Reporting period is {age} year(s) behind the assessment year.",
        flags=flags,
    )


def _score_consistency(record: MetricRecord, weight: float) -> DataQualityDimensionScore:
    value_text = str(record.value).strip()
    flags: list[str] = []
    score = 100
    if value_text.lower() in _PLACEHOLDER_VALUES:
        return DataQualityDimensionScore(
            dimension="consistency",
            score=10,
            weight=weight,
            rationale="Metric value is a placeholder.",
            flags=["placeholder_value"],
        )
    if _looks_quantitative_unit(record.unit) and _NUMERIC_RE.search(value_text.replace(",", "")) is None:
        score -= 45
        flags.append("non_numeric_value")
    if record.unit.lower() not in {"qualitative", "text"} and value_text.lower().endswith("%") and "%" not in record.unit:
        score -= 10
        flags.append("value_unit_mismatch")
    return DataQualityDimensionScore(
        dimension="consistency",
        score=max(0, score),
        weight=weight,
        rationale="Value shape is consistent with the stated unit and avoids placeholders.",
        flags=flags,
    )


def _score_source_type(record: MetricRecord, weight: float) -> DataQualityDimensionScore:
    scores = {
        "audited_statement": 100,
        "system_import": 88,
        "investee_submission": 78,
        "document_extraction": 68,
        "manual_entry": 58,
        "proxy_estimate": 42,
    }
    score = scores[record.source_type]
    flags = ["weak_source_type"] if score < 60 else []
    return DataQualityDimensionScore(
        dimension="source_type",
        score=score,
        weight=weight,
        rationale=f"Source type is {record.source_type}.",
        flags=flags,
    )


def _score_verification_level(record: MetricRecord, weight: float) -> DataQualityDimensionScore:
    scores = {
        "audited": 100,
        "third_party_verified": 92,
        "management_verified": 80,
        "self_reported": 60,
        "proxy_estimate": 45,
        "unverified": 35,
    }
    score = scores[record.verification_status]
    flags = ["not_verified"] if score < 70 else []
    return DataQualityDimensionScore(
        dimension="verification_level",
        score=score,
        weight=weight,
        rationale=f"Verification status is {record.verification_status}.",
        flags=flags,
    )


def _looks_quantitative_unit(unit: str) -> bool:
    text = unit.lower()
    cues = (
        "%",
        "amount",
        "count",
        "days",
        "eur",
        "hours",
        "kg",
        "kwh",
        "mwh",
        "number",
        "people",
        "tco2e",
        "ton",
        "usd",
    )
    return any(cue in text for cue in cues)


def _quality_band(score: int) -> Literal["low", "moderate", "high"]:
    if score >= 80:
        return "high"
    if score >= 50:
        return "moderate"
    return "low"


def _recommendations(dimensions: list[DataQualityDimensionScore]) -> list[str]:
    recs: list[str] = []
    flags = {flag for item in dimensions for flag in item.flags}
    if "unit_unspecified" in flags:
        recs.append("Add the explicit reporting unit before LP or assurance use.")
    if "missing_evidence" in flags:
        recs.append("Attach source evidence such as an upload, system export, or audited statement.")
    if "period_year_missing" in flags or "stale_period" in flags:
        recs.append("Refresh the reporting period or document why stale data is acceptable.")
    if "placeholder_value" in flags or "non_numeric_value" in flags:
        recs.append("Replace placeholders or inconsistent values with measured data.")
    if "weak_source_type" in flags or "not_verified" in flags:
        recs.append("Move the metric through management or third-party review.")
    return recs


__all__ = [
    "DEFAULT_RUBRIC_WEIGHTS",
    "DataQualityAssessment",
    "DataQualityDimension",
    "DataQualityDimensionScore",
    "apply_quality_assessment",
    "assess_metric_record_quality",
]
