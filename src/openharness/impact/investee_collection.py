"""Investee data-collection questionnaire schema generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.database import MetricStore, get_metric_store
from openharness.impact.metric_records import metric_record_from_value
from openharness.impact.models import MetricRecord
from openharness.tools.impact.common import normalize_metric_ids, normalize_sector


SECTOR_METRIC_TEMPLATES: dict[str, list[str]] = {
    "energy": ["OI4112", "OI6697", "PI8706", "PI2822"],
    "fintech": ["PI4060", "PI2740", "OI6213", "OI1571"],
    "financial": ["PI4060", "PI2740", "OI6213", "OI1571"],
    "healthcare": ["PI4060", "PI3902", "PI7191", "OI8869"],
    "health": ["PI4060", "PI3902", "PI7191", "OI8869"],
    "agriculture": ["PI4060", "PI1290", "OI5409", "PI3687"],
    "education": ["PI4060", "PI2389", "PI2822", "OI8869"],
    "circular_economy": ["OI6697", "OI2535", "OI7920", "OI1479"],
    "livestock": ["PI4060", "OI4112", "OI6697", "PI3687"],
}


class ValidationRule(BaseModel):
    """One machine-readable validation rule for a questionnaire field."""

    rule: Literal["required", "metric_id", "number_or_text", "expected_unit", "evidence_required"]
    value: str | bool | None = None
    message: str = ""


class EvidenceRequirement(BaseModel):
    """Evidence guidance attached to one metric question."""

    required: bool = True
    examples: list[str] = Field(default_factory=list)


class QuestionnaireField(BaseModel):
    """A single metric input field shown to an investee."""

    metric_id: str
    label: str
    definition: str = ""
    guidance: str = ""
    unit: str = "unspecified"
    value_type: Literal["number", "text", "boolean", "currency", "percent"] = "text"
    required: bool = True
    evidence: EvidenceRequirement = Field(default_factory=EvidenceRequirement)
    validation_rules: list[ValidationRule] = Field(default_factory=list)
    sdg_goals: list[int] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)


class QuestionnaireSection(BaseModel):
    """A group of related investee questionnaire fields."""

    id: str
    title: str
    description: str = ""
    fields: list[QuestionnaireField] = Field(default_factory=list)


class InvesteeQuestionnaireSchema(BaseModel):
    """Portable questionnaire schema for web forms, CSV templates, or APIs."""

    sector: str
    reporting_period: str
    metric_count: int
    sections: list[QuestionnaireSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SubmissionMetricResponse(BaseModel):
    """One investee-submitted metric answer."""

    metric_id: str
    value: Any
    unit: str = "unspecified"
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str = ""


class SubmissionReviewEvent(BaseModel):
    """Review event for a collection submission."""

    status: Literal[
        "draft",
        "submitted",
        "flagged",
        "approved",
        "rejected",
        "resubmission_requested",
    ]
    actor: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    comments: str = ""


class CollectionSubmission(BaseModel):
    """Investee questionnaire submission with analyst review state."""

    submission_id: str
    company_name: str
    reporting_period: str
    submitted_by: str
    source: str = "investee portal"
    status: Literal[
        "draft",
        "submitted",
        "flagged",
        "approved",
        "rejected",
        "resubmission_requested",
    ] = "submitted"
    responses: list[SubmissionMetricResponse] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    submitted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    review_history: list[SubmissionReviewEvent] = Field(default_factory=list)


class SubmissionValidationResult(BaseModel):
    """Validation outcome for one collection submission."""

    is_valid: bool
    missing_required: list[str] = Field(default_factory=list)
    unknown_metrics: list[str] = Field(default_factory=list)
    evidence_missing: list[str] = Field(default_factory=list)
    unit_mismatches: list[str] = Field(default_factory=list)
    duplicate_metrics: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _section_id(label: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in label).strip("_")
    return cleaned or "general"


def _infer_unit(metric_reporting_format: str) -> str:
    text = (metric_reporting_format or "").strip()
    if not text:
        return "unspecified"
    lowered = text.lower()
    if "percent" in lowered or "%" in lowered:
        return "%"
    if "currency" in lowered or "usd" in lowered or "eur" in lowered:
        return "currency"
    if "number" in lowered or "decimal" in lowered or "integer" in lowered:
        return "number"
    if "yes/no" in lowered or "boolean" in lowered:
        return "yes/no"
    return text


def _infer_value_type(unit: str, metric_reporting_format: str) -> Literal[
    "number", "text", "boolean", "currency", "percent"
]:
    combined = f"{unit} {metric_reporting_format}".lower()
    if "yes/no" in combined or "boolean" in combined:
        return "boolean"
    if unit == "%":
        return "percent"
    if unit == "currency":
        return "currency"
    if unit == "number" or any(token in combined for token in ("decimal", "integer", "numeric")):
        return "number"
    return "text"


def _evidence_examples(metric_id: str, unit: str) -> list[str]:
    examples = ["source spreadsheet or system export", "management sign-off"]
    if unit in {"tCO2e", "kg", "MWh", "kWh", "number"} or metric_id.startswith("OI"):
        examples.insert(0, "calculation workbook")
    if unit == "currency":
        examples.insert(0, "financial statement extract")
    if unit == "%":
        examples.insert(0, "calculation denominator and numerator")
    return list(dict.fromkeys(examples))


def _field_for_metric(metric_id: str, store: MetricStore) -> QuestionnaireField | None:
    metric = store.get(metric_id)
    if metric is None:
        return None
    unit = _infer_unit(metric.reporting_format)
    value_type = _infer_value_type(unit, metric.reporting_format)
    evidence = EvidenceRequirement(
        required=True,
        examples=_evidence_examples(metric.id, unit),
    )
    return QuestionnaireField(
        metric_id=metric.id,
        label=metric.name,
        definition=metric.definition,
        guidance=metric.usage_guidance or metric.calculation or "",
        unit=unit,
        value_type=value_type,
        required=True,
        evidence=evidence,
        validation_rules=[
            ValidationRule(rule="required", value=True, message="Provide a value or mark the metric unavailable."),
            ValidationRule(rule="metric_id", value=metric.id, message=f"Metric must remain mapped to {metric.id}."),
            ValidationRule(rule="number_or_text", value=value_type, message=f"Expected {value_type} value."),
            ValidationRule(rule="expected_unit", value=unit, message=f"Expected unit: {unit}."),
            ValidationRule(rule="evidence_required", value=True, message="Attach or reference supporting evidence."),
        ],
        sdg_goals=metric.sdg_goals,
        dimensions=metric.dimensions.active_dimensions,
    )


def default_metric_ids_for_sector(sector: str) -> list[str]:
    """Return built-in starter metrics for a sector template."""
    normalized = normalize_sector(sector).replace(" ", "_")
    return SECTOR_METRIC_TEMPLATES.get(normalized, [])


def generate_investee_questionnaire_schema(
    *,
    sector: str,
    metric_ids: list[str] | None = None,
    reporting_period: str = "current",
    store: MetricStore | None = None,
) -> InvesteeQuestionnaireSchema:
    """Generate a dynamic investee questionnaire schema from metric definitions."""
    store = store or get_metric_store()
    selected = list(metric_ids or [])
    if not selected:
        selected = default_metric_ids_for_sector(sector)

    normalized_ids, warnings = normalize_metric_ids(selected)
    fields_by_section: dict[str, list[QuestionnaireField]] = {}
    for metric_id in normalized_ids:
        field = _field_for_metric(metric_id, store)
        if field is None:
            warnings.append(f"Unknown metric ID: {metric_id}")
            continue
        metric = store.get(metric_id)
        section = metric.primary_impact_category or metric.section or "General"
        fields_by_section.setdefault(section, []).append(field)

    sections = [
        QuestionnaireSection(
            id=_section_id(title),
            title=title,
            description=f"Metrics for {title.lower()} reporting.",
            fields=fields,
        )
        for title, fields in sorted(fields_by_section.items())
    ]

    return InvesteeQuestionnaireSchema(
        sector=normalize_sector(sector),
        reporting_period=reporting_period,
        metric_count=sum(len(section.fields) for section in sections),
        sections=sections,
        warnings=warnings,
    )


def create_collection_submission(
    *,
    submission_id: str,
    company_name: str,
    schema: InvesteeQuestionnaireSchema,
    responses: dict[str, Any] | list[SubmissionMetricResponse | dict[str, Any]],
    submitted_by: str,
    source: str = "investee portal",
) -> CollectionSubmission:
    """Create a submitted questionnaire response object from form data."""
    rows: list[SubmissionMetricResponse] = []
    if isinstance(responses, dict):
        field_units = {
            field.metric_id: field.unit
            for section in schema.sections
            for field in section.fields
        }
        for metric_id, value in responses.items():
            mid = str(metric_id).strip().upper()
            if isinstance(value, dict):
                payload = dict(value)
                payload.setdefault("metric_id", mid)
                payload.setdefault("unit", field_units.get(mid, "unspecified"))
                rows.append(SubmissionMetricResponse.model_validate(payload))
            else:
                rows.append(SubmissionMetricResponse(
                    metric_id=mid,
                    value=value,
                    unit=field_units.get(mid, "unspecified"),
                ))
    else:
        rows = [
            item if isinstance(item, SubmissionMetricResponse)
            else SubmissionMetricResponse.model_validate(item)
            for item in responses
        ]

    return CollectionSubmission(
        submission_id=submission_id,
        company_name=company_name,
        reporting_period=schema.reporting_period,
        submitted_by=submitted_by,
        source=source,
        responses=rows,
        review_history=[
            SubmissionReviewEvent(
                status="submitted",
                actor=submitted_by,
                comments="Submission created.",
            )
        ],
    )


def validate_collection_submission(
    submission: CollectionSubmission,
    schema: InvesteeQuestionnaireSchema,
) -> SubmissionValidationResult:
    """Validate one submission against its questionnaire schema."""
    expected_fields = {
        field.metric_id: field
        for section in schema.sections
        for field in section.fields
    }
    seen: set[str] = set()
    duplicate_metrics: list[str] = []
    unknown_metrics: list[str] = []
    evidence_missing: list[str] = []
    unit_mismatches: list[str] = []
    warnings: list[str] = []

    for response in submission.responses:
        metric_id = response.metric_id.strip().upper()
        if metric_id in seen and metric_id not in duplicate_metrics:
            duplicate_metrics.append(metric_id)
        seen.add(metric_id)
        field = expected_fields.get(metric_id)
        if field is None:
            unknown_metrics.append(metric_id)
            continue
        if field.evidence.required and not response.evidence_refs:
            evidence_missing.append(metric_id)
        if (
            response.unit
            and field.unit != "unspecified"
            and response.unit != "unspecified"
            and response.unit != field.unit
        ):
            unit_mismatches.append(metric_id)
        if response.value is None or (isinstance(response.value, str) and not response.value.strip()):
            warnings.append(f"{metric_id}: empty value")

    missing_required = [
        metric_id
        for metric_id, field in expected_fields.items()
        if field.required and metric_id not in seen
    ]
    is_valid = not any((
        missing_required,
        unknown_metrics,
        evidence_missing,
        unit_mismatches,
        duplicate_metrics,
        warnings,
    ))
    return SubmissionValidationResult(
        is_valid=is_valid,
        missing_required=missing_required,
        unknown_metrics=unknown_metrics,
        evidence_missing=evidence_missing,
        unit_mismatches=unit_mismatches,
        duplicate_metrics=duplicate_metrics,
        warnings=warnings,
    )


def review_collection_submission(
    submission: CollectionSubmission,
    *,
    status: Literal["flagged", "approved", "rejected", "resubmission_requested"],
    actor: str,
    comments: str = "",
) -> CollectionSubmission:
    """Return a copy of a submission with an appended review event."""
    history = list(submission.review_history)
    history.append(SubmissionReviewEvent(status=status, actor=actor, comments=comments))
    return submission.model_copy(update={"status": status, "review_history": history})


def submission_to_metric_records(
    submission: CollectionSubmission,
    schema: InvesteeQuestionnaireSchema,
    *,
    require_approved: bool = True,
    owner: str = "",
    quality_score: int = 70,
) -> tuple[list[MetricRecord], list[str]]:
    """Convert a reviewed submission into canonical metric records."""
    if require_approved and submission.status != "approved":
        return [], [f"Submission {submission.submission_id} is not approved"]

    validation = validate_collection_submission(submission, schema)
    if not validation.is_valid:
        errors = (
            [f"missing required: {m}" for m in validation.missing_required]
            + [f"unknown metric: {m}" for m in validation.unknown_metrics]
            + [f"missing evidence: {m}" for m in validation.evidence_missing]
            + [f"unit mismatch: {m}" for m in validation.unit_mismatches]
            + [f"duplicate metric: {m}" for m in validation.duplicate_metrics]
            + validation.warnings
        )
        return [], errors

    field_units = {
        field.metric_id: field.unit
        for section in schema.sections
        for field in section.fields
    }
    records: list[MetricRecord] = []
    for response in submission.responses:
        metric_id = response.metric_id.strip().upper()
        records.append(metric_record_from_value(
            metric_id=metric_id,
            value=response.value,
            unit=response.unit if response.unit != "unspecified" else field_units.get(metric_id, "unspecified"),
            period=submission.reporting_period,
            source=submission.source,
            owner=owner or submission.submitted_by,
            quality_score=quality_score,
            verification_status="management_verified" if submission.status == "approved" else "self_reported",
            source_type="investee_submission",
            evidence_refs=response.evidence_refs,
            notes=response.notes,
        ))
    return records, []


__all__ = [
    "CollectionSubmission",
    "EvidenceRequirement",
    "InvesteeQuestionnaireSchema",
    "QuestionnaireField",
    "QuestionnaireSection",
    "SECTOR_METRIC_TEMPLATES",
    "SubmissionMetricResponse",
    "SubmissionReviewEvent",
    "SubmissionValidationResult",
    "ValidationRule",
    "create_collection_submission",
    "default_metric_ids_for_sector",
    "generate_investee_questionnaire_schema",
    "review_collection_submission",
    "submission_to_metric_records",
    "validate_collection_submission",
]
