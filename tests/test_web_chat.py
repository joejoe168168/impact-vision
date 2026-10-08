"""Tests for the web chat UI, its REST surface and the WebSocket protocol."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from openharness.api.client import ApiMessageCompleteEvent, ApiTextDeltaEvent  # noqa: E402
from openharness.api.usage import UsageSnapshot  # noqa: E402
from openharness.engine.messages import ConversationMessage, TextBlock  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class ScriptedApiClient:
    """Streams a fixed assistant reply so tests never touch a real provider."""

    def __init__(self, chunks: list[str] | None = None) -> None:
        self.chunks = chunks or ["Impact ", "Vision ", "here."]
        self.calls = 0

    async def stream_message(self, request):  # noqa: ANN001 - protocol shape
        del request
        self.calls += 1
        for chunk in self.chunks:
            yield ApiTextDeltaEvent(text=chunk)
        text = "".join(self.chunks)
        yield ApiMessageCompleteEvent(
            message=ConversationMessage(role="assistant", content=[TextBlock(text=text)]),
            usage=UsageSnapshot(input_tokens=10, output_tokens=len(self.chunks)),
            stop_reason="end_turn",
        )


@pytest.fixture(autouse=True)
def isolated_web_home(tmp_path, monkeypatch):
    """Keep settings, transcripts and uploads inside the test's tmp dir.

    ``OPENHARNESS_CONFIG_DIR`` matters most: without it the provider-config
    tests would rewrite the developer's real ``~/.openharness/settings.json``.
    """
    monkeypatch.setenv("OPENHARNESS_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "config" / "data"))
    monkeypatch.setenv("IMPACT_VISION_WEB_HOME", str(tmp_path / "oh-home"))
    monkeypatch.setenv("IMPACT_VISION_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
    monkeypatch.delenv("IMPACT_VISION_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    from openharness.web import chat_session

    chat_session.reset_session_manager()
    yield
    chat_session.reset_session_manager()


@pytest.fixture
def client():
    from openharness.web.app import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def scripted(monkeypatch):
    """Make every new session use the scripted client instead of a live one."""
    from openharness.web import chat_session

    fake = ScriptedApiClient()
    original = chat_session.ChatSession.ensure_started

    async def patched(self):
        self.options.api_client = fake
        await original(self)

    monkeypatch.setattr(chat_session.ChatSession, "ensure_started", patched)
    return fake


# ---------------------------------------------------------------------------
# UI document
# ---------------------------------------------------------------------------


def test_chat_ui_is_self_contained():
    from openharness.web.chat_ui import render_chat_html

    html = render_chat_html()
    assert html.startswith("<!DOCTYPE html>")
    assert "/*__CSS__*/" not in html and "/*__JS__*/" not in html
    # Zero build step: no external scripts or stylesheets.
    assert "<script src=" not in html
    assert "cdn." not in html
    assert 'id="input"' in html and 'id="thread"' in html
    assert "/ws/chat" in html


def test_ui_routes_are_mounted(client):
    assert client.get("/").status_code == 200
    assert client.get("/chat").status_code == 200
    # The original tool console keeps working, just no longer at "/".
    console = client.get("/console")
    assert console.status_code == 200
    assert "Web Console" in console.text
    assert "Impact Vision" in client.get("/").text


def test_rest_gateway_still_served(client):
    assert client.get("/api/v1/health").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/v1/score" in schema["paths"]


# ---------------------------------------------------------------------------
# REST: sessions
# ---------------------------------------------------------------------------


def test_bootstrap_payload(client):
    payload = client.get("/api/v1/chat/bootstrap").json()
    assert payload["sessions"] == []
    assert payload["provider"]["active_profile"]
    assert payload["provider"]["profiles"]
    assert Path(payload["uploads_dir"]).name == "uploads"


def test_session_crud(client):
    created = client.post("/api/v1/chat/sessions", json={"title": "Portfolio review"}).json()
    session_id = created["session"]["session_id"]

    listed = client.get("/api/v1/chat/sessions").json()["sessions"]
    assert [s["session_id"] for s in listed] == [session_id]
    assert listed[0]["title"] == "Portfolio review"

    assert client.patch(f"/api/v1/chat/sessions/{session_id}", json={"title": "Renamed"}).status_code == 200
    assert client.get("/api/v1/chat/sessions").json()["sessions"][0]["title"] == "Renamed"

    snapshot = client.get(f"/api/v1/chat/sessions/{session_id}").json()
    assert snapshot["type"] == "snapshot"
    assert snapshot["transcript"] == []

    assert client.delete(f"/api/v1/chat/sessions/{session_id}").status_code == 200
    assert client.get("/api/v1/chat/sessions").json()["sessions"] == []
    assert client.get(f"/api/v1/chat/sessions/{session_id}").status_code == 404


def test_sessions_survive_a_restart(client):
    from openharness.web import chat_session

    created = client.post("/api/v1/chat/sessions", json={"title": "Persisted"}).json()
    session_id = created["session"]["session_id"]

    # Simulate a fresh process: drop the in-memory registry entirely.
    chat_session.reset_session_manager()

    listed = client.get("/api/v1/chat/sessions").json()["sessions"]
    assert [s["title"] for s in listed] == ["Persisted"]
    assert client.get(f"/api/v1/chat/sessions/{session_id}").json()["session_id"] == session_id


# ---------------------------------------------------------------------------
# REST: provider configuration
# ---------------------------------------------------------------------------


def test_provider_snapshot_shape(client):
    payload = client.get("/api/v1/chat/providers").json()
    names = {p["name"] for p in payload["profiles"]}
    assert {"claude-api", "openai-compatible"} <= names
    assert payload["claude_models"]
    assert "openai" in payload["suggested_models"]


def test_provider_update_persists(client, tmp_path):
    response = client.post(
        "/api/v1/chat/providers",
        json={
            "profile": "openai-compatible",
            "model": "gpt-5.4",
            "base_url": "http://localhost:11434/v1",
            "make_active": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["active_profile"] == "openai-compatible"
    profile = next(p for p in payload["profiles"] if p["name"] == "openai-compatible")
    assert profile["base_url"] == "http://localhost:11434/v1"
    assert profile["model"] == "gpt-5.4"


def test_unknown_provider_rejected(client):
    response = client.post("/api/v1/chat/providers", json={"profile": "does-not-exist"})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# REST: uploads and artifacts
# ---------------------------------------------------------------------------


def test_upload_lands_in_the_workspace(client):
    response = client.post(
        "/api/v1/chat/uploads",
        files={"files": ("Impact Memo.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 200
    saved = response.json()["files"][0]
    assert saved["name"] == "Impact Memo.pdf"
    assert saved["stored_name"].endswith("Impact_Memo.pdf")
    assert Path(saved["path"]).read_bytes() == b"%PDF-1.4 fake"


def test_upload_filename_is_sanitised(client):
    response = client.post(
        "/api/v1/chat/uploads",
        files={"files": ("../../etc/passwd.txt", b"nope", "text/plain")},
    )
    saved = response.json()["files"][0]
    assert ".." not in saved["stored_name"]
    from openharness.web.chat_api import uploads_dir

    assert Path(saved["path"]).parent == uploads_dir()


def test_upload_refuses_non_document_types(client):
    response = client.post("/api/v1/chat/uploads", files={"files": ("tool.exe", b"MZ", "application/octet-stream")})
    assert response.status_code == 415


def test_download_refuses_paths_outside_the_workspace(client, tmp_path):
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("classified")
    response = client.get("/api/v1/chat/artifacts/download", params={"path": str(outside)})
    assert response.status_code in (403, 404)


def test_download_serves_workspace_files(client, tmp_path):
    target = tmp_path / "report.md"
    target.write_text("# Impact report")
    response = client.get("/api/v1/chat/artifacts/download", params={"path": str(target)})
    assert response.status_code == 200
    assert response.text == "# Impact report"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_api_key_is_enforced_when_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("IMPACT_VISION_API_KEY", "topsecret")
    import importlib

    from openharness.api_gateway import router as gateway

    importlib.reload(gateway)
    try:
        from openharness.web.chat_api import build_chat_router
        from fastapi import FastAPI

        probe = FastAPI()
        probe.include_router(build_chat_router(auth_dependency=gateway.verify_api_key))
        with TestClient(probe) as probe_client:
            assert probe_client.get("/api/v1/chat/sessions").status_code == 401
            ok = probe_client.get(
                "/api/v1/chat/sessions", headers={"Authorization": "Bearer topsecret"}
            )
            assert ok.status_code == 200
    finally:
        monkeypatch.delenv("IMPACT_VISION_API_KEY", raising=False)
        importlib.reload(gateway)


def test_websocket_rejects_a_bad_token(client, monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_API_KEY", "topsecret")
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/chat?token=wrong") as ws:
            ws.receive_json()


# ---------------------------------------------------------------------------
# WebSocket protocol
# ---------------------------------------------------------------------------


def _drain(ws, until: str, limit: int = 60) -> list[dict]:
    events: list[dict] = []
    for _ in range(limit):
        event = ws.receive_json()
        events.append(event)
        if event.get("type") == until:
            return events
    raise AssertionError(f"never saw {until!r}; got {[e.get('type') for e in events]}")


def test_websocket_sends_a_snapshot_and_ready(client):
    with client.websocket_connect("/ws/chat") as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "snapshot"
        assert snapshot["session_id"]
        ready = _drain(ws, "ready")[-1]
        assert any(c["name"] == "/help" for c in ready["commands"])
        assert ready["state"]["model"]


def test_slash_command_runs_without_the_model(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.receive_json()
        _drain(ws, "ready")
        ws.send_json({"type": "submit", "text": "/help"})
        events = _drain(ws, "turn_complete")
        rows = [e["item"] for e in events if e.get("type") == "transcript_item"]
        assert rows[0]["role"] == "user" and rows[0]["text"] == "/help"
        assert any("Available commands" in r["text"] for r in rows if r["role"] == "system")


def test_streaming_turn_emits_deltas_then_completion(client, scripted):
    with client.websocket_connect("/ws/chat") as ws:
        ws.receive_json()
        _drain(ws, "ready")
        ws.send_json({"type": "submit", "text": "Summarise IRIS+ in one line."})
        events = _drain(ws, "turn_complete", limit=120)

        kinds = [e["type"] for e in events]
        assert "assistant_delta" in kinds
        assert "assistant_complete" in kinds
        deltas = "".join(e["text"] for e in events if e["type"] == "assistant_delta")
        assert deltas == "Impact Vision here."
        final = next(e for e in events if e["type"] == "assistant_complete")
        assert final["item"]["text"] == "Impact Vision here."
        assert scripted.calls == 1


def test_transcript_replays_on_reconnect(client, scripted):
    with client.websocket_connect("/ws/chat") as ws:
        snapshot = ws.receive_json()
        session_id = snapshot["session_id"]
        _drain(ws, "ready")
        ws.send_json({"type": "submit", "text": "hello"})
        _drain(ws, "turn_complete", limit=120)

    with client.websocket_connect(f"/ws/chat?session={session_id}") as ws:
        replay = ws.receive_json()
        assert replay["type"] == "snapshot"
        roles = [row["role"] for row in replay["transcript"]]
        assert roles == ["user", "assistant"]
        assert replay["transcript"][1]["text"] == "Impact Vision here."


def test_title_is_derived_from_the_first_message(client, scripted):
    with client.websocket_connect("/ws/chat") as ws:
        ws.receive_json()
        _drain(ws, "ready")
        ws.send_json({"type": "submit", "text": "Score Acme Solar on the 5 Dimensions"})
        events = _drain(ws, "turn_complete", limit=120)
        titles = [e["title"] for e in events if e.get("type") == "title"]
        assert titles and titles[0].startswith("Score Acme Solar")


def test_unknown_message_type_is_reported(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.receive_json()
        _drain(ws, "ready")
        ws.send_json({"type": "not-a-real-type"})
        for _ in range(20):
            event = ws.receive_json()
            if event.get("type") == "error":
                assert "Unknown message type" in event["message"]
                return
        raise AssertionError("no error event for an unknown message type")


def test_ping_pong(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.receive_json()
        ws.send_json({"type": "ping"})
        for _ in range(20):
            if ws.receive_json().get("type") == "pong":
                return
        raise AssertionError("no pong")


# ---------------------------------------------------------------------------
# Session internals
# ---------------------------------------------------------------------------


def test_artifacts_are_tracked_from_write_tools(tmp_path):
    from openharness.web.chat_session import ChatSession

    written = tmp_path / "impact-report.html"
    written.write_text("<h1>report</h1>")

    session = ChatSession()
    session._last_tool_inputs["write_file"] = {"path": str(written)}
    session._maybe_record_artifact("write_file")
    session._maybe_record_artifact("write_file")  # deduplicated

    assert [a.name for a in session.artifacts] == ["impact-report.html"]
    assert session.artifacts[0].as_dict()["exists"] is True


def test_impact_report_output_path_is_captured(tmp_path):
    """``impact_report`` takes ``output_path`` rather than ``path``."""
    from openharness.web.chat_session import ChatSession

    report = tmp_path / "acme-impact.xlsx"
    report.write_bytes(b"PK fake xlsx")

    session = ChatSession()
    session._last_tool_inputs["impact_report"] = {"output_path": str(report), "output_format": "xlsx"}
    session._maybe_record_artifact("impact_report", f"XLSX report saved to: {report}")

    assert [a.name for a in session.artifacts] == ["acme-impact.xlsx"]


def test_saved_to_line_captures_files_from_any_tool(tmp_path):
    from openharness.web.chat_session import ChatSession

    deck = tmp_path / "ddq.csv"
    deck.write_text("a,b\n")

    session = ChatSession()
    session._maybe_record_artifact("some_future_tool", f"Export saved to: {deck}\nRows: 1")
    assert [a.name for a in session.artifacts] == ["ddq.csv"]


def test_reader_tools_produce_no_artifacts(tmp_path):
    """A path the agent merely *read* must not show up as an artifact."""
    from openharness.web.chat_session import ChatSession

    source = tmp_path / "notes.md"
    source.write_text("# notes")

    session = ChatSession()
    session._last_tool_inputs["read_file"] = {"path": str(source)}
    session._maybe_record_artifact("read_file", "# notes")

    session._last_tool_inputs["grep"] = {"pattern": "IRIS"}
    session._maybe_record_artifact("grep", "3 matches")

    assert session.artifacts == []


def test_missing_files_are_not_recorded(tmp_path):
    from openharness.web.chat_session import ChatSession

    session = ChatSession()
    session._last_tool_inputs["write_file"] = {"path": str(tmp_path / "never-written.md")}
    session._maybe_record_artifact("write_file")
    assert session.artifacts == []


def test_transcript_is_persisted_and_restored(tmp_path):
    from openharness.web.chat_session import ChatSession, web_chat_dir

    session = ChatSession(title="Saved chat")
    session._record({"role": "user", "text": "hello"})
    session.persist()

    stored = json.loads((web_chat_dir() / f"{session.session_id}.json").read_text())
    assert stored["title"] == "Saved chat"

    restored = ChatSession.from_stored(stored)
    assert restored.session_id == session.session_id
    assert restored.transcript[0]["text"] == "hello"


def test_permission_resolution_round_trip():
    import asyncio

    from openharness.web.chat_session import ChatSession

    session = ChatSession()

    async def scenario():
        task = asyncio.create_task(session._ask_permission("Bash", "rm -rf build/"))
        await asyncio.sleep(0.05)
        request_id = next(iter(session._permission_requests))
        assert session.resolve_permission(request_id, True) is True
        assert await task is True
        # A stale id is a no-op rather than an exception.
        assert session.resolve_permission("nope", True) is False

    asyncio.run(scenario())
