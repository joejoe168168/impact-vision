"""Third-party verification workspace (v3 Track 8.2 / 8.6).

Provides the data contracts a verification provider (Big-4, boutique
assurer, internal auditor) needs to actually use Impact Vision evidence:

* Read-only access to the assurance pack and the evidence index.
* A finding lifecycle (open → in_review → resolved / unresolved).
* Comment threads anchored to specific evidence node IDs.
* A clean JSON-shaped "API payload" so a future REST endpoint at
  ``/api/v1/verification/{workspace_id}`` can hand the same
  structure over the wire.

The workspace itself is in-memory; persistence is left to callers
(e.g. SQLite via :mod:`openharness.impact.storage` or any other store).
The state machine is enforced here so multiple front ends can share
the same logic.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field

from openharness.impact.assurance import AssurancePack, EvidenceEntry
from openharness.impact.audit_trail import AuditTrail
from openharness.impact.evidence_graph import EvidenceGraph


FindingSeverity = Literal["info", "low", "medium", "high", "critical"]
FindingStatus = Literal[
    "open",
    "in_review",
    "management_responded",
    "resolved",
    "unresolved",
]
CommentStatus = Literal["open", "resolved"]


class VerificationFinding(BaseModel):
    """One verifier finding linked to evidence and management response."""

    finding_id: str = Field(default_factory=lambda: f"finding_{secrets.token_hex(6)}")
    severity: FindingSeverity = "medium"
    observation: str
    evidence_refs: list[str] = Field(default_factory=list)
    management_response: str = ""
    status: FindingStatus = "open"
    raised_by: str = ""
    raised_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())


class VerificationComment(BaseModel):
    """Threaded verifier comment anchored to an evidence node."""

    comment_id: str = Field(default_factory=lambda: f"comment_{secrets.token_hex(6)}")
    evidence_node_id: str
    author: str
    text: str
    status: CommentStatus = "open"
    created_at: str = Field(default_factory=lambda: _now())
    resolved_at: str = ""
    resolved_by: str = ""


class VerificationWorkspace(BaseModel):
    """Read-only verifier portal built off an :class:`AssurancePack`."""

    workspace_id: str = Field(default_factory=lambda: f"workspace_{secrets.token_hex(6)}")
    fund_name: str
    reporting_period: str
    pack: AssurancePack
    evidence_graph: EvidenceGraph | None = None
    findings: list[VerificationFinding] = Field(default_factory=list)
    comments: list[VerificationComment] = Field(default_factory=list)
    opened_at: str = Field(default_factory=lambda: _now())
    closed_at: str = ""
    closed_by: str = ""
    closure_summary: str = ""
    permitted_evidence_ids: list[str] = Field(default_factory=list)

    def list_evidence(self) -> list[EvidenceEntry]:
        """Return the evidence index visible to the verifier."""
        if not self.permitted_evidence_ids:
            return list(self.pack.evidence_index)
        allowed = set(self.permitted_evidence_ids)
        return [item for item in self.pack.evidence_index if item.entry_id in allowed]

    def add_comment(
        self,
        *,
        evidence_node_id: str,
        author: str,
        text: str,
        audit_trail: AuditTrail | None = None,
    ) -> VerificationComment:
        if self.evidence_graph is not None and evidence_node_id not in self.evidence_graph.node_ids():
            raise ValueError(f"Evidence node not in workspace graph: {evidence_node_id}")
        comment = VerificationComment(
            evidence_node_id=evidence_node_id,
            author=author,
            text=text,
        )
        self.comments.append(comment)
        if audit_trail is not None:
            audit_trail.record_event(
                event_type="verification.comment_added",
                payload={
                    "workspace_id": self.workspace_id,
                    "comment_id": comment.comment_id,
                    "evidence_node_id": evidence_node_id,
                    "text": text,
                },
                actor=author,
            )
        return comment

    def resolve_comment(
        self,
        comment_id: str,
        *,
        resolver: str,
        audit_trail: AuditTrail | None = None,
    ) -> VerificationComment:
        comment = self._find_comment(comment_id)
        if comment.status == "resolved":
            return comment
        index = self.comments.index(comment)
        updated = comment.model_copy(update={
            "status": "resolved",
            "resolved_at": _now(),
            "resolved_by": resolver,
        })
        self.comments[index] = updated
        if audit_trail is not None:
            audit_trail.record_event(
                event_type="verification.comment_resolved",
                payload={
                    "workspace_id": self.workspace_id,
                    "comment_id": comment_id,
                },
                actor=resolver,
            )
        return updated

    def submit_finding(
        self,
        *,
        observation: str,
        severity: FindingSeverity,
        raised_by: str,
        evidence_refs: Iterable[str] | None = None,
        audit_trail: AuditTrail | None = None,
    ) -> VerificationFinding:
        refs = list(evidence_refs or [])
        self._validate_evidence_refs(refs)
        finding = VerificationFinding(
            severity=severity,
            observation=observation,
            evidence_refs=refs,
            raised_by=raised_by,
        )
        self.findings.append(finding)
        if audit_trail is not None:
            audit_trail.record_event(
                event_type="verification.finding_raised",
                payload={
                    "workspace_id": self.workspace_id,
                    "finding_id": finding.finding_id,
                    "severity": severity,
                    "observation": observation,
                },
                actor=raised_by,
            )
        return finding

    def respond_to_finding(
        self,
        finding_id: str,
        *,
        response: str,
        responder: str,
        audit_trail: AuditTrail | None = None,
    ) -> VerificationFinding:
        finding = self._find_finding(finding_id)
        if finding.status in {"resolved", "unresolved"}:
            raise ValueError(
                f"Cannot respond to terminal finding {finding_id} "
                f"with status {finding.status}"
            )
        index = self.findings.index(finding)
        updated = finding.model_copy(update={
            "management_response": response,
            "status": "management_responded",
            "updated_at": _now(),
        })
        self.findings[index] = updated
        if audit_trail is not None:
            audit_trail.record_event(
                event_type="verification.finding_response",
                payload={
                    "workspace_id": self.workspace_id,
                    "finding_id": finding_id,
                    "response": response,
                },
                actor=responder,
            )
        return updated

    def transition_finding(
        self,
        finding_id: str,
        *,
        status: FindingStatus,
        actor: str,
        audit_trail: AuditTrail | None = None,
    ) -> VerificationFinding:
        finding = self._find_finding(finding_id)
        allowed: dict[FindingStatus, set[FindingStatus]] = {
            "open": {"in_review", "unresolved"},
            "in_review": {"management_responded", "resolved", "unresolved"},
            "management_responded": {"resolved", "unresolved", "in_review"},
            "resolved": set(),
            "unresolved": set(),
        }
        if status not in allowed[finding.status]:
            raise ValueError(
                f"Invalid finding transition {finding.status} -> {status}"
            )
        index = self.findings.index(finding)
        updated = finding.model_copy(update={
            "status": status,
            "updated_at": _now(),
        })
        self.findings[index] = updated
        if audit_trail is not None:
            audit_trail.record_event(
                event_type="verification.finding_transition",
                payload={
                    "workspace_id": self.workspace_id,
                    "finding_id": finding_id,
                    "status": status,
                },
                actor=actor,
            )
        return updated

    def close(
        self,
        *,
        closer: str,
        summary: str = "",
        audit_trail: AuditTrail | None = None,
    ) -> "VerificationWorkspace":
        unresolved = [
            f for f in self.findings
            if f.status not in {"resolved", "unresolved"}
        ]
        if unresolved:
            raise ValueError(
                f"Cannot close workspace: {len(unresolved)} unfinished finding(s)"
            )
        self.closed_at = _now()
        self.closed_by = closer
        self.closure_summary = summary
        if audit_trail is not None:
            audit_trail.record_event(
                event_type="verification.workspace_closed",
                payload={
                    "workspace_id": self.workspace_id,
                    "summary": summary,
                    "finding_count": len(self.findings),
                },
                actor=closer,
            )
        return self

    def to_api_payload(self) -> dict[str, Any]:
        """Return the workspace shape exposed by ``/api/v1/verification/{id}``."""
        return {
            "workspace_id": self.workspace_id,
            "fund_name": self.fund_name,
            "reporting_period": self.reporting_period,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "closed_by": self.closed_by,
            "closure_summary": self.closure_summary,
            "pack": self.pack.model_dump(mode="json"),
            "evidence_graph": (
                self.evidence_graph.model_dump(mode="json")
                if self.evidence_graph is not None
                else None
            ),
            "findings": [f.model_dump(mode="json") for f in self.findings],
            "comments": [c.model_dump(mode="json") for c in self.comments],
        }

    def _find_comment(self, comment_id: str) -> VerificationComment:
        for comment in self.comments:
            if comment.comment_id == comment_id:
                return comment
        raise KeyError(f"Unknown comment: {comment_id}")

    def _find_finding(self, finding_id: str) -> VerificationFinding:
        for finding in self.findings:
            if finding.finding_id == finding_id:
                return finding
        raise KeyError(f"Unknown finding: {finding_id}")

    def _visible_evidence_ids(self) -> set[str]:
        ids = {item.entry_id for item in self.list_evidence()}
        if self.evidence_graph is not None:
            ids.update(self.evidence_graph.node_ids())
        return ids

    def _validate_evidence_refs(self, evidence_refs: Iterable[str]) -> None:
        refs = list(evidence_refs)
        if not refs:
            return
        visible = self._visible_evidence_ids()
        missing = [ref for ref in refs if ref not in visible]
        if missing:
            raise ValueError(
                "Finding references evidence outside the verifier workspace: "
                + ", ".join(missing)
            )


def open_workspace(
    *,
    pack: AssurancePack,
    evidence_graph: EvidenceGraph | None = None,
    permitted_evidence_ids: Iterable[str] | None = None,
) -> VerificationWorkspace:
    """Open a verifier workspace from an :class:`AssurancePack`."""
    return VerificationWorkspace(
        fund_name=pack.fund_name,
        reporting_period=pack.reporting_period,
        pack=pack,
        evidence_graph=evidence_graph,
        permitted_evidence_ids=list(permitted_evidence_ids or []),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "CommentStatus",
    "FindingSeverity",
    "FindingStatus",
    "VerificationComment",
    "VerificationFinding",
    "VerificationWorkspace",
    "open_workspace",
]
