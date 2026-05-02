"""Tests for v4 Tracks 3-10 — data room, value creation, reporting,
training, website, copilot, regulatory, verification bundle."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

import pytest

from openharness.impact.engagements import (
    BenchmarkQuery,
    DataRoomSubmission,
    DiagnosticAnswer,
    DiagnosticResult,
    EngagementQuery,
    FieldSubmission,
    ImpactRiskEntry,
    ReportSection,
    SFDRClassificationInput,
    ScenarioInput,
    UKSDRLabelInput,
    answer_from_approved_evidence,
    build_assurance_bundle,
    build_business_case,
    build_coaching_card,
    build_coaching_cards,
    build_data_request_pack,
    build_executive_deck,
    build_mandate_pack,
    build_peer_dashboard,
    build_practice_pack,
    build_public_microsite,
    build_regulator_narrative,
    build_report_from_template,
    build_reporting_pack,
    build_risk_rating,
    build_training_plan,
    build_value_creation_plan,
    capture_lead,
    classify_sfdr,
    classify_uk_sdr,
    decide_claim,
    evaluate_assurance_readiness,
    extract_meeting_notes,
    get_default_benchmark_provider,
    issue_readiness_badge,
    issue_verifier_token,
    list_diagnostic_questions,
    list_jurisdictions,
    list_verifier_marketplace,
    list_workshop_packs,
    record_learning_loop,
    rewrite_for_audiences,
    rollup_multi_entity,
    run_challenge,
    run_scenario,
    run_upload_demo,
    schedule_deadlines,
    score_completeness,
    score_diagnostic,
    score_supply_chain_hotspots,
    transition_report,
    verify_assurance_bundle,
)
from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext


# ====================================================================== Track 3


def _pack():
    return build_data_request_pack(
        engagement_id="eng-1",
        bundle_id="dd_mid",
    )


def test_data_request_pack_has_bundle_defaults() -> None:
    pack = _pack()
    assert pack.fields
    # Every field should carry a guidance card.
    for field in pack.fields:
        assert field.definition
        assert field.acceptable_evidence
        assert field.common_mistakes


def test_completeness_scoring_flags_missing_and_unverified() -> None:
    pack = _pack()
    field_oi = next(f for f in pack.fields if f.metric_id == "OI4112")
    submissions = [
        DataRoomSubmission(
            pack_id=pack.pack_id,
            engagement_id=pack.engagement_id,
            entity_name="Entity A",
            responses=[
                FieldSubmission(
                    field_id=field_oi.field_id,
                    metric_id="OI4112",
                    value="1200",
                    unit="people",
                    evidence_refs=["evidence://a"],
                )
            ],
        ),
        DataRoomSubmission(
            pack_id=pack.pack_id,
            engagement_id=pack.engagement_id,
            entity_name="Entity B",
            responses=[
                FieldSubmission(
                    field_id=field_oi.field_id,
                    metric_id="OI4112",
                    value="800",
                    # no evidence refs → unverified exception
                )
            ],
        ),
    ]
    report = score_completeness(pack, submissions)
    assert len(report.rows) == 2
    # Entity A partial (missing other required fields → coverage < 1)
    assert 0.0 < report.rows[0].coverage_pct < 1.0
    # Exceptions include at least one 'missing' and one 'unverified'.
    kinds = {exc.kind for exc in report.exceptions}
    assert "missing" in kinds
    assert "unverified" in kinds


def test_rollup_multi_entity_tracks_fill_rate() -> None:
    pack = _pack()
    field_ids = {f.metric_id: f.field_id for f in pack.fields}
    submissions = [
        DataRoomSubmission(
            pack_id=pack.pack_id,
            entity_name="A",
            responses=[
                FieldSubmission(field_id=field_ids["OI4112"], metric_id="OI4112", value="1"),
                FieldSubmission(field_id=field_ids["PI4060"], metric_id="PI4060", value="2"),
            ],
        ),
        DataRoomSubmission(
            pack_id=pack.pack_id,
            entity_name="B",
            responses=[
                FieldSubmission(field_id=field_ids["OI4112"], metric_id="OI4112", value="3"),
            ],
        ),
    ]
    rollup = rollup_multi_entity(pack, submissions)
    assert rollup.entity_count == 2
    assert rollup.per_metric_fill_rate["OI4112"] == 1.0
    assert rollup.per_metric_fill_rate["PI4060"] == 0.5
    assert rollup.fill_rate > 0.0


def test_coaching_cards_populate_guidance() -> None:
    pack = _pack()
    field_oi = next(f for f in pack.fields if f.metric_id == "OI4112")
    submissions = [
        DataRoomSubmission(
            pack_id=pack.pack_id,
            entity_name="Entity A",
            responses=[
                FieldSubmission(field_id=field_oi.field_id, metric_id="OI4112", value=""),
            ],
        ),
    ]
    report = score_completeness(pack, submissions)
    cards = build_coaching_cards(report, pack=pack, submissions=submissions)
    assert cards
    for card in cards:
        assert card.message
        assert card.suggested_action


def test_coaching_cards_preserve_entity_for_unverified_exceptions() -> None:
    """Bug regression: non-missing exceptions used to resolve to entity 'Unknown'."""
    pack = _pack()
    field_oi = next(f for f in pack.fields if f.metric_id == "OI4112")
    submissions = [
        DataRoomSubmission(
            pack_id=pack.pack_id,
            entity_name="Acme Holdings",
            responses=[
                FieldSubmission(
                    field_id=field_oi.field_id,
                    metric_id="OI4112",
                    value="1500",
                    # no evidence_refs → unverified exception
                )
            ],
        ),
    ]
    report = score_completeness(pack, submissions)
    unverified_cards = [
        c
        for c in build_coaching_cards(report, pack=pack, submissions=submissions)
        if "evidence" in c.message.lower()
    ]
    assert unverified_cards
    # Entity name threaded through via submission_id lookup.
    assert all(c.entity_name == "Acme Holdings" for c in unverified_cards)


def test_completeness_does_not_count_empty_values_as_covered() -> None:
    """Bug regression: empty-value submissions used to inflate coverage."""
    pack = _pack()
    field_oi = next(f for f in pack.fields if f.metric_id == "OI4112")
    submissions = [
        DataRoomSubmission(
            pack_id=pack.pack_id,
            entity_name="Empty Co",
            responses=[
                # Empty value — must NOT count toward coverage.
                FieldSubmission(field_id=field_oi.field_id, metric_id="OI4112", value=""),
            ],
        )
    ]
    report = score_completeness(pack, submissions)
    # 4 required fields (dd_mid), 0 covered → coverage 0.0.
    assert report.rows[0].coverage_pct == 0.0
    assert "OI4112" in report.rows[0].missing_metrics
    # The empty value should NOT be double-logged as both a missing-metric
    # exception AND a missing-value exception for OI4112.
    oi_missing = [
        e for e in report.exceptions if e.metric_id.upper() == "OI4112" and e.kind == "missing"
    ]
    assert len(oi_missing) == 1


# ====================================================================== Track 4


def test_benchmark_provider_returns_aggregates() -> None:
    provider = get_default_benchmark_provider()
    result = provider.fetch(
        BenchmarkQuery(metric_id="OI4112", sector="financial services")
    )
    assert result.sample_size > 0
    assert result.median_value is not None


def test_peer_dashboard_handles_multiple_queries() -> None:
    provider = get_default_benchmark_provider()
    dashboard = build_peer_dashboard(
        provider,
        [
            BenchmarkQuery(metric_id="OI4112", sector="financial services"),
            BenchmarkQuery(metric_id="PD5833", sector="energy"),
        ],
        engagement_id="eng-42",
    )
    assert len(dashboard.observations) == 2


def test_risk_rating_flags_material_risks() -> None:
    entries = [
        ImpactRiskEntry(title="Regulatory breach", category="regulatory", likelihood="high", severity="high"),
        ImpactRiskEntry(title="Brand issue", category="reputational", likelihood="low", severity="low"),
    ]
    rating = build_risk_rating(engagement_id="e", entries=entries)
    assert "Regulatory breach" in rating.material_risks
    assert "Brand issue" not in rating.material_risks
    assert rating.overall_score > 0.0


def test_value_creation_plan_ties_actions_to_inputs() -> None:
    plan = build_value_creation_plan(
        engagement_id="e",
        kpi_gaps=["beneficiaries reached"],
        material_risks=["Regulatory breach"],
        peer_gaps=["emissions intensity"],
    )
    assert len(plan.actions) == 3
    categories = {a.tied_to_kpi or a.tied_to_risk or a.title for a in plan.actions}
    assert any("beneficiaries" in c.lower() for c in categories)


def test_business_case_computes_uplift() -> None:
    case = build_business_case(
        engagement_id="e",
        revenue_upside_usd=1_000_000,
        cost_reduction_usd=250_000,
        risk_avoidance_usd=100_000,
        valuation_multiple=8.0,
    )
    assert case.total_financial_upside_usd == 1_350_000.0
    assert case.valuation_uplift_usd == 10_800_000.0


def test_scenario_engine_returns_downside_base_upside() -> None:
    result = run_scenario(
        metric="revenue",
        base_value=1000,
        inputs=[ScenarioInput(name="growth", base_value=1.0)],
    )
    scenarios = {o.scenario for o in result.outcomes}
    assert scenarios == {"downside", "base", "upside"}
    downside = next(o for o in result.outcomes if o.scenario == "downside")
    upside = next(o for o in result.outcomes if o.scenario == "upside")
    assert downside.value < 1000 < upside.value


def test_supply_chain_hotspots_rank_by_emissions() -> None:
    hotspots = score_supply_chain_hotspots(
        entries=[
            {"supplier_name": "A", "spend_usd": 10_000_000, "emissions_intensity_tco2e_per_musd": 200},
            {"supplier_name": "B", "spend_usd": 5_000_000, "emissions_intensity_tco2e_per_musd": 800},
        ]
    )
    assert hotspots[0].supplier_name in {"A", "B"}
    # Highest score should be 100 (normalised).
    assert hotspots[0].hotspot_score == 100.0


# ====================================================================== Track 5


def test_build_report_from_template_populates_sections() -> None:
    report = build_report_from_template(
        template_id="impact_dd",
        title="Acme DD",
        engagement_id="e",
        sections=[ReportSection(title="Executive Summary", body="Summary text")],
    )
    assert len(report.sections) >= 5
    # Supplied section body propagated.
    section = next(s for s in report.sections if s.title == "Executive Summary")
    assert section.body == "Summary text"


def test_report_state_machine_and_claim_decision() -> None:
    report = build_report_from_template(
        template_id="impact_dd", title="Acme DD",
    )
    report = transition_report(report, "in_review", actor="lead")
    report = transition_report(report, "approved", actor="reviewer")
    with pytest.raises(ValueError):
        transition_report(report, "draft", actor="x")
    report = transition_report(report, "published", actor="pub")
    # Add a claim and decide.
    from openharness.impact.engagements import ClaimReview
    report.claim_reviews.append(
        ClaimReview(claim_id="c1", text="Claim text")
    )
    decision = decide_claim(
        report, "c1", status="caveated", reviewer="lead", caveat="Data pending", evidence_refs=["e://1"]
    )
    assert decision.status == "caveated"
    assert decision.caveat == "Data pending"


def test_executive_deck_and_microsite_build() -> None:
    report = build_report_from_template(template_id="annual_impact", title="Annual")
    report.sections[0].body = "Year in review body with multiple\nbullet points\nand context."
    deck = build_executive_deck(report)
    assert len(deck.slides) >= 3
    microsite = build_public_microsite(report)
    assert microsite.pages[0].slug == "overview"


def test_rewrite_for_audiences_produces_variant_per_audience() -> None:
    rewrite = rewrite_for_audiences("Impact thesis summary", ["ic", "lp", "regulator"])
    assert set(rewrite.variants) == {"ic", "lp", "regulator"}


# ====================================================================== Track 6


def test_build_training_plan_scales_effort_by_maturity() -> None:
    plan_initial = build_training_plan(
        engagement_id="e", maturity_stage="initial", missing_topics=["theory_of_change"]
    )
    plan_managed = build_training_plan(
        engagement_id="e", maturity_stage="managed", missing_topics=["theory_of_change"]
    )
    assert plan_initial.total_effort_days > plan_managed.total_effort_days


def test_workshop_pack_lookup() -> None:
    packs = list_workshop_packs()
    assert packs
    assert all(p.agenda for p in packs)


def test_issue_readiness_badge_threshold() -> None:
    with pytest.raises(ValueError):
        issue_readiness_badge(kind="assurance_ready", issued_to="Fund", score=0.5)
    badge = issue_readiness_badge(kind="data_ready", issued_to="Fund", score=0.85)
    assert badge.kind == "data_ready"


def test_learning_loop_entry_captures_timestamp() -> None:
    loop = record_learning_loop(
        training_assigned="KPI design",
        action_completed="Ran workshop",
        data_improvement="KPI coverage up 20%",
        score_change=5.0,
    )
    assert loop.reviewed_at


def test_coaching_card_has_prescription() -> None:
    card = build_coaching_card(
        entity_name="Co", failed_validation="Missing evidence for OI4112"
    )
    assert "OI4112" in card.failed_validation
    assert card.prescription


# ====================================================================== Track 7


def test_diagnostic_scoring_ignores_duplicate_answers() -> None:
    """Bug regression: duplicate answers used to inflate max_score."""
    questions = list_diagnostic_questions()
    q0 = questions[0]
    duplicate_answers = [
        DiagnosticAnswer(question_id=q0.question_id, option_id=q0.options[0]["id"]),
        DiagnosticAnswer(question_id=q0.question_id, option_id=q0.options[-1]["id"]),
    ]
    result = score_diagnostic(duplicate_answers)
    # max_score = 4 * total questions, regardless of duplicate answers.
    assert result.max_score == 4 * len(questions)


def test_diagnostic_scoring_classifies_stage() -> None:
    questions = list_diagnostic_questions()
    assert questions
    # Answer every question at the top score.
    top_answers = [
        DiagnosticAnswer(question_id=q.question_id, option_id=q.options[-1]["id"])
        for q in questions
    ]
    top = score_diagnostic(top_answers)
    assert top.stage in {"managed", "optimising"}
    bottom = score_diagnostic(
        [
            DiagnosticAnswer(question_id=q.question_id, option_id=q.options[0]["id"])
            for q in questions
        ]
    )
    assert bottom.stage in {"initial", "developing"}


def test_capture_lead_requires_consent_and_valid_email() -> None:
    diagnostic = DiagnosticResult(
        total_score=10, max_score=28, stage="developing", category_scores={}
    )
    with pytest.raises(ValueError):
        capture_lead(email="bad", diagnostic=diagnostic, consent=True)
    with pytest.raises(ValueError):
        capture_lead(email="a@b.co", diagnostic=diagnostic, consent=False)
    lead = capture_lead(email="a@b.co", diagnostic=diagnostic, consent=True)
    assert lead.stage == "developing"


def test_upload_demo_returns_hash_only() -> None:
    result = run_upload_demo(text="Our impact thesis focuses on rural electrification.")
    assert len(result.content_hash) == 64
    assert result.word_count > 0
    # Privacy: no raw text in sample_outputs or privacy note text.
    for value in result.sample_outputs.values():
        assert "rural electrification" not in value.lower()


# ====================================================================== Track 8


def test_challenge_mode_flags_unsupported_claims() -> None:
    findings = run_challenge(
        claims=[{"claim_id": "c1", "text": "Reduced emissions by 40%"}],
        toc_validation_findings=[
            {"code": "causal_strength", "message": "Weak link detected", "severity": "low"}
        ],
        stakeholder_voice_present=False,
    )
    categories = {f.category for f in findings}
    assert "unsupported_claim" in categories
    assert "weak_toc_link" in categories
    assert "missing_stakeholder" in categories


def test_safe_answer_respects_approved_evidence_only() -> None:
    query = EngagementQuery(engagement_id="e", question="How many beneficiaries were served?")
    answer = answer_from_approved_evidence(
        query,
        approved_claims=[],
        approved_metrics=[],
    )
    assert answer.confidence == 0.0
    answer2 = answer_from_approved_evidence(
        query,
        approved_claims=[{"claim_id": "c1", "text": "Served 10000 beneficiaries."}],
        approved_metrics=[
            {"metric_id": "OI4112", "name": "Direct beneficiaries", "value": 10000, "unit": "people"}
        ],
    )
    assert answer2.confidence > 0.0
    assert answer2.citations


def test_meeting_note_extraction_parses_prefixes() -> None:
    text = (
        "Decision: Launch Q2 pilot with 2 investees.\n"
        "Action: Draft ToC by Friday.\n"
        "Risk: Supply chain exposure to FX volatility.\n"
        "Random observation about weather"
    )
    ingestion = extract_meeting_notes(raw_text=text, engagement_id="e")
    assert len(ingestion.decisions) == 1
    assert len(ingestion.action_items) == 1
    assert len(ingestion.risks) == 1


# ====================================================================== Track 9


def test_jurisdiction_profiles_are_available() -> None:
    profiles = list_jurisdictions()
    assert len(profiles) >= 6
    eu = next(p for p in profiles if p.jurisdiction == "EU")
    assert "SFDR" in eu.frameworks[0] or any("SFDR" in f for f in eu.frameworks)


def test_sfdr_classifier_assigns_article() -> None:
    article_9 = classify_sfdr(
        SFDRClassificationInput(
            promotes_environmental_social=True,
            sustainable_investment_objective=True,
            pai_consideration=True,
            do_no_significant_harm_embedded=True,
        )
    )
    assert article_9.article == "article_9"
    assert article_9.requires_pai_statement is True
    article_6 = classify_sfdr(
        SFDRClassificationInput(
            promotes_environmental_social=False,
            sustainable_investment_objective=False,
        )
    )
    assert article_6.article == "article_6"


def test_uk_sdr_label_checks_anti_greenwashing() -> None:
    result = classify_uk_sdr(
        UKSDRLabelInput(
            primary_objective="impact",
            evidence_of_impact=True,
            anti_greenwashing_reviewed=True,
        )
    )
    assert result.can_use_label is True
    assert result.label == "sustainability_impact"
    blocked = classify_uk_sdr(
        UKSDRLabelInput(
            primary_objective="impact",
            evidence_of_impact=False,
            anti_greenwashing_reviewed=False,
        )
    )
    assert blocked.can_use_label is False
    assert blocked.caveats


def test_schedule_deadlines_marks_status() -> None:
    fy_end = (date.today() + timedelta(days=40)).isoformat()
    deadlines = schedule_deadlines(
        engagement_id="e",
        jurisdiction="EU",
        fiscal_year_end=fy_end,
        owner="ESG lead",
    )
    assert deadlines
    assert any(d.status in {"upcoming", "due_soon"} for d in deadlines)


def test_regulator_narrative_incorporates_obligations() -> None:
    narrative = build_regulator_narrative(
        engagement_id="e",
        jurisdiction="EU",
        approved_metrics_summary="Approved metrics for FY26 are covered.",
        known_gaps=["Article 8 PAI statement pending sign-off"],
    )
    assert narrative.sections
    assert any("CSRD" in s["title"] or "SFDR" in s["title"] for s in narrative.sections)
    assert narrative.caveats


# ===================================================================== Track 10


def test_assurance_bundle_signature_roundtrip() -> None:
    mandate = build_mandate_pack(engagement_id="e")
    practice = build_practice_pack(engagement_id="e")
    reporting = build_reporting_pack(engagement_id="e", claims=[{"text": "Claim A"}])
    bundle = build_assurance_bundle(
        engagement_id="e", mandate=mandate, practice=practice, reporting=reporting
    )
    assert verify_assurance_bundle(bundle) is True
    # Tamper and re-verify.
    bundle.reporting.claims[0].text = "Different claim"
    assert verify_assurance_bundle(bundle) is False


def test_readiness_badge_requires_completion() -> None:
    mandate = build_mandate_pack(engagement_id="e")
    practice = build_practice_pack(engagement_id="e")
    reporting = build_reporting_pack(engagement_id="e")
    bundle = build_assurance_bundle(
        engagement_id="e", mandate=mandate, practice=practice, reporting=reporting
    )
    badge = evaluate_assurance_readiness(bundle)
    assert badge.is_assurance_ready is False
    assert badge.gaps

    # Mark everything verified and re-evaluate.
    for item in bundle.mandate.items:
        item.status = "verified"
    for item in bundle.practice.items:
        item.status = "verified"
    # Re-build to recompute hashes for any future verification.
    complete_bundle = build_assurance_bundle(
        engagement_id="e",
        mandate=bundle.mandate,
        practice=bundle.practice,
        reporting=bundle.reporting,
    )
    badge2 = evaluate_assurance_readiness(complete_bundle)
    # Reporting pack is still empty (no claims) → 0 completion but the rule only
    # checks the configured threshold per pillar; empty claims → completion 0.
    # So assurance_ready is still False but mandate + practice gaps are gone.
    assert len(badge2.gaps) <= 1


def test_verifier_token_hashes_secret() -> None:
    record, plaintext = issue_verifier_token(
        engagement_id="e", verifier_name="BlueMark"
    )
    assert record.token_hash != plaintext
    assert record.engagement_id == "e"


def test_verifier_marketplace_populated() -> None:
    listings = list_verifier_marketplace()
    names = {listing.name for listing in listings}
    assert {"BlueMark"}.issubset(names)


# =============================================================== workspace hook


def test_workspace_record_artifact_writes_audit_event() -> None:
    """Generic v4 artifact hook should land in the hash-chained audit trail."""
    from openharness.impact.audit_trail import AuditTrail
    from openharness.impact.engagements import EngagementWorkspace

    audit = AuditTrail(tenant_id="t", fund_id="f")
    workspace = EngagementWorkspace(audit_trail=audit)
    engagement = workspace.create_engagement(
        name="Acme DD",
        client_name="Acme",
        client_type="fund",
        bundle_id="dd_mid",
    )
    before = len(audit.feed.reports)
    workspace.record_artifact(
        engagement.engagement_id,
        kind="assurance_bundle.signed",
        artifact_id="bundle_123",
        metadata={"pillars": 3},
    )
    after = len(audit.feed.reports)
    assert after == before + 1
    last = audit.feed.reports[-1]
    assert last.report_kind == "engagement.assurance_bundle.signed"
    assert last.payload["artifact_id"] == "bundle_123"
    assert last.payload["metadata"] == {"pillars": 3}


def test_workspace_record_artifact_requires_known_engagement() -> None:
    from openharness.impact.engagements import EngagementWorkspace

    workspace = EngagementWorkspace()
    with pytest.raises(KeyError):
        workspace.record_artifact("unknown_eng", kind="report.built")


# ====================================================================== tool


def _run(tool, payload):
    args = tool.input_model.model_validate(payload)
    return asyncio.run(tool.execute(args, ToolExecutionContext(cwd=Path.cwd())))


def test_engagement_suite_tool_is_registered() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("engagement_suite")
    assert tool is not None


def test_engagement_suite_covers_every_track_smoke() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("engagement_suite")
    assert tool is not None

    # Track 3 — build a request pack.
    r = _run(
        tool,
        {
            "action": "build_request_pack",
            "engagement_id": "e1",
            "payload": {"bundle_id": "dd_mid"},
        },
    )
    assert not r.is_error
    assert r.metadata["pack"]

    # Track 4 — benchmark.
    r = _run(
        tool,
        {
            "action": "benchmark",
            "payload": {
                "queries": [{"metric_id": "OI4112", "sector": "financial services"}]
            },
        },
    )
    assert not r.is_error

    # Track 5 — list templates.
    r = _run(tool, {"action": "list_report_templates", "payload": {}})
    assert not r.is_error
    assert r.metadata["templates"]

    # Track 6 — training plan.
    r = _run(
        tool,
        {
            "action": "training_plan",
            "engagement_id": "e1",
            "payload": {"missing_topics": ["theory_of_change"]},
        },
    )
    assert not r.is_error

    # Track 7 — diagnostic questions.
    r = _run(tool, {"action": "diagnostic_questions", "payload": {}})
    assert not r.is_error
    assert r.metadata["questions"]

    # Track 8 — run challenge.
    r = _run(
        tool,
        {
            "action": "run_challenge",
            "payload": {
                "claims": [{"claim_id": "c1", "text": "claim"}],
                "stakeholder_voice_present": False,
            },
        },
    )
    assert not r.is_error

    # Track 9 — list jurisdictions.
    r = _run(tool, {"action": "list_jurisdictions", "payload": {}})
    assert not r.is_error

    # Track 10 — build & verify assurance bundle.
    mandate = _run(tool, {"action": "build_mandate_pack", "engagement_id": "e1", "payload": {}}).metadata["pack"]
    practice = _run(tool, {"action": "build_practice_pack", "engagement_id": "e1", "payload": {}}).metadata["pack"]
    reporting = _run(tool, {"action": "build_reporting_pack", "engagement_id": "e1", "payload": {}}).metadata["pack"]
    bundle = _run(
        tool,
        {
            "action": "build_assurance_bundle",
            "engagement_id": "e1",
            "payload": {"mandate": mandate, "practice": practice, "reporting": reporting},
        },
    ).metadata["bundle"]
    verify = _run(
        tool, {"action": "verify_assurance_bundle", "payload": {"bundle": bundle}}
    )
    assert verify.metadata["is_valid"] is True


def test_engagement_suite_readonly_classification() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("engagement_suite")
    assert tool is not None
    # Read-only action.
    assert tool.is_read_only(
        tool.input_model.model_validate({"action": "diagnostic_questions"})
    )
    # State-changing action.
    assert not tool.is_read_only(
        tool.input_model.model_validate({"action": "build_assurance_bundle"})
    )


def test_engagement_suite_reports_errors_cleanly() -> None:
    """Malformed payloads should surface as is_error=True (not uncaught)."""
    registry = create_default_tool_registry()
    tool = registry.get("engagement_suite")
    assert tool is not None

    # Missing required bundle_id.
    r = _run(tool, {"action": "build_request_pack", "engagement_id": "e1", "payload": {}})
    assert r.is_error
    # Unknown template.
    r2 = _run(
        tool,
        {
            "action": "build_report",
            "payload": {"template_id": "does_not_exist", "title": "X"},
        },
    )
    assert r2.is_error
    # Invalid transition.
    bad = _run(
        tool,
        {
            "action": "transition_report",
            "payload": {
                "report": {
                    "title": "T",
                    "template_id": "imm_baseline",
                    "sections": [],
                    "approval_state": "draft",
                },
                "next_state": "published",
                "actor": "x",
            },
        },
    )
    assert bad.is_error


def test_sfdr_classification_matrix() -> None:
    """Exhaustive check on the four SFDR input permutations."""
    # Art 6: neither promotes nor targets sustainability.
    r1 = classify_sfdr(
        SFDRClassificationInput(
            promotes_environmental_social=False,
            sustainable_investment_objective=False,
        )
    )
    assert r1.article == "article_6"
    # Art 8 with PAI considered: no gap note for PAI.
    r2 = classify_sfdr(
        SFDRClassificationInput(
            promotes_environmental_social=True,
            sustainable_investment_objective=False,
            pai_consideration=True,
        )
    )
    assert r2.article == "article_8"
    assert all("PAI" not in g for g in r2.gaps)
    # Art 9 without DNSH: flagged as gap.
    r3 = classify_sfdr(
        SFDRClassificationInput(
            promotes_environmental_social=True,
            sustainable_investment_objective=True,
            pai_consideration=True,
            do_no_significant_harm_embedded=False,
        )
    )
    assert r3.article == "article_9"
    assert any("DNSH" in g or "Do-No-Significant" in g or "significant harm" in g.lower() for g in r3.gaps)
    # Art 9 complete.
    r4 = classify_sfdr(
        SFDRClassificationInput(
            promotes_environmental_social=True,
            sustainable_investment_objective=True,
            pai_consideration=True,
            do_no_significant_harm_embedded=True,
        )
    )
    assert r4.article == "article_9"
    assert r4.requires_pai_statement is True


def test_schedule_deadlines_flags_overdue_and_due_soon() -> None:
    """Overdue fiscal year ends produce overdue deadlines; near ones produce due_soon."""
    past_fy_end = (date.today() - timedelta(days=200)).isoformat()  # +90 → overdue
    deadlines = schedule_deadlines(
        engagement_id="e", jurisdiction="EU", fiscal_year_end=past_fy_end
    )
    assert any(d.status == "overdue" for d in deadlines)

    near_fy_end = (date.today() - timedelta(days=80)).isoformat()  # +90 → 10 days left
    deadlines = schedule_deadlines(
        engagement_id="e", jurisdiction="EU", fiscal_year_end=near_fy_end
    )
    assert any(d.status == "due_soon" for d in deadlines)


def test_copilot_queue_blocks_unsafe_approval() -> None:
    """Queue should refuse approval of low-confidence or unsourced outputs."""
    from openharness.impact.engagements import CopilotOutput, CopilotReviewQueue

    queue = CopilotReviewQueue()
    low_confidence = CopilotOutput(
        kind="claim_draft",
        prompt="draft a claim",
        response="The fund reached 10k beneficiaries.",
        confidence=0.3,
        source_refs=["evidence://1"],
    )
    queue.enqueue(low_confidence)
    with pytest.raises(ValueError):
        queue.decide(
            low_confidence.output_id, decision="approved", reviewer="x"
        )

    unsourced = CopilotOutput(
        kind="claim_draft",
        prompt="draft a claim",
        response="...",
        confidence=0.9,
        source_refs=[],
    )
    queue.enqueue(unsourced)
    with pytest.raises(ValueError):
        queue.decide(
            unsourced.output_id, decision="approved", reviewer="x"
        )

    # approved_with_edits bypasses the strict gate but still needs the
    # policy_passed computed field to detect the missing source.
    reviewed = queue.decide(
        unsourced.output_id,
        decision="approved_with_edits",
        reviewer="x",
        reviewer_edits="Rewrote to cite approved evidence",
    )
    assert reviewed.decision == "approved_with_edits"
    assert reviewed.policy_passed is False  # still no source_refs
