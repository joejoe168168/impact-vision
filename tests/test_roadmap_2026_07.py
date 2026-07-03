"""Tests for the July-2026 roadmap-update items.

Covers the four tickets in ``docs/roadmap-updates-2026-07.md``:
SFDR 2.0 category preview, AI-estimate provenance flag, EDCI-first
collection scaffold, and the regulatory milestone watch-list.
"""

from __future__ import annotations

import asyncio
from datetime import date


def _ctx():
    from pathlib import Path

    from openharness.tools.base import ToolExecutionContext

    return ToolExecutionContext(cwd=Path.cwd())


# --------------------------------------------------------------- SFDR 2.0
def test_sfdr2_sustainable_candidate_threshold_met() -> None:
    from openharness.impact.frameworks.sfdr_pai import SFDR2Input, classify_sfdr2_category

    res = classify_sfdr2_category(SFDR2Input(
        current_article=9,
        has_sustainable_objective=True,
        pct_strategy_aligned=85.0,
    ))
    assert res.category == "sustainable"
    assert res.threshold_met is True
    assert not res.exclusion_flags
    assert "PROPOSED LAW" in res.status
    assert res.migration_note  # Art 9 migration hint


def test_sfdr2_transition_candidate_from_signals() -> None:
    from openharness.impact.frameworks.sfdr_pai import SFDR2Input, classify_sfdr2_category

    res = classify_sfdr2_category(SFDR2Input(
        current_article=8,
        description="Portfolio companies follow SBTi-validated transition plans",
        pct_strategy_aligned=60.0,
        fund_in_ramp_up=True,
    ))
    assert res.category == "transition"
    assert res.threshold_met is False
    # Council phase-in relief surfaces as a caveat, not a pass.
    assert any("phase-in" in c for c in res.caveats)


def test_sfdr2_exclusions_and_unclassified() -> None:
    from openharness.impact.frameworks.sfdr_pai import SFDR2Input, classify_sfdr2_category

    res = classify_sfdr2_category(SFDR2Input(
        has_sustainable_objective=True,
        pct_strategy_aligned=90.0,
        invests_in_controversial_weapons=True,
        has_ungc_oecd_violators=True,
    ))
    assert len(res.exclusion_flags) == 2

    plain = classify_sfdr2_category(SFDR2Input(description="A generalist buyout fund"))
    assert plain.category == "unclassified"
    assert plain.threshold_met is None


def test_sfdr2_missing_threshold_input_is_a_caveat() -> None:
    from openharness.impact.frameworks.sfdr_pai import SFDR2Input, classify_sfdr2_category

    res = classify_sfdr2_category(SFDR2Input(current_article=8, applies_binding_esg_criteria=True))
    assert res.category == "esg_basics"
    assert res.threshold_met is None
    assert any("70%" in c for c in res.caveats)


def test_sfdr2_via_framework_tool() -> None:
    from openharness.tools.impact.framework_tool import FrameworkTool

    tool = FrameworkTool()
    listed = asyncio.run(tool.execute({"framework": "sfdr2", "action": "list"}, _ctx()))
    assert not listed.is_error
    assert "esg_basics" in listed.output

    assessed = asyncio.run(tool.execute({
        "framework": "sfdr2",
        "action": "assess",
        "sfdr2_inputs": {"current_article": 9, "pct_strategy_aligned": 75},
    }, _ctx()))
    assert not assessed.is_error
    assert assessed.metadata["category"] == "sustainable"
    assert assessed.metadata["threshold_met"] is True

    bad = asyncio.run(tool.execute({
        "framework": "sfdr2",
        "action": "assess",
        "sfdr2_inputs": {"pct_strategy_aligned": 250},
    }, _ctx()))
    assert bad.is_error


# ------------------------------------------------------ estimate provenance
def test_metric_record_is_estimate_flag() -> None:
    from openharness.impact.models import MetricRecord

    base = dict(metric_id="OI4112", value=100, unit="tCO2e", period="FY2025",
                source="model", owner="analyst", quality_score=50)
    measured = MetricRecord(**base, verification_status="third_party_verified")
    assert measured.is_estimate is False

    proxy = MetricRecord(**base, verification_status="proxy_estimate")
    assert proxy.is_estimate is True

    modelled = MetricRecord(**base, estimation_methodology="EEIO spend-based model")
    assert modelled.is_estimate is True
    # Computed field serializes so every report surface sees it.
    assert modelled.model_dump()["is_estimate"] is True


