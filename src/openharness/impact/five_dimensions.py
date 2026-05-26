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
    "manufacturing": {"what": 1.2, "who": 1.0, "how_much": 1.2, "contribution": 1.0, "risk": 1.2},
    "transport": {"what": 1.2, "who": 1.0, "how_much": 1.0, "contribution": 1.0, "risk": 1.2},
    "logistics": {"what": 1.2, "who": 1.0, "how_much": 1.0, "contribution": 1.0, "risk": 1.2},
    "construction": {"what": 1.0, "who": 1.0, "how_much": 1.2, "contribution": 1.0, "risk": 1.3},
    "tourism": {"what": 1.0, "who": 1.2, "how_much": 1.0, "contribution": 0.8, "risk": 1.0},
    "retail": {"what": 1.0, "who": 1.2, "how_much": 1.0, "contribution": 0.8, "risk": 1.0},
    "mining": {"what": 0.8, "who": 0.8, "how_much": 1.0, "contribution": 0.8, "risk": 1.5},
    "extractives": {"what": 0.8, "who": 0.8, "how_much": 1.0, "contribution": 0.8, "risk": 1.5},
    "media": {"what": 1.0, "who": 1.2, "how_much": 1.0, "contribution": 1.0, "risk": 0.8},
    "professional services": {"what": 1.0, "who": 1.0, "how_much": 0.8, "contribution": 0.8, "risk": 0.8},
    "waste management": {"what": 1.5, "who": 1.2, "how_much": 1.2, "contribution": 1.2, "risk": 1.2},
    "ict": {"what": 1.2, "who": 1.2, "how_much": 1.0, "contribution": 1.2, "risk": 1.0},
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


_NEGATION_PHRASES = (
    "not ", "no ", "don't ", "doesn't ", "do not ", "does not ",
    "without ", "lack ", "lacks ", "lacking ", "unable to ",
    "anti-", "anti ", "free of ", "free from ", "zero ", "never ",
)


def _get_min_metrics_threshold() -> int:
    config = _load_scoring_config()
    return int(config.get("min_metrics_for_above_baseline", 3))


def __getattr__(name: str):
    """Lazy module-level attribute access to keep config-driven values fresh.

    Earlier versions snapshotted ``MIN_METRICS_FOR_ABOVE_BASELINE`` at import
    time, so subsequent edits to ``data/scoring_config.yaml`` had no effect on
    long-lived processes. Reading the threshold via ``__getattr__`` re-uses the
    config cache while still allowing the cache to be reset for tests.
    """
    if name == "MIN_METRICS_FOR_ABOVE_BASELINE":
        return _get_min_metrics_threshold()
    raise AttributeError(name)


# Compatibility alias evaluated once at import for code paths that captured
# the value into a local. Callers wanting always-current values should access
# the attribute directly each time.
MIN_METRICS_FOR_ABOVE_BASELINE = _get_min_metrics_threshold()


def _keyword_not_negated(text: str, keyword: str) -> bool:
    """Check that keyword appears in text without nearby negation within a 30-char window."""
    idx = text.find(keyword)
    while idx >= 0:
        window = text[max(0, idx - 30):idx].lower()
        if not any(neg in window for neg in _NEGATION_PHRASES):
            return True
        idx = text.find(keyword, idx + len(keyword))
    return False


_ADDITIONALITY_PHRASES = (
    "first-of-kind", "first of kind", "first mover",
    "unique", "novel", "pioneering", "no existing solution",
    "underserved market", "unserved", "underbanked", "unbanked",
    "market gap", "white space", "blue ocean",
    "counterfactual", "would not have happened",
    "catalytic", "catalyst", "crowding in", "crowd-in",
    "additional", "additionality",
    "transformative", "systemic change",
)


def assess_additionality(company: Company) -> dict:
    """Assess contribution/additionality signals from company data.

    Returns a dict with additionality_score (0-5), signals found, and
    a counterfactual prompt for human review.
    """
    text = f"{company.description} {company.sector} {' '.join(company.impact_themes)}".lower()
    signals: list[str] = []
    for phrase in _ADDITIONALITY_PHRASES:
        if phrase in text and _keyword_not_negated(text, phrase):
            signals.append(phrase)

    score = min(5.0, 1.0 + len(signals) * 0.6)

    counterfactual = (
        f"What would happen to {company.name or 'the target beneficiaries'} "
        "without this intervention? Would outcomes be significantly different? "
        "Consider: (1) Are comparable alternatives available in this market? "
        "(2) Is the investor contribution catalytic or substitutional? "
        "(3) What is the depth of engagement beyond capital?"
    )

    return {
        "additionality_score": round(score, 1),
        "signals_found": signals,
        "signal_count": len(signals),
        "counterfactual_prompt": counterfactual,
        "assessment": (
            "Strong additionality signals" if len(signals) >= 3
            else "Moderate additionality signals" if len(signals) >= 1
            else "Weak additionality — consider documenting counterfactual"
        ),
    }


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

    additionality = assess_additionality(company)
    if additionality["signal_count"] >= 2:
        baseline["contribution"] += 0.3
    if additionality["signal_count"] >= 4:
        baseline["contribution"] += 0.3

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
        # No reference set: this dimension is not measurable for the company's
        # theme. Surface the inferred baseline only — do NOT auto-floor at 1.0.
        return DimensionScore(
            dimension=dimension_name,
            score=round(max(0.5, baseline_score), 1),
            metrics_reported=0,
            metrics_available=0,
            gaps=[],
            notes="Estimated from sector/description analysis (no reference metrics available)",
            provenance="estimated",
        )

    ref_ratio = len(matched_in_reference) / available if available > 0 else 0
    # When the theme's reference set is very small (<10 metrics) the per-extra
    # bonus inflates scores quickly; soften it for narrow themes.
    extra_per_metric = 0.05 if available < 10 else 0.1
    extra_bonus = (
        min(0.5, (total_reported_dim - len(matched_in_reference)) * extra_per_metric)
        if total_reported_dim > len(matched_in_reference)
        else 0
    )
    metric_score = ref_ratio * 4.5 + extra_bonus + (0.5 if total_reported_dim > 0 else 0)
    score = min(5.0, max(metric_score, baseline_score))

    # Per-dimension floor: until you've reported at least MIN_METRICS_FOR_ABOVE_BASELINE
    # metrics that hit THIS dimension's reference set, cap its score at 2.5 even if
    # the baseline + extra-bonus interaction tries to push it higher.
    if len(matched_in_reference) < MIN_METRICS_FOR_ABOVE_BASELINE and score > 2.5:
        score = 2.5

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


