"""Proposal builder (roadmap-v4 Track 1.2).

Given a bundle pick and light intake notes, produce a deterministic
proposal skeleton (scope / workplan / assumptions / fees / outputs / risk
caveats). The proposal is structured so it can later be rendered into any
format (PDF, Notion, docx) — we deliberately avoid string templating here.

Track 8.3 (Proposal + SOW copilot) will layer an LLM on top of this, but
the consultant's audit-friendly scaffold must come from code, not a prompt,
so every assumption is visible for review.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Iterable

from pydantic import BaseModel, Field, computed_field

from openharness.impact.engagements.bundles import (
    EngagementBundle,
    EngagementBundleType,
    get_bundle,
)
from openharness.impact.engagements.checklist import (
    CONSULTANT_CHECKLIST_PHASES,
    build_consultant_checklist,
)
from openharness.impact.engagements.models import ChecklistItem


class ProposalAssumption(BaseModel):
    """One assumption the proposal is conditional on."""

    assumption_id: str = Field(default_factory=lambda: f"as_{secrets.token_hex(4)}")
    statement: str
    evidence_needed: str = ""


class ProposalFeeLine(BaseModel):
    """A fee-line on the proposal (deliberately simple — no currency math)."""

    item: str
    effort_days: float = 0.0
    rate_usd_per_day: float = 0.0
    total_usd: float = 0.0


class ProposalRiskCaveat(BaseModel):
    """Explicit risk caveat (e.g. 'data quality depends on investee response')."""

    title: str
    description: str
    severity: str = "medium"


class ProposalWorkplanItem(BaseModel):
    """One row of the workplan (phase, duration, deliverables, owner)."""

    phase: str
    summary: str
    start_offset_days: int
    duration_days: int
    deliverables: list[str] = Field(default_factory=list)


class EngagementProposal(BaseModel):
    """Structured consultant proposal (roadmap-v4 Track 1.2)."""

    proposal_id: str = Field(default_factory=lambda: f"prop_{secrets.token_hex(6)}")
    engagement_name: str
    client_name: str
    bundle_id: EngagementBundleType
    prepared_by: str
    prepared_at: str = Field(default_factory=lambda: _now())
    scope: str
    objectives: list[str] = Field(default_factory=list)
    workplan: list[ProposalWorkplanItem] = Field(default_factory=list)
    assumptions: list[ProposalAssumption] = Field(default_factory=list)
    fees: list[ProposalFeeLine] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    risk_caveats: list[ProposalRiskCaveat] = Field(default_factory=list)
    checklist_preview: list[ChecklistItem] = Field(default_factory=list)
    sla_days: int = 30

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_fee_usd(self) -> float:
        return round(sum(line.total_usd for line in self.fees), 2)


def build_proposal(
    *,
    engagement_name: str,
    client_name: str,
    bundle_id: EngagementBundleType,
    prepared_by: str,
    objectives: Iterable[str] | None = None,
    intake_notes: str = "",
    day_rate_usd: float = 1500.0,
    assumptions: Iterable[str] | None = None,
    extra_risk_caveats: Iterable[ProposalRiskCaveat] | None = None,
) -> EngagementProposal:
    """Deterministically build a proposal scaffold from a bundle pick.

    The workplan is produced by splitting the bundle's SLA across its default
    checklist phases proportionally. Fees assume the SLA as billable effort —
    the consultant is expected to adjust both before sending the proposal to
    the client.
    """
    bundle: EngagementBundle = get_bundle(bundle_id)
    phases = bundle.default_checklist_phases or list(
        CONSULTANT_CHECKLIST_PHASES.keys()
    )
    sla = max(1, bundle.default_sla_days)
    per_phase = max(1, sla // max(1, len(phases)))
    remaining = sla
    workplan: list[ProposalWorkplanItem] = []
    offset = 0
    for idx, phase_id in enumerate(phases):
        phase = CONSULTANT_CHECKLIST_PHASES.get(phase_id)
        duration = per_phase if idx < len(phases) - 1 else max(1, remaining)
        workplan.append(
            ProposalWorkplanItem(
                phase=phase_id,
                summary=phase.purpose if phase else f"Phase: {phase_id}",
                start_offset_days=offset,
                duration_days=duration,
                deliverables=_deliverables_for_phase(phase_id, bundle),
            )
        )
        offset += duration
        remaining -= duration

    fees = [
        ProposalFeeLine(
            item=f"{item.phase.title()} phase",
            effort_days=float(item.duration_days),
            rate_usd_per_day=day_rate_usd,
            total_usd=round(item.duration_days * day_rate_usd, 2),
        )
        for item in workplan
    ]

    proposal_assumptions = [
        ProposalAssumption(
            statement=(
                "Client provides an authoritative point of contact and "
                "approves the data request pack within 5 business days of "
                "engagement start."
            ),
            evidence_needed="Signed engagement letter",
        ),
        ProposalAssumption(
            statement=(
                "All impact claims are reviewed through the evidence queue "
                "before being surfaced in client-facing outputs."
            ),
            evidence_needed="Evidence-review log",
        ),
    ]
    for raw in assumptions or []:
        proposal_assumptions.append(ProposalAssumption(statement=raw))

    caveats: list[ProposalRiskCaveat] = [
        ProposalRiskCaveat(
            title="Data quality dependency",
            description=(
                "Deliverable depth is conditional on the completeness and "
                "verifiability of client-provided data. Gaps will be flagged "
                "rather than inferred."
            ),
            severity="high",
        ),
        ProposalRiskCaveat(
            title="AI outputs are consultant-curated",
            description=(
                "AI-generated claims pass the evidence review queue before "
                "publication; overrides are logged to the engagement audit "
                "trail."
            ),
            severity="medium",
        ),
    ]
    caveats.extend(list(extra_risk_caveats or []))

    checklist_preview = build_consultant_checklist(
        phases,
        owner=prepared_by,
    )

    objectives_list = list(objectives or [])
    if intake_notes and not objectives_list:
        objectives_list = [
            line.strip("- ").strip()
            for line in intake_notes.splitlines()
            if line.strip()
        ][:5]

    return EngagementProposal(
        engagement_name=engagement_name,
        client_name=client_name,
        bundle_id=bundle_id,
        prepared_by=prepared_by,
        scope=bundle.description,
        objectives=objectives_list,
        workplan=workplan,
        assumptions=proposal_assumptions,
        fees=fees,
        outputs=list(bundle.default_deliverables),
        risk_caveats=caveats,
        checklist_preview=checklist_preview,
        sla_days=sla,
    )


def _deliverables_for_phase(phase_id: str, bundle: EngagementBundle) -> list[str]:
    # Lightweight heuristic: reporting/final-phase work owns all the bundle's
    # named deliverables; earlier phases own working artefacts.
    if phase_id in {"reporting", "training"}:
        return list(bundle.default_deliverables)
    if phase_id == "kpi_design":
        return ["KPI framework"]
    if phase_id == "toc_workshop":
        return ["Theory of Change v1"]
    if phase_id == "discovery":
        return ["Intake summary"]
    if phase_id == "data_request":
        return ["Data request pack"]
    if phase_id == "stakeholder_map":
        return ["Stakeholder map"]
    return []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def suggest_engagement_end(*, start_iso: str, sla_days: int) -> str:
    """Utility: add SLA days to a start date in ISO format."""
    try:
        start = datetime.fromisoformat(start_iso)
    except ValueError:
        return ""
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return (start + timedelta(days=max(1, sla_days))).isoformat()


__all__ = [
    "EngagementProposal",
    "ProposalAssumption",
    "ProposalFeeLine",
    "ProposalRiskCaveat",
    "ProposalWorkplanItem",
    "build_proposal",
    "suggest_engagement_end",
]
