"""W1.5: engagement_suite actions are discoverable and payloads are validated."""

from __future__ import annotations

import asyncio
import json
import typing
from pathlib import Path

from impact_vision.tools.base import ToolExecutionContext
from impact_vision.tools.impact.engagement_suite_catalog import ACTION_AREAS, payload_catalog
from impact_vision.tools.impact.engagement_suite_tool import EngagementSuiteInput, EngagementSuiteTool

ACTIONS = set(typing.get_args(EngagementSuiteInput.model_fields["action"].annotation)) - {"describe"}
NO_PAYLOAD = {  # listing actions that take no arguments
    "benchmark_teaser", "build_mandate_pack", "build_practice_pack", "diagnostic_questions",
    "gallery", "list_jurisdictions", "list_report_templates", "list_verifier_marketplace",
    "list_workshop_packs", "playbooks", "cn_topics",
}


def _run(action: str, payload: dict | None = None):
    args = EngagementSuiteInput(action=action, payload=payload or {})
    return asyncio.run(EngagementSuiteTool().execute(args, ToolExecutionContext(cwd=Path("."))))


def test_every_action_has_exactly_one_area():
    listed = [a for actions in ACTION_AREAS.values() for a in actions]
    assert sorted(listed) == sorted(ACTIONS)
    assert len(listed) == len(set(listed))


def test_payload_keys_are_derived_for_every_action_that_reads_one():
    keys, open_actions = payload_catalog()
    missing = sorted(a for a in ACTIONS - NO_PAYLOAD if a not in keys and a not in open_actions)
    assert missing == []
    assert keys["build_request_pack"] == (
        "bundle_id", "counterparty_employees", "geography", "requester_in_csrd_scope", "sector", "title"
    )
    # Payloads handed to pydantic models resolve to the model's fields.
    assert "employees" in keys["assess_eu_omnibus_scope"]
    assert len(open_actions) <= 3


def test_describe_lists_areas_and_single_actions():
    everything = json.loads(_run("describe").output)
    assert set(everything) == set(ACTION_AREAS)
    one = json.loads(_run("describe", {"action": "classify_sfdr"}).output)
    assert one["area"] == "Regulatory workbench"
    assert "pai_consideration" in one["payload_keys"]


def test_typos_are_rejected_with_the_accepted_keys():
    result = _run("build_request_pack", {"bundel_id": "x"})
    assert result.is_error
    assert "bundel_id" in result.output and "bundle_id" in result.output


def test_valid_payload_still_dispatches():
    result = _run("list_jurisdictions")
    assert not result.is_error
