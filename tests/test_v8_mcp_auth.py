"""Authenticated, stateless MCP over HTTP (roadmap v8 W5.6)."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import httpx
import pytest

from impact_vision.impact.mcp_auth import TokenStore, build_app, tool_scope

HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


def _rpc(method: str, params: dict | None = None, id_: int = 1) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}})


@pytest.fixture
def store(tmp_path):
    return TokenStore(tmp_path / "tokens.json")


@asynccontextmanager
async def _client(store):
    app = build_app(store)
    async with app.app.router.lifespan_context(app.app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8765") as c:
            yield c


def test_tokens_are_hashed_scoped_and_revocable(store):
    token = store.create("analyst", ["read"])
    raw = store.path.read_text()
    assert token not in raw and "analyst" in raw
    assert oct(store.path.stat().st_mode)[-3:] == "600"
    who = store.verify(token)
    assert who and who.allows("read") and not who.allows("assess")
    assert store.verify("ivmcp_wrong") is None
    with pytest.raises(ValueError):
        store.create("analyst", ["read"])
    with pytest.raises(ValueError):
        store.create("x", ["root"])
    assert store.revoke("analyst") and store.verify(token) is None


def test_expired_token_is_refused(store, monkeypatch):
    token = store.create("temp", ["read"], days=1)
    import impact_vision.impact.mcp_auth as mod

    monkeypatch.setattr(mod.time, "time", lambda: 10**11)
    assert store.verify(token) is None


def test_scopes_cover_the_tool_surface():
    assert tool_scope("iris_catalog") == "read"
    assert tool_scope("pitch_deck_analyze") == "files"
    assert tool_scope("pipeline") == "write"
    assert tool_scope("five_dimension_assess") == "assess"


async def test_discovery_without_a_session(store):
    async with _client(store) as client:
        info = (await client.get("/.well-known/mcp.json")).json()
    assert info["stateless"] and info["auth"]["scheme"] == "bearer"
    assert {"name": "iris_catalog", "scope": "read"} in info["tools"]


async def test_requests_need_a_valid_token(store):
    async with _client(store) as client:
        r = await client.post("/mcp", content=_rpc("tools/list"), headers=HEADERS)
        assert r.status_code == 401 and "Bearer" in r.headers["www-authenticate"]
        r = await client.post("/mcp", content=_rpc("tools/list"),
                              headers={**HEADERS, "authorization": "Bearer nope"})
    assert r.status_code == 401


async def test_scoped_call_runs_and_is_audited(store):
    from impact_vision.impact.audit_trail import AuditTrail
    from impact_vision.impact.state_store import get_state_store

    token = store.create("reader", ["read"])
    auth = {**HEADERS, "authorization": f"Bearer {token}"}
    async with _client(store) as client:
        await _calls(client, auth)

    events = [r.payload for r in AuditTrail(fund_id="mcp", store=get_state_store()).feed.reports]
    outcomes = [(e["tool"], e["outcome"], e["actor"]) for e in events]
    assert ("iris_catalog", "ok", "reader") in outcomes
    assert ("pitch_deck_analyze", "denied", "reader") in outcomes
    assert all("/etc/passwd" not in json.dumps(e) for e in events)


async def _calls(client, auth):
    disc = (await client.post("/mcp", content=_rpc("server/discover"), headers=auth)).json()
    assert disc["result"]["endpoint"] == "/mcp"

    ok = await client.post("/mcp", headers=auth, content=_rpc(
        "tools/call", {"name": "iris_catalog", "arguments": {"action": "search", "query": "jobs", "limit": 2}}))
    assert ok.status_code == 200, ok.text
    assert "result" in ok.json()

    denied = await client.post("/mcp", headers=auth, content=_rpc(
        "tools/call", {"name": "pitch_deck_analyze", "arguments": {"file_path": "/etc/passwd"}}))
    assert denied.status_code == 403 and denied.json()["error"]["code"] == -32003



async def test_token_tenant_scopes_the_audit_and_state(store):
    from impact_vision.impact.audit_trail import AuditTrail
    from impact_vision.impact.state_store import get_state_store

    token = store.create("fund-b-bot", ["read"], tenant="fund-b")
    auth = {**HEADERS, "authorization": f"Bearer {token}"}
    async with _client(store) as client:
        ok = await client.post("/mcp", headers=auth, content=_rpc(
            "tools/call", {"name": "iris_catalog", "arguments": {"action": "search", "query": "jobs", "limit": 1}}))
        assert ok.status_code == 200
    default_events = [r.payload for r in AuditTrail(fund_id="mcp", store=get_state_store()).feed.reports]
    assert all(e["actor"] != "fund-b-bot" for e in default_events)
    raw = get_state_store()
    assert raw.get("fund-b", "audit_trail", "mcp")
    with pytest.raises(ValueError):
        store.create("bad", ["read"], tenant="../x")
