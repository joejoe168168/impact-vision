"""Tests for the canonical impact metric-record contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from openharness.impact.metric_records import (
    metric_record_from_value,
    metric_records_from_reported_metrics,
    metric_records_to_reported_metrics,
    validate_metric_record,
    validate_metric_records,
)
from openharness.impact.models import MetricRecord


def test_metric_record_valid_contract() -> None:
    record = MetricRecord(
        metric_id="oi4112",
        value="150 tCO2e",
        unit="tCO2e",
        period="FY2025",
        source="investee-upload.csv",
        owner="cfo@example.test",
        quality_score=84,
        verification_status="management_verified",
        source_type="investee_submission",
        evidence_refs=["evidence://doc-1", "evidence://doc-1", " "],
    )

    assert record.metric_id == "OI4112"
    assert record.quality_band == "high"
    assert record.is_verified is True
    assert record.evidence_refs == ["evidence://doc-1"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("metric_id", "BADID"),
        ("unit", ""),
        ("period", " "),
        ("source", ""),
        ("owner", ""),
        ("quality_score", 101),
        ("verification_status", "approved"),
        ("source_type", "spreadsheet"),
    ],
)
def test_metric_record_rejects_invalid_required_fields(field: str, value: object) -> None:
    payload = {
        "metric_id": "PI4060",
        "value": 25000,
        "unit": "people",
        "period": "Q1 2026",
        "source": "portal",
        "owner": "impact analyst",
        "quality_score": 75,
        "verification_status": "self_reported",
        "source_type": "manual_entry",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        MetricRecord.model_validate(payload)


def test_metric_record_rejects_empty_value() -> None:
    with pytest.raises(ValidationError):
        metric_record_from_value(
            metric_id="PI4060",
            value=" ",
            unit="people",
            period="FY2025",
            source="portal",
            owner="analyst",
        )


def test_validate_metric_record_returns_errors_without_raising() -> None:
    record, errors = validate_metric_record({
        "metric_id": "bad",
        "value": "100",
        "unit": "count",
        "period": "FY2025",
        "source": "portal",
        "owner": "analyst",
        "quality_score": 60,
    })

    assert record is None
    assert any("metric_id" in err for err in errors)


def test_validate_metric_records_preserves_valid_rows() -> None:
    records, errors = validate_metric_records([
        {
            "metric_id": "PI4060",
            "value": "1000",
            "unit": "people",
            "period": "FY2025",
            "source": "portal",
            "owner": "analyst",
            "quality_score": 60,
        },
        {
            "metric_id": "NOPE",
            "value": "1000",
            "unit": "people",
            "period": "FY2025",
            "source": "portal",
            "owner": "analyst",
            "quality_score": 60,
        },
    ])

    assert [record.metric_id for record in records] == ["PI4060"]
    assert errors and errors[0].startswith("record[1]")


def test_reported_metrics_conversion_roundtrip() -> None:
    records, warnings = metric_records_from_reported_metrics(
        {"oi4112": "150 tCO2e", "BADID": "ignored"},
        unit_by_metric={"OI4112": "tCO2e"},
        period="FY2025",
        source="legacy import",
        owner="analyst",
        quality_score=55,
    )

    assert len(records) == 1
    assert records[0].metric_id == "OI4112"
    assert records[0].unit == "tCO2e"
    assert records[0].quality_band == "moderate"
    assert warnings == ["Ignored invalid metric ID: BADID"]
    assert metric_records_to_reported_metrics(records) == {"OI4112": "150 tCO2e"}


def test_reported_metrics_conversion_marks_missing_units() -> None:
    records, warnings = metric_records_from_reported_metrics(
        {"PI4060": "25000"},
        period="current",
        source="quick entry",
        owner="analyst",
    )

    assert warnings == []
    assert records[0].unit == "unspecified"
    assert records[0].verification_status == "self_reported"
