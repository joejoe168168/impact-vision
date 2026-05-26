"""Agent tool: consolidated surface for v4 Tracks 3-10.

Rather than spawn eight near-identical tools, this single tool dispatches
to the appropriate :mod:`openharness.impact.engagements` sub-module by
``action`` name. It runs off the shared in-memory
:class:`~openharness.impact.engagements.EngagementWorkspace` singleton so
it composes cleanly with `engagement_workspace` and `toc_builder`.

Actions:

* **data_room** (Track 3): ``build_request_pack``, ``score_completeness``,
  ``rollup_entities``, ``build_coaching_cards``.
* **value_creation** (Track 4): ``benchmark``, ``risk_rating``,
  ``value_plan``, ``business_case``, ``run_scenario``, ``supply_hotspots``.
* **reporting** (Track 5): ``list_report_templates``, ``build_report``,
  ``transition_report``, ``decide_claim``, ``executive_deck``,
  ``public_microsite``, ``rewrite_audiences``.
* **training** (Track 6): ``training_plan``, ``workshop_pack``,
  ``coaching_card``, ``learning_loop``, ``issue_badge``.
* **website** (Track 7): ``diagnostic_questions``, ``score_diagnostic``,
  ``gallery``, ``playbooks``, ``benchmark_teaser``, ``capture_lead``,
  ``upload_demo``, ``partner_mode``.
* **copilot** (Track 8): ``run_challenge``, ``safe_answer``,
  ``extract_meeting_notes``.
* **regulatory** (Track 9): ``list_jurisdictions``, ``classify_sfdr``,
  ``classify_uk_sdr``, ``schedule_deadlines``, ``regulator_narrative``.
* **verification** (Track 10): ``build_bundle``, ``verify_bundle``,
  ``readiness_badge``, ``issue_verifier_token``,
  ``list_verifier_marketplace``.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.engagements import (
    BenchmarkQuery,
    ClaimReview,
    DataRoomSubmission,
    DiagnosticAnswer,
    EngagementQuery,
    ImpactRiskEntry,
    MandatePack,
    PracticePack,
    ReportSection,
    ReportingPack,
    SFDRClassificationInput,
    ScenarioInput,
    UKSDRLabelInput,
    ValueCreationAction,
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
    build_report_from_template,
    build_reporting_pack,
    build_regulator_narrative,
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
    get_playbook_page,
    get_workshop_pack,
    issue_readiness_badge,
    issue_verifier_token,
    list_diagnostic_questions,
    list_gallery_items,
    list_jurisdictions,
    list_playbook_pages,
    list_report_templates,
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
from openharness.impact.engagements.website import (
    build_benchmark_teaser,
    describe_partner_mode,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


SuiteAction = Literal[
    # Track 3
    "build_request_pack",
    "score_completeness",
    "rollup_entities",
    "build_coaching_cards",
    # Track 4
    "benchmark",
    "risk_rating",
    "value_plan",
    "business_case",
    "run_scenario",
    "supply_hotspots",
    # Track 5
    "list_report_templates",
    "build_report",
    "transition_report",
    "decide_claim",
    "executive_deck",
    "public_microsite",
    "rewrite_audiences",
    # Track 6
    "training_plan",
    "list_workshop_packs",
    "workshop_pack",
    "coaching_card",
    "learning_loop",
    "issue_badge",
    # Track 7
    "diagnostic_questions",
    "score_diagnostic",
    "gallery",
    "playbooks",
    "playbook_page",
    "benchmark_teaser",
    "capture_lead",
    "upload_demo",
    "partner_mode",
    # Track 8
    "run_challenge",
    "safe_answer",
    "extract_meeting_notes",
    # Track 9
    "list_jurisdictions",
    "classify_sfdr",
    "classify_uk_sdr",
    "schedule_deadlines",
    "regulator_narrative",
    # Track 10
    "build_mandate_pack",
    "build_practice_pack",
    "build_reporting_pack",
    "build_assurance_bundle",
    "verify_assurance_bundle",
    "readiness_badge",
    "issue_verifier_token",
    "list_verifier_marketplace",
]


class EngagementSuiteInput(BaseModel):
    """Unified input schema. Most fields are action-scoped and optional."""

    action: SuiteAction
    engagement_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    """Free-form payload for the action (validated inside the dispatcher)."""
    output_format: Literal["json", "text"] = "json"


class EngagementSuiteTool(BaseTool):
    name = "engagement_suite"
    description = (
        "Consolidated v4 Tracks 3-10 surface. One action parameter dispatches "
        "to the data room (Track 3), value-creation intelligence (4), "
        "reporting studio (5), training engine (6), public website data "
        "(7), AI copilot governance (8), regulatory workbench (9), and "
        "BlueMark-style 3-pillar verification bundle (10). Operates on the "
        "shared in-memory EngagementWorkspace singleton."
    )
    input_model = EngagementSuiteInput

    _READONLY_ACTIONS: set[str] = {
        "benchmark",
        "run_scenario",
        "supply_hotspots",
        "list_report_templates",
        "executive_deck",
        "public_microsite",
        "rewrite_audiences",
        "list_workshop_packs",
        "workshop_pack",
        "learning_loop",
        "diagnostic_questions",
        "score_diagnostic",
        "gallery",
        "playbooks",
        "playbook_page",
        "benchmark_teaser",
        "upload_demo",
        "partner_mode",
        "run_challenge",
        "safe_answer",
        "extract_meeting_notes",
        "list_jurisdictions",
        "classify_sfdr",
        "classify_uk_sdr",
        "schedule_deadlines",
        "regulator_narrative",
        "verify_assurance_bundle",
        "list_verifier_marketplace",
    }

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, EngagementSuiteInput) else (
            EngagementSuiteInput.model_validate(arguments)
        )
        return args.action in self._READONLY_ACTIONS

    async def execute(
        self,
        arguments: BaseModel,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context
        args = (
            arguments
            if isinstance(arguments, EngagementSuiteInput)
            else EngagementSuiteInput.model_validate(arguments)
        )
        try:
            payload = self._dispatch(args)
        except (KeyError, ValueError, TypeError) as exc:
            return ToolResult(output=str(exc), is_error=True)
        return ToolResult(
            output=json.dumps(payload, indent=2, default=str),
            metadata=payload,
        )

    def _dispatch(self, args: EngagementSuiteInput) -> dict[str, Any]:
        p = args.payload
        action = args.action

        # ------------- Track 3
        if action == "build_request_pack":
            pack = build_data_request_pack(
                engagement_id=args.engagement_id,
                bundle_id=p["bundle_id"],
                title=p.get("title", ""),
                sector=p.get("sector", ""),
                geography=p.get("geography", ""),
            )
            return {"pack": pack.model_dump(mode="json")}

        if action == "score_completeness":
            from openharness.impact.engagements import DataRequestPack

            pack = DataRequestPack.model_validate(p["pack"])
            submissions = [
                DataRoomSubmission.model_validate(s) for s in p.get("submissions", [])
            ]
            report = score_completeness(pack, submissions)
            return {"report": report.model_dump(mode="json")}

        if action == "rollup_entities":
            from openharness.impact.engagements import DataRequestPack

            pack = DataRequestPack.model_validate(p["pack"])
            submissions = [
                DataRoomSubmission.model_validate(s) for s in p.get("submissions", [])
            ]
            rollup = rollup_multi_entity(pack, submissions)
            return {"rollup": rollup.model_dump(mode="json")}

        if action == "build_coaching_cards":
            from openharness.impact.engagements import (
                CompletenessReport,
                DataRequestPack,
            )

            pack = DataRequestPack.model_validate(p["pack"])
            report = CompletenessReport.model_validate(p["report"])
            cards = build_coaching_cards(report, pack=pack)
            return {"cards": [c.model_dump(mode="json") for c in cards]}

        # ------------- Track 4
        if action == "benchmark":
            provider = get_default_benchmark_provider()
            queries = [BenchmarkQuery.model_validate(q) for q in p.get("queries", [])]
            dashboard = build_peer_dashboard(
                provider, queries, engagement_id=args.engagement_id
            )
            return {"dashboard": dashboard.model_dump(mode="json")}

        if action == "risk_rating":
            entries = [ImpactRiskEntry.model_validate(r) for r in p.get("entries", [])]
            rating = build_risk_rating(engagement_id=args.engagement_id, entries=entries)
            return {"rating": rating.model_dump(mode="json")}

        if action == "value_plan":
            extra = [
                ValueCreationAction.model_validate(a)
                for a in p.get("extra_actions", [])
            ]
            plan = build_value_creation_plan(
                engagement_id=args.engagement_id,
                kpi_gaps=p.get("kpi_gaps", []),
                material_risks=p.get("material_risks", []),
                peer_gaps=p.get("peer_gaps", []),
                extra_actions=extra,
            )
            return {"plan": plan.model_dump(mode="json")}

        if action == "business_case":
            # ``build_business_case`` accepts whatever fields ``BusinessCase``
            # exposes; ``engagement_id`` is one of them, so a payload that
            # also contains ``engagement_id`` would raise a duplicate-keyword
            # ``TypeError``. Strip conflicting keys and let the explicit
            # ``args.engagement_id`` win.
            payload_kwargs = {k: v for k, v in p.items() if k != "engagement_id"}
            case = build_business_case(
                engagement_id=args.engagement_id, **payload_kwargs
            )
            return {"case": case.model_dump(mode="json")}

        if action == "run_scenario":
            inputs = [ScenarioInput.model_validate(i) for i in p.get("inputs", [])]
            result = run_scenario(
                metric=p["metric"],
                base_value=float(p.get("base_value", 0.0)),
                inputs=inputs,
                engagement_id=args.engagement_id,
            )
            return {"scenario": result.model_dump(mode="json")}

        if action == "supply_hotspots":
            hotspots = score_supply_chain_hotspots(entries=p.get("entries", []))
            return {"hotspots": [h.model_dump(mode="json") for h in hotspots]}

        # ------------- Track 5
        if action == "list_report_templates":
            return {
                "templates": [t.model_dump(mode="json") for t in list_report_templates()]
            }

        if action == "build_report":
            sections = [ReportSection.model_validate(s) for s in p.get("sections", [])]
            claims = [ClaimReview.model_validate(c) for c in p.get("claim_reviews", [])]
            report = build_report_from_template(
                template_id=p["template_id"],
                title=p.get("title", "Report"),
                engagement_id=args.engagement_id,
                sections=sections or None,
                claim_reviews=claims or None,
            )
            return {"report": report.model_dump(mode="json")}

        if action == "transition_report":
            from openharness.impact.engagements import Report

            report = Report.model_validate(p["report"])
            updated = transition_report(
                report,
                p["next_state"],
                actor=p.get("actor", "system"),
                note=p.get("note", ""),
            )
            return {"report": updated.model_dump(mode="json")}

        if action == "decide_claim":
            from openharness.impact.engagements import Report

            report = Report.model_validate(p["report"])
            decision = decide_claim(
                report,
                p["claim_id"],
                status=p["status"],
                reviewer=p.get("reviewer", "consultant"),
                caveat=p.get("caveat", ""),
                evidence_refs=p.get("evidence_refs"),
            )
            return {
                "claim": decision.model_dump(mode="json"),
                "report": report.model_dump(mode="json"),
            }

        if action == "executive_deck":
            from openharness.impact.engagements import Report

            report = Report.model_validate(p["report"])
            deck = build_executive_deck(report)
            return {"deck": deck.model_dump(mode="json")}

        if action == "public_microsite":
            from openharness.impact.engagements import Report

            report = Report.model_validate(p["report"])
            microsite = build_public_microsite(report)
            return {"microsite": microsite.model_dump(mode="json")}

        if action == "rewrite_audiences":
            rewrite = rewrite_for_audiences(
                p.get("base_text", ""),
                p.get("audiences", ["lp"]),
            )
            return {"rewrite": rewrite.model_dump(mode="json")}

        # ------------- Track 6
        if action == "training_plan":
            plan = build_training_plan(
                engagement_id=args.engagement_id,
                maturity_stage=p.get("maturity_stage", "developing"),
                missing_topics=p.get("missing_topics"),
                failed_validations=p.get("failed_validations"),
                objectives=p.get("objectives"),
            )
            return {"plan": plan.model_dump(mode="json")}

        if action == "list_workshop_packs":
            return {"packs": [w.model_dump(mode="json") for w in list_workshop_packs()]}

        if action == "workshop_pack":
            return {"pack": get_workshop_pack(p["pack_id"]).model_dump(mode="json")}

        if action == "coaching_card":
            try:
                card = build_coaching_card(**p)
            except TypeError as e:
                raise ValueError(
                    f"coaching_card payload mismatch: {e}. Expected keys: "
                    "entity_name, failed_validation, prescription, example, severity"
                ) from e
            return {"card": card.model_dump(mode="json")}

        if action == "learning_loop":
            try:
                loop = record_learning_loop(**p)
            except TypeError as e:
                raise ValueError(
                    f"learning_loop payload mismatch: {e}. Expected keys: "
                    "training_assigned, action_completed, data_improvement, score_change"
                ) from e
            return {"loop": loop.model_dump(mode="json")}

        if action == "issue_badge":
            badge = issue_readiness_badge(
                kind=p["kind"],
                issued_to=p["issued_to"],
                score=float(p.get("score", 0.0)),
                criteria=p.get("criteria", ""),
            )
            return {"badge": badge.model_dump(mode="json")}

        # ------------- Track 7
        if action == "diagnostic_questions":
            return {
                "questions": [q.model_dump(mode="json") for q in list_diagnostic_questions()]
            }

        if action == "score_diagnostic":
            answers = [DiagnosticAnswer.model_validate(a) for a in p.get("answers", [])]
            result = score_diagnostic(answers)
            return {"result": result.model_dump(mode="json")}

        if action == "gallery":
            return {"items": [i.model_dump(mode="json") for i in list_gallery_items()]}

        if action == "playbooks":
            return {"pages": [pg.model_dump(mode="json") for pg in list_playbook_pages()]}

        if action == "playbook_page":
            return {"page": get_playbook_page(p["slug"]).model_dump(mode="json")}

        if action == "benchmark_teaser":
            return {"teaser": build_benchmark_teaser().model_dump(mode="json")}

        if action == "capture_lead":
            from openharness.impact.engagements import DiagnosticResult

            diagnostic = DiagnosticResult.model_validate(p["diagnostic"])
            lead = capture_lead(
                email=p["email"],
                diagnostic=diagnostic,
                organization=p.get("organization", ""),
                role=p.get("role", ""),
                consent=bool(p.get("consent", False)),
            )
            return {"lead": lead.model_dump(mode="json")}

        if action == "upload_demo":
            result = run_upload_demo(text=p.get("text", ""))
            return {"result": result.model_dump(mode="json")}

        if action == "partner_mode":
            mode = describe_partner_mode(
                p.get("partner_id", "partner"),
                p.get("name", "Partner"),
            )
            return {"partner": mode.model_dump(mode="json")}

        # ------------- Track 8
        if action == "run_challenge":
            findings = run_challenge(
                claims=p.get("claims", []),
                toc_validation_findings=p.get("toc_findings"),
                stakeholder_voice_present=bool(p.get("stakeholder_voice_present", False)),
            )
            return {"findings": [f.model_dump(mode="json") for f in findings]}

        if action == "safe_answer":
            query = EngagementQuery.model_validate(
                {
                    "engagement_id": args.engagement_id or "default",
                    **p.get("query", {}),
                }
            )
            answer = answer_from_approved_evidence(
                query,
                approved_claims=p.get("approved_claims", []),
                approved_metrics=p.get("approved_metrics", []),
                gaps=p.get("gaps"),
            )
            return {"answer": answer.model_dump(mode="json")}

        if action == "extract_meeting_notes":
            ingestion = extract_meeting_notes(
                raw_text=p.get("text", ""),
                engagement_id=args.engagement_id,
            )
            return {"ingestion": ingestion.model_dump(mode="json")}

        # ------------- Track 9
        if action == "list_jurisdictions":
            return {"jurisdictions": [j.model_dump(mode="json") for j in list_jurisdictions()]}

        if action == "classify_sfdr":
            result = classify_sfdr(SFDRClassificationInput.model_validate(p))
            return {"result": result.model_dump(mode="json")}

        if action == "classify_uk_sdr":
            result = classify_uk_sdr(UKSDRLabelInput.model_validate(p))
            return {"result": result.model_dump(mode="json")}

        if action == "schedule_deadlines":
            deadlines = schedule_deadlines(
                engagement_id=args.engagement_id,
                jurisdiction=p["jurisdiction"],
                fiscal_year_end=p["fiscal_year_end"],
                owner=p.get("owner", ""),
            )
            return {"deadlines": [d.model_dump(mode="json") for d in deadlines]}

        if action == "regulator_narrative":
            narrative = build_regulator_narrative(
                engagement_id=args.engagement_id,
                jurisdiction=p["jurisdiction"],
                approved_metrics_summary=p.get("approved_metrics_summary", ""),
                known_gaps=p.get("known_gaps"),
            )
            return {"narrative": narrative.model_dump(mode="json")}

        # ------------- Track 10
        if action == "build_mandate_pack":
            pack = build_mandate_pack(engagement_id=args.engagement_id)
            return {"pack": pack.model_dump(mode="json")}

        if action == "build_practice_pack":
            pack = build_practice_pack(engagement_id=args.engagement_id)
            return {"pack": pack.model_dump(mode="json")}

        if action == "build_reporting_pack":
            pack = build_reporting_pack(
                engagement_id=args.engagement_id,
                lp_narrative_ref=p.get("lp_narrative_ref", ""),
                claims=p.get("claims"),
            )
            return {"pack": pack.model_dump(mode="json")}

        if action == "build_assurance_bundle":
            bundle = build_assurance_bundle(
                engagement_id=args.engagement_id,
                mandate=MandatePack.model_validate(p["mandate"]),
                practice=PracticePack.model_validate(p["practice"]),
                reporting=ReportingPack.model_validate(p["reporting"]),
            )
            return {"bundle": bundle.model_dump(mode="json")}

        if action == "verify_assurance_bundle":
            from openharness.impact.engagements import AssuranceBundle

            bundle = AssuranceBundle.model_validate(p["bundle"])
            return {"is_valid": verify_assurance_bundle(bundle)}

        if action == "readiness_badge":
            from openharness.impact.engagements import AssuranceBundle

            bundle = AssuranceBundle.model_validate(p["bundle"])
            badge = evaluate_assurance_readiness(bundle)
            return {"badge": badge.model_dump(mode="json")}

        if action == "issue_verifier_token":
            record, raw = issue_verifier_token(
                engagement_id=args.engagement_id or p.get("engagement_id", ""),
                verifier_name=p["verifier_name"],
                validity_days=int(p.get("validity_days", 90)),
            )
            return {"token": record.model_dump(mode="json"), "plaintext": raw}

        if action == "list_verifier_marketplace":
            return {
                "listings": [
                    listing.model_dump(mode="json")
                    for listing in list_verifier_marketplace()
                ]
            }

        raise ValueError(f"Unknown engagement_suite action: {action}")


__all__ = ["EngagementSuiteTool"]
