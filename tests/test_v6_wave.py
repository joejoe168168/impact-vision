"""Wave-level acceptance coverage for the v6 implementation plan."""

from __future__ import annotations

from datetime import date

from openharness.impact.audit_trail import AuditTrail
from openharness.impact.cids_export import export_cids, validate_cids
from openharness.impact.climate_accounting import (
    energy_to_tce,
    scope1_mass_balance,
    scope3_estimate,
    water_balance,
)
from openharness.impact.concordance import load_concordance
from openharness.impact.contribution import (
    ContributionChannel,
    ContributionClaim,
    ContributionEvidence,
    contribution_scorecard,
)
from openharness.impact.ddq_responder import load_ddq_bank
from openharness.impact.disclosure_checklist import load_checklist
from openharness.impact.engagements.data_room import burden_report, dedupe_requests
from openharness.impact.engagements.materiality import (
    FinancialMaterialityInput,
    ImpactMaterialityScore,
    assess_materiality,
)
from openharness.impact.engagements.toc_builder import (
    KPIFramework,
    KPIFrameworkEntry,
    lock_kpi_framework,
    promote_kpis_to_conditions,
)
from openharness.impact.engagements.regulatory import (
    classify_cn_disclosure,
    load_cn_topics,
)
from openharness.impact.evidence_graph import EvidenceGraph, EvidenceNode
from openharness.impact.frameworks.esrs import load_simplified_datapoints
from openharness.impact.frameworks.sfdr_v2 import (
    PortfolioHolding,
    SFDRv2Category,
    classify_sfdr_v2,
)
from openharness.impact.metric_records import (
    comparability_score,
    portfolio_comparability_index,
)
from openharness.impact.deal_gate import TargetCondition, gate_with_targets
from openharness.impact.models import Company, MetricRecord
from openharness.impact.regulatory_calendar import issb_status, issb_summary
from openharness.impact.regulatory_packs import ca_climate_scope
from openharness.impact.standards_registry import load_articles, mandatory_gap_scan
from openharness.impact.xbrl_export import render_ixbrl, tag_records


def _record(metric_id: str = "OI4112", **updates) -> MetricRecord:
    payload = {
        "metric_id": metric_id,
        "value": 10,
        "unit": "tCO2e",
        "period": "2026-12-31",
        "source": "ledger",
        "owner": "CFO",
        "quality_score": 90,
        "verification_status": "third_party_verified",
        "boundary": "operational control",
        "methodology": "GHG Protocol",
    }
    payload.update(updates)
    return MetricRecord.model_validate(payload)


def test_regulatory_currency_assets_and_boundaries() -> None:
    result = classify_sfdr_v2(
        [
            PortfolioHolding(name="A", weight=0.7, follows_esg_strategy=True),
            PortfolioHolding(name="B", weight=0.3),
        ],
        SFDRv2Category.SUSTAINABLE,
    )
    assert result.eligible and result.legal_status == "proposal"
    assert len(load_simplified_datapoints()) == 430
    assert len(issb_summary()) >= 36
    assert issb_status("Hong Kong")["effective"] == "2025-08-01"
    assert ca_climate_scope(1_000_000_000, True)["sb253"] is False
    assert ca_climate_scope(1_000_000_001, True)["sb253"] is True


def test_concordance_xbrl_and_comparability_acceptance() -> None:
    concordance = load_concordance()
    assert len(concordance.entries) >= 20
    record = _record()
    translations = concordance.translate(record, "gri")
    assert translations[0][0].datapoint_id == "305-1"
    tags, untaggable = tag_records([record], "esrs_set1", concordance)
    assert tags and not untaggable
    assert "ix:nonFraction" in render_ixbrl("<html><body></body></html>", tags, "A", record.period)
    assert comparability_score(record, concordance)["score"] == 100
    portfolio = portfolio_comparability_index(
        {"A": [record], "B": [record], "C": [record]}, concordance
    )
    assert portfolio["index"] == 100 and portfolio["shared_concepts"]


def test_contribution_monitoring_and_burden_reduction() -> None:
    claim = ContributionClaim(
        claim_id="c1",
        company="A",
        channel=ContributionChannel.NON_FINANCIAL_SUPPORT,
        narrative="Board support",
        stated_at="2025-01-01",
        planned_activities=[{"activity_id": "board", "description": "Board work"}],
    )
    evidence = ContributionEvidence(
        activity_id="board",
        occurred_at="2026-06-01",
        description="Minutes",
        artifact_refs=["minutes"],
    )
    score = contribution_scorecard([claim], [evidence], [], as_of=date(2026, 7, 1))
    assert score["claims"][0]["grade"] == "A"
    packs = [
        {"pack_id": "a", "fields": [{"id": "one", "label": "Scope 1 emissions"}]},
        {"pack_id": "b", "fields": [{"id": "two", "label": "Direct GHG"}]},
    ]
    consolidated = dedupe_requests(packs)
    assert len(consolidated["consolidated"]) == 1
    assert burden_report(packs, consolidated)["estimated_hours_saved"] > 0


