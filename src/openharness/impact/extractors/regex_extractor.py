"""Regex-based claim extractor — zero-dependency reference implementation.

Useful as a default for environments that can't run an LLM, and as a
deterministic baseline against which LLM extractors can be measured.

It surfaces three classes of claim:
  1. Quantified outcomes ("3,500 students enrolled in 2024")
  2. Forward commitments ("net-zero by 2030", "carbon neutral by 2040")
  3. Certifications ("B-Corp certified", "ISO 14001")

For richer extraction (causal claims, theory-of-change wording, IRIS+
metric mapping with semantic similarity), drop in an LLM-backed adapter
that satisfies the same `ClaimExtractor` protocol.
"""
from __future__ import annotations

import re

from openharness.impact.extractors.base import (
    ClaimCategory,
    ClaimExtractor,  # noqa: F401 — re-exported protocol for documentation / subclassing
    ExtractedClaim,
)


_NUMBER_UNIT = re.compile(
    r"""
    (?<![\d.,])
    (?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)
    \s*
    (?P<unit>%|million|billion|thousand|GWh|MWh|kWh|MW|tCO2e?|t\s?CO2e?|tonnes?|tons?|kg|
            hectares?|ha|jobs?|students?|patients?|farmers?|households?|smallholders?|
            customers?|clients?|users?|employees?|staff|workers?|people|individuals|
            families|trees|loans?|beneficiaries)
    (?![A-Za-z0-9])
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Evidence-quality signals. These upgrade a claim from "narrative" to evidence
# an IC can rely on; dropping them made well-evidenced pitches look unverified.
_EVIDENCE_SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("third_party_verified", re.compile(
        r"\b(?:independently|externally|third[\s-]party)[\s-](?:verified|validated|assured|certified)\b"
        r"|\bverified\s+by\s+(?:an?\s+)?[A-Z][\w&.-]+",
        re.IGNORECASE,
    )),
    ("audited", re.compile(
        r"\b[A-Z]{3,}[\s-]audited\b|\baudited\s+by\b|\b(?:third[\s-]party|independent|external)\s+"
        r"(?:\w+\s+){0,2}audits?\b|\bassurance\s+(?:statement|provider|engagement)\b",
        re.IGNORECASE,
    )),
    ("certified", re.compile(
        r"\b(?:B[-\s]?Corp|ISO\s?\d{4,5}|Fair[-\s]?Trade|Rainforest Alliance|FSC|MSC|RSPO|"
        r"LEED|BREEAM|GOTS|2X)\b[\w\s-]{0,15}\bcertifi(?:ed|cation)\b"
        r"|\bcertified\s+(?:by|under|to)\b",
        re.IGNORECASE,
    )),
    ("controlled_evaluation", re.compile(
        r"\brandomi[sz]ed\b|\bRCTs?\b|\bcontrol\s+group\b|\bcounterfactual\b|"
        r"\bquasi[\s-]experimental\b|\bdifference[\s-]in[\s-]differences?\b|"
        r"\bmatched\s+(?:control|comparison)\b",
        re.IGNORECASE,
    )),
    ("baseline_comparison", re.compile(
        r"\b(?:versus|vs\.?|compared\s+(?:to|with)|relative\s+to|from)\s+(?:our\s+|a\s+|the\s+)?"
        r"(?:\d{4}\s+)?baseline\b|\bbaseline\s*(?:\(|:|of)",
        re.IGNORECASE,
    )),
)

# Sentence boundaries: ., ! or ? followed by whitespace/end — never the point
# inside a decimal such as "1.8 GWh" — and line breaks (headings, list items;
# reflow wrapped PDF lines before extracting).
_SENTENCE_END = re.compile(r"(?<!\d)[.!?](?=\s|$)|(?<=\d)\.(?=\s|$)|\n")


_FORWARD_RE = re.compile(
    r"\b(?:we\s+)?(?:target|aim|plan|intend|commit(?:ted)?\s+to|over\s+the\s+next|by\s+20[3-9]\d)\b",
    re.IGNORECASE,
)


def evidence_signals(sentence: str) -> list[str]:
    """Return the evidence-quality signals present in *sentence*."""
    return [name for name, pattern in _EVIDENCE_SIGNALS if pattern.search(sentence)]


_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_COMMITMENT_RE = re.compile(
    r"\b(net[\s-]?zero|carbon[\s-]?neutral|fossil[\s-]?free|fully renewable|"
    r"100\s*%\s*renewable|100\s*%\s*recyclable|paris[\s-]?aligned|1\.5\s*°?C\s*aligned)\b"
    r".{0,40}?\b(by|until|before)\s+(?P<year>20\d{2})",
    re.IGNORECASE,
)
_CERTIFICATION_RE = re.compile(
    r"\b(B[-\s]?Corp(?:oration)?|ISO\s?\d{4,5}(?:[-:]\d{1,4})?|LEED\s?(?:Platinum|Gold|Silver)?|"
    r"Fair[-\s]?Trade|Rainforest Alliance|Cradle\s?to\s?Cradle|EU\s?Ecolabel|"
    r"GRESB|GIIRS|ENERGY\s?STAR|HQE|BREEAM|FSC|MSC|RSPO)\b",
    re.IGNORECASE,
)


def _extract_year(window: str) -> int | None:
    m = _YEAR_RE.search(window)
    return int(m.group()) if m else None


def _categorise_unit(unit: str) -> ClaimCategory:
    u = re.sub(r"\s+", "", unit.lower())
    if u in {"gwh", "mwh", "kwh", "mw", "tco2", "tco2e", "tons", "ton", "tonnes", "tonne", "kg",
             "hectares", "hectare", "ha", "trees"}:
        return "outcome"
    if u in {"jobs", "job", "students", "student", "patients", "patient", "farmers", "farmer",
             "households", "household", "smallholders", "smallholder", "customers", "customer",
             "clients", "client", "users", "user", "employees", "employee", "staff", "workers",
             "worker", "people", "individuals", "individual", "families", "family", "loans",
             "loan", "beneficiaries"}:
        return "outcome"
    if u == "%":
        return "comparison"
    return "output"


class RegexExtractor:
    """Concrete `ClaimExtractor` — fully deterministic, no external calls."""
    id = "regex"

    def extract(self, text: str, *, context: dict | None = None) -> list[ExtractedClaim]:
        if not text:
            return []
        claims: list[ExtractedClaim] = []
        seen: set[str] = set()

        for m in _NUMBER_UNIT.finditer(text):
            sentence = self._sentence_around(text, m.start())
            key = sentence.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                value = float(m.group("value").replace(",", ""))
            except ValueError:
                value = None
            unit = m.group("unit")
            signals = evidence_signals(sentence)
            claims.append(
                ExtractedClaim(
                    text=sentence,
                    category="commitment" if _FORWARD_RE.search(sentence) else _categorise_unit(unit),
                    metric_value=value,
                    metric_unit=unit,
                    metric_year=_extract_year(sentence),
                    confidence=0.7 if signals else 0.55,
                    evidence_signals=signals,
                    raw_extractor_id=self.id,
                )
            )

        for m in _COMMITMENT_RE.finditer(text):
            sentence = self._sentence_around(text, m.start())
            key = sentence.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            year = m.group("year")
            claims.append(
                ExtractedClaim(
                    text=sentence,
                    category="commitment",
                    metric_year=int(year) if year else None,
                    confidence=0.7,
                    evidence_signals=evidence_signals(sentence),
                    raw_extractor_id=self.id,
                )
            )

        for m in _CERTIFICATION_RE.finditer(text):
            sentence = self._sentence_around(text, m.start())
            key = sentence.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            claims.append(
                ExtractedClaim(
                    text=sentence,
                    category="certification",
                    confidence=0.75,
                    evidence_signals=evidence_signals(sentence) or ["certified"],
                    raw_extractor_id=self.id,
                )
            )

        # Sentences whose only claim is about *how* impact is evidenced
        # ("SEDEX-audited", "randomized pilot with a control group").
        for sentence in self._sentences(text):
            key = sentence.strip().lower()
            if key in seen:
                continue
            signals = evidence_signals(sentence)
            if not signals:
                continue
            seen.add(key)
            claims.append(
                ExtractedClaim(
                    text=sentence,
                    category="evaluation" if "controlled_evaluation" in signals else "verification",
                    metric_year=_extract_year(sentence),
                    confidence=0.7,
                    evidence_signals=signals,
                    raw_extractor_id=self.id,
                )
            )

        return claims

    @staticmethod
    def _sentences(text: str) -> list[str]:
        out: list[str] = []
        start = 0
        for m in _SENTENCE_END.finditer(text):
            out.append(text[start:m.end()].strip())
            start = m.end()
        if start < len(text):
            out.append(text[start:].strip())
        return [s for s in out if s]

    @staticmethod
    def _sentence_around(text: str, idx: int) -> str:
        """Return the sentence containing *idx* (decimal points are not boundaries)."""
        start = 0
        for m in _SENTENCE_END.finditer(text):
            if m.end() <= idx:
                start = m.end()
                continue
            return text[start:m.end()].strip()
        return text[start:].strip()
