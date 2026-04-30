"""Tests for investee questionnaire schema generation."""

from __future__ import annotations

from openharness.impact.database import MetricStore
from openharness.impact.investee_collection import (
    create_collection_submission,
    default_metric_ids_for_sector,
    generate_investee_questionnaire_schema,
    review_collection_submission,
    submission_to_metric_records,
    validate_collection_submission,
)
from openharness.impact.models import DimensionTags, Metric


def _store() -> MetricStore:
    return MetricStore([
        Metric(
            id="OI4112",
            name="Greenhouse Gas Emissions",
            definition="Amount of greenhouse gas emissions.",
            usage_guidance="Report Scope 1 and Scope 2 emissions separately where possible.",
            primary_impact_category="Climate",
            reporting_format="Decimal number",
            sdg_goals=[13],
            dimensions=DimensionTags(what=True, risk=True),
        ),
        Metric(
            id="PI4060",
            name="Client Individuals",
            definition="Number of unique clients served.",
            primary_impact_category="Stakeholders",
            reporting_format="Number",
            sdg_goals=[1, 8],
            dimensions=DimensionTags(who=True, how_much_scale=True),
        ),
        Metric(
            id="OI6213",
            name="Permanent Employees: Female",
            definition="Percentage of permanent employees who are female.",
            primary_impact_category="Diversity",
            reporting_format="Percent",
            sdg_goals=[5],
            dimensions=DimensionTags(who=True),
        ),
    ])


def test_generate_questionnaire_from_explicit_metrics() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="Energy",
        metric_ids=["oi4112", "PI4060"],
        reporting_period="FY2025",
        store=_store(),
    )

    assert schema.sector == "energy"
    assert schema.reporting_period == "FY2025"
    assert schema.metric_count == 2
    fields = [field for section in schema.sections for field in section.fields]
    assert [field.metric_id for field in fields] == ["OI4112", "PI4060"]
    assert fields[0].label == "Greenhouse Gas Emissions"
    assert fields[0].definition
    assert fields[0].guidance.startswith("Report Scope")
    assert fields[0].unit == "number"
    assert fields[0].required is True
    assert fields[0].evidence.required is True
    assert "calculation workbook" in fields[0].evidence.examples
    assert {rule.rule for rule in fields[0].validation_rules} == {
        "required",
        "metric_id",
        "number_or_text",
        "expected_unit",
        "evidence_required",
    }
    assert fields[0].sdg_goals == [13]
    assert "what" in fields[0].dimensions


def test_questionnaire_groups_fields_into_sections() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="fintech",
        metric_ids=["PI4060", "OI6213"],
        store=_store(),
    )

    section_titles = [section.title for section in schema.sections]
    assert section_titles == ["Diversity", "Stakeholders"]
    assert schema.sections[0].id == "diversity"
    female_field = schema.sections[0].fields[0]
    assert female_field.unit == "%"
    assert female_field.value_type == "percent"
    assert "calculation denominator and numerator" in female_field.evidence.examples


def test_questionnaire_warns_for_invalid_and_unknown_metrics() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="energy",
        metric_ids=["BADID", "PI9999"],
        store=_store(),
    )

    assert schema.metric_count == 0
    assert "Ignored invalid metric ID: BADID" in schema.warnings
    assert "Unknown metric ID: PI9999" in schema.warnings


def test_sector_default_template_is_used_when_metric_ids_omitted() -> None:
    assert default_metric_ids_for_sector("Energy")[:2] == ["OI4112", "OI6697"]
    schema = generate_investee_questionnaire_schema(
        sector="energy",
        store=_store(),
    )

    assert schema.metric_count == 1
    assert schema.sections[0].fields[0].metric_id == "OI4112"
    assert "Unknown metric ID: OI6697" in schema.warnings


def test_collection_submission_validates_and_approves_to_metric_records() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="energy",
        metric_ids=["OI4112"],
        reporting_period="FY2025",
        store=_store(),
    )
    submission = create_collection_submission(
        submission_id="sub-001",
        company_name="SolarCo",
        schema=schema,
        responses={
            "OI4112": {
                "value": "150",
                "unit": "number",
                "evidence_refs": ["evidence://calc"],
            }
        },
        submitted_by="cfo@solarco.test",
    )

    validation = validate_collection_submission(submission, schema)
    assert validation.is_valid
    approved = review_collection_submission(
        submission,
        status="approved",
        actor="analyst@fund.test",
        comments="Matches source workbook.",
    )
    records, errors = submission_to_metric_records(
        approved,
        schema,
        owner="analyst@fund.test",
        quality_score=82,
    )

    assert errors == []
    assert approved.status == "approved"
    assert approved.review_history[-1].comments == "Matches source workbook."
    assert len(records) == 1
    assert records[0].metric_id == "OI4112"
    assert records[0].period == "FY2025"
    assert records[0].source_type == "investee_submission"
    assert records[0].verification_status == "management_verified"
    assert records[0].quality_score == 82
    assert records[0].evidence_refs == ["evidence://calc"]


def test_collection_submission_flags_missing_evidence_and_missing_required() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="energy",
        metric_ids=["OI4112", "PI4060"],
        store=_store(),
    )
    submission = create_collection_submission(
        submission_id="sub-002",
        company_name="SolarCo",
        schema=schema,
        responses={"OI4112": "150"},
        submitted_by="cfo@solarco.test",
    )

    validation = validate_collection_submission(submission, schema)
    assert not validation.is_valid
    assert validation.missing_required == ["PI4060"]
    assert validation.evidence_missing == ["OI4112"]

    flagged = review_collection_submission(
        submission,
        status="resubmission_requested",
        actor="analyst@fund.test",
        comments="Please attach calculation workbook and client count.",
    )
    assert flagged.status == "resubmission_requested"
    assert flagged.review_history[-1].status == "resubmission_requested"


def test_submission_to_metric_records_requires_approval_by_default() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="energy",
        metric_ids=["OI4112"],
        store=_store(),
    )
    submission = create_collection_submission(
        submission_id="sub-003",
        company_name="SolarCo",
        schema=schema,
        responses={
            "OI4112": {
                "value": "150",
                "unit": "number",
                "evidence_refs": ["evidence://calc"],
            }
        },
        submitted_by="cfo@solarco.test",
    )

    records, errors = submission_to_metric_records(submission, schema)
    assert records == []
    assert errors == ["Submission sub-003 is not approved"]


def test_collection_submission_flags_unknown_duplicate_and_unit_mismatch() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="energy",
        metric_ids=["OI4112"],
        store=_store(),
    )
    submission = create_collection_submission(
        submission_id="sub-004",
        company_name="SolarCo",
        schema=schema,
        responses=[
            {"metric_id": "OI4112", "value": "150", "unit": "kg", "evidence_refs": ["e1"]},
            {"metric_id": "OI4112", "value": "160", "unit": "number", "evidence_refs": ["e2"]},
            {"metric_id": "PI9999", "value": "1", "unit": "count", "evidence_refs": ["e3"]},
        ],
        submitted_by="cfo@solarco.test",
    )

    validation = validate_collection_submission(submission, schema)
    assert not validation.is_valid
    assert validation.duplicate_metrics == ["OI4112"]
    assert validation.unknown_metrics == ["PI9999"]
    assert validation.unit_mismatches == ["OI4112"]
