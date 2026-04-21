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
    (?P<value>\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)
    \s*
    (?P<unit>%|million|billion|thousand|MWh|kWh|tCO2e?|tons?|kg|hectares?|jobs?|
            students?|patients?|farmers?|households?|smallholders?|customers?|users?|
            employees?|people|individuals|families|trees|loans?)
    """,
    re.IGNORECASE | re.VERBOSE,
)

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
    u = unit.lower()
    if u in {"mwh", "kwh", "tco2", "tco2e", "tons", "ton", "kg", "hectares", "hectare", "trees"}:
        return "outcome"
    if u in {"jobs", "job", "students", "student", "patients", "patient", "farmers", "farmer",
             "households", "household", "smallholders", "smallholder", "customers", "customer",
             "users", "user", "employees", "employee", "people", "individuals", "individual",
             "families", "family", "loans", "loan"}:
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
            claims.append(
                ExtractedClaim(
                    text=sentence,
                    category=_categorise_unit(unit),
                    metric_value=value,
                    metric_unit=unit,
                    metric_year=_extract_year(sentence),
                    confidence=0.55,
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
                    raw_extractor_id=self.id,
                )
            )

        return claims

    @staticmethod
    def _sentence_around(text: str, idx: int) -> str:
        start = max(0, idx - 200)
        end = min(len(text), idx + 200)
        window = text[start:end]
        # cut to sentence boundaries inside the window
        first_period = window.rfind(".", 0, idx - start)
        last_period = window.find(".", idx - start)
        s = first_period + 1 if first_period >= 0 else 0
        e = last_period + 1 if last_period >= 0 else len(window)
        return window[s:e].strip()
