"""Tests for EDCI completeness reports."""

from __future__ import annotations

from openharness.impact.frameworks.edci import (
    assess_edci_coverage,
    assess_edci_completeness,
    get_edci_metrics,
    portfolio_edci_completeness,
)
from openharness.impact.models import MetricRecord


def test_assess_edci_completeness_statuses_all_metrics() -> None:
    report = assess_edci_completeness(
        company_name="DemoCo",
        metric_records=[
            MetricRecord(
                metric_id="OI4112",
                value="100",
                unit="tCO2e",
                period="FY2025",
                source="ghg workbook",
                owner="analyst",
                quality_score=90,
                evidence_refs=["evidence://scope1"],
            )
        ],
        reported_data={"EDCI-E2": "50", "OI1571": "45%"},
        proxy_values={"EDCI-E3": "250"},
        not_applicable=["EDCI-G1"],
    )

    assert report.scope == "company"
    assert report.total_fields == 19
    assert report.required_fields == 14
    assert report.optional_fields == 5
    assert report.available == 3
    assert report.proxy == 1
    assert report.not_applicable == 1
    assert report.missing == 14
    assert report.completeness_pct == 26.3
    assert report.required_completeness_pct == 21.4

    rows = {row.edci_id: row for row in report.rows}
    assert rows["EDCI-E1"].status == "available"
    assert rows["EDCI-E1"].source_metric_id == "OI4112"
    assert rows["EDCI-E1"].evidence_refs == ["evidence://scope1"]
    assert rows["EDCI-E2"].status == "available"
    assert rows["EDCI-E2"].source_metric_id == "EDCI-E2"
    assert rows["EDCI-E3"].status == "proxy"
    assert rows["EDCI-G1"].status == "not_applicable"
    assert rows["EDCI-G1"].required is False
    assert rows["EDCI-S6"].status == "available"
    assert rows["EDCI-S6"].source_metric_id == "OI1571"


def test_portfolio_edci_completeness_rolls_up_companies() -> None:
    report = portfolio_edci_completeness([
        {
            "company_name": "A",
            "reported_data": {"EDCI-E2": "50"},
        },
        {
            "company_name": "B",
            "reported_data": {"OI1571": "60%"},
            "proxy_values": {"EDCI-E3": "100"},
            "not_applicable": ["EDCI-G1"],
        },
    ])

    assert report.scope == "portfolio"
    assert report.company_count == 2
    assert report.total_fields == 38
    assert report.required_fields == 28
    assert report.optional_fields == 10
    assert report.available == 2
    assert report.proxy == 1
    assert report.not_applicable == 1
    assert report.missing == 34
    assert report.by_category["environment"]["total"] == 14
    assert report.by_category["social"]["total"] == 22
    assert report.by_category["governance"]["total"] == 2
    assert report.by_category["governance"]["optional"] == 2


def test_completeness_report_accepts_legacy_reported_metrics_alias() -> None:
    report = portfolio_edci_completeness([
        {
            "name": "LegacyCo",
            "reported_metrics": {"OI1571": "30%"},
        }
    ])

    row = next(row for row in report.rows if row.edci_id == "EDCI-S6")
    assert row.company_name == "LegacyCo"
    assert row.status == "available"
    assert row.source_metric_id == "OI1571"


def test_edci_2026_optional_cybersecurity_metric_is_exposed() -> None:
    metrics = get_edci_metrics()
    cyber = next(metric for metric in metrics if metric.id == "EDCI-G1")

    assert len(metrics) == 19
    assert cyber.required is False
    assert "Cybersecurity" in cyber.name


def test_edci_coverage_does_not_count_keywords_without_data() -> None:
    result = assess_edci_coverage(
        reported_data={"edci-e2": "50", "OI3324": "30%"},
        document_text="The company reports 1,200 MWh of energy consumption and annual penetration testing.",
    )
    rows = {row["id"]: row for row in result["metrics"]}

    assert rows["EDCI-E2"]["addressed"] is True
    assert rows["EDCI-E7"]["addressed"] is True
    assert rows["EDCI-E7"]["evidence_status"] == "proxy"
    assert rows["EDCI-G1"]["addressed"] is False
    assert rows["EDCI-G1"]["evidence_status"] == "heuristic"
