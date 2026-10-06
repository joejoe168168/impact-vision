"""Bundle default data-request fields must cite real, correctly labelled IRIS+ IDs."""

from __future__ import annotations

import re

import pytest

from openharness.impact.database import get_metric_store
from openharness.impact.engagements.data_room import _DEFAULT_FIELDS_BY_BUNDLE

# Generic qualifiers ("Direct", "Total", ...) don't identify a concept, so a
# label must share a substantive word with the catalogue name.
_STOPWORDS = {
    "and", "the", "for", "from", "per", "total", "percent", "number",
    "direct", "indirect", "served", "new",
}


def _keywords(text: str) -> set[str]:
    words = {w.lower() for w in re.findall(r"[A-Za-z]+", text)}
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


_DEFAULT_FIELDS = sorted(
    {(metric_id, label) for fields in _DEFAULT_FIELDS_BY_BUNDLE.values() for metric_id, label, *_ in fields}
)


@pytest.mark.parametrize(("metric_id", "label"), _DEFAULT_FIELDS)
def test_default_field_metric_exists_and_label_matches_catalogue(metric_id: str, label: str) -> None:
    metric = get_metric_store().get(metric_id)
    assert metric is not None, f"{metric_id} ({label!r}) is not in the IRIS+ catalogue"
    shared = _keywords(label) & _keywords(metric.name)
    assert shared, f"{metric_id} label {label!r} shares no keyword with catalogue name {metric.name!r}"


def test_illustrative_benchmark_ids_exist_and_match_their_data() -> None:
    """Sample observations / website teaser must use real IDs for what their numbers measure."""
    from openharness.impact.engagements.website import build_benchmark_teaser
    from openharness.impact.knowledge import load_knowledge

    store = get_metric_store()
    rows = [(r["metric_id"], r["sector"]) for r in load_knowledge("benchmarks.yaml")["sample_observations"]["rows"]]
    rows += [(r.metric_id, r.sector) for r in build_benchmark_teaser().rows]
    for metric_id, _sector in rows:
        assert store.get(metric_id) is not None, metric_id
    ids = {metric_id for metric_id, _ in rows}
    assert "OI4112" not in ids and "PD5833" not in ids  # Scope 1 / affordable housing were mislabels
    assert store.get("OI1479").name.startswith("Greenhouse Gas Emissions")
