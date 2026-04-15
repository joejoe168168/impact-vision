"""5-Dimension Impact scoring logic (What/Who/How Much/Contribution/Risk)."""

from __future__ import annotations

from openharness.impact.database import MetricStore
from openharness.impact.models import Company, DimensionScore, FiveDimensionScore


def _grade_from_score(score: float) -> str:
    if score >= 4.5:
        return "A"
    if score >= 3.5:
        return "B+"
    if score >= 3.0:
        return "B"
    if score >= 2.5:
        return "B-"
    if score >= 2.0:
        return "C+"
    if score >= 1.5:
        return "C"
    if score >= 1.0:
        return "D"
    return "F"


def _score_dimension(
    dimension_name: str,
    field_name: str,
    reported_ids: set[str],
    store: MetricStore,
    theme: str | None,
) -> DimensionScore:
    """Score a single dimension based on which metrics are reported.

    Uses a hybrid approach: looks at all metrics with the correct dimension tag
    that the company has reported (regardless of theme), plus theme-specific
    metrics as the reference set for gap identification.
    """
    all_dim_metrics = store.filter_by_dimension(field_name.replace("how_much_", ""))
    if not all_dim_metrics:
        all_dim_metrics = [m for m in store.all_metrics() if getattr(m.dimensions, field_name, False)]

    all_dim_ids = {m.id for m in all_dim_metrics}
    reported_with_dim = all_dim_ids & reported_ids

    if theme:
        theme_candidates = store.filter_by_theme(theme)
        theme_dim = [m for m in theme_candidates if getattr(m.dimensions, field_name, False)]
        theme_dim_ids = {m.id for m in theme_dim}
        reference_set = theme_dim_ids if theme_dim_ids else all_dim_ids
    else:
        reference_set = all_dim_ids

    matched_in_reference = reference_set & reported_ids
    total_reported_dim = len(reported_with_dim)
    available = len(reference_set) if reference_set else len(all_dim_ids)

    if available == 0:
        return DimensionScore(
            dimension=dimension_name,
            score=1.0,
            metrics_reported=0,
            metrics_available=0,
            gaps=[],
            notes=f"No {dimension_name} metrics found",
        )

    # Score: credit for both theme-specific and any dimension-tagged metrics reported
    # Primary score from reference set coverage, bonus for extra dimension metrics
    ref_ratio = len(matched_in_reference) / available if available > 0 else 0
    extra_bonus = min(0.5, (total_reported_dim - len(matched_in_reference)) * 0.1) if total_reported_dim > len(matched_in_reference) else 0
    score = min(5.0, ref_ratio * 4.5 + extra_bonus + (0.5 if total_reported_dim > 0 else 0))

    gap_ids = sorted(reference_set - reported_ids)[:10]
    gaps = [f"{mid} ({store.get(mid).name if store.get(mid) else mid})" for mid in gap_ids]

    return DimensionScore(
        dimension=dimension_name,
        score=round(score, 1),
        metrics_reported=total_reported_dim,
        metrics_available=available,
        gaps=gaps,
        notes=f"Reporting {total_reported_dim} metrics ({len(matched_in_reference)} theme-specific, {available} available)",
    )


def assess_five_dimensions(
    company: Company,
    store: MetricStore,
    theme: str | None = None,
) -> FiveDimensionScore:
    """Run a 5-Dimension impact assessment for a company."""
    reported_ids = set(company.reported_metrics.keys())

    if theme is None and company.impact_themes:
        theme = company.impact_themes[0]

    dim_fields = [
        ("What", "what"),
        ("Who", "who"),
        ("How Much (Scale)", "how_much_scale"),
        ("Contribution", "contribution_depth"),
        ("Risk", "risk"),
    ]

    scores: dict[str, DimensionScore] = {}
    for display_name, field_name in dim_fields:
        scores[field_name] = _score_dimension(
            display_name, field_name, reported_ids, store, theme
        )

    how_much_depth = _score_dimension("How Much (Depth)", "how_much_depth", reported_ids, store, theme)
    how_much_duration = _score_dimension("How Much (Duration)", "how_much_duration", reported_ids, store, theme)

    how_much_combined = DimensionScore(
        dimension="How Much",
        score=round(
            (scores["how_much_scale"].score + how_much_depth.score + how_much_duration.score) / 3.0,
            1,
        ),
        metrics_reported=scores["how_much_scale"].metrics_reported + how_much_depth.metrics_reported + how_much_duration.metrics_reported,
        metrics_available=scores["how_much_scale"].metrics_available + how_much_depth.metrics_available + how_much_duration.metrics_available,
        gaps=scores["how_much_scale"].gaps[:5] + how_much_depth.gaps[:3] + how_much_duration.gaps[:2],
        notes=f"Scale={scores['how_much_scale'].score}, Depth={how_much_depth.score}, Duration={how_much_duration.score}",
    )

    overall = round(
        (scores["what"].score + scores["who"].score + how_much_combined.score + scores["contribution_depth"].score + scores["risk"].score) / 5.0,
        1,
    )

    recommendations: list[str] = []
    if scores["what"].score < 2:
        recommendations.append("Strengthen outcome measurement: define WHAT outcomes you contribute to with specific metrics")
    if scores["who"].score < 2:
        recommendations.append("Define WHO: specify target demographics, geography, and stakeholder characteristics")
    if how_much_combined.score < 2:
        recommendations.append("Measure HOW MUCH: track scale (# stakeholders), depth (degree of change), and duration")
    if scores["contribution_depth"].score < 2:
        recommendations.append("Assess CONTRIBUTION: establish counterfactual or benchmark comparison")
    if scores["risk"].score < 2:
        recommendations.append("Evaluate RISK: assess evidence risk, execution risk, and external risk factors")

    return FiveDimensionScore(
        what=scores["what"],
        who=scores["who"],
        how_much=how_much_combined,
        contribution=scores["contribution_depth"],
        risk=scores["risk"],
        overall_score=overall,
        overall_grade=_grade_from_score(overall),
        impact_theme=theme or "",
        recommendations=recommendations,
    )
