"""Coverage for the remaining roadmap-v2 institutional-readiness surfaces."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from openharness.impact.database import MetricStore
from openharness.impact.investee_collection import (
    create_collection_submission,
    generate_investee_questionnaire_schema,
    review_collection_submission,
)
from openharness.impact.models import DimensionTags, Metric, MetricRecord
from openharness.impact.roadmap_v2 import (
    AIExtractionReview,
    PCAFPosition,
    ReportPublication,
    SourceLinkedAnswer,
    answer_portfolio_query,
    autofill_sfdr_pai,
    build_climate_coverage_dashboard,
    build_collection_tracker,
    build_esrs_disclosure_pack,
    build_immutable_report_manifest,
    build_issb_disclosure_pack,
    build_lp_export_bundle,
    build_review_queue,
    calculate_carbon_intensity,
    calculate_difference_in_differences,
    calculate_pcaf_financed_emissions,
    decide_ai_extraction,
    estimate_scope3_proxy,
    explore_framework_crosswalk,
    generate_counterfactual_questions,
    harmonize_uploaded_metrics,
    issue_collection_link,
    monitor_regulatory_change,
    preview_csv_metric_import,
    run_control_checks,
    run_contribution_analysis,
    run_rule_pack_tests,
    score_evidence_strength,
    select_jurisdiction_profile,
    transition_report_publication,
)


def _store() -> MetricStore:
    return MetricStore([
        Metric(
            id="OI4112",
            name="Greenhouse Gas Emissions",
            definition="GHG emissions.",
            primary_impact_category="Climate",
            reporting_format="Decimal number",
            sdg_goals=[13],
            dimensions=DimensionTags(what=True, risk=True),
        ),
        Metric(
            id="PI4060",
            name="Client Individuals",
            definition="Clients served.",
            primary_impact_category="Stakeholders",
            reporting_format="Number",
            sdg_goals=[1],
            dimensions=DimensionTags(who=True),
        ),
    ])


def _metric_record(
    metric_id: str = "PI4060",
    value: object = "100",
    *,
    verification_status: str = "management_verified",
    owner: str = "analyst",
) -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        value=value,
        unit="number",
        period="FY2025",
        source="portal",
        owner=owner,
        quality_score=80,
        verification_status=verification_status,
        source_type="investee_submission",
        evidence_refs=["evidence://source"],
    )


def test_public_collection_link_token_and_expiry() -> None:
    issued = issue_collection_link(submission_id="sub-1", expires_in_hours=1, token="secret")

    assert issued.link.is_active("secret")
    assert not issued.link.is_active("wrong")
    assert "/collect/" in issued.url_path
    expired_at = datetime(2099, 1, 1, tzinfo=timezone.utc)
    expired = issued.link.model_copy(update={"expires_at": "2000-01-01T00:00:00+00:00"})
    assert not expired.is_active("secret", at=expired_at)


def test_collection_tracker_and_review_queue_flags_missing_and_anomaly() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="energy",
        metric_ids=["OI4112", "PI4060"],
        reporting_period="FY2025",
        store=_store(),
    )
    submission = create_collection_submission(
        submission_id="sub-2",
        company_name="SolarCo",
        schema=schema,
        responses={"OI4112": {"value": "200", "unit": "number"}},
        submitted_by="cfo",
    )

    tracker = build_collection_tracker(
        schemas_by_company={"SolarCo": schema, "MissingCo": schema},
        submissions=[submission],
        current_period="FY2025",
    )
    assert {row.company_name: row.status for row in tracker} == {
        "SolarCo": "submitted",
        "MissingCo": "missing",
    }
    assert tracker[0].missing_metrics == ["PI4060"]

    queue = build_review_queue(
        [submission],
        {"sub-2": schema},
        previous_values={("SolarCo", "OI4112"): 50},
    )
    assert queue[0].submission_id == "sub-2"
    assert {"missing_required", "evidence_missing", "period_anomaly"} <= set(queue[0].flags)


def test_csv_import_preview_maps_duplicates_and_errors() -> None:
    csv_text = (
        "Metric,Value,Unit,Period,Source,Owner,Quality\n"
        "PI4060,100,number,FY2025,portal,analyst,80\n"
        "PI4060,100,number,FY2025,portal,analyst,80\n"
        "BAD,100,number,FY2025,portal,analyst,80\n"
    )
    preview = preview_csv_metric_import(
        csv_text,
        {
            "Metric": "metric_id",
            "Value": "value",
            "Unit": "unit",
            "Period": "period",
            "Source": "source",
            "Owner": "owner",
            "Quality": "quality_score",
        },
    )

    assert preview.valid_count == 1
    assert preview.duplicate_count == 1
    assert preview.error_count == 1


def test_climate_scope3_pcaf_intensity_and_dashboard() -> None:
    proxy = estimate_scope3_proxy(
        company_name="ClimateCo",
        sector="software",
        basis="spend",
        amount=1000,
        factor_tco2e_per_unit=0.02,
    )
    assert proxy.tco2e == 20

    pcaf = calculate_pcaf_financed_emissions(PCAFPosition(
        company_name="ClimateCo",
        investment_value_usd=1_000_000,
        enterprise_value_usd=10_000_000,
        company_emissions_tco2e=500,
        data_quality_score=3,
    ))
    assert pcaf.attribution_factor == 0.1
    assert pcaf.financed_emissions_tco2e == 50

    intensity = calculate_carbon_intensity(
        company_name="ClimateCo",
        total_tco2e=100,
        revenue=1_000,
        employees=10,
        units=50,
        ownership_pct=25,
    )
    assert intensity.tco2e_per_revenue == 0.1
    assert intensity.ownership_adjusted_footprint == 25

    dashboard = build_climate_coverage_dashboard([("ClimateCo", "direct", "direct", "proxy")])
    assert dashboard[0].actual_scopes == 2
    assert dashboard[0].estimated_scopes == 1


def test_disclosure_packs_crosswalk_jurisdiction_and_rule_tests() -> None:
    issb = build_issb_disclosure_pack(
        entity="Co",
        reporting_period="FY2025",
        answers=[SourceLinkedAnswer(
            code="S2-MT-1",
            prompt="Climate metrics",
            answer="100 tCO2e",
            source_node_ids=["missing-node"],
            metric_ids=["OI4112"],
            status="direct",
        )],
    )
    assert issb.framework == "ISSB S1/S2"

    esrs = build_esrs_disclosure_pack(
        amended_version="2025-exposure-draft",
        double_materiality_links={"E1-6": ["metric:OI4112"]},
    )
    assert esrs.answers[0].status == "direct"

    sfdr = autofill_sfdr_pai(
        required_codes=["PAI-1", "PAI-2", "PAI-3"],
        direct_values={"PAI-1": "reported"},
        proxy_values={"PAI-2": "estimated"},
        not_applicable={"PAI-3"},
    )
    assert [row.status for row in sfdr] == ["direct", "proxy", "not_applicable"]

    assert select_jurisdiction_profile("EU").frameworks[:2] == ["ESRS", "SFDR"]
    assert explore_framework_crosswalk("scope 1")
    result = run_rule_pack_tests("ISSB", "S1-S2-2023", ["governance", "metrics"], {"governance": "ok"})
    assert not result.passed
    assert result.failures == ["metrics"]


def test_lp_bundle_publication_branding_and_controls() -> None:
    bundle = build_lp_export_bundle(
        formats=["html", "json"],
        source_refs=["evidence://one"],
        portfolio_payloads=[{"company_name": "Co", "metric_records": [_metric_record("OI4112")]}],
    )
    assert bundle.evidence_manifest["evidence://one"]
    assert bundle.edci_report and bundle.edci_report.scope == "portfolio"

    report = ReportPublication(report_id="r1")
    approved = transition_report_publication(report, "reviewer_approved", actor="reviewer")
    published = transition_report_publication(approved, "published", actor="reviewer")
    assert published.state == "published"
    assert published.published_at
    with pytest.raises(ValueError):
        transition_report_publication(report, "published", actor="reviewer")

    controls = run_control_checks(
        metric_records=[_metric_record()],
        ai_outputs_pending_review=1,
        unsupported_claim_count=1,
    )
    assert [item.control_id for item in controls] == [
        "segregation_of_duties",
        "late_edits",
        "unreviewed_ai_outputs",
        "unsupported_claims",
    ]
    assert not controls[2].passed


def test_ai_review_manifest_causal_and_query_helpers() -> None:
    review = AIExtractionReview(
        item_id="ai-1",
        extracted_text="100 clients served",
        confidence=0.9,
        source_refs=["evidence://source"],
    )
    approved = decide_ai_extraction(review, "approved", "analyst")
    assert approved.decision == "approved"

    with pytest.raises(ValueError):
        decide_ai_extraction(review.model_copy(update={"confidence": 0.2}), "approved", "analyst")

    manifest = build_immutable_report_manifest("r1", {"source.csv": "abc", "report.html": "<h1>x</h1>"})
    assert manifest.manifest_hash
    assert len(manifest.artifact_hashes) == 2

    contribution = run_contribution_analysis(
        hypothesis="Capital improves access",
        contribution_claim="Investment accelerated growth",
        evidence_for=["board minutes", "deployment data"],
        evidence_against=["market grew"],
    )
    assert contribution.confidence_score == pytest.approx(2 / 3, rel=1e-3)
    assert len(generate_counterfactual_questions("education", "SaaS", "learning gains")) == 4
    assert score_evidence_strength(
        study_design="DID",
        sample_size=500,
        third_party_review=True,
        beneficiary_voice=True,
    ).score == 90
    assert calculate_difference_in_differences(
        treatment_pre=10,
        treatment_post=18,
        comparator_pre=12,
        comparator_post=15,
    ) == 5

    mappings = harmonize_uploaded_metrics(
        ["client individuals reached"],
        {"PI4060": "client individuals", "OI4112": "greenhouse gas emissions"},
    )
    assert mappings[0].canonical_metric_id == "PI4060"
    assert mappings[0].confidence > 0

    query = answer_portfolio_query("average value", [_metric_record(value="100"), _metric_record(value="200")])
    assert query.answer == "150.0"
    assert query.citations == ["evidence://source", "evidence://source"]

    change = monitor_regulatory_change(
        change_id="issb-update",
        changed_framework="ISSB",
        rule_packs={"global": ["ISSB"], "eu": ["ESRS"]},
        templates={"lp": ["ISSB", "EDCI"]},
        company_profiles={"Co": ["ISSB"], "Other": ["SFDR"]},
    )
    assert change.affected_rule_packs == ["global"]
    assert change.affected_templates == ["lp"]
    assert change.affected_companies == ["Co"]


def test_approved_submission_shows_tracker_approved() -> None:
    schema = generate_investee_questionnaire_schema(
        sector="energy",
        metric_ids=["OI4112"],
        reporting_period="FY2025",
        store=_store(),
    )
    submission = create_collection_submission(
        submission_id="sub-3",
        company_name="SolarCo",
        schema=schema,
        responses={"OI4112": {"value": "200", "unit": "number", "evidence_refs": ["evidence://calc"]}},
        submitted_by="cfo",
    )
    approved = review_collection_submission(submission, status="approved", actor="analyst")
    tracker = build_collection_tracker(
        schemas_by_company={"SolarCo": schema},
        submissions=[approved],
        current_period="FY2025",
    )
    assert tracker[0].status == "approved"
