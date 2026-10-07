"""The per-SDG core metric sets cite real, goal-tagged, correctly named IRIS+ metrics."""

from __future__ import annotations

import re

from openharness.impact._paths import data_path
from openharness.impact.database import get_metric_store


def _entries():
    goal = None
    in_map = False
    for line in data_path("core_metric_set_per_sdg.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith("core_metrics_by_sdg:"):
            in_map = True
            continue
        if not in_map:
            continue
        m = re.match(r"\s+(\d+):", line)
        if m:
            goal = int(m.group(1))
            continue
        m = re.match(r"\s+-\s+([A-Z]{2}\d{4})\s+#\s+(.+?)\s*$", line)
        if m:
            yield goal, m.group(1), m.group(2)


def test_every_core_metric_exists_is_goal_tagged_and_named() -> None:
    store = get_metric_store()
    entries = list(_entries())
    assert len(entries) > 100
    for goal, metric_id, comment in entries:
        metric = store.get(metric_id)
        assert metric is not None, f"SDG {goal}: {metric_id} not in IRIS+"
        assert goal in metric.sdg_goals, f"SDG {goal}: {metric_id} ({metric.name}) is not tagged to the goal"
        assert comment == metric.name, f"SDG {goal}: {metric_id} comment {comment!r} != {metric.name!r}"


def test_clean_energy_goals_count_avoided_emissions_not_scope_1() -> None:
    goals = {}
    for goal, metric_id, _ in _entries():
        goals.setdefault(goal, set()).add(metric_id)
    assert "OI2764" in goals[7] and "OI2764" in goals[13]   # GHG emissions avoided
    assert "OI4112" not in goals[7]                          # Scope 1 is not clean-energy evidence


def test_footprint_disclosure_does_not_drive_sdg_13() -> None:
    from openharness.impact.models import Company
    from openharness.impact.sdg_mapper import map_sdg_alignment

    fintech = Company(
        name="Lender", sector="fintech", description="Digital microfinance for women micro-entrepreneurs.",
        sdg_claims=[1, 5], reported_metrics={"OI1479": "120 tCO2e", "OI4112": "80 tCO2e", "PI4060": "45000"},
    )
    scores = {a.goal: a for a in map_sdg_alignment(fintech, get_metric_store())}
    assert 13 not in {g for g, a in scores.items() if a.provenance == "evidence-based"}
    assert scores[13].score < max(scores[1].score, scores[5].score)
