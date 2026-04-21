"""URL-grounded LLM source verifier (Phase 15.6).

Implements the :class:`SourceVerifier` protocol on top of an
OpenAI-compatible chat endpoint, combined with a pluggable URL fetcher
that retrieves *public* filings (GIIN impact reports, CDP responses,
SEC 10-Ks, SFDR annexes, sustainability reports, company press pages).

The verifier is intentionally conservative:

* Offline-safe: when the LLM or fetcher is unavailable it falls back to
  :class:`HeuristicVerifier` and marks the reason.
* Deterministic schema: always returns a :class:`VerificationResult`
  with at most one supporting / contradicting source.
* Never invents URLs: only sources the caller (or the configured
  ``known_sources`` seed list) has pre-registered are ever cited.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib import request as _urllib_request
from urllib.error import HTTPError, URLError

from openharness.impact.extractors.base import (
    ExtractedClaim,
    VerificationResult,
)
from openharness.impact.extractors.heuristic_verifier import HeuristicVerifier

log = logging.getLogger(__name__)


_DEFAULT_SYSTEM_PROMPT = (
    "You are an impact verification analyst. Given one claim and the text "
    "extracted from a public source, decide whether the source CORROBORATES, "
    "CONTRADICTS or is NEUTRAL to the claim. Return strict JSON of the form "
    '{"verdict": "corroborates|contradicts|neutral", "confidence": 0..1, '
    '"reason": "one-sentence justification"}. No prose.'
)


UrlFetcher = Callable[[str, float], str]
"""A callable ``fetcher(url, timeout_seconds) -> raw_html_or_text``."""


def _default_fetcher(url: str, timeout: float = 15.0) -> str:
    """Plain-text GET with a 1 MB cap and a UA header."""
    req = _urllib_request.Request(
        url, headers={"User-Agent": "impact-vision/0.14 (verifier)"}
    )
    with _urllib_request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        body = resp.read(1_000_000)
    return body.decode("utf-8", errors="replace")


@dataclass
class LLMSourceVerifier:
    """Verifies claims against public sources via an OpenAI-compatible LLM."""

    id: str = "llm"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    timeout: float = 45.0
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT
    known_sources: list[str] = field(default_factory=list)
    """Seed list of public-filing URLs to try for every claim."""
    fetcher: UrlFetcher = field(default=_default_fetcher)
    fallback: Any = field(default_factory=HeuristicVerifier)

    def verify(self, claim: ExtractedClaim, *, context: dict | None = None) -> VerificationResult:
        """Verify one claim against the first reachable source."""
        api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        candidate_urls: list[str] = list(self.known_sources)
        if context and isinstance(context.get("sources"), list):
            candidate_urls.extend(str(u) for u in context["sources"][:10])

        if not api_key or not candidate_urls:
            return self._fallback(claim, reason="no-api-key-or-sources")

        for url in candidate_urls[:5]:  # cap per-claim work
            try:
                source_text = self.fetcher(url, self.timeout)
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                log.debug("fetcher skipped %s: %s", url, exc)
                continue
            if not source_text:
                continue
            try:
                verdict = self._ask_llm(claim.text, source_text, api_key)
            except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                log.info("LLMSourceVerifier LLM error for %s: %s", url, exc)
                continue
            if verdict is None:
                continue
            v = str(verdict.get("verdict", "neutral")).lower()
            conf = max(0.0, min(1.0, float(verdict.get("confidence", 0.0) or 0.0)))
            reason = str(verdict.get("reason", ""))[:400]
            if v == "corroborates":
                return VerificationResult(
                    claim_text=claim.text, verified=True, confidence=conf,
                    supporting_sources=[url], contradicting_sources=[],
                    reason=reason, verifier_id=self.id,
                )
            if v == "contradicts":
                return VerificationResult(
                    claim_text=claim.text, verified=False, confidence=conf,
                    supporting_sources=[], contradicting_sources=[url],
                    reason=reason, verifier_id=self.id,
                )

        return self._fallback(claim, reason="no-supporting-source-found")

    # ------------------------------------------------------------------

    def _ask_llm(self, claim_text: str, source_text: str, api_key: str) -> dict | None:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": (
                    f"CLAIM:\n{claim_text}\n\n"
                    f"SOURCE TEXT (truncated):\n{source_text[:20_000]}"
                )},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        req = _urllib_request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "impact-vision/0.14",
            },
            method="POST",
        )
        with _urllib_request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        choices = data.get("choices") or []
        if not choices:
            return None
        msg = choices[0].get("message") or {}
        content = str(msg.get("content") or "")
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def _fallback(self, claim: ExtractedClaim, *, reason: str) -> VerificationResult:
        r = self.fallback.verify(claim)
        r.verifier_id = f"{self.id}-fallback({reason})"
        return r
