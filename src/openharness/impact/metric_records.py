"""Canonical metric-record helpers for investee collection and reporting."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from openharness.impact.models import MetricRecord
from openharness.tools.impact.common import normalize_metric_map


def validate_metric_record(data: MetricRecord | dict[str, Any]) -> tuple[MetricRecord | None, list[str]]:
    """Validate one metric record and return ``(record, errors)``.

    This helper keeps collection/import flows non-throwing while preserving the
    stricter Pydantic contract for code paths that want exceptions directly.
    """
    if isinstance(data, MetricRecord):
        return data, []
    try:
        return MetricRecord.model_validate(data), []
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        ]
        return None, errors


def validate_metric_records(
    records: list[MetricRecord | dict[str, Any]],
) -> tuple[list[MetricRecord], list[str]]:
    """Validate multiple metric records, preserving valid rows and row-level errors."""
    valid: list[MetricRecord] = []
    errors: list[str] = []
    for idx, item in enumerate(records):
        record, item_errors = validate_metric_record(item)
        if record is not None:
            valid.append(record)
        else:
            errors.extend(f"record[{idx}] {err}" for err in item_errors)
    return valid, errors


def metric_record_from_value(
    *,
    metric_id: str,
    value: Any,
    unit: str,
    period: str,
    source: str,
    owner: str,
    quality_score: int = 60,
    verification_status: str = "self_reported",
    source_type: str = "manual_entry",
    evidence_refs: list[str] | None = None,
    notes: str = "",
) -> MetricRecord:
    """Build a canonical metric record from a single reported metric value."""
    return MetricRecord(
        metric_id=metric_id,
        value=value,
        unit=unit,
        period=period,
        source=source,
        owner=owner,
        quality_score=quality_score,
        verification_status=verification_status,
        source_type=source_type,
        evidence_refs=evidence_refs or [],
        notes=notes,
    )


def metric_records_from_reported_metrics(
    reported_metrics: dict[str, Any] | None,
    *,
    unit_by_metric: dict[str, str] | None = None,
    period: str,
    source: str,
    owner: str,
    quality_score: int = 60,
    verification_status: str = "self_reported",
    source_type: str = "manual_entry",
) -> tuple[list[MetricRecord], list[str]]:
    """Convert legacy ``{metric_id: value}`` maps into canonical records.

    Invalid metric IDs are returned as warnings through ``normalize_metric_map``.
    Missing units are represented explicitly as ``"unspecified"`` so importers
    can retain the row while downstream review queues request unit completion.
    """
    normalized, warnings = normalize_metric_map(
        {str(k): "" if v is None else str(v) for k, v in (reported_metrics or {}).items()}
    )
    unit_by_metric = {k.strip().upper(): v for k, v in (unit_by_metric or {}).items()}
    rows: list[MetricRecord | dict[str, Any]] = []
    for metric_id, value in normalized.items():
        rows.append({
            "metric_id": metric_id,
            "value": value,
            "unit": unit_by_metric.get(metric_id, "unspecified"),
            "period": period,
            "source": source,
            "owner": owner,
            "quality_score": quality_score,
            "verification_status": verification_status,
            "source_type": source_type,
        })
    records, errors = validate_metric_records(rows)
    return records, warnings + errors


def metric_records_to_reported_metrics(records: list[MetricRecord]) -> dict[str, str]:
    """Convert canonical records back to the legacy map expected by current tools."""
    return {record.metric_id: str(record.value).strip() for record in records}


def estimate_disclosure_label(record: MetricRecord) -> str:
    """Return the estimate-disclosure badge for a record, or "" if measured.

    AI-estimated or modelled values must be labelled as estimates with the
    methodology disclosed wherever they surface (HTML report, XLSX, LP DDQ,
    LP Q&A) — presenting a modelled number as a measured one is a
    greenwashing exposure (EDCI / ILPA guidance).
    """
    if not record.is_estimate:
        return ""
    methodology = record.estimation_methodology.strip()
    if methodology:
        return f"ESTIMATE — {methodology}"
    return "ESTIMATE — methodology not disclosed"


def flag_undisclosed_estimates(records: list[MetricRecord]) -> list[str]:
    """Warn for estimated values whose methodology has not been disclosed."""
    return [
        f"{record.metric_id}: estimated value has no estimation_methodology — "
        "disclose the model/proxy used before LP or regulatory reporting"
        for record in records
        if record.is_estimate and not record.estimation_methodology.strip()
    ]


__all__ = [
    "estimate_disclosure_label",
    "flag_undisclosed_estimates",
    "metric_record_from_value",
    "metric_records_from_reported_metrics",
    "metric_records_to_reported_metrics",
    "validate_metric_record",
    "validate_metric_records",
]
