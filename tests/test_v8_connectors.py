"""Read-only connectors and sync (roadmap v8 W3.5). HTTP is mocked."""
from __future__ import annotations

import httpx
import pytest

from impact_vision.impact.connectors import get_connector
from impact_vision.impact.connectors.crm import AffinitySource, DealCloudSource, map_stage
from impact_vision.impact.connectors.documents import FolderSource, GoogleDriveSource, SharePointSource
from impact_vision.impact.connectors.sync import sync_deals, sync_documents

DECK = b"# Sunlit Homes - Seed pitch\n\nSunlit Homes sells solar lanterns in Uganda.\n\n## Traction\n- 12,000 households served in 2024.\n"


def test_folder_source_lists_companies_and_stays_inside(tmp_path):
    (tmp_path / "Sunlit Homes").mkdir()
    (tmp_path / "Sunlit Homes" / "deck.md").write_bytes(DECK)
    (tmp_path / "Sunlit Homes" / "notes.exe").write_bytes(b"x")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "x.pdf").write_bytes(b"x")
    src = FolderSource(tmp_path)
    docs = src.list_documents()
    assert [(d.name, d.company) for d in docs] == [("deck.md", "Sunlit Homes")]
    assert src.fetch(docs[0]) == DECK
    with pytest.raises(PermissionError):
        src.fetch(type(docs[0])(id="../../etc/passwd", name="passwd"))


def test_sync_documents_copies_once_and_assesses(tmp_path):
    room = tmp_path / "room"
    (room / "Sunlit Homes").mkdir(parents=True)
    (room / "Sunlit Homes" / "deck.md").write_bytes(DECK)
    out = sync_documents(FolderSource(room), assess=True, target=tmp_path / "inbox")
    assert len(out["copied"]) == 1 and out["assessed"][0]["assessment_id"] and not out["errors"]
    again = sync_documents(FolderSource(room), target=tmp_path / "inbox")
    assert again["copied"] == [] and again["unchanged"] == 1


def test_google_drive_lists_folders_exports_google_docs():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer gtok"
        q = request.url.params.get("q", "")
        if request.url.path.endswith("/files") and "'root1'" in q:
            return httpx.Response(200, json={"files": [
                {"id": "f1", "name": "Sunlit", "mimeType": "application/vnd.google-apps.folder"},
                {"id": "d0", "name": "fund.pdf", "mimeType": "application/pdf", "size": "10"}]})
        if request.url.path.endswith("/files") and "'f1'" in q:
            return httpx.Response(200, json={"files": [
                {"id": "g1", "name": "Memo", "mimeType": "application/vnd.google-apps.document"},
                {"id": "z1", "name": "photo.jpg", "mimeType": "image/jpeg"}]})
        if request.url.path.endswith("/files/g1/export"):
            assert request.url.params["mimeType"] == "application/pdf"
            return httpx.Response(200, content=b"%PDF-export")
        if request.url.path.endswith("/files/d0"):
            assert request.url.params["alt"] == "media"
            return httpx.Response(200, content=b"%PDF-raw")
        return httpx.Response(404)

    src = GoogleDriveSource("root1", token="gtok", transport=httpx.MockTransport(handler))
    docs = {d.name: d for d in src.list_documents()}
    assert set(docs) == {"fund.pdf", "Memo.pdf"} and docs["Memo.pdf"].company == "Sunlit"
    assert src.fetch(docs["Memo.pdf"]) == b"%PDF-export" and src.fetch(docs["fund.pdf"]) == b"%PDF-raw"


