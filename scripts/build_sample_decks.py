"""Build the bundled sample pitch decks (PDF) from their Markdown sources.

Each ``## heading`` becomes one slide-style page. Run after editing a deck::

    python scripts/build_sample_decks.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

DECKS = Path(__file__).resolve().parents[1] / "data" / "sample_decks"
PAGE = pymupdf.paper_rect("a4-l")  # landscape, like a deck
MARGIN = 48


def _slides(markdown: str) -> list[tuple[str, str]]:
    title_match = re.search(r"^# (.+)$", markdown, re.M)
    title = title_match.group(1).strip() if title_match else "Pitch deck"
    note = re.search(r"^\*(.+)\*$", markdown, re.M)
    slides = [(title, note.group(1) if note else "")]
    for block in re.split(r"^## ", markdown, flags=re.M)[1:]:
        heading, _, body = block.partition("\n")
        slides.append((heading.strip(), " ".join(body.split())))
    return slides


# The built-in Helvetica only covers Latin-1; map typographic characters so the
# PDF text layer doesn't turn them into "?".
_ASCII = str.maketrans({"\u2014": " - ", "\u2013": "-", "\u2265": ">=", "\u2264": "<=",
                        "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2192": "->"})


def build(md_path: Path) -> Path:
    doc = pymupdf.open()
    for i, (heading, body) in enumerate(_slides(md_path.read_text(encoding="utf-8").translate(_ASCII))):
        page = doc.new_page(width=PAGE.width, height=PAGE.height)
        size = 30 if i == 0 else 24
        page.insert_textbox(
            pymupdf.Rect(MARGIN, MARGIN, PAGE.width - MARGIN, MARGIN + 90),
            heading, fontsize=size, fontname="helv", color=(0.05, 0.28, 0.63),
        )
        page.insert_textbox(
            pymupdf.Rect(MARGIN, MARGIN + 100, PAGE.width - MARGIN, PAGE.height - MARGIN),
            body, fontsize=14 if i else 12, fontname="helv", lineheight=1.35,
        )
    out = md_path.with_suffix(".pdf")
    doc.set_metadata({"title": _slides(md_path.read_text(encoding="utf-8"))[0][0],
                      "subject": "Fictional sample deck for the Impact Vision demo"})
    doc.save(out, garbage=4, deflate=True)
    doc.close()
    return out


if __name__ == "__main__":
    for md in sorted(DECKS.glob("*.md")):
        print("built", build(md))
