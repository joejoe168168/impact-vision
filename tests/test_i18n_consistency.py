"""Chinese reports: no English enum values left in the table cells, consistent
placeholders across languages, and mainland wording in zh-CN."""
from __future__ import annotations

import re

import pytest
import yaml

from impact_vision.impact._paths import data_path
from impact_vision.impact.pipeline import assess_file, sample_deck_path
from impact_vision.impact.report_templates.decision_report import render_decision_report
from impact_vision.impact.report_templates.design.strings import EN, ZH_CN, ZH_HK

_SLOT = re.compile(r"\{(\w+)[^}]*\}")


@pytest.fixture(scope="module")
def solar():
    return assess_file(sample_deck_path("solar")).report_data


def test_placeholders_match_across_languages() -> None:
    """A translation that drops or renames a {slot} fails at render time, in one language only."""
    for key, english in EN.items():
        slots = sorted(_SLOT.findall(english))
        assert sorted(_SLOT.findall(ZH_HK[key])) == slots, key
        assert sorted(_SLOT.findall(ZH_CN[key])) == slots, key


def test_traditional_and_simplified_do_not_mix() -> None:
    simplified_only = set("响评机资与伙监审据证险风绿会业标贡献谁总择无这来")
    assert not {c for v in ZH_HK.values() for c in v} & simplified_only


@pytest.mark.parametrize(("lang", "outcome", "intent"), [("zh-HK", "成果", "目標／意向"), ("zh-CN", "成果", "目标／意向")])
def test_claim_types_are_translated(solar, lang: str, outcome: str, intent: str) -> None:
    html = render_decision_report(solar, lang=lang)
    assert "<td>outcome</td>" not in html and "<td>intent</td>" not in html      # were shown in English
    assert f"<td>{outcome}</td>" in html and f"<td>{intent}</td>" in html
    assert "<td>outcome</td>" in render_decision_report(solar)                    # English is unchanged


def test_target_status_and_language_note_are_translated(solar) -> None:
    data = dict(solar, target_tracking={"targets": [
        {"metric_id": "PI7954", "target_description": "150,000 households", "current_value": 42000,
         "progress_pct": 28.0, "status": "active"},
        {"metric_id": "OI2764", "target": "80,000 tCO2e", "status": "on_hold_pending_review"},
    ]})
    zh = render_decision_report(data, lang="zh-HK")
    assert "<td>進行中</td>" in zh and "<td>active</td>" not in zh
    assert "<td>on hold pending review</td>" in zh                 # an unknown status still reads as words
    assert "<td>active</td>" in render_decision_report(data)
    # The note used to say recommendations stay in the original language; they are translated since 0.19.
    assert "建議及行業風險以原文顯示" not in zh and "IRIS+ 指標名稱保留英文" in zh


def test_zh_cn_phrasebook_uses_mainland_wording() -> None:
    book = yaml.safe_load(data_path("i18n", "phrasebook.yaml").read_text(encoding="utf-8"))
    entries = [*book["patterns"], *book["fragments"], *book["exact"].values()]
    hong_kong_usage = ("量度", "甚么", "受惠", "连结", "「", "」", "质素", "持份者")
    for entry in entries:
        assert not any(term in entry["zh-CN"] for term in hong_kong_usage), entry["zh-CN"]
        # zh-HK keeps its own wording and punctuation.
        assert sorted(_SLOT.findall(entry["zh-HK"])) == sorted(_SLOT.findall(entry["zh-CN"]))
    assert any("量度" in e["zh-HK"] for e in entries) and any("衡量" in e["zh-CN"] for e in entries)