def test_sharepoint_pages_and_refuses_foreign_links():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "root:/Deals:/children" in str(request.url):
            return httpx.Response(200, json={"value": [{"id": "1", "name": "a.pdf", "file": {}}],
                                             "@odata.nextLink": "https://graph.microsoft.com/v1.0/next"})
        if str(request.url).endswith("/next"):
            return httpx.Response(200, json={"value": [{"id": "2", "name": "b.docx", "file": {}}]})
        return httpx.Response(404)

    src = SharePointSource("drv", "Deals", token="t", transport=httpx.MockTransport(handler))
    assert [d.name for d in src.list_documents()] == ["a.pdf", "b.docx"]

    def evil(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"value": [], "@odata.nextLink": "https://evil.example/steal"})

    with pytest.raises(PermissionError):
        SharePointSource("drv", "Deals", token="t", transport=httpx.MockTransport(evil)).list_documents()


def test_stage_mapping():
    assert map_stage("Due Diligence") == "dd_in_progress"
    assert map_stage("IC / Term sheet") == "ic_review"
    assert map_stage("Closed Lost") == "passed"
    assert map_stage("Portfolio") == "monitoring"
    assert map_stage("Weird") == ""


def test_affinity_rows_become_deals_and_sync_into_the_pipeline(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer akey"
        assert request.url.path == "/v2/lists/42/list-entries"
        if "cursor" not in str(request.url):
            return httpx.Response(200, json={"data": [
                {"id": 1, "type": "company", "entity": {"name": "Sunlit Homes", "fields": [
                    {"name": "Status", "value": {"type": "dropdown", "data": {"text": "Due Diligence"}}},
                    {"name": "Sector", "value": {"type": "text", "data": "energy"}}]}}],
                "pagination": {"nextUrl": "https://api.affinity.co/v2/lists/42/list-entries?cursor=abc"}})
        return httpx.Response(200, json={"data": [
            {"id": 2, "type": "company", "entity": {"name": "Agua Viva", "fields": []}}],
            "pagination": {"nextUrl": None}})

    src = AffinitySource("42", token="akey", transport=httpx.MockTransport(handler))
    deals = src.list_deals()
    assert [(d.name, d.stage, d.sector) for d in deals] == [("Sunlit Homes", "dd_in_progress", "energy"),
                                                           ("Agua Viva", "", "")]
    out = sync_deals(src)
    assert out["added"] == ["Sunlit Homes", "Agua Viva"] and out["stage_not_mapped"] == ["Agua Viva"]
    from impact_vision.impact.storage import get_assessment_store

    assert get_assessment_store().get_pipeline_entry("Sunlit Homes")["pipeline_stage"] == "dd_in_progress"


def test_dealcloud_token_paging_and_stage_moves():
    tokens = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/rest/v1/oauth/token":
            body = dict(x.split("=") for x in request.content.decode().split("&"))
            assert body["grant_type"] == "client_credentials" and body["scope"] == "data"
            tokens.append(1)
            return httpx.Response(200, json={"access_token": "dc", "expires_in": 900})
        assert request.headers["authorization"] == "Bearer dc"
        skip = int(request.url.params["skip"])
        rows = [{"EntryId": 7, "Name": "Sunlit Homes", "Stage": {"name": "IC"}}] if skip == 0 else []
        return httpx.Response(200, json={"rows": rows, "totalRecords": 1})

    src = DealCloudSource("2011", base_url="https://fund.dealcloud.com", client_id="c", client_secret="s",
                          transport=httpx.MockTransport(handler))
    from impact_vision.impact.storage import get_assessment_store

    get_assessment_store().upsert_pipeline_entry("Sunlit Homes", pipeline_stage="screening")
    out = sync_deals(src)
    assert out["moved"] == [{"company": "Sunlit Homes", "from": "screening", "to": "ic_review"}]
    assert len(tokens) == 1
    with pytest.raises(ValueError):
        DealCloudSource("1", base_url="https://evil.example", client_id="c", client_secret="s")


def test_registry_and_missing_settings(monkeypatch):
    monkeypatch.delenv("IMPACT_VISION_GDRIVE_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="IMPACT_VISION_GDRIVE"):
        get_connector("gdrive")
    with pytest.raises(ValueError):
        get_connector("dropbox")