def test_estimate_disclosure_label_and_flags() -> None:
    from openharness.impact.metric_records import (
        estimate_disclosure_label,
        flag_undisclosed_estimates,
    )
    from openharness.impact.models import MetricRecord

    base = dict(metric_id="OI4112", value=100, unit="tCO2e", period="FY2025",
                source="model", owner="analyst", quality_score=50)
    disclosed = MetricRecord(**base, verification_status="proxy_estimate",
                             estimation_methodology="grid-average emission factors")
    undisclosed = MetricRecord(**base, verification_status="proxy_estimate")
    measured = MetricRecord(**base, verification_status="audited")

    assert "grid-average" in estimate_disclosure_label(disclosed)
    assert "not disclosed" in estimate_disclosure_label(undisclosed)
    assert estimate_disclosure_label(measured) == ""

    warnings = flag_undisclosed_estimates([disclosed, undisclosed, measured])
    assert len(warnings) == 1
    assert "OI4112" in warnings[0]


def test_evidence_chain_metric_link_carries_estimate_badge() -> None:
    from openharness.impact.evidence_chain_renderer import MetricLink

    link = MetricLink(metric_id="OI4112", is_estimate=True, estimate_note="ESTIMATE — proxy")
    payload = link.model_dump()
    assert payload["is_estimate"] is True
    assert payload["estimate_note"].startswith("ESTIMATE")


# ------------------------------------------------------- EDCI-first scaffold
def test_edci_core_iris_metric_ids() -> None:
    from openharness.impact.frameworks.edci import edci_core_iris_metric_ids

    ids = edci_core_iris_metric_ids()
    assert ids, "core EDCI metrics should cross-reference IRIS+ IDs"
    assert len(ids) == len(set(ids))
    assert all(id_[:2] in ("PI", "OI", "OD", "FP", "PD") for id_ in ids)


def test_edci_core_data_request_pack() -> None:
    from openharness.impact.engagements.data_room import build_data_request_pack
    from openharness.impact.frameworks.edci import EDCI_METRICS

    pack = build_data_request_pack(engagement_id="eng-1", bundle_id="edci_core")
    assert len(pack.fields) == len(EDCI_METRICS)
    by_id = {f.metric_id: f for f in pack.fields}
    # Scope 3 is non-core in the 2026 cycle → optional.
    assert by_id["EDCI-E3"].required is False
    assert by_id["EDCI-E1"].required is True
    assert "EDCI" in by_id["EDCI-E1"].frameworks
    # Estimate-labelling guardrail travels with every field.
    assert any("estimate" in m.lower() for m in by_id["EDCI-E1"].common_mistakes)


def test_investee_questionnaire_edci_template() -> None:
    from openharness.impact.investee_collection import default_metric_ids_for_sector

    ids = default_metric_ids_for_sector("edci")
    assert ids
    from openharness.impact.frameworks.edci import edci_core_iris_metric_ids

    assert ids == edci_core_iris_metric_ids()
    # Sector templates unchanged.
    assert default_metric_ids_for_sector("energy") == ["OI4112", "OI6697", "PI8706", "PI2822"]


# ------------------------------------------------------------- watch-list
def test_regulatory_watchlist_sorting_and_status() -> None:
    from openharness.impact.regulatory_calendar import regulatory_watchlist

    items = regulatory_watchlist(today=date(2026, 7, 3))
    assert items
    dates = [item.event_date for item in items]
    assert dates == sorted(dates)
    ecgt = next(item for item in items if "ECGT" in item.event)
    assert ecgt.days_until == (date(2026, 9, 27) - date(2026, 7, 3)).days
    # Nothing before today unless include_passed.
    assert all(item.days_until >= 0 for item in items)

    with_passed = regulatory_watchlist(today=date(2030, 1, 1), include_passed=True)
    assert all(item.status == "passed" for item in with_passed)
    assert regulatory_watchlist(today=date(2030, 1, 1)) == []


def test_regulatory_watchlist_jurisdiction_filter() -> None:
    from openharness.impact.regulatory_calendar import regulatory_watchlist

    us_items = regulatory_watchlist(today=date(2026, 7, 3), jurisdiction="us")
    assert us_items
    assert all(item.jurisdiction == "US" for item in us_items)


def test_regulatory_calendar_tool_watchlist_action() -> None:
    from openharness.tools.impact.regulatory_calendar_tool import RegulatoryCalendarTool

    tool = RegulatoryCalendarTool()
    res = asyncio.run(tool.execute({"action": "watchlist"}, _ctx()))
    assert not res.is_error
    assert res.metadata["watchlist"]
    assert "watch-list" in res.output
