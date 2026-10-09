"""v8 Wave 3: the company record — stages, expected vs actual, review events."""
from __future__ import annotations


import pytest

from impact_vision.impact.company_record import (
    add_event,
    company_timeline,
    list_companies,
    set_stage,
)
from impact_vision.impact.pipeline import assess_document, save_bundle

DECK = """# Sunlit Homes — Seed pitch

Sunlit Homes sells solar lanterns to off-grid households in rural Uganda.

## Traction
- {reach} households served in 2024.
- Household lighting costs fell 35% versus their previous kerosene spend (customer survey, before and after).
"""


def _bundle(reach: str = "12,000"):
    return assess_document(DECK.format(reach=reach), name="Sunlit Homes")


def test_assessment_is_filed_as_an_expectation_in_screening():
    save_bundle(_bundle())
    t = company_timeline("Sunlit Homes")
    assert t["stage"] == "screening" and len(t["assessments"]) == 1
    rec = t["outcomes"][0]
    assert rec["record_kind"] == "expected" and rec["outcome"] == "people" and rec["reach"] == 12_000
    assert t["expected_vs_actual"][0]["status"] == "no actual yet"


def test_after_investment_assessments_are_actuals_and_compared():
    save_bundle(_bundle("12,000"))
    set_stage("Sunlit Homes", "invested", actor="IC", rationale="approved 2026-10")
    save_bundle(_bundle("2,000"))  # the company served far fewer than expected
    t = company_timeline("Sunlit Homes")
    kinds = [r["record_kind"] for r in t["outcomes"]]
    assert kinds == ["expected", "actual"]
    row = t["expected_vs_actual"][0]
    assert row["status"] == "below the expected range" and row["variance_pct"] < -50
    assert any(e["kind"] == "stage" and e["target"] == "invested" for e in t["events"])
    assert [tr["to_stage"] for tr in t["transitions"]][-1] == "invested"


def test_review_events_and_ic_decision():
    save_bundle(_bundle())
    with pytest.raises(ValueError):
        add_event("Sunlit Homes", "approval", author="", text="ok")
    add_event("Sunlit Homes", "comment", author="Ann", text="Checked the survey sample (n=400).")
    t = add_event("Sunlit Homes", "approval", author="IC chair", text="Approved with an evidence plan.")
    assert t["ic_decision"]["author"] == "IC chair" and t["ic_decision"]["kind"] == "approval"
    with pytest.raises(ValueError):
        set_stage("Sunlit Homes", "launched")


def test_list_splits_portfolio_and_pipeline():
    save_bundle(_bundle())
    save_bundle(assess_document(DECK.format(reach="900").replace("Sunlit Homes", "Moonlit Co"), name="Moonlit Co"))
    set_stage("Moonlit Co", "monitoring")
    rows = {r["company"]: r for r in list_companies()}
    assert rows["Moonlit Co"]["portfolio"] and not rows["Sunlit Homes"]["portfolio"]
    assert rows["Sunlit Homes"]["expected_impact"]["unit"] == "depth-weighted person-years"


def test_schema_is_versioned(tmp_path):
    from impact_vision.impact.storage import SCHEMA_VERSION, AssessmentStore

    store = AssessmentStore(tmp_path / "old.db")
    assert store.schema_version == SCHEMA_VERSION >= 2
    AssessmentStore(tmp_path / "old.db")  # re-opening applies nothing twice
    assert store.schema_version == SCHEMA_VERSION


def test_web_api(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    monkeypatch.setenv("IMPACT_VISION_WEB_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("IMPACT_VISION_API_KEY", raising=False)
    from impact_vision.web.app import app

    save_bundle(_bundle())
    with TestClient(app, base_url="http://127.0.0.1:8787") as client:
        assert client.get("/api/v1/chat/companies").json()["companies"][0]["company"] == "Sunlit Homes"
        t = client.get("/api/v1/chat/companies/Sunlit Homes").json()
        assert t["stage"] == "screening"
        moved = client.post("/api/v1/chat/companies/Sunlit Homes/stage", json={"stage": "ic_review", "actor": "Ann"})
        assert moved.status_code == 200 and moved.json()["stage"] == "ic_review"
        bad = client.post("/api/v1/chat/companies/Sunlit Homes/events", json={"kind": "approval", "author": ""})
        assert bad.status_code == 400
        assert client.get("/api/v1/chat/companies/Nobody").status_code == 404


def test_every_assessment_is_kept_as_history():
    save_bundle(_bundle("12,000"))
    save_bundle(_bundle("13,000"))
    assert len(company_timeline("Sunlit Homes")["assessments"]) == 2
