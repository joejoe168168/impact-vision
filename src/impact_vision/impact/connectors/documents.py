"""Document sources: data-room folder, Google Drive, SharePoint / OneDrive (v8 W3.5)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from impact_vision.impact.connectors.base import DocumentRef, env, http_client, supported

GOOGLE_DOC_TYPES = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.presentation": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class FolderSource:
    """A data-room export (or any synced folder). Top-level subfolders are companies."""

    id = "folder"

    def __init__(self, root: str | Path = "") -> None:
        self.root = Path(root or env("IMPACT_VISION_DATAROOM_DIR")).expanduser().resolve()
        if not self.root.is_dir():
            raise RuntimeError(f"{self.root} is not a folder")

    def list_documents(self) -> list[DocumentRef]:
        out = []
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root)
            if not path.is_file() or any(p.startswith(".") for p in rel.parts) or not supported(path.name):
                continue
            stat = path.stat()
            out.append(DocumentRef(
                id=str(rel), name=path.name, size=stat.st_size, source=self.id,
                modified=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
                company=rel.parts[0] if len(rel.parts) > 1 else ""))
        return out

    def fetch(self, doc: DocumentRef) -> bytes:
        path = (self.root / doc.id).resolve()
        if self.root not in path.parents:
            raise PermissionError("document is outside the data room")
        return path.read_bytes()


class GoogleDriveSource:
    """A Drive folder via the Drive API v3 (``IMPACT_VISION_GDRIVE_TOKEN``: an OAuth access
    token with the drive.readonly scope). Subfolders one level down are companies."""

    id = "gdrive"
    API = "https://www.googleapis.com/drive/v3"

    def __init__(self, folder_id: str = "", *, token: str = "", transport: httpx.BaseTransport | None = None) -> None:
        self.folder_id = folder_id or env("IMPACT_VISION_GDRIVE_FOLDER")
        self.token = token or env("IMPACT_VISION_GDRIVE_TOKEN")
        self.client = http_client(transport)

    def _get(self, path: str, **params: Any) -> httpx.Response:
        r = self.client.get(self.API + path, params=params, headers={"authorization": f"Bearer {self.token}"})
        r.raise_for_status()
        return r

    def _children(self, folder: str) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        token = None
        while True:
            params = {"q": f"'{folder}' in parents and trashed=false", "pageSize": 200,
                      "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size)"}
            if token:
                params["pageToken"] = token
            page = self._get("/files", **params).json()
            files.extend(page.get("files") or [])
            token = page.get("nextPageToken")
            if not token:
                return files

    def list_documents(self) -> list[DocumentRef]:
        out = []
        for item in self._children(self.folder_id):
            if item.get("mimeType") == "application/vnd.google-apps.folder":
                for child in self._children(item["id"]):
                    if ref := self._ref(child, item["name"]):
                        out.append(ref)
            elif ref := self._ref(item, ""):
                out.append(ref)
        return out

    def _ref(self, item: dict[str, Any], company: str) -> DocumentRef | None:
        mime = item.get("mimeType", "")
        name = item.get("name", "")
        if mime in GOOGLE_DOC_TYPES:
            name += ".xlsx" if "spreadsheet" in mime else ".pdf"
        elif not supported(name):
            return None
        return DocumentRef(id=f"{item['id']}|{mime}", name=name, modified=item.get("modifiedTime", ""),
                           size=int(item["size"]) if item.get("size") else None, company=company, source=self.id)

    def fetch(self, doc: DocumentRef) -> bytes:
        file_id, _, mime = doc.id.partition("|")
        if mime in GOOGLE_DOC_TYPES:
            return self._get(f"/files/{quote(file_id)}/export", mimeType=GOOGLE_DOC_TYPES[mime]).content
        return self._get(f"/files/{quote(file_id)}", alt="media").content


class SharePointSource:
    """A SharePoint / OneDrive folder via Microsoft Graph (``IMPACT_VISION_GRAPH_TOKEN``:
    an access token with Files.Read.All or Sites.Read.All)."""

    id = "sharepoint"
    API = "https://graph.microsoft.com/v1.0"

    def __init__(self, drive_id: str = "", folder_path: str = "", *, token: str = "",
                 transport: httpx.BaseTransport | None = None) -> None:
        self.drive_id = drive_id or env("IMPACT_VISION_SHAREPOINT_DRIVE")
        self.folder_path = (folder_path or os.environ.get("IMPACT_VISION_SHAREPOINT_PATH", "")).strip("/")
        self.token = token or env("IMPACT_VISION_GRAPH_TOKEN")
        self.client = http_client(transport)

    def _get(self, url: str) -> httpx.Response:
        if not url.startswith(self.API + "/"):
            raise PermissionError("Graph paging link points outside graph.microsoft.com")
        r = self.client.get(url, headers={"authorization": f"Bearer {self.token}"})
        r.raise_for_status()
        return r

    def _children(self, path: str) -> list[dict[str, Any]]:
        where = f"root:/{quote(path)}:" if path else "root"
        url: str | None = f"{self.API}/drives/{quote(self.drive_id)}/{where}/children?$top=200"
        items: list[dict[str, Any]] = []
        while url:
            page = self._get(url).json()
            items.extend(page.get("value") or [])
            url = page.get("@odata.nextLink")
        return items

    def list_documents(self) -> list[DocumentRef]:
        out = []
        for item in self._children(self.folder_path):
            if "folder" in item:
                sub = f"{self.folder_path}/{item['name']}".strip("/")
                out += [r for c in self._children(sub) if (r := self._ref(c, item["name"]))]
            elif ref := self._ref(item, ""):
                out.append(ref)
        return out

    def _ref(self, item: dict[str, Any], company: str) -> DocumentRef | None:
        if "file" not in item or not supported(item.get("name", "")):
            return None
        return DocumentRef(id=item["id"], name=item["name"], modified=item.get("lastModifiedDateTime", ""),
                           size=item.get("size"), company=company, source=self.id)

    def fetch(self, doc: DocumentRef) -> bytes:
        r = self.client.get(f"{self.API}/drives/{quote(self.drive_id)}/items/{quote(doc.id)}/content",
                            headers={"authorization": f"Bearer {self.token}"})
        if r.status_code in (301, 302, 303, 307, 308):
            # Graph answers with a short-lived pre-authenticated download URL; no token is sent there.
            location = r.headers.get("location", "")
            from impact_vision.utils.safe_fetch import ensure_public_url

            ensure_public_url(location)
            r = self.client.get(location)
        r.raise_for_status()
        return r.content


__all__ = ["FolderSource", "GoogleDriveSource", "SharePointSource"]
