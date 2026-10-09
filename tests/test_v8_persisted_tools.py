"""Stateful tools keep their state between calls (roadmap v8 W5.4)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from impact_vision.impact.assurance import build_assurance_pack
from impact_vision.tools import create_default_tool_registry
from impact_vision.tools.base import ToolExecutionContext


def _run(name: str, payload: dict, *, ok: bool = True):
    tool = create_default_tool_registry().get(name)
    result = asyncio.run(tool.execute(tool.input_model.model_validate(payload), ToolExecutionContext(cwd=Path.cwd())))
    assert result.is_error is not ok, result.output
    return result.metadata


def test_verification_workspace_resumes_by_id():
    pack = build_assurance_pack(fund_name="Demo Fund", reporting_period="FY2026", assertion_text="Assertion",
                                prepared_by="CFO", subject_description="Selected metrics", metrics=["OI4112"])
    opened = _run("verification_workspace", {"action": "open", "pack": pack.model_dump(mode="json")})
    wid = opened["workspace_id"]
    _run("verification_workspace", {"action": "submit_finding", "workspace_id": wid,
                                    "observation": "Reach figure lacks source", "severity": "high",
                                    "raised_by": "verifier"})
    snap = _run("verification_workspace", {"action": "snapshot", "workspace_id": wid})
    assert [f["observation"] for f in snap["findings"]] == ["Reach figure lacks source"]
    # another tenant can't see it
    _run("verification_workspace", {"action": "snapshot", "workspace_id": wid, "tenant_id": "other"}, ok=False)


def test_lp_qa_workspace_resumes_by_name():
    base = {"workspace_name": "fy26", "fund_name": "Demo Fund", "reporting_period": "FY2026"}
    _run("lp_narrative", {**base, "action": "qa_ask", "question": {"question_id": "q1", "text": "How many jobs?"}})
    out = _run("lp_narrative", {**base, "action": "qa_export"})
    assert [q["question_id"] for q in out["questions"]] == ["q1"]


def test_consent_register_grant_revoke_list():
    consent = {"consent_id": "c-1", "respondent_id": "r-1", "survey_id": "s-1", "consent_text_version": "v1"}
    _run("stakeholder_voice", {"action": "consent_grant", "consent": consent})
    _run("stakeholder_voice", {"action": "consent_grant", "consent": {**consent, "consent_id": "c-2"}})
    revoked = _run("stakeholder_voice", {"action": "consent_revoke", "consent_id": "c-1"})
    assert revoked["revoked_at"]
    listing = _run("stakeholder_voice", {"action": "consent_list"})
    assert (listing["active"], listing["revoked"]) == (1, 1)


def test_state_store_migrations_are_recorded_and_idempotent(tmp_path):
    import sqlite3

    from impact_vision.impact.state_store import SCHEMA_VERSION, SQLiteStateStore

    path = tmp_path / "state.db"
    legacy = sqlite3.connect(path)  # a 0.17 database: the table, no version record
    legacy.execute("CREATE TABLE iv_state (tenant_id TEXT NOT NULL, kind TEXT NOT NULL, key TEXT NOT NULL, "
                   "payload TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (tenant_id, kind, key))")
    legacy.execute("INSERT INTO iv_state VALUES ('t', 'k', 'a', '{\"x\": 1}', 'now')")
    legacy.commit()
    legacy.close()
    store = SQLiteStateStore(path)
    assert store.schema_version == SCHEMA_VERSION and store.get("t", "k", "a") == {"x": 1}
    store.close()
    again = SQLiteStateStore(path)
    rows = again._conn.execute("SELECT version FROM iv_schema ORDER BY version").fetchall()
    assert [r[0] for r in rows] == list(range(1, SCHEMA_VERSION + 1))


def test_gateway_webhooks_and_jobs_persist(monkeypatch):
    from fastapi.testclient import TestClient

    from impact_vision.api_gateway import router

    async def no_check(url):  # noqa: ANN001 - SSRF check needs DNS; not under test here
        return None

    monkeypatch.setattr(router, "_ensure_webhook_target", no_check)
    client = TestClient(router.app)
    hook = client.post("/api/v1/webhook", json={"url": "https://hooks.example.org/x", "events": ["tool_complete"]})
    wid = hook.json()["webhook_id"]
    assert [w["id"] for w in client.get("/api/v1/webhooks").json()["webhooks"]] == [wid]
    assert router._state().get(router._GATEWAY, "webhook", wid)["url"] == "https://hooks.example.org/x"
    assert client.delete(f"/api/v1/webhook/{wid}").status_code == 200
    assert router._webhook_list() == []
    router._save_job("j1", {"status": "processing", "total": 1, "completed": 0, "results": []})
    assert client.get("/api/v1/batch/j1").json()["status"] == "interrupted"
