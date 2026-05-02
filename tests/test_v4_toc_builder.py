"""Tests for v4 Wave 2 — Theory of Change + KPI framework builder (Track 2)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from openharness.impact.audit_trail import AuditTrail
from openharness.impact.engagements import (
    EngagementWorkspace,
    ToCAssumption,
    draft_toc_from_intake,
    generate_kpi_framework,
    lock_kpi_framework,
    render_canvas_markdown,
    render_canvas_mermaid,
    validate_toc_canvas,
)
from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext


# ---------------------------------------------------------------- draft canvas


def test_draft_canvas_links_layers_sequentially() -> None:
    canvas = draft_toc_from_intake(
        name="Off-grid solar",
        problem_statement="50% of rural households lack reliable electricity.",
        stakeholders=["Rural households"],
        inputs=["EUR 5M growth equity"],
        activities=["Distribute pay-as-you-go solar kits"],
        outputs=["50,000 households with installed solar kits"],
        outcomes=["Reduced kerosene usage", "4 extra study hours per student/day"],
        impact=["Improved household health and educational attainment"],
        assumptions=["Kits are maintainable at village level"],
        risks=["Exchange-rate volatility"],
    )
    assert canvas.name == "Off-grid solar"
    # Inputs → activities → outputs → outcomes → impact, plus stakeholder links.
    kinds = {n.kind for n in canvas.nodes}
    assert {"input", "activity", "output", "outcome", "impact", "stakeholder"}.issubset(kinds)
    # Each layer's fan-out should produce at least the expected edge counts.
    assert any(e.label == "funds" for e in canvas.edges)
    assert any(e.label == "produces" for e in canvas.edges)
    assert any(e.label == "drives" for e in canvas.edges)
    assert any(e.label == "contributes to" for e in canvas.edges)
    assert any(e.label == "benefits" for e in canvas.edges)
    # Nothing starts out reviewed — the consultant must sign off explicitly.
    assert canvas.review_coverage_pct == 0.0
    assert canvas.assumptions and canvas.risks


def test_draft_canvas_ignores_blank_inputs() -> None:
    canvas = draft_toc_from_intake(
        name="Minimal",
        stakeholders=["  "],
        inputs=None,
        outcomes=["Outcome A"],
    )
    # Only the outcome survives.
    assert [n.kind for n in canvas.nodes] == ["outcome"]


# ----------------------------------------------------------- logic validation


def _canvas_missing_outcomes():
    return draft_toc_from_intake(
        name="No outcomes",
        problem_statement="Gap",
        activities=["Do the thing"],
        outputs=["Thing done"],
    )


def _canvas_with_gaps():
    canvas = draft_toc_from_intake(
        name="With gaps",
        problem_statement="Gap",
        inputs=["Capital"],
        activities=["Activity"],
        outputs=["Output"],
        outcomes=["Outcome A"],
        impact=["Impact A"],
        risks=["Regulatory risk"],  # no mitigation
        assumptions=["Stakeholders will participate"],  # not tested
    )
    return canvas


def test_validator_flags_missing_outcomes_and_impact() -> None:
    canvas = _canvas_missing_outcomes()
    report = validate_toc_canvas(canvas)
    codes = {f.code for f in report.findings}
    assert "has_outcomes" in codes
    assert "has_impact" in codes
    assert report.is_passing is False


def test_validator_reports_all_rule_codes() -> None:
    canvas = _canvas_with_gaps()
    report = validate_toc_canvas(canvas)
    codes = {f.code for f in report.findings}
    # Canvas has no IRIS+ metrics on outcomes → unmeasured outcome.
    assert "outcomes_have_indicators" in codes
    # Canvas has no assumption attached to the outcome → missing assumption.
    assert "outcomes_have_assumptions" in codes
    # Risk has no mitigation → flagged.
    assert "risks_have_mitigations" in codes
    # Assumption is untested → flagged.
    assert "assumption_tested" in codes
    # No stakeholders node → flagged.
    assert "stakeholders_identified" in codes
    # No equity notes / equity segment → flagged.
    assert "equity_lens" in codes
    # Every edge is 'untested' → flagged.
    assert "causal_strength" in codes


def test_validator_is_passing_when_canvas_is_clean() -> None:
    canvas = draft_toc_from_intake(
        name="Clean",
        problem_statement="Rural electrification gap",
        stakeholders=["Rural households"],
        inputs=["Equity"],
        activities=["Distribute solar kits"],
        outputs=["50k households served"],
        outcomes=["Reduced kerosene usage"],
        impact=["Improved health"],
    )
    # Add a validated assumption attached to the outcome.
    outcome = next(n for n in canvas.nodes if n.kind == "outcome")
    canvas.assumptions.append(
        ToCAssumption(
            statement="Households maintain kits over 3+ years.",
            attaches_to=[outcome.node_id],
            tested=True,
            evidence_refs=["evidence://field-study-2025"],
        )
    )
    # Mark every edge as strong to clear the causal_strength rule.
    for edge in canvas.edges:
        edge.causal_strength = "strong"
    # Add an IRIS+ metric to the outcome to clear outcomes_have_indicators.
    outcome.iris_metrics = ["OI4112"]
    # Risks in the seed canvas were empty so risks_have_mitigations doesn't fire.
    canvas.equity_notes = "Female-headed households prioritised in distribution."

    report = validate_toc_canvas(canvas)
    codes = {f.code for f in report.findings}
    # Clean canvas — no high/critical findings.
    assert report.is_passing is True
    # These specific rules should not fire.
    for forbidden in {
        "has_outcomes",
        "has_impact",
        "has_problem_statement",
        "outcomes_have_indicators",
        "outcomes_have_assumptions",
        "stakeholders_identified",
        "equity_lens",
        "causal_strength",
    }:
        assert forbidden not in codes, forbidden


# ------------------------------------------------------------- KPI generation


def test_generate_kpi_framework_preserves_explicit_canvas_picks() -> None:
    canvas = draft_toc_from_intake(
        name="Explicit picks",
        problem_statement="x",
        inputs=["Capital"],
        activities=["Activity"],
        outputs=["Output"],
        outcomes=["Improved household income"],
        impact=["Systemic poverty reduction"],
    )
    outcome = next(n for n in canvas.nodes if n.kind == "outcome")
    outcome.iris_metrics = ["OI4112", "PI4060"]
    framework = generate_kpi_framework(
        canvas=canvas,
        sector="financial services",
        impact_themes=["financial inclusion"],
    )
    # Explicit picks should all be included.
    iris_ids = {entry.iris_metric_id for entry in framework.entries}
    assert {"OI4112", "PI4060"}.issubset(iris_ids)
    # Every entry must be tied to the outcome that spawned it.
    for entry in framework.entries:
        assert entry.outcome_node_id == outcome.node_id
        assert entry.outcome_label == outcome.label


def test_generate_kpi_framework_expands_cross_references() -> None:
    canvas = draft_toc_from_intake(
        name="XR test",
        problem_statement="x",
        outcomes=["Jobs created"],
    )
    outcome = next(n for n in canvas.nodes if n.kind == "outcome")
    # OI6213 is in the v3 cross-reference map (jobs created concept).
    outcome.iris_metrics = ["OI6213"]
    framework = generate_kpi_framework(canvas=canvas)
    entry = next(e for e in framework.entries if e.iris_metric_id == "OI6213")
    # At least one external framework mapping should come back from cross_reference.
    assert entry.frameworks, "expected cross-framework expansion"


def test_lock_kpi_framework_bumps_version_and_flags_locked() -> None:
    canvas = draft_toc_from_intake(
        name="Lock test",
        outcomes=["Outcome"],
    )
    outcome = next(n for n in canvas.nodes if n.kind == "outcome")
    outcome.iris_metrics = ["OI4112"]
    framework = generate_kpi_framework(canvas=canvas)
    assert not framework.locked
    locked = lock_kpi_framework(framework)
    assert locked.locked is True
    assert locked.version == framework.version + 1


# ----------------------------------------------------------- render integration


def test_render_mermaid_and_markdown_include_canvas_name() -> None:
    canvas = draft_toc_from_intake(
        name="Render",
        outcomes=["Outcome A"],
    )
    mermaid = render_canvas_mermaid(canvas)
    markdown = render_canvas_markdown(canvas)
    assert mermaid.startswith("flowchart")
    assert "Outcome A" in mermaid
    assert "Theory of Change — Render" in markdown
    assert "```mermaid" in markdown


# -------------------------------------------------------------- workspace wire


def test_workspace_attaches_canvas_and_runs_validator() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="ToC",
        client_name="Demo",
        bundle_id="strategy_imm",
    )
    canvas = draft_toc_from_intake(
        name="ToC",
        problem_statement="x",
        inputs=["Capital"],
        activities=["Activity"],
        outputs=["Output"],
        outcomes=["Outcome A"],
        impact=["Impact A"],
    )
    attached = workspace.attach_toc_canvas(engagement.engagement_id, canvas)
    assert attached.engagement_id == engagement.engagement_id

    # Attaching a second canvas bumps the version.
    canvas_v2 = draft_toc_from_intake(name="ToC v2", outcomes=["Outcome B"])
    attached_v2 = workspace.attach_toc_canvas(engagement.engagement_id, canvas_v2)
    assert attached_v2.version == attached.version + 1

    report = workspace.validate_toc(engagement.engagement_id)
    assert report.canvas_id == attached_v2.canvas_id


def test_workspace_generates_and_locks_kpi_framework() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="KPI",
        client_name="Demo",
        bundle_id="strategy_imm",
    )
    canvas = draft_toc_from_intake(
        name="KPI canvas",
        problem_statement="x",
        outcomes=["Jobs created"],
    )
    outcome = next(n for n in canvas.nodes if n.kind == "outcome")
    outcome.iris_metrics = ["OI6213"]
    workspace.attach_toc_canvas(engagement.engagement_id, canvas)

    framework = workspace.generate_kpi_framework_for(engagement.engagement_id)
    assert framework.metric_count >= 1

    locked = workspace.lock_kpi_framework_for(engagement.engagement_id)
    assert locked.locked is True
    again = workspace.get_kpi_framework(engagement.engagement_id)
    assert again.framework_id == locked.framework_id


def test_workspace_mark_node_reviewed_tracks_sopact_counter() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="Review",
        client_name="Demo",
        bundle_id="strategy_imm",
    )
    canvas = draft_toc_from_intake(name="x", outcomes=["O"])
    workspace.attach_toc_canvas(engagement.engagement_id, canvas)
    node = next(n for n in canvas.nodes if n.kind == "outcome")
    updated = workspace.mark_toc_node_reviewed(
        engagement.engagement_id, node.node_id, actor="consultant"
    )
    reviewed = next(n for n in updated.nodes if n.node_id == node.node_id)
    assert reviewed.consultant_reviewed is True
    assert updated.review_coverage_pct > 0.0


def test_workspace_audit_trail_records_toc_and_kpi_events() -> None:
    audit = AuditTrail(tenant_id="t", fund_id="f")
    workspace = EngagementWorkspace(audit_trail=audit)
    engagement = workspace.create_engagement(
        name="Audit", client_name="Demo", bundle_id="strategy_imm"
    )
    canvas = draft_toc_from_intake(
        name="x", outcomes=["O"], problem_statement="x"
    )
    outcome = next(n for n in canvas.nodes if n.kind == "outcome")
    outcome.iris_metrics = ["OI4112"]
    starting = audit.length
    workspace.attach_toc_canvas(engagement.engagement_id, canvas)
    workspace.validate_toc(engagement.engagement_id)
    workspace.generate_kpi_framework_for(engagement.engagement_id)
    workspace.lock_kpi_framework_for(engagement.engagement_id)
    assert audit.length >= starting + 4
    ok, _ = audit.verify()
    assert ok


def test_workspace_raises_when_no_canvas_attached() -> None:
    workspace = EngagementWorkspace()
    engagement = workspace.create_engagement(
        name="Empty", client_name="Demo", bundle_id="dd_light"
    )
    with pytest.raises(ValueError):
        workspace.validate_toc(engagement.engagement_id)
    with pytest.raises(ValueError):
        workspace.generate_kpi_framework_for(engagement.engagement_id)
    with pytest.raises(ValueError):
        workspace.get_kpi_framework(engagement.engagement_id)


# ----------------------------------------------------------------- agent tool


def _run(tool, payload):
    args = tool.input_model.model_validate(payload)
    return asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path.cwd())))


def test_toc_builder_tool_is_registered() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("toc_builder")
    assert tool is not None
    assert tool.description


def test_toc_tool_full_flow_smoke() -> None:
    registry = create_default_tool_registry()
    eng_tool = registry.get("engagement_workspace")
    toc_tool = registry.get("toc_builder")
    assert eng_tool is not None and toc_tool is not None

    created = _run(
        eng_tool,
        {
            "action": "create_engagement",
            "bundle_id": "strategy_imm",
            "name": "Acme Strategy",
            "client_name": "Acme",
            "owner": "lead",
        },
    )
    engagement_id = created.metadata["engagement"]["engagement_id"]

    drafted = _run(
        toc_tool,
        {
            "action": "draft_canvas",
            "engagement_id": engagement_id,
            "name": "Acme ToC",
            "problem_statement": "Energy access gap.",
            "stakeholders": ["Rural households"],
            "inputs": ["Growth equity"],
            "activities": ["Distribute solar kits"],
            "outputs": ["50k kits installed"],
            "outcomes": ["Reduced kerosene usage"],
            "impact": ["Improved health outcomes"],
            "assumptions": ["Kits are maintainable"],
            "risks": ["FX volatility"],
        },
    )
    assert not drafted.is_error

    attached = _run(
        toc_tool,
        {
            "action": "attach_canvas",
            "engagement_id": engagement_id,
            "canvas": drafted.metadata["canvas"],
            "actor": "lead",
        },
    )
    assert not attached.is_error

    validated = _run(
        toc_tool, {"action": "validate", "engagement_id": engagement_id}
    )
    assert not validated.is_error
    assert validated.metadata["report"]["findings"]

    mermaid = _run(
        toc_tool,
        {
            "action": "render_mermaid",
            "engagement_id": engagement_id,
            "output_format": "text",
        },
    )
    assert not mermaid.is_error
    assert mermaid.output.startswith("flowchart")

    kpi = _run(
        toc_tool,
        {
            "action": "generate_kpi",
            "engagement_id": engagement_id,
            "sector": "energy",
            "impact_themes": ["energy access"],
            "sdg_goals": [7],
        },
    )
    assert not kpi.is_error
    assert "framework" in kpi.metadata


def test_toc_tool_validate_accepts_inline_canvas() -> None:
    registry = create_default_tool_registry()
    toc_tool = registry.get("toc_builder")
    assert toc_tool is not None

    drafted = _run(
        toc_tool,
        {
            "action": "draft_canvas",
            "name": "Inline",
            "outcomes": ["Outcome"],
        },
    )
    validated = _run(
        toc_tool,
        {
            "action": "validate",
            "canvas": drafted.metadata["canvas"],
        },
    )
    assert not validated.is_error
    assert validated.metadata["report"]["canvas_id"] == drafted.metadata["canvas"]["canvas_id"]


def test_toc_tool_is_read_only_flags() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("toc_builder")
    assert tool is not None
    assert tool.is_read_only(tool.input_model.model_validate({"action": "draft_canvas"}))
    assert tool.is_read_only(tool.input_model.model_validate({"action": "render_mermaid"}))
    assert not tool.is_read_only(
        tool.input_model.model_validate({"action": "attach_canvas", "engagement_id": "x"})
    )
    assert not tool.is_read_only(
        tool.input_model.model_validate({"action": "generate_kpi", "engagement_id": "x"})
    )
