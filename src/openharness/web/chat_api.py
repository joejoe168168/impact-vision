"""WebSocket + REST API backing the Impact Vision web chat UI.

Everything the browser needs lives here:

``GET  /api/v1/chat/bootstrap``            one-shot payload for page load
``GET  /api/v1/chat/sessions``             conversation sidebar
``POST /api/v1/chat/sessions``             new conversation
``PATCH/DELETE /api/v1/chat/sessions/{id}``rename / delete
``GET  /api/v1/chat/sessions/{id}``        full transcript replay
``GET  /api/v1/chat/providers``            provider profiles + auth state
``POST /api/v1/chat/providers``            switch profile / set model, base URL, key
``POST /api/v1/chat/uploads``              drag-and-drop file intake
``GET  /api/v1/chat/artifacts/download``   download a generated file
``WS   /ws/chat``                          the live conversation stream

The WebSocket speaks the same event vocabulary as
:class:`openharness.web.chat_session.ChatSession` emits, so adding a backend
event automatically reaches the browser without touching this module.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

try:
    from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
except ImportError as _exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "FastAPI is required for the web chat UI. Install with: pip install fastapi uvicorn"
    ) from _exc

from pydantic import BaseModel, Field

from openharness.web.chat_session import ChatSession, SessionOptions, get_session_manager

log = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = int(os.environ.get("IMPACT_VISION_MAX_UPLOAD_MB", "64")) * 1024 * 1024
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class NewSessionRequest(BaseModel):
    title: str = "New chat"
    model: str | None = None
    active_profile: str | None = None
    permission_mode: str | None = Field(
        default=None, description="default | plan | full_auto"
    )
    system_prompt: str | None = None


class RenameRequest(BaseModel):
    title: str


class ProviderUpdate(BaseModel):
    """Configure which LLM endpoint the agent talks to."""

    profile: str | None = Field(default=None, description="Provider profile to activate")
    model: str | None = None
    base_url: str | None = Field(default=None, description="OpenAI/Anthropic-compatible endpoint URL")
    api_key: str | None = Field(default=None, description="Stored in the local credential store")
    api_format: str | None = Field(default=None, description="anthropic | openai | copilot")
    label: str | None = None
    make_active: bool = True


# ---------------------------------------------------------------------------
# Upload / artifact helpers
# ---------------------------------------------------------------------------


# Documents a fund user uploads; anything else (executables, archives,
# scripts) is refused.
UPLOAD_EXTENSIONS = frozenset({
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".csv", ".txt", ".md", ".json",
    ".yaml", ".yml", ".png", ".jpg", ".jpeg",
})
# What the artifacts panel may download from the workspace.
DOWNLOAD_EXTENSIONS = UPLOAD_EXTENSIONS | {".html", ".htm", ".svg", ".zip", ".docm", ".xml", ".xbrl"}


def uploads_dir() -> Path:
    """Return (and create) the folder that receives browser uploads.

    It lives in the web home (``~/.openharness/web-uploads`` by default), not
    in the working directory, so confidential decks never land in a git
    checkout.
    """
    default = Path(os.environ.get("IMPACT_VISION_WEB_HOME", Path.home() / ".openharness")) / "web-uploads"
    root = Path(os.environ.get("IMPACT_VISION_UPLOAD_DIR", default))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", Path(name or "upload").name).strip("._") or "upload"
    return cleaned[:120]


def _download_roots() -> list[Path]:
    """Directories a download is allowed to serve from."""
    roots = [Path.cwd().resolve(), uploads_dir().resolve()]
    extra = os.environ.get("IMPACT_VISION_DOWNLOAD_ROOTS", "")
    for item in extra.split(os.pathsep):
        if item.strip():
            with contextlib.suppress(OSError):
                roots.append(Path(item).expanduser().resolve())
    return roots


def _resolve_download(raw_path: str) -> Path:
    """Resolve a download request, refusing anything outside the allowed roots."""
    try:
        target = Path(raw_path).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if target.suffix.lower() not in DOWNLOAD_EXTENSIONS:
        raise HTTPException(status_code=403, detail="Only report and document files can be downloaded")
    for root in _download_roots():
        with contextlib.suppress(ValueError):
            relative = target.relative_to(root)
            if any(part.startswith(".") for part in relative.parts[:-1]) or relative.name.startswith("."):
                continue  # hidden files and folders (.git, .env, .openharness) are never served
            return target
    raise HTTPException(status_code=403, detail="Path is outside the served workspace")


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------


def _provider_snapshot() -> dict[str, Any]:
    """Current provider profiles, active selection and model options."""
    from openharness.auth.manager import AuthManager
    from openharness.config import load_settings
    from openharness.config.settings import (
        CLAUDE_MODEL_ALIAS_OPTIONS,
        PROFILE_MODEL_SUGGESTIONS,
        auth_source_env_var_candidates,
        is_local_base_url,
    )

    settings = load_settings()
    manager = AuthManager(settings)
    statuses = manager.get_profile_statuses()
    active = manager.get_active_profile()
    materialized = settings.materialize_active_profile()

    profiles = [
        {
            "name": name,
            "label": info.get("label", name),
            "provider": info.get("provider"),
            "api_format": info.get("api_format"),
            "auth_source": info.get("auth_source"),
            "configured": bool(info.get("configured")),
            "active": name == active,
            "base_url": info.get("base_url"),
            "model": info.get("model"),
            "uses_api_key": "api_key" in str(info.get("auth_source", "")),
            "local": is_local_base_url(info.get("base_url")),
            "key_env": (auth_source_env_var_candidates(str(info.get("auth_source", ""))) or ("",))[-1],
            "models": list(PROFILE_MODEL_SUGGESTIONS.get(name, ())),
        }
        for name, info in statuses.items()
    ]
    return {
        "active_profile": active,
        "model": materialized.model,
        "base_url": materialized.base_url,
        "api_format": materialized.api_format,
        "permission_mode": settings.permission.mode.value,
        "max_turns": settings.max_turns,
        "effort": settings.effort,
        "profiles": profiles,
        "claude_models": [
            {"value": value, "label": label, "description": description}
            for value, label, description in CLAUDE_MODEL_ALIAS_OPTIONS
        ],
        "suggested_models": {k: list(v) for k, v in PROFILE_MODEL_SUGGESTIONS.items()},
    }


def _apply_provider_update(update: ProviderUpdate) -> dict[str, Any]:
    from openharness.auth.manager import AuthManager
    from openharness.config import load_settings
    from openharness.config.settings import credential_storage_provider_name

    settings = load_settings()
    manager = AuthManager(settings)
    profile_name = (update.profile or manager.get_active_profile()).strip()

    profiles = manager.settings.merged_profiles()
    if profile_name not in profiles:
        raise HTTPException(status_code=400, detail=f"Unknown provider profile: {profile_name}")

    # Repointing a profile that already holds a key would send that key to the
    # new endpoint. Require the key to be re-entered with the new URL, unless
    # the new endpoint is on this machine (local servers need no key).
    from openharness.auth.storage import load_credential
    from openharness.config.settings import is_local_base_url

    current = profiles[profile_name]
    new_url = (update.base_url or "").strip() or None if update.base_url is not None else current.base_url
    if (
        (new_url or None) != (current.base_url or None)
        and not update.api_key
        and not is_local_base_url(new_url)
        and load_credential(credential_storage_provider_name(profile_name, current), "api_key")
    ):
        raise HTTPException(
            status_code=400,
            detail="Changing the endpoint of a profile with a saved key: re-enter the API key for the new endpoint.",
        )

    changes: dict[str, Any] = {}
    if update.model:
        changes["last_model"] = update.model
    if update.base_url is not None:
        changes["base_url"] = update.base_url.strip() or None
    if update.api_format:
        changes["api_format"] = update.api_format
    if update.label:
        changes["label"] = update.label
    if changes:
        manager.update_profile(profile_name, **changes)

    if update.api_key:
        profile = manager.settings.merged_profiles()[profile_name]
        slot = credential_storage_provider_name(profile_name, profile)
        manager.store_credential(slot, "api_key", update.api_key.strip())

    if update.make_active and profile_name != manager.get_active_profile():
        manager.use_profile(profile_name)

    return _provider_snapshot()


def _apply_default_options(manager_options: SessionOptions) -> SessionOptions:
    """Refresh runtime defaults from the on-disk settings."""
    from openharness.config import load_settings

    settings = load_settings().materialize_active_profile()
    manager_options.model = settings.model
    manager_options.active_profile = settings.active_profile
    manager_options.base_url = settings.base_url
    manager_options.api_format = settings.api_format
    return manager_options


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def build_chat_router(*, auth_dependency: Any = None) -> APIRouter:
    """Return the chat API router.

    ``auth_dependency`` is the gateway's ``verify_api_key`` callable, applied to
    the REST endpoints. WebSockets carry the token as a query parameter instead,
    because browsers cannot set headers on a ``WebSocket`` handshake.
    """
    deps = [Depends(auth_dependency)] if auth_dependency else []
    router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

    # -- bootstrap ------------------------------------------------------

    @router.get("/bootstrap", dependencies=deps)
    async def bootstrap() -> dict[str, Any]:
        manager = get_session_manager()
        _apply_default_options(manager.default_options)
        return {
            "sessions": manager.list_sessions(),
            "provider": _provider_snapshot(),
            "workspace": str(Path.cwd()),
            "uploads_dir": str(uploads_dir()),
            "auth_required": bool(os.environ.get("IMPACT_VISION_API_KEY")),
            "version": _version(),
        }

    # -- sessions -------------------------------------------------------

    @router.get("/sessions", dependencies=deps)
    async def list_sessions() -> dict[str, Any]:
        return {"sessions": get_session_manager().list_sessions()}

    @router.post("/sessions", dependencies=deps)
    async def create_session(req: NewSessionRequest) -> dict[str, Any]:
        if (req.permission_mode or "").strip().lower() == "full_auto" and os.environ.get(
            "IMPACT_VISION_WEB_ALLOW_FULL_AUTO", ""
        ).strip().lower() not in {"1", "true", "yes"}:
            raise HTTPException(
                status_code=403,
                detail="full_auto can't be enabled over the web API (set IMPACT_VISION_WEB_ALLOW_FULL_AUTO=1 on a trusted machine).",
            )
        manager = get_session_manager()
        _apply_default_options(manager.default_options)
        overrides = {
            key: value
            for key, value in {
                "model": req.model,
                "active_profile": req.active_profile,
                "permission_mode": req.permission_mode,
                "system_prompt": req.system_prompt,
            }.items()
            if value
        }
        session = manager.create(title=req.title or "New chat", overrides=overrides)
        return {"session": session.meta()}

    @router.get("/sessions/{session_id}", dependencies=deps)
    async def get_session(session_id: str) -> dict[str, Any]:
        session = get_session_manager().get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session.snapshot()

    @router.patch("/sessions/{session_id}", dependencies=deps)
    async def rename_session(session_id: str, req: RenameRequest) -> dict[str, Any]:
        if not get_session_manager().rename(session_id, req.title):
            raise HTTPException(status_code=404, detail="Session not found")
        return {"ok": True, "title": req.title}

    @router.delete("/sessions/{session_id}", dependencies=deps)
    async def delete_session(session_id: str) -> dict[str, Any]:
        deleted = await get_session_manager().delete(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"ok": True}

    # -- provider configuration ----------------------------------------

    @router.get("/providers", dependencies=deps)
    async def get_providers() -> dict[str, Any]:
        return _provider_snapshot()

    @router.post("/providers", dependencies=deps)
    async def set_provider(update: ProviderUpdate) -> dict[str, Any]:
        snapshot = _apply_provider_update(update)
        manager = get_session_manager()
        _apply_default_options(manager.default_options)
        return snapshot

    # -- uploads --------------------------------------------------------

    @router.post("/uploads", dependencies=deps)
    async def upload(files: list[UploadFile] = File(...)) -> dict[str, Any]:
        saved: list[dict[str, Any]] = []
        target_dir = uploads_dir()
        for item in files:
            suffix = Path(item.filename or "").suffix.lower()
            if suffix not in UPLOAD_EXTENSIONS:
                raise HTTPException(
                    status_code=415,
                    detail=f"{item.filename}: only {', '.join(sorted(UPLOAD_EXTENSIONS))} files can be uploaded",
                )
            payload = await item.read(_MAX_UPLOAD_BYTES + 1)
            if len(payload) > _MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"{item.filename} exceeds the {_MAX_UPLOAD_BYTES // (1024 * 1024)}MB upload limit",
                )
            stamp = time.strftime("%Y%m%d-%H%M%S")
            name = f"{stamp}-{_safe_filename(item.filename or 'upload')}"
            destination = target_dir / name
            destination.write_bytes(payload)
            saved.append(
                {
                    "name": item.filename,
                    "stored_name": name,
                    "path": str(destination),
                    "size": len(payload),
                    "content_type": item.content_type,
                }
            )
        return {"files": saved}

    # -- artifacts ------------------------------------------------------

    @router.get("/artifacts", dependencies=deps)
    async def list_artifacts(session_id: str = Query(...)) -> dict[str, Any]:
        session = get_session_manager().get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"artifacts": [artifact.as_dict() for artifact in session.artifacts]}

    @router.get("/artifacts/download", dependencies=deps)
    async def download_artifact(path: str = Query(...)) -> Any:
        target = _resolve_download(path)
        return FileResponse(target, filename=target.name)

    return router


def build_chat_ws_router() -> APIRouter:
    """Return the WebSocket router (separate so REST auth deps don't apply)."""
    router = APIRouter()

    @router.websocket("/ws/chat")
    async def chat_socket(websocket: WebSocket, session: str | None = None, token: str | None = None) -> None:
        from openharness.api_gateway.security import token_matches

        # Browsers can't set headers on a WebSocket, so the UI offers the token
        # as a subprotocol ("iv", "bearer.<token>") to keep it out of URLs and
        # access logs. ``?token=`` still works for older clients.
        offered = [p.strip() for p in websocket.headers.get("sec-websocket-protocol", "").split(",") if p.strip()]
        supplied = next((p[len("bearer."):] for p in offered if p.startswith("bearer.")), None) or token
        if not token_matches(supplied):
            await websocket.close(code=4401, reason="Invalid or missing API key")
            return

        await websocket.accept(subprotocol="iv" if "iv" in offered else None)
        manager = get_session_manager()
        chat = manager.get_or_create(session)
        _apply_default_options(manager.default_options)

        await websocket.send_json(chat.snapshot())

        async with chat.subscribe() as queue:
            pump = asyncio.create_task(_pump(websocket, queue))
            try:
                await chat.ensure_started()
                await _consume_client(websocket, chat, manager)
            except WebSocketDisconnect:
                pass
            except Exception:  # noqa: BLE001 - never kill the server on one socket
                log.exception("WebSocket loop failed for session %s", chat.session_id)
            finally:
                pump.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await pump
                chat.persist()

    return router


async def _pump(websocket: WebSocket, queue: asyncio.Queue[dict[str, Any]]) -> None:
    """Forward backend events to the browser."""
    while True:
        event = await queue.get()
        try:
            await websocket.send_json(event)
        except Exception:  # noqa: BLE001 - socket closed underneath us
            return


async def _consume_client(websocket: WebSocket, chat: ChatSession, manager: Any) -> None:
    """Handle inbound browser messages for one socket."""
    while True:
        message = await websocket.receive_json()
        kind = str(message.get("type") or "")

        if kind == "submit":
            await chat.submit(str(message.get("text") or ""))
        elif kind == "cancel":
            await chat.cancel()
        elif kind == "permission_response":
            chat.resolve_permission(str(message.get("request_id") or ""), bool(message.get("allowed")))
        elif kind == "question_response":
            chat.resolve_question(str(message.get("request_id") or ""), str(message.get("answer") or ""))
        elif kind == "ping":
            await websocket.send_json({"type": "pong"})
        elif kind == "rename":
            title = str(message.get("title") or "").strip()
            if title:
                manager.rename(chat.session_id, title)
                await websocket.send_json({"type": "title", "title": title})
        else:
            await websocket.send_json({"type": "error", "message": f"Unknown message type: {kind}"})


def _version() -> str:
    with contextlib.suppress(Exception):
        from importlib.metadata import version

        return version("impact-vision")
    return "0.0.0"


__all__ = ["build_chat_router", "build_chat_ws_router", "uploads_dir"]
