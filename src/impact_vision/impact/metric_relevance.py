"""Rank IRIS+ metric suggestions by relevance to the company (v8 W0.6).

Every "report these metrics" suggestion used to take ``sorted(ids)[:n]``, i.e.
the alphabetically first IDs. An edtech was told to report "Racial Equity
Negative Screen" and a solar company "Adaptation Needs Assessment". This
module ranks candidates instead:

1. in the company's sector core set,
2. tagged to one of the company's impact themes,
3. specific to few SDGs (cross-cutting metrics such as "Client Individuals:
   Total", tagged to six or more goals, rank last),
4. wording that overlaps the company's own document.

Ties fall back to the ID so output is stable.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

_STOP = {
    "total", "number", "percentage", "rate", "value", "amount", "of", "the", "and", "or", "for",
    "by", "to", "in", "on", "with", "a", "an", "individuals", "client", "clients", "policy",
}


_MAX_THEMES_FOR_MATCH = 6


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower()) if w not in _STOP}


def rank_metrics(
    candidates: Iterable[str],
    company: Any = None,
    store: Any = None,
    *,
    goal: int | None = None,
    limit: int | None = None,
    relevant_only: bool = False,
) -> list[str]:
    """Return *candidates* ordered most-relevant first (optionally the top *limit*).

    ``relevant_only`` drops candidates with no tie to this company (not in its
    sector core set, not tagged to its themes, fewer than two words in common
    with its document) — for open-ended lists such as a dimension's whole
    reference set, where "most relevant of 400" can still be irrelevant.
    """
    ids = [c for c in dict.fromkeys(candidates) if c]
    if not ids:
        return []
    if store is None:
        from impact_vision.impact.database import get_metric_store

        store = get_metric_store()

    core: set[str] = set()
    themes: list[str] = []
    doc_words: set[str] = set()
    if company is not None:
        from impact_vision.impact.gap_analysis import core_set_for_sector
        from impact_vision.impact.text_sections import company_text

        core, _ = core_set_for_sector(getattr(company, "sector", "") or "")
        themes = [t.lower() for t in getattr(company, "impact_themes", []) or []]
        doc_words = _words(f"{company_text(company)} {' '.join(themes)}")

    tied: set[str] = set()

    def score(metric_id: str) -> tuple[float, str]:
        metric = store.get(metric_id) if store is not None else None
        value = 0.0
        if metric_id in core:
            value += 4
            tied.add(metric_id)
        if metric is not None:
            metric_themes = {t.lower() for t in metric.impact_themes}
            # A metric tagged to most themes (e.g. "Adaptation Needs Assessment",
            # 27 of them) matches every company; it's generic, not relevant.
            theme_specific = 0 < len(metric_themes) <= _MAX_THEMES_FOR_MATCH
            if themes and theme_specific and any(
                    t in metric_themes or any(t in m or m in t for m in metric_themes) for t in themes):
                value += 3
                tied.add(metric_id)
            if len(_words(metric.name) & doc_words) >= 2:
                tied.add(metric_id)
            goals = len(metric.sdg_goals)
            if goal is not None and goal in metric.sdg_goals:
                value += 1
            if goals and goals <= 3:
                value += 2
            elif goals and goals <= 5:
                value += 1
            elif goals >= 6:
                value -= 2
            value += min(2, len(_words(metric.name) & doc_words))
        return (-value, metric_id)

    ranked = sorted(ids, key=score)
    if relevant_only:
        ranked = [m for m in ranked if m in tied]
    return ranked[:limit] if limit else ranked


def metric_label(metric_id: str, store: Any = None) -> str:
    if store is None:
        from impact_vision.impact.database import get_metric_store

        store = get_metric_store()
    metric = store.get(metric_id) if store is not None else None
    return f"{metric.name} ({metric_id})" if metric is not None else metric_id


__all__ = ["metric_label", "rank_metrics"]
