"""BlueMark-style 3-Pillar Verification Bundle (roadmap-v4 Track 10).

Composes the existing v3 surfaces — :mod:`openharness.impact.verification_workspace`,
:mod:`openharness.impact.frameworks.ifc_opim`, the audit trail, the evidence
graph, and :mod:`openharness.impact.signed_feed` — into the three pillars
LPs and verifiers already recognise from BlueMark:

1. **Mandate verification** — thesis, theory of change, governance,
   exclusions, additionality, beneficiary lens (Track 10.1).
2. **Practice verification** — OPIM 9-principle alignment with evidence
   references and finding lifecycle (Track 10.2).
3. **Reporting verification** — claim-by-claim review of the LP narrative
   against the evidence graph and audit trail (Track 10.3).

Adds:

* A verifier-facing read-only token + engagement-scoped access structure
  (Track 10.4).
* Independent-verifier marketplace metadata (Track 10.5) — pluggable so a
  consultant can hand the bundle off to BlueMark / DNV / KPMG without
  duplicating data.
* `AssuranceBundle` — the PDF + JSON-LD + signed-manifest envelope that
  an OPIM Principle 9 publication needs (Track 10.6).
* `AssuranceReadinessBadge` — completeness-driven badge on the engagement
  workspace (Track 10.7).
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field


PillarName = Literal["mandate", "practice", "reporting"]

ItemStatus = Literal["not_started", "in_progress", "evidence_submitted", "reviewed", "verified"]

FindingSeverity = Literal["info", "low", "medium", "high", "critical"]


# --------------------------------------------- Pillar 1: Mandate verification


class MandateItem(BaseModel):
    """One mandate-verification check."""

    item_id: str = Field(default_factory=lambda: f"m_{secrets.token_hex(4)}")
    code: str
    question: str
    status: ItemStatus = "not_started"
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str = ""


class MandatePack(BaseModel):
    """Track 10.1 — mandate verification pack."""

    pack_id: str = Field(default_factory=lambda: f"pillar1_{secrets.token_hex(4)}")
    engagement_id: str = ""
    items: list[MandateItem] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completion_pct(self) -> float:
        if not self.items:
            return 0.0
        done = sum(1 for i in self.items if i.status == "verified")
        return round(done / len(self.items), 3)


_MANDATE_CHECKS = [
    ("M1", "Is the investment thesis explicit about who benefits and how?"),
    ("M2", "Does the fund have a documented theory of change?"),
    ("M3", "Are exclusions (e.g. fossil fuels, weapons, tobacco) formally governed?"),
    ("M4", "Has additionality been tested (financial + impact)?"),
    ("M5", "Is the beneficiary lens (equity + inclusion) explicit?"),
    ("M6", "Is there IC-level governance over impact decisions?"),
]


def build_mandate_pack(engagement_id: str = "") -> MandatePack:
    return MandatePack(
        engagement_id=engagement_id,
        items=[MandateItem(code=code, question=q) for code, q in _MANDATE_CHECKS],
    )


# --------------------------------------------- Pillar 2: Practice verification


class PracticePrincipleItem(BaseModel):
    """One OPIM principle alignment check."""

    item_id: str = Field(default_factory=lambda: f"p_{secrets.token_hex(4)}")
    principle_number: int
    principle_title: str
    status: ItemStatus = "not_started"
    evidence_refs: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class PracticePack(BaseModel):
    """Track 10.2 — OPIM 9-principle practice pack."""

    pack_id: str = Field(default_factory=lambda: f"pillar2_{secrets.token_hex(4)}")
    engagement_id: str = ""
    items: list[PracticePrincipleItem] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completion_pct(self) -> float:
        if not self.items:
            return 0.0
        done = sum(1 for i in self.items if i.status == "verified")
        return round(done / len(self.items), 3)


_OPIM_PRINCIPLES = [
    (1, "Define strategic impact objectives"),
    (2, "Manage strategic impact on a portfolio basis"),
    (3, "Establish the Manager's contribution to impact"),
    (4, "Assess expected impact of each investment"),
    (5, "Assess, address, and monitor impact risks"),
    (6, "Monitor impact progress and manage performance"),
    (7, "Conduct exits in a responsible manner"),
    (8, "Review, document, and improve decisions and processes"),
    (9, "Publicly disclose alignment and arrange independent verification"),
]


def build_practice_pack(engagement_id: str = "") -> PracticePack:
    return PracticePack(
        engagement_id=engagement_id,
        items=[
            PracticePrincipleItem(principle_number=num, principle_title=title)
            for num, title in _OPIM_PRINCIPLES
        ],
    )


# ------------------------------------------- Pillar 3: Reporting verification


class ReportingClaim(BaseModel):
    """One claim under reporting verification."""

    claim_id: str = Field(default_factory=lambda: f"c_{secrets.token_hex(4)}")
    text: str
    evidence_refs: list[str] = Field(default_factory=list)
    status: Literal["approved", "caveated", "rejected", "needs_evidence"] = "needs_evidence"
    reviewer: str = ""


class ReportingPack(BaseModel):
    """Track 10.3 — claim-by-claim reporting pack."""

    pack_id: str = Field(default_factory=lambda: f"pillar3_{secrets.token_hex(4)}")
    engagement_id: str = ""
    lp_narrative_ref: str = ""
    claims: list[ReportingClaim] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completion_pct(self) -> float:
        if not self.claims:
            return 0.0
        done = sum(
            1 for c in self.claims if c.status in {"approved", "caveated", "rejected"}
        )
        return round(done / len(self.claims), 3)


def build_reporting_pack(
    engagement_id: str = "",
    lp_narrative_ref: str = "",
    claims: Iterable[dict] | None = None,
) -> ReportingPack:
    return ReportingPack(
        engagement_id=engagement_id,
        lp_narrative_ref=lp_narrative_ref,
        claims=[
            ReportingClaim.model_validate(c) for c in claims or []
        ],
    )


# --------------------------------------------- verifier token / access scope


class VerifierToken(BaseModel):
    """Engagement-scoped read-only token for a third-party verifier."""

    token_id: str = Field(default_factory=lambda: f"vrft_{secrets.token_hex(8)}")
    engagement_id: str
    verifier_name: str
    token_hash: str
    scopes: list[str] = Field(default_factory=lambda: ["read:pillars", "read:evidence"])
    issued_at: str = Field(default_factory=lambda: _now())
    expires_at: str = ""


def issue_verifier_token(
    *,
    engagement_id: str,
    verifier_name: str,
    token: str | None = None,
    validity_days: int = 90,
) -> tuple[VerifierToken, str]:
    """Issue a verifier token. Returns ``(record, plaintext)`` once only."""
    raw = token or secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires = datetime.now(timezone.utc).replace(microsecond=0) + _timedelta(validity_days)
    record = VerifierToken(
        engagement_id=engagement_id,
        verifier_name=verifier_name,
        token_hash=token_hash,
        expires_at=expires.isoformat(),
    )
    return record, raw


def _timedelta(days: int):
    from datetime import timedelta

    return timedelta(days=max(1, days))


# -------------------------------------------- independent-verifier marketplace


class VerifierMarketplaceListing(BaseModel):
    """Track 10.5 — marketplace metadata for an independent verifier."""

    listing_id: str = Field(default_factory=lambda: f"vmp_{secrets.token_hex(4)}")
    name: str
    accreditations: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    methodologies: list[str] = Field(default_factory=list)
    contact: str = ""
    pillars_supported: list[PillarName] = Field(
        default_factory=lambda: ["mandate", "practice", "reporting"]
    )


VERIFIER_MARKETPLACE: list[VerifierMarketplaceListing] = [
    VerifierMarketplaceListing(
        name="BlueMark",
        accreditations=["OPIM", "ISAE 3000"],
        sectors=["impact_funds", "dfi"],
        jurisdictions=["global"],
        methodologies=["3-pillar"],
    ),
    VerifierMarketplaceListing(
        name="KPMG Sustainability Assurance",
        accreditations=["ISAE 3000", "ISSB"],
        sectors=["corporates", "funds"],
        jurisdictions=["EU", "UK", "US"],
        methodologies=["ISSB", "ESRS", "OPIM"],
    ),
    VerifierMarketplaceListing(
        name="DNV Business Assurance",
        accreditations=["ISAE 3000", "AA1000AS"],
        sectors=["corporates", "funds"],
        jurisdictions=["global"],
        methodologies=["AA1000AS", "ISSB"],
    ),
]


def list_verifier_marketplace() -> list[VerifierMarketplaceListing]:
    return list(VERIFIER_MARKETPLACE)


# ----------------------------------------------- Assurance bundle + manifest


class AssuranceManifest(BaseModel):
    """Signed manifest binding the three pillars together."""

    manifest_id: str = Field(default_factory=lambda: f"mf_{secrets.token_hex(6)}")
    engagement_id: str = ""
    pillar_hashes: dict[PillarName, str]
    generated_at: str = Field(default_factory=lambda: _now())
    signature_algorithm: str = "sha256"
    signature: str = ""


class AssuranceBundle(BaseModel):
    """Track 10.6 — OPIM Principle 9 publication bundle."""

    bundle_id: str = Field(default_factory=lambda: f"bundle_{secrets.token_hex(6)}")
    engagement_id: str = ""
    mandate: MandatePack
    practice: PracticePack
    reporting: ReportingPack
    manifest: AssuranceManifest

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overall_completion_pct(self) -> float:
        parts = [
            self.mandate.completion_pct,
            self.practice.completion_pct,
            self.reporting.completion_pct,
        ]
        return round(sum(parts) / len(parts), 3)


def _hash_payload(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def build_assurance_bundle(
    *,
    engagement_id: str,
    mandate: MandatePack,
    practice: PracticePack,
    reporting: ReportingPack,
    secret_key: bytes = b"impact-vision-assurance",
) -> AssuranceBundle:
    """Build and sign an assurance bundle.

    ``secret_key`` defaults to the demo constant used throughout the
    v3 HMAC audit trail (see
    :class:`openharness.impact.audit_trail.AuditTrail`). Production
    deployments MUST override it with a KMS- or HSM-issued key; the
    default is only appropriate for CI and local development.
    """
    import hmac

    pillar_hashes = {
        "mandate": _hash_payload(mandate.model_dump(mode="json")),
        "practice": _hash_payload(practice.model_dump(mode="json")),
        "reporting": _hash_payload(reporting.model_dump(mode="json")),
    }
    manifest_body = _hash_payload(pillar_hashes)
    signature = hmac.new(secret_key, manifest_body.encode("utf-8"), hashlib.sha256).hexdigest()
    manifest = AssuranceManifest(
        engagement_id=engagement_id,
        pillar_hashes=pillar_hashes,  # type: ignore[arg-type]
        signature=signature,
    )
    return AssuranceBundle(
        engagement_id=engagement_id,
        mandate=mandate,
        practice=practice,
        reporting=reporting,
        manifest=manifest,
    )


def verify_assurance_bundle(
    bundle: AssuranceBundle,
    *,
    secret_key: bytes = b"impact-vision-assurance",
) -> bool:
    """Recompute hashes / signature and verify the bundle is untampered."""
    import hmac

    expected_hashes = {
        "mandate": _hash_payload(bundle.mandate.model_dump(mode="json")),
        "practice": _hash_payload(bundle.practice.model_dump(mode="json")),
        "reporting": _hash_payload(bundle.reporting.model_dump(mode="json")),
    }
    if expected_hashes != bundle.manifest.pillar_hashes:
        return False
    manifest_body = _hash_payload(expected_hashes)
    expected_sig = hmac.new(secret_key, manifest_body.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, bundle.manifest.signature)


# ------------------------------------------- Assurance-ready badge (10.7)


class AssuranceReadinessBadge(BaseModel):
    engagement_id: str
    is_assurance_ready: bool
    score: float
    gaps: list[str] = Field(default_factory=list)
    issued_at: str = Field(default_factory=lambda: _now())


def evaluate_assurance_readiness(
    bundle: AssuranceBundle,
    *,
    required_completion_pct: float = 0.85,
) -> AssuranceReadinessBadge:
    """Set the assurance-ready badge based on pillar completeness."""
    gaps: list[str] = []
    if bundle.mandate.completion_pct < required_completion_pct:
        gaps.append(
            f"Mandate pillar below threshold ({bundle.mandate.completion_pct})."
        )
    if bundle.practice.completion_pct < required_completion_pct:
        gaps.append(
            f"Practice pillar below threshold ({bundle.practice.completion_pct})."
        )
    if bundle.reporting.completion_pct < required_completion_pct:
        gaps.append(
            f"Reporting pillar below threshold ({bundle.reporting.completion_pct})."
        )
    return AssuranceReadinessBadge(
        engagement_id=bundle.engagement_id,
        is_assurance_ready=not gaps,
        score=bundle.overall_completion_pct,
        gaps=gaps,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "AssuranceBundle",
    "AssuranceManifest",
    "AssuranceReadinessBadge",
    "FindingSeverity",
    "ItemStatus",
    "MandateItem",
    "MandatePack",
    "PillarName",
    "PracticePack",
    "PracticePrincipleItem",
    "ReportingClaim",
    "ReportingPack",
    "VERIFIER_MARKETPLACE",
    "VerifierMarketplaceListing",
    "VerifierToken",
    "build_assurance_bundle",
    "build_mandate_pack",
    "build_practice_pack",
    "build_reporting_pack",
    "evaluate_assurance_readiness",
    "issue_verifier_token",
    "list_verifier_marketplace",
    "verify_assurance_bundle",
]
