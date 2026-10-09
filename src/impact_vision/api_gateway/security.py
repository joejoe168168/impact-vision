"""Secure-by-default protections for the local web app and REST gateway (v8 W0.1).

Without ``IMPACT_VISION_API_KEY`` the server is meant for the person at the
keyboard. A browser on the same machine can still reach it, so a hostile page
must not be able to drive it. This module provides:

* **Host allow-list**: rejects DNS-rebinding requests whose ``Host`` is an
  attacker's domain that resolves to 127.0.0.1.
* **Origin check**: rejects cross-site state-changing requests and WebSocket
  handshakes. Browsers always send ``Origin`` on those; non-browser clients
  (curl, scripts) send none and are allowed, because they already run on the
  machine.
* **Same-origin CORS by default**: no ``*``. Opt in with
  ``IMPACT_VISION_CORS_ORIGINS``.

With an API key configured every request needs the token anyway, so the Host
and Origin checks are relaxed for hosted deployments behind a domain.

Environment:
  ``IMPACT_VISION_API_KEY``         bearer token required on every request
  ``IMPACT_VISION_ALLOWED_HOSTS``   extra Host names (comma separated; ``*`` = any)
  ``IMPACT_VISION_CORS_ORIGINS``    origins allowed cross-origin (comma separated)
"""
from __future__ import annotations

import ipaddress
import json
import os
import secrets
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

LOOPBACK_NAMES = {"localhost", "127.0.0.1", "::1", "[::1]", "testserver"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def configured_api_key() -> str:
    """The bearer token, read on every request so a launcher can set it late."""
    return os.environ.get("IMPACT_VISION_API_KEY", "")


def token_matches(supplied: str | None) -> bool:
    expected = configured_api_key()
    if not expected:
        return True
    return bool(supplied) and secrets.compare_digest(str(supplied), expected)


def is_loopback_host(host: str) -> bool:
    host = (host or "").strip().strip("[]").lower()
    if host in {"localhost", ""} or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def parse_origins(raw: str | None) -> list[str]:
    """Comma-separated origins. Empty means same-origin only (no CORS)."""
    return [item.strip().rstrip("/") for item in (raw or "").split(",") if item.strip()]


def cors_origins() -> list[str]:
    return parse_origins(os.environ.get("IMPACT_VISION_CORS_ORIGINS"))


def _hostname(host_header: str) -> str:
    host_header = (host_header or "").strip().lower()
    if host_header.startswith("["):
        return host_header.split("]", 1)[0] + "]"
    return host_header.rsplit(":", 1)[0] if host_header.count(":") == 1 else host_header


def host_allowed(host_header: str) -> bool:
    extra = {h.strip().lower() for h in os.environ.get("IMPACT_VISION_ALLOWED_HOSTS", "").split(",") if h.strip()}
    if "*" in extra:
        return True
    name = _hostname(host_header)
    return name in LOOPBACK_NAMES or is_loopback_host(name) or name in extra


def origin_allowed(origin: str | None, host_header: str) -> bool:
    """Same-origin, or listed in IMPACT_VISION_CORS_ORIGINS. Absent = not a browser."""
    if origin is None:
        return True
    origin = origin.strip().rstrip("/")
    if not origin or origin == "null":
        return False
    if origin in cors_origins():
        return True
    return urlsplit(origin).netloc.lower() == (host_header or "").strip().lower()


class LocalGuardMiddleware:
    """ASGI middleware enforcing the Host and Origin rules above."""

    def __init__(self, app: Callable[..., Awaitable[Any]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        host = headers.get("host", "")
        origin = headers.get("origin")
        keyed = bool(configured_api_key())
        problem = ""
        if not keyed and not host_allowed(host):
            problem = f"Host {host!r} is not allowed (set IMPACT_VISION_ALLOWED_HOSTS or IMPACT_VISION_API_KEY)"
        elif scope["type"] == "websocket" or scope.get("method", "GET") not in SAFE_METHODS:
            if not origin_allowed(origin, host):
                problem = "Cross-origin request refused"
        if not problem:
            await self.app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 4403, "reason": problem})
            return
        body = json.dumps({"detail": problem}).encode()
        await send({"type": "http.response.start", "status": 403,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


def ensure_launch_token(host: str) -> str | None:
    """Binding beyond loopback without a key: mint a per-launch token.

    Returns the new token (so the launcher can print a login URL), or None
    when no token was needed or one is already configured.
    """
    if configured_api_key() or is_loopback_host(host):
        return None
    token = secrets.token_urlsafe(24)
    os.environ["IMPACT_VISION_API_KEY"] = token
    return token


__all__ = [
    "LocalGuardMiddleware",
    "configured_api_key",
    "cors_origins",
    "ensure_launch_token",
    "host_allowed",
    "is_loopback_host",
    "origin_allowed",
    "parse_origins",
    "token_matches",
]
