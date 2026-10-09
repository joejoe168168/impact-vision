"""Reviewer sign-off for AI Act Art 50 (roadmap v8 Wave 4)."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_sign_off_marks_the_report_and_is_audited(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_WEB_HOME", str(tmp_path))
    from impact_vision.impact.ai_provenance import marking_from_html
    from impact_vision.impact.pipeline import sample_deck_path
    from impact_vision.web.app import app
    from impact_vision.web.reports_api import create_report, load_report, render_report

    rep = create_report(sample_deck_path("solar"))
    client = TestClient(app, base_url="http://127.0.0.1:8788")
    assert client.post(f"/api/v1/chat/reports/{rep['id']}/sign-off", json={"reviewer": " "}).status_code == 400
    r = client.post(f"/api/v1/chat/reports/{rep['id']}/sign-off",
                    json={"reviewer": "Jane Ng", "note": "Checked reach against the KPI file."})
    assert r.status_code == 200 and len(r.json()["report_sha256"]) == 64
    record = load_report(rep["id"])
    assert record["sign_offs"][0]["reviewer"] == "Jane Ng"
    html = render_report(record)
    assert "Reviewed and signed off by Jane Ng" in html
    marking = marking_from_html(html)
    assert marking["human_reviewed"] is True and marking["reviewer"] == "Jane Ng"
    assert "已由 Jane Ng" in render_report(record, lang="zh-HK")

    from impact_vision.impact.audit_trail import AuditTrail
    from impact_vision.impact.company_record import company_timeline
    from impact_vision.impact.state_store import get_state_store

    events = [x.payload for x in AuditTrail(fund_id="reports", store=get_state_store()).feed.reports]
    assert any(e.get("report_id") == rep["id"] and e["actor"] == "Jane Ng" for e in events)
    assert any(e["target"] == "report sign-off" for e in company_timeline(record["company"])["events"])
