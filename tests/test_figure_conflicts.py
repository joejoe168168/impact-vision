"""Two different figures for the same metric are reported, not silently reduced to the first."""
from __future__ import annotations

from impact_vision.impact.consistency import find_conflicts
from impact_vision.impact.expected_impact import suggest_conditions
from impact_vision.impact.i18n_phrasebook import localize
from impact_vision.impact.pipeline import assess_document, assess_file, sample_deck_path
from impact_vision.impact.report_templates.decision_report import render_decision_report

DECK = """# SunPath Energy

SunPath sells pay-as-you-go solar home systems in rural Kenya.

## Traction
- We have connected 42,000 households across 14 counties.
- Repayment rates stay above 92%.

## Impact
- {second}
- Our systems avoided 20,000 tCO2e in 2024.
"""


def _bundle(second: str):
    return assess_document(DECK.format(second=second), name="SunPath Energy")


def test_conflicting_figures_are_reported_with_both_sentences() -> None:
    data = _bundle("Our systems reach 24,000 households, replacing kerosene lamps.").report_data
    (conflict,) = data["figure_conflicts"]
    assert conflict["metric_id"] == "PI7954" and conflict["values"] == ["24,000", "42,000"]
    assert conflict["difference_pct"] == 43 and conflict["name"]
    assert [s["value"] for s in conflict["sources"]] == ["24,000", "42,000"]
    assert "24,000 households" in conflict["sources"][0]["sentence"]
    assert not conflict["sources"][0]["sentence"].startswith("-")


def test_the_conflict_leads_the_evidence_plan_and_becomes_a_condition_precedent() -> None:
    block = _bundle("Our systems reach 24,000 households, replacing kerosene lamps.").report_data["expected_impact"]
    first = block["evidence_plan"][0]
    assert first["kind"] == "reconcile" and "24,000 and 42,000" in first["action"]
    assert len(block["evidence_plan"]) <= 4
    reconcile = next(c for c in suggest_conditions(block) if c["text"] == first["action"])
    assert reconcile["type"] == "condition_precedent"


def test_report_shows_the_conflict_in_every_language() -> None:
    data = _bundle("Our systems reach 24,000 households, replacing kerosene lamps.").report_data
    en = render_decision_report(data)
    assert "Figures that disagree" in en and "24,000 and 42,000 (43% apart)" in en
    zh = render_decision_report(data, lang="zh-HK")
    assert "互相矛盾的數字" in zh and "相差 43%" in zh
    action = data["expected_impact"]["evidence_plan"][0]
    for lang, word in (("zh-HK", "查明"), ("zh-CN", "查明")):
        assert word in localize(action["action"], lang) and "43%" in localize(action["why"], lang)


def test_close_figures_other_years_and_targets_are_not_conflicts() -> None:
    assert _bundle("Our systems reach 41,000 households, replacing kerosene lamps.").report_data[
        "figure_conflicts"] == []                                              # within tolerance
    # A dated earlier figure next to an undated current one reads as growth.
    assert _bundle("In 2023 our systems reached 24,000 households.").report_data["figure_conflicts"] == []
    growth = find_conflicts([{"text": "We connected 24,000 households in 2023.", "category": "outcome"},
                             {"text": "We connected 42,000 households in 2024.", "category": "outcome"}])
    assert growth == []                                                        # growth, not a contradiction
    target = find_conflicts([{"text": "We have connected 42,000 households.", "category": "outcome"},
                             {"text": "We target 150,000 households by 2028.", "category": "commitment"}])
    assert target == []


def test_sample_decks_have_no_conflicts_and_pdf_conflicts_get_pages() -> None:
    for deck in ("solar", "microfinance", "pig-farm"):
        bundle = assess_file(sample_deck_path(deck))
        assert bundle.report_data["figure_conflicts"] == [], deck
        assert "Figures that disagree" not in render_decision_report(bundle.report_data)


def test_conflicts_are_in_the_csv_export() -> None:
    import csv
    import io

    from impact_vision.impact import exports

    data = _bundle("Our systems reach 24,000 households, replacing kerosene lamps.").report_data
    rows = list(csv.DictReader(io.StringIO(exports.to_csv(data))))
    row = next(r for r in rows if r["Section"] == "Figure conflict")
    assert row["Metric"] == "PI7954" and row["Value"] == "24,000 vs 42,000" and row["Numeric"] == "43"


def test_bayes_fold_counts_contradicting_evidence_from_a_generator() -> None:
    from impact_vision.impact.bayes import default_prior, fold

    posterior = fold(default_prior(), (v for v in [True, False, False]))
    assert (posterior.n_corroborating, posterior.n_contradicting) == (1, 2)      # was (1, 0)
