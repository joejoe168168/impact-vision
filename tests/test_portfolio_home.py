"""W3.4: portfolio home — pipeline, heat-map, deadlines, review queue, attention list."""

from __future__ import annotations

import copy
import re
from datetime import date

import pytest

from openharness.impact.pipeline import SAMPLE_DECKS, assess_file, sample_deck_path
from openharness.impact.portfolio_home import (
    build_portfolio_home,
    record_from_bundle,
    render_portfolio_home,
)

TODAY = date(2026, 10, 6)


@pytest.fixture(scope="module")
def records():
    return [record_from_bundle(assess_file(sample_deck_path(k))) for k in SAMPLE_DECKS]


def test_view_summarises_the_portfolio(records):
    v = build_portfolio_home(records, fund_name="Fund I", today=TODAY)
    kpis = {k["label"]: k["value"] for k in v["kpis"]}
    assert kpis["Companies"] == "3"
    assert sum(p["count"] for p in v["pipeline"]) == 3
    assert [c["name"] for c in v["companies"]] == sorted(c["name"] for c in v["companies"])
    assert all(len(c["dims"]) == 5 and len(c["sdgs"]) == len(v["sdg_cols"]) for c in v["companies"])
    assert all(1 <= d["lvl"] <= 5 for c in v["companies"] for d in c["dims"] if d["value"] is not None)
    frameworks = {d["framework"] for d in v["deadlines"]} | {d["framework"] for d in
                  build_portfolio_home(records, jurisdictions=["US"], today=TODAY)["deadlines"]}
    assert "California SB 253" in frameworks and any("SFDR" in f for f in frameworks)
    assert all(r["confidence"] < 0.5 for r in v["review"]) and v["review_total"] >= len(v["review"])


def test_attention_flags_stale_and_greenwashing(records):
    stale = copy.deepcopy(records[0])
    stale["created_at"] = "2025-01-01T00:00:00Z"
    stale["summary"]["greenwashing_risk"] = 72.0
    v = build_portfolio_home([stale], today=TODAY)
    reasons = " | ".join(a["reason"] for a in v["attention"])
    assert "days ago" in reasons and "Greenwashing risk 72/100" in reasons
    assert next(k for k in v["kpis"] if k["label"] == "Greenwashing flags")["value"] == "1"


def test_render_is_escaped_accessible_and_handles_empty(records):
    evil = copy.deepcopy(records[0])
    evil["summary"]["company"] = "<img src=x onerror=alert(1)>"
    html = render_portfolio_home(build_portfolio_home([evil], today=TODAY))
    assert "<img src=x" not in html
    for head in re.findall(r"<thead>(.*?)</thead>", html, re.S):
        assert all('scope="col"' in th for th in re.findall(r"<th[^>]*>", head) if "gap" not in th)
    empty = render_portfolio_home(build_portfolio_home([], today=TODAY))
    assert "No assessments yet" in empty


def test_web_portfolio_view(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from openharness.impact import storage

    monkeypatch.setenv("IMPACT_VISION_WEB_HOME", str(tmp_path))
    monkeypatch.setattr(storage, "_global_store", storage.AssessmentStore(tmp_path / "iv.db"))
    from openharness.web import reports_api
    from openharness.web.app import app

    for _ in range(2):  # re-assessing a company replaces it on the portfolio page
        reports_api.create_report(sample_deck_path("solar").with_suffix(".md"))
    res = TestClient(app).get("/api/v1/chat/portfolio/view", params={"jurisdictions": "US"})
    assert res.status_code == 200
    assert res.text.count('<td class="co">') == 1
    assert "SunPath Energy Ltd" in res.text and "California SB 253" in res.text
