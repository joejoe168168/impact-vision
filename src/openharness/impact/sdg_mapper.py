"""SDG alignment mapping: score a company's alignment to each SDG goal."""

from __future__ import annotations

from openharness.impact.database import MetricStore
from openharness.impact.models import Company, SDGAlignment
from openharness.impact.sdg_taxonomy import get_sdg_goal


def map_sdg_alignment(
    company: Company,
    store: MetricStore,
    goals: list[int] | None = None,
) -> list[SDGAlignment]:
    """Score a company's SDG alignment per goal.

    Algorithm:
    1. For each SDG goal, find all IRIS+ metrics mapped to it
    2. Check which of those are reported by the company
    3. Also check if the company claims that SDG goal
    4. Compute alignment score (0-100):
       - Up to 60 points from metric coverage
       - Up to 20 points from having relevant impact themes
       - Up to 20 points from metric depth (definitions, calculations present)
    """
    target_goals = goals or list(range(1, 18))
    reported_ids = set(company.reported_metrics.keys())
    alignments: list[SDGAlignment] = []

    for goal_num in target_goals:
        sdg = get_sdg_goal(goal_num)
        if sdg is None:
            continue

        goal_metrics = store.filter_by_sdg(goal_num)
        if not goal_metrics:
            if goal_num in company.sdg_claims:
                alignments.append(SDGAlignment(
                    goal=goal_num,
                    goal_name=sdg.name,
                    score=10.0,
                    confidence="low",
                ))
            continue

        goal_metric_ids = {m.id for m in goal_metrics}
        matched_metric_ids = goal_metric_ids & reported_ids
        matched_targets: set[str] = set()
        for m in goal_metrics:
            if m.id in matched_metric_ids:
                matched_targets.update(m.sdg_targets)

        # Score: metric coverage (up to 60)
        coverage = len(matched_metric_ids) / len(goal_metric_ids) if goal_metric_ids else 0
        metric_score = min(60.0, coverage * 60.0)

        # Score: theme alignment (up to 20)
        theme_score = 0.0
        if company.impact_themes:
            themes_lower = {t.lower() for t in company.impact_themes}
            goal_themes: set[str] = set()
            for m in goal_metrics:
                goal_themes.update(t.lower() for t in m.impact_themes)
            theme_overlap = themes_lower & goal_themes
            if theme_overlap:
                theme_score = min(20.0, (len(theme_overlap) / max(len(themes_lower), 1)) * 20.0)

        # Score: data depth bonus (up to 20)
        depth_score = 0.0
        if matched_metric_ids:
            with_definition = sum(
                1 for mid in matched_metric_ids
                if (m_obj := store.get(mid)) and m_obj.definition
            )
            depth_score = min(20.0, (with_definition / len(matched_metric_ids)) * 20.0)

        total_score = round(metric_score + theme_score + depth_score, 1)
        confidence = "high" if total_score >= 50 else "medium" if total_score >= 20 else "low"

        alignments.append(SDGAlignment(
            goal=goal_num,
            goal_name=sdg.name,
            score=total_score,
            matched_targets=sorted(matched_targets),
            matched_metrics=sorted(matched_metric_ids),
            confidence=confidence,
        ))

    alignments.sort(key=lambda a: a.score, reverse=True)
    return alignments
