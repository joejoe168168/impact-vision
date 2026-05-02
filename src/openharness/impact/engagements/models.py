"""Engagement workspace data contracts (v4 Track 1.1–1.6).

These are the canonical Pydantic models every other v4 module uses to talk
about a consulting engagement. They are storage-agnostic: callers may persist
them via :mod:`openharness.impact.storage`, a future REST layer, or keep them
in memory via :class:`~openharness.impact.engagements.workspace.EngagementWorkspace`.

The vocabulary follows roadmap-v4 §4 and §4a so that a DD-Light, a Verification
bundle and an Annual Impact Report can all be described with the same shape.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, field_validator


ClientType = Literal[
    "fund",
    "corporate_csr",
    "foundation",
    "nonprofit",
    "social_enterprise",
]

EngagementStatus = Literal[
    "proposal",
    "active",
    "on_hold",
    "closed",
    "cancelled",
]

DeliverableState = Literal[
    "planned",
    "in_progress",
    "draft",
    "client_review",
    "final",
    "cancelled",
]

ChecklistStatus = Literal[
    "pending",
    "in_progress",
    "blocked",
    "completed",
    "skipped",
]

DocumentKind = Literal[
    "intake_doc",
    "data_room_file",
    "interview_note",
    "workshop_output",
    "raw_data",
    "deliverable_draft",
    "deliverable_final",
    "other",
]


class ChecklistItem(BaseModel):
    """One item in the consultant checklist (Track 1.3).

    Checklist items mirror roadmap-v4 §4b/1.3: the canonical consultant
    workflow is Discovery → Data Request → Stakeholder Map → ToC Workshop →
    KPI Design → Reporting → Training. ``phase`` is the grouping key that
    makes a Gantt-style renderer trivial on the UI side.
    """

    item_id: str = Field(default_factory=lambda: f"chk_{secrets.token_hex(6)}")
    phase: str
    title: str
    description: str = ""
    status: ChecklistStatus = "pending"
    owner: str = ""
    due_date: str = ""
    depends_on: list[str] = Field(default_factory=list)
    tool_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str = ""
    completed_at: str = ""


class Deliverable(BaseModel):
    """A named artefact the consultant promises to produce (Track 1.5).

    Deliverables carry a state machine (``planned → in_progress → draft →
    client_review → final``) enforced in
    :class:`~openharness.impact.engagements.workspace.EngagementWorkspace`.
    The ``tool_refs`` field points at the existing v3 agent tools that
    produce the artefact (e.g. ``impact_report``, ``lp_narrative``,
    ``exit_impact``, ``verification_workspace``).
    """

    deliverable_id: str = Field(default_factory=lambda: f"dlv_{secrets.token_hex(6)}")
    name: str
    description: str = ""
    state: DeliverableState = "planned"
    owner: str = ""
    reviewer: str = ""
    due_date: str = ""
    tool_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    artifact_uri: str = ""
    artifact_hash: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())


class EngagementDocument(BaseModel):
    """Any file/note attached to the engagement evidence vault (Track 1.4).

    The vault does not store file contents — it stores references (local path,
    S3 URI, evidence_graph node ID, etc.) so everything can be hashed into the
    audit trail without duplicating binary data.
    """

    document_id: str = Field(default_factory=lambda: f"doc_{secrets.token_hex(6)}")
    kind: DocumentKind
    name: str
    uri: str = ""
    uploaded_by: str = ""
    uploaded_at: str = Field(default_factory=lambda: _now())
    content_hash: str = ""
    linked_deliverable_id: str = ""
    linked_checklist_item_id: str = ""
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class EngagementNote(BaseModel):
    """A free-text consultant note (meeting minute, observation, hypothesis).

    Roadmap-v4 Track 8.4 (meeting-note ingestion) will extend this with
    auto-extracted decisions and action items, but the baseline contract is
    kept minimal here so Wave 1 ships without an NLP dependency.
    """

    note_id: str = Field(default_factory=lambda: f"note_{secrets.token_hex(6)}")
    author: str
    text: str
    recorded_at: str = Field(default_factory=lambda: _now())
    tags: list[str] = Field(default_factory=list)
    linked_checklist_item_id: str = ""


class EngagementDecision(BaseModel):
    """A recorded consultant judgement (Track 1.4 + Sopact-counter response).

    Roadmap-v4 §1 response to Sopact: every consultant override of an AI
    suggestion must be logged as a reviewer event so the engagement output
    is itself an auditable artefact. Storing decisions as structured records
    (rather than loose notes) is what makes that possible.
    """

    decision_id: str = Field(default_factory=lambda: f"dec_{secrets.token_hex(6)}")
    title: str
    rationale: str
    decided_by: str
    decided_at: str = Field(default_factory=lambda: _now())
    evidence_refs: list[str] = Field(default_factory=list)
    supersedes: str = ""


class ConsultantOverride(BaseModel):
    """Consultant override of an AI suggestion (Sopact-counter feature).

    ``target_kind`` lets us track overrides against any v3 artefact family
    (AI extraction, ToC outcome, KPI pick, greenwashing flag…) without
    hard-coding the schemas.
    """

    override_id: str = Field(default_factory=lambda: f"ov_{secrets.token_hex(6)}")
    target_kind: Literal[
        "ai_extraction",
        "toc_outcome",
        "kpi_selection",
        "greenwashing_flag",
        "benchmark",
        "other",
    ] = "other"
    target_id: str
    ai_suggestion: str = ""
    consultant_decision: str
    rationale: str = ""
    overridden_by: str
    overridden_at: str = Field(default_factory=lambda: _now())


class TemplateLibraryEntry(BaseModel):
    """Reusable template for a given client type (Track 1.6).

    A template is effectively a bundle preset plus curated checklist hints
    (e.g. a foundation engagement typically needs grantee consent language
    that a fund engagement does not).
    """

    template_id: str
    client_type: ClientType
    title: str
    description: str
    default_bundle: str
    recommended_deliverables: list[str] = Field(default_factory=list)
    default_checklist_phases: list[str] = Field(default_factory=list)
    guidance: str = ""


class Engagement(BaseModel):
    """Top-level consultant engagement record (Track 1.1)."""

    model_config = {"validate_assignment": True}

    engagement_id: str = Field(default_factory=lambda: f"eng_{secrets.token_hex(6)}")
    name: str
    client_name: str
    client_type: ClientType = "fund"
    fund_name: str = ""
    programme: str = ""
    scope: str = ""
    timeline_start: str = ""
    timeline_end: str = ""
    owner: str = ""
    status: EngagementStatus = "proposal"
    bundle: str = ""
    template_id: str = ""
    created_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())
    tenant_id: str = "default"

    deliverables: list[Deliverable] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    documents: list[EngagementDocument] = Field(default_factory=list)
    notes: list[EngagementNote] = Field(default_factory=list)
    decisions: list[EngagementDecision] = Field(default_factory=list)
    overrides: list[ConsultantOverride] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    toc_canvas: Any | None = None
    """Attached Theory of Change canvas (v4 Track 2). Kept as ``Any`` to avoid a
    circular import; see :mod:`openharness.impact.engagements.toc_builder`."""
    kpi_framework: Any | None = None
    """Locked or draft KPI framework (v4 Track 2.3)."""

    @field_validator("timeline_start", "timeline_end")
    @classmethod
    def _validate_iso(cls, value: str) -> str:
        if not value:
            return value
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"timeline dates must be ISO 8601 (got {value!r})"
            ) from exc
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def deliverable_completion_pct(self) -> float:
        """Fraction of deliverables that have reached ``final`` state."""
        if not self.deliverables:
            return 0.0
        finals = sum(1 for d in self.deliverables if d.state == "final")
        return round(finals / len(self.deliverables), 3)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def checklist_completion_pct(self) -> float:
        """Fraction of checklist items marked ``completed``."""
        if not self.checklist:
            return 0.0
        done = sum(1 for item in self.checklist if item.status == "completed")
        return round(done / len(self.checklist), 3)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "ChecklistItem",
    "ChecklistStatus",
    "ClientType",
    "ConsultantOverride",
    "Deliverable",
    "DeliverableState",
    "DocumentKind",
    "Engagement",
    "EngagementDecision",
    "EngagementDocument",
    "EngagementNote",
    "EngagementStatus",
    "TemplateLibraryEntry",
]
