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
import logging
import os
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


@dataclass
class Ed25519Signer:
    """Asymmetric signer (v8 W5.5): only the private key can sign, anyone with
    the published public key can verify — so a verifier can't forge, unlike
    HMAC. Needs the ``cryptography`` package (``[assurance]`` extra)."""

    private_key: Any
    id: str = "ed25519"

    @classmethod
    def from_material(cls, raw: bytes | str) -> "Ed25519Signer":
        """PEM private key, or a base64 / hex 32-byte seed."""
        import base64
        import binascii

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        data = raw.encode("utf-8") if isinstance(raw, str) else raw
        if b"PRIVATE KEY" in data:
            return cls(serialization.load_pem_private_key(data, password=None))
        text = data.strip()
        for decode in (binascii.unhexlify, base64.b64decode):
            try:
                seed = decode(text)
            except (binascii.Error, ValueError):
                continue
            if len(seed) == 32:
                return cls(Ed25519PrivateKey.from_private_bytes(seed))
        raise SigningKeyError("Ed25519 key must be a PEM private key or a 32-byte seed (hex or base64)")

    @classmethod
    def generate(cls) -> "Ed25519Signer":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        return cls(Ed25519PrivateKey.generate())

    def public_key_pem(self) -> str:
        from cryptography.hazmat.primitives import serialization

        return self.private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")

    def private_key_pem(self) -> str:
        from cryptography.hazmat.primitives import serialization

        return self.private_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()).decode("ascii")

    def sign(self, message: bytes) -> str:
        return self.private_key.sign(message).hex()

    def verify(self, message: bytes, signature: str) -> bool:
        return verify_ed25519(message, signature, self.public_key_pem())


def verify_ed25519(message: bytes, signature: str, public_key_pem: str) -> bool:
    """Check an Ed25519 signature with only the public key (what a verifier holds)."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization

    try:
        key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
        key.verify(bytes.fromhex(signature), message)  # type: ignore[union-attr]
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def ed25519_env_var(purpose: str) -> str:
    return f"IMPACT_VISION_{purpose.upper()}_ED25519_KEY"


def get_ed25519_signer(purpose: str) -> Ed25519Signer | None:
    """The Ed25519 signer for *purpose* when a key is configured, else None.

    ``IMPACT_VISION_<PURPOSE>_ED25519_KEY`` → ``IMPACT_VISION_ED25519_KEY`` →
    a key file at ``IMPACT_VISION_ED25519_KEY_FILE``.
    """
    raw = os.environ.get(ed25519_env_var(purpose)) or os.environ.get("IMPACT_VISION_ED25519_KEY")
    path = os.environ.get("IMPACT_VISION_ED25519_KEY_FILE")
    if not raw and path and os.path.exists(path):
        raw = open(path, "rb").read()  # noqa: SIM115 - small key file
    return Ed25519Signer.from_material(raw) if raw else None


# --- Signing keys -----------------------------------------------------------
#
# Every signer resolves its key from the environment. The built-in development
# keys are public (they're in this source file), so anything signed with them
# is labelled ``hmac-sha256-dev`` and production deployments refuse to use
# them: set ``IMPACT_VISION_ENV=production`` or ``IMPACT_VISION_ALLOW_DEV_KEYS=0``.

logger = logging.getLogger(__name__)

# Historical development keys, kept per purpose so artifacts signed by earlier
# releases still verify in development.
_DEV_KEYS: dict[str, bytes] = {
    "audit": b"impact-vision-audit",
    "lp_portal": b"impact-vision-demo",
    "lp_dataroom": b"impact-vision-lp-dataroom",
    "assurance": b"impact-vision-assurance",
    "dmrv": b"impact-vision-dmrv",
}
_warned_dev_purposes: set[str] = set()


class SigningKeyError(ValueError):
    """Raised when no signing key is configured and development keys are disabled."""


def dev_keys_allowed() -> bool:
    """True unless the deployment is marked as production."""
    if os.environ.get("IMPACT_VISION_ENV", "").strip().lower() in {"prod", "production"}:
        return False
    return os.environ.get("IMPACT_VISION_ALLOW_DEV_KEYS", "1").strip() != "0"


def key_env_var(purpose: str) -> str:
    return f"IMPACT_VISION_{purpose.upper()}_HMAC_KEY"


def resolve_signing_key(purpose: str, key: bytes | str | None = None) -> tuple[bytes, bool]:
    """Return ``(key, is_dev_key)`` for *purpose*.

    Order: explicit *key* → ``IMPACT_VISION_<PURPOSE>_HMAC_KEY`` →
    ``IMPACT_VISION_HMAC_KEY`` → the development key (only when
    :func:`dev_keys_allowed`; otherwise :class:`SigningKeyError`).
    """
    raw = key or os.environ.get(key_env_var(purpose)) or os.environ.get("IMPACT_VISION_HMAC_KEY")
    if raw:
        return (raw.encode("utf-8") if isinstance(raw, str) else raw), False
    if not dev_keys_allowed():
        raise SigningKeyError(
            f"No signing key configured for {purpose!r}. Set {key_env_var(purpose)} "
            "(or IMPACT_VISION_HMAC_KEY); development keys are disabled in production."
        )
    if purpose not in _warned_dev_purposes:
        _warned_dev_purposes.add(purpose)
        logger.warning(
            "Signing %s artifacts with the public development key; signatures are not "
            "tamper-evident. Set %s for real deployments.",
            purpose,
            key_env_var(purpose),
        )
    return _DEV_KEYS.get(purpose, f"impact-vision-{purpose}".encode()), True


def get_signer(purpose: str, key: bytes | str | None = None) -> "HMACSigner":
    """HMAC signer for *purpose*; its ``id`` discloses a development key."""
    resolved, is_dev = resolve_signing_key(purpose, key)
    return HMACSigner(key=resolved, id="hmac-sha256-dev" if is_dev else "hmac-sha256")


class LazySigner:
    """Signer that resolves its key on first use, not at construction.

    Objects that *may* sign (audit trails, portals) can be created in a
    production deployment without a key; actually signing still fails closed.
    """

    def __init__(self, purpose: str) -> None:
        self.purpose = purpose
        self._signer: HMACSigner | None = None

    def _resolve(self) -> "HMACSigner":
        if self._signer is None:
            self._signer = get_signer(self.purpose)
        return self._signer

    @property
    def id(self) -> str:  # type: ignore[override]
        return self._resolve().id

    def sign(self, message: bytes) -> str:
        return self._resolve().sign(message)

    def verify(self, message: bytes, signature: str) -> bool:
        return self._resolve().verify(message, signature)


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