def test_china_reporting_materiality_and_articles() -> None:
    assert classify_cn_disclosure("chinext", [], False)["mandatory"] is False
    assert classify_cn_disclosure("chinext", ["chinext_index"], False)["mandatory"] is True
    assert len(load_cn_topics()) == 21
    assert len(load_checklist("climate").pillars) == 4
    results = assess_materiality(
        ["climate"],
        [
            ImpactMaterialityScore(
                topic_id="climate", scale=5, scope=5, irremediability=5, likelihood=5
            )
        ],
        [FinancialMaterialityInput(topic_id="climate", qualitative_band="high")],
    )
    assert results[0].quadrant == "dual" and results[0].disclose
    articles = load_articles("sse_g14")
    assert len(articles) == 63
    assert {
        mode: sum(a.modality == mode for a in articles)
        for mode in {"shall", "encouraged", "neutral"}
    } == {"shall": 49, "encouraged": 7, "neutral": 7}
    assert mandatory_gap_scan("sse_g14", [str(i) for i in range(1, 64)])["gaps"] == []


def test_calculators_cids_and_ddq_bank() -> None:
    assert scope1_mass_balance([{"mass": 12, "carbon_content": 1}], [])["emissions_tco2e"] == 44
    assert scope3_estimate({1: {"activity": 10, "factor": 2}})["category_count"] == 15
    assert energy_to_tce([{"fuel": "raw_coal", "quantity_kg": 1000}])["total_tce"] > 0
    assert water_balance([{"source_type": "reclaimed", "volume": 100}], 20)["consumption"] == 80
    cids = export_cids(Company(name="A"), None, [_record()], [])
    assert validate_cids(cids) == []
    assert len(load_ddq_bank()) == 80


def test_issa_evidence_fixture_is_constructible() -> None:
    graph = EvidenceGraph(
        nodes=[
            EvidenceNode(
                id="e1",
                type="evidence",
                label="audit",
                data={"quality_score": 90, "independent": True},
            )
        ]
    )
    assert graph.nodes[0].id == "e1"
    assert AuditTrail().head


def test_locked_kpis_promote_to_binding_conditions() -> None:
    framework = KPIFramework(
        entries=[
            KPIFrameworkEntry(
                iris_metric_id="OI4112",
                iris_metric_name="Greenhouse gas emissions",
            )
        ]
    )
    locked = lock_kpi_framework(framework)
    targets = promote_kpis_to_conditions(locked.framework_id, by_period="2028")
    assert targets[0].metric_id == "OI4112"
    assert targets[0].condition_kind == "covenant"
    gate = gate_with_targets({"deal_id": "d1"}, targets)
    assert gate["verdict"] == "pass"
    assert gate["monitoring_schedule"][0]["due"] == "2028"


def test_aspiration_only_target_does_not_pass_gate() -> None:
    target = TargetCondition(
        target_id="t1",
        metric_id="OI4112",
        target_value=5,
        by_period="2028",
        condition_kind="aspiration",
    )
    result = gate_with_targets({}, [target])
    assert result["verdict"] == "block"
    assert result["targets_set_at_investment"] is False


def test_ic_memo_and_portal_render_v6_conditions() -> None:
    from openharness.impact.fund_thesis import FundThesis
    from openharness.impact.ic_memo import render_ic_memo_markdown
    from openharness.impact.investee_portal import build_investee_portal
    from openharness.impact.models import Assessment
    from openharness.impact.deal_gate import evaluate_deal

    assessment = Assessment(
        company=Company(name="A", geography="Hong Kong"),
        assessed_at="2026-07-19",
        sdg_alignments=[],
    )
    scorecard = evaluate_deal(assessment, FundThesis())
    condition = TargetCondition(
        target_id="t1",
        metric_id="OI4112",
        target_value=5,
        by_period="2028",
        condition_kind="covenant",
    )
    memo = render_ic_memo_markdown(assessment, scorecard, target_conditions=[condition])
    assert "Impact targets as investment conditions" in memo
    assert "OI4112" in memo
    routing = {"ghg_scope1_emissions": [("lp1", "scope1", "number")]}
    portal = build_investee_portal(routing=routing)
    assert "Consolidated investor data request" in portal
    assert portal.count('name="ghg_scope1_emissions"') == 1


def test_lp_dataroom_bundle_hashes_and_writer(tmp_path) -> None:
    import hashlib
    import json

    from openharness.impact.engagements.data_room import (
        build_lp_dataroom,
        write_lp_dataroom_bundle,
    )
    from openharness.impact.signed_feed import HMACSigner

    company = Company(name="A")
    bundle = build_lp_dataroom({"name": "Fund"}, [company], {"A": [_record()]})
    assert {
        "portfolio.xbrl.json",
        "metrics.csv",
        "concordance_coverage.json",
        "comparability.json",
        "ddq_answers.xlsx",
        "portfolio.cids.json",
        "manifest.json",
    } == set(bundle["artifacts"])
    for name, digest in bundle["manifest"]["files"].items():
        assert hashlib.sha256(bundle["artifacts"][name]).hexdigest() == digest
    signature_payload = json.dumps(bundle["manifest"]["files"], sort_keys=True).encode()
    assert HMACSigner(key=b"impact-vision-lp-dataroom").verify(
        signature_payload, bundle["manifest"]["signature"]
    )
    written = write_lp_dataroom_bundle(tmp_path, {"name": "Fund"}, [company], {"A": [_record()]})
    assert len(written["files"]) == 7
