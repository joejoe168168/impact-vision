"""Split a pitch deck / memo into role sections (v8 W0.5).

Scoring used to read only the first 1,000 characters of a document. That hid
the evidence and risk sections, and it read the *problem statement* ("kerosene
causes indoor air pollution") as the company's own adverse impact. Scorers now
read :func:`scoring_text`: the whole document minus the sections that describe
the world rather than the company (problem, market, competition, team, ask).

Sections are found from headings: markdown ``#`` lines, short title-case or
upper-case lines, and "Label:" lines. A document with no recognisable headings
is used whole.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Section role by heading keyword (first match wins, checked in order).
_ROLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("risk", ("risk", "what could go wrong", "mitigation", "safeguard", "negative impact", "do no harm")),
    ("evidence", ("evidence", "results", "impact to date", "traction", "evaluation", "outcomes",
                  "verification", "proof", "track record", "data")),
    ("problem", ("problem", "challenge", "the need", "context", "why now", "status quo", "pain")),
    ("market", ("market", "opportunity size", "tam", "competition", "competitor", "landscape")),
    ("governance", ("governance", "policy", "policies", "oversight")),
    ("team", ("team", "founder", "leadership", "advisor", "board")),
    ("ask", ("the ask", "funding", "use of funds", "investment ask", "raise", "financials", "terms")),
    ("solution", ("solution", "product", "what we do", "business model", "how it works", "approach",
                  "model", "theory of change", "targets", "plan")),
)
# Roles that describe the world, not the company: excluded from scoring text.
CONTEXT_ROLES = frozenset({"problem", "market", "team", "ask"})

_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_LABEL_LINE = re.compile(r"^\s*([A-Z][A-Za-z &/'’-]{2,40}):\s*$")


@dataclass
class Section:
    heading: str
    role: str
    text: str


def _role_for(heading: str) -> str:
    lowered = heading.lower()
    for role, keywords in _ROLES:
        if any(re.search(r"\b" + re.escape(k), lowered) for k in keywords):
            return role
    return "other"


def _heading(line: str, *, after_blank: bool) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 60:
        return None
    match = _MD_HEADING.match(line)
    if match:
        return match.group(1).strip()
    match = _LABEL_LINE.match(line)
    if match:
        return match.group(1).strip()
    words = stripped.split()
    if (
        after_blank
        and 1 <= len(words) <= 6
        and stripped[0].isupper()
        and not stripped.endswith((".", ",", ";", ":", "!", "?"))
        and not any(c.isdigit() for c in stripped)
    ):
        return stripped
    return None


def split_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    heading, buffer = "", []
    previous_blank = True
    for line in (text or "").splitlines():
        found = _heading(line, after_blank=previous_blank)
        previous_blank = not line.strip()
        if found is not None:
            if buffer or heading:
                sections.append(Section(heading, _role_for(heading) if heading else "intro", "\n".join(buffer)))
            heading, buffer = found, []
        else:
            buffer.append(line)
    sections.append(Section(heading, _role_for(heading) if heading else "intro", "\n".join(buffer)))
    return [s for s in sections if s.text.strip() or s.heading]


def scoring_text(text: str) -> str:
    """The document minus problem / market / team / ask sections.

    Falls back to the whole text when headings can't be found or when the
    filter would remove almost everything.
    """
    sections = split_sections(text)
    if len(sections) <= 1:
        return text or ""
    kept = [f"{s.heading}\n{s.text}" if s.heading else s.text for s in sections if s.role not in CONTEXT_ROLES]
    result = "\n".join(kept).strip()
    return result if len(result) >= 0.25 * len((text or "").strip()) else (text or "")


def company_text(company: object) -> str:
    """What the scorers read: the sectioned document when known, else the description."""
    return getattr(company, "assessment_text", "") or getattr(company, "description", "") or ""


__all__ = ["CONTEXT_ROLES", "Section", "company_text", "scoring_text", "split_sections"]
