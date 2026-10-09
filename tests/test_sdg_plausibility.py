"""W0.4: SDG results must be plausible — goal-filtered targets, no generic 'high'."""

from __future__ import annotations

import yaml

from impact_vision.impact.database import get_metric_store
from impact_vision.impact.models import Company
from impact_vision.impact.sdg_mapper import generate_sdg_gap_recommendations, map_sdg_alignment
from impact_vision.impact.sdk import ImpactVision


def _brightpath() -> Company:
    data = yaml.safe_load(open("examples/sample_company.yaml", encoding="utf-8"))["company"]
    return Company(**data)


def test_sdk_uses_full_catalog():
    assert ImpactVision()._store.count > 100


def test_matched_targets_belong_to_goal():
    for a in map_sdg_alignment(_brightpath(), get_metric_store()):
        assert all(t.startswith(f"{a.goal}.") for t in a.matched_targets), (a.goal, a.matched_targets)


def test_microfinance_is_not_high_on_life_below_water():
    by_goal = {a.goal: a for a in map_sdg_alignment(_brightpath(), get_metric_store())}
    assert by_goal[14].confidence == "low"
    assert by_goal[14].material is False
    assert by_goal[1].material is True  # claimed goal


def test_high_confidence_requires_goal_specific_metric():
    company = Company(name="Generic", description="A company.", reported_metrics={"PI4060": 100})
    for a in map_sdg_alignment(company, get_metric_store()):
        assert a.confidence != "high"


def test_recommendations_skip_non_material_goals_and_rank_themes():
    company = _brightpath()
    store = get_metric_store()
    alignments = map_sdg_alignment(company, store)
    recs = generate_sdg_gap_recommendations(alignments, company, store)
    non_material = {a.goal for a in alignments if not a.material}
    assert not (set(recs) & non_material)
    theme_recs = [r for rs in recs.values() for r in rs if r.startswith("Add impact themes")]
    # Ranking by relevance: not every goal gets the same alphabetical suggestion.
    assert len(set(theme_recs)) > 1 or len(theme_recs) <= 1
