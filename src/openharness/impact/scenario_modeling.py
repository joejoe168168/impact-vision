"""Scenario modeling for impact investment analysis.

Provides what-if analysis: model how changes in metrics, portfolio
composition, or target achievement affect impact scores.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.impact.models import Company


class ScenarioResult(BaseModel):
    """Result of a single scenario simulation."""
    scenario_name: str = ""
    baseline_score: float = 0.0
    projected_score: float = 0.0
    delta: float = 0.0
    pct_change: float = 0.0
    dimension_deltas: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


def model_impact_scenario(
    company: Company,
    *,
    add_metrics: dict[str, str] | None = None,
    remove_metrics: list[str] | None = None,
    change_sector: str | None = None,
    scenario_name: str = "custom",
) -> ScenarioResult:
    """Run a what-if scenario against a company's impact profile.

    Simulates adding/removing metrics or changing sector, then computes
    projected scores vs the baseline to show the delta.
    """
    from openharness.impact.five_dimensions import assess_five_dimensions

    baseline = assess_five_dimensions(company)
    baseline_score = baseline.overall_score

    modified = company.model_copy(deep=True)
    if add_metrics:
        merged = dict(modified.reported_metrics)
        merged.update(add_metrics)
        modified.reported_metrics = merged
    if remove_metrics:
        merged = {k: v for k, v in modified.reported_metrics.items() if k not in remove_metrics}
        modified.reported_metrics = merged
    if change_sector:
        modified.sector = change_sector

    projected = assess_five_dimensions(modified)
    projected_score = projected.overall_score
    delta = round(projected_score - baseline_score, 2)

    dim_deltas: dict[str, float] = {}
    for dim_name in ["what", "who", "how_much", "contribution", "risk"]:
        base_dim = getattr(baseline, dim_name, None)
        proj_dim = getattr(projected, dim_name, None)
        if base_dim is not None and proj_dim is not None:
            dim_deltas[dim_name] = round(proj_dim.score - base_dim.score, 2)

    recs: list[str] = []
    if delta > 0:
        recs.append(f"This scenario improves the overall score by {delta:.2f} points.")
    elif delta < 0:
        recs.append(f"This scenario reduces the overall score by {abs(delta):.2f} points.")
    else:
        recs.append("This scenario has no net effect on the overall score.")

    for dim, d in dim_deltas.items():
        if d > 0.3:
            recs.append(f"Strong improvement in {dim} dimension (+{d:.2f}).")
        elif d < -0.3:
            recs.append(f"Significant decline in {dim} dimension ({d:.2f}).")

    pct = round(delta / max(baseline_score, 0.01) * 100, 1)

    return ScenarioResult(
        scenario_name=scenario_name,
        baseline_score=round(baseline_score, 2),
        projected_score=round(projected_score, 2),
        delta=delta,
        pct_change=pct,
        dimension_deltas=dim_deltas,
        recommendations=recs,
    )


def compare_scenarios(
    company: Company,
    scenarios: list[dict],
) -> list[ScenarioResult]:
    """Run multiple scenarios and return sorted results (best improvement first)."""
    results = []
    for sc in scenarios:
        result = model_impact_scenario(
            company,
            add_metrics=sc.get("add_metrics"),
            remove_metrics=sc.get("remove_metrics"),
            change_sector=sc.get("change_sector"),
            scenario_name=sc.get("name", "unnamed"),
        )
        results.append(result)
    return sorted(results, key=lambda r: r.delta, reverse=True)
