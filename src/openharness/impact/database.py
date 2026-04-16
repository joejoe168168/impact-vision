"""In-memory IRIS+ metric store with query and filter API."""

from __future__ import annotations

import logging

from openharness.impact.catalog import (
    get_default_excel_path,
    get_default_json_path,
    load_catalog_from_excel,
    load_catalog_json,
    save_catalog_json,
)
from openharness.impact.models import Metric

logger = logging.getLogger(__name__)


class MetricStore:
    """Queryable in-memory store for IRIS+ metrics."""

    def __init__(self, metrics: list[Metric] | None = None) -> None:
        self._metrics: dict[str, Metric] = {}
        if metrics:
            for m in metrics:
                self._metrics[m.id] = m

    @property
    def count(self) -> int:
        return len(self._metrics)

    def get(self, metric_id: str) -> Metric | None:
        return self._metrics.get(metric_id.upper().strip())

    def all_metrics(self) -> list[Metric]:
        return list(self._metrics.values())

    def search(self, query: str, limit: int = 20) -> list[Metric]:
        """Full-text search across metric names and definitions."""
        q = query.lower()
        results: list[tuple[int, Metric]] = []
        for m in self._metrics.values():
            score = 0
            if q in m.name.lower():
                score += 10
            if q in m.id.lower():
                score += 20
            if q in m.definition.lower():
                score += 5
            if q in m.primary_impact_category.lower():
                score += 3
            if any(q in t.lower() for t in m.impact_themes):
                score += 3
            if score > 0:
                results.append((score, m))
        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results[:limit]]

    def filter_by_sdg(self, goal: int, target: str | None = None) -> list[Metric]:
        """Filter metrics mapped to a specific SDG goal or target."""
        results: list[Metric] = []
        for m in self._metrics.values():
            if goal in m.sdg_goals:
                if target is None or target in m.sdg_targets:
                    results.append(m)
        return results

    def filter_by_theme(self, theme: str) -> list[Metric]:
        """Filter metrics by impact theme (case-insensitive partial match)."""
        t = theme.lower()
        return [
            m for m in self._metrics.values()
            if any(t in th.lower() for th in m.impact_themes)
            or t in m.primary_impact_category.lower()
        ]

    def filter_by_dimension(self, dimension: str) -> list[Metric]:
        """Filter metrics tagged with a specific dimension of impact."""
        dim_map = {
            "what": "what",
            "who": "who",
            "how_much_scale": "how_much_scale",
            "how_much_depth": "how_much_depth",
            "how_much_duration": "how_much_duration",
            "scale": "how_much_scale",
            "depth": "how_much_depth",
            "duration": "how_much_duration",
            "contribution": "contribution_depth",
            "contribution_depth": "contribution_depth",
            "contribution_duration": "contribution_duration",
            "risk": "risk",
        }
        field_name = dim_map.get(dimension.lower().replace(" ", "_"))
        if not field_name:
            return []
        return [
            m for m in self._metrics.values()
            if getattr(m.dimensions, field_name, False)
        ]

    def filter_by_section(self, section: str) -> list[Metric]:
        s = section.lower()
        return [m for m in self._metrics.values() if s in m.section.lower()]

    def filter_by_stakeholder(self, stakeholder: str) -> list[Metric]:
        s = stakeholder.lower()
        return [
            m for m in self._metrics.values()
            if any(s in st.lower() for st in m.stakeholders)
        ]

    def stats(self) -> dict:
        """Return summary statistics about the loaded catalog."""
        total = len(self._metrics)
        with_sdg = sum(1 for m in self._metrics.values() if m.sdg_goals)
        with_dims = sum(1 for m in self._metrics.values() if m.dimensions.active_dimensions)

        sdg_counts: dict[int, int] = {}
        for m in self._metrics.values():
            for g in m.sdg_goals:
                sdg_counts[g] = sdg_counts.get(g, 0) + 1

        theme_counts: dict[str, int] = {}
        for m in self._metrics.values():
            for t in m.impact_themes:
                theme_counts[t] = theme_counts.get(t, 0) + 1

        category_counts: dict[str, int] = {}
        for m in self._metrics.values():
            cat = m.primary_impact_category
            if cat:
                category_counts[cat] = category_counts.get(cat, 0) + 1

        dim_counts: dict[str, int] = {}
        for m in self._metrics.values():
            for d in m.dimensions.active_dimensions:
                dim_counts[d] = dim_counts.get(d, 0) + 1

        return {
            "total_metrics": total,
            "metrics_with_sdg_mapping": with_sdg,
            "metrics_with_dimension_tags": with_dims,
            "sdg_coverage": dict(sorted(sdg_counts.items())),
            "top_themes": dict(sorted(theme_counts.items(), key=lambda x: -x[1])[:15]),
            "categories": dict(sorted(category_counts.items(), key=lambda x: -x[1])),
            "dimension_counts": dim_counts,
        }


_global_store: MetricStore | None = None


def get_metric_store(force_reload: bool = False) -> MetricStore:
    """Get or create the global MetricStore singleton.

    Loads from processed JSON if available, otherwise from Excel.
    """
    global _global_store
    if _global_store is not None and not force_reload:
        return _global_store

    json_path = get_default_json_path()
    if json_path.exists() and not force_reload:
        logger.info("Loading catalog from JSON cache: %s", json_path)
        metrics = load_catalog_json(json_path)
        _global_store = MetricStore(metrics)
        return _global_store

    excel_path = get_default_excel_path()
    if excel_path.exists():
        logger.info("Loading catalog from Excel: %s", excel_path)
        metrics = load_catalog_from_excel(excel_path)
        save_catalog_json(metrics, json_path)
        _global_store = MetricStore(metrics)
        return _global_store

    logger.warning("No IRIS+ catalog found. Store will be empty.")
    _global_store = MetricStore()
    return _global_store


def ensure_catalog_loaded() -> MetricStore:
    """Ensure the catalog is loaded, raising if no data source found."""
    store = get_metric_store()
    if store.count == 0:
        excel_path = get_default_excel_path()
        raise FileNotFoundError(
            f"IRIS+ catalog not loaded. Place the Excel file at: {excel_path}"
        )
    return store
