"""Heuristic source verifier — rule-based, no external API.

This is the deterministic fall-back verifier. It applies straightforward
rules:

  * Quantified outcomes with explicit year + unit + verifying organisation
    cited nearby in the source corpus → verified=True
  * Commitments (forward-looking) → verified=False but flagged as
    ``promissory`` rather than fabricated.
  * Vague / ambiguous wording → verified=False with a "weak language" reason.

A real production deployment would replace this with an adapter that calls
out to (e.g.) audit firm databases, regulator filings, scientific
publications, etc.
"""
from __future__ import annotations

import re

from openharness.impact.extractors.base import (
    ExtractedClaim,
    SourceVerifier,  # noqa: F401 — re-exported protocol for documentation / subclassing
    VerificationResult,
)


_AUTHORITATIVE_SOURCES = (
    "audited", "third party", "third-party", "verified by", "certified by",
    "validated by", "assured by", "attested by", "iso", "sgs", "bureau veritas",
    "deloitte", "kpmg", "ernst & young", "ey", "pwc", "pricewaterhousecoopers",
    "moody's", "msci", "sustainalytics", "isos", "verra", "gold standard",
    "sbti", "cdp",
)
_WEAK_LANGUAGE = (
    "could", "may", "might", "potentially", "approximately", "around", "roughly",
    "estimated", "estimate", "projected", "expected", "anticipated",
)


class HeuristicVerifier:
    """Concrete `SourceVerifier` — deterministic, no external calls."""
    id = "heuristic"

    def verify(
        self, claim: ExtractedClaim, *, context: dict | None = None
    ) -> VerificationResult:
        text = (claim.text or "").lower()
        corpus = ((context or {}).get("source_corpus") or "").lower()

        sources_hit = [s for s in _AUTHORITATIVE_SOURCES if s in text or s in corpus]
        weak_hit = [w for w in _WEAK_LANGUAGE if re.search(rf"\b{re.escape(w)}\b", text)]

        if claim.category == "commitment":
            return VerificationResult(
                claim_text=claim.text,
                verified=False,
                confidence=0.3,
                reason="Forward-looking commitment — not verifiable until target year.",
                supporting_sources=sources_hit,
                verifier_id=self.id,
            )

        if claim.category in {"certification"} and sources_hit:
            return VerificationResult(
                claim_text=claim.text,
                verified=True,
                confidence=0.7,
                reason="Certification mentioned alongside accredited body.",
                supporting_sources=sources_hit,
                verifier_id=self.id,
            )

        if claim.category in {"outcome", "output"}:
            has_year = claim.metric_year is not None
            has_value = claim.metric_value is not None
            if has_year and has_value and sources_hit:
                return VerificationResult(
                    claim_text=claim.text,
                    verified=True,
                    confidence=0.65,
                    reason="Quantified outcome with year, unit, and authoritative source.",
                    supporting_sources=sources_hit,
                    verifier_id=self.id,
                )
            if has_year and has_value:
                return VerificationResult(
                    claim_text=claim.text,
                    verified=False,
                    confidence=0.4,
                    reason="Quantified, but no third-party assurance found in the surrounding text.",
                    verifier_id=self.id,
                )

        if weak_hit:
            return VerificationResult(
                claim_text=claim.text,
                verified=False,
                confidence=0.2,
                reason=f"Weak / hedging language detected: {', '.join(weak_hit)}.",
                verifier_id=self.id,
            )

        return VerificationResult(
            claim_text=claim.text,
            verified=False,
            confidence=0.25,
            reason="Insufficient evidence to verify.",
            verifier_id=self.id,
        )
