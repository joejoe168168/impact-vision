"""IC memo: one verdict in every format, suggested conditions, and an honest fund thesis label."""
from __future__ import annotations

import json

import pytest
import yaml
from typer.testing import CliRunner

from impact_vision.impact.expected_impact import suggest_conditions
from impact_vision.impact.ic_memo import render_ic_memo, render_ic_memo_html
from impact_vision.impact.pipeline import assess_document, assess_file, format_summary, sample_deck_path


@pytest.fixture(scope="module")
def solar():
    return assess_file(sample_deck_path("solar"))


def _memo(bundle, fmt="markdown", **kwargs):
    return render_ic_memo(bundle.assessment, bundle.scorecard, bundle.thesis, output_format=fmt,
                          expected_impact=bundle.report_data["expected_impact"],
                          dd_coverage_pct=bundle.dd.coverage_pct, **kwargs)


def test_markdown_recommendation_is_the_gate_shown_in_the_header(solar) -> None:
    md = _memo(solar)
    section = md.split("## 8. Recommendation", 1)[1]
    assert "**Evidence plan required**" in section
    assert "Fund thesis checks:" in section
    assert solar.scorecard.recommendation not in section          # the v1 text used to be printed here


def test_memo_suggests_conditions_from_the_evidence_plan_and_stated_targets(solar) -> None:
    block = solar.report_data["expected_impact"]
    conditions = suggest_conditions(block)
    assert conditions and {c["type"] for c in conditions} <= {"condition_precedent", "covenant", "reporting"}
    # Conditions precedent come first; every plan step and a stated target are covered.
    assert [c["type"] for c in conditions] == sorted(
        (c["type"] for c in conditions), key=["condition_precedent", "covenant", "reporting"].index)
    verify = next(c for c in conditions if "verified by a third party" in c["text"])
    assert verify["type"] == "condition_precedent" and verify["timing"] == "before closing"
    target = next(c for c in conditions if c["source"] == "stated target")
    assert target["type"] == "covenant" and "150,000 connected households" in target["text"]

    md = _memo(solar)
    section = md.split("## 7. Impact targets as investment conditions", 1)[1].split("## 8.", 1)[0]
    assert "No binding impact targets have been set yet" in section and "| Condition precedent |" in section
    html = render_ic_memo_html(solar.assessment, solar.scorecard, solar.thesis,
                               expected_impact=block, dd_coverage_pct=solar.dd.coverage_pct)
    assert "Suggested condition" in html and "before closing" in html
    assert "No binding impact targets were set as" not in html
    assert solar.summary()["suggested_conditions"] == conditions


def test_binding_targets_replace_the_suggestions(solar) -> None:
    from impact_vision.impact.deal_gate import TargetCondition

    binding = [TargetCondition(target_id="t1", metric_id="PI7954", baseline=42000, target_value=150000,
                               by_period="FY2028", condition_kind="covenant")]
    md = _memo(solar, target_conditions=binding)
    assert "| PI7954 | 42000.0 | 150000.0 | FY2028 | covenant |" in md and "Suggested condition" not in md


def test_no_conditions_are_suggested_for_a_deal_that_fails_the_thesis(solar) -> None:
    block = dict(solar.report_data["expected_impact"], gate={"state": "fails_thesis", "label": "Fails thesis"})
    assert suggest_conditions(block) == []
    assert suggest_conditions(None) == []


def test_every_plan_kind_has_a_condition_rule() -> None:
    from impact_vision.impact._paths import data_path

    rules = yaml.safe_load(data_path("methodology", "v2.yaml").read_text(encoding="utf-8"))["conditions"]["kinds"]
    for deck in ("solar", "microfinance", "pig-farm"):
        for item in assess_file(sample_deck_path(deck)).report_data["expected_impact"]["evidence_plan"]:
            assert item["kind"] in rules, item
    bare = assess_document("# Vague Co\n\nWe make the world better.", name="Vague Co")
    assert {i["kind"] for i in bare.report_data["expected_impact"]["evidence_plan"]} <= set(rules)


def test_the_bundled_example_thesis_is_labelled_as_such(solar, tmp_path) -> None:
    assert solar.thesis.is_example and not solar.thesis.is_default
    md = _memo(solar)
    assert "(bundled example thesis)" in md and "**Example thesis.**" in md
    html = render_ic_memo_html(solar.assessment, solar.scorecard, solar.thesis)
    assert "Example thesis." in html and "(bundled example thesis)" in html
    assert "bundled example" in format_summary(solar)
    assert solar.summary()["fund_thesis"] == {"name": solar.thesis.name, "example": True}

    own = tmp_path / "thesis.yaml"
    own.write_text(yaml.safe_dump({"fund": {"name": "Harbour Inclusion Fund II", "strategy": "impact_first",
                                            "vintage_year": 2026},
                                   "sdg_weights": {1: 0.5, 8: 0.5}}), encoding="utf-8")
    mine = assess_file(sample_deck_path("microfinance"), thesis_path=own)
    assert mine.thesis.name == "Harbour Inclusion Fund II" and not mine.thesis.is_example
    md = _memo(mine)
    assert "Harbour Inclusion Fund II" in md and "Example thesis" not in md and "bundled example" not in md
    assert "bundled example" not in format_summary(mine)
    with pytest.raises(FileNotFoundError):
        assess_file(sample_deck_path("solar"), thesis_path=tmp_path / "missing.yaml")


def test_assess_cli_takes_a_thesis(tmp_path) -> None:
    from impact_vision.cli import app

    own = tmp_path / "thesis.yaml"
    own.write_text(yaml.safe_dump({"fund": {"name": "Harbour Inclusion Fund II"}}), encoding="utf-8")
    runner = CliRunner()
    deck = str(sample_deck_path("solar"))
    out = runner.invoke(app, ["assess", deck, "-o", str(tmp_path / "a"), "--thesis", str(own), "--json"])
    assert out.exit_code == 0, out.output
    summary = json.loads(out.output[out.output.index("{"):])
    assert summary["fund_thesis"] == {"name": "Harbour Inclusion Fund II", "example": False}
    assert summary["suggested_conditions"]
    missing = runner.invoke(app, ["assess", deck, "-o", str(tmp_path / "b"), "--thesis", str(tmp_path / "nope.yaml")])
    assert missing.exit_code == 1
    default = runner.invoke(app, ["assess", deck, "-o", str(tmp_path / "c")])
    assert "bundled example" in default.output


def test_pptx_shows_the_same_verdict_and_the_ai_disclosure(solar, tmp_path) -> None:
    pptx = pytest.importorskip("pptx")
    path = _memo(solar, fmt="pptx", path=tmp_path / "memo.pptx")
    slides = pptx.Presentation(str(path)).slides
    texts = ["\n".join(s.text_frame.text for s in slide.shapes if s.has_text_frame) for slide in slides]
    gate = texts[-1]
    assert "IC Gate: Evidence plan required" in gate and "Expected impact:" in gate
    assert "verified by a third party" in gate and "Methodology v" in gate and "no generative AI" in gate
