"""Tests for v4 Wave 1 — Consultant Engagement Workspace (Track 1)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from openharness.impact.audit_trail import AuditTrail
from openharness.impact.engagements import (
    CLIENT_TEMPLATE_LIBRARY,
    ENGAGEMENT_BUNDLES,
    EngagementWorkspace,
    build_consultant_checklist,
    build_proposal,
    get_bundle,
    get_client_template,
    list_bundles,
)
from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext


# --------------------------------------------------------------------- bundles


def test_all_12_engagement_bundles_are_catalogued() -> None:
    expected = {
        "strategy_imm",
        "dd_light",
        "dd_mid",
        "dd_full_iwa",
        "esg_baseline",
        "annual_impact_report",
        "lp_ddq",
        "verification_3pillar",
        "exit_vdd",
        "regulatory",
        "stakeholder_voice",
        "capacity_training",
    }
    assert expected == set(ENGAGEMENT_BUNDLES)

    listing = list_bundles()
    assert {b.bundle_id for b in listing} == expected
    # All bundles have at least one bundled tool and one deliverable.
    for bundle in listing:
        assert bundle.bundled_tools, bundle.bundle_id
        assert bundle.default_deliverables, bundle.bundle_id
        assert bundle.default_sla_days > 0, bundle.bundle_id


def test_get_bundle_raises_for_unknown_id() -> None:
    with pytest.raises(KeyError):
        get_bundle("not_a_bundle")


def test_verification_bundle_references_existing_v3_tools() -> None:
    bundle = get_bundle("verification_3pillar")
    registry = create_default_tool_registry()
    registered = {t.name for t in registry.list_tools()}
    assert bundle.bundled_tools, "verification bundle must bundle tools"
    assert set(bundle.bundled_tools).issubset(registered), (
        set(bundle.bundled_tools) - registered
    )


# ------------------------------------------------------------------- checklist


def test_build_checklist_chains_items_sequentially() -> None:
    items = build_consultant_checklist(
        ["discovery", "data_request", "reporting"],
        owner="consultant",
    )
    assert len(items) >= 6  # each phase has >= 2 default items
    assert items[0].phase == "discovery"
    assert items[-1].phase == "reporting"
    assert items[0].depends_on == []
    for previous, current in zip(items, items[1:]):
        assert current.depends_on == [previous.item_id]
    assert all(item.owner == "consultant" for item in items)


def test_build_checklist_accepts_extra_items() -> None:
    items = build_consultant_checklist(
        ["discovery"],
        extra_items=[{"phase": "discovery", "title": "Custom task", "description": "x"}],
    )
    titles = [item.title for item in items]
    assert "Custom task" in titles


# -------------------------------------------------------------------- proposal


def test_build_proposal_produces_workplan_and_fees() -> None:
    proposal = build_proposal(
        engagement_name="Acme Q3 DD",
        client_name="Acme Capital",
        bundle_id="dd_mid",
        prepared_by="Jane Consultant",
        objectives=["Validate impact thesis", "Produce KPI annex"],
    )
    assert proposal.engagement_name == "Acme Q3 DD"
    assert proposal.bundle_id == "dd_mid"
    assert proposal.workplan  # non-empty
    assert proposal.fees
    assert proposal.total_fee_usd > 0
    # SLA days equal sum of workplan duration.
    assert sum(item.duration_days for item in proposal.workplan) == proposal.sla_days
    assert len(proposal.assumptions) >= 2
    assert len(proposal.risk_caveats) >= 2
    assert proposal.checklist_preview


def test_proposal_extracts_objectives_from_intake_notes() -> None:
    proposal = build_proposal(
        engagement_name="Foundation Review",
        client_name="Demo Foundation",
        bundle_id="stakeholder_voice",
        prepared_by="consultant",
        intake_notes="- Understand grantee impact\n- Run beneficiary survey\n- Produce learning-loop writeup",
    )
    assert proposal.objectives
    assert any("beneficiary" in obj.lower() for obj in proposal.objectives)


# ------------------------------------------------------------------- templates


def test_client_templates_reference_known_bundles() -> None:
    known_bundles = set(ENGAGEMENT_BUNDLES)
    for template in CLIENT_TEMPLATE_LIBRARY.values():
        assert template.default_bundle in known_bundles, template.template_id


def test_get_client_template_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_client_template("does_not_exist")


# ------------------------------------------------------------------ workspace


def test_create_engagement_autopopulates_from_bundle() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="Demo Fund annual report",
        client_name="Demo Fund",
        client_type="fund",
        bundle_id="annual_impact_report",
        owner="lead",
    )
    bundle = get_bundle("annual_impact_report")
    assert {d.name for d in engagement.deliverables} == set(bundle.default_deliverables)
    assert engagement.checklist, "checklist should be pre-populated"
    assert engagement.bundle == "annual_impact_report"
    assert engagement.deliverable_completion_pct == 0.0
    assert engagement.checklist_completion_pct == 0.0


def test_create_engagement_from_template_overrides_bundle() -> None:
    workspace = EngagementWorkspace()
    template = get_client_template("fund_annual_cycle")
    engagement = workspace.create_engagement(
        name="Fund annual cycle",
        client_name="Demo Fund",
        template_id=template.template_id,
        client_type=template.client_type,
    )
    # Template drives the bundle + deliverable list.
    assert engagement.template_id == "fund_annual_cycle"
    assert engagement.bundle == template.default_bundle
    assert {d.name for d in engagement.deliverables} == set(
        template.recommended_deliverables
    )


def test_deliverable_state_machine_blocks_invalid_transitions() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="DD mid",
        client_name="Acme",
        bundle_id="dd_mid",
    )
    deliverable = engagement.deliverables[0]

    # Invalid first move: planned -> final (skipping intermediate states).
    with pytest.raises(ValueError):
        workspace.transition_deliverable(
            engagement.engagement_id,
            deliverable.deliverable_id,
            "final",
            actor="consultant",
        )

    # Valid path.
    for state in ("in_progress", "draft", "client_review", "final"):
        workspace.transition_deliverable(
            engagement.engagement_id,
            deliverable.deliverable_id,
            state,
            actor="consultant",
            artifact_hash="abc123" if state == "final" else "",
        )

    refreshed = workspace.get_engagement(engagement.engagement_id)
    updated = next(
        d for d in refreshed.deliverables if d.deliverable_id == deliverable.deliverable_id
    )
    assert updated.state == "final"
    assert updated.artifact_hash == "abc123"
    assert len(updated.history) == 4

    # No transitions allowed from final.
    with pytest.raises(ValueError):
        workspace.transition_deliverable(
            engagement.engagement_id,
            deliverable.deliverable_id,
            "draft",
            actor="consultant",
        )


def test_engagement_status_transitions_respect_state_machine() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="SOW",
        client_name="Acme",
        bundle_id="dd_light",
    )
    assert engagement.status == "proposal"
    workspace.transition_engagement(engagement.engagement_id, "active", actor="ops")
    workspace.transition_engagement(engagement.engagement_id, "on_hold", actor="ops")
    workspace.transition_engagement(engagement.engagement_id, "active", actor="ops")
    workspace.transition_engagement(engagement.engagement_id, "closed", actor="ops")
    with pytest.raises(ValueError):
        workspace.transition_engagement(engagement.engagement_id, "active", actor="ops")


def test_checklist_updates_and_completion_percentages() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="Strategy",
        client_name="Demo",
        bundle_id="strategy_imm",
        owner="lead",
    )
    total = len(engagement.checklist)
    assert total > 0
    # Complete half of the items and assert percentage reflects that.
    half = total // 2
    for item in engagement.checklist[:half]:
        workspace.update_checklist_item(
            engagement.engagement_id,
            item.item_id,
            status="completed",
            actor="lead",
        )
    refreshed = workspace.get_engagement(engagement.engagement_id)
    assert refreshed.checklist_completion_pct == round(half / total, 3)


def test_document_attachment_hashes_content_for_audit_without_storing_it() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="DD-Full",
        client_name="Demo",
        bundle_id="dd_full_iwa",
    )
    document = workspace.attach_document(
        engagement.engagement_id,
        kind="intake_doc",
        name="pitch_deck.pdf",
        uri="s3://bucket/pitch_deck.pdf",
        content="fake bytes",
        uploaded_by="analyst",
    )
    assert document.content_hash  # non-empty
    assert document.uri == "s3://bucket/pitch_deck.pdf"
    assert document.content_hash != "fake bytes"
    refreshed = workspace.get_engagement(engagement.engagement_id)
    assert refreshed.documents == [document]


def test_decisions_and_overrides_are_captured_for_sopact_counter() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="ToC workshop",
        client_name="Demo",
        bundle_id="strategy_imm",
    )
    decision = workspace.record_decision(
        engagement.engagement_id,
        title="Adopt outcome X over outcome Y",
        rationale="Stronger evidence base and stakeholder alignment.",
        decided_by="lead",
    )
    override = workspace.record_override(
        engagement.engagement_id,
        target_kind="toc_outcome",
        target_id="outcome-42",
        consultant_decision="Rejected AI-suggested outcome — unsupported.",
        overridden_by="lead",
        ai_suggestion="Increased rural household incomes by 25%.",
        rationale="No baseline data in intake docs.",
    )
    refreshed = workspace.get_engagement(engagement.engagement_id)
    assert refreshed.decisions == [decision]
    assert refreshed.overrides == [override]


def test_workspace_audit_trail_receives_state_changes() -> None:
    audit = AuditTrail(tenant_id="t1", fund_id="engagements")
    workspace = EngagementWorkspace(audit_trail=audit)
    starting_len = audit.length
    engagement = workspace.create_engagement(
        name="Annual report",
        client_name="Demo Fund",
        bundle_id="annual_impact_report",
    )
    workspace.transition_deliverable(
        engagement.engagement_id,
        engagement.deliverables[0].deliverable_id,
        "in_progress",
        actor="lead",
    )
    workspace.record_override(
        engagement.engagement_id,
        target_kind="ai_extraction",
        target_id="claim-1",
        consultant_decision="Rejected",
        overridden_by="lead",
    )
    assert audit.length >= starting_len + 3
    ok, _ = audit.verify()
    assert ok


def test_export_and_import_state_round_trip() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="Round-trip",
        client_name="Demo",
        bundle_id="dd_light",
    )
    snapshot = workspace.export_state()

    restored = EngagementWorkspace()
    restored.import_state(snapshot)
    assert restored.get_engagement(engagement.engagement_id).name == "Round-trip"


def test_list_engagements_supports_filters() -> None:
    workspace = EngagementWorkspace()
    workspace.create_engagement(
        name="Fund DD", client_name="A", bundle_id="dd_light", client_type="fund"
    )
    workspace.create_engagement(
        name="Foundation review",
        client_name="B",
        bundle_id="stakeholder_voice",
        client_type="foundation",
    )
    assert len(workspace.list_engagements(client_type="fund")) == 1
    assert len(workspace.list_engagements(client_type="foundation")) == 1
    assert len(workspace.list_engagements()) == 2


# ------------------------------------------------------------------ agent tool


def test_engagement_workspace_tool_is_registered() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("engagement_workspace")
    assert tool is not None
    assert tool.description


def _run(tool, payload):
    args = tool.input_model.model_validate(payload)
    return asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path.cwd())))


def test_engagement_tool_full_flow_smoke() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("engagement_workspace")
    assert tool is not None

    bundles = _run(tool, {"action": "list_bundles"})
    assert not bundles.is_error
    assert len(bundles.metadata["bundles"]) == 12

    templates = _run(tool, {"action": "list_templates"})
    assert not templates.is_error
    assert templates.metadata["templates"]

    proposal = _run(
        tool,
        {
            "action": "build_proposal",
            "bundle_id": "dd_mid",
            "name": "Acme DD",
            "client_name": "Acme",
            "prepared_by": "consultant",
            "objectives": ["Validate thesis", "Produce KPI annex"],
            "day_rate_usd": 2000,
        },
    )
    assert not proposal.is_error
    assert proposal.metadata["proposal"]["total_fee_usd"] > 0

    created = _run(
        tool,
        {
            "action": "create_engagement",
            "bundle_id": "dd_mid",
            "name": "Acme DD",
            "client_name": "Acme",
            "client_type": "fund",
            "owner": "consultant",
        },
    )
    assert not created.is_error
    engagement_id = created.metadata["engagement"]["engagement_id"]
    deliverable_id = created.metadata["engagement"]["deliverables"][0]["deliverable_id"]

    transition = _run(
        tool,
        {
            "action": "transition_deliverable",
            "engagement_id": engagement_id,
            "deliverable_id": deliverable_id,
            "next_state": "in_progress",
            "actor": "consultant",
        },
    )
    assert not transition.is_error
    assert transition.metadata["deliverable"]["state"] == "in_progress"

    summary = _run(
        tool,
        {
            "action": "summarize_engagement",
            "engagement_id": engagement_id,
        },
    )
    assert not summary.is_error
    assert summary.metadata["summary"]["deliverable_count"] > 0


def test_engagement_tool_rejects_invalid_state_transition() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("engagement_workspace")
    assert tool is not None

    created = _run(
        tool,
        {
            "action": "create_engagement",
            "bundle_id": "dd_light",
            "name": "Invalid-flow",
            "client_name": "Demo",
        },
    )
    engagement_id = created.metadata["engagement"]["engagement_id"]
    deliverable_id = created.metadata["engagement"]["deliverables"][0]["deliverable_id"]

    bad = _run(
        tool,
        {
            "action": "transition_deliverable",
            "engagement_id": engagement_id,
            "deliverable_id": deliverable_id,
            "next_state": "final",
            "actor": "consultant",
        },
    )
    assert bad.is_error
    assert "Invalid deliverable transition" in bad.output


def test_engagement_tool_is_read_only_flags() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("engagement_workspace")
    assert tool is not None
    assert tool.is_read_only(tool.input_model.model_validate({"action": "list_bundles"}))
    assert tool.is_read_only(tool.input_model.model_validate({"action": "build_proposal", "bundle_id": "dd_mid"}))
    assert not tool.is_read_only(
        tool.input_model.model_validate({"action": "create_engagement", "bundle_id": "dd_mid"})
    )
