"""Plain-language form helpers for the Streamlit dashboard (v7 W3.3).

Pure functions (no Streamlit import) so the pickers can be unit-tested:
fund staff choose a sector from a list, metrics by name and SDGs by title
instead of typing IRIS+ IDs and goal numbers.
"""
from __future__ import annotations

from typing import Any, Iterable

_SEP = " — "


def sector_options() -> list[str]:
    """The 18 benchmark sectors, alphabetically."""
    from impact_vision.impact.benchmarks import get_all_benchmarks

    return sorted(get_all_benchmarks())


def sdg_options() -> list[str]:
    from impact_vision.impact.sdg_taxonomy import SDG_GOALS

    return [f"{g.number}{_SEP}{g.name}" for g in SDG_GOALS]


def sdg_numbers(labels: Iterable[str]) -> list[int]:
    out = []
    for label in labels:
        head = str(label).split(_SEP, 1)[0].strip()
        if head.isdigit():
            out.append(int(head))
    return out


def metric_label(metric: Any) -> str:
    return f"{metric.id}{_SEP}{metric.name}"


def metric_options(store: Any, *, ids: Iterable[str] = ()) -> list[str]:
    """Every catalog metric as "ID — Name", sorted by name; *ids* first if given."""
    first = [m for i in ids if (m := store.get(i))]
    rest = sorted((m for m in store.all_metrics() if m.id not in {x.id for x in first}),
                  key=lambda m: m.name.lower())
    return [metric_label(m) for m in [*first, *rest]]


def metric_id(label: str) -> str:
    return str(label).split(_SEP, 1)[0].strip().upper()


def metrics_from_rows(rows: Any) -> dict[str, str]:
    """``[{"Metric": "OI4112 — …", "Value": "1,200 tCO2e"}, …]`` (or a DataFrame) → ``{id: value}``."""
    if hasattr(rows, "to_dict"):
        rows = rows.to_dict("records")
    out: dict[str, str] = {}
    for row in rows or []:
        label, value = row.get("Metric"), row.get("Value")
        if label and value not in (None, "") and str(value).strip():
            out[metric_id(label)] = str(value).strip()
    return out


__all__ = [
    "metric_id",
    "metric_label",
    "metric_options",
    "metrics_from_rows",
    "sdg_numbers",
    "sdg_options",
    "sector_options",
]
