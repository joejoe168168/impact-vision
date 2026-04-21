"""Pluggable extractor / verifier interfaces.

This package defines the *protocol* for swapping LLM providers and source
verifiers in and out of Impact Vision without coupling the core engine to
any single vendor (OpenAI, Anthropic, local models, internal compliance
tooling, etc.).
"""

from openharness.impact.extractors.base import (
    ClaimExtractor,
    ExtractedClaim,
    SourceVerifier,
    VerificationResult,
    NoopExtractor,
    NoopVerifier,
    get_extractor,
    get_verifier,
    register_extractor,
    register_verifier,
)
from openharness.impact.extractors.regex_extractor import RegexExtractor
from openharness.impact.extractors.heuristic_verifier import HeuristicVerifier
from openharness.impact.extractors.llm_extractor import LLMClaimExtractor
from openharness.impact.extractors.llm_verifier import LLMSourceVerifier

# Register the bundled deterministic providers so they're discoverable by id.
register_extractor(RegexExtractor())
register_verifier(HeuristicVerifier())

# The LLM providers are registered under their default ``id`` so
# ``ImpactVision(extractor_id="llm")`` works out-of-the-box; they are
# offline-safe by design (fallback to regex / heuristic when no API key
# is configured).
register_extractor(LLMClaimExtractor())
register_verifier(LLMSourceVerifier())

__all__ = [
    "ClaimExtractor",
    "ExtractedClaim",
    "SourceVerifier",
    "VerificationResult",
    "NoopExtractor",
    "NoopVerifier",
    "RegexExtractor",
    "HeuristicVerifier",
    "LLMClaimExtractor",
    "LLMSourceVerifier",
    "get_extractor",
    "get_verifier",
    "register_extractor",
    "register_verifier",
]
