"""Is a matched phrase asserted, or denied / only planned?

Evidence cues ("control group", "audited", "client protection policy") used to
count wherever they appeared, so "we have no control group yet" read as a
controlled evaluation and "accounts have not been audited" lowered verification
risk. :func:`asserted` looks at the clause around one match and says whether
the company states the thing as a present fact.

It is a clause-level rule, not a parser: a negator or a plan marker shortly
before the match (in the same clause), or a "has not been …" shortly after it,
makes the match unasserted. When unsure it keeps the match, so a positive
statement is never dropped because of a negation elsewhere in the sentence.
"""
from __future__ import annotations

import re
from collections.abc import Iterator

# How far to look, in characters. A clause is rarely longer than this.
_BEFORE = 50
_AFTER = 60

# Clause breaks: the negator must sit in the same clause as the match. A comma
# only breaks the clause when a conjunction follows ("no debt, and an RCT
# showed …"); "no RCT, control group or baseline" stays one clause.
_CLAUSE_BREAK = re.compile(
    r"[;:.!?()\[\]—–。；：！？（），、]"
    r"|,\s+(?:and|but|while|whereas|which|who|so|yet|although|though)\b"
    r"|\b(?:but|however|although|though|whereas)\b"
    r"|\band\s+(?=(?:our|we|the|its|it|they|this|these|all|an?)\b)"
    r"|(?:但是|但|然而|不過|不过)",
    re.IGNORECASE,
)

_NEGATED_BEFORE = re.compile(
    r"\b(?:no(?!\s+(?:fewer|less|later)\b)|not(?!\s+only\b)|never|without|neither|nor|lacks?|lacking|lacked|"
    r"absence\s+of|yet\s+to|unable\s+to|cannot|can't|won't|isn't|aren't|wasn't|weren't|don't|doesn't|"
    r"didn't|haven't|hasn't|hadn't)\b"
    # Chinese negators bind tightly: only when they sit just before the match.
    r"|(?:沒有|没有|尚未|還未|还未|並無|并无|未有|未曾|未經|未经|缺乏|無|无|未|不)[^，。、]{0,6}$",
    re.IGNORECASE,
)
# Plans are intent, not evidence: "we plan to run an RCT", "will be audited".
_PLANNED_BEFORE = re.compile(
    r"\b(?:plan(?:s|ned|ning)?\s+to|intend(?:s|ed)?\s+to|aim(?:s|ed|ing)?\s+to|hop(?:e|es|ing)\s+to|"
    r"expect(?:s|ed)?\s+to|seek(?:s|ing)?\s+to|going\s+to|will|would|shall|"
    r"(?:is|are)\s+(?:planned|scheduled|being\s+designed)|pending|upcoming)\b"
    r"|(?:計劃|计划|將會|将会|打算|預計|预计)[^，。、]{0,8}$",
    re.IGNORECASE,
)
# "… control group has not yet been established", "… audit is pending". Narrow on
# purpose: "the control group did not receive the product" describes a real study.
_NEGATED_AFTER = re.compile(
    r"^\W{0,3}(?:\w+\W+){0,3}?(?:"
    r"(?:has|have|had|is|are|was|were)\s+(?:not|never|yet\s+to)\s+(?:yet\s+)?(?:be(?:en)?\s+)?"
    r"(?:established|set\s+up|completed?|done|conducted|carried\s+out|available|in\s+place|started|begun|"
    r"performed|undertaken|obtained|received|issued|finali[sz]ed|commissioned|recruited|formed)\b"
    r"|(?:is|are|remains?)\s+(?:pending|planned|outstanding|under\s+development)\b)"
    r"|^.{0,4}(?:尚未|還未|还未|仍未)",
    re.IGNORECASE,
)


def _clause_before(text: str, start: int) -> str:
    window = text[max(0, start - _BEFORE):start]
    last = None
    for last in _CLAUSE_BREAK.finditer(window):
        pass
    return window[last.end():] if last else window


def _clause_after(text: str, end: int) -> str:
    window = text[end:end + _AFTER]
    brk = _CLAUSE_BREAK.search(window)
    return window[:brk.start()] if brk else window


def asserted(text: str, start: int, end: int) -> bool:
    """True when ``text[start:end]`` is stated as a present fact (not denied, not merely planned)."""
    before = _clause_before(text, start)
    if _NEGATED_BEFORE.search(before) or _PLANNED_BEFORE.search(before):
        return False
    return not _NEGATED_AFTER.search(_clause_after(text, end))


def asserted_matches(pattern: re.Pattern[str], text: str) -> Iterator[re.Match[str]]:
    """Matches of *pattern* in *text* that are asserted."""
    for m in pattern.finditer(text):
        if asserted(text, m.start(), m.end()):
            yield m


def asserts(pattern: re.Pattern[str], text: str) -> bool:
    """True when *pattern* occurs at least once as an asserted fact."""
    return next(asserted_matches(pattern, text), None) is not None


def asserts_phrase(phrase: str, text: str, *, word_boundary: bool = False) -> bool:
    """Like :func:`asserts` for a literal phrase (case-insensitive)."""
    body = re.escape(phrase)
    pattern = re.compile(rf"\b{body}\b" if word_boundary else body, re.IGNORECASE)
    return asserts(pattern, text)


__all__ = ["asserted", "asserted_matches", "asserts", "asserts_phrase"]
