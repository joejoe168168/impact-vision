"""Tests for structured metric and report audit events."""

from __future__ import annotations

from openharness.impact.audit_trail import AuditTrail


def test_record_metric_event_creates_hash_chained_payload() -> None:
    trail = AuditTrail(tenant_id="tenant-a", fund_id="fund-i")
    event = trail.record_metric_event(
        action="metric_created",
        metric_id="oi4112",
        actor="analyst@example.test",
        period="FY2026",
        new_value="150 tCO2e",
        source="investee-submission",
        evidence_refs=["evidence://ghg"],
        review_status="submitted",
    )

    assert event.report_kind == "metric.created"
    assert event.report_period == "FY2026"
    assert event.payload["metric_id"] == "OI4112"
    assert event.payload["actor"] == "analyst@example.test"
    assert event.payload["evidence_refs"] == ["evidence://ghg"]
    assert trail.verify() == (True, [])


def test_record_metric_update_and_approval_preserve_order() -> None:
    trail = AuditTrail()
    trail.record_metric_event(
        action="metric_updated",
        metric_id="PI4060",
        actor="analyst",
        old_value=1000,
        new_value=1200,
    )
    trail.record_metric_event(
        action="metric_approved",
        metric_id="PI4060",
        actor="reviewer",
        review_status="management_verified",
    )

    assert trail.length == 2
    assert trail.feed.reports[1].prev_hash == trail.feed.reports[0].content_hash
    assert trail.feed.reports[1].report_kind == "metric.approved"


def test_record_report_publication_event() -> None:
    trail = AuditTrail(tenant_id="tenant-a", fund_id="fund-i")
    event = trail.record_report_publication(
        report_id="lp-q4-2026",
        report_format="html",
        actor="lp-relations",
        period="2026-Q4",
        standards=["IRIS_PLUS@5.3c", "EDCI@2025"],
        evidence_manifest_hash="abc123",
        report_hash="def456",
    )

    assert event.report_kind == "report.published"
    assert event.payload["standards"] == ["IRIS_PLUS@5.3c", "EDCI@2025"]
    assert event.payload["evidence_manifest_hash"] == "abc123"
    assert trail.verify() == (True, [])
