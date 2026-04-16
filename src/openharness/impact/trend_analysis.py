"""Trend analysis engine for metric time-series data and target tracking."""

from __future__ import annotations

import re
from typing import Any

from openharness.impact.models import Company, MetricValue


def _parse_numeric(value: Any) -> float | None:
    """Attempt to extract a numeric value from various formats."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.\-]", "", value.strip())
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    return None


def _period_sort_key(period: str) -> tuple[int, int]:
    """Extract a sortable (year, sub-period) tuple from period strings."""
    period = period.upper().strip()

    fy_match = re.search(r"FY\s*(\d{4})", period)
    if fy_match:
        return (int(fy_match.group(1)), 0)

    q_match = re.search(r"Q(\d)\s*(\d{4})", period)
    if q_match:
        return (int(q_match.group(2)), int(q_match.group(1)))

    h_match = re.search(r"H(\d)\s*(\d{4})", period)
    if h_match:
        return (int(h_match.group(2)), int(h_match.group(1)))

    year_match = re.search(r"(\d{4})", period)
    if year_match:
        return (int(year_match.group(1)), 0)

    return (0, 0)


def analyze_metric_trend(values: list[MetricValue]) -> dict:
    """Analyze trend for a single metric's time-series.

    Returns a dict with direction, change_pct, data_points, first/last values,
    and a human-readable summary.
    """
    numeric_entries = []
    for mv in values:
        num = _parse_numeric(mv.value)
        if num is not None:
            numeric_entries.append((mv, num))

    if len(numeric_entries) < 2:
        return {
            "metric_id": values[0].metric_id if values else "",
            "direction": "insufficient_data",
            "data_points": len(numeric_entries),
            "summary": "Not enough data points for trend analysis (need at least 2).",
        }

    sorted_entries = sorted(numeric_entries, key=lambda x: _period_sort_key(x[0].period))
    first_val = sorted_entries[0][1]
    last_val = sorted_entries[-1][1]

    if first_val == 0:
        change_pct = 100.0 if last_val > 0 else (-100.0 if last_val < 0 else 0.0)
    else:
        change_pct = round(((last_val - first_val) / abs(first_val)) * 100, 1)

    abs_change = last_val - first_val

    if abs(change_pct) < 5:
        direction = "stable"
    elif change_pct > 0:
        direction = "improving"
    else:
        direction = "declining"

    periods = [e[0].period for e in sorted_entries]
    values_list = [e[1] for e in sorted_entries]

    volatility = 0.0
    if len(values_list) >= 3:
        diffs = [abs(values_list[i] - values_list[i - 1]) for i in range(1, len(values_list))]
        avg_diff = sum(diffs) / len(diffs)
        mean_val = sum(values_list) / len(values_list)
        if mean_val != 0:
            volatility = round((avg_diff / abs(mean_val)) * 100, 1)

    verified_count = sum(1 for e in sorted_entries if e[0].verified)

    summary_parts = [
        f"Metric {sorted_entries[0][0].metric_id}: {direction}",
        f"({first_val} -> {last_val}, {change_pct:+.1f}%)",
        f"over {len(sorted_entries)} data points",
        f"({periods[0]} to {periods[-1]})" if periods[0] and periods[-1] else "",
    ]

    return {
        "metric_id": sorted_entries[0][0].metric_id,
        "direction": direction,
        "change_pct": change_pct,
        "absolute_change": abs_change,
        "first_value": first_val,
        "last_value": last_val,
        "first_period": periods[0],
        "last_period": periods[-1],
        "data_points": len(sorted_entries),
        "volatility_pct": volatility,
        "verified_count": verified_count,
        "values": [{"period": e[0].period, "value": e[1]} for e in sorted_entries],
        "summary": " ".join(p for p in summary_parts if p),
    }


def analyze_company_trends(company: Company) -> dict:
    """Analyze all metric trends for a company using its metric_history.

    Returns a dict with per-metric trends and an overall summary.
    """
    if not company.metric_history:
        return {
            "company": company.name,
            "trends": [],
            "overall_direction": "no_data",
            "summary": f"No historical metric data available for {company.name}.",
        }

    by_metric: dict[str, list[MetricValue]] = {}
    for mv in company.metric_history:
        by_metric.setdefault(mv.metric_id, []).append(mv)

    trends = []
    for metric_id, mvs in sorted(by_metric.items()):
        trend = analyze_metric_trend(mvs)
        trends.append(trend)

    direction_counts = {"improving": 0, "declining": 0, "stable": 0}
    for t in trends:
        d = t.get("direction", "")
        if d in direction_counts:
            direction_counts[d] += 1

    total_with_trend = sum(direction_counts.values())
    if total_with_trend == 0:
        overall = "insufficient_data"
    elif direction_counts["improving"] > total_with_trend / 2:
        overall = "mostly_improving"
    elif direction_counts["declining"] > total_with_trend / 2:
        overall = "mostly_declining"
    elif direction_counts["stable"] > total_with_trend / 2:
        overall = "mostly_stable"
    else:
        overall = "mixed"

    summary_parts = [
        f"Trend analysis for {company.name}:",
        f"{len(trends)} metrics analyzed.",
        f"{direction_counts['improving']} improving,",
        f"{direction_counts['declining']} declining,",
        f"{direction_counts['stable']} stable.",
        f"Overall: {overall.replace('_', ' ')}.",
    ]

    return {
        "company": company.name,
        "trends": trends,
        "metrics_analyzed": len(trends),
        "direction_counts": direction_counts,
        "overall_direction": overall,
        "summary": " ".join(summary_parts),
    }


def _extract_target_numeric(target_str: str) -> float | None:
    """Extract numeric target value from strings like '500 tCO2e by 2027'."""
    num = re.search(r"([\d,.]+)", target_str)
    if num:
        cleaned = num.group(1).replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def assess_target_progress(company: Company) -> dict:
    """Compare current metric values against impact_targets.

    Returns per-target progress (on_track, behind, exceeded, no_data) and
    an aggregate completion percentage.
    """
    if not company.impact_targets:
        return {
            "company": company.name,
            "targets": [],
            "overall_progress_pct": 0.0,
            "summary": f"No impact targets set for {company.name}.",
        }

    latest_values: dict[str, MetricValue] = {}
    for mv in company.metric_history:
        existing = latest_values.get(mv.metric_id)
        if existing is None or _period_sort_key(mv.period) > _period_sort_key(existing.period):
            latest_values[mv.metric_id] = mv

    for mid, val_str in company.reported_metrics.items():
        if mid not in latest_values:
            latest_values[mid] = MetricValue(metric_id=mid, value=val_str, period="current")

    targets_result = []
    on_track_count = 0
    assessed_count = 0

    for metric_id, target_str in company.impact_targets.items():
        target_num = _extract_target_numeric(target_str)
        current_mv = latest_values.get(metric_id)
        current_num = _parse_numeric(current_mv.value) if current_mv else None

        if target_num is None or current_num is None:
            targets_result.append({
                "metric_id": metric_id,
                "target": target_str,
                "current_value": str(current_mv.value) if current_mv else "N/A",
                "progress_pct": None,
                "status": "no_data",
                "summary": f"{metric_id}: Cannot assess — target or current value not numeric.",
            })
            continue

        assessed_count += 1
        progress_pct = round((current_num / target_num) * 100, 1) if target_num != 0 else 100.0

        if progress_pct >= 100:
            status = "exceeded"
            on_track_count += 1
        elif progress_pct >= 70:
            status = "on_track"
            on_track_count += 1
        elif progress_pct >= 40:
            status = "behind"
        else:
            status = "at_risk"

        targets_result.append({
            "metric_id": metric_id,
            "target": target_str,
            "target_value": target_num,
            "current_value": current_num,
            "progress_pct": progress_pct,
            "status": status,
            "summary": f"{metric_id}: {current_num} / {target_num} ({progress_pct:.0f}%) — {status}",
        })

    overall_pct = 0.0
    if assessed_count > 0:
        pcts = [t["progress_pct"] for t in targets_result if t["progress_pct"] is not None]
        overall_pct = round(sum(pcts) / len(pcts), 1) if pcts else 0.0

    summary_parts = [
        f"Target tracking for {company.name}:",
        f"{len(targets_result)} targets,",
        f"{on_track_count} on-track/exceeded,",
        f"{assessed_count - on_track_count} behind/at-risk.",
        f"Overall progress: {overall_pct:.0f}%.",
    ]

    return {
        "company": company.name,
        "targets": targets_result,
        "total_targets": len(targets_result),
        "on_track_count": on_track_count,
        "overall_progress_pct": overall_pct,
        "summary": " ".join(summary_parts),
    }
