"""Tests for EDCI completeness reports."""

from __future__ import annotations

from openharness.impact.frameworks.edci import (
    assess_edci_completeness,
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
        reported_data={"EDCI-E2": "50", "OI6213": "45%"},
        proxy_values={"EDCI-E3": "250"},
        not_applicable=["EDCI-G2"],
    )

    assert report.scope == "company"
    assert report.total_fields == 17
    assert report.available == 3
    assert report.proxy == 1
    assert report.not_applicable == 1
    assert report.missing == 12
    assert report.completeness_pct == 29.4

    rows = {row.edci_id: row for row in report.rows}
    assert rows["EDCI-E1"].status == "available"
    assert rows["EDCI-E1"].source_metric_id == "OI4112"
    assert rows["EDCI-E1"].evidence_refs == ["evidence://scope1"]
    assert rows["EDCI-E2"].status == "available"
    assert rows["EDCI-E2"].source_metric_id == "EDCI-E2"
    assert rows["EDCI-E3"].status == "proxy"
    assert rows["EDCI-G2"].status == "not_applicable"
    assert rows["EDCI-S4"].status == "available"
    assert rows["EDCI-S4"].source_metric_id == "OI6213"


def test_portfolio_edci_completeness_rolls_up_companies() -> None:
    report = portfolio_edci_completeness([
        {
            "company_name": "A",
            "reported_data": {"EDCI-E2": "50"},
        },
        {
            "company_name": "B",
            "reported_data": {"OI6213": "60%"},
            "proxy_values": {"EDCI-E3": "100"},
            "not_applicable": ["EDCI-G2"],
        },
    ])

    assert report.scope == "portfolio"
    assert report.company_count == 2
    assert report.total_fields == 34
    assert report.available == 2
    assert report.proxy == 1
    assert report.not_applicable == 1
    assert report.missing == 30
    assert report.by_category["environment"]["total"] == 12
    assert report.by_category["social"]["total"] == 16
    assert report.by_category["governance"]["total"] == 6


def test_completeness_report_accepts_legacy_reported_metrics_alias() -> None:
    report = portfolio_edci_completeness([
        {
            "name": "LegacyCo",
            "reported_metrics": {"OI1571": "30%"},
        }
    ])

    row = next(row for row in report.rows if row.edci_id == "EDCI-S5")
    assert row.company_name == "LegacyCo"
    assert row.status == "available"
    assert row.source_metric_id == "OI1571"
