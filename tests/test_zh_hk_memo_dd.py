"""zh-HK IC memo and DD report (TECH_SPEC U3b)."""
from __future__ import annotations

import re

import pytest

from impact_vision.impact.pipeline import assess_file, sample_deck_path, write_deliverables
from impact_vision.impact.report_templates.localize_html import LABELS_ZH_HK, localize_document, localize_text

_SIMPLIFIED = "这为与项风险证据质额计划报"


@pytest.fixture(scope="module")
def packs(tmp_path_factory):
    bundle = assess_file(sample_deck_path("pig-farm"))
    out = {}
    for lang in ("en", "zh-HK"):
        d = tmp_path_factory.mktemp(lang.replace("-", "_"))
        files = write_deliverables(bundle, d, include_docx=False, lang=lang)
        out[lang] = {p.name.rsplit("_", 2)[-2] + "_" + p.name.rsplit("_", 1)[-1]: p.read_text(encoding="utf-8")
                     for p in files if p.name.endswith(("_ic_memo.html", "_dd_report.html"))}
    return out


def test_memo_is_chinese(packs):
    memo = packs["zh-HK"]["ic_memo.html"]
    assert '<html lang="zh-HK"' in memo
    assert "投資委員會備忘錄" in memo and "跳至主要內容" in memo and "本頁內容" in memo
    assert not re.findall(r"<h2[^>]*>[A-Za-z0-9.& -]+</h2>", memo)
    assert "Kampung Makmur" in memo  # names and claims stay verbatim


def test_dd_report_is_marked_chinese(packs):
    dd = packs["zh-HK"]["dd_report.html"]
    assert '<html lang="zh-HK"' in dd and "跳至主要內容" in dd


def test_english_is_untouched(packs):
    for doc in packs["en"].values():
        assert '<html lang="en"' in doc and "Skip to main content" in doc
        assert not re.search(r"[一-鿿]", doc)
        assert localize_document(doc, "en") is doc


def test_styles_and_scripts_are_not_rewritten():
    doc = '<html lang="en"><head><style>a>b{}</style></head><body><h2>Recommendation</h2><p>Acme says: Risk</p></body></html>'
    out = localize_document(doc, "zh-HK")
    assert "<style>a>b{}</style>" in out and "<h2>建議</h2>" in out and "Acme says: Risk" in out


def test_patterns_and_no_simplified_characters():
    assert localize_text("3. SDG alignment") == "3. 可持續發展目標契合度"
    assert localize_text("41.7% covered vs. min 70.0%") == "已覆蓋 41.7%，最低要求 70.0%"
    assert localize_text("A verbatim company claim.") == "A verbatim company claim."
    for en, zh in LABELS_ZH_HK.items():
        assert zh.strip() and not (set(zh) & set(_SIMPLIFIED)), en
