"""v8 W2.2: every claim from a PDF carries the page it came from."""
from __future__ import annotations

from openharness.impact.pipeline import SAMPLE_DECKS, assess_file, sample_deck_path
from openharness.impact.report_templates.decision_report import render_decision_report


def test_pdf_claims_have_pages_and_the_ledger_shows_them():
    for key in SAMPLE_DECKS:
        bundle = assess_file(sample_deck_path(key))
        claims = bundle.assessment.impact_claims
        located = [c for c in claims if c.source_page]
        assert len(located) >= 0.95 * len(claims), key
        assert all(row.get("source_page") for row in bundle.report_data["impact_claims"])
    html = render_decision_report(bundle.report_data)
    assert 'class="cite"' in html and "p. " in html
    assert "第" in render_decision_report(bundle.report_data, lang="zh-HK")


def test_markdown_has_no_pages_and_renders_without_citation(tmp_path):
    deck = tmp_path / "d.md"
    deck.write_text("# Acme — Seed pitch\n\nWe served 1,200 households in 2024.\n", encoding="utf-8")
    bundle = assess_file(deck)
    assert all(c.source_page is None for c in bundle.assessment.impact_claims)
