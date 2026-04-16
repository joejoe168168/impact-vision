"""5-Dimension Impact scoring logic (What/Who/How Much/Contribution/Risk)."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from openharness.impact.database import MetricStore
from openharness.impact.models import Company, DimensionScore, FiveDimensionScore

logger = logging.getLogger(__name__)

_DEFAULTS_SECTOR_BASELINE: dict[str, dict[str, float]] = {
    "agriculture": {"what": 1.5, "who": 1.5, "how_much": 1.2, "contribution": 1.0, "risk": 1.0},
    "livestock": {"what": 1.3, "who": 1.2, "how_much": 1.0, "contribution": 0.8, "risk": 1.2},
    "healthcare": {"what": 2.0, "who": 2.0, "how_much": 1.5, "contribution": 1.5, "risk": 1.0},
    "health": {"what": 2.0, "who": 2.0, "how_much": 1.5, "contribution": 1.5, "risk": 1.0},
    "energy": {"what": 1.8, "who": 1.5, "how_much": 1.5, "contribution": 1.5, "risk": 1.0},
    "education": {"what": 2.0, "who": 2.0, "how_much": 1.5, "contribution": 1.2, "risk": 0.8},
    "fintech": {"what": 1.5, "who": 1.8, "how_much": 1.5, "contribution": 1.5, "risk": 1.2},
    "financial": {"what": 1.5, "who": 1.8, "how_much": 1.5, "contribution": 1.5, "risk": 1.2},
    "water": {"what": 2.0, "who": 1.8, "how_much": 1.5, "contribution": 1.5, "risk": 1.0},
    "technology": {"what": 1.2, "who": 1.2, "how_much": 1.0, "contribution": 1.0, "risk": 0.8},
    "real estate": {"what": 1.0, "who": 1.0, "how_much": 1.0, "contribution": 0.8, "risk": 0.8},
}

_DEFAULTS_KEYWORD_BOOST: dict[str, dict[str, float]] = {
    "poverty": {"what": 0.5, "who": 0.5},
    "food": {"what": 0.5, "who": 0.3},
    "hunger": {"what": 0.5, "who": 0.5},
    "smallholder": {"who": 0.5, "how_much": 0.3},
    "rural": {"who": 0.3, "how_much": 0.2},
    "climate": {"what": 0.3, "risk": 0.3},
    "carbon": {"what": 0.3, "risk": 0.2},
    "emission": {"what": 0.3, "risk": 0.3},
    "pollution": {"risk": 0.5, "what": 0.2},
    "women": {"who": 0.5},
    "gender": {"who": 0.5},
    "community": {"who": 0.4, "how_much": 0.2},
    "sustainable": {"contribution": 0.3},
    "innovation": {"contribution": 0.3, "what": 0.2},
    "evidence": {"risk": -0.3},
}

_config_cache: dict | None = None


def _load_scoring_config() -> dict:
    """Load scoring config from data/scoring_config.yaml, falling back to hardcoded defaults."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_paths = [
        Path(__file__).parent.parent.parent.parent / "data" / "scoring_config.yaml",
        Path("data/scoring_config.yaml"),
    ]
    for path in config_paths:
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    _config_cache = raw
                    logger.debug("Loaded scoring config from %s", path)
                    return _config_cache
            except Exception:
                logger.warning("Failed to parse %s, using defaults", path)

    _config_cache = {}
    return _config_cache


def _get_sector_baselines() -> dict[str, dict[str, float]]:
    config = _load_scoring_config()
    return config.get("sector_baselines", _DEFAULTS_SECTOR_BASELINE)


def _get_keyword_boosts() -> dict[str, dict[str, float]]:
    config = _load_scoring_config()
    return config.get("keyword_dimension_boosts", _DEFAULTS_KEYWORD_BOOST)


_NEGATION_PHRASES = ("not ", "no ", "don't ", "doesn't ", "do not ", "does not ", "without ", "lack ", "unable to ")
MIN_METRICS_FOR_ABOVE_BASELINE = 3


def _keyword_not_negated(text: str, keyword: str) -> bool:
    """Check that keyword appears in text without nearby negation within a 30-char window."""
    idx = text.find(keyword)
    while idx >= 0:
        window = text[max(0, idx - 30):idx].lower()
        if not any(neg in window for neg in _NEGATION_PHRASES):
            return True
        idx = text.find(keyword, idx + len(keyword))
    return False


