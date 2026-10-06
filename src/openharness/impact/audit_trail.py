"""Immutable audit trail (Phase 17).

Thin wrapper around :mod:`openharness.impact.signed_feed` that appends
*every* scoring / classification / DD decision to the hash-chained
feed, so auditors can replay the exact inputs that produced each
published number.

This module intentionally keeps a small API surface: record events
through :func:`record_event` and the chain takes care of content hashes,
previous-hash linking and HMAC signatures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.signed_feed import (
    ReportFeed,
    SignedReport,
    LazySigner,
    Signer,
)


MetricAuditEventType = Literal[
    "metric_created",
    "metric_updated",
    "metric_imported",
    "metric_approved",
]


class MetricAuditEvent(BaseModel):
    """Structured audit event for metric lifecycle changes."""

    metric_id: str
    action: MetricAuditEventType
    old_value: Any = None
    new_value: Any = None
    source: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    review_status: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportPublicationEvent(BaseModel):
    """Structured audit event for report publication."""

    report_id: str
    report_format: str
    standards: list[str] = Field(default_factory=list)
    evidence_manifest_hash: str = ""
    report_hash: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass
class AuditTrail:
    """Append-only, hash-chained log of impact decisions.

    Parameters
    ----------
    tenant_id / fund_id:
        Scope for this trail. A GP typically has one trail per fund.
    signer:
        :class:`Signer` implementation. Defaults to a demo HMAC signer;
        production deployments should supply a KMS-backed signer.
    """

    tenant_id: str = "default"
    fund_id: str = "default"
    signer: Signer = field(default_factory=lambda: LazySigner("audit"))
    store: Any = None  # openharness.impact.state_store.StateStore (W5.3)
    feed: ReportFeed = field(init=False)

    def __post_init__(self) -> None:
        self.feed = ReportFeed(tenant_id=self.tenant_id, fund_id=self.fund_id)
        self._reload()

    def _reload(self) -> None:
        """Restore the chain from the state store (several trails may share a fund)."""
        if self.store is None:
            return
        saved = self.store.get(self.tenant_id, "audit_trail", self.fund_id)
        if saved:
            self.feed = ReportFeed.model_validate(saved)

    def _save(self) -> None:
        if self.store is not None:
            self.store.put(self.tenant_id, "audit_trail", self.fund_id, self.feed.model_dump(mode="json"))

    def record_event(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        actor: str = "system",
        period: str | None = None,
    ) -> SignedReport:
        """Append one event. ``event_type`` becomes the report kind."""
        enriched = dict(payload)
        enriched.setdefault("actor", actor)
        enriched.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        p = period or datetime.now(timezone.utc).strftime("%Y-%m")
        self._reload()  # append to the latest persisted head, not a stale copy
        report = self.feed.append(self.signer, event_type, p, enriched)
        self._save()
        return report

    def record_metric_event(
        self,
        *,
        action: MetricAuditEventType,
        metric_id: str,
        actor: str,
        period: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        source: str = "",
        evidence_refs: list[str] | None = None,
        review_status: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SignedReport:
        """Append a structured metric lifecycle event."""
        event = MetricAuditEvent(
            metric_id=metric_id.strip().upper(),
            action=action,
            old_value=old_value,
            new_value=new_value,
            source=source,
            evidence_refs=evidence_refs or [],
            review_status=review_status,
            metadata=metadata or {},
        )
        return self.record_event(
            event_type=f"metric.{action.removeprefix('metric_')}",
            payload=event.model_dump(mode="json"),
            actor=actor,
            period=period,
        )

    def record_report_publication(
        self,
        *,
        report_id: str,
        report_format: str,
        actor: str,
        period: str,
        standards: list[str] | None = None,
        evidence_manifest_hash: str = "",
        report_hash: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SignedReport:
        """Append a structured report-publication event."""
        event = ReportPublicationEvent(
            report_id=report_id,
            report_format=report_format,
            standards=standards or [],
            evidence_manifest_hash=evidence_manifest_hash,
            report_hash=report_hash,
            metadata=metadata or {},
        )
        return self.record_event(
            event_type="report.published",
            payload=event.model_dump(mode="json"),
            actor=actor,
            period=period,
        )

    def verify(self) -> tuple[bool, list[str]]:
        return self.feed.verify(self.signer)

    @property
    def length(self) -> int:
        return len(self.feed.reports)

    @property
    def head(self) -> str:
        return self.feed.head_hash


__all__ = [
    "AuditTrail",
    "MetricAuditEvent",
    "MetricAuditEventType",
    "ReportPublicationEvent",
]
