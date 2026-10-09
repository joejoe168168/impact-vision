"""Localise generated report sentences into zh-HK / zh-CN (roadmap v8 W3.7).

The engine writes its findings in English. ``data/i18n/phrasebook.yaml``
(built by ``scripts/build_phrasebook.py``) maps each generated sentence
pattern to a Chinese template, so a Chinese report can be sent unedited.

Only generated text is translated. Company claims and quotes are evidence and
stay verbatim; IRIS+ metric names stay in English. Text no pattern matches
passes through unchanged, so a new English sentence never breaks a report:
it just shows in English until the phrasebook covers it.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from impact_vision.impact._paths import data_path

LANGS = ("zh-HK", "zh-CN")
_SLOT = re.compile(r"\{(\w+)(?::(\w+))?\}")
_VERIFIED = {"zh-HK": "，已核實", "zh-CN": "，已核实"}


@lru_cache(maxsize=1)
def _book() -> dict[str, Any]:
    path = data_path("i18n/phrasebook.yaml")
    if not path.exists():
        return {"patterns": [], "exact": {}, "fragments": []}
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    patterns = [(re.compile(p["en"]), p) for p in doc.get("patterns") or []]
    exact = {k.lower(): v for k, v in (doc.get("exact") or {}).items()}
    fragments = [(re.compile(p["en"]), p) for p in doc.get("fragments") or []]
    return {"patterns": patterns, "exact": exact, "fragments": fragments}


def _word(text: str, lang: str) -> str:
    """One noun or label: stakeholder table, then the exact table."""
    from impact_vision.impact.report_templates.design.strings import STAKEHOLDERS_ZH_CN, STAKEHOLDERS_ZH_HK

    table = {"zh-HK": STAKEHOLDERS_ZH_HK, "zh-CN": STAKEHOLDERS_ZH_CN}[lang]
    if text in table:
        return table[text]
    hit = _book()["exact"].get(text.strip().lower())
    return hit[lang] if hit else text


def _fill(kind: str | None, value: str, lang: str) -> str:
    if kind is None:
        return value
    if kind == "verified":
        return _VERIFIED[lang] if value else ""
    if kind == "sector":
        from impact_vision.impact.report_templates.design.strings import SECTOR_NAMES

        return SECTOR_NAMES.get(lang, {}).get(value.lower(), SECTOR_NAMES.get(lang, {}).get(value, value))
    if kind == "gwc":
        from impact_vision.impact.report_templates.design.strings import translator

        out = translator(lang)(f"gwc_{value}")
        return value if out == f"gwc_{value}" else out
    if kind == "note":
        rest = value.strip().lstrip("·").strip()
        if not rest:
            return ""
        for rx, entry in _book()["fragments"]:
            rest = rx.sub(lambda m, e=entry: _SLOT.sub(lambda s: m.groupdict().get(s.group(1)) or "", e[lang]), rest)
        return ("" if rest.startswith("（") else " · ") + rest
    return _word(value, lang)


def localize(text: str, lang: str) -> str:
    """Translate one generated sentence; unknown text comes back unchanged."""
    if lang not in LANGS or not text:
        return text
    book = _book()
    hit = book["exact"].get(text.strip().lower())
    if hit:
        return hit[lang]
    for rx, entry in book["patterns"]:
        m = rx.match(text.strip())
        if m:
            groups = m.groupdict()
            return _SLOT.sub(lambda s: _fill(s.group(2), groups.get(s.group(1)) or "", lang), entry[lang])
    return text


def localize_list(items: list[str], lang: str) -> list[str]:
    return [localize(x, lang) for x in items]


__all__ = ["LANGS", "localize", "localize_list"]
