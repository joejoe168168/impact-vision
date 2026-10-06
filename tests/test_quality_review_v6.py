"""Regression coverage for the v6 data-quality and currency review."""

from __future__ import annotations

import asyncio
from pathlib import Path

from openharness.impact.concordance import load_concordance
from openharness.impact.frameworks.esrs import (
    load_simplified_datapoints,
    simplified_esrs_metadata,
)
from openharness.impact.issb_reporting import load_s2_amendments
from openharness.impact.models import MetricRecord
from openharness.impact.regulatory_calendar import issb_summary
from openharness.impact.standards_registry import load_articles
from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.regulatory_calendar_tool import RegulatoryCalendarTool


def _record() -> MetricRecord:
    return MetricRecord(
        metric_id="OI4112",
        value=10,
        unit="tCO2e",
        period="2026-12-31",
        source="ledger",
        owner="CFO",
        quality_score=90,
        verification_status="third_party_verified",
        boundary="operational control",
        methodology="GHG Protocol",
    )


def test_simplified_esrs_rows_are_explicitly_provenanced() -> None:
    rows = load_simplified_datapoints()
    metadata = simplified_esrs_metadata()
    assert len(rows) >= 50 and not any(row.synthetic for row in rows)
    assert metadata["status"] == "published_oj"
    assert metadata["legal_instrument"] == "Commission Delegated Regulation (EU) 2026/1563"
    assert metadata["effective_from"] == "2027-01-01"
    assert all(row.source_url for row in rows)


def test_issb_s2_amendment_register_is_available() -> None:
    amendments = load_s2_amendments()
    assert len(amendments) == 4
    assert all(item.status == "issued" for item in amendments)
    assert all(item.effective_date == "2027-01-01" for item in amendments)
    assert all(item.early_application for item in amendments)
    rows = issb_summary()
    assert all(r["source_quality"] == ("deep_link" if r["source_url"] else "authority_name_only") for r in rows)
    assert any(r["source_quality"] == "authority_name_only" for r in rows)


def test_concordance_yaml_enriches_legacy_refs_instead_of_replacing_them() -> None:
    translations = load_concordance().translate(_record(), "edci")
    assert translations
    assert translations[0][0].datapoint_id == "EDCI-E1"


def test_sse_article_fixture_discloses_summary_status() -> None:
    article = load_articles("sse_g14")[0]
    assert article.content_status == "generated_summary"
    assert article.source_url.startswith("https://www.sse.com.cn/")


def test_regulatory_tool_exposes_issued_s2_amendments() -> None:
    context = ToolExecutionContext(cwd=Path.cwd())
    result = asyncio.run(
        RegulatoryCalendarTool().execute({"action": "s2_amendments"}, context)
    )
    assert not result.is_error
    assert result.metadata["effective_date"] == "2027-01-01"
    assert len(result.metadata["amendments"]) == 4
