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

# Register the bundled deterministic providers so they're discoverable by id.
register_extractor(RegexExtractor())
register_verifier(HeuristicVerifier())

__all__ = [
    "ClaimExtractor",
    "ExtractedClaim",
    "SourceVerifier",
    "VerificationResult",
    "NoopExtractor",
    "NoopVerifier",
    "RegexExtractor",
    "HeuristicVerifier",
    "get_extractor",
    "get_verifier",
    "register_extractor",
    "register_verifier",
]
