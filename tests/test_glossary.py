"""W1.7: one glossary source for docs and report appendices."""

from __future__ import annotations

import re
from pathlib import Path

from impact_vision.impact.glossary import load_glossary, render_glossary_markdown, terms_used_in
from impact_vision.impact.pipeline import assess_file, sample_deck_path
from impact_vision.tools.impact.impact_report_tool import _to_html

REPO = Path(__file__).resolve().parents[1]


def test_docs_glossary_is_generated_from_yaml():
    assert (REPO / "docs" / "glossary.md").read_text(encoding="utf-8") == render_glossary_markdown()


def test_every_term_has_definition_and_match_phrases():
    for entry in load_glossary():
        assert entry["definition"].strip() and entry["match"], entry["term"]


def test_terms_match_whole_words_only():
    assert [e["term"] for e in terms_used_in("Our SFDR Article 8 fund")] == ["SFDR (Article 6 / 8 / 9)"]
    assert terms_used_in("reconsideration of opimistic plans") == []


def test_report_appendix_follows_audience():
    bundle = assess_file(sample_deck_path("solar"))
    full = _to_html(bundle.report_data)
    assert 'id="sec-glossary"' in full
    assert "Greenwashing (impact-washing) risk" in full
    bundle.report_data["audience"] = "public"
    public = _to_html(bundle.report_data)
    defined = re.findall(r"<dt>(.*?)</dt>", public.split('id="sec-glossary"', 1)[1])
    assert "Greenwashing (impact-washing) risk" not in defined
    assert "Five Dimensions of Impact (5D)" in defined
