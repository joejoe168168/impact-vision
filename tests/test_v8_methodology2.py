"""Methodology 2.0 (v8 Wave 1) and the W2.5 perturbation / gaming tests.

A score must move when the impact moves (reach, depth, evidence) and must not
move when only the vocabulary does.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from openharness.impact.expected_impact import (
    assess_expected_impact,
    methodology_mode,
    read_outcomes,
)
from openharness.impact.pipeline import assess_document, assess_file, sample_deck_path

DECKS = Path(__file__).parent / "golden_decks"

BASE = """# Sunlit Homes — Seed pitch

Sunlit Homes sells solar lanterns to off-grid households in rural Uganda.

## Traction
- 12,000 households served in 2024.
- Household lighting costs fell 35% versus their previous kerosene spend (customer survey, before and after).

## Ask
USD 2m seed round.
"""


def _people(text: str) -> dict:
    bundle = assess_document(text, name="Sunlit Homes")
    block = bundle.report_data["expected_impact"]
    return next(o for o in block["outcomes"] if o["kind"] == "people"), block


def test_reads_reach_depth_and_ask():
    inp = read_outcomes([], BASE, sector="energy")
    assert inp.reach and inp.reach.value == 12_000 and inp.reach.noun == "households"
    assert inp.depth and abs(inp.depth.value - 0.35) < 1e-9
    assert inp.ask_usd == 2_000_000


def test_scaling_reach_scales_expected_impact():
    big, _ = _people(BASE)
    small, _ = _people(BASE.replace("12,000 households", "120 households"))
    assert small["p50"] < big["p50"] / 50          # ~×100 smaller, not unchanged as in v1


def test_buzzwords_do_not_move_expected_impact():
    plain, _ = _people(BASE)
    hyped = BASE.replace("Sunlit Homes sells", "Sunlit Homes is a unique, novel, catalytic, transformative "
                                                "and additional company that sells")
    buzz, _ = _people(hyped)
    assert buzz["p50"] == pytest.approx(plain["p50"], rel=0.02)


def test_a_comparison_group_narrows_the_range_and_nets_deadweight():
    weak, _ = _people(BASE)
    strong_text = BASE.replace("(customer survey, before and after)",
                               "(independent study versus a matched comparison group)")
    strong, block = _people(strong_text)
    assert strong["spread"] < weak["spread"]
    factors = {f["name"]: f for f in strong["factors"]}
    assert factors["Without deadweight"]["median"] == 1.0
    assert block["evidence_quality"]["score"] > _people(BASE)[1]["evidence_quality"]["score"]


def test_problem_statement_is_not_reach_and_targets_are_kept_apart():
    text = BASE.replace("## Traction", "## The problem\n25 million people in Uganda have no electricity.\n\n## Traction")
    text += "\n## Targets\nWe target 100,000 households by 2028.\n"
    people, block = _people(text)
    assert "25 million" not in people["source"]
    assert any("100,000" in t for t in block["targets"])


def test_ranges_are_reproducible():
    a, _ = _people(BASE)
    b, _ = _people(BASE)
    assert (a["p10"], a["p50"], a["p90"]) == (b["p10"], b["p50"], b["p90"])


def test_unmeasured_depth_tops_the_evidence_plan():
    text = BASE.replace("- Household lighting costs fell 35% versus their previous kerosene spend "
                        "(customer survey, before and after).\n", "")
    people, block = _people(text)
    assert people["depth_measured"] is False
    assert people["drivers"][0]["factor"] == "Depth of change"
    assert "Measure how much life changes" in block["evidence_plan"][0]["action"]


def test_gate2_states_on_goldens():
    green = assess_file(DECKS / "greenvibe.md").report_data["expected_impact"]["gate"]
    assert green["state"] == "fails_thesis"
    solar = assess_file(sample_deck_path("solar")).report_data["expected_impact"]
    assert solar["gate"]["state"] == "evidence_plan" and solar["gate"]["plan"]
    assert {o["kind"] for o in solar["outcomes"]} == {"people", "climate"}


def test_ready_when_evidence_is_good():
    from openharness.impact.models import ImpactClaim

    claims = [ImpactClaim(text="We served 50,000 farmers in 2024, verified by an independent auditor.",
                          category="outcome", evidence_strength=3,
                          entities={"evidence": ["third_party_verified"]}),
              ImpactClaim(text="Yields rose 22% versus a matched comparison group in an independent evaluation.",
                          category="outcome", evidence_strength=4,
                          entities={"evidence": ["controlled_evaluation", "third_party_verified"]})]
    block = assess_expected_impact(claims, " ".join(c.text for c in claims), sector="agriculture",
                                   data_completeness_pct=60)
    assert block["gate"]["state"] == "ready", block["gate"]


def test_chinese_deck_is_read():
    block = assess_file(DECKS / "yikang_eldercare_hk.md").report_data["expected_impact"]
    people = block["outcomes"][0]
    assert people["stakeholder"] == "older people" and people["evidence_level"] >= 2
    assert any(f["name"] == "Depth of change" and f["median"] == pytest.approx(0.27) for f in people["factors"])


def test_report_leads_with_expected_impact_and_v1_switch(monkeypatch):
    from openharness.impact.report_templates.decision_report import build_view, render_decision_report

    data = assess_file(sample_deck_path("solar")).report_data
    view = build_view(data)
    assert view["kpis"][0]["label"] == "Expected impact"
    assert view["verdict"]["label"] == "Evidence plan required"
    assert "sec-impact" in render_decision_report(data)
    zh = render_decision_report(data, lang="zh-HK")
    assert "預期影響" in zh and "住戶" in zh
    monkeypatch.setenv("IMPACT_VISION_METHODOLOGY_VERSION", "1")
    assert methodology_mode() == "1"
    assert build_view(data)["verdict"]["label"] != "Evidence plan required"
