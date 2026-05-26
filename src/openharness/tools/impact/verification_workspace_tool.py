"""Tool: Verifier workspace with read-only evidence access, findings, and comments (v3)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.assurance import AssurancePack
from openharness.impact.evidence_graph import EvidenceGraph
from openharness.impact.verification_workspace import (
    FindingSeverity,
    FindingStatus,
    VerificationWorkspace,
    open_workspace,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class VerificationWorkspaceInput(BaseModel):
    action: Literal[
        "open",
        "submit_finding",
        "respond_finding",
        "transition_finding",
        "comment",
        "resolve_comment",
        "close",
        "snapshot",
    ] = Field(description="Action to perform on the verifier workspace.")
    pack: dict = Field(default_factory=dict, description="AssurancePack payload (for 'open')")
    workspace: dict = Field(default_factory=dict, description="VerificationWorkspace state to mutate")
    permitted_evidence_ids: list[str] = Field(default_factory=list)
    evidence_graph: dict = Field(default_factory=dict)
    observation: str = ""
    severity: FindingSeverity = "medium"
    raised_by: str = "verifier"
    finding_id: str = ""
    response: str = ""
    responder: str = ""
    status: FindingStatus = "in_review"
    actor: str = "verifier"
    evidence_node_id: str = ""
    author: str = "verifier"
    text: str = ""
    comment_id: str = ""
    closer: str = "audit_lead"
    summary: str = ""


class VerificationWorkspaceTool(BaseTool):
    name = "verification_workspace"
    description = (
        "Open a third-party verifier workspace, manage findings (open/in_review/resolved/unresolved), "
        "post comments threaded to evidence nodes, and produce a JSON API payload. "
        "Actions: 'open', 'submit_finding', 'respond_finding', 'transition_finding', "
        "'comment', 'resolve_comment', 'close', 'snapshot'."
    )
    input_model = VerificationWorkspaceInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        # The base registry occasionally hands in a plain dict (e.g. from
        # the MCP gateway) which doesn't expose ``.action`` directly. Validate
        # first so a passive caller doesn't accidentally trip the write path.
        try:
            args = (
                arguments
                if isinstance(arguments, VerificationWorkspaceInput)
                else VerificationWorkspaceInput.model_validate(arguments)
            )
        except Exception:
            return False
        return args.action == "snapshot"

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, VerificationWorkspaceInput) else VerificationWorkspaceInput.model_validate(arguments)

        if args.action == "open":
            if not args.pack:
                return ToolResult(output="pack is required for 'open'", is_error=True)
            try:
                pack = AssurancePack.model_validate(args.pack)
                graph = EvidenceGraph.model_validate(args.evidence_graph) if args.evidence_graph else None
                workspace = open_workspace(
                    pack=pack,
                    evidence_graph=graph,
                    permitted_evidence_ids=args.permitted_evidence_ids,
                )
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Open failed: {e}", is_error=True)
            return _ok(workspace.to_api_payload())

        if not args.workspace:
            return ToolResult(output="workspace state required for this action", is_error=True)
        try:
            workspace = VerificationWorkspace.model_validate(args.workspace)
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid workspace state: {e}", is_error=True)

        try:
            if args.action == "submit_finding":
                workspace.submit_finding(
                    observation=args.observation,
                    severity=args.severity,
                    raised_by=args.raised_by,
                )
            elif args.action == "respond_finding":
                workspace.respond_to_finding(
                    args.finding_id,
                    response=args.response,
                    responder=args.responder or args.actor,
                )
            elif args.action == "transition_finding":
                workspace.transition_finding(
                    args.finding_id,
                    status=args.status,
                    actor=args.actor,
                )
            elif args.action == "comment":
                workspace.add_comment(
                    evidence_node_id=args.evidence_node_id,
                    author=args.author,
                    text=args.text,
                )
            elif args.action == "resolve_comment":
                workspace.resolve_comment(args.comment_id, resolver=args.actor)
            elif args.action == "close":
                workspace.close(closer=args.closer, summary=args.summary)
            elif args.action == "snapshot":
                pass
            else:
                return ToolResult(output=f"Unknown action: {args.action}", is_error=True)
        except (KeyError, ValueError) as e:
            return ToolResult(output=str(e), is_error=True)

        return _ok(workspace.to_api_payload())


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)
