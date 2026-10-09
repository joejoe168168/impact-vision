"""W3.2: offline deck analysis, inline report viewer and signed share links in the web app."""

from __future__ import annotations

import shutil
import time

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from impact_vision.impact.pipeline import sample_deck_path  # noqa: E402
from impact_vision.web import reports_api  # noqa: E402


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


def _upload_and_assess(client) -> dict:
    deck = sample_deck_path("solar").with_suffix(".md")
    with deck.open("rb") as fh:
        up = client.post("/api/v1/chat/uploads", files={"files": (deck.name, fh, "text/markdown")})
    assert up.status_code == 200
    res = client.post("/api/v1/chat/assess", json={"stored_name": up.json()["files"][0]["stored_name"]})
    assert res.status_code == 200, res.text
    return res.json()


def test_assess_view_and_files(client):
    rep = _upload_and_assess(client)
    assert rep["company"] == "SunPath Energy Ltd" and "report_data" not in rep
    assert rep["summary"]["gate"] and rep["assessment_id"]
    assert any(n.endswith("_data.xlsx") for n in rep["files"])
    assert client.get("/api/v1/chat/reports").json()["reports"][0]["id"] == rep["id"]

    lp = client.get(f"/api/v1/chat/reports/{rep['id']}/view", params={"audience": "lp", "lang": "zh-HK"})
    assert lp.status_code == 200 and '<html lang="zh-HK"' in lp.text
    assert 'id="sec-greenwashing"' not in lp.text
    assert client.get(f"/api/v1/chat/reports/{rep['id']}/view", params={"audience": "x"}).status_code == 422

    name = next(n for n in rep["files"] if n.endswith("_ic_memo.html"))
    assert client.get(f"/api/v1/chat/reports/{rep['id']}/files/{name}").status_code == 200
    assert client.get(f"/api/v1/chat/reports/{rep['id']}/files/report.json").status_code == 404
    assert client.get("/api/v1/chat/reports/../../etc/view").status_code == 404


def test_assess_rejects_paths_outside_uploads(client, tmp_path):
    outside = tmp_path / "secret.md"
    outside.write_text("secret", encoding="utf-8")
    for name in ("../secret.md", str(outside), "missing.md"):
        assert client.post("/api/v1/chat/assess", json={"stored_name": name}).status_code == 404


def test_share_links_are_signed_scoped_and_revocable(client):
    rep = _upload_and_assess(client)
    share = client.post(f"/api/v1/chat/reports/{rep['id']}/share",
                        json={"audience": "public", "lang": "en", "days": 7}).json()
    assert share["expires_at"] - time.time() == pytest.approx(7 * 86400, abs=60)

    page = client.get(share["path"])
    assert page.status_code == 200 and "SunPath" in page.text
    assert "Confidential" not in page.text and 'id="sec-verdict"' not in page.text
    assert page.headers["x-robots-tag"].startswith("noindex")
    assert page.headers["cache-control"] == "private, no-store"

    body, sig = share["path"].removeprefix("/shared/").split(".")
    assert client.get(f"/shared/{body}.{sig[:-2]}xx").status_code == 404      # tampered signature
    forged, _ = reports_api.make_share_token(rep["id"], audience="full")
    assert client.get(f"/shared/{forged}").status_code == 200                # same install key
    assert client.post(f"/api/v1/chat/reports/{rep['id']}/share", json={"audience": "boss"}).status_code == 422

    client.delete(f"/api/v1/chat/reports/{rep['id']}")
    assert client.get(share["path"]).status_code == 404                      # revoked


def test_share_tokens_expire_and_never_use_the_public_dev_key(client, tmp_path):
    token, exp = reports_api.make_share_token("0123456789abcdef", days=1, now=1_000_000)
    assert reports_api.read_share_token(token, now=1_000_000 + 3600)["r"] == "0123456789abcdef"
    with pytest.raises(ValueError, match="expired"):
        reports_api.read_share_token(token, now=exp + 1)
    key_file = reports_api.reports_dir() / ".share.key"
    assert key_file.exists() and (key_file.stat().st_mode & 0o077) == 0
    # a different install (new secret) cannot read the token
    shutil.rmtree(reports_api.reports_dir())
    with pytest.raises(ValueError):
        reports_api.read_share_token(token, now=1_000_000)


def test_chat_ui_has_analyze_flow():
    from impact_vision.web.chat_ui import render_chat_html

    html = render_chat_html()
    for needle in ("Analyze a pitch deck", "analyzeFiles", 'id="viewerFrame"', "createShare",
                   'data-tab="reports"', 'sandbox="allow-scripts'):
        assert needle in html
    assert "allow-same-origin" not in html
