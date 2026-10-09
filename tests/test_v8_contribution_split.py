"""Enterprise vs investor contribution on evidence only (roadmap v8 W1.4)."""
from __future__ import annotations

from impact_vision.impact.contribution_split import (
    contribution_split,
    delivered_from_claims,
    investor_contribution,
)
from impact_vision.impact.pipeline import assess_document

BASE = """# Sunlit Homes — Seed pitch

Sunlit Homes sells solar lanterns to off-grid households in rural Uganda.

## Traction
- 12,000 households served in 2024.
- Household lighting costs fell 35% versus their previous kerosene spend (customer survey).

## Ask
USD 2m seed round.
"""

HYPE = BASE.replace("Sunlit Homes sells", "Sunlit Homes is a unique, novel, catalytic, transformative, "
                                           "pioneering and additional company that sells")


def _contribution(text: str) -> float:
    return assess_document(text, name="Sunlit Homes").report_data["five_dimensions"]["contribution"]["score"]


def test_adjectives_do_not_move_contribution():
    assert _contribution(HYPE) == _contribution(BASE)
    split = assess_document(HYPE, name="Sunlit").report_data["contribution_split"]
    assert {"catalytic", "transformative", "unique"} <= set(split["investor"]["adjectives_ignored"])
    assert split["investor"]["score"] == 0


def test_a_comparison_group_raises_enterprise_contribution():
    strong = BASE.replace("(customer survey)", "(independent study versus a matched comparison group)")
    assert _contribution(strong) > _contribution(BASE)
    a = assess_document(BASE, name="S").report_data["contribution_split"]["enterprise"]
    b = assess_document(strong, name="S").report_data["contribution_split"]["enterprise"]
    assert b["score"] > a["score"] and b["signals"][0]["signal"] == "controlled_evaluation"


def test_investor_channels_need_specifics():
    memo = ("We would be the first institutional investor in the company. "
            "The term sheet includes impact covenants in the shareholders' agreement. "
            "We take a board seat and fund a TA facility of USD 150,000. "
            "The facility is a 7-year tenor loan with a first-loss tranche.")
    inv = investor_contribution(memo)
    levels = {c["id"]: c["level"] for c in inv["channels"]}
    assert levels == {"signal": 2, "engage": 2, "grow": 2, "flexible": 2}
    assert inv["score"] == round(100 * 8 / 12)
    vague = investor_contribution("Our catalytic, highly additional capital will be transformative.")
    assert sum(c["level"] for c in vague["channels"]) == 0
    stated = investor_contribution("We offer patient capital.")
    assert {c["id"]: c["level"] for c in stated["channels"]}["flexible"] == 1  # stated, not documented


def test_logged_delivery_reaches_level_three():
    claims = [{"channel": "non_financial_support", "planned_activities": [{"activity_id": "ta-1"}]}]
    evidence = [{"activity_id": "ta-1", "description": "Pricing workshop delivered", "artifact_refs": ["doc://ta.pdf"]}]
    delivered = delivered_from_claims(claims, evidence)
    split = contribution_split("We take a board seat.", None, delivered=delivered)
    engage = next(c for c in split["investor"]["channels"] if c["id"] == "engage")
    assert engage["level"] == 3 and engage["delivered"] == ["Pricing workshop delivered"]


def test_v1_keeps_the_old_contribution(monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_METHODOLOGY_VERSION", "1")
    assert _contribution(HYPE) > _contribution(BASE)
