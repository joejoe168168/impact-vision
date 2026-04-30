"""Tests for reusable metric-record data-quality scoring."""

from __future__ import annotations

import pytest

from openharness.impact.data_quality import (
    apply_quality_assessment,
    assess_metric_record_quality,
)
from openharness.impact.models import MetricRecord


def _record(**overrides: object) -> MetricRecord:
    payload = {
        "metric_id": "OI4112",
        "value": "150 tCO2e",
        "unit": "tCO2e",
        "period": "FY2026",
        "source": "audited-ghg-inventory.pdf",
        "owner": "cfo@example.test",
        "quality_score": 60,
        "verification_status": "third_party_verified",
        "source_type": "audited_statement",
        "evidence_refs": ["evidence://ghg-inventory"],
    }
    payload.update(overrides)
    return MetricRecord.model_validate(payload)


def test_assess_metric_record_quality_scores_high_quality_records() -> None:
    assessment = assess_metric_record_quality(_record(), current_year=2026)

    assert assessment.metric_id == "OI4112"
    assert assessment.overall_score >= 90
    assert assessment.quality_band == "high"
    assert assessment.score_for("completeness") == 100
    assert assessment.score_for("verification_level") == 92
    assert assessment.recommendations == []


def test_assess_metric_record_quality_flags_incomplete_stale_records() -> None:
    assessment = assess_metric_record_quality(
        _record(
            value="unknown",
            unit="unspecified",
            period="FY2022",
            source_type="manual_entry",
            verification_status="unverified",
            evidence_refs=[],
        ),
        current_year=2026,
    )

    assert assessment.overall_score < 50
    assert assessment.quality_band == "low"
    assert assessment.score_for("completeness") == 45
    assert assessment.score_for("recency") == 40
    assert assessment.score_for("consistency") == 10
    assert len(assessment.recommendations) >= 4


def test_apply_quality_assessment_returns_updated_record_copy() -> None:
    record = _record(quality_score=1)
    updated = apply_quality_assessment(record, current_year=2026)

    assert record.quality_score == 1
    assert updated.quality_score >= 90
    assert updated.metric_id == record.metric_id


def test_assess_metric_record_quality_normalizes_custom_weights() -> None:
    assessment = assess_metric_record_quality(
        _record(period="FY2020"),
        current_year=2026,
        weights={
            "completeness": 1,
            "recency": 9,
            "consistency": 0,
            "source_type": 0,
            "verification_level": 0,
        },
    )

    assert assessment.overall_score < 40
    assert assessment.score_for("recency") == 20


def test_assess_metric_record_quality_rejects_incomplete_weights() -> None:
    with pytest.raises(ValueError, match="Missing data-quality rubric weights"):
        assess_metric_record_quality(
            _record(),
            weights={
                "completeness": 1,
                "recency": 1,
            },  # type: ignore[arg-type]
        )
