"""v8 Wave 0 security: a hostile web page or document must not drive the local server."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

EVIL = "https://evil.example"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "config" / "data"))
    monkeypatch.setenv("IMPACT_VISION_WEB_HOME", str(tmp_path / "oh-home"))
    monkeypatch.delenv("IMPACT_VISION_UPLOAD_DIR", raising=False)
    monkeypatch.delenv("IMPACT_VISION_API_KEY", raising=False)
    monkeypatch.delenv("IMPACT_VISION_ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("IMPACT_VISION_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("IMPACT_VISION_API_ALLOW_PATHS", raising=False)
    monkeypatch.chdir(tmp_path)
    from openharness.web import chat_session

    chat_session.reset_session_manager()
    yield
    chat_session.reset_session_manager()


@pytest.fixture
def client():
    from openharness.web.app import app

    with TestClient(app, base_url="http://127.0.0.1:8787") as c:
        yield c


# --------------------------------------------------------------- Host / Origin


def test_dns_rebinding_host_is_refused(client):
    r = client.get("/api/v1/chat/providers", headers={"Host": "evil.example:8787"})
    assert r.status_code == 403


def test_cross_origin_state_change_is_refused(client):
    r = client.post("/api/v1/chat/providers", json={"profile": "custom", "base_url": EVIL},
                    headers={"Origin": EVIL})
    assert r.status_code == 403
    r = client.post("/api/v1/chat/sessions", json={}, headers={"Origin": "null"})
    assert r.status_code == 403


def test_same_origin_and_non_browser_requests_work(client):
    assert client.post("/api/v1/chat/sessions", json={},
                       headers={"Origin": "http://127.0.0.1:8787"}).status_code == 200
    assert client.post("/api/v1/chat/sessions", json={}).status_code == 200  # curl: no Origin


def test_no_wildcard_cors(client):
    r = client.options("/api/v1/chat/providers", headers={
        "Origin": EVIL, "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") not in {"*", EVIL}


def test_cross_origin_websocket_is_refused(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/chat", headers={"Origin": EVIL}) as ws:
            ws.receive_json()


def test_listed_cors_origin_is_allowed(client, monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_CORS_ORIGINS", "https://dash.example")
    r = client.post("/api/v1/chat/sessions", json={}, headers={"Origin": "https://dash.example"})
    assert r.status_code == 200


def test_with_api_key_hosts_are_free_but_token_required(client, monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_API_KEY", "s3cret")
    host = {"Host": "impact.example.org"}
    assert client.get("/api/v1/chat/sessions", headers=host).status_code == 401
    ok = client.get("/api/v1/chat/sessions", headers={**host, "Authorization": "Bearer s3cret"})
    assert ok.status_code == 200


def test_websocket_token_via_subprotocol(client, monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_API_KEY", "s3cret")
    with client.websocket_connect("/ws/chat", subprotocols=["iv", "bearer.s3cret"]) as ws:
        assert ws.receive_json()["type"]
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/chat", subprotocols=["iv", "bearer.wrong"]) as ws:
            ws.receive_json()


def test_launch_token_only_beyond_loopback(monkeypatch):
    from openharness.api_gateway.security import ensure_launch_token

    assert ensure_launch_token("127.0.0.1") is None
    token = ensure_launch_token("0.0.0.0")
    assert token and len(token) >= 24
    import os

    assert os.environ.pop("IMPACT_VISION_API_KEY") == token


# ----------------------------------------------------------- provider re-key


def test_repointing_a_keyed_profile_needs_the_key_again(client):
    first = client.post("/api/v1/chat/providers", json={
        "profile": "custom", "base_url": "https://llm.internal/v1", "api_key": "sk-real"})
    assert first.status_code == 200
    moved = client.post("/api/v1/chat/providers", json={"profile": "custom", "base_url": EVIL})
    assert moved.status_code == 400 and "re-enter" in moved.json()["detail"]
    rekeyed = client.post("/api/v1/chat/providers", json={
        "profile": "custom", "base_url": "https://llm2.internal/v1", "api_key": "sk-new"})
    assert rekeyed.status_code == 200
    local = client.post("/api/v1/chat/providers", json={
        "profile": "custom", "base_url": "http://localhost:1234/v1"})
    assert local.status_code == 200
    same = client.post("/api/v1/chat/providers", json={"profile": "custom", "model": "m2"})
    assert same.status_code == 200


# ------------------------------------------------------------ routes & files


def test_legacy_pitch_deck_route_refuses_server_paths(client):
    r = client.post("/api/v1/pitch-deck", json={"file_path": "/etc/hosts.md"})
    assert r.status_code == 400
    r = client.post("/api/v1/pitch-deck", json={"url": "http://127.0.0.1:22/"})
    assert r.status_code == 400


def test_webhook_to_private_address_is_refused(client):
    r = client.post("/api/v1/webhook", json={"url": "http://169.254.169.254/latest", "events": ["tool_complete"]})
    assert r.status_code == 400


def test_url_fetch_rechecks_redirect_targets():
    from openharness.tools.impact.pitch_deck_analyze_tool import _ensure_public_url, _UrlFetchError

    for bad in ("http://127.0.0.1/", "http://10.0.0.5/x", "file:///etc/passwd"):
        with pytest.raises(_UrlFetchError):
            _ensure_public_url(bad)


def test_download_refuses_hidden_and_non_document_files(client, tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]")
    (tmp_path / ".env").write_text("SECRET=1")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "notes.md").write_text("x")
    (tmp_path / "report.html").write_text("<p>ok</p>")
    get = lambda p: client.get("/api/v1/chat/artifacts/download", params={"path": str(p)})  # noqa: E731
    assert get(tmp_path / "pyproject.toml").status_code == 403
    assert get(tmp_path / ".env").status_code == 403
    assert get(tmp_path / ".git" / "notes.md").status_code == 403
    assert get(tmp_path / "report.html").status_code == 200


def test_uploads_live_outside_the_workspace(client, tmp_path):
    saved = client.post("/api/v1/chat/uploads", files={"files": ("deck.md", b"# Deck", "text/markdown")})
    path = Path(saved.json()["files"][0]["path"])
    assert tmp_path / "oh-home" in path.parents
    assert not (tmp_path / ".impact-vision").exists()


def test_full_auto_cannot_be_set_from_the_web(client):
    r = client.post("/api/v1/chat/sessions", json={"permission_mode": "full_auto"})
    assert r.status_code == 403


# --------------------------------------------------------- agent containment


def test_fund_sessions_confine_file_access(tmp_path):
    from openharness.config.settings import PermissionSettings
    from openharness.permissions.checker import PermissionChecker

    checker = PermissionChecker(PermissionSettings(), confine_to=[tmp_path])
    inside = checker.evaluate("file_read_tool", is_read_only=True, file_path=str(tmp_path / "deck.md"))
    outside = checker.evaluate("file_read_tool", is_read_only=True, file_path="/etc/passwd")
    sneaky = checker.evaluate("file_read_tool", is_read_only=True, file_path=str(tmp_path / ".." / "x"))
    assert inside.allowed and not outside.allowed and not sneaky.allowed


def test_mode_change_keeps_confinement(tmp_path):
    from openharness.config.settings import PermissionSettings
    from openharness.engine.query_engine import QueryEngine
    from openharness.permissions.checker import PermissionChecker

    engine = QueryEngine.__new__(QueryEngine)
    engine._permission_checker = PermissionChecker(PermissionSettings(), confine_to=[tmp_path])  # noqa: SLF001
    engine.set_permission_checker(PermissionChecker(PermissionSettings()))
    assert engine._permission_checker.confine_to == [tmp_path.resolve()]  # noqa: SLF001


# ------------------------------------------------- found by the bandit gate (W5.7)


def test_legacy_report_header_escapes_company_text():
    from openharness.impact.report_templates.html_template import render_header

    html = render_header({"company": {"name": "<script>alert(1)</script>", "impact_themes": ["<b>x</b>"]}})
    assert "<script>alert" not in html and "&lt;script&gt;" in html
    assert "<style>" in html  # the trusted CSS still renders


def test_shared_fetcher_refuses_private_targets_and_schemes():
    from openharness.utils.safe_fetch import UnsafeUrlError, ensure_public_url

    for bad in ("http://169.254.169.254/latest/meta-data", "http://localhost:8787/", "ftp://example.com/x",
                "file:///etc/passwd"):
        with pytest.raises(UnsafeUrlError):
            ensure_public_url(bad)


def test_verifier_fetches_through_the_safe_fetcher(monkeypatch):
    from openharness.impact.extractors import llm_verifier

    with pytest.raises(Exception) as exc:
        llm_verifier._default_fetcher("http://127.0.0.1:22/")
    assert "non-public" in str(exc.value)
