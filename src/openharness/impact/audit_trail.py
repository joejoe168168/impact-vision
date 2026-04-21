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
from typing import Any

from openharness.impact.signed_feed import (
    HMACSigner,
    ReportFeed,
    SignedReport,
    Signer,
)


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
    signer: Signer = field(default_factory=lambda: HMACSigner(key=b"impact-vision-audit"))
    feed: ReportFeed = field(init=False)

    def __post_init__(self) -> None:
        self.feed = ReportFeed(tenant_id=self.tenant_id, fund_id=self.fund_id)

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
        return self.feed.append(self.signer, event_type, p, enriched)

    def verify(self) -> tuple[bool, list[str]]:
        return self.feed.verify(self.signer)

    @property
    def length(self) -> int:
        return len(self.feed.reports)

    @property
    def head(self) -> str:
        return self.feed.head_hash


__all__ = ["AuditTrail"]
