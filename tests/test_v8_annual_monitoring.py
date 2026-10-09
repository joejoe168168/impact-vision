"""Annual monitoring linked to the company record (roadmap v8 W3.4)."""
from __future__ import annotations

from datetime import date

import pytest

from impact_vision.impact import annual_monitoring as am
from impact_vision.impact.company_record import company_timeline, set_stage
from impact_vision.impact.pipeline import assess_file, sample_deck_path, save_bundle


@pytest.fixture
def invested():
    bundle = assess_file(sample_deck_path("solar"))
    save_bundle(bundle)  # at screening: stored as the expectation
    name = bundle.company.name
    set_stage(name, "invested", actor="IC", rationale="approved")
    return name


def _answers(**over):
    return {"reach": "30,000", "depth_measure": "household energy spend", "depth_pct": "-25",
            "evidence": "before_after", "tco2e": "4000", "employees": "120", "variance": "Slower rollout in Q1.",
            **over}


def test_request_is_built_from_the_expectation(invested):
    req = am.create_request(invested, "2026", contact_email="cfo@investee.example")
    ids = [q["id"] for q in req["questions"]]
    assert {"reach", "depth_pct", "evidence", "tco2e", "energy_mwh", "employees", "variance"} <= set(ids)
    reach_q = next(q for q in req["questions"] if q["id"] == "reach")
    assert "plan at investment" in reach_q["label"]
    assert req["token"] and req["token"] not in str(am.list_requests())
    assert req["due"] == "2027-03-31"


def test_pre_investment_company_is_refused():
    bundle = assess_file(sample_deck_path("solar"))
    save_bundle(bundle)
    with pytest.raises(ValueError, match="invested"):
        am.create_request(bundle.company.name, "2026")


def test_submission_files_actuals_and_explains_variance(invested):
    req = am.create_request(invested, "2026")
    with pytest.raises(ValueError, match="Please answer"):
        am.submit_response(req["token"], {"depth_pct": "10"})
    out = am.submit_response(req["token"], _answers())
    t = company_timeline(invested)
    actual = [r for r in t["outcomes"] if r["record_kind"] == "actual"]
    assert {r["outcome"] for r in actual} == {"people", "climate"}
    assert all(r["period"] == "2026" for r in actual)
    people = next(v for v in out["variance"] if v["outcome"] == "people")
    assert people["company_explanation"] == "Slower rollout in Q1."
    assert any("reach" in d for d in people["drivers"]) or people["variance_pct"] is not None
    with pytest.raises(ValueError, match="already"):
        am.submit_response(req["token"], _answers())
    with pytest.raises(PermissionError):
        am.submit_response("forged-token", _answers())


def test_better_evidence_raises_evidence_quality(invested):
    weak = am.results_statement({"company": "X", "period": "2026", "expected": []},
                                _answers(evidence="records"))
    strong = am.results_statement({"company": "X", "period": "2026", "expected": []},
                                  _answers(evidence="comparison", verified="on"))
    assert "comparison group" in strong and "verified by an independent" in strong
    assert "comparison group" not in weak


def test_reminders_by_email_and_webhook(invested, monkeypatch):
    req = am.create_request(invested, "2026", due="2027-03-31", contact_email="cfo@investee.example")
    assert am.due_reminders(date(2027, 3, 1)) == []                      # too early
    assert [r["key"] for r in am.due_reminders(date(2027, 3, 20))] == [req["key"]]

    sent, fired = [], []

    class FakeSMTP:
        def __init__(self, host, port, timeout):  # noqa: ANN001
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):  # noqa: ANN002
            return False

        def starttls(self):
            pass

        def send_message(self, msg):  # noqa: ANN001
            sent.append((msg["To"], msg["Subject"]))

    monkeypatch.setenv("IMPACT_VISION_SMTP_HOST", "smtp.example.org")
    monkeypatch.setattr(am.smtplib, "SMTP", FakeSMTP)
    done = am.send_reminders(today=date(2027, 3, 20), webhook=lambda e, p: fired.append((e, p["company"])))
    assert done[0]["email"] == "sent" and done[0]["webhook"] == "fired"
    assert sent == [("cfo@investee.example", f"{invested}: 2026 impact results are due in 11 days")]
    assert fired == [("monitoring_reminder", invested)]
    assert am.due_reminders(date(2027, 3, 22)) == []                     # reminded 2 days ago
    assert len(am.due_reminders(date(2027, 3, 31))) == 1                # due date
    assert len(am.due_reminders(date(2027, 4, 10))) == 1                # overdue, weekly


def test_portal_round_trip_over_http(invested):
    from fastapi.testclient import TestClient

    from impact_vision.web.app import app

    client = TestClient(app, base_url="http://127.0.0.1:8788")
    made = client.post(f"/api/v1/chat/companies/{invested}/monitoring",
                       json={"period": "2026", "contact_email": "cfo@investee.example"})
    assert made.status_code == 200, made.text
    path = made.json()["portal_url"].split("8788", 1)[1]
    form = client.get(path)
    assert form.status_code == 200 and "Send results" in form.text
    assert "form-action 'self'" in form.headers["content-security-policy"]
    assert form.headers["referrer-policy"] == "same-origin"  # no-referrer makes browsers post Origin: null
    bad = client.post(path, data={"depth_pct": "5"}, headers={"origin": "http://127.0.0.1:8788"})
    assert bad.status_code == 400 and "Please answer" in bad.text
    ok = client.post(path, data=_answers(), headers={"origin": "http://127.0.0.1:8788"})
    assert ok.status_code == 200 and "Thank you" in ok.text
    status = client.get(f"/api/v1/chat/companies/{invested}/monitoring").json()
    assert status["requests"][0]["status"] == "submitted" and status["variance"]
    assert client.get("/portal/not-a-token").status_code == 404
