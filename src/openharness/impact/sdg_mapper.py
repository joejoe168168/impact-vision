"""SDG alignment mapping: score a company's alignment to each SDG goal."""

from __future__ import annotations

from openharness.impact.database import MetricStore
from openharness.impact.models import Company, SDGAlignment
from openharness.impact.sdg_taxonomy import get_sdg_goal

_SECTOR_SDG_RELEVANCE: dict[str, dict[int, float]] = {
    "agriculture": {1: 0.6, 2: 0.9, 3: 0.3, 6: 0.5, 8: 0.5, 12: 0.7, 13: 0.6, 15: 0.7},
    "livestock": {1: 0.5, 2: 0.8, 3: 0.3, 6: 0.4, 8: 0.4, 12: 0.6, 13: 0.7, 15: 0.5},
    "healthcare": {1: 0.4, 3: 0.9, 5: 0.3, 8: 0.4, 10: 0.5, 17: 0.3},
    "health": {1: 0.4, 3: 0.9, 5: 0.3, 8: 0.4, 10: 0.5, 17: 0.3},
    "energy": {7: 0.9, 8: 0.5, 9: 0.5, 11: 0.4, 13: 0.8},
    "solar": {7: 0.9, 9: 0.4, 11: 0.4, 13: 0.8},
    "education": {4: 0.9, 5: 0.5, 8: 0.6, 10: 0.5},
    "fintech": {1: 0.6, 5: 0.4, 8: 0.7, 9: 0.5, 10: 0.6},
    "financial": {1: 0.6, 5: 0.4, 8: 0.7, 9: 0.5, 10: 0.6},
    "water": {3: 0.4, 6: 0.9, 11: 0.4, 14: 0.5},
    "technology": {4: 0.3, 8: 0.5, 9: 0.7, 10: 0.4, 11: 0.4},
    "real estate": {7: 0.3, 9: 0.3, 11: 0.8, 13: 0.4},
    "housing": {1: 0.4, 7: 0.3, 11: 0.8},
}

_KEYWORD_SDG_MAP: dict[str, list[tuple[int, float]]] = {
    "poverty": [(1, 0.8)],
    "hunger": [(2, 0.8)],
    "food": [(2, 0.7), (12, 0.3)],
    "farm": [(2, 0.6), (15, 0.3)],
    "health": [(3, 0.7)],
    "medical": [(3, 0.7)],
    "education": [(4, 0.8)],
    "school": [(4, 0.7)],
    "training": [(4, 0.5)],
    "gender": [(5, 0.7)],
    "women": [(5, 0.7)],
    "water": [(6, 0.8)],
    "sanitation": [(6, 0.7)],
    "energy": [(7, 0.7)],
    "solar": [(7, 0.8), (13, 0.4)],
    "renewable": [(7, 0.8), (13, 0.5)],
    "employment": [(8, 0.6)],
    "jobs": [(8, 0.6)],
    "livelihood": [(1, 0.5), (8, 0.6)],
    "infrastructure": [(9, 0.6)],
    "innovation": [(9, 0.5)],
    "inequality": [(10, 0.7)],
    "inclusion": [(10, 0.5), (5, 0.3)],
    "urban": [(11, 0.6)],
    "city": [(11, 0.5)],
    "waste": [(12, 0.6)],
    "recycling": [(12, 0.7)],
    "sustainable": [(12, 0.4)],
    "climate": [(13, 0.8)],
    "carbon": [(13, 0.7)],
    "emission": [(13, 0.7)],
    "ocean": [(14, 0.7)],
    "marine": [(14, 0.7)],
    "forest": [(15, 0.7)],
    "biodiversity": [(15, 0.7)],
    "land": [(15, 0.4)],
    "justice": [(16, 0.6)],
    "governance": [(16, 0.5)],
    "partnership": [(17, 0.5)],
    "rural": [(1, 0.4), (2, 0.3), (11, 0.3)],
    "smallholder": [(1, 0.5), (2, 0.6)],
    "pollution": [(6, 0.3), (13, 0.4), (14, 0.3), (15, 0.3)],
    "pig": [(2, 0.5), (12, 0.4)],
    "livestock": [(2, 0.6), (12, 0.5), (13, 0.4)],
    "poultry": [(2, 0.5)],
}


def _infer_sdg_from_description(company: Company) -> dict[int, float]:
    """Infer SDG relevance from company description and sector."""
    text = f"{company.description} {company.sector} {' '.join(company.impact_themes)}".lower()
    inferred: dict[int, float] = {}

    for sector_key, sdg_map in _SECTOR_SDG_RELEVANCE.items():
        if sector_key in text:
            for goal, relevance in sdg_map.items():
                inferred[goal] = max(inferred.get(goal, 0), relevance)

    for keyword, sdg_list in _KEYWORD_SDG_MAP.items():
        if keyword in text:
            for goal, relevance in sdg_list:
                inferred[goal] = max(inferred.get(goal, 0), relevance)

    for goal_num in company.sdg_claims:
        inferred[goal_num] = max(inferred.get(goal_num, 0), 0.7)

    return inferred


def map_sdg_alignment(
    company: Company,
    store: MetricStore,
    goals: list[int] | None = None,
) -> list[SDGAlignment]:
    """Score a company's SDG alignment per goal.

    Uses a hybrid approach:
    1. Hard data: reported metrics mapped to SDGs (up to 60 pts)
    2. Description inference: sector and keyword analysis (up to 25 pts)
    3. Theme alignment (up to 15 pts)
    """
    target_goals = goals or list(range(1, 18))
    reported_ids = set(company.reported_metrics.keys())
    inferred_sdg = _infer_sdg_from_description(company)
    alignments: list[SDGAlignment] = []

    for goal_num in target_goals:
        sdg = get_sdg_goal(goal_num)
        if sdg is None:
            continue

        goal_metrics = store.filter_by_sdg(goal_num)
        if not goal_metrics:
            relevance = inferred_sdg.get(goal_num, 0)
            if relevance > 0 or goal_num in company.sdg_claims:
                score = max(10.0, round(relevance * 35, 1))
                alignments.append(SDGAlignment(
                    goal=goal_num,
                    goal_name=sdg.name,
                    score=score,
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

        # Score: description/sector inference (up to 25)
        inferred_score = inferred_sdg.get(goal_num, 0) * 25.0

        # Score: theme alignment (up to 15)
        theme_score = 0.0
        if company.impact_themes:
            themes_lower = {t.lower() for t in company.impact_themes}
            goal_themes: set[str] = set()
            for m in goal_metrics:
                goal_themes.update(t.lower() for t in m.impact_themes)
            theme_overlap = themes_lower & goal_themes
            if theme_overlap:
                theme_score = min(15.0, (len(theme_overlap) / max(len(themes_lower), 1)) * 15.0)

        total_score = round(metric_score + inferred_score + theme_score, 1)
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
