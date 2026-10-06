"""W3.3: plain-language dashboard pickers and the deck-upload path."""

from __future__ import annotations

from pathlib import Path

import pytest

from openharness.dashboard import forms

APP = Path(__file__).resolve().parents[1] / "src" / "openharness" / "dashboard" / "app.py"


def test_pickers_use_names_not_ids():
    from openharness.impact.database import get_metric_store

    assert len(forms.sector_options()) == 18 and "Energy" in forms.sector_options()
    assert forms.sdg_options()[6] == "7 — Affordable and Clean Energy"
    assert forms.sdg_numbers(["7 — Affordable and Clean Energy", "13 — Climate Action", "x"]) == [7, 13]

    store = get_metric_store()
    options = forms.metric_options(store, ids=["OI8869"])
    assert options[0].startswith("OI8869 — ") and len(options) == len(store.all_metrics())
    rows = [{"Metric": options[0], "Value": " 180 "}, {"Metric": options[1], "Value": ""}]
    assert forms.metrics_from_rows(rows) == {"OI8869": "180"}


@pytest.fixture()
def app_test():
    testing = pytest.importorskip("streamlit.testing.v1")
    return testing.AppTest.from_file(str(APP), default_timeout=60)


def test_dashboard_data_entry_runs(app_test):
    at = app_test.run()
    assert not at.exception
    at.radio(key="assess_mode").set_value("Data I enter").run()
    assert not at.exception
    assert at.selectbox[0].value == "Financial Services"
    at.button[0].click().run()
    assert not at.exception
    assert any("5 Dimensions" in h.value for h in at.subheader)
