"""Exclusion screening on a company's own documents.

``data/exclusion_criteria.yaml`` lists activities most impact funds will not
finance (controversial weapons, fossil fuels, tobacco, UN Global Compact
violations, …). :func:`screen_exclusions` reads the text sentence by sentence
and sorts every keyword it finds into one of two kinds:

* **involvement** — the company says it does the thing ("we also operate a
  coal mining subsidiary"). A *mandatory* category with an involvement hit
  fails the screen.
* **mention** — the keyword appears, but the sentence denies it, guards
  against it or replaces it ("we do not finance coal mining", "anti-bribery
  training", "replacing kerosene and petroleum lamps", "forced labour risk in
  the supply chain: we audit suppliers"). A mention never fails the screen; it
  is listed as something to ask about.

Naming a harm is not committing it, and a deck that discusses its risks openly
must not be punished for that. When the sentence is ambiguous the hit is a
mention.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Iterable

import yaml

from impact_vision.impact._paths import data_path
from impact_vision.impact.negation import asserted

_SENTENCE = re.compile(r"(?<=[.!?。；;])\s+|\n+")


@lru_cache(maxsize=1)
def _config() -> dict[str, Any]:
    path = data_path("exclusion_criteria.yaml")
    doc: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    doc = doc or {}
    guards = [re.compile(p, re.IGNORECASE) for p in doc.get("guard_patterns") or []]
    return {"categories": doc.get("categories") or {}, "guards": guards}


def criteria() -> dict[str, dict[str, Any]]:
    """The exclusion categories (id → label, keywords, severity, …)."""
    categories: dict[str, dict[str, Any]] = _config()["categories"]
    return categories


def clear_cache() -> None:
    _config.cache_clear()


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    # "labor" also matches "labour"; a trailing plural is the same keyword.
    body = re.escape(keyword.lower()).replace("labor", "labou?r")
    return re.compile(rf"(?<![\w-]){body}s?(?![\w-])", re.IGNORECASE)


def screen_exclusions(text: str, *, severities: Iterable[str] = ("mandatory", "common", "watch")) -> dict[str, Any]:
    """Screen *text*. ``passed`` is False only for involvement in a mandatory category."""
    cfg = _config()
    wanted = set(severities)
    sentences = [s.strip(" -•*\t") for s in _SENTENCE.split(text or "") if s.strip()]
    hits: list[dict[str, Any]] = []
    for category_id, cat in cfg["categories"].items():
        severity = str(cat.get("severity", "common"))
        if severity not in wanted:
            continue
        found: dict[str, dict[str, Any]] = {}
        for keyword in cat.get("keywords") or []:
            pattern = _keyword_pattern(str(keyword))
            for sentence in sentences:
                for match in pattern.finditer(sentence):
                    guarded = any(g.search(sentence) for g in cfg["guards"])
                    # A bare heading ("Over-indebtedness;") names a topic; it states nothing.
                    states_something = len(sentence.split()) >= 4
                    involved = (cat.get("self_declared", True) and not guarded and states_something
                                and asserted(sentence, match.start(), match.end()))
                    kind = "involvement" if involved else "mention"
                    best = found.get("hit")
                    if best is None or (kind == "involvement" and best["kind"] == "mention"):
                        found["hit"] = {"keyword": str(keyword), "kind": kind,
                                        "sentence": sentence if len(sentence) <= 220 else sentence[:217] + "…"}
        if found:
            hits.append({"category": category_id, "label": cat.get("label", category_id), "severity": severity,
                         "sfdr_pai": cat.get("sfdr_pai", ""), "description": cat.get("description", ""),
                         **found["hit"]})
    failures = [h for h in hits if h["kind"] == "involvement" and h["severity"] == "mandatory"]
    order = {"mandatory": 0, "common": 1, "watch": 2}
    hits.sort(key=lambda h: (h["kind"] != "involvement", order.get(h["severity"], 3), h["label"]))
    return {
        "passed": not failures,
        "failures": failures,
        "questions": [h for h in hits if h not in failures],
        "hits": hits,
        "categories_screened": len([c for c in cfg["categories"].values()
                                    if str(c.get("severity", "common")) in wanted]),
    }


__all__ = ["clear_cache", "criteria", "screen_exclusions"]
