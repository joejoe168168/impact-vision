"""Signed / hash-chained LP report feed.

Produces a tamper-evident audit trail of LP reports. Each report becomes
a `SignedReport` carrying:

  * `content_hash`  — SHA-256 of the canonical JSON payload.
  * `prev_hash`     — `content_hash` of the previous report in the chain.
  * `signature`     — HMAC-SHA256 of `(content_hash || prev_hash)` using the
                      tenant's signing key. (HMAC is the default; pluggable
                      `Signer` allows Ed25519 / x509 / KMS in production.)
  * `published_at`  — RFC-3339 timestamp.

LPs (or auditors) can replay the chain and detect any retroactive edit:
the chain only verifies if every link's `prev_hash` equals the previous
link's `content_hash` *and* every signature validates against the tenant's
public key.

This is intentionally a small, dependency-free implementation. Any tenant
that needs full PKI / non-repudiation should plug in a `Signer` backed by
HSM / KMS (AWS, GCP, Vault, etc.).
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


GENESIS_HASH = "0" * 64


def _canonical_json(payload: dict) -> bytes:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def content_hash(payload: dict) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


@runtime_checkable
class Signer(Protocol):
    id: str
    def sign(self, message: bytes) -> str: ...
    def verify(self, message: bytes, signature: str) -> bool: ...


@dataclass
class HMACSigner:
    """Default signer — symmetric HMAC. Good enough for internal LP packets;
    use Ed25519 / KMS for external non-repudiation."""
    key: bytes
    id: str = "hmac-sha256"

    def sign(self, message: bytes) -> str:
        return hmac.new(self.key, message, hashlib.sha256).hexdigest()

    def verify(self, message: bytes, signature: str) -> bool:
        expected = self.sign(message)
        return hmac.compare_digest(expected, signature)


class SignedReport(BaseModel):
    """One link in the LP report chain."""
    tenant_id: str
    fund_id: str
    report_kind: str           # "ilpa_esg" | "giin_iris" | "sfdr_pai" | ...
    report_period: str         # e.g. "2025-Q4"
    payload: dict[str, Any] = Field(default_factory=dict)
    content_hash: str
    prev_hash: str = GENESIS_HASH
    signature: str
    signer_id: str
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReportFeed(BaseModel):
    """Append-only log of `SignedReport`s for a tenant + fund."""
    tenant_id: str
    fund_id: str
    reports: list[SignedReport] = Field(default_factory=list)

    @property
    def head_hash(self) -> str:
        return self.reports[-1].content_hash if self.reports else GENESIS_HASH

    def append(
        self,
        signer: Signer,
        report_kind: str,
        report_period: str,
        payload: dict,
    ) -> SignedReport:
        ch = content_hash(payload)
        prev = self.head_hash
        msg = (ch + "|" + prev).encode("utf-8")
        sig = signer.sign(msg)
        report = SignedReport(
            tenant_id=self.tenant_id,
            fund_id=self.fund_id,
            report_kind=report_kind,
            report_period=report_period,
            payload=payload,
            content_hash=ch,
            prev_hash=prev,
            signature=sig,
            signer_id=signer.id,
        )
        self.reports.append(report)
        return report

    def verify(self, signer: Signer) -> tuple[bool, list[str]]:
        """Replay the chain. Returns ``(ok, problems)``."""
        problems: list[str] = []
        prev = GENESIS_HASH
        for i, r in enumerate(self.reports):
            recomputed = content_hash(r.payload)
            if recomputed != r.content_hash:
                problems.append(f"#{i}: content_hash mismatch (payload tampered)")
            if r.prev_hash != prev:
                problems.append(f"#{i}: prev_hash mismatch (chain broken)")
            msg = (r.content_hash + "|" + r.prev_hash).encode("utf-8")
            if not signer.verify(msg, r.signature):
                problems.append(f"#{i}: signature invalid")
            prev = r.content_hash
        return (len(problems) == 0, problems)


def export_chain(feed: ReportFeed) -> str:
    """JSON serialisation of the entire chain — what you ship to the LP."""
    return json.dumps(
        {
            "tenant_id": feed.tenant_id,
            "fund_id": feed.fund_id,
            "report_count": len(feed.reports),
            "head_hash": feed.head_hash,
            "reports": [r.model_dump(mode="json") for r in feed.reports],
        },
        indent=2,
        default=str,
    )


def import_chain(blob: str) -> ReportFeed:
    data = json.loads(blob)
    return ReportFeed(
        tenant_id=data["tenant_id"],
        fund_id=data["fund_id"],
        reports=[SignedReport.model_validate(r) for r in data.get("reports", [])],
    )
