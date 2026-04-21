"""Pluggable extractor + verifier protocols.

`ClaimExtractor` lifts impact claims out of an unstructured document
(impact reports, pitch decks, websites). `SourceVerifier` checks whether a
given claim is corroborated by an authoritative external source (regulator
filings, peer-reviewed studies, audit reports).

Both are *Protocols* — concrete adapters live in their own modules
(`openai_extractor.py`, `anthropic_extractor.py`, etc.) and are looked up
by name through a small registry. This keeps the core engine free of any
provider-specific dependencies and makes it trivial to swap in an internal
compliance LLM behind a firewall.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


ClaimCategory = Literal[
    "outcome",        # quantified outcome ("3,500 students enrolled")
    "output",         # activity output ("delivered 12 workshops")
    "input",          # input metric ("invested $5M in sustainability")
    "commitment",     # forward-looking commitment ("net-zero by 2030")
    "certification",  # certification claim ("B-Corp certified")
    "comparison",     # peer / benchmark comparison
    "estimate",       # modelled / estimated value
    "anecdote",       # qualitative / case-study
    "unknown",
]


class ExtractedClaim(BaseModel):
    """Structured representation of one impact claim found in source text."""
    text: str
    category: ClaimCategory = "unknown"
    metric_value: float | None = None
    metric_unit: str | None = None
    metric_year: int | None = None
    geography: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.5)
    page_or_section: str | None = None
    suggested_iris_metric_id: str | None = None
    raw_extractor_id: str = ""


class VerificationResult(BaseModel):
    """Outcome of attempting to corroborate a claim against a source."""
    claim_text: str
    verified: bool
    confidence: float = Field(ge=0, le=1, default=0.0)
    supporting_sources: list[str] = Field(default_factory=list)
    contradicting_sources: list[str] = Field(default_factory=list)
    reason: str = ""
    checked_at: date = Field(default_factory=date.today)
    verifier_id: str = ""


@runtime_checkable
class ClaimExtractor(Protocol):
    """Provider-pluggable interface for extracting structured claims."""
    id: str

    def extract(self, text: str, *, context: dict | None = None) -> list[ExtractedClaim]:  # pragma: no cover
        ...


@runtime_checkable
class SourceVerifier(Protocol):
    """Provider-pluggable interface for verifying claims."""
    id: str

    def verify(self, claim: ExtractedClaim, *, context: dict | None = None) -> VerificationResult:  # pragma: no cover
        ...


# ---------------------------------------------------------------------------
# Default no-op implementations — used when no provider is configured. They
# keep downstream pipelines deterministic without leaking demo data.
# ---------------------------------------------------------------------------

class NoopExtractor:
    """Returns no claims — used when no LLM provider is configured."""
    id = "noop"

    def extract(self, text: str, *, context: dict | None = None) -> list[ExtractedClaim]:
        return []


class NoopVerifier:
    """Marks every claim as 'unverified' with confidence 0.

    Production deployments will swap this for a real verifier; the no-op
    version is the safe default — it never returns a false positive.
    """
    id = "noop"

    def verify(self, claim: ExtractedClaim, *, context: dict | None = None) -> VerificationResult:
        return VerificationResult(
            claim_text=claim.text,
            verified=False,
            confidence=0.0,
            reason="No verifier configured. Configure a SourceVerifier provider.",
            verifier_id=self.id,
        )


# ---------------------------------------------------------------------------
# Tiny registry — Cursor-style entrypoint discovery (Phase 15) plugs in here
# ---------------------------------------------------------------------------

_EXTRACTORS: dict[str, ClaimExtractor] = {"noop": NoopExtractor()}
_VERIFIERS: dict[str, SourceVerifier] = {"noop": NoopVerifier()}


def register_extractor(extractor: ClaimExtractor) -> None:
    if not getattr(extractor, "id", None):
        raise ValueError("Extractor must define an `id` attribute.")
    _EXTRACTORS[extractor.id] = extractor


def register_verifier(verifier: SourceVerifier) -> None:
    if not getattr(verifier, "id", None):
        raise ValueError("Verifier must define an `id` attribute.")
    _VERIFIERS[verifier.id] = verifier


def get_extractor(extractor_id: str = "noop") -> ClaimExtractor:
    if extractor_id not in _EXTRACTORS:
        raise KeyError(
            f"Unknown extractor '{extractor_id}'. Registered: {sorted(_EXTRACTORS)}"
        )
    return _EXTRACTORS[extractor_id]


def get_verifier(verifier_id: str = "noop") -> SourceVerifier:
    if verifier_id not in _VERIFIERS:
        raise KeyError(
            f"Unknown verifier '{verifier_id}'. Registered: {sorted(_VERIFIERS)}"
        )
    return _VERIFIERS[verifier_id]
