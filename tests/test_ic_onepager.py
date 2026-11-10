"""F3: the IC one-pager shows the same numbers as the impact report, on one A4 page."""

from __future__ import annotations

import pytest

from impact_vision.impact.pipeline import (
    SAMPLE_DECKS,
    assess_file,
    sample_deck_path,
    write_deliverables,
)
from impact_vision.impact.report_templates.decision_report import build_view
from impact_vision.impact.report_templates.onepager import build_onepager, render_ic_onepager


@pytest.fixture(scope="module")
def bundle():
    return assess_file(sample_deck_path(next(iter(SAMPLE_DECKS))))


@pytest.mark.parametrize("lang", ["en", "zh-HK"])
def test_same_p50_and_verdict_as_the_report(bundle, lang):
    view = build_view(bundle.report_data, audience="ic", lang=lang)
    page = build_onepager(bundle.report_data, lang)
    html = render_ic_onepager(bundle.report_data, lang)
    row = view["impact"]["rows"][0]
    assert page["outcomes"][0]["p50"] == row["p50"]
    assert f"<b>{row['p50']}</b>" in html
    assert view["verdict"]["label"] in html
    assert bundle.company.name in html


def test_content_is_capped_and_footer_carries_stamp_and_disclosure(bundle):
    page = build_onepager(bundle.report_data)
    assert len(page["reasons"]) <= 3 and len(page["conditions"]) <= 3
    assert page["negative"] and isinstance(page["negative"]["controlled"], bool)
    html = render_ic_onepager(bundle.report_data)
    assert page["stamp"] and page["stamp"] in html
    assert page["ai_disclosure"][:40] in html
    assert "size: A4" in html and html.count("class='page'") == 1
    assert ("A control is described" in html) or ("No control is described" in html)


def test_write_deliverables_writes_the_onepager(bundle, tmp_path):
    files = write_deliverables(bundle, tmp_path, include_docx=False, include_data=False)
    (page,) = [f for f in files if f.name.endswith("_ic_onepager.html")]
    assert "<main class='page'" in page.read_text(encoding="utf-8")


def test_labels_come_from_the_shared_string_table(bundle):
    from impact_vision.impact.report_templates.design.strings import STRINGS

    for lang in ("en", "zh-HK", "zh-CN"):
        html = render_ic_onepager(bundle.report_data, lang)
        for key in ("op_title", "op_reasons", "op_conditions", "op_negative", "eq_title"):
            assert STRINGS[lang][key] in html, (lang, key)
    zh = render_ic_onepager(bundle.report_data, "zh-HK")
    assert "covenant:" not in zh and "reporting:" not in zh and "Suggested conditions" not in zh


@pytest.mark.parametrize("lang", ["en", "zh-HK"])
def test_prints_on_exactly_one_a4_page_in_chromium(lang, tmp_path):
    """The --pdf path (headless Chromium) gives one page for every sample deck."""
    pytest.importorskip("playwright.sync_api")
    fitz = pytest.importorskip("pymupdf")
    from impact_vision.impact.report_templates.pdf import PdfUnavailable, html_to_pdf

    for key in SAMPLE_DECKS:
        data = assess_file(sample_deck_path(key)).report_data
        try:
            path, engine = html_to_pdf(render_ic_onepager(data, lang), tmp_path / f"{key}_{lang}.pdf")
        except PdfUnavailable as exc:
            pytest.skip(f"Chromium not available: {exc}")
        if engine != "chromium":
            pytest.skip(f"printed with {engine}, not Chromium")
        with fitz.open(path) as doc:
            assert doc.page_count == 1, (key, lang, doc.page_count)
            w, h = doc[0].rect.width, doc[0].rect.height
            assert abs(w - 595.3) < 2 and abs(h - 841.9) < 2  # A4 in points
