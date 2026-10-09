"""Regenerate docs/glossary.md from data/glossary.yaml.

    python scripts/build_glossary.py
"""

from __future__ import annotations

from pathlib import Path

from impact_vision.impact.glossary import render_glossary_markdown

OUT = Path(__file__).resolve().parents[1] / "docs" / "glossary.md"

if __name__ == "__main__":
    OUT.write_text(render_glossary_markdown(), encoding="utf-8")
    print(f"wrote {OUT}")
