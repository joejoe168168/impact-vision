"""zh-HK IC memo and DD report (TECH_SPEC U3b)."""
from __future__ import annotations

import re

import pytest

from impact_vision.impact.pipeline import assess_file, sample_deck_path, write_deliverables
from impact_vision.impact.report_templates.localize_html import (
    LABELS_ZH_HK,
    localize_document,
    localize_text,
)

_SIMPLIFIED = "这为与项风险证据质额计划报"


@pytest.fixture(scope="module")
def packs(tmp_path_factory):
    bundle = assess_file(sample_deck_path("pig-farm"))
    out = {}
    for lang in ("en", "zh-HK", "zh-CN"):
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


def test_dd_report_labels_and_questions_in_traditional_chinese(packs):
    from impact_vision.impact.i18n import load_dd_checklist_localized

    dd = packs["zh-HK"]["dd_report.html"]
    assert "盡職審查問卷助手" in dd and "覆蓋率" in dd
    assert not re.findall(r"<h2[^>]*>[A-Za-z0-9.&; ()/-]+</h2>", dd)
    zh = load_dd_checklist_localized("zh-HK")
    assert zh["categories"]["governance_esg"].startswith("管治") and "甚麼" in zh["questions"][0]["question"]
    assert not (set(str(zh["questions"])) & set("这为与项风险证据质额计划报"))
    # Every English question in the report is rendered in Chinese.
    from impact_vision.impact.dd_checklist import load_checklist

    for q in load_checklist():
        assert f">{q.question}<" not in dd.replace("&#x27;", "'"), q.id


_TRADITIONAL = "這為與項險證據質額計劃報們說時麼審"


@pytest.mark.parametrize("lang", ["zh-HK", "zh-CN"])
def test_checklists_cover_every_question_by_id(lang):
    from impact_vision.impact.dd_checklist import load_checklist
    from impact_vision.impact.i18n import load_dd_checklist_localized

    zh = load_dd_checklist_localized(lang)
    assert [q["id"] for q in zh["questions"]] == [q.id for q in load_checklist()]
    bad = _SIMPLIFIED if lang == "zh-HK" else _TRADITIONAL
    assert not (set(str(zh["questions"])) & set(bad))


def test_zh_locale_aliases_pick_the_checklist_by_script():
    from impact_vision.impact.i18n import load_dd_checklist_localized

    assert load_dd_checklist_localized("zh") == load_dd_checklist_localized("zh-CN")
    assert load_dd_checklist_localized("zh_TW") == load_dd_checklist_localized("zh-HK")


def test_memo_and_dd_report_in_simplified_chinese(packs):
    memo, dd = packs["zh-CN"]["ic_memo.html"], packs["zh-CN"]["dd_report.html"]
    for doc in (memo, dd):
        assert '<html lang="zh-CN"' in doc
        assert not re.findall(r"<h2[^>]*>[A-Za-z0-9.&; ()/-]+</h2>", doc)
        body = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", "", doc, flags=re.S)
        assert not (set(body) & set(_TRADITIONAL))
    assert "投资委员会备忘录" in memo and "尽职调查问卷助手" in dd and "Kampung Makmur" in memo


def test_no_english_chrome_left_in_memo(packs):
    memo = re.sub(r"<(style|script)\b[^>]*>.*?</\1>|<[^>]+>", " ", packs["zh-HK"]["ic_memo.html"], flags=re.S)
    for phrase in ("Expected impact is quantified", "No binding impact targets", "Review before submission",
                   "Automated analysis", "bundled example thesis", "Substantive with Gaps",
                   "vs. min", "thesis checks", "Scale=", "Ready for IC", "Methodology v"):
        assert phrase not in memo, phrase


def test_c8_note_in_memo_in_every_language(packs):
    assert "Ready, with" in packs["en"]["ic_memo.html"] and "core metric set reported" in packs["en"]["ic_memo.html"]
    assert "核心指標集已報告" in packs["zh-HK"]["ic_memo.html"]
    assert "核心指标集已报告" in packs["zh-CN"]["ic_memo.html"]


def test_multi_sentence_text_is_only_translated_whole():
    assert localize_text("Review before submission. Not investment advice.") == "提交前請審閱。並非投資建議。"
    claim = "Review before submission. We reach 5,000 farmers."
    assert localize_text(claim) == claim


def test_zh_cn_tables_are_built_from_the_zh_hk_source():
    """scripts/build_phrasebook.py must be re-run after editing localize_html.py."""
    from impact_vision.impact.report_templates import localize_html as lh

    derived = lh._derived()
    missing = [k for k in {**lh._EXTRA, **lh.LABELS_ZH_HK} if k not in derived["labels"]]
    assert not missing, f"re-run scripts/build_phrasebook.py: {missing[:5]}"
    assert all(rx.pattern in derived["label_patterns"] for rx, _ in lh._PATTERNS)
