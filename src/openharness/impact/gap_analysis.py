"""Gap analysis: compare reported metrics against IRIS+ Core Metric Sets."""

from __future__ import annotations

from openharness.impact.database import MetricStore
from openharness.impact.models import Company

_DIMENSION_LABELS = {
    "what": "What",
    "who": "Who",
    "how_much_scale": "How Much (Scale)",
    "how_much_depth": "How Much (Depth)",
    "how_much_duration": "How Much (Duration)",
    "contribution_depth": "Contribution (Depth)",
    "contribution_duration": "Contribution (Duration)",
    "risk": "Risk",
}

_5D_GROUP = {
    "what": "What",
    "who": "Who",
    "how_much_scale": "How Much",
    "how_much_depth": "How Much",
    "how_much_duration": "How Much",
    "contribution_depth": "Contribution",
    "contribution_duration": "Contribution",
    "risk": "Risk",
}

_FALLBACK_DIMENSION: dict[str, str] = {
    # Resource / impact signals a metric conveys even when the catalog has no
    # explicit dimension tags. Populated from the Core Metric Set comments
    # below — keeps the report useful when the catalog is older.
    "OD8350": "What",
    "OI4753": "Risk",
    "PI4060": "Who",
    "OI8869": "Who",
    "OI1571": "Who",
    "OI6213": "Who",
    "FP3021": "How Much",
    "FP4761": "How Much",
    "OI1479": "Risk",
    "OI4112": "Risk",
    "OD4091": "Contribution",
    "OI4732": "Contribution",
    "OI1582": "What",
    "OI1075": "Contribution",
    "OI5049": "Contribution",
    "OI4324": "Contribution",
}

_FALLBACK_UNIT: dict[str, str] = {
    "OI1479": "tCO2e / year",
    "OI4112": "tCO2e / year",
    "PI4060": "count of individuals",
    "OI8869": "count of employees",
    "OI1571": "count of female managers",
    "OI6213": "count of female employees",
    "FP3021": "reporting currency",
    "FP4761": "percentage",
    "OI1582": "ratio (highest / lowest wage)",
    "OI1075": "count of directors",
    "OD8350": "structured description",
    "OI4753": "Yes / No policy attestation",
    "OI4732": "Yes / No reporting attestation",
    "OI5049": "Yes / No feedback-system attestation",
    "OI4324": "Yes / No policy attestation",
    "OD4091": "free-text target description",
}


