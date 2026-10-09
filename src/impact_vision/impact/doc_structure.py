"""Document structure the sentence extractors can't see (roadmap v8 W2.1).

Pitch decks put their best numbers in tables. A sentence-based extractor sees
``| Patients treated | 18,000 | 31,000 |`` as noise, so :func:`tables_to_sentences`
rewrites each table row as a sentence that says what the row says::

    | Metric           | 2023   | 2024   |
    | Patients treated | 18,000 | 31,000 |
    →  31,000 patients treated in 2024 (18,000 in 2023).

The latest year with a value leads, earlier years follow in brackets, and a
row whose label starts with a count noun ("Patients treated", "Farmers
reached") puts the number first, the way the claim extractors expect it.
"""
from __future__ import annotations

import re

_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_YEAR = re.compile(r"^(?:FY\s?)?((?:19|20)\d{2})\b", re.IGNORECASE)
_NUMBER = re.compile(r"^[~≈<>]?\s*[$€£]?\s*\d[\d,]*(?:\.\d+)?\s*(?:%|[kKmM]|million|bn)?\b")
_COUNT_NOUNS = ("patients", "students", "households", "farmers", "smallholders", "customers", "clients", "users",
                "employees", "staff", "workers", "people", "individuals", "families", "beneficiaries", "learners",
                "borrowers", "jobs", "loans", "trees", "tenants", "residents", "children", "women", "girls")


def _cells(line: str) -> list[str] | None:
    m = _ROW.match(line)
    return [c.strip() for c in m.group(1).split("|")] if m else None


def _row_sentence(label: str, header: list[str], values: list[str]) -> str:
    label = re.sub(r"[*_`]", "", label).strip().rstrip(":")
    years = [(_YEAR.match(h).group(1) if _YEAR.match(h) else "") for h in header]  # type: ignore[union-attr]
    pairs = [(y, v) for y, v in zip(years, values) if v and _NUMBER.match(v)]
    if not label or not pairs:
        return ""
    dated = [(y, v) for y, v in pairs if y]
    lead_noun = label.split()[0].lower() if label.split() else ""
    if dated:
        year, value = dated[-1]
        rest = ", ".join(f"{v} in {y}" for y, v in reversed(dated[:-1]))
        body = (f"{value} {label[0].lower() + label[1:]} in {year}" if lead_noun in _COUNT_NOUNS
                else f"{label}: {value} in {year}")
        return body + (f" ({rest})" if rest else "") + "."
    cols = [f"{h}: {v}" if h else v for h, v in zip(header, values) if v]
    value = pairs[0][1]
    if lead_noun in _COUNT_NOUNS and len(cols) == 1:
        return f"{value} {label[0].lower() + label[1:]}."
    return f"{label}: " + "; ".join(cols) + "."


def tables_to_sentences(text: str) -> str:
    """Replace pipe tables with one sentence per data row; other text is unchanged."""
    if "|" not in (text or ""):
        return text or ""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        header = _cells(lines[i])
        if header and i + 1 < len(lines) and _SEPARATOR.match(lines[i + 1]):
            j = i + 2
            sentences = []
            while j < len(lines) and (row := _cells(lines[j])) is not None:
                sentence = _row_sentence(row[0], header[1:], row[1:])
                if sentence:
                    sentences.append(f"- {sentence}")
                j += 1
            out.extend(sentences or lines[i:j])
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def prepare_text(text: str) -> str:
    """Everything a document needs before sentence extraction."""
    return tables_to_sentences(text)


__all__ = ["prepare_text", "tables_to_sentences"]
