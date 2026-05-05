"""Standards conformance regressions for conservative impact tooling."""

from __future__ import annotations

from openharness.impact.database import get_metric_store
from openharness.impact.exit_impact import ExitImpactPlan
from openharness.impact.frameworks.cross_reference import get_all_cross_references
from openharness.impact.frameworks.edci import assess_edci_coverage, get_edci_metrics
from openharness.impact.frameworks.sfdr_pai import assess_sfdr_compliance, get_pai_indicators
from openharness.impact.models import Company
from openharness.impact.sdk import ImpactVision


def _assert_iris_ids_exist(metric_ids: list[str], context: str) -> None:
    store = get_metric_store()
    missing = [metric_id for metric_id in metric_ids if store.get(metric_id) is None]
    assert missing == [], f"Missing IRIS+ catalog IDs in {context}: {missing}"


def test_opim_exit_impact_uses_principle_7_with_principle_8_learning_context() -> None:
    plan = ExitImpactPlan(company=Company(name="ExitCo"))

    assert plan.opim_principle == "OPIM Principle 7"
    assert plan.learning_principle == "OPIM Principle 8"


def test_edci_2026_kpi_set_matches_public_categories() -> None:
    metrics = get_edci_metrics()
    ids = {metric.id for metric in metrics}
    names = {metric.name for metric in metrics}

    assert len(metrics) == 19
    assert {"EDCI-E1", "EDCI-E2", "EDCI-E3", "EDCI-E7", "EDCI-G1"} <= ids
    assert "Cybersecurity Testing" in names
    assert "Living Wage" not in names
    assert "Board Independence" not in names
    assert next(metric for metric in metrics if metric.id == "EDCI-E3").required is False
    assert next(metric for metric in metrics if metric.id == "EDCI-G1").required is False


def test_edci_mentions_do_not_count_as_reportable_coverage() -> None:
    result = assess_edci_coverage(
        document_text=(
            "The company discusses Scope 1 emissions, renewable energy, and "
            "penetration testing but has not supplied KPI data."
        )
    )
    rows = {row["id"]: row for row in result["metrics"]}

    assert result["addressed"] == 0
    assert rows["EDCI-E1"]["evidence_status"] == "heuristic"
    assert rows["EDCI-E7"]["evidence_status"] == "heuristic"
    assert rows["EDCI-G1"]["evidence_status"] == "heuristic"


def test_sfdr_mentions_do_not_count_as_pai_coverage() -> None:
    result = assess_sfdr_compliance(
        company_description="We discuss GHG emissions, board diversity, and fossil fuel exposure."
    )
    rows = {row["number"]: row for row in result["indicators"]}

    assert result["addressed"] == 0
    assert rows[1]["status"] == "mentioned"
    assert rows[13]["status"] == "mentioned"
    assert rows[1]["data_points_needed"]


def test_sfdr_accepts_direct_and_proxy_data_without_keyword_inference() -> None:
    result = assess_sfdr_compliance(
        reported_data={"SFDR PAI 1": "100 tCO2e", "OI1582": "12%"},
        proxy_data={"PAI-13": "40%"},
    )
    rows = {row["number"]: row for row in result["indicators"]}

    assert rows[1]["status"] == "available"
    assert rows[12]["status"] == "proxy"
    assert rows[13]["status"] == "proxy"


def test_framework_iris_cross_references_exist_in_bundled_catalog() -> None:
    store = get_metric_store()
    missing: dict[str, list[str]] = {}

    for indicator in get_pai_indicators(mandatory_only=False):
        for metric_id in indicator.iris_cross_refs:
            if store.get(metric_id) is None:
                missing.setdefault(metric_id, []).append(f"SFDR PAI {indicator.number}")

    for metric in get_edci_metrics():
        for metric_id in metric.iris_cross_refs:
            if store.get(metric_id) is None:
                missing.setdefault(metric_id, []).append(metric.id)

    for cross_ref in get_all_cross_references():
        for metric_id in cross_ref.iris_plus:
            if store.get(metric_id) is None:
                missing.setdefault(metric_id, []).append(cross_ref.concept)

    assert missing == {}


def test_sdk_country_argument_maps_to_company_geography() -> None:
    assessment = ImpactVision().assess_company_text(
        "GeoCo",
        text="We serve rural clients with clean energy access.",
        sector="energy",
        country="KE",
    )

    assert assessment.company.geography == "KE"


def test_production_tool_iris_mappings_are_catalog_backed() -> None:
    from openharness.impact.frameworks.cdp import CDP_TO_IRIS
    from openharness.impact.frameworks.issb_ifrs_s1 import get_ifrs_s1_framework
    from openharness.impact.frameworks.issb_ifrs_s2 import get_ifrs_s2_framework
    from openharness.impact.frameworks.tnfd import TNFD_DISCLOSURES
    from openharness.impact.greenwashing import _ADVERSE_METRICS_BY_SECTOR
    from openharness.impact.investee_collection import SECTOR_METRIC_TEMPLATES
    from openharness.tools.impact.improvement_advisor_tool import (
        _DIMENSION_IMPROVEMENT_STRATEGIES,
        _SECTOR_PEER_PATTERNS,
    )
    from openharness.tools.impact.product_passport_tool import DPP_CATEGORIES

    for category, config in DPP_CATEGORIES.items():
        _assert_iris_ids_exist(config["iris_mappings"], f"DPP {category}")

    for sector, metric_ids in SECTOR_METRIC_TEMPLATES.items():
        _assert_iris_ids_exist(metric_ids, f"investee template {sector}")

    for dimension, strategies in _DIMENSION_IMPROVEMENT_STRATEGIES.items():
        metric_ids = [strategy["metric"] for strategy in strategies]
        _assert_iris_ids_exist(metric_ids, f"improvement strategy {dimension}")

    for sector, pattern in _SECTOR_PEER_PATTERNS.items():
        _assert_iris_ids_exist(pattern["common_metrics"], f"peer pattern {sector}")

    for code, metric_ids in CDP_TO_IRIS.items():
        _assert_iris_ids_exist(metric_ids, f"CDP {code}")

    for disclosure in TNFD_DISCLOSURES:
        _assert_iris_ids_exist(disclosure.iris_cross_refs, f"TNFD {disclosure.code}")

    for framework in (get_ifrs_s1_framework(), get_ifrs_s2_framework()):
        for pillar in framework.pillars:
            for disclosure in pillar.disclosures:
                _assert_iris_ids_exist(
                    disclosure.iris_cross_refs,
                    f"{framework.name} {disclosure.code}",
                )

    for sector, metric_ids in _ADVERSE_METRICS_BY_SECTOR.items():
        iris_ids = [
            metric_id for metric_id in metric_ids
            if not metric_id.startswith(("CUSTOM:", "EDCI-"))
        ]
        _assert_iris_ids_exist(iris_ids, f"greenwashing adverse set {sector}")
