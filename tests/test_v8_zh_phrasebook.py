"""zh-HK / zh-CN report bodies (roadmap v8 W3.7): generated sentences are
translated, company evidence stays verbatim, English is untouched."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from impact_vision.impact.i18n_phrasebook import localize
from impact_vision.impact.pipeline import assess_file, sample_deck_path
from impact_vision.impact.report_templates.decision_report import build_view

DECKS = Path(__file__).parent / "golden_decks"


@pytest.mark.parametrize("lang", ["zh-HK", "zh-CN"])
def test_generated_sentences_are_translated(lang):
    for deck in sorted(DECKS.glob("*.md")):
        view = build_view(assess_file(deck).report_data, lang=lang)
        texts = list(view["verdict"]["reasons"]) + [a["text"] for a in view["actions"]]
        texts += [m[k] for m in view["mind"] for k in ("what", "why")]
        texts += [r["impact"] for r in (view.get("negatives") or {}).get("items", [])]
        texts += [r["sentence"] for r in (view.get("five_d") or {}).get("rows", [])]
        for text in texts:
            # IRIS+ names may stay in English; a whole English sentence may not.
            assert not re.search(r"^[A-Z][a-z]+ [a-z]+ [a-z]+ [a-z]+", text), (deck.name, text)


def test_english_is_unchanged_and_claims_stay_verbatim():
    data = assess_file(sample_deck_path("solar")).report_data
    en, zh = build_view(data), build_view(data, lang="zh-HK")
    assert [a["text"] for a in en["actions"]] != [a["text"] for a in zh["actions"]]
    assert [c["text"] for c in en["evidence"]["claims"]] == [c["text"] for c in zh["evidence"]["claims"]]


def test_unknown_text_passes_through_and_slots_translate():
    assert localize("Something new the engine says.", "zh-HK") == "Something new the engine says."
    assert localize("vague wording", "en") == "vague wording"
    assert localize("Show how you manage: clients become over-indebted (affects borrowers).", "zh-CN") \
        == "说明如何管理：客户过度负债（影响借款人）。"
    assert "12,000 名住戶" in localize("Have the headline reach figure (12,000 households) verified by a third party.",
                                     "zh-HK")
