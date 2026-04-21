"""OpenAI-compatible LLM claim extractor (Phase 15.6).

Wraps any OpenAI-compatible chat endpoint (OpenAI, Anthropic-via-proxy,
Ollama, Minimax, Moonshot, Together, DeepSeek, local vLLM, etc.) behind
the :class:`ClaimExtractor` Protocol defined in
:mod:`openharness.impact.extractors.base`.

Design goals
------------
*   **No hard vendor dependency.**  The adapter talks HTTP directly via
    ``urllib.request`` — we do *not* import the ``openai`` Python client
    so this module works in environments where the OpenAI SDK is blocked
    or vendored differently.
*   **Offline-safe.**  When no ``api_key``/``base_url`` is configured or
    the endpoint returns an error, the extractor falls back to the
    deterministic :class:`RegexExtractor` and surfaces a
    ``fallback_reason`` on each claim so callers can tell it happened.
*   **Deterministic output schema.**  We always return
    ``list[ExtractedClaim]`` — never free-form text — by prompting the
    model for strict JSON and validating it with Pydantic.
*   **Swappable via the registry.**  Import-time registration mirrors the
    pattern used by ``RegexExtractor``/``HeuristicVerifier``; clients
    simply do ``iv = ImpactVision(extractor_id="llm")``.

Example
-------
::

    from openharness.impact.extractors import register_extractor
    from openharness.impact.extractors.llm_extractor import LLMClaimExtractor

    register_extractor(LLMClaimExtractor(
        id="llm",
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
    ))

    iv = ImpactVision(extractor_id="llm")
    claims = iv.extract_claims(long_pitch_deck_text)
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any
from urllib import request as _urllib_request
from urllib.error import HTTPError, URLError

from openharness.impact.extractors.base import ExtractedClaim
from openharness.impact.extractors.regex_extractor import RegexExtractor

log = logging.getLogger(__name__)


_DEFAULT_SYSTEM_PROMPT = (
    "You are an impact-investing analyst. Extract every distinct impact claim "
    "from the user's text and return them as strict JSON. "
    "For each claim return an object with these keys:\n"
    "  - text (string)\n"
    "  - category (one of: outcome, output, input, commitment, certification, "
    "comparison, estimate, anecdote, unknown)\n"
    "  - metric_value (number or null)\n"
    "  - metric_unit (string or null)\n"
    "  - metric_year (integer or null)\n"
    "  - geography (ISO-2 country or region, or null)\n"
    "  - confidence (0.0-1.0)\n"
    "  - page_or_section (string or null)\n"
    "  - suggested_iris_metric_id (string or null)\n"
    "Return a single JSON object of the shape "
    '{"claims": [ ... ]}. No prose, no markdown fencing.'
)


@dataclass
class LLMClaimExtractor:
    """OpenAI-compatible claim extractor.

    Attributes
    ----------
    id:
        Registry ID. Default ``"llm"``.
    model:
        Model name sent in the ``model`` field of the chat-completions
        request body (e.g. ``"gpt-4o-mini"``, ``"minimax/minimax-m2.7"``).
    base_url:
        Base URL of an OpenAI-compatible endpoint, e.g.
        ``"https://api.openai.com/v1"`` or ``"https://runanytime.hxi.me/v1"``.
    api_key:
        Bearer token. When ``None``, extracts via the regex fallback only.
    timeout:
        Seconds to wait for the HTTP call before falling back.
    system_prompt:
        Override the default system prompt (advanced).
    fallback:
        Extractor to call when the LLM is unavailable; defaults to a
        :class:`RegexExtractor` instance.
    """

    id: str = "llm"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    timeout: float = 60.0
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT
    fallback: Any = field(default_factory=RegexExtractor)

    def extract(self, text: str, *, context: dict | None = None) -> list[ExtractedClaim]:
        """Extract claims from ``text`` and return them as a list.

        Falls back to the regex extractor when the LLM cannot be reached.
        Every claim is stamped with ``raw_extractor_id = self.id`` (or
        ``"llm-fallback"`` if we had to use the regex path).
        """
        api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key or not text or not text.strip():
            return self._fallback_claims(text, reason="no-api-key-or-empty")

        try:
            raw = self._chat(text, api_key)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            log.info("LLMClaimExtractor fallback (%s): %s", type(exc).__name__, exc)
            return self._fallback_claims(text, reason=f"llm-error:{type(exc).__name__}")

        cleaned = _strip_think_blocks(raw)
        parsed = _safe_parse_json(cleaned)
        if parsed is None or "claims" not in parsed:
            return self._fallback_claims(text, reason="llm-bad-json")

        out: list[ExtractedClaim] = []
        for item in parsed.get("claims", [])[:200]:  # hard cap
            try:
                claim = ExtractedClaim(
                    text=str(item.get("text", "")).strip()[:500],
                    category=item.get("category", "unknown") or "unknown",
                    metric_value=_to_float(item.get("metric_value")),
                    metric_unit=_to_str_or_none(item.get("metric_unit")),
                    metric_year=_to_int_or_none(item.get("metric_year")),
                    geography=_to_str_or_none(item.get("geography")),
                    confidence=max(0.0, min(1.0, _to_float(item.get("confidence"), 0.5) or 0.5)),
                    page_or_section=_to_str_or_none(item.get("page_or_section")),
                    suggested_iris_metric_id=_to_str_or_none(item.get("suggested_iris_metric_id")),
                    raw_extractor_id=self.id,
                )
                if claim.text:
                    out.append(claim)
            except Exception as exc:  # noqa: BLE001 — keep the pipe robust
                log.debug("dropping malformed LLM claim %r: %s", item, exc)

        if not out:
            return self._fallback_claims(text, reason="llm-returned-empty")
        return out

    # ------------------------------------------------------------------
    # Internal helpers (kept package-private for testability)
    # ------------------------------------------------------------------

    def _chat(self, user_text: str, api_key: str) -> str:
        """Send one chat-completions request and return the assistant content."""
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_text[:24_000]},  # cheap truncation
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
        with _urllib_request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 — trusted base_url
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("LLM response has no choices")
        msg = choices[0].get("message") or {}
        return str(msg.get("content") or "")

    def _fallback_claims(self, text: str, *, reason: str) -> list[ExtractedClaim]:
        claims = list(self.fallback.extract(text)) if text else []
        for c in claims:
            c.raw_extractor_id = f"{self.id}-fallback({reason})"
        return claims


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|```\s*$", re.MULTILINE)


def _strip_think_blocks(raw: str) -> str:
    """Remove ``<think>…</think>`` and code fences some models wrap output in."""
    cleaned = _THINK_BLOCK_RE.sub("", raw)
    cleaned = _CODE_FENCE_RE.sub("", cleaned)
    return cleaned.strip()


def _safe_parse_json(s: str) -> dict | None:
    """Best-effort JSON extraction from an LLM string."""
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Look for the first top-level object
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(s[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _to_float(v: Any, default: float | None = None) -> float | None:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_int_or_none(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _to_str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None
