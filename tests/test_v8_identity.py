"""OIDC sign-in, RBAC and tenant isolation (roadmap v8 W5.3)."""
from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from impact_vision.api_gateway import oidc
from impact_vision.impact.identity import Identity, TenantGuard, acting_as, tenant_home
from impact_vision.impact.state_store import MemoryStateStore

ISSUER = "https://idp.example.org"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def idp(monkeypatch, tmp_path):
    monkeypatch.setenv("IMPACT_VISION_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("IMPACT_VISION_OIDC_CLIENT_ID", "iv-web")
    monkeypatch.setenv("IMPACT_VISION_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("IMPACT_VISION_WEB_HOME", str(tmp_path))
    monkeypatch.setenv("IMPACT_VISION_OIDC_ADMINS", "boss@fund-a.org")
    monkeypatch.setattr(oidc, "_DISCOVERY", {})
    issued: dict = {}

    async def fetch_json(url):
        assert url == ISSUER + "/.well-known/openid-configuration"
        return {"issuer": ISSUER, "authorization_endpoint": ISSUER + "/authorize",
                "token_endpoint": ISSUER + "/token", "jwks_uri": ISSUER + "/jwks",
                "id_token_signing_alg_values_supported": ["RS256"]}

    async def post_form(url, data):
        assert data["code"] == "good-code" and data["code_verifier"]
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": "iv-web", "sub": issued["sub"], "email": issued["email"],
                  "nonce": issued.get("nonce", ""), "iat": now, "exp": now + 300, **issued.get("extra", {})}
        return {"id_token": jwt.encode(claims, KEY, algorithm="RS256")}

    monkeypatch.setattr(oidc, "fetch_json", fetch_json)
    monkeypatch.setattr(oidc, "post_form", post_form)
    monkeypatch.setattr(oidc, "signing_key", lambda uri, token: KEY.public_key())
    return issued


def _client():
    from impact_vision.web.app import app

    return TestClient(app, base_url="http://127.0.0.1:8788")


def _sign_in(client, issued, sub, email, **extra):
    r = client.get("/auth/login", params={"next": "/api/v1/chat/sessions"}, follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["code_challenge_method"] == ["S256"] and q["client_id"] == ["iv-web"]
    issued.update(sub=sub, email=email, nonce=q["nonce"][0], extra=extra)
    r = client.get("/auth/callback", params={"code": "good-code", "state": q["state"][0]}, follow_redirects=False)
    assert r.status_code == 302, r.text
    assert r.headers["location"] == "/api/v1/chat/sessions"
    return client


def test_requests_need_sign_in(idp):
    client = _client()
    assert client.get("/api/v1/chat/sessions").status_code == 401
    page = client.get("/", headers={"accept": "text/html"}, follow_redirects=False)
    assert page.status_code == 302 and page.headers["location"].startswith("/auth/login")
    assert client.get("/auth/me").status_code == 401


def test_sign_in_sets_tenant_and_roles(idp):
    client = _sign_in(_client(), idp, "u1", "ana@fund-a.org")
    me = client.get("/auth/me").json()
    assert me["tenant"] == "fund-a.org" and me["roles"] == ["analyst"]
    boss = _sign_in(_client(), idp, "u2", "boss@fund-a.org").get("/auth/me").json()
    assert "tenant_admin" in boss["roles"]


def test_bad_state_or_nonce_is_refused(idp):
    client = _client()
    r = client.get("/auth/login", follow_redirects=False)
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert client.get("/auth/callback", params={"code": "good-code", "state": "forged"}).status_code == 400
    idp.update(sub="u1", email="a@x.org", nonce="wrong")
    r = client.get("/auth/callback", params={"code": "good-code", "state": q["state"][0]})
    assert r.status_code == 401 and "nonce" in r.text


def test_viewer_cannot_write_or_change_providers(idp):
    client = _sign_in(_client(), idp, "v1", "viewer@fund-a.org", roles=["viewer"])
    assert client.get("/api/v1/chat/sessions").status_code == 200
    assert client.post("/api/v1/chat/sessions", json={}).status_code == 403
    assert client.get("/api/v1/chat/providers").status_code == 403


def test_sessions_are_isolated_by_tenant_and_owner(idp):
    a = _sign_in(_client(), idp, "a1", "ana@fund-a.org")
    sid = a.post("/api/v1/chat/sessions", json={"title": "Deal A"}).json()["session"]["session_id"]
    assert a.get(f"/api/v1/chat/sessions/{sid}").status_code == 200
    b = _sign_in(_client(), idp, "b1", "bo@fund-b.org")
    assert b.get(f"/api/v1/chat/sessions/{sid}").status_code == 404
    assert all(s["session_id"] != sid for s in b.get("/api/v1/chat/sessions").json()["sessions"])
    colleague = _sign_in(_client(), idp, "a2", "cy@fund-a.org")
    assert colleague.get(f"/api/v1/chat/sessions/{sid}").status_code == 404
    admin = _sign_in(_client(), idp, "a3", "boss@fund-a.org")
    assert admin.get(f"/api/v1/chat/sessions/{sid}").status_code == 200


def test_state_store_and_paths_are_tenant_scoped(tmp_path):
    raw = MemoryStateStore()
    guard = TenantGuard(raw, "fund-a.org")
    guard.put("default", "k", "x", {"v": 1})
    assert raw.get("fund-a.org", "k", "x") == {"v": 1} and raw.get("default", "k", "x") is None
    with pytest.raises(PermissionError):
        guard.get("fund-b.org", "k", "x")
    assert tenant_home(tmp_path, "default") == tmp_path
    assert tenant_home(tmp_path, "fund-a.org") == tmp_path / "tenants" / "fund-a.org"
    with pytest.raises(PermissionError):
        tenant_home(tmp_path, "../etc")


def test_assessment_db_is_per_tenant(monkeypatch, tmp_path):
    from impact_vision.impact import storage

    monkeypatch.setattr(storage, "_global_store", storage.AssessmentStore(tmp_path / "iv.db"))
    storage.get_assessment_store().upsert_pipeline_entry("Shared Co", pipeline_stage="screening")
    with acting_as(Identity(sub="x", tenant_id="fund-a.org", auth="oidc")):
        mine = storage.get_assessment_store()
        assert Path(mine._db_path) == tmp_path / "tenants" / "fund-a.org" / "iv.db"
        assert mine.get_pipeline_entry("Shared Co") is None
    assert storage.get_assessment_store().get_pipeline_entry("Shared Co")


def test_local_mode_is_unchanged(monkeypatch):
    monkeypatch.delenv("IMPACT_VISION_OIDC_ISSUER", raising=False)
    client = _client()
    assert client.get("/api/v1/chat/sessions").status_code == 200
    assert client.get("/auth/me").json()["mode"] == "local"
