"""Agent tool: consultant engagement workspace (v4 Track 1).

Wraps :class:`openharness.impact.engagements.EngagementWorkspace` so an
agent / MCP client can drive the whole Track 1 flow with a single tool:

* ``list_bundles`` / ``get_bundle`` — browse the 12 productised bundles.
* ``list_templates`` / ``get_template`` — browse the client-type template
  library.
* ``build_proposal`` — generate a deterministic proposal scaffold from a
  bundle pick.
* ``create_engagement`` — instantiate an engagement, optionally
  auto-populating deliverables + checklist from the bundle / template.
* ``list_engagements`` / ``get_engagement`` / ``summarize_engagement``.
* ``transition_deliverable`` — draft → client_review → final state machine.
* ``update_checklist_item`` — track consultant progress.
* ``attach_document`` / ``add_note`` / ``record_decision`` / ``record_override``
  — wire into the evidence vault and audit trail.

The tool keeps a **single module-level workspace** so consecutive calls
operate on the same state, mirroring the pattern used by the v3
verification workspace tool.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.engagements import (
    CLIENT_TEMPLATE_LIBRARY,
    ENGAGEMENT_BUNDLES,
    EngagementWorkspace,
    build_proposal,
    list_bundles,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


_DEFAULT_WORKSPACE: EngagementWorkspace | None = None


def _workspace() -> EngagementWorkspace:
    global _DEFAULT_WORKSPACE
    if _DEFAULT_WORKSPACE is None:
        _DEFAULT_WORKSPACE = EngagementWorkspace()
    return _DEFAULT_WORKSPACE


EngagementAction = Literal[
    "list_bundles",
    "get_bundle",
    "list_templates",
    "get_template",
    "build_proposal",
    "create_engagement",
    "list_engagements",
    "get_engagement",
    "summarize_engagement",
    "transition_engagement",
    "add_deliverable",
    "transition_deliverable",
    "update_checklist_item",
    "attach_document",
    "add_note",
    "record_decision",
    "record_override",
    "export_state",
]


class EngagementWorkspaceInput(BaseModel):
    """Unified input schema — most fields are action-specific and optional."""

    action: EngagementAction
    bundle_id: str = ""
    template_id: str = ""
    engagement_id: str = ""
    deliverable_id: str = ""
    checklist_item_id: str = ""

    # create_engagement / build_proposal
    name: str = ""
    client_name: str = ""
    client_type: Literal[
        "fund", "corporate_csr", "foundation", "nonprofit", "social_enterprise"
    ] = "fund"
    owner: str = ""
    fund_name: str = ""
    programme: str = ""
    scope: str = ""
    timeline_start: str = ""
    timeline_end: str = ""
    autopopulate: bool = True
    tags: list[str] = Field(default_factory=list)

    prepared_by: str = ""
    objectives: list[str] = Field(default_factory=list)
    intake_notes: str = ""
    day_rate_usd: float = 1500.0

    # transitions
    next_state: str = ""
    actor: str = ""
    artifact_uri: str = ""
    artifact_hash: str = ""
    note: str = ""

    # checklist update
    status: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str = ""

    # document attach
    kind: str = "other"
    uri: str = ""
    content: str = ""
    linked_deliverable_id: str = ""
    linked_checklist_item_id: str = ""
    document_tags: list[str] = Field(default_factory=list)

    # note
    author: str = ""
    text: str = ""

    # decision / override
    title: str = ""
    rationale: str = ""
    decided_by: str = ""
    supersedes: str = ""
    target_kind: Literal[
        "ai_extraction",
        "toc_outcome",
        "kpi_selection",
        "greenwashing_flag",
        "benchmark",
        "other",
    ] = "other"
    target_id: str = ""
    ai_suggestion: str = ""
    consultant_decision: str = ""
    overridden_by: str = ""

    # list filters
    filter_status: str = ""
    filter_client_type: str = ""

    # add_deliverable
    deliverable_description: str = ""
    deliverable_owner: str = ""
    due_date: str = ""
    tool_refs: list[str] = Field(default_factory=list)

    output_format: Literal["json", "text"] = "json"


class EngagementWorkspaceTool(BaseTool):
    name = "engagement_workspace"
    description = (
        "Consultant engagement workspace (roadmap-v4 Track 1). Browse the 12 "
        "productised engagement bundles and client-type templates, build a "
        "proposal, create an engagement with auto-populated deliverables + "
        "checklist, drive the deliverable state machine (planned → "
        "in_progress → draft → client_review → final), update checklist "
        "items, attach documents to the evidence vault, and record "
        "consultant decisions / AI overrides — every state change is "
        "audit-logged."
    )
    input_model = EngagementWorkspaceInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, EngagementWorkspaceInput) else (
            EngagementWorkspaceInput.model_validate(arguments)
        )
        return args.action in {
            "list_bundles",
            "get_bundle",
            "list_templates",
            "get_template",
            "list_engagements",
            "get_engagement",
            "summarize_engagement",
            "export_state",
            "build_proposal",
        }

    async def execute(
        self,
        arguments: BaseModel,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context  # unused
        args = (
            arguments
            if isinstance(arguments, EngagementWorkspaceInput)
            else EngagementWorkspaceInput.model_validate(arguments)
        )
        workspace = _workspace()

        try:
            payload = self._dispatch(args, workspace)
        except (KeyError, ValueError) as exc:
            return ToolResult(output=str(exc), is_error=True)

        if args.output_format == "text":
            return ToolResult(output=_text_render(args.action, payload), metadata=payload)
        return ToolResult(
            output=json.dumps(payload, indent=2, default=str),
            metadata=payload,
        )

    # ---------------------------------------------------------------- dispatch

    def _dispatch(
        self,
        args: EngagementWorkspaceInput,
        workspace: EngagementWorkspace,
    ) -> dict[str, Any]:
        if args.action == "list_bundles":
            return {"bundles": [b.model_dump(mode="json") for b in list_bundles()]}

        if args.action == "get_bundle":
            if not args.bundle_id:
                raise ValueError("bundle_id is required")
            bundle = ENGAGEMENT_BUNDLES[args.bundle_id]  # type: ignore[index]
            return {"bundle": bundle.model_dump(mode="json")}

        if args.action == "list_templates":
            return {
                "templates": [
                    t.model_dump(mode="json")
                    for t in CLIENT_TEMPLATE_LIBRARY.values()
                ]
            }

        if args.action == "get_template":
            if not args.template_id:
                raise ValueError("template_id is required")
            template = CLIENT_TEMPLATE_LIBRARY[args.template_id]
            return {"template": template.model_dump(mode="json")}

        if args.action == "build_proposal":
            if not args.bundle_id:
                raise ValueError("bundle_id is required to build a proposal")
            proposal = build_proposal(
                engagement_name=args.name or "Untitled engagement",
                client_name=args.client_name or "Unnamed client",
                bundle_id=args.bundle_id,  # type: ignore[arg-type]
                prepared_by=args.prepared_by or args.owner or "consultant",
                objectives=args.objectives or None,
                intake_notes=args.intake_notes,
                day_rate_usd=args.day_rate_usd,
            )
            return {"proposal": proposal.model_dump(mode="json")}

        if args.action == "create_engagement":
            engagement = workspace.create_engagement(
                name=args.name or "Untitled engagement",
                client_name=args.client_name or "Unnamed client",
                client_type=args.client_type,
                bundle_id=args.bundle_id or None,  # type: ignore[arg-type]
                template_id=args.template_id,
                owner=args.owner,
                fund_name=args.fund_name,
                programme=args.programme,
                scope=args.scope,
                timeline_start=args.timeline_start,
                timeline_end=args.timeline_end,
                tags=args.tags,
                autopopulate=args.autopopulate,
            )
            return {"engagement": engagement.model_dump(mode="json")}

        if args.action == "list_engagements":
            status = args.filter_status or None
            ctype = args.filter_client_type or None
            engagements = workspace.list_engagements(
                status=status,  # type: ignore[arg-type]
                client_type=ctype,  # type: ignore[arg-type]
            )
            return {
                "engagements": [
                    workspace.summarize(e.engagement_id).model_dump(mode="json")
                    for e in engagements
                ]
            }

        if args.action == "get_engagement":
            return {
                "engagement": workspace.get_engagement(args.engagement_id).model_dump(
                    mode="json"
                )
            }

        if args.action == "summarize_engagement":
            return {
                "summary": workspace.summarize(args.engagement_id).model_dump(
                    mode="json"
                )
            }

        if args.action == "transition_engagement":
            if not args.next_state:
                raise ValueError("next_state is required")
            engagement = workspace.transition_engagement(
                args.engagement_id,
                args.next_state,  # type: ignore[arg-type]
                actor=args.actor or args.owner or "system",
            )
            return {"engagement": engagement.model_dump(mode="json")}

        if args.action == "add_deliverable":
            deliverable = workspace.add_deliverable(
                args.engagement_id,
                name=args.name,
                description=args.deliverable_description,
                owner=args.deliverable_owner or args.owner,
                due_date=args.due_date,
                tool_refs=args.tool_refs,
            )
            return {"deliverable": deliverable.model_dump(mode="json")}

        if args.action == "transition_deliverable":
            if not args.next_state:
                raise ValueError("next_state is required")
            deliverable = workspace.transition_deliverable(
                args.engagement_id,
                args.deliverable_id,
                args.next_state,  # type: ignore[arg-type]
                actor=args.actor or args.owner or "system",
                artifact_uri=args.artifact_uri,
                artifact_hash=args.artifact_hash,
                note=args.note,
            )
            return {"deliverable": deliverable.model_dump(mode="json")}

        if args.action == "update_checklist_item":
            item = workspace.update_checklist_item(
                args.engagement_id,
                args.checklist_item_id,
                status=args.status or None,  # type: ignore[arg-type]
                owner=args.owner or None,
                evidence_refs=args.evidence_refs or None,
                notes=args.notes or None,
                actor=args.actor or args.owner or "system",
            )
            return {"checklist_item": item.model_dump(mode="json")}

        if args.action == "attach_document":
            document = workspace.attach_document(
                args.engagement_id,
                kind=args.kind,
                name=args.name,
                uri=args.uri,
                content=args.content,
                uploaded_by=args.author or args.owner,
                linked_deliverable_id=args.linked_deliverable_id,
                linked_checklist_item_id=args.linked_checklist_item_id,
                tags=args.document_tags,
                notes=args.notes,
            )
            return {"document": document.model_dump(mode="json")}

        if args.action == "add_note":
            note = workspace.add_note(
                args.engagement_id,
                author=args.author or args.owner or "consultant",
                text=args.text,
                tags=args.tags,
                linked_checklist_item_id=args.linked_checklist_item_id,
            )
            return {"note": note.model_dump(mode="json")}

        if args.action == "record_decision":
            decision = workspace.record_decision(
                args.engagement_id,
                title=args.title,
                rationale=args.rationale,
                decided_by=args.decided_by or args.owner or "consultant",
                evidence_refs=args.evidence_refs,
                supersedes=args.supersedes,
            )
            return {"decision": decision.model_dump(mode="json")}

        if args.action == "record_override":
            override = workspace.record_override(
                args.engagement_id,
                target_kind=args.target_kind,
                target_id=args.target_id,
                consultant_decision=args.consultant_decision,
                overridden_by=args.overridden_by or args.owner or "consultant",
                ai_suggestion=args.ai_suggestion,
                rationale=args.rationale,
            )
            return {"override": override.model_dump(mode="json")}

        if args.action == "export_state":
            return workspace.export_state()

        raise ValueError(f"Unknown engagement_workspace action: {args.action}")


def _text_render(action: str, payload: dict[str, Any]) -> str:
    if action == "list_bundles":
        lines = ["ENGAGEMENT BUNDLES (roadmap-v4 §4a)"]
        for bundle in payload.get("bundles", []):
            lines.append(
                f"  - {bundle['bundle_id']:<22} {bundle['name']} "
                f"({bundle['compass_step']}, {bundle['default_sla_days']}d)"
            )
        return "\n".join(lines)

    if action == "list_engagements":
        rows = payload.get("engagements", [])
        if not rows:
            return "(no engagements)"
        lines = ["ENGAGEMENTS"]
        for row in rows:
            lines.append(
                f"  - {row['engagement_id']}  {row['name']} / {row['client_name']} "
                f"[{row['status']}] "
                f"deliverables={row['deliverables_final']}/{row['deliverable_count']} "
                f"checklist={row['checklist_completed']}/{row['checklist_count']}"
            )
        return "\n".join(lines)

    if action == "summarize_engagement":
        s = payload.get("summary", {})
        return (
            f"Engagement {s.get('engagement_id')} '{s.get('name')}' "
            f"for {s.get('client_name')} ({s.get('client_type')})\n"
            f"  bundle: {s.get('bundle') or '-'}  template: {s.get('template_id') or '-'}\n"
            f"  status: {s.get('status')}\n"
            f"  deliverables: {s.get('deliverables_final')}/{s.get('deliverable_count')}"
            f" ({s.get('deliverable_completion_pct')})\n"
            f"  checklist:    {s.get('checklist_completed')}/{s.get('checklist_count')}"
            f" ({s.get('checklist_completion_pct')})\n"
            f"  documents: {s.get('document_count')}  decisions: {s.get('decision_count')}"
            f"  overrides: {s.get('override_count')}"
        )

    return json.dumps(payload, indent=2, default=str)


__all__ = ["EngagementWorkspaceTool"]
