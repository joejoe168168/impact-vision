"""F2: `impact-vision compare` puts deals side by side without a composite or a winner."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from impact_vision.cli import app
from impact_vision.impact.compare import compare_bundles, format_comparison, render_comparison_html
from impact_vision.impact.pipeline import SAMPLE_DECKS, assess_file, sample_deck_path

runner = CliRunner()


def _fake(name, outcomes):
    return SimpleNamespace(
        company=SimpleNamespace(name=name, sector="energy"),
        scorecard=SimpleNamespace(display_status="WARN"),
        greenwashing=SimpleNamespace(overall_score=20.0, classification="Low"),
        report_data={"expected_impact": {
            "gate": {"state": "evidence_plan", "label": "Evidence plan required", "plan": [{"action": "Verify"}]},
            "outcomes": outcomes, "evidence_quality": {"score": 50, "label": "fair"}}},
    )


def _outcome(kind, p10, p50, p90, unit="tCO2e"):
    return {"kind": kind, "unit": unit, "stakeholder": "x", "p10": p10, "p50": p50, "p90": p90}


@pytest.fixture(scope="module")
def bundles():
    return [assess_file(sample_deck_path(k)) for k in list(SAMPLE_DECKS)[:2]]


def test_two_decks_give_two_columns_and_no_composite(bundles):
    out = compare_bundles(bundles)
    assert [d["company"] for d in out["deals"]] == [b.company.name for b in bundles]
    text = json.dumps(out).lower()
    assert "composite" not in text and "winner" not in text
    for deal, bundle in zip(out["deals"], bundles):
        head = bundle.summary()["expected_impact"]
        assert deal["outcomes"][head["kind"]]["p50"] == head["p50"]  # same number as the report
        assert deal["evidence_quality"]["score"] == bundle.summary()["evidence_quality"]
    html = render_comparison_html(out)
    for b in bundles:
        assert b.company.name in html
    assert format_comparison(out)


def test_overlapping_ranges_are_flagged():
    out = compare_bundles([_fake("A", [_outcome("climate", 10, 50, 100)]),
                           _fake("B", [_outcome("climate", 80, 200, 400)])])
    (note,) = out["notes"]
    assert note["overlap"] is True and "cannot be told apart" in note["text"]

    out = compare_bundles([_fake("A", [_outcome("climate", 10, 50, 100)]),
                           _fake("B", [_outcome("climate", 150, 200, 400)])])
    assert out["notes"][0]["overlap"] is False and out["notes"][0]["text"].count("B") == 1


def test_different_outcome_kinds_are_not_ranked():
    out = compare_bundles([_fake("A", [_outcome("climate", 10, 50, 100)]),
                           _fake("B", [_outcome("people", 1000, 2000, 4000, unit="person-years")])])
    assert out["outcome_kinds"] == ["climate", "people"]
    assert all(n["overlap"] is None for n in out["notes"])
    assert not any("above" in n["text"] for n in out["notes"])


def test_needs_two():
    with pytest.raises(ValueError):
        compare_bundles([_fake("A", [])])


def test_cli_compare(tmp_path):
    paths = [str(sample_deck_path(k)) for k in list(SAMPLE_DECKS)[:2]]
    result = runner.invoke(app, ["compare", *paths, "--json", "--out-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.output)["deals"]) == 2
    assert (tmp_path / "comparison.html").is_file()
    assert runner.invoke(app, ["compare", paths[0], "--out-dir", str(tmp_path)]).exit_code == 2


def test_per_usd_1m_uses_the_ask_read_from_the_deck(tmp_path):
    """The figure comes from expected_impact["ask"] / outcome["per_usd_1m"]; blank without an ask."""
    with_ask = _fake("A", [{**_outcome("climate", 10, 50, 100), "per_usd_1m": {"p10": 5, "p50": 25, "p90": 50}}])
    with_ask.report_data["expected_impact"]["ask"] = {"usd": 2_000_000, "text": "USD 2m"}
    no_ask = _fake("B", [{**_outcome("climate", 10, 50, 100), "per_usd_1m": {"p10": 5, "p50": 25, "p90": 50}}])
    out = compare_bundles([with_ask, no_ask])
    a, b = out["deals"]
    assert a["ask_usd"] == 2_000_000 and a["outcomes"]["climate"]["p50_per_usd_1m"] == 25
    assert b["ask_usd"] is None and b["outcomes"]["climate"]["p50_per_usd_1m"] is None
    html = render_comparison_html(out)
    assert html.count("per US$1m") == 1

    # End to end: a deck that states its raise gets the figure; the sample decks state none.
    deck = tmp_path / "raise.md"
    deck.write_text("# Raincatch Ltd\nRainwater tanks for rural schools in Kenya.\n"
                    "We serve 12,000 students in 40 schools; a baseline survey in 2024 showed absence fell 18%.\n"
                    "## The ask\nWe are raising USD 2m in a seed round.\n", encoding="utf-8")
    real = assess_file(deck)
    col = compare_bundles([real, real])["deals"][0]
    assert col["ask_usd"] == pytest.approx(2_000_000)
    per = [o["p50_per_usd_1m"] for o in col["outcomes"].values()]
    assert per and all(v is not None and v > 0 for v in per)
