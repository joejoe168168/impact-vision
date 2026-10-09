"""OIDC sign-in, sessions and role checks for the web app (roadmap v8 W5.3).

Off unless ``IMPACT_VISION_OIDC_ISSUER`` is set; then every request must carry
a session cookie from ``/auth/login`` (authorization-code flow with PKCE) or
the gateway API key. Settings:

=================================  =============================================
``IMPACT_VISION_OIDC_ISSUER``      issuer URL (discovery at ``/.well-known/openid-configuration``)
``IMPACT_VISION_OIDC_CLIENT_ID``   client id (required)
``IMPACT_VISION_OIDC_CLIENT_SECRET``  client secret (omit for a public PKCE client)
``IMPACT_VISION_OIDC_REDIRECT_URL``   callback URL, default ``<this site>/auth/callback``
``IMPACT_VISION_OIDC_TENANT_CLAIM``   claim naming the tenant (default ``tenant``;
                                   falls back to the email domain)
``IMPACT_VISION_OIDC_ROLES_CLAIM``    claim listing roles (default ``roles``)
``IMPACT_VISION_OIDC_DEFAULT_ROLE``   role when the token names none (default ``analyst``)
``IMPACT_VISION_OIDC_ADMINS``         comma-separated emails that get ``tenant_admin``
``IMPACT_VISION_SESSION_SECRET``      cookie signing key (default: a generated 0600 file)
``IMPACT_VISION_API_TENANT``          tenant for API-key (machine) calls (default ``default``)
=================================  =============================================

Roles are the presets in ``impact.tenancy.BUILTIN_ROLES``; routes map to
permissions in :data:`ROUTE_PERMISSIONS`.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from impact_vision.impact.identity import DEFAULT_TENANT, Identity, acting_as, valid_tenant_id
from impact_vision.impact.tenancy import (
    BUILTIN_ROLES,
    PERM_DEAL_DELETE,
    PERM_DEAL_READ,
    PERM_DEAL_WRITE,
    PERM_PORTFOLIO_READ,
    PERM_REPORT_GENERATE,
    PERM_REPORT_PUBLISH_LP,
    PERM_USER_ADMIN,
)

SESSION_COOKIE = "iv_session"
FLOW_COOKIE = "iv_oidc"
SESSION_SECONDS = 8 * 3600
PUBLIC_PREFIXES = ("/auth/", "/shared/", "/api/v1/health", "/health", "/favicon")
_ALGS = {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384"}

# (method or "*", path prefix, permission) — first match wins.
ROUTE_PERMISSIONS: list[tuple[str, str, str]] = [
    ("*", "/api/v1/chat/providers", PERM_USER_ADMIN),
    ("POST", "/api/v1/chat/reports", PERM_REPORT_PUBLISH_LP),  # creating share links
    ("DELETE", "/api/v1/chat/reports", PERM_DEAL_DELETE),
    ("GET", "/api/v1/chat/portfolio", PERM_PORTFOLIO_READ),
    ("POST", "/api/v1/chat/assess", PERM_REPORT_GENERATE),
    ("WS", "/ws/chat", PERM_DEAL_WRITE),
    ("POST", "/", PERM_DEAL_WRITE),
    ("PUT", "/", PERM_DEAL_WRITE),
    ("PATCH", "/", PERM_DEAL_WRITE),
    ("DELETE", "/", PERM_DEAL_WRITE),
    ("*", "/", PERM_DEAL_READ),
]


def oidc_enabled() -> bool:
    return bool(os.environ.get("IMPACT_VISION_OIDC_ISSUER", "").strip())


def _env(name: str, default: str = "") -> str:
    return os.environ.get(f"IMPACT_VISION_{name}", default).strip()


# ------------------------------------------------------------------ signing


def _secret() -> bytes:
    raw = _env("SESSION_SECRET")
    if raw:
        return raw.encode()
    from impact_vision.config.paths import get_config_dir

    path = get_config_dir() / "session.key"
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(secrets.token_hex(32))
    return Path(path).read_text().strip().encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(claims: dict[str, Any]) -> str:
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    return body + "." + _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())


def unsign(value: str) -> dict[str, Any] | None:
    try:
        body, sig = value.split(".", 1)
        if not hmac.compare_digest(sig, _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())):
            return None
        claims: dict[str, Any] = json.loads(_unb64(body))
    except (ValueError, TypeError):
        return None
    return claims if claims.get("exp", 0) > time.time() else None


# ------------------------------------------------------------------ identity


def identity_from_claims(claims: dict[str, Any]) -> Identity:
    """Map ID-token claims to an Identity (tenant + roles)."""
    email = str(claims.get("email") or "")
    tenant = str(claims.get(_env("OIDC_TENANT_CLAIM", "tenant")) or "").strip().lower()
    if not tenant and "@" in email:
        tenant = email.rsplit("@", 1)[1].lower()
    tenant = tenant or DEFAULT_TENANT
    if not valid_tenant_id(tenant):
        raise PermissionError(f"tenant claim {tenant!r} is not a valid tenant id")
    raw = claims.get(_env("OIDC_ROLES_CLAIM", "roles")) or []
    roles = [r for r in ([raw] if isinstance(raw, str) else raw) if r in BUILTIN_ROLES]
    admins = {e.strip().lower() for e in _env("OIDC_ADMINS").split(",") if e.strip()}
    if email.lower() in admins:
        roles.append("tenant_admin")
    if not roles:
        roles = [_env("OIDC_DEFAULT_ROLE", "analyst")]
    return Identity(sub=str(claims["sub"]), tenant_id=tenant, roles=tuple(dict.fromkeys(roles)),
                    email=email, name=str(claims.get("name") or email), auth="oidc")


def _session_identity(cookie: str) -> Identity | None:
    claims = unsign(cookie)
    if not claims:
        return None
    return Identity(sub=claims["sub"], tenant_id=claims["t"], roles=tuple(claims["r"]), email=claims.get("e", ""),
                    name=claims.get("n", ""), auth="oidc")


def required_permission(method: str, path: str) -> str:
    for m, prefix, perm in ROUTE_PERMISSIONS:
        if (m == "*" or m == method) and path.startswith(prefix):
            return perm
    return str(PERM_DEAL_READ)


# ------------------------------------------------------------------ provider I/O (patched in tests)


async def fetch_json(url: str) -> dict[str, Any]:
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        data: dict[str, Any] = r.json()
        return data


async def post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, data=data, headers={"accept": "application/json"})
        r.raise_for_status()
        out: dict[str, Any] = r.json()
        return out


def signing_key(jwks_uri: str, token: str) -> Any:
    try:
        import jwt
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("OIDC needs PyJWT: pip install 'impact-vision[oidc]'") from exc
    return jwt.PyJWKClient(jwks_uri).get_signing_key_from_jwt(token).key


_DISCOVERY: dict[str, dict[str, Any]] = {}


async def discovery() -> dict[str, Any]:
    issuer = _env("OIDC_ISSUER").rstrip("/")
    if issuer not in _DISCOVERY:
        _DISCOVERY[issuer] = await fetch_json(issuer + "/.well-known/openid-configuration")
    return _DISCOVERY[issuer]


async def verify_id_token(id_token: str, nonce: str) -> dict[str, Any]:
    import jwt

    meta = await discovery()
    algs = sorted(_ALGS & set(meta.get("id_token_signing_alg_values_supported") or ["RS256"])) or ["RS256"]
    key = await asyncio.to_thread(signing_key, meta["jwks_uri"], id_token)
    claims: dict[str, Any] = jwt.decode(id_token, key, algorithms=algs, audience=_env("OIDC_CLIENT_ID"),
                                        issuer=meta.get("issuer") or _env("OIDC_ISSUER"),
                                        options={"require": ["exp", "iat", "sub"]})
    if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
        raise PermissionError("nonce mismatch")
    return claims


# ------------------------------------------------------------------ ASGI middleware


async def _respond(send: Any, status: int, body: bytes, headers: list[tuple[bytes, bytes]]) -> None:
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def _cookies(headers: dict[str, str]) -> dict[str, str]:
    out = {}
    for part in headers.get("cookie", "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            out[k] = v
    return out


class IdentityMiddleware:
    """Resolve who is calling, enforce the route's permission, run the request as them."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] not in {"http", "websocket"} or not oidc_enabled():
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        who = self._api_key_identity(headers) or _session_identity(_cookies(headers).get(SESSION_COOKIE, ""))
        method = "WS" if scope["type"] == "websocket" else scope.get("method", "GET")
        if who is None:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 4401, "reason": "Sign in required"})
            elif method == "GET" and "text/html" in headers.get("accept", ""):
                target = "/auth/login?" + urlencode({"next": path})
                await _respond(send, 302, b"", [(b"location", target.encode())])
            else:
                await _respond(send, 401, b'{"detail":"Sign in required"}', [(b"content-type", b"application/json")])
            return
        perm = required_permission(method, path)
        if not who.can(perm):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 4403, "reason": f"Needs {perm}"})
            else:
                body = json.dumps({"detail": f"Your role can't do this (needs {perm})"}).encode()
                await _respond(send, 403, body, [(b"content-type", b"application/json")])
            return
        with acting_as(who):
            await self.app(scope, receive, send)

    @staticmethod
    def _api_key_identity(headers: dict[str, str]) -> Identity | None:
        from impact_vision.api_gateway.security import configured_api_key, token_matches

        if not configured_api_key():
            return None
        auth = headers.get("authorization", "")
        offered = [p.strip() for p in headers.get("sec-websocket-protocol", "").split(",")]
        supplied = (auth[7:].strip() if auth[:7].lower() == "bearer " else headers.get("x-api-key", "")) or next(
            (p[len("bearer."):] for p in offered if p.startswith("bearer.")), "")
        if supplied and token_matches(supplied):
            return Identity(sub="api-key", tenant_id=_env("API_TENANT", DEFAULT_TENANT), roles=("tenant_admin",),
                            name="API key", auth="api_key")
        return None


