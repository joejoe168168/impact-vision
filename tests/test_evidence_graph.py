"""Tests for claim, metric, target, and report-section evidence lineage."""

from __future__ import annotations

from openharness.impact.evidence_graph import build_evidence_graph, graph_warnings
from openharness.impact.models import ImpactClaim, ImpactTarget, MetricRecord


def test_build_evidence_graph_links_claim_metric_target_and_section() -> None:
    metric = MetricRecord(
        metric_id="OI4112",
        value="150",
        unit="tCO2e",
        period="FY2025",
        source="investee workbook",
        owner="analyst",
        quality_score=85,
        verification_status="management_verified",
        source_type="investee_submission",
        evidence_refs=["evidence://ghg-workbook"],
    )
    claim = ImpactClaim(
        text="The company avoided 150 tCO2e in FY2025.",
        category="outcome",
        mapped_metrics=["OI4112"],
        confidence=0.8,
    )
    target = ImpactTarget(
        metric_id="OI4112",
        target_value=200,
        target_unit="tCO2e",
        target_date="2027",
        description="200 tCO2e avoided by 2027",
    )

    graph = build_evidence_graph(
        claims=[claim],
        metric_records=[metric],
        targets=[target],
        report_sections={"sec-claims": ["claim:1"], "sec-targets": ["OI4112", "target:OI4112"]},
    )

    ids = graph.node_ids()
    assert {
        "claim:1",
        "metric:OI4112",
        "target:OI4112",
        "evidence:evidence-ghg-workbook",
        "section:sec-claims",
        "section:sec-targets",
    } <= ids

    link_types = {(link.source, link.target, link.type) for link in graph.links}
    assert ("metric:OI4112", "evidence:evidence-ghg-workbook", "supported_by") in link_types
    assert ("claim:1", "metric:OI4112", "measured_by") in link_types
    assert ("target:OI4112", "metric:OI4112", "tracks") in link_types
    assert ("claim:1", "section:sec-claims", "appears_in") in link_types
    assert graph_warnings(graph) == []


def test_build_evidence_graph_uses_target_tracking_without_explicit_targets() -> None:
    metric = {
        "metric_id": "PI4060",
        "value": "25000",
        "unit": "people",
        "period": "FY2025",
        "source": "portal",
        "owner": "analyst",
        "quality_score": 70,
        "evidence_refs": ["evidence://crm-export"],
    }
    graph = build_evidence_graph(
        metric_records=[metric],
        target_tracking={
            "targets": [
                {
                    "metric_id": "PI4060",
                    "target": "30,000 clients by 2026",
                    "current_value": 25000,
                    "progress_pct": 83.3,
                    "status": "on_track",
                }
            ]
        },
    )

    assert "target:PI4060" in graph.node_ids()
    assert any(
        link.source == "target:PI4060"
        and link.target == "metric:PI4060"
        and link.type == "tracks"
        for link in graph.links
    )


def test_graph_warnings_flags_unsupported_claims_and_metrics_without_evidence() -> None:
    graph = build_evidence_graph(
        claims=[
            {
                "text": "We improve livelihoods across rural communities.",
                "category": "intent",
                "mapped_metrics": [],
            }
        ],
        metric_records=[
            {
                "metric_id": "PI4060",
                "value": "25000",
                "unit": "people",
                "period": "FY2025",
                "source": "portal",
                "owner": "analyst",
                "quality_score": 70,
            }
        ],
    )

    assert graph_warnings(graph) == [
        "metric:PI4060 has no supporting evidence reference",
        "claim:1 is not linked to a reported metric",
    ]


def test_links_for_returns_incident_links() -> None:
    graph = build_evidence_graph(
        metric_records=[
            MetricRecord(
                metric_id="OI4112",
                value="150",
                unit="tCO2e",
                period="FY2025",
                source="workbook",
                owner="analyst",
                quality_score=90,
                evidence_refs=["evidence://ghg"],
            )
        ],
    )

    links = graph.links_for("metric:OI4112")
    assert len(links) == 1
    assert links[0].type == "supported_by"
