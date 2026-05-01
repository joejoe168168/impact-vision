"""Tests for v3 third-party verifier workspace."""

from __future__ import annotations

import pytest

from openharness.impact.assurance import EvidenceEntry, build_assurance_pack
from openharness.impact.audit_trail import AuditTrail
from openharness.impact.verification_workspace import open_workspace


def _pack():
    return build_assurance_pack(
        fund_name="Demo Fund",
        reporting_period="Q1 2026",
        assertion_text="Management assertion text.",
        prepared_by="CFO",
        subject_description="Selected impact metrics",
        metrics=["OI4112", "PI4060"],
    )


def _pack_with_evidence():
    return build_assurance_pack(
        fund_name="Demo Fund",
        reporting_period="Q1 2026",
        assertion_text="Management assertion text.",
        prepared_by="CFO",
        subject_description="Selected impact metrics",
        metrics=["OI4112"],
        evidence=[
            EvidenceEntry(
                entry_id="evidence:workbook",
                description="Audited metric workbook",
            ),
        ],
    )


def test_workspace_opens_with_pack_and_supports_findings_lifecycle() -> None:
    workspace = open_workspace(pack=_pack())
    audit = AuditTrail()
    finding = workspace.submit_finding(
        observation="Evidence missing for OI4112 Q1",
        severity="high",
        raised_by="auditor",
        audit_trail=audit,
    )
    workspace.respond_to_finding(
        finding.finding_id,
        response="Workbook attached.",
        responder="cfo",
        audit_trail=audit,
    )
    workspace.transition_finding(
        finding.finding_id,
        status="resolved",
        actor="auditor",
        audit_trail=audit,
    )
    assert workspace.findings[0].status == "resolved"
    assert audit.length == 3


def test_invalid_finding_transition_raises() -> None:
    workspace = open_workspace(pack=_pack())
    finding = workspace.submit_finding(
        observation="Late edit",
        severity="medium",
        raised_by="auditor",
    )
    # Move through the valid open -> in_review -> resolved path
    workspace.transition_finding(finding.finding_id, status="in_review", actor="auditor")
    workspace.transition_finding(finding.finding_id, status="resolved", actor="auditor")
    # Resolved is terminal; any further transition must fail.
    with pytest.raises(ValueError):
        workspace.transition_finding(finding.finding_id, status="in_review", actor="auditor")


def test_finding_evidence_refs_must_be_visible_to_workspace() -> None:
    workspace = open_workspace(pack=_pack_with_evidence())
    finding = workspace.submit_finding(
        observation="Trace workbook",
        severity="medium",
        raised_by="auditor",
        evidence_refs=["evidence:workbook"],
    )
    assert finding.evidence_refs == ["evidence:workbook"]
    with pytest.raises(ValueError, match="outside the verifier workspace"):
        workspace.submit_finding(
            observation="Unknown evidence",
            severity="medium",
            raised_by="auditor",
            evidence_refs=["evidence:missing"],
        )


def test_terminal_finding_cannot_receive_management_response() -> None:
    workspace = open_workspace(pack=_pack())
    finding = workspace.submit_finding(
        observation="Late edit",
        severity="medium",
        raised_by="auditor",
    )
    workspace.transition_finding(finding.finding_id, status="unresolved", actor="auditor")
    with pytest.raises(ValueError, match="terminal finding"):
        workspace.respond_to_finding(
            finding.finding_id,
            response="Updated anyway",
            responder="cfo",
        )


def test_comment_thread_anchored_to_evidence_node_and_resolved() -> None:
    workspace = open_workspace(pack=_pack())
    comment = workspace.add_comment(
        evidence_node_id="evidence:audit-trail",
        author="auditor",
        text="Need to see signed memo.",
    )
    assert comment.status == "open"
    resolved = workspace.resolve_comment(comment.comment_id, resolver="cfo")
    assert resolved.status == "resolved"


def test_close_blocks_until_findings_resolved() -> None:
    workspace = open_workspace(pack=_pack())
    workspace.submit_finding(
        observation="Open issue",
        severity="medium",
        raised_by="auditor",
    )
    with pytest.raises(ValueError):
        workspace.close(closer="audit_lead")
    workspace.transition_finding(
        workspace.findings[0].finding_id,
        status="unresolved",
        actor="auditor",
    )
    workspace.close(closer="audit_lead", summary="Closed with one unresolved finding.")
    assert workspace.closed_at != ""


def test_to_api_payload_includes_findings_and_comments() -> None:
    workspace = open_workspace(pack=_pack())
    workspace.submit_finding(
        observation="Test",
        severity="info",
        raised_by="auditor",
    )
    payload = workspace.to_api_payload()
    assert payload["fund_name"] == "Demo Fund"
    assert len(payload["findings"]) == 1
    assert "pack" in payload
