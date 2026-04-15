"""Gap analysis: compare reported metrics against IRIS+ Core Metric Sets."""

from __future__ import annotations

from openharness.impact.database import MetricStore
from openharness.impact.models import Company

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
        info = {
            "id": metric_id,
            "name": metric_obj.name if metric_obj else metric_id,
            "definition": metric_obj.definition[:200] if metric_obj and metric_obj.definition else "",
            "section": metric_obj.section if metric_obj else "",
        }
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
        extra_metrics.append({
            "id": mid,
            "name": m.name if m else mid,
            "value": company.reported_metrics.get(mid),
        })

    return {
        "company": company.name,
        "core_metric_set_size": total,
        "metrics_reported": reported_count,
        "metrics_missing": total - reported_count,
        "coverage_percentage": coverage_pct,
        "reported": reported_metrics,
        "missing": missing_metrics,
        "required": required_metrics,
        "extra_metrics_reported": extra_metrics,
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
