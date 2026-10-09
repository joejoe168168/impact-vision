"""Plain-language glossary (v7 W1.7).

``data/glossary.yaml`` is the single source for ``docs/glossary.md``
(``scripts/build_glossary.py``) and the "Terms used in this report" appendix
of the HTML impact report.
"""

from __future__ import annotations

import html
import re
from functools import lru_cache

import yaml

from impact_vision.impact._paths import data_path


@lru_cache(maxsize=1)
def load_glossary() -> list[dict]:
    path = data_path("glossary.yaml")
    if not path.is_file():
        return []
    with open(path, encoding="utf-8") as f:
        return list((yaml.safe_load(f) or {}).get("terms", []))


def terms_used_in(text: str) -> list[dict]:
    """Glossary entries whose match phrases appear in *text* (whole words)."""
    lowered = text.lower()
    found = []
    for entry in load_glossary():
        for phrase in entry.get("match", []):
            if re.search(rf"(?<![\w-]){re.escape(phrase.lower())}(?![\w-])", lowered):
                found.append(entry)
                break
    return found


def render_glossary_markdown() -> str:
    """The full glossary as Markdown, grouped by category."""
    lines = [
        "# Glossary",
        "",
        "Plain-language definitions of the terms Impact Vision uses in its reports.",
        "Generated from `data/glossary.yaml` by `scripts/build_glossary.py` — edit the",
        "YAML, not this file.",
        "",
    ]
    categories: dict[str, list[dict]] = {}
    for entry in load_glossary():
        categories.setdefault(entry.get("category", "Other"), []).append(entry)
    for category, entries in categories.items():
        lines += [f"## {category}", ""]
        for entry in entries:
            lines += [f"**{entry['term']}** — {' '.join(entry['definition'].split())}", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_glossary_html(text: str) -> str:
    """A collapsible appendix of the glossary terms that appear in *text*."""
    entries = terms_used_in(text)
    if not entries:
        return ""
    items = "".join(
        f"<dt>{html.escape(e['term'])}</dt><dd>{html.escape(' '.join(e['definition'].split()))}</dd>"
        for e in entries
    )
    return (
        '<h2 id="sec-glossary">Terms used in this report</h2>'
        '<details class="glossary"><summary>Show definitions '
        f"({len(entries)} terms)</summary><dl>{items}</dl></details>"
    )


__all__ = ["load_glossary", "render_glossary_html", "render_glossary_markdown", "terms_used_in"]
