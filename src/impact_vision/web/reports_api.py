"""Reports in the web app: analyse a deck, view it inline, share it read-only (v7 W3.2).

``POST /api/v1/chat/assess``                       run the offline pipeline on an upload
``GET  /api/v1/chat/reports``                      saved reports, newest first
``GET  /api/v1/chat/reports/{id}``                 one report's summary and files
``GET  /api/v1/chat/reports/{id}/view``            decision report HTML (audience/lang/theme)
``GET  /api/v1/chat/reports/{id}/files/{name}``    a deliverable (HTML, DOCX, XLSX, CSV, JSON)
``POST /api/v1/chat/reports/{id}/share``           signed, expiring read-only link
``GET  /api/v1/chat/portfolio/view``               portfolio home across all saved reports (W3.4)
``GET  /api/v1/chat/engagements``                  saved consultant engagements (summaries)
``GET  /api/v1/chat/engagements/view``             engagement view: deliverables, checklist, due dates
``GET  /shared/{token}``                           the shared report (no API key needed)

Share links are HMAC-signed with ``IMPACT_VISION_SHARE_HMAC_KEY`` (or
``IMPACT_VISION_HMAC_KEY``). Without one, a random per-install secret is
created next to the reports (never the public development key, which would
make links forgeable). Deleting a report revokes its links.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

try:
    from fastapi import APIRouter, Depends, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse
except ImportError as _exc:  # pragma: no cover - optional
    APIRouter = None  # type: ignore[assignment]
    _FASTAPI_IMPORT_ERROR: Exception | None = _exc
else:
    _FASTAPI_IMPORT_ERROR = None

from pydantic import BaseModel, Field

_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_AUDIENCES = ("full", "ic", "lp", "regulator", "public")
_LANGS = ("en", "zh-HK", "zh-CN")
SHARE_MAX_DAYS = 90
_SHARE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data: https:; "
        "script-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'; "
        "frame-ancestors 'self'"
    ),
}


# ---------------------------------------------------------------- storage


def _web_home() -> Path:
    return Path(os.environ.get("IMPACT_VISION_WEB_HOME", Path.home() / ".openharness"))


def reports_dir() -> Path:
    from impact_vision.impact.identity import tenant_home

    target = tenant_home(_web_home()) / "web-reports"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _report_path(report_id: str) -> Path:
    if not _ID_RE.match(report_id or ""):
        raise HTTPException(status_code=404, detail="Report not found")
    folder = reports_dir() / report_id
    if not (folder / "report.json").is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return folder


def load_report(report_id: str) -> dict[str, Any]:
    return json.loads((_report_path(report_id) / "report.json").read_text(encoding="utf-8"))


def _public(record: dict[str, Any]) -> dict[str, Any]:
    """The record without the bulky report payload."""
    return {k: v for k, v in record.items() if k != "report_data"}


def list_reports(limit: int = 50) -> list[dict[str, Any]]:
    rows = []
    for meta in reports_dir().glob("*/report.json"):
        try:
            rows.append(_public(json.loads(meta.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    rows.sort(key=lambda r: r.get("created_at", 0), reverse=True)
    return rows[:limit]


def create_report(source: Path | list[Path], *, name: str = "", sector: str = "", geography: str = "",
                  stage: str = "", label: str = "") -> dict[str, Any]:
    """Run the offline pipeline on *source* (one file or several) and store the report."""
    from impact_vision.impact.pipeline import assess_files, save_bundle, write_deliverables

    sources = list(source) if isinstance(source, (list, tuple)) else [source]
    source = sources[0]
    label = label or " + ".join(s.name for s in sources)
    bundle = assess_files(sources, name=name, sector=sector, geography=geography, stage=stage,
                          source_label=label)
    report_id = secrets.token_hex(8)
    folder = reports_dir() / report_id
    files = write_deliverables(bundle, folder)
    assessment_id = ""
    try:
        assessment_id = save_bundle(bundle, source_label=label or source.name)
    except Exception:  # noqa: BLE001 - the report is still useful without the DB row
        pass
    record = {
        "id": report_id,
        "created_at": time.time(),
        "company": bundle.company.name,
        "source": label or source.name,
        "assessment_id": assessment_id,
        # Kept so the report can be corrected and re-run on the same files.
        "inputs": {"stored_names": [s.name for s in sources], "name": name, "sector": sector,
                   "geography": geography, "stage": stage},
        "summary": bundle.summary(),
        "files": [p.name for p in files],
        "report_data": bundle.report_data,
    }
    (folder / "report.json").write_text(json.dumps(record, default=str), encoding="utf-8")
    return _public(record)


def render_report(record: dict[str, Any], *, audience: str = "full", lang: str = "en",
                  theme: str = "") -> str:
    from impact_vision.impact.report_templates.decision_report import render_decision_report

    data = dict(record["report_data"])
    if theme in {"light", "dark"}:
        data["theme"] = theme
    return render_decision_report(data, audience=audience, lang=lang)


def render_portfolio_page(*, jurisdictions: str = "auto", fund_name: str = "Portfolio",
                          theme: str = "") -> str:
    """Portfolio home (W3.4) built from every saved report plus CRM pipeline rows."""
    from impact_vision.impact.portfolio_home import build_portfolio_home, render_portfolio_home

    records, seen = [], set()
    for meta in list_reports(limit=500):  # newest first: keep the latest report per company
        key = str(meta.get("company", "")).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            records.append(load_report(meta["id"]))
        except (OSError, ValueError, HTTPException):
            continue
    pipeline_rows: list[dict[str, Any]] = []
    try:
        from impact_vision.impact.storage import get_assessment_store

        pipeline_rows = get_assessment_store().list_pipeline()
    except Exception:  # noqa: BLE001 - the page works without the CRM table
        pass
    if jurisdictions.strip().lower() in {"", "auto"}:
        # The fund's domicile (IMPACT_VISION_FUND_DOMICILE, e.g. "HK") plus where
        # the portfolio companies operate — not a fixed EU/US/UK list.
        from impact_vision.impact.portfolio_home import jurisdictions_for

        codes = jurisdictions_for(records, os.environ.get("IMPACT_VISION_FUND_DOMICILE", ""))[:8]
    else:
        codes = [j.strip() for j in jurisdictions.split(",") if j.strip()][:8]
    try:
        from impact_vision.impact.evidence_workflow import list_review_queues

        queues = list_review_queues()
    except Exception:  # noqa: BLE001 - the page must render even if the state store is unavailable
        queues = {}
    view = build_portfolio_home(records, fund_name=fund_name[:120] or "Portfolio",
                                jurisdictions=codes, pipeline_rows=pipeline_rows, review_queues=queues)
    return render_portfolio_home(view, theme=theme)


def _engagement_workspace():  # noqa: ANN202
    """The persisted workspace the engagement tools write to (W5.3)."""
    from impact_vision.tools.impact.engagement_workspace_tool import _workspace

    return _workspace()


# ---------------------------------------------------------------- share tokens


def _share_key() -> bytes:
    raw = os.environ.get("IMPACT_VISION_SHARE_HMAC_KEY") or os.environ.get("IMPACT_VISION_HMAC_KEY")
    if raw:
        return raw.encode("utf-8")
    (_web_home() / "web-reports").mkdir(parents=True, exist_ok=True)
    key_file = _web_home() / "web-reports" / ".share.key"  # one key for every tenant
    if not key_file.exists():
        fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(secrets.token_hex(32))
    return key_file.read_text().strip().encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_share_token(report_id: str, *, audience: str = "lp", lang: str = "en",
                     days: int = 14, now: float | None = None) -> tuple[str, int]:
    exp = int((now or time.time()) + max(1, min(days, SHARE_MAX_DAYS)) * 86400)
    from impact_vision.impact.identity import current_tenant

    body = _b64(json.dumps({"r": report_id, "a": audience, "l": lang, "e": exp, "t": current_tenant()},
                           separators=(",", ":")).encode())
    sig = _b64(hmac.new(_share_key(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", exp


def read_share_token(token: str, *, now: float | None = None) -> dict[str, Any]:
    """Return the token claims; raises ValueError if forged, malformed or expired."""
    try:
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(_share_key(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        claims = json.loads(_unb64(body))
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid share link") from exc
    if claims.get("e", 0) < (now or time.time()):
        raise ValueError("share link expired")
    if claims.get("a") not in _AUDIENCES or claims.get("l") not in _LANGS:
        raise ValueError("invalid share link")
    return claims


# ---------------------------------------------------------------- routes


class AssessRequest(BaseModel):
    stored_name: str = Field("", description="File name returned by POST /api/v1/chat/uploads")
    stored_names: list[str] = Field(default_factory=list,
                                    description="Several uploads about one company, assessed together")
    name: str = ""
    sector: str = ""
    geography: str = ""
    stage: str = ""


class StageRequest(BaseModel):
    stage: str
    actor: str = ""
    rationale: str = ""


class EventRequest(BaseModel):
    kind: str = Field("comment", description="comment | approval | decline | correction")
    author: str = ""
    text: str = ""
    target: str = ""
    assessment_id: str = ""


class ShareRequest(BaseModel):
    audience: str = Field("lp", description="full | ic | lp | regulator | public")
    lang: str = "en"
    days: int = Field(14, ge=1, le=SHARE_MAX_DAYS)


def _check_view(audience: str, lang: str) -> tuple[str, str]:
    from impact_vision.impact.report_templates.design.strings import normalize_lang

    if audience not in _AUDIENCES:
        raise HTTPException(status_code=422, detail=f"audience must be one of {', '.join(_AUDIENCES)}")
    lang = normalize_lang(lang)
    if lang not in _LANGS:
        raise HTTPException(status_code=422, detail=f"lang must be one of {', '.join(_LANGS)}")
    return audience, lang


def build_reports_router(*, auth_dependency: Any = None) -> Any:
    from impact_vision.web.chat_api import _safe_filename, uploads_dir

    if _FASTAPI_IMPORT_ERROR is not None:  # pragma: no cover
        raise ImportError("FastAPI is required: pip install 'impact-vision[web]'") from _FASTAPI_IMPORT_ERROR
    router = APIRouter(prefix="/api/v1/chat")
    deps = [Depends(auth_dependency)] if auth_dependency else []

    @router.post("/assess", dependencies=deps)
    async def assess(req: AssessRequest) -> dict[str, Any]:
        names = [n for n in ([req.stored_name] + list(req.stored_names)) if n]
        if not names:
            raise HTTPException(status_code=422, detail="Pass stored_name or stored_names")
        sources = []
        for stored in dict.fromkeys(names):
            source = (uploads_dir() / _safe_filename(stored)).resolve()
            if source.parent != uploads_dir().resolve() or not source.is_file():
                raise HTTPException(status_code=404, detail="Upload not found — upload the file first")
            sources.append(source)
        label = " + ".join(re.sub(r"^\d{8}-\d{6}-", "", s.name) for s in sources)
        try:
            return await asyncio.to_thread(create_report, sources, name=req.name, sector=req.sector,
                                           geography=req.geography, stage=req.stage, label=label)
        except ValueError as exc:  # unsupported type, empty text
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/reports", dependencies=deps)
    async def reports() -> dict[str, Any]:
        return {"reports": list_reports()}

    @router.get("/reports/{report_id}", dependencies=deps)
    async def report(report_id: str) -> dict[str, Any]:
        return _public(load_report(report_id))

    @router.delete("/reports/{report_id}", dependencies=deps)
    async def delete_report(report_id: str) -> dict[str, Any]:
        import shutil

        shutil.rmtree(_report_path(report_id))
        return {"deleted": report_id}

    @router.get("/reports/{report_id}/view", dependencies=deps, response_class=HTMLResponse)
    async def view(report_id: str, audience: str = "full", lang: str = "en", theme: str = "") -> HTMLResponse:
        audience, lang = _check_view(audience, lang)
        return HTMLResponse(render_report(load_report(report_id), audience=audience, lang=lang, theme=theme))

    @router.get("/reports/{report_id}/files/{name}", dependencies=deps)
    async def file(report_id: str, name: str) -> Any:
        record = load_report(report_id)
        if name not in record.get("files", []):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(_report_path(report_id) / name, filename=name)

    @router.get("/portfolio/view", dependencies=deps, response_class=HTMLResponse)
    async def portfolio_view(jurisdictions: str = "auto", fund_name: str = "Portfolio",
                             theme: str = "") -> HTMLResponse:
        return HTMLResponse(await asyncio.to_thread(
            render_portfolio_page, jurisdictions=jurisdictions, fund_name=fund_name, theme=theme))

    # -- company record (v8 W3): pipeline → invested → exited -----------
    @router.get("/companies", dependencies=deps)
    async def companies() -> dict[str, Any]:
        from impact_vision.impact.company_record import list_companies

        return {"companies": await asyncio.to_thread(list_companies)}

    @router.get("/companies/{name}", dependencies=deps)
    async def company(name: str) -> dict[str, Any]:
        from impact_vision.impact.company_record import company_timeline

        timeline = await asyncio.to_thread(company_timeline, name)
        if not timeline["stage"] and not timeline["assessments"]:
            raise HTTPException(status_code=404, detail="No such company on record")
        return timeline

    @router.post("/companies/{name}/stage", dependencies=deps)
    async def company_stage(name: str, req: StageRequest) -> dict[str, Any]:
        from impact_vision.impact.company_record import set_stage

        try:
            return await asyncio.to_thread(set_stage, name, req.stage, actor=req.actor[:120],
                                           rationale=req.rationale[:2000])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/companies/{name}/exit", dependencies=deps)
    async def company_exit(name: str) -> dict[str, Any]:
        from impact_vision.impact.company_record import exit_assessment

        try:
            return await asyncio.to_thread(exit_assessment, name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/portfolio/lp-report", dependencies=deps, response_class=HTMLResponse)
    async def lp_report(fund_name: str = "Portfolio", theme: str = "") -> HTMLResponse:
        from impact_vision.impact.company_record import lp_report_view, render_lp_report

        view = await asyncio.to_thread(lp_report_view, fund_name[:120] or "Portfolio")
        return HTMLResponse(render_lp_report(view, theme=theme))

    @router.post("/companies/{name}/events", dependencies=deps)
    async def company_event(name: str, req: EventRequest) -> dict[str, Any]:
        from impact_vision.impact.company_record import add_event

        try:
            return await asyncio.to_thread(add_event, name, req.kind, author=req.author[:120],
                                           text=req.text[:5000], target=req.target[:200],
                                           assessment_id=req.assessment_id[:40])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/engagements", dependencies=deps)
    async def engagements_list() -> dict[str, Any]:
        ws = _engagement_workspace()
        return {"engagements": [ws.summarize(e.engagement_id).model_dump(mode="json")
                                for e in ws.list_engagements()]}

    @router.get("/engagements/view", dependencies=deps, response_class=HTMLResponse)
    async def engagements_view(theme: str = "") -> HTMLResponse:
        from impact_vision.impact.engagement_home import build_engagement_home, render_engagement_home

        view = build_engagement_home(_engagement_workspace().list_engagements())
        return HTMLResponse(render_engagement_home(view, theme=theme))

    @router.post("/reports/{report_id}/share", dependencies=deps)
    async def share(report_id: str, req: ShareRequest) -> dict[str, Any]:
        load_report(report_id)
        audience, lang = _check_view(req.audience, req.lang)
        token, exp = make_share_token(report_id, audience=audience, lang=lang, days=req.days)
        return {"path": f"/shared/{token}", "expires_at": exp, "audience": audience, "lang": lang}

    return router


def build_shared_router() -> Any:
    router = APIRouter()

    @router.get("/shared/{token}", response_class=HTMLResponse, include_in_schema=False)
    async def shared(token: str) -> HTMLResponse:
        from impact_vision.impact.identity import DEFAULT_TENANT, Identity, acting_as

        try:
            claims = read_share_token(token)
            # The link carries its tenant; read the report as a viewer of that tenant only.
            viewer = Identity(sub="share-link", tenant_id=claims.get("t") or DEFAULT_TENANT,
                              roles=("viewer",), auth="share")
            with acting_as(viewer):
                record = load_report(claims["r"])
        except (ValueError, HTTPException, PermissionError):
            return HTMLResponse(
                "<!doctype html><meta charset=utf-8><title>Link unavailable</title>"
                "<p style='font:16px system-ui;margin:3rem'>This share link is invalid, expired "
                "or has been revoked. Ask the sender for a new one.</p>",
                status_code=404, headers=_SHARE_HEADERS)
        with acting_as(viewer):
            html = render_report(record, audience=claims["a"], lang=claims["l"])
        return HTMLResponse(html, headers=_SHARE_HEADERS)

    return router


__all__ = [
    "build_reports_router",
    "build_shared_router",
    "create_report",
    "list_reports",
    "load_report",
    "make_share_token",
    "read_share_token",
    "render_report",
    "reports_dir",
]