_ADVERSE_IMPACT_PATTERNS = (
    "adverse impact", "negative impact", "harm", "pollution", "displacement",
    "deforestation", "child labor", "forced labor", "corruption", "bribery",
    "toxic", "hazardous", "contamination", "exploitation",
)

_MITIGATION_PATTERNS = (
    "mitigation", "mitigate", "remediation", "remedy", "safeguard",
    "prevention", "grievance mechanism", "corrective action",
    "environmental management plan", "social impact assessment",
)


def _compute_negative_impact_penalty(company: Company) -> float:
    """Compute a risk dimension penalty (0-1.5) for adverse impacts without mitigation.

    The match is negation-aware so that a company describing itself as
    "free of forced labor" or "without harmful side effects" is not penalised
    as if it acknowledged those harms.
    """
    text = f"{company.description} {company.sector} {' '.join(company.impact_themes)}".lower()
    adverse_count = sum(
        1 for p in _ADVERSE_IMPACT_PATTERNS
        if p in text and _keyword_not_negated(text, p)
    )
    mitigation_count = sum(1 for p in _MITIGATION_PATTERNS if p in text)

    if adverse_count == 0:
        return 0.0
    unmitigated = max(0, adverse_count - mitigation_count)
    return min(1.5, unmitigated * 0.3)


def _compute_exclusion_penalty(company: Company) -> float:
    """Compute a risk penalty from exclusion flags."""
    if not company.exclusion_flags:
        return 0.0
    return min(1.0, len(company.exclusion_flags) * 0.5)


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

    contribution_duration = _score_dimension(
        "Contribution (Duration)", "contribution_duration", reported_ids, store, theme,
        baseline.get("contribution", 0.5),
    )

    contribution_combined = DimensionScore(
        dimension="Contribution",
        score=round(
            (scores["contribution_depth"].score + contribution_duration.score) / 2.0,
            1,
        ),
        metrics_reported=scores["contribution_depth"].metrics_reported + contribution_duration.metrics_reported,
        metrics_available=scores["contribution_depth"].metrics_available + contribution_duration.metrics_available,
        gaps=scores["contribution_depth"].gaps[:5] + contribution_duration.gaps[:5],
        notes=f"Depth={scores['contribution_depth'].score}, Duration={contribution_duration.score}",
    )

    neg_penalty = _compute_negative_impact_penalty(company)
    excl_penalty = _compute_exclusion_penalty(company)
    total_penalty = neg_penalty + excl_penalty
    if total_penalty > 0:
        risk_score_obj = scores["risk"]
        risk_score_obj.score = round(max(0.5, risk_score_obj.score - total_penalty), 1)
        penalty_notes = []
        if neg_penalty > 0:
            penalty_notes.append(f"adverse impact penalty -{neg_penalty:.1f}")
        if excl_penalty > 0:
            penalty_notes.append(f"exclusion flag penalty -{excl_penalty:.1f}")
        risk_score_obj.notes += f" ({'; '.join(penalty_notes)})"

    total_metrics = len(reported_ids)
    if 0 < total_metrics < MIN_METRICS_FOR_ABOVE_BASELINE:
        cap = 2.5
        for dim_score in [scores["what"], scores["who"], contribution_combined, scores["risk"]]:
            if dim_score.score > cap:
                dim_score.score = cap
                dim_score.notes += f" (capped: report ≥{MIN_METRICS_FOR_ABOVE_BASELINE} metrics to unlock higher scores)"
        if how_much_combined.score > cap:
            how_much_combined.score = cap
            how_much_combined.notes += f" (capped: report ≥{MIN_METRICS_FOR_ABOVE_BASELINE} metrics to unlock higher scores)"

    overall = round(
        (scores["what"].score + scores["who"].score + how_much_combined.score + contribution_combined.score + scores["risk"].score) / 5.0,
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
    if contribution_combined.score < 2:
        recommendations.append("Assess CONTRIBUTION: establish counterfactual or benchmark comparison")
    if scores["risk"].score < 2:
        recommendations.append("Evaluate RISK: assess evidence risk, execution risk, and external risk factors")

    all_dims = [scores["what"], scores["who"], how_much_combined, contribution_combined, scores["risk"]]
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
        contribution=contribution_combined,
        risk=scores["risk"],
        overall_score=overall,
        overall_grade=_grade_from_score(overall),
        overall_provenance=overall_provenance,
        impact_theme=theme or "",
        recommendations=recommendations,
    )
