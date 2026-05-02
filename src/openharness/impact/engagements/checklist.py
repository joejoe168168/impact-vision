"""Consultant checklist generator (roadmap-v4 Track 1.3).

Turns a bundle pick + a list of checklist-phase names into a concrete,
dependency-linked :class:`~openharness.impact.engagements.models.ChecklistItem`
list. The phase list is opinionated and sequential: the output of one phase
unlocks the next (``depends_on`` is populated to reflect that).

No network, no LLM: this is pure data plumbing so the agent can ship it
deterministically. Track 8 (copilot) will later AI-augment the prompts,
but the skeleton has to come from here first so the copilot has something
to *challenge*.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from pydantic import BaseModel, Field

from openharness.impact.engagements.models import ChecklistItem


class ChecklistPhase(BaseModel):
    """Metadata for one phase of the consultant workflow."""

    phase_id: str
    title: str
    purpose: str
    default_items: list[dict[str, str]] = Field(default_factory=list)


CONSULTANT_CHECKLIST_PHASES: dict[str, ChecklistPhase] = {
    "discovery": ChecklistPhase(
        phase_id="discovery",
        title="Discovery",
        purpose=(
            "Understand the client's strategy, investor base, reporting "
            "obligations, and existing IMM maturity."
        ),
        default_items=[
            {
                "title": "Run intake interview with sponsor",
                "description": (
                    "Document fund / programme scope, timeline, and success "
                    "criteria."
                ),
            },
            {
                "title": "Capture current IMM artefacts",
                "description": (
                    "Collect existing impact thesis, prior reports, LP DDQ "
                    "responses, and regulatory filings."
                ),
            },
            {
                "title": "Identify stakeholder contacts",
                "description": "Name the IC, LP, board, and investee leads.",
            },
        ],
    ),
    "data_request": ChecklistPhase(
        phase_id="data_request",
        title="Data Request",
        purpose=(
            "Pull the minimum viable evidence set: portfolio list, metrics, "
            "policies, stakeholder consent, and supplementary documents."
        ),
        default_items=[
            {
                "title": "Send smart data request pack",
                "description": (
                    "Use the bundle's questionnaire (investee_collection / "
                    "questionnaire_v2) and issue no-auth links."
                ),
            },
            {
                "title": "Track receipt and completeness",
                "description": (
                    "Flag missing / stale / unverified fields via "
                    "build_collection_tracker."
                ),
            },
            {
                "title": "Ingest and tag evidence",
                "description": (
                    "Attach documents to the engagement vault and hash them "
                    "into the audit trail."
                ),
            },
        ],
    ),
    "stakeholder_map": ChecklistPhase(
        phase_id="stakeholder_map",
        title="Stakeholder Map",
        purpose=(
            "Identify who benefits, who is excluded, and whose voice is "
            "missing (equity & inclusion lens)."
        ),
        default_items=[
            {
                "title": "Map beneficiary segments",
                "description": (
                    "Use the stakeholder_voice template for the sector and "
                    "persist stable stakeholder IDs."
                ),
            },
            {
                "title": "Design feedback instrument",
                "description": (
                    "Lean Data survey, interview guide, or worker voice "
                    "template with GDPR/PDPA consent language."
                ),
            },
        ],
    ),
    "toc_workshop": ChecklistPhase(
        phase_id="toc_workshop",
        title="Theory of Change Workshop",
        purpose=(
            "Facilitate a ToC session: problem, inputs, activities, outputs, "
            "outcomes, impact, assumptions. AI drafts the first pass; the "
            "consultant interrogates it with the client."
        ),
        default_items=[
            {
                "title": "AI-draft ToC from intake docs",
                "description": (
                    "Seed the toc_graph with outcomes + assumptions extracted "
                    "from the pitch deck / memo."
                ),
            },
            {
                "title": "Facilitate client rewrite session",
                "description": (
                    "Log every override as a ConsultantOverride record so the "
                    "session output is audit-trail-grade."
                ),
            },
            {
                "title": "Validate logic chain",
                "description": (
                    "Flag weak causal links, untested assumptions, and "
                    "unmeasured outcomes before KPI design."
                ),
            },
        ],
    ),
    "kpi_design": ChecklistPhase(
        phase_id="kpi_design",
        title="KPI Framework Design",
        purpose=(
            "Map validated ToC outcomes to IRIS+ / SDG / EDCI / ESRS / ISSB / "
            "GRI metrics, lock the framework for this engagement."
        ),
        default_items=[
            {
                "title": "Run metric recommender",
                "description": (
                    "Invoke metric_recommender with the ToC outcomes and fund "
                    "thesis."
                ),
            },
            {
                "title": "Cross-reference across frameworks",
                "description": (
                    "Use cross_reference to confirm each KPI has a defensible "
                    "framework home."
                ),
            },
            {
                "title": "Lock KPI framework v1",
                "description": (
                    "Capture the final list as a Deliverable with an "
                    "artefact_hash."
                ),
            },
        ],
    ),
    "reporting": ChecklistPhase(
        phase_id="reporting",
        title="Reporting",
        purpose="Assemble the deliverable(s) and walk the client through evidence.",
        default_items=[
            {
                "title": "Draft deliverable from verified data",
                "description": (
                    "Use the bundle's report tool (impact_report / "
                    "lp_narrative / exit_impact / verification_workspace) "
                    "operating over approved evidence only."
                ),
            },
            {
                "title": "Run claim review panel",
                "description": (
                    "Per claim: approved / caveated / rejected / needs "
                    "evidence (greenwashing_reviewer)."
                ),
            },
            {
                "title": "Client review and sign-off",
                "description": "Move deliverable state to client_review, then final.",
            },
        ],
    ),
    "training": ChecklistPhase(
        phase_id="training",
        title="Training & Capacity Building",
        purpose=(
            "Productise the consultant's judgement so the client can run the "
            "system next cycle."
        ),
        default_items=[
            {
                "title": "Generate training plan",
                "description": (
                    "Seed from failed validations and evidence gaps "
                    "(improvement_advisor)."
                ),
            },
            {
                "title": "Deliver workshop pack",
                "description": (
                    "ToC / KPI / ESG baseline / data quality / stakeholder "
                    "voice / reporting as required."
                ),
            },
            {
                "title": "Schedule follow-up loop",
                "description": (
                    "Training assigned → action completed → data improves → "
                    "score updates."
                ),
            },
        ],
    ),
}


def build_consultant_checklist(
    phases: Sequence[str],
    *,
    owner: str = "",
    extra_items: Iterable[dict[str, str]] | None = None,
) -> list[ChecklistItem]:
    """Build a checklist from a phase sequence.

    Parameters
    ----------
    phases:
        Ordered phase IDs (see :data:`CONSULTANT_CHECKLIST_PHASES`). Unknown
        phases are skipped (useful for custom bundles).
    owner:
        Default owner applied to every generated item.
    extra_items:
        Optional list of ``{"phase": str, "title": str, "description": str}``
        payloads appended to the relevant phase. Consultants use this to graft
        bundle-specific tasks onto the canonical backbone.

    The output is **sequentially linked** via ``depends_on``: each item's
    dependency is the previous item's ID, so a UI can render a proper Gantt.
    """
    items: list[ChecklistItem] = []
    previous_id = ""
    extras_by_phase: dict[str, list[dict[str, str]]] = {}
    for extra in extra_items or []:
        phase = extra.get("phase", "")
        if not phase:
            continue
        extras_by_phase.setdefault(phase, []).append(extra)

    for phase_id in phases:
        phase = CONSULTANT_CHECKLIST_PHASES.get(phase_id)
        if phase is None:
            continue
        phase_items = list(phase.default_items) + list(extras_by_phase.get(phase_id, []))
        for raw in phase_items:
            item = ChecklistItem(
                phase=phase.phase_id,
                title=raw.get("title", ""),
                description=raw.get("description", ""),
                owner=owner,
                depends_on=[previous_id] if previous_id else [],
            )
            items.append(item)
            previous_id = item.item_id
    return items


__all__ = [
    "CONSULTANT_CHECKLIST_PHASES",
    "ChecklistPhase",
    "build_consultant_checklist",
]
