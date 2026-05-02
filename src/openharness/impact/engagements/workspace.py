"""In-memory engagement workspace store (roadmap-v4 Track 1.1 / 1.4 / 1.5).

Owns the life-cycle of :class:`~openharness.impact.engagements.models.Engagement`
records: creation, deliverable state machine, evidence-vault attachment,
consultant overrides, and audit-trail integration.

The store is deliberately **in-memory**. Persistence is left to callers
(SQLite via :mod:`openharness.impact.storage`, future REST layer, etc.),
mirroring the pattern used by
:mod:`openharness.impact.verification_workspace`.

Audit integration: when an :class:`~openharness.impact.audit_trail.AuditTrail`
is passed on construction, *every* state-changing operation (engagement
creation, deliverable transitions, override capture, decision log) appends
a hash-chained event. This is the v3 trust backbone reused for v4 per
roadmap-v4 §4.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel

from openharness.impact.audit_trail import AuditTrail
from openharness.impact.engagements.bundles import (
    EngagementBundleType,
    get_bundle,
)
from openharness.impact.engagements.checklist import build_consultant_checklist
from openharness.impact.engagements.toc_builder import (
    KPIFramework,
    ToCCanvas,
    ToCValidationReport,
    generate_kpi_framework,
    lock_kpi_framework,
    validate_toc_canvas,
)
from openharness.impact.engagements.models import (
    ChecklistItem,
    ChecklistStatus,
    ClientType,
    ConsultantOverride,
    Deliverable,
    DeliverableState,
    Engagement,
    EngagementDecision,
    EngagementDocument,
    EngagementNote,
    EngagementStatus,
)
from openharness.impact.engagements.templates import get_client_template


_DELIVERABLE_TRANSITIONS: dict[DeliverableState, set[DeliverableState]] = {
    "planned": {"in_progress", "cancelled"},
    "in_progress": {"draft", "cancelled"},
    "draft": {"client_review", "in_progress", "cancelled"},
    "client_review": {"final", "draft", "cancelled"},
    "final": set(),
    "cancelled": set(),
}

_ENGAGEMENT_TRANSITIONS: dict[EngagementStatus, set[EngagementStatus]] = {
    "proposal": {"active", "cancelled"},
    "active": {"on_hold", "closed", "cancelled"},
    "on_hold": {"active", "cancelled"},
    "closed": set(),
    "cancelled": set(),
}


class EngagementWorkspaceSummary(BaseModel):
    """Lightweight roll-up for tool / UI consumption."""

    engagement_id: str
    name: str
    client_name: str
    client_type: ClientType
    status: EngagementStatus
    bundle: str = ""
    template_id: str = ""
    deliverable_count: int = 0
    deliverables_final: int = 0
    deliverable_completion_pct: float = 0.0
    checklist_count: int = 0
    checklist_completed: int = 0
    checklist_completion_pct: float = 0.0
    document_count: int = 0
    decision_count: int = 0
    override_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class EngagementWorkspace:
    """In-memory store for consultant engagements.

    Parameters
    ----------
    tenant_id:
        Tenant scope (maps onto the v3 multi-tenant story in
        :mod:`openharness.impact.tenancy`).
    audit_trail:
        Optional :class:`AuditTrail`. When provided every state-changing
        call appends a signed audit event so the workspace is tamper-evident.
    """

    def __init__(
        self,
        *,
        tenant_id: str = "default",
        audit_trail: AuditTrail | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.audit_trail = audit_trail
        self._engagements: dict[str, Engagement] = {}

    # ------------------------------------------------------------------ engagements

    def create_engagement(
        self,
        *,
        name: str,
        client_name: str,
        client_type: ClientType = "fund",
        bundle_id: EngagementBundleType | None = None,
        template_id: str = "",
        owner: str = "",
        fund_name: str = "",
        programme: str = "",
        scope: str = "",
        timeline_start: str = "",
        timeline_end: str = "",
        tags: Iterable[str] | None = None,
        autopopulate: bool = True,
    ) -> Engagement:
        """Create a new engagement.

        When ``autopopulate`` is true (the default) the bundle or template's
        default deliverables and checklist phases are materialised onto the
        engagement so the consultant has a working scaffold immediately.
        """
        bundle_key: EngagementBundleType | None = bundle_id
        template = None
        if template_id:
            template = get_client_template(template_id)
            bundle_key = bundle_key or template.default_bundle  # type: ignore[assignment]
            if not client_type:
                client_type = template.client_type
        engagement = Engagement(
            name=name.strip(),
            client_name=client_name.strip(),
            client_type=client_type,
            fund_name=fund_name,
            programme=programme,
            scope=scope or (get_bundle(bundle_key).description if bundle_key else ""),
            timeline_start=timeline_start,
            timeline_end=timeline_end,
            owner=owner,
            bundle=bundle_key or "",
            template_id=template_id,
            tenant_id=self.tenant_id,
            tags=list(tags or []),
        )
        if autopopulate and bundle_key:
            bundle = get_bundle(bundle_key)
            phases = template.default_checklist_phases if template else bundle.default_checklist_phases
            default_deliverables = (
                template.recommended_deliverables
                if template and template.recommended_deliverables
                else bundle.default_deliverables
            )
            engagement.deliverables = [
                Deliverable(
                    name=name_,
                    owner=owner,
                    tool_refs=list(bundle.bundled_tools),
                )
                for name_ in default_deliverables
            ]
            engagement.checklist = build_consultant_checklist(phases, owner=owner)
        self._engagements[engagement.engagement_id] = engagement
        self._audit(
            "engagement.created",
            engagement_id=engagement.engagement_id,
            client_name=engagement.client_name,
            bundle=engagement.bundle,
            template_id=engagement.template_id,
            actor=owner or "system",
        )
        return engagement

    def get_engagement(self, engagement_id: str) -> Engagement:
        """Return an engagement by ID or raise :class:`KeyError`."""
        try:
            return self._engagements[engagement_id]
        except KeyError as exc:
            raise KeyError(f"Unknown engagement {engagement_id!r}") from exc

    def list_engagements(
        self,
        *,
        status: EngagementStatus | None = None,
        client_type: ClientType | None = None,
    ) -> list[Engagement]:
        """List engagements with optional status / client-type filters."""
        out = list(self._engagements.values())
        if status is not None:
            out = [e for e in out if e.status == status]
        if client_type is not None:
            out = [e for e in out if e.client_type == client_type]
        return sorted(out, key=lambda e: e.created_at)

    def transition_engagement(
        self,
        engagement_id: str,
        next_status: EngagementStatus,
        *,
        actor: str,
    ) -> Engagement:
        """Move an engagement through its top-level status machine."""
        engagement = self.get_engagement(engagement_id)
        allowed = _ENGAGEMENT_TRANSITIONS[engagement.status]
        if next_status not in allowed:
            raise ValueError(
                f"Invalid engagement transition {engagement.status} -> {next_status}"
            )
        engagement.status = next_status
        engagement.updated_at = _now()
        self._audit(
            "engagement.transitioned",
            engagement_id=engagement.engagement_id,
            from_status=engagement.status,
            to_status=next_status,
            actor=actor,
        )
        return engagement

    # ------------------------------------------------------------------ deliverables

    def add_deliverable(
        self,
        engagement_id: str,
        *,
        name: str,
        description: str = "",
        owner: str = "",
        due_date: str = "",
        tool_refs: Iterable[str] | None = None,
    ) -> Deliverable:
        """Attach a new deliverable to an engagement."""
        engagement = self.get_engagement(engagement_id)
        deliverable = Deliverable(
            name=name,
            description=description,
            owner=owner,
            due_date=due_date,
            tool_refs=list(tool_refs or []),
        )
        engagement.deliverables.append(deliverable)
        engagement.updated_at = _now()
        self._audit(
            "engagement.deliverable.added",
            engagement_id=engagement_id,
            deliverable_id=deliverable.deliverable_id,
            name=name,
            actor=owner or "system",
        )
        return deliverable

    def transition_deliverable(
        self,
        engagement_id: str,
        deliverable_id: str,
        next_state: DeliverableState,
        *,
        actor: str,
        artifact_uri: str = "",
        artifact_hash: str = "",
        note: str = "",
    ) -> Deliverable:
        """Apply the deliverable state machine with an audit entry."""
        engagement = self.get_engagement(engagement_id)
        for deliverable in engagement.deliverables:
            if deliverable.deliverable_id != deliverable_id:
                continue
            allowed = _DELIVERABLE_TRANSITIONS[deliverable.state]
            if next_state not in allowed:
                raise ValueError(
                    f"Invalid deliverable transition {deliverable.state} -> {next_state}"
                )
            previous = deliverable.state
            deliverable.state = next_state
            deliverable.updated_at = _now()
            if artifact_uri:
                deliverable.artifact_uri = artifact_uri
            if artifact_hash:
                deliverable.artifact_hash = artifact_hash
            deliverable.history.append(
                {
                    "from": previous,
                    "to": next_state,
                    "actor": actor,
                    "at": deliverable.updated_at,
                    "note": note,
                }
            )
            engagement.updated_at = deliverable.updated_at
            self._audit(
                "engagement.deliverable.transitioned",
                engagement_id=engagement_id,
                deliverable_id=deliverable_id,
                from_state=previous,
                to_state=next_state,
                artifact_hash=artifact_hash,
                actor=actor,
            )
            return deliverable
        raise KeyError(f"Unknown deliverable {deliverable_id!r}")

    # ------------------------------------------------------------------ checklist

    def update_checklist_item(
        self,
        engagement_id: str,
        item_id: str,
        *,
        status: ChecklistStatus | None = None,
        owner: str | None = None,
        evidence_refs: Iterable[str] | None = None,
        notes: str | None = None,
        actor: str = "",
    ) -> ChecklistItem:
        """Update a checklist item and audit the change."""
        engagement = self.get_engagement(engagement_id)
        for item in engagement.checklist:
            if item.item_id != item_id:
                continue
            if status is not None:
                if status == "completed" and item.status != "completed":
                    item.completed_at = _now()
                item.status = status
            if owner is not None:
                item.owner = owner
            if evidence_refs is not None:
                item.evidence_refs = list(evidence_refs)
            if notes is not None:
                item.notes = notes
            engagement.updated_at = _now()
            self._audit(
                "engagement.checklist.updated",
                engagement_id=engagement_id,
                item_id=item_id,
                new_status=item.status,
                actor=actor or owner or "system",
            )
            return item
        raise KeyError(f"Unknown checklist item {item_id!r}")

    # ------------------------------------------------------------------ evidence vault

    def attach_document(
        self,
        engagement_id: str,
        *,
        kind: str,
        name: str,
        uri: str = "",
        content: str = "",
        uploaded_by: str = "",
        linked_deliverable_id: str = "",
        linked_checklist_item_id: str = "",
        tags: Iterable[str] | None = None,
        notes: str = "",
    ) -> EngagementDocument:
        """Attach a document reference to the evidence vault.

        ``content`` is hashed for the audit trail but **not** stored (the
        vault is a reference registry, not a blob store).
        """
        engagement = self.get_engagement(engagement_id)
        content_hash = (
            hashlib.sha256(content.encode("utf-8")).hexdigest() if content else ""
        )
        document = EngagementDocument(
            kind=kind,  # type: ignore[arg-type]
            name=name,
            uri=uri,
            uploaded_by=uploaded_by,
            content_hash=content_hash,
            linked_deliverable_id=linked_deliverable_id,
            linked_checklist_item_id=linked_checklist_item_id,
            tags=list(tags or []),
            notes=notes,
        )
        engagement.documents.append(document)
        engagement.updated_at = _now()
        self._audit(
            "engagement.document.attached",
            engagement_id=engagement_id,
            document_id=document.document_id,
            kind=kind,
            name=name,
            content_hash=content_hash,
            actor=uploaded_by or "system",
        )
        return document

    def add_note(
        self,
        engagement_id: str,
        *,
        author: str,
        text: str,
        tags: Iterable[str] | None = None,
        linked_checklist_item_id: str = "",
    ) -> EngagementNote:
        """Record a free-text note against the engagement."""
        engagement = self.get_engagement(engagement_id)
        note = EngagementNote(
            author=author,
            text=text,
            tags=list(tags or []),
            linked_checklist_item_id=linked_checklist_item_id,
        )
        engagement.notes.append(note)
        engagement.updated_at = _now()
        self._audit(
            "engagement.note.recorded",
            engagement_id=engagement_id,
            note_id=note.note_id,
            author=author,
            actor=author,
        )
        return note

    def record_decision(
        self,
        engagement_id: str,
        *,
        title: str,
        rationale: str,
        decided_by: str,
        evidence_refs: Iterable[str] | None = None,
        supersedes: str = "",
    ) -> EngagementDecision:
        """Record a consultant decision against the engagement."""
        engagement = self.get_engagement(engagement_id)
        decision = EngagementDecision(
            title=title,
            rationale=rationale,
            decided_by=decided_by,
            evidence_refs=list(evidence_refs or []),
            supersedes=supersedes,
        )
        engagement.decisions.append(decision)
        engagement.updated_at = _now()
        self._audit(
            "engagement.decision.recorded",
            engagement_id=engagement_id,
            decision_id=decision.decision_id,
            title=title,
            actor=decided_by,
        )
        return decision

    def record_override(
        self,
        engagement_id: str,
        *,
        target_kind: Literal[
            "ai_extraction",
            "toc_outcome",
            "kpi_selection",
            "greenwashing_flag",
            "benchmark",
            "other",
        ],
        target_id: str,
        consultant_decision: str,
        overridden_by: str,
        ai_suggestion: str = "",
        rationale: str = "",
    ) -> ConsultantOverride:
        """Capture a consultant override of an AI suggestion.

        This is the core Sopact counter-position feature: overrides are
        first-class, audit-logged records rather than anonymous edits.
        """
        engagement = self.get_engagement(engagement_id)
        override = ConsultantOverride(
            target_kind=target_kind,
            target_id=target_id,
            ai_suggestion=ai_suggestion,
            consultant_decision=consultant_decision,
            rationale=rationale,
            overridden_by=overridden_by,
        )
        engagement.overrides.append(override)
        engagement.updated_at = _now()
        self._audit(
            "engagement.override.recorded",
            engagement_id=engagement_id,
            override_id=override.override_id,
            target_kind=target_kind,
            target_id=target_id,
            actor=overridden_by,
        )
        return override

    # ------------------------------------------------------------------ ToC / KPI (Track 2)

    def attach_toc_canvas(
        self,
        engagement_id: str,
        canvas: ToCCanvas,
        *,
        actor: str = "consultant",
    ) -> ToCCanvas:
        """Attach (or replace) the engagement's Theory of Change canvas.

        When a canvas already exists, the version is bumped so the replacement
        is attributable in the audit trail.
        """
        engagement = self.get_engagement(engagement_id)
        previous = getattr(engagement, "toc_canvas", None)
        canvas_to_attach = canvas.model_copy()
        canvas_to_attach.engagement_id = engagement_id
        if previous is not None:
            try:
                canvas_to_attach.version = int(previous.version) + 1  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001 - version bump must never crash
                canvas_to_attach.version = canvas_to_attach.version + 1
        engagement.toc_canvas = canvas_to_attach
        engagement.updated_at = _now()
        self._audit(
            "engagement.toc.attached",
            engagement_id=engagement_id,
            canvas_id=canvas_to_attach.canvas_id,
            version=canvas_to_attach.version,
            actor=actor,
        )
        return canvas_to_attach

    def get_toc_canvas(self, engagement_id: str) -> ToCCanvas:
        """Return the engagement's ToC canvas or raise ``ValueError``."""
        engagement = self.get_engagement(engagement_id)
        canvas = getattr(engagement, "toc_canvas", None)
        if canvas is None:
            raise ValueError(f"Engagement {engagement_id!r} has no ToC canvas attached.")
        return canvas  # type: ignore[return-value]

    def validate_toc(self, engagement_id: str) -> ToCValidationReport:
        """Run the logic-chain validator against the engagement's canvas."""
        canvas = self.get_toc_canvas(engagement_id)
        report = validate_toc_canvas(canvas)
        self._audit(
            "engagement.toc.validated",
            engagement_id=engagement_id,
            canvas_id=canvas.canvas_id,
            findings=len(report.findings),
            is_passing=report.is_passing,
            severities=report.severity_counts,
            actor="system",
        )
        return report

    def mark_toc_node_reviewed(
        self,
        engagement_id: str,
        node_id: str,
        *,
        actor: str,
        reviewed: bool = True,
    ) -> ToCCanvas:
        """Toggle ``consultant_reviewed`` on a canvas node (Sopact-counter hook)."""
        canvas = self.get_toc_canvas(engagement_id)
        for node in canvas.nodes:
            if node.node_id == node_id:
                node.consultant_reviewed = reviewed
                canvas.version += 1
                self._audit(
                    "engagement.toc.node.reviewed",
                    engagement_id=engagement_id,
                    canvas_id=canvas.canvas_id,
                    node_id=node_id,
                    reviewed=reviewed,
                    actor=actor,
                )
                return canvas
        raise KeyError(f"Unknown ToC node {node_id!r}")

    def generate_kpi_framework_for(
        self,
        engagement_id: str,
        *,
        sector: str = "",
        geography: str = "",
        impact_themes: Iterable[str] | None = None,
        sdg_goals: Iterable[int] | None = None,
        per_outcome_limit: int = 3,
        include_core_set: bool = True,
        actor: str = "system",
    ) -> KPIFramework:
        """Generate (and attach) a KPI framework for the engagement's canvas."""
        canvas = self.get_toc_canvas(engagement_id)
        framework = generate_kpi_framework(
            canvas=canvas,
            sector=sector,
            geography=geography,
            impact_themes=impact_themes,
            sdg_goals=sdg_goals,
            per_outcome_limit=per_outcome_limit,
            include_core_set=include_core_set,
            engagement_id=engagement_id,
        )
        engagement = self.get_engagement(engagement_id)
        engagement.kpi_framework = framework
        engagement.updated_at = _now()
        self._audit(
            "engagement.kpi.generated",
            engagement_id=engagement_id,
            framework_id=framework.framework_id,
            canvas_id=canvas.canvas_id,
            metric_count=framework.metric_count,
            actor=actor,
        )
        return framework

    def lock_kpi_framework_for(
        self,
        engagement_id: str,
        *,
        actor: str = "consultant",
    ) -> KPIFramework:
        """Lock the engagement's KPI framework so downstream tools treat it as immutable."""
        engagement = self.get_engagement(engagement_id)
        framework = getattr(engagement, "kpi_framework", None)
        if framework is None:
            raise ValueError(
                f"Engagement {engagement_id!r} has no KPI framework to lock."
            )
        locked = lock_kpi_framework(framework)
        engagement.kpi_framework = locked
        engagement.updated_at = _now()
        self._audit(
            "engagement.kpi.locked",
            engagement_id=engagement_id,
            framework_id=locked.framework_id,
            version=locked.version,
            actor=actor,
        )
        return locked

    def get_kpi_framework(self, engagement_id: str) -> KPIFramework:
        """Return the engagement's KPI framework or raise ``ValueError``."""
        engagement = self.get_engagement(engagement_id)
        framework = getattr(engagement, "kpi_framework", None)
        if framework is None:
            raise ValueError(
                f"Engagement {engagement_id!r} has no KPI framework."
            )
        return framework  # type: ignore[return-value]

    # ----------------------------------------------------- v4 Tracks 3-10 hooks

    def record_artifact(
        self,
        engagement_id: str,
        *,
        kind: str,
        artifact_id: str = "",
        metadata: dict | None = None,
        actor: str = "system",
    ) -> None:
        """Generic audit-trail anchor for Tracks 3-10 outputs.

        The engagement modules (data room, reporting, verification,
        etc.) ship as pure functions so they can be tested in isolation.
        When they are used inside an engagement the workspace should
        still own the auditability guarantee: call this once per
        artefact the consultant decides to attach / sign / publish and
        the event will land in the hash-chained audit trail.

        ``kind`` examples::

            "data_pack.attached"
            "data_pack.completeness_scored"
            "report.built"
            "report.published"
            "assurance_bundle.signed"
            "verifier_token.issued"
            "regulatory.classified"
            "training_plan.delivered"
            "copilot_output.reviewed"
        """
        self.get_engagement(engagement_id)  # raises if missing
        self._audit(
            f"engagement.{kind}",
            engagement_id=engagement_id,
            artifact_id=artifact_id,
            metadata=metadata,
            actor=actor,
        )

    # ------------------------------------------------------------------ summary

    def summarize(self, engagement_id: str) -> EngagementWorkspaceSummary:
        """Return a compact roll-up for the given engagement."""
        engagement = self.get_engagement(engagement_id)
        deliverables_final = sum(
            1 for d in engagement.deliverables if d.state == "final"
        )
        checklist_completed = sum(
            1 for item in engagement.checklist if item.status == "completed"
        )
        return EngagementWorkspaceSummary(
            engagement_id=engagement.engagement_id,
            name=engagement.name,
            client_name=engagement.client_name,
            client_type=engagement.client_type,
            status=engagement.status,
            bundle=engagement.bundle,
            template_id=engagement.template_id,
            deliverable_count=len(engagement.deliverables),
            deliverables_final=deliverables_final,
            deliverable_completion_pct=engagement.deliverable_completion_pct,
            checklist_count=len(engagement.checklist),
            checklist_completed=checklist_completed,
            checklist_completion_pct=engagement.checklist_completion_pct,
            document_count=len(engagement.documents),
            decision_count=len(engagement.decisions),
            override_count=len(engagement.overrides),
            created_at=engagement.created_at,
            updated_at=engagement.updated_at,
        )

    # ------------------------------------------------------------------ persistence helpers

    def export_state(self) -> dict[str, list[dict]]:
        """Return a JSON-safe snapshot of every engagement in the workspace."""
        return {
            "tenant_id": self.tenant_id,  # type: ignore[dict-item]
            "engagements": [
                engagement.model_dump(mode="json")
                for engagement in self._engagements.values()
            ],
        }

    def import_state(self, payload: dict) -> None:
        """Restore a workspace from an :meth:`export_state` snapshot."""
        self._engagements.clear()
        for raw in payload.get("engagements", []):
            engagement = Engagement.model_validate(raw)
            self._engagements[engagement.engagement_id] = engagement

    # ------------------------------------------------------------------ internals

    def _audit(self, event_type: str, *, actor: str = "system", **payload) -> None:
        if self.audit_trail is None:
            return
        cleaned = {
            key: value
            for key, value in payload.items()
            if value is not None
        }
        try:
            self.audit_trail.record_event(
                event_type=event_type,
                payload=json.loads(json.dumps(cleaned, default=str)),
                actor=actor,
            )
        except Exception:  # noqa: BLE001 - audit must never crash a workflow call
            return


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "EngagementWorkspace",
    "EngagementWorkspaceSummary",
]
