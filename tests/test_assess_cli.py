"""W1.1 / W1.2: `impact-vision demo` and `impact-vision assess` work offline."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from impact_vision.cli import app
from impact_vision.impact.pipeline import (
    SAMPLE_DECKS,
    assess_file,
    reflow_pdf_text,
    sample_deck_path,
)

runner = CliRunner()


@pytest.mark.parametrize("key", list(SAMPLE_DECKS))
def test_sample_decks_ship_as_pdf_and_assess(key):
    path = sample_deck_path(key)
    assert path.suffix == ".pdf" and path.is_file()
    summary = assess_file(path).summary()
    assert summary["company"] and "\n" not in summary["company"]
    assert summary["claims"] > 0
    assert summary["gate"] != "FAIL"  # fictional decks are data-light, not red flags


def test_pdf_reflow_keeps_headings_and_joins_wrapped_lines():
    text = "People & smallholders\nWe employ 142\nstaff, of whom 38% are women.\nRisks\nWe audit."
    out = reflow_pdf_text(text)
    assert "We employ 142 staff" in out
    assert out.startswith("People & smallholders\n")


def test_demo_writes_gallery_and_deliverables(tmp_path):
    result = runner.invoke(app, ["demo", "--no-open", "--out-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    index = tmp_path / "index.html"
    assert index.is_file()
    html = index.read_text(encoding="utf-8")
    for key in SAMPLE_DECKS:
        assert sample_deck_path(key).name  # sanity
    assert html.count('class="gcard"') == len(SAMPLE_DECKS)
    assert len(list(tmp_path.glob("*_impact_report.html"))) == len(SAMPLE_DECKS)
    assert "impact-vision assess" in result.output


def test_demo_rejects_unknown_deck(tmp_path):
    result = runner.invoke(app, ["demo", "--deck", "nope", "--no-open", "-o", str(tmp_path)])
    assert result.exit_code == 2


def test_assess_markdown_json(tmp_path):
    deck = tmp_path / "deck.md"
    deck.write_text(
        "SunPath Energy Ltd sells solar home systems to off-grid households in Kenya. "
        "We have connected 42,000 households. Our systems avoided 20,000 tCO2e in 2024.",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = runner.invoke(app, ["assess", str(deck), "--json", "-o", str(out), "--audience", "lp"])
    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    assert summary["company"] == "SunPath Energy Ltd"
    assert summary["reported_metrics"]["PI7954"] == "42,000"
    report = out / "sunpath_energy_ltd_impact_report.html"
    assert report.is_file()
    assert 'id="sec-greenwashing"' not in report.read_text(encoding="utf-8")  # LP view


def test_assess_errors_are_friendly(tmp_path):
    missing = runner.invoke(app, ["assess", str(tmp_path / "nope.pdf")])
    assert missing.exit_code == 1 and "No such file" in missing.output
    bad = tmp_path / "deck.xlsx"
    bad.write_text("x", encoding="utf-8")
    assert runner.invoke(app, ["assess", str(bad)]).exit_code == 1
    deck = tmp_path / "d.md"
    deck.write_text("Hello", encoding="utf-8")
    assert runner.invoke(app, ["assess", str(deck), "--audience", "everyone"]).exit_code == 2
