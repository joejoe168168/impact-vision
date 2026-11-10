"""C5b: reach by stakeholder, effect sizes, thousands separators, Chinese numerals."""

from impact_vision.impact.expected_impact import read_outcomes


def _read(text: str):
    return read_outcomes([], scoring_text=text, full_text=text)


def test_reach_prefers_beneficiaries_over_registered_users():
    out = _read("We trained 5,000 farmers last season. The app has 900,000 users registered.")
    assert out.reach.value == 5000 and out.reach.noun == "farmers"


def test_generic_noun_is_kept_as_other_reach():
    out = _read("We serve 5,000 farmers in Kenya. Our platform has 40,000 customers.")
    assert out.reach.noun == "farmers"
    assert [(f.noun, f.value) for f in out.other_reach] == [("customers", 40000)]


def test_generic_noun_is_reach_when_it_is_all_there_is():
    assert _read("Our platform has 40,000 customers across Kenya.").reach.value == 40000


def test_effect_size_is_not_a_percentage():
    out = _read("An RCT found learning gains of 0.21 SD for enrolled pupils.")
    assert out.depth.effect_size == 0.21
    assert abs(out.depth.value - 0.084) < 1e-9


def test_space_as_thousands_separator():
    assert _read("We supply clean water to 12 000 households.").reach.value == 12000
    assert _read("We supply clean water to 12 000 households.").reach.value == 12000


def test_year_does_not_bleed_into_the_count():
    assert _read("Cohort of 2023 120 students completed the course.").reach.value == 120


def test_chinese_wan_and_numerals():
    assert _read("我們每年服務 3.2 萬名長者,遍及全港。").reach.value == 32000
    assert _read("計劃已惠及三千名學生及其家庭。").reach.value == 3000