def _infer_baseline(company: Company) -> dict[str, float]:
    """Infer baseline 5D scores from sector and description keywords."""
    text = f"{company.description} {company.sector} {' '.join(company.impact_themes)}".lower()
    baseline: dict[str, float] = {"what": 0.5, "who": 0.5, "how_much": 0.5, "contribution": 0.5, "risk": 0.5}

    for sector_key, scores in _get_sector_baselines().items():
        if sector_key in text:
            for dim, val in scores.items():
                baseline[dim] = max(baseline[dim], val)

    for keyword, boosts in _get_keyword_boosts().items():
        if keyword in text and _keyword_not_negated(text, keyword):
            for dim, val in boosts.items():
                baseline[dim] = baseline[dim] + val

    return {dim: min(2.5, max(0.5, val)) for dim, val in baseline.items()}


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
    baseline_score: float = 0.5,
) -> DimensionScore:
    """Score a single dimension combining reported metrics and inferred baseline."""
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
            score=round(max(1.0, baseline_score), 1),
            metrics_reported=0,
            metrics_available=0,
            gaps=[],
            notes="Estimated from sector/description analysis",
            provenance="estimated",
        )

    ref_ratio = len(matched_in_reference) / available if available > 0 else 0
    extra_bonus = min(0.5, (total_reported_dim - len(matched_in_reference)) * 0.1) if total_reported_dim > len(matched_in_reference) else 0
    metric_score = ref_ratio * 4.5 + extra_bonus + (0.5 if total_reported_dim > 0 else 0)
    score = min(5.0, max(metric_score, baseline_score))

    gap_ids = sorted(reference_set - reported_ids)[:10]
    gaps = [f"{mid} ({store.get(mid).name if store.get(mid) else mid})" for mid in gap_ids]

    if total_reported_dim > 0:
        notes = f"Reporting {total_reported_dim} metrics ({len(matched_in_reference)} theme-specific, {available} available)"
        provenance = "evidence-based" if total_reported_dim >= 3 else "partial"
    else:
        notes = f"Estimated from sector/description ({available} metrics available to track)"
        provenance = "estimated"

    return DimensionScore(
        dimension=dimension_name,
        score=round(score, 1),
        metrics_reported=total_reported_dim,
        metrics_available=available,
        gaps=gaps,
        notes=notes,
        provenance=provenance,
    )


def assess_five_dimensions(
    company: Company,
    store: MetricStore,
    theme: str | None = None,
) -> FiveDimensionScore:
    """Run a 5-Dimension impact assessment for a company."""
    reported_ids = set(company.reported_metrics.keys())
    baseline = _infer_baseline(company)

    if theme is None and company.impact_themes:
        theme = company.impact_themes[0]

    dim_fields = [
        ("What", "what", "what"),
        ("Who", "who", "who"),
        ("How Much (Scale)", "how_much_scale", "how_much"),
        ("Contribution", "contribution_depth", "contribution"),
        ("Risk", "risk", "risk"),
    ]

    scores: dict[str, DimensionScore] = {}
    for display_name, field_name, baseline_key in dim_fields:
        scores[field_name] = _score_dimension(
            display_name, field_name, reported_ids, store, theme,
            baseline_score=baseline.get(baseline_key, 0.5),
        )

    how_much_depth = _score_dimension("How Much (Depth)", "how_much_depth", reported_ids, store, theme, baseline.get("how_much", 0.5))
    how_much_duration = _score_dimension("How Much (Duration)", "how_much_duration", reported_ids, store, theme, baseline.get("how_much", 0.5))

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

    total_metrics = len(reported_ids)
    if 0 < total_metrics < MIN_METRICS_FOR_ABOVE_BASELINE:
        cap = 2.5
        for dim_score in [scores["what"], scores["who"], scores["contribution_depth"], scores["risk"]]:
            if dim_score.score > cap:
                dim_score.score = cap
                dim_score.notes += f" (capped: report ≥{MIN_METRICS_FOR_ABOVE_BASELINE} metrics to unlock higher scores)"
        if how_much_combined.score > cap:
            how_much_combined.score = cap
            how_much_combined.notes += f" (capped: report ≥{MIN_METRICS_FOR_ABOVE_BASELINE} metrics to unlock higher scores)"

    overall = round(
        (scores["what"].score + scores["who"].score + how_much_combined.score + scores["contribution_depth"].score + scores["risk"].score) / 5.0,
        1,
    )

    recommendations: list[str] = []
    has_metrics = bool(reported_ids)
    if not has_metrics:
        recommendations.append("Start tracking IRIS+ metrics to strengthen evidence and move beyond estimated scores")
    elif total_metrics < MIN_METRICS_FOR_ABOVE_BASELINE:
        recommendations.append(f"Report at least {MIN_METRICS_FOR_ABOVE_BASELINE} IRIS+ metrics to unlock scores above 2.5 (currently reporting {total_metrics})")
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

    all_dims = [scores["what"], scores["who"], how_much_combined, scores["contribution_depth"], scores["risk"]]
    prov_set = {d.provenance for d in all_dims}
    if prov_set == {"evidence-based"}:
        overall_provenance = "evidence-based"
    elif "evidence-based" in prov_set or "partial" in prov_set:
        overall_provenance = "partial"
    else:
        overall_provenance = "estimated"

    return FiveDimensionScore(
        what=scores["what"],
        who=scores["who"],
        how_much=how_much_combined,
        contribution=scores["contribution_depth"],
        risk=scores["risk"],
        overall_score=overall,
        overall_grade=_grade_from_score(overall),
        overall_provenance=overall_provenance,
        impact_theme=theme or "",
        recommendations=recommendations,
    )
