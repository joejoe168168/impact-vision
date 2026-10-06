"""Engagement view (W3.2 deferral, unblocked by W5.3 persistence)."""

from __future__ import annotations

import re
from datetime import date

import pytest

TODAY = date(2026, 10, 6)


def _workspace(store=None):
    from openharness.impact.engagements.workspace import EngagementWorkspace

    ws = EngagementWorkspace(store=store)
    eng = ws.create_engagement(name="Fund I DD", client_name="Acme Capital", bundle_id="dd_light",
                               autopopulate=False)
    ws.transition_engagement(eng.engagement_id, "active", actor="cl")
    ws.add_deliverable(eng.engagement_id, name="IC memo", owner="cl", due_date="2026-10-01")
    ws.add_deliverable(eng.engagement_id, name="LP report", owner="cl", due_date="2026-10-15")
    ws.create_engagement(name="Old project", client_name="Beta", autopopulate=False)
    return ws, eng


def test_view_counts_overdue_and_soon_items() -> None:
    from openharness.impact.engagement_home import build_engagement_home, render_engagement_home

    ws, eng = _workspace()
    view = build_engagement_home(ws.list_engagements(), today=TODAY)
    kpis = {k["label"]: k["value"] for k in view["kpis"]}
    assert kpis["Active engagements"] == "2" and kpis["Overdue"] == "1" and kpis["Due in 14 days"] == "1"
    card = next(c for c in view["engagements"] if c["id"] == eng.engagement_id)
    assert [i["title"] for i in card["upcoming"]] == ["IC memo", "LP report"]
    assert card["upcoming"][0]["status"] == "overdue"
    html = render_engagement_home(view)
    assert "Fund I DD" in html and "5d late" in html and "in 9d" in html
    for head in re.findall(r"<thead>(.*?)</thead>", html, re.S):
        assert all('scope="col"' in th for th in re.findall(r"<th[^>]*>", head))
    assert "No engagements yet" in render_engagement_home(build_engagement_home([], today=TODAY))


def test_web_engagement_routes_read_the_persisted_workspace(monkeypatch) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from openharness.impact.state_store import MemoryStateStore
    from openharness.tools.impact import engagement_workspace_tool as tool
    from openharness.web.app import app

    store = MemoryStateStore()
    ws, _ = _workspace(store)
    monkeypatch.setattr(tool, "_DEFAULT_WORKSPACE", None)
    monkeypatch.setattr("openharness.impact.state_store._STORE", store)
    client = TestClient(app)
    listed = client.get("/api/v1/chat/engagements").json()["engagements"]
    assert {e["name"] for e in listed} == {"Fund I DD", "Old project"}  # restored from the store
    page = client.get("/api/v1/chat/engagements/view")
    assert page.status_code == 200 and "Acme Capital" in page.text
