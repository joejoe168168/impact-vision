"""U4: share links carry a notice, views are audited, and one link can be withdrawn."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from impact_vision.impact.pipeline import sample_deck_path  # noqa: E402
from impact_vision.web import reports_api  # noqa: E402


@pytest.fixture()
def events(monkeypatch):
    seen: list[tuple[str, dict, str]] = []
    monkeypatch.setattr(reports_api, "_audit_share",
                        lambda event_type, payload, *, actor: seen.append((event_type, payload, actor)))
    return seen


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_WEB_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("IMPACT_VISION_UPLOAD_DIR", str(tmp_path / "uploads"))
    from impact_vision.impact import storage

    monkeypatch.setattr(storage, "_global_store", storage.AssessmentStore(tmp_path / "iv.db"))
    monkeypatch.delenv("IMPACT_VISION_SHARE_HMAC_KEY", raising=False)
    monkeypatch.delenv("IMPACT_VISION_HMAC_KEY", raising=False)
    from impact_vision.web.app import app

    return TestClient(app)


@pytest.fixture()
def report_id(client) -> str:
    return reports_api.create_report(sample_deck_path("pig-farm"))["id"]


def _share(client, report_id: str, **body) -> dict:
    res = client.post(f"/api/v1/chat/reports/{report_id}/share", json={"audience": "lp", "days": 7, **body})
    assert res.status_code == 200, res.text
    return res.json()


def test_view_is_audited_once_and_shows_the_notice(client, report_id, events):
    share = _share(client, report_id)
    page = client.get(share["path"], headers={"user-agent": "Mozilla/5.0 Chrome/130.0"})
    assert page.status_code == 200
    day = datetime.fromtimestamp(share["expires_at"], tz=timezone.utc).strftime("%Y-%m-%d")
    assert f"Shared read-only · expires {day}" in page.text
    viewed = [e for e in events if e[0] == "report.share_viewed"]
    assert len(viewed) == 1
    payload = viewed[0][1]
    assert payload["jti"] == share["jti"] and payload["user_agent_family"] == "chrome" and not payload["preview"]
    assert "ip" not in payload and "Mozilla" not in str(payload)       # nothing identifying is stored
    row = client.get(f"/api/v1/chat/reports/{report_id}/shares").json()["shares"][0]
    assert row["status"] == "live" and row["views"] == 1 and row["previews"] == 0


def test_link_previews_are_counted_apart(client, report_id, events):
    share = _share(client, report_id)
    client.get(share["path"], headers={"user-agent": "Slackbot-LinkExpanding 1.0"})
    assert events[-1][1]["preview"] is True
    row = reports_api.list_shares(report_id)[0]
    assert row["views"] == 0 and row["previews"] == 1


def test_revoke_one_link_gives_410_and_leaves_the_other(client, report_id, events):
    first, second = _share(client, report_id), _share(client, report_id, audience="public")
    res = client.delete(f"/api/v1/chat/reports/{report_id}/shares/{first['jti']}")
    assert res.status_code == 200 and res.json()["revoked"]["revoked"] is True
    assert client.get(first["path"]).status_code == 410
    assert client.get(second["path"]).status_code == 200
    assert client.get(f"/api/v1/chat/reports/{report_id}").status_code == 200   # the report is still there
    status = {r["jti"]: r["status"] for r in reports_api.list_shares(report_id)}
    assert status == {first["jti"]: "revoked", second["jti"]: "live"}
    assert [e[0] for e in events].count("report.share_revoked") == 1
    assert client.delete(f"/api/v1/chat/reports/{report_id}/shares/nope").status_code == 404


def test_legacy_token_without_jti_still_opens(client, report_id, events):
    token, _ = reports_api.make_share_token(report_id, audience="lp")
    assert "j" not in reports_api.read_share_token(token)
    assert client.get(f"/shared/{token}").status_code == 200
    assert events[-1][1]["jti"] == "legacy"


def test_views_reach_the_audit_trail(client, report_id):
    from impact_vision.impact.audit_trail import AuditTrail
    from impact_vision.impact.identity import current_tenant
    from impact_vision.impact.state_store import get_state_store

    def length() -> int:
        return AuditTrail(tenant_id=current_tenant(), fund_id="reports", store=get_state_store()).length

    before = length()
    share = _share(client, report_id)
    assert client.get(share["path"]).status_code == 200
    assert length() == before + 2          # share_created + share_viewed


def test_banner_and_error_pages_are_translated(client, report_id):
    share = _share(client, report_id, lang="zh-HK")
    page = client.get(share["path"])
    day = datetime.fromtimestamp(share["expires_at"], tz=timezone.utc).strftime("%Y-%m-%d")
    assert f"唯讀分享 · {day} 到期" in page.text and "Shared read-only" not in page.text
    cn = _share(client, report_id, lang="zh-CN")
    client.delete(f"/api/v1/chat/reports/{report_id}/shares/{cn['jti']}")
    gone = client.get(cn["path"])
    assert gone.status_code == 410 and "<html lang='zh-CN'>" in gone.text and "发送人已撤回" in gone.text
    # A forged link has no trustworthy claims: the browser's language decides.
    bad = client.get("/shared/not-a-token", headers={"accept-language": "zh-HK,zh;q=0.9,en;q=0.8"})
    assert bad.status_code == 404 and "此分享連結無效" in bad.text
    assert "This share link is invalid" in client.get("/shared/not-a-token").text


def test_ui_reuses_one_live_link_per_edition_and_language(client, report_id, events):
    first = _share(client, report_id, reuse=True)
    again = _share(client, report_id, reuse=True)
    assert again["path"] == first["path"] and again["jti"] == first["jti"] and again["reused"]
    assert len([e for e in events if e[0] == "report.share_created"]) == 1
    other_lang = _share(client, report_id, reuse=True, lang="zh-HK")
    longer = _share(client, report_id, reuse=True, days=30)
    assert len({first["jti"], other_lang["jti"], longer["jti"]}) == 3
    assert client.get(again["path"]).status_code == 200
    # A withdrawn link is never handed out again.
    client.delete(f"/api/v1/chat/reports/{report_id}/shares/{first['jti']}")
    fresh = _share(client, report_id, reuse=True)
    assert fresh["jti"] != first["jti"] and not fresh["reused"]
    # Without reuse (the API default) every call issues its own link, as before.
    assert _share(client, report_id)["jti"] != fresh["jti"]