def _clip(text: str, limit: int) -> str:
    """Truncate ``text`` to ``limit`` chars on a word boundary, adding an ellipsis.

    Avoids ragged mid-word cuts (e.g. "...passed th") produced by a raw slice so
    that every consumer of this dict — the HTML report, JSON and CSV exports —
    receives readable text. Falls back to a hard slice only when there is no
    nearby space.
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip()
    sp = cut.rfind(" ")
    if sp > limit * 0.6:
        cut = cut[:sp].rstrip()
    return cut.rstrip(",;:.") + "\u2026"


def _metric_info(metric_id: str, metric_obj) -> dict:
    """Build a rich, renderable dict describing a Core Metric Set entry."""
    name = metric_obj.name if metric_obj else metric_id
    definition = _clip(metric_obj.definition, 240) if metric_obj and metric_obj.definition else ""
    section = metric_obj.section if metric_obj else ""
    subsection = metric_obj.subsection if metric_obj else ""
    reporting_format = metric_obj.reporting_format if metric_obj else ""
    calculation = (metric_obj.calculation or "") if metric_obj else ""
    usage_guidance = (metric_obj.usage_guidance or "") if metric_obj else ""
    sdg_goals = metric_obj.sdg_goals if metric_obj else []

    if metric_obj:
        active = metric_obj.dimensions.active_dimensions
        dim_tags_full = [_DIMENSION_LABELS.get(d, d) for d in active]
        dim_groups = sorted({_5D_GROUP.get(d, d) for d in active})
    else:
        dim_tags_full = []
        dim_groups = []
    if not dim_groups and metric_id in _FALLBACK_DIMENSION:
        dim_groups = [_FALLBACK_DIMENSION[metric_id]]

    unit = reporting_format or _FALLBACK_UNIT.get(metric_id, "")
    how_to_measure = (
        calculation.strip() if calculation else _clip(usage_guidance, 240)
    )

    category = section
    if subsection:
        category = f"{section} / {subsection}" if section else subsection

    return {
        "id": metric_id,
        "name": name,
        "definition": definition,
        "section": section,
        "subsection": subsection,
        "category": category or "General",
        "reporting_format": reporting_format,
        "unit": unit,
        "calculation": calculation.strip(),
        "usage_guidance": _clip(usage_guidance, 320),
        "how_to_measure": how_to_measure,
        "dimension_tags": dim_tags_full,
        "dimension_groups": dim_groups,
        "sdg_goals": list(sdg_goals),
    }


CORE_METRIC_SET_IDS = {
    "OD8350",  # Client Model
    "OI4753",  # Client Protection Policy
    "PI4060",  # Client Individuals: Total
    "OI8869",  # Permanent Employees: Total
    "OI1571",  # Full-time Employees: Female Managers
    "OI6213",  # Full-time Employees: Female
    "FP3021",  # Revenue from Grants and Donations
    "FP4761",  # Revenue Growth
    "OI1479",  # Greenhouse Gas Emissions: Total
    "OI4112",  # Greenhouse Gas Emissions: Direct (Scope 1)
    "OD4091",  # Social and Environmental Targets
    "OI4732",  # Social and Environmental Performance Reporting
    "OI1582",  # Wage Equity
    "OI1075",  # Board of Directors: Total
    "OI5049",  # Client Feedback System
    "OI4324",  # Community Service Policy
}


def analyze_gaps(
    company: Company,
    store: MetricStore,
    core_set: set[str] | None = None,
) -> dict:
    """Compare company's reported metrics against Core Metric Set.

    Returns a structured gap analysis with coverage ratios.
    """
    target_set = core_set or CORE_METRIC_SET_IDS
    reported_ids = set(company.reported_metrics.keys())

    required_metrics = []
    reported_metrics = []
    missing_metrics = []

    for metric_id in sorted(target_set):
        metric_obj = store.get(metric_id)
        info = _metric_info(metric_id, metric_obj)
        required_metrics.append(info)
        if metric_id in reported_ids:
            reported_metrics.append({
                **info,
                "value": company.reported_metrics.get(metric_id),
            })
        else:
            missing_metrics.append(info)

    total = len(target_set)
    reported_count = len(reported_metrics)
    coverage_pct = round((reported_count / total) * 100, 1) if total > 0 else 0

    extra_reported = sorted(reported_ids - target_set)
    extra_metrics = []
    for mid in extra_reported[:20]:
        m = store.get(mid)
        info = _metric_info(mid, m)
        info["value"] = company.reported_metrics.get(mid)
        extra_metrics.append(info)

    # Group missing metrics by category (section) for the UI
    missing_by_category: dict[str, list[dict]] = {}
    for info in missing_metrics:
        missing_by_category.setdefault(info["category"], []).append(info)
    missing_by_category = dict(sorted(missing_by_category.items()))

    # Group missing metrics by the 5D group they feed, so the renderer can
    # tie "Missing Metrics" back to the 5D radar and score rationale.
    missing_by_dimension: dict[str, list[str]] = {}
    for info in missing_metrics:
        for grp in info.get("dimension_groups") or ["General"]:
            missing_by_dimension.setdefault(grp, []).append(info["id"])

    return {
        "company": company.name,
        "core_metric_set_size": total,
        "metrics_reported": reported_count,
        "metrics_missing": total - reported_count,
        "coverage_percentage": coverage_pct,
        "reported": reported_metrics,
        "missing": missing_metrics,
        "missing_by_category": missing_by_category,
        "missing_by_dimension": missing_by_dimension,
        "required": required_metrics,
        "extra_metrics_reported": extra_metrics,
        "suggested_metrics": [
            {
                "iris_id": info["id"],
                "name": info["name"],
                "dimension_groups": info.get("dimension_groups", []),
                "unit": info.get("unit", ""),
            }
            for info in missing_metrics[:10]
        ],
        "recommendations": _generate_recommendations(missing_metrics, coverage_pct),
    }


def _generate_recommendations(missing: list[dict], coverage_pct: float) -> list[str]:
    recs: list[str] = []
    if coverage_pct < 30:
        recs.append(
            "Critical: Coverage is below 30%. Start by reporting the most fundamental "
            "metrics: Revenue, Total Clients, Total Employees."
        )
    elif coverage_pct < 60:
        recs.append(
            "Coverage is below 60%. Focus on closing gaps in the IRIS+ Core Metric Set "
            "to achieve baseline compliance."
        )
    elif coverage_pct < 80:
        recs.append(
            "Good progress. Target 80%+ coverage by adding the remaining metrics."
        )

    if missing:
        recs.append(
            f"Priority missing metrics: {', '.join(m['id'] + ' (' + m['name'] + ')' for m in missing[:5])}"
        )

    return recs
