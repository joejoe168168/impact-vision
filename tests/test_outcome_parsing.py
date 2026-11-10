"""Reading reach, the ask and tonnes from a deck: goals, currencies and running totals."""
from __future__ import annotations

import pytest

from impact_vision.impact.expected_impact import _ask, read_outcomes
from impact_vision.impact.pipeline import assess_document

DECK = """# EduPath — Series A

EduPath runs low-cost tutoring centres in Bihar.

## Traction
- 120,000 students enrolled in 2025.
- Test scores rose 22% versus the district baseline.

## {ask_heading}
{ask_line}
"""


def _deck(heading: str = "The ask", line: str = "We are raising USD 10m to reach 1 million students.") -> str:
    return DECK.format(ask_heading=heading, ask_line=line)


def test_a_funding_goal_is_a_target_not_reach() -> None:
    inp = read_outcomes([], "120,000 students enrolled in 2025.\nWe are raising USD 10m to reach 1 million students.")
    assert inp.reach is not None and inp.reach.value == 120_000          # was 1,000,000
    assert any("1 million students" in t for t in inp.targets)
    # A result that happens to follow "to" is still a result.
    plain = read_outcomes([], "Thanks to 4,000 farmers, yields rose 12%.")
    assert plain.reach is not None and plain.reach.value == 4_000


@pytest.mark.parametrize("heading", ["The ask", "Funding", "Use of funds", "Ask"])
def test_the_ask_is_found_under_any_ask_heading(heading: str) -> None:
    block = assess_document(_deck(heading), name="EduPath").report_data["expected_impact"]
    assert block["ask"] and block["ask"]["usd"] == pytest.approx(10_000_000)
    people = next(o for o in block["outcomes"] if o["kind"] == "people")
    assert people["per_usd_1m"]["p50"] == pytest.approx(people["p50"] / 10)
    assert {f["name"]: f["median"] for f in people["factors"]}["Reach"] == 120_000


@pytest.mark.parametrize(("line", "usd"), [
    ("Raising USD 5m seed round.", 5_000_000),
    ("Raising $5m seed round.", 5_000_000),
    ("Raising HK$ 25m Series A.", 25_000_000 * 0.128),
    ("Raising S$ 4m seed round.", 4_000_000 * 0.74),            # was read as US$4m
    ("Raising A$ 3m seed round.", 3_000_000 * 0.66),            # was read as US$3m
    ("Raising R$ 10m seed round.", 10_000_000 / 4.95),          # was read as US$10m
    ("Raising MXN 40m Series A.", 40_000_000 / 17.5),           # was not read at all
    ("Raising ZAR 30m round.", 30_000_000 / 18.2),
])
def test_ask_currencies(line: str, usd: float) -> None:
    amount, _text = _ask(line)
    assert amount == pytest.approx(usd, rel=0.01)


def test_an_unknown_currency_is_left_out_rather_than_guessed() -> None:
    assert _ask("Raising XYZ 10m seed round.") == (None, "")


def _climate(sentence: str) -> dict:
    deck = f"# CoolGrid\n\nCoolGrid sells solar cold rooms in Kenya.\n\n## Impact\n- {sentence}\n"
    block = assess_document(deck, name="CoolGrid", sector="energy").report_data["expected_impact"]
    return next(o for o in block["outcomes"] if o["kind"] == "climate")


def test_a_running_total_of_tonnes_is_not_multiplied_by_years() -> None:
    yearly = _climate("Our units avoided 20,000 tCO2e in 2025.")
    total = _climate("Our units have avoided 20,000 tCO2e since launch.")
    duration = {f["name"]: f for f in total["factors"]}["Duration (years)"]
    assert duration["median"] == 1.0 and duration["why_key"] == "why_cumulative"
    assert {f["name"]: f["median"] for f in yearly["factors"]}["Duration (years)"] > 1
    assert total["p50"] < yearly["p50"] / 2                     # was identical


def test_cumulative_reason_is_translated() -> None:
    from impact_vision.impact.report_templates.design.strings import translator

    assert "累計" in translator("zh-HK")("why_cumulative") and "累计" in translator("zh-CN")("why_cumulative")
