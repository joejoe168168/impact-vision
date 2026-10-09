"""LP export bundles, report publication workflow, control checks and immutable manifests (moved from roadmap_v2, v7 W5.4)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from impact_vision.impact._util import _now
from impact_vision.impact.frameworks.edci import EDCICompletenessReport, portfolio_edci_completeness
from impact_vision.impact.models import MetricRecord

PublicationState = Literal["draft", "reviewer_approved", "published", "superseded"]


class LPExportBundle(BaseModel):
    """LP export bundle manifest."""

    bundle_id: str
    formats: list[Literal["pdf", "html", "xlsx", "json"]]
    source_index: list[str] = Field(default_factory=list)
    evidence_manifest: dict[str, str] = Field(default_factory=dict)
    edci_report: EDCICompletenessReport | None = None


def build_lp_export_bundle(
    *,
    formats: list[Literal["pdf", "html", "xlsx", "json"]],
    source_refs: list[str],
    portfolio_payloads: list[dict[str, Any]] | None = None,
) -> LPExportBundle:
    """Build an LP bundle with source index, evidence hashes, and optional EDCI attachment."""
    manifest = {ref: hashlib.sha256(ref.encode("utf-8")).hexdigest() for ref in source_refs}
    return LPExportBundle(
        bundle_id=f"lp_{hashlib.sha1(json.dumps(source_refs, sort_keys=True).encode(), usedforsecurity=False).hexdigest()[:10]}",
        formats=formats,
        source_index=source_refs,
        evidence_manifest=manifest,
        edci_report=portfolio_edci_completeness(portfolio_payloads) if portfolio_payloads else None,
    )


class ReportPublication(BaseModel):
    """Report publication workflow state."""

    report_id: str
    state: PublicationState = "draft"
    reviewer: str = ""
    published_at: str = ""
    supersedes: str = ""


def transition_report_publication(
    report: ReportPublication,
    next_state: PublicationState,
    *,
    actor: str,
) -> ReportPublication:
    """Move a report through draft, approval, publication, and supersession."""
    allowed = {
        "draft": {"reviewer_approved"},
        "reviewer_approved": {"published"},
        "published": {"superseded"},
        "superseded": set(),
    }
    if next_state not in allowed[report.state]:
        raise ValueError(f"Invalid report transition {report.state} -> {next_state}")
    updates: dict[str, Any] = {"state": next_state}
    if next_state == "reviewer_approved":
        updates["reviewer"] = actor
    if next_state == "published":
        updates["published_at"] = _now()
    return report.model_copy(update=updates)


class FundBrandingProfile(BaseModel):
    """White-label LP/reporting branding metadata."""

    fund_name: str
    logo_url: str = ""
    primary_color: str = "#0d47a1"
    disclaimer: str = ""
    contact_email: str = ""


class ControlCheckResult(BaseModel):
    """Internal control check result."""

    control_id: str
    passed: bool
    severity: Literal["low", "medium", "high"] = "medium"
    message: str = ""


def run_control_checks(
    *,
    metric_records: list[MetricRecord],
    ai_outputs_pending_review: int = 0,
    late_edit_count: int = 0,
    unsupported_claim_count: int = 0,
) -> list[ControlCheckResult]:
    """Check segregation, late edits, unreviewed AI, and unsupported claims."""
    owners = {record.owner for record in metric_records}
    approvers = {record.owner for record in metric_records if record.is_verified}
    return [
        ControlCheckResult(
            control_id="segregation_of_duties",
            passed=not owners or owners != approvers,
            severity="high",
            message="Metric owner set should not equal approver set.",
        ),
        ControlCheckResult(
            control_id="late_edits",
            passed=late_edit_count == 0,
            severity="medium",
            message=f"{late_edit_count} late edit(s) after review cutoff.",
        ),
        ControlCheckResult(
            control_id="unreviewed_ai_outputs",
            passed=ai_outputs_pending_review == 0,
            severity="high",
            message=f"{ai_outputs_pending_review} AI output(s) pending review.",
        ),
        ControlCheckResult(
            control_id="unsupported_claims",
            passed=unsupported_claim_count == 0,
            severity="high",
            message=f"{unsupported_claim_count} unsupported claim(s).",
        ),
    ]


class ImmutableReportManifest(BaseModel):
    """Immutable manifest containing hashes for report artifacts."""

    report_id: str
    artifact_hashes: dict[str, str]
    manifest_hash: str


def build_immutable_report_manifest(report_id: str, artifacts: dict[str, str]) -> ImmutableReportManifest:
    """Hash source documents, exports, and final reports into one manifest."""
    artifact_hashes = {
        name: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for name, content in sorted(artifacts.items())
    }
    manifest_hash = hashlib.sha256(json.dumps(artifact_hashes, sort_keys=True).encode("utf-8")).hexdigest()
    return ImmutableReportManifest(report_id=report_id, artifact_hashes=artifact_hashes, manifest_hash=manifest_hash)


class ExceptionRegisterEntry(BaseModel):
    """Known gap, override, or unresolved limitation."""

    exception_id: str
    category: Literal["gap", "management_override", "limitation"]
    description: str
    owner: str
    status: Literal["open", "mitigated", "accepted"] = "open"


__all__ = [
    "PublicationState",
    "LPExportBundle",
    "build_lp_export_bundle",
    "ReportPublication",
    "transition_report_publication",
    "FundBrandingProfile",
    "ControlCheckResult",
    "run_control_checks",
    "ImmutableReportManifest",
    "build_immutable_report_manifest",
    "ExceptionRegisterEntry",
]
