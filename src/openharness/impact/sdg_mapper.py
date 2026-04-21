"""SDG alignment mapping: score a company's alignment to each SDG goal."""

from __future__ import annotations

from pathlib import Path

import yaml

from openharness.impact.database import MetricStore
from openharness.impact.models import Company, SDGAlignment
from openharness.impact.sdg_taxonomy import get_sdg_goal

_DEFAULTS_SECTOR_SDG: dict[str, dict[int, float]] = {
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

_DEFAULTS_KEYWORD_SDG: dict[str, list[tuple[int, float]]] = {
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

_sdg_config_cache: dict | None = None
_core_metrics_per_sdg_cache: dict[int, list[str]] | None = None


def _load_core_metrics_per_sdg() -> dict[int, list[str]]:
    """Load the curated 'core metric set per SDG' from YAML.

    Falls back to an empty dict, in which case sdg_mapper uses the broad
    `store.filter_by_sdg(goal)` set (legacy behaviour, size-biased).
    """
    global _core_metrics_per_sdg_cache
    if _core_metrics_per_sdg_cache is not None:
        return _core_metrics_per_sdg_cache

    candidates = [
        Path(__file__).parent.parent.parent.parent / "data" / "core_metric_set_per_sdg.yaml",
        Path("data/core_metric_set_per_sdg.yaml"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            mapping = (raw or {}).get("core_metrics_by_sdg") or {}
            result: dict[int, list[str]] = {}
            for goal, ids in mapping.items():
                try:
                    g = int(goal)
                except (TypeError, ValueError):
                    continue
                if isinstance(ids, list):
                    result[g] = [str(x).strip().upper() for x in ids if x]
            _core_metrics_per_sdg_cache = result
            return _core_metrics_per_sdg_cache
        except Exception:
            continue

    _core_metrics_per_sdg_cache = {}
    return _core_metrics_per_sdg_cache


def _load_sdg_keywords_config() -> dict:
    """Load SDG keyword config from data/sdg_keywords.yaml with fallback to defaults."""
    global _sdg_config_cache
    if _sdg_config_cache is not None:
        return _sdg_config_cache

    config_paths = [
        Path(__file__).parent.parent.parent.parent / "data" / "sdg_keywords.yaml",
        Path("data/sdg_keywords.yaml"),
    ]
    for path in config_paths:
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    _sdg_config_cache = raw
                    return _sdg_config_cache
            except Exception:
                pass
    _sdg_config_cache = {}
    return _sdg_config_cache


def _get_sector_sdg_relevance() -> dict[str, dict[int, float]]:
    config = _load_sdg_keywords_config()
    raw = config.get("sector_sdg_relevance")
    if not raw or not isinstance(raw, dict):
        return _DEFAULTS_SECTOR_SDG
    result: dict[str, dict[int, float]] = {}
    for sector, mapping in raw.items():
        result[str(sector)] = {int(k): float(v) for k, v in mapping.items()}
    return result


def _get_keyword_sdg_map() -> dict[str, list[tuple[int, float]]]:
    config = _load_sdg_keywords_config()
    raw = config.get("keyword_sdg_map")
    if not raw or not isinstance(raw, dict):
        return _DEFAULTS_KEYWORD_SDG
    result: dict[str, list[tuple[int, float]]] = {}
    for keyword, pairs in raw.items():
        result[str(keyword)] = [(int(p[0]), float(p[1])) for p in pairs]
    return result


_NEGATION_PHRASES = ("not ", "no ", "don't ", "doesn't ", "do not ", "does not ", "without ", "lack ", "unable to ")


def _keyword_not_negated(text: str, keyword: str) -> bool:
    """Check that keyword appears in text without nearby negation within a 30-char window."""
    idx = text.find(keyword)
    while idx >= 0:
        window = text[max(0, idx - 30):idx].lower()
        if not any(neg in window for neg in _NEGATION_PHRASES):
            return True
        idx = text.find(keyword, idx + len(keyword))
    return False


_CONTEXT_WINDOW_SIZE = 80


def _keyword_in_context(text: str, keyword: str) -> bool:
    """Verify that a keyword appears in a substantive context window.

    Returns False if the keyword only appears in very short fragments
    (e.g. table headers, bullet labels) that don't indicate actual alignment.
    """
    idx = text.find(keyword)
    while idx >= 0:
        start = max(0, idx - _CONTEXT_WINDOW_SIZE)
        end = min(len(text), idx + len(keyword) + _CONTEXT_WINDOW_SIZE)
        window = text[start:end]
        words = window.split()
        if len(words) >= 5:
            return True
        idx = text.find(keyword, idx + len(keyword))
    return False


_GEO_SDG_BOOST: dict[str, dict[int, float]] = {
    "africa": {1: 0.3, 2: 0.3, 3: 0.2, 6: 0.2, 7: 0.2},
    "sub-saharan": {1: 0.3, 2: 0.3, 3: 0.2, 6: 0.2, 7: 0.2},
    "south asia": {1: 0.2, 2: 0.2, 4: 0.2, 5: 0.2, 6: 0.2},
    "southeast asia": {1: 0.2, 2: 0.2, 8: 0.2, 13: 0.2, 14: 0.2},
    "latin america": {1: 0.2, 10: 0.2, 15: 0.2, 16: 0.2},
    "pacific": {13: 0.3, 14: 0.3, 15: 0.2},
    "middle east": {6: 0.3, 7: 0.2, 8: 0.2},
    "europe": {7: 0.1, 12: 0.2, 13: 0.2},
    "china": {7: 0.1, 9: 0.2, 11: 0.2, 13: 0.2},
    "india": {1: 0.2, 3: 0.2, 4: 0.2, 6: 0.2, 8: 0.2},
    "kenya": {1: 0.3, 2: 0.3, 3: 0.2, 8: 0.2},
    "nigeria": {1: 0.3, 3: 0.2, 4: 0.2, 7: 0.2},
    "malaysia": {2: 0.2, 8: 0.2, 12: 0.2, 13: 0.2, 15: 0.2},
    "indonesia": {1: 0.2, 2: 0.2, 13: 0.2, 14: 0.2, 15: 0.2},
    "brazil": {1: 0.2, 2: 0.2, 10: 0.2, 15: 0.2},
}


def _infer_sdg_from_description(company: Company) -> dict[int, float]:
    """Infer SDG relevance from company description and sector."""
    text = f"{company.description} {company.sector} {' '.join(company.impact_themes)}".lower()
    inferred: dict[int, float] = {}

    sector_relevance = _get_sector_sdg_relevance()
    for sector_key, sdg_map in sector_relevance.items():
        if sector_key in text:
            for goal, relevance in sdg_map.items():
                inferred[goal] = max(inferred.get(goal, 0), relevance)

    keyword_map = _get_keyword_sdg_map()
    for keyword, sdg_list in keyword_map.items():
        if keyword in text and _keyword_not_negated(text, keyword) and _keyword_in_context(text, keyword):
            for goal, relevance in sdg_list:
                inferred[goal] = max(inferred.get(goal, 0), relevance)

    if company.geography:
        geo_lower = company.geography.lower()
        for geo_key, sdg_boosts in _GEO_SDG_BOOST.items():
            if geo_key in geo_lower:
                for goal, boost in sdg_boosts.items():
                    inferred[goal] = min(1.0, inferred.get(goal, 0) + boost)

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
                    provenance="estimated",
                ))
            continue

        # Use the curated 'core metric set per SDG' when available so that
        # coverage scoring is comparable across goals of different breadth.
        # Fall back to the full filter_by_sdg() set if the YAML is absent.
        core_per_sdg = _load_core_metrics_per_sdg()
        broad_goal_metric_ids = {m.id for m in goal_metrics}
        curated_ids = set(core_per_sdg.get(goal_num, []))
        # Intersect with what the catalog actually knows about, so a stale
        # YAML entry doesn't penalise the company.
        all_known_ids = {m.id for m in store.all_metrics()}
        coverage_set = (curated_ids & all_known_ids) or broad_goal_metric_ids
        scoring_basis = "core_set" if (curated_ids & all_known_ids) else "broad_catalog"

        matched_metric_ids = coverage_set & reported_ids
        # Targets / evidence chain still use the broad set so we surface every
        # SDG target the company has touched.
        matched_targets: set[str] = set()
        evidence_chain: list[dict[str, object]] = []
        for m in goal_metrics:
            if m.id in (broad_goal_metric_ids & reported_ids):
                matched_targets.update(m.sdg_targets)
                for tgt in m.sdg_targets:
                    evidence_chain.append({
                        "claim_text": company.reported_metrics.get(m.id, ""),
                        "metric_id": m.id,
                        "evidence_type": "reported_metric",
                        "sdg_target": tgt,
                        "confidence": 0.8 if len(matched_metric_ids) >= 3 else 0.5,
                    })

        coverage = len(matched_metric_ids) / len(coverage_set) if coverage_set else 0
        metric_score = min(60.0, coverage * 60.0)

        inferred_score = inferred_sdg.get(goal_num, 0) * 25.0
        if inferred_score > 0 and company.description:
            evidence_chain.append({
                "claim_text": company.description[:120],
                "metric_id": "",
                "evidence_type": "description_inference",
                "sdg_target": f"SDG {goal_num}",
                "confidence": round(inferred_sdg.get(goal_num, 0), 2),
            })

        theme_score = 0.0
        if company.impact_themes:
            themes_lower = {t.lower() for t in company.impact_themes}
            goal_themes: set[str] = set()
            for m in goal_metrics:
                goal_themes.update(t.lower() for t in m.impact_themes)
            theme_overlap = themes_lower & goal_themes
            if theme_overlap:
                theme_score = min(15.0, (len(theme_overlap) / max(len(themes_lower), 1)) * 15.0)
                for t in sorted(theme_overlap):
                    evidence_chain.append({
                        "claim_text": f"Theme: {t}",
                        "metric_id": "",
                        "evidence_type": "theme_alignment",
                        "sdg_target": f"SDG {goal_num}",
                        "confidence": round(theme_score / 15.0, 2),
                    })

        total_score = round(metric_score + inferred_score + theme_score, 1)
        confidence = "high" if total_score >= 50 else "medium" if total_score >= 20 else "low"

        if len(matched_metric_ids) >= 3:
            provenance = "evidence-based"
        elif matched_metric_ids:
            provenance = "partial"
        else:
            provenance = "estimated"

        alignments.append(SDGAlignment(
            goal=goal_num,
            goal_name=sdg.name,
            score=total_score,
            matched_targets=sorted(matched_targets),
            matched_metrics=sorted(matched_metric_ids),
            confidence=confidence,
            provenance=provenance,
            evidence_chain=evidence_chain,
            scoring_basis=scoring_basis,
        ))

    alignments.sort(key=lambda a: a.score, reverse=True)
    return alignments


def generate_sdg_gap_recommendations(
    alignments: list[SDGAlignment],
    company: Company,
    store: MetricStore,
) -> dict[int, list[str]]:
    """Generate specific recommendations for strengthening partial SDG alignments.

    For each SDG with score between 5-60 (partial alignment), identify which
    scoring component is weakest and suggest concrete improvement steps.

    Returns: {goal_number: [recommendation_strings]}
    """
    recommendations: dict[int, list[str]] = {}
    reported_ids = set(company.reported_metrics.keys())
    themes_lower = {t.lower() for t in (company.impact_themes or [])}

    for alignment in alignments:
        if alignment.score <= 5 or alignment.score > 60:
            continue

        recs: list[str] = []
        goal_num = alignment.goal

        goal_metrics = store.filter_by_sdg(goal_num)
        goal_metric_ids = {m.id for m in goal_metrics} if goal_metrics else set()
        matched = goal_metric_ids & reported_ids
        unmatched = goal_metric_ids - reported_ids

        if unmatched and len(matched) < 3:
            top_missing = sorted(unmatched)[:3]
            recs.append(
                f"Report metrics {', '.join(top_missing)} to strengthen SDG {goal_num} evidence "
                f"({len(matched)}/{len(goal_metric_ids)} currently tracked)"
            )

        if alignment.provenance == "estimated":
            goal = get_sdg_goal(goal_num)
            goal_name = goal.name if goal else f"Goal {goal_num}"
            recs.append(
                f"Add specific outcome descriptions related to \"{goal_name}\" targets in company documentation"
            )

        if goal_metrics:
            goal_themes: set[str] = set()
            for m in goal_metrics:
                goal_themes.update(t.lower() for t in m.impact_themes)
            missing_themes = goal_themes - themes_lower
            if missing_themes:
                suggest = sorted(missing_themes)[:2]
                recs.append(
                    f"Add impact themes: {', '.join(t.title() for t in suggest)}"
                )

        if alignment.confidence in ("low", "medium") and not alignment.matched_targets:
            goal = get_sdg_goal(goal_num)
            if goal and goal.targets:
                target_ids = [t.id for t in goal.targets[:3]]
                recs.append(
                    f"Map activities to specific SDG targets: {', '.join(target_ids)}"
                )

        if recs:
            recommendations[goal_num] = recs

    return recommendations
