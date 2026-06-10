"""Tests for the impact_advisor router and the merged tool surfaces."""

from __future__ import annotations

import asyncio
from pathlib import Path

from openharness.impact.tool_advisor import (
    PLAYBOOKS,
    TOOL_ROUTES,
    get_playbook,
    list_playbooks,
    route_query,
    routed_tool_names,
)
from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext


def _ctx() -> ToolExecutionContext:
    return ToolExecutionContext(cwd=Path.cwd())


# ---------------------------------------------------------------------------
# Routing engine
# ---------------------------------------------------------------------------


def test_route_query_greenwashing() -> None:
    result = route_query("check this deck for greenwashing claims")
    tools = [r["tool"] for r in result["recommendations"]]
    assert "greenwashing_detect" in tools


def test_route_query_regulatory() -> None:
    result = route_query("what SFDR and CSRD deadlines apply to our EU fund?")
    tools = [r["tool"] for r in result["recommendations"]]
    assert "regulatory_calendar" in tools or "framework_assess" in tools
    assert result["playbook"] is not None
    assert result["playbook"]["playbook_id"] == "regulatory_compliance"


def test_route_query_verification() -> None:
    result = route_query("prepare for BlueMark verification")
    tools = [r["tool"] for r in result["recommendations"]]
    assert "verification_workspace" in tools


def test_route_query_phrase_outranks_token() -> None:
    result = route_query("build a theory of change with KPIs")
    assert result["recommendations"][0]["tool"] == "toc_builder"
    assert result["playbook"]["playbook_id"] == "theory_of_change"


def test_route_query_no_match() -> None:
    result = route_query("zzzz qqqq")
    assert result["recommendations"] == []
    assert result["playbook"] is None


def test_playbook_lookup() -> None:
    pb = get_playbook("deal_screening")
    assert pb is not None
    assert pb.steps[0].tool == "pitch_deck_analyze"
    assert get_playbook("does_not_exist") is None
    assert len(list_playbooks()) == len(PLAYBOOKS)


def test_routing_table_matches_registry() -> None:
    """Every tool referenced by a route or playbook must be registered."""
    registry = create_default_tool_registry()
    registered = {tool.name for tool in registry.list_tools()}
    missing = routed_tool_names() - registered
    assert not missing, f"Routes reference unregistered tools: {missing}"


def test_routes_have_keywords_and_summaries() -> None:
    for route in TOOL_ROUTES:
        assert route.keywords, f"{route.tool} has no keywords"
        assert route.summary


# ---------------------------------------------------------------------------
# impact_advisor agent tool
# ---------------------------------------------------------------------------


def test_advisor_tool_route_action() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("impact_advisor")
    assert tool is not None
    args = tool.input_model.model_validate(
        {"action": "route", "query": "generate an LP report with a narrative"}
    )
    result = asyncio.run(tool.execute(args, _ctx()))
    assert not result.is_error
    assert "impact_report" in result.output or "lp_narrative" in result.output
    assert result.metadata["recommendations"]


def test_advisor_tool_catalog_and_playbooks() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("impact_advisor")

    catalog = asyncio.run(
        tool.execute(tool.input_model.model_validate({"action": "catalog"}), _ctx())
    )
    assert not catalog.is_error
    assert "IMPACT TOOL CATALOG" in catalog.output

    listed = asyncio.run(
        tool.execute(tool.input_model.model_validate({"action": "list_playbooks"}), _ctx())
    )
    assert not listed.is_error
    assert "deal_screening" in listed.output

    pb = asyncio.run(
        tool.execute(
            tool.input_model.model_validate({"action": "playbook", "playbook_id": "lp_reporting"}),
            _ctx(),
        )
    )
    assert not pb.is_error
    assert "lp_ddq_export" in pb.output

    bad = asyncio.run(
        tool.execute(
            tool.input_model.model_validate({"action": "playbook", "playbook_id": "nope"}),
            _ctx(),
        )
    )
    assert bad.is_error


def test_advisor_tool_route_requires_query() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("impact_advisor")
    result = asyncio.run(
        tool.execute(tool.input_model.model_validate({"action": "route"}), _ctx())
    )
    assert result.is_error


# ---------------------------------------------------------------------------
# Merged tool surfaces
# ---------------------------------------------------------------------------


def test_greenwashing_detect_review_claims_action() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("greenwashing_detect")
    args = tool.input_model.model_validate(
        {
            "action": "review_claims",
            "company_name": "DemoCo",
            "sector": "energy",
            "claims": [
                {
                    "text": "Reduced 100 tCO2e in FY2025",
                    "mapped_metrics": ["OI4112"],
                    "evidence_strength": 3,
                }
            ],
        }
    )
    result = asyncio.run(tool.execute(args, _ctx()))
    assert not result.is_error
    assert "GREENWASHING REVIEWER" in result.output
    assert result.metadata["items"]


def test_greenwashing_detect_default_action_unchanged() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("greenwashing_detect")
    args = tool.input_model.model_validate(
        {"company_name": "DemoCo", "company_description": "Clean energy for rural areas"}
    )
    result = asyncio.run(tool.execute(args, _ctx()))
    assert not result.is_error


def test_verification_workspace_prep_actions() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("verification_workspace")
    args = tool.input_model.model_validate(
        {
            "action": "readiness_check",
            "company_name": "DemoCo",
            "sector": "energy",
            "reported_metrics": {"OI4112": "100 tCO2e"},
            "has_theory_of_change": True,
            "verification_target": "bluemark",
        }
    )
    assert tool.is_read_only(args)
    result = asyncio.run(tool.execute(args, _ctx()))
    assert not result.is_error
    assert "readiness" in result.output.lower()


def test_impact_report_narrative_section_delegation() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("impact_report")
    args = tool.input_model.model_validate(
        {
            "company_name": "Solar Co",
            "company_description": "Solar energy access for rural households",
            "sector": "Energy",
            "sdg_claims": [7, 13],
            "narrative_mode": "narrative_prompt",
            "narrative_section": "executive_summary",
            "narrative_audience": "board",
        }
    )
    result = asyncio.run(tool.execute(args, _ctx()))
    assert not result.is_error
    assert "EXECUTIVE SUMMARY PROMPT" in result.output
    assert "BOARD" in result.output