# ------------------------------------------------------------------ routes


def build_auth_router() -> Any:
    router = APIRouter(include_in_schema=False)

    def _secure(request: Request) -> bool:
        return request.url.scheme == "https"

    def _redirect_uri(request: Request) -> str:
        return _env("OIDC_REDIRECT_URL") or str(request.url_for("oidc_callback"))

    @router.get("/auth/login")
    async def oidc_login(request: Request, next: str = "/") -> Any:  # noqa: A002
        if not oidc_enabled():
            return RedirectResponse("/")
        meta = await discovery()
        state, nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48)
        challenge = _b64(hashlib.sha256(verifier.encode()).digest())
        params = {"response_type": "code", "client_id": _env("OIDC_CLIENT_ID"), "redirect_uri": _redirect_uri(request),
                  "scope": _env("OIDC_SCOPES", "openid email profile"), "state": state, "nonce": nonce,
                  "code_challenge": challenge, "code_challenge_method": "S256"}
        safe_next = next if next.startswith("/") and not next.startswith("//") else "/"
        resp = RedirectResponse(meta["authorization_endpoint"] + "?" + urlencode(params), status_code=302)
        resp.set_cookie(FLOW_COOKIE, sign({"s": state, "n": nonce, "v": verifier, "x": safe_next,
                                           "exp": int(time.time()) + 600}),
                        max_age=600, httponly=True, samesite="lax", secure=_secure(request), path="/auth/")
        return resp

    @router.get("/auth/callback", name="oidc_callback")
    async def oidc_callback(request: Request, code: str = "", state: str = "", error: str = "") -> Any:
        flow = unsign(request.cookies.get(FLOW_COOKIE, ""))
        if error or not code or not flow or not hmac.compare_digest(flow["s"], state):
            return JSONResponse({"detail": error or "Sign-in failed: start again at /auth/login"}, status_code=400)
        meta = await discovery()
        form = {"grant_type": "authorization_code", "code": code, "redirect_uri": _redirect_uri(request),
                "client_id": _env("OIDC_CLIENT_ID"), "code_verifier": flow["v"]}
        if _env("OIDC_CLIENT_SECRET"):
            form["client_secret"] = _env("OIDC_CLIENT_SECRET")
        try:
            tokens = await post_form(meta["token_endpoint"], form)
            claims = await verify_id_token(tokens["id_token"], flow["n"])
            who = identity_from_claims(claims)
        except Exception as exc:  # noqa: BLE001 - any failure is a refused sign-in
            return JSONResponse({"detail": f"Sign-in refused: {exc}"}, status_code=401)
        resp = RedirectResponse(flow["x"], status_code=302)
        resp.set_cookie(SESSION_COOKIE, sign({"sub": who.sub, "t": who.tenant_id, "r": list(who.roles),
                                              "e": who.email, "n": who.name,
                                              "exp": int(time.time()) + SESSION_SECONDS}),
                        max_age=SESSION_SECONDS, httponly=True, samesite="lax", secure=_secure(request))
        resp.delete_cookie(FLOW_COOKIE, path="/auth/")
        return resp

    @router.get("/auth/logout")
    async def oidc_logout() -> Any:
        target = "/"
        if oidc_enabled():
            target = (await discovery()).get("end_session_endpoint") or "/"
        resp = RedirectResponse(target, status_code=302)
        resp.delete_cookie(SESSION_COOKIE)
        return resp

    @router.get("/auth/me")
    async def oidc_me(request: Request) -> Any:
        who = _session_identity(request.cookies.get(SESSION_COOKIE, "")) if oidc_enabled() else None
        if oidc_enabled() and who is None:
            return JSONResponse({"signed_in": False, "mode": "oidc"}, status_code=401)
        from impact_vision.impact.identity import LOCAL

        who = who or LOCAL
        return {"signed_in": True, "mode": "oidc" if oidc_enabled() else "local", "sub": who.sub,
                "email": who.email, "name": who.name, "tenant": who.tenant_id, "roles": list(who.roles),
                "permissions": sorted(who.permissions)}

    return router


__all__ = ["IdentityMiddleware", "ROUTE_PERMISSIONS", "build_auth_router", "identity_from_claims", "oidc_enabled",
           "required_permission", "sign", "unsign"]
