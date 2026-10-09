"""Deal sources: Affinity and DealCloud lists, read-only (roadmap v8 W3.5).

Each list row becomes a :class:`Deal`. Which CRM field holds the stage,
sector or geography differs per fund, so the field names are settings
(``IMPACT_VISION_CRM_STAGE_FIELD`` …, defaults "Status" / "Stage", "Sector",
"Geography" / "Country"), and CRM stage names are mapped onto pipeline stages
by :func:`map_stage` (override with ``IMPACT_VISION_CRM_STAGE_MAP``, e.g.
``"Term sheet=ic_review,Portfolio=invested"``).
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx

from impact_vision.impact.connectors.base import Deal, env, http_client

_STAGE_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("passed", ("pass", "declin", "lost", "dead", "rejected")),
    ("exited", ("exit", "realis", "realiz", "sold")),
    ("monitoring", ("monitor", "portfolio")),
    ("invested", ("invested", "closed won", "funded", "closed")),
    ("ic_review", ("ic", "investment committee", "term sheet", "approval")),
    ("dd_in_progress", ("due diligence", "diligence", "dd")),
    ("screening", ("screen", "qualif", "first meeting", "review", "evaluat")),
    ("sourcing", ("lead", "new", "sourc", "prospect", "pipeline")),
)


def map_stage(value: str) -> str:
    """CRM stage name → pipeline stage ('' when unknown)."""
    raw = (value or "").strip()
    custom = dict(pair.split("=", 1) for pair in os.environ.get("IMPACT_VISION_CRM_STAGE_MAP", "").split(",")
                  if "=" in pair)
    custom = {k.strip().lower(): v.strip() for k, v in custom.items()}
    if raw.lower() in custom:
        return custom[raw.lower()]
    lowered = f" {raw.lower()} "
    for stage, words in _STAGE_WORDS:
        if any(f" {w}" in lowered for w in words):
            return stage
    return ""


def _setting(name: str, default: str) -> list[str]:
    raw = os.environ.get(f"IMPACT_VISION_CRM_{name}_FIELD", "") or default
    return [x.strip().lower() for x in raw.split("|") if x.strip()]


def _text(value: Any) -> str:
    """Flatten a CRM field value (text, number, dropdown, list, person…) to a string."""
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("data", "text", "name", "value", "displayValue"):
            if key in value:
                return _text(value[key])
        first, last = value.get("firstName"), value.get("lastName")
        return " ".join(x for x in (first, last) if x)
    if isinstance(value, list):
        return ", ".join(t for t in (_text(v) for v in value) if t)
    return str(value)


def _deal(name: str, fields: dict[str, str], source_id: str) -> Deal:
    lowered = {k.lower(): v for k, v in fields.items()}

    def pick(setting: str, default: str) -> str:
        return next((lowered[k] for k in _setting(setting, default) if lowered.get(k)), "")

    return Deal(name=name, stage=map_stage(pick("STAGE", "status|stage|deal stage")),
                sector=pick("SECTOR", "sector|industry"), geography=pick("GEOGRAPHY", "geography|country|region"),
                owner=pick("OWNER", "owner|deal lead|deal team"), source_id=source_id, fields=fields)


class AffinitySource:
    """Rows of an Affinity list via API v2 (``IMPACT_VISION_AFFINITY_KEY``, a v2 API key;
    ``IMPACT_VISION_AFFINITY_LIST`` the list ID). Needs "Export data from Lists"."""

    id = "affinity"
    API = "https://api.affinity.co"

    def __init__(self, list_id: str = "", *, token: str = "", transport: httpx.BaseTransport | None = None) -> None:
        self.list_id = list_id or env("IMPACT_VISION_AFFINITY_LIST")
        self.token = token or env("IMPACT_VISION_AFFINITY_KEY")
        self.client = http_client(transport)

    def list_deals(self) -> list[Deal]:
        url: str | None = f"{self.API}/v2/lists/{int(self.list_id)}/list-entries?limit=100&fieldTypes=list&fieldTypes=global"
        deals: list[Deal] = []
        while url:
            if not url.startswith(self.API + "/"):
                raise PermissionError("Affinity paging link points outside api.affinity.co")
            r = self.client.get(url, headers={"authorization": f"Bearer {self.token}"})
            r.raise_for_status()
            page = r.json()
            for row in page.get("data") or []:
                entity = row.get("entity") or {}
                fields = {f.get("name", ""): _text(f.get("value")) for f in entity.get("fields") or []
                          if f.get("name")}
                if entity.get("name"):
                    deals.append(_deal(entity["name"], fields, f"affinity:{row.get('id')}"))
            url = (page.get("pagination") or {}).get("nextUrl")
        return deals


class DealCloudSource:
    """Rows of a DealCloud entry type via the REST API (client credentials:
    ``IMPACT_VISION_DEALCLOUD_CLIENT_ID`` / ``_SECRET``; ``IMPACT_VISION_DEALCLOUD_URL``
    e.g. https://yourfund.dealcloud.com; ``IMPACT_VISION_DEALCLOUD_ENTRY_TYPE`` the
    entry type (e.g. Deal) ID)."""

    id = "dealcloud"

    def __init__(self, entry_type: str = "", *, base_url: str = "", client_id: str = "", client_secret: str = "",
                 name_field: str = "", transport: httpx.BaseTransport | None = None) -> None:
        self.base = (base_url or env("IMPACT_VISION_DEALCLOUD_URL")).rstrip("/")
        if not self.base.startswith("https://") or not self.base.split("/")[2].endswith(".dealcloud.com"):
            raise ValueError("IMPACT_VISION_DEALCLOUD_URL must be https://<tenant>.dealcloud.com")
        self.entry_type = entry_type or env("IMPACT_VISION_DEALCLOUD_ENTRY_TYPE")
        self.client_id = client_id or env("IMPACT_VISION_DEALCLOUD_CLIENT_ID")
        self.client_secret = client_secret or env("IMPACT_VISION_DEALCLOUD_SECRET")
        self.name_field = (name_field or os.environ.get("IMPACT_VISION_DEALCLOUD_NAME_FIELD", "") or "Name").lower()
        self.client = http_client(transport)
        self._token, self._expires = "", 0.0

    def _bearer(self) -> str:
        if not self._token or time.time() > self._expires - 60:
            r = self.client.post(f"{self.base}/api/rest/v1/oauth/token", data={
                "client_id": self.client_id, "client_secret": self.client_secret,
                "grant_type": "client_credentials", "scope": "data"})
            r.raise_for_status()
            body = r.json()
            self._token = body["access_token"]
            self._expires = time.time() + float(body.get("expires_in", 900))
        return self._token

    def list_deals(self) -> list[Deal]:
        deals: list[Deal] = []
        skip, limit = 0, 1000
        while True:
            r = self.client.get(f"{self.base}/api/rest/v4/data/entrydata/rows/{self.entry_type}",
                                params={"limit": limit, "skip": skip},
                                headers={"authorization": f"Bearer {self._bearer()}"})
            r.raise_for_status()
            page = r.json()
            rows = page.get("rows") or []
            for row in rows:
                fields = {str(k): _text(v) for k, v in row.items()}
                name = next((v for k, v in fields.items() if k.lower() == self.name_field and v), "")
                if name:
                    deals.append(_deal(name, fields, f"dealcloud:{row.get('EntryId', row.get('entryId', ''))}"))
            skip += len(rows)
            if not rows or skip >= int(page.get("totalRecords") or 0):
                return deals


__all__ = ["AffinitySource", "DealCloudSource", "map_stage"]
