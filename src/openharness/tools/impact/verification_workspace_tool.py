"""Tool: Verifier workspace with read-only evidence access, findings, and comments (v3)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.assurance import AssurancePack
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
        "readiness_check",
        "evidence_map",
        "ifc_alignment",
        "issa5000_pack",
    ] = Field(description="Action to perform on the verifier workspace (or pre-verification prep).")
    pack: dict = Field(default_factory=dict, description="AssurancePack payload (for 'open')")
    workspace: dict = Field(
        default_factory=dict, description="VerificationWorkspace state to mutate"
    )
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

    # Pre-verification prep fields (actions 'readiness_check' / 'evidence_map' / 'ifc_alignment')
    company_name: str = Field(default="", description="Company name (prep actions)")
    company_description: str = Field(default="", description="Company description (prep actions)")
    sector: str = ""
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    impact_themes: list[str] = Field(default_factory=list)
    has_theory_of_change: bool = False
    has_impact_policy: bool = False
    has_exclusion_screening: bool = False
    has_external_audit: bool = False
    verification_target: str = Field(
        default="bluemark",
        description="Target verifier for prep actions: 'bluemark', 'ifc_opim', 'aa1000', 'general'",
    )
    assertions: list[dict] = Field(default_factory=list)
    assurance_level: Literal["limited", "reasonable"] = "limited"


_PREP_ACTIONS = {"readiness_check", "evidence_map", "ifc_alignment", "issa5000_pack"}


class VerificationWorkspaceTool(BaseTool):
    name = "verification_workspace"
    description = (
        "Verification preparation and third-party verifier workspace in one tool. "
        "Prep actions: 'readiness_check' (BlueMark / IFC OPIM / AA1000 readiness), "
        "'evidence_map' (map available evidence to verification requirements), "
        "'ifc_alignment' (IFC Operating Principles check). "
        "Workspace actions: 'open', 'submit_finding', 'respond_finding', 'transition_finding', "
        "'comment', 'resolve_comment', 'close', 'snapshot' — manage findings "
        "(open/in_review/resolved/unresolved) and comments threaded to evidence nodes."
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
        return args.action == "snapshot" or args.action in _PREP_ACTIONS

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, VerificationWorkspaceInput)
            else VerificationWorkspaceInput.model_validate(arguments)
        )

        if args.action in _PREP_ACTIONS:
            if args.action == "issa5000_pack":
                import json
                from openharness.impact.assurance import build_issa5000_pack
                from openharness.impact.audit_trail import AuditTrail
                from openharness.impact.evidence_graph import EvidenceGraph

                try:
                    payload = build_issa5000_pack(
                        {"assertions": args.assertions},
                        EvidenceGraph.model_validate(args.evidence_graph or {}),
                        AuditTrail(),
                        args.assurance_level,
                    )
                    return ToolResult(output=json.dumps(payload, default=str), metadata=payload)
                except Exception as exc:
                    return ToolResult(output=f"ISSA 5000 pack failed: {exc}", is_error=True)
            from openharness.tools.impact.verification_prep_tool import (
                VerificationPrepInput,
                VerificationPrepTool,
            )

            prep_input = VerificationPrepInput(
                action=args.action,
                company_name=args.company_name,
                company_description=args.company_description,
                sector=args.sector,
                reported_metrics=args.reported_metrics,
                sdg_claims=args.sdg_claims,
                impact_themes=args.impact_themes,
                has_theory_of_change=args.has_theory_of_change,
                has_impact_policy=args.has_impact_policy,
                has_exclusion_screening=args.has_exclusion_screening,
                has_external_audit=args.has_external_audit,
                verification_target=args.verification_target,
            )
            return await VerificationPrepTool().execute(prep_input, context)

        if args.action == "open":
            if not args.pack:
                return ToolResult(output="pack is required for 'open'", is_error=True)
            try:
                pack = AssurancePack.model_validate(args.pack)
                graph = (
                    EvidenceGraph.model_validate(args.evidence_graph)
                    if args.evidence_graph
                    else None
                )
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
