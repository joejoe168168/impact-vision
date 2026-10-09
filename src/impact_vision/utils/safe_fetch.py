"""Fetch public http(s) URLs without SSRF (v8 W0.2 / W5).

Used wherever a URL can come from a document or a remote caller: the deck
fetcher, the claim verifier. Each request — and every redirect hop — must be
http(s) and resolve only to public addresses, so a document can't make the
server read ``http://169.254.169.254/`` or ``http://localhost:8787/``.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class UnsafeUrlError(ValueError):
    """The URL is not http(s) or resolves to a non-public address."""


def ensure_public_url(url: str) -> None:
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Only http(s) URLs are allowed, got scheme '{scheme or 'none'}'.")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL is missing a host component.")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"DNS lookup failed for '{host}': {exc}") from exc
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise UnsafeUrlError(f"Refusing to fetch '{host}', which resolves to non-public address {ip}.")


class _CheckedRedirect(HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]  # noqa: ANN001
        ensure_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_public(url: str, *, timeout: float = 10.0, headers: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    """``urlopen`` for public URLs only, re-checking every redirect."""
    ensure_public_url(url)
    request = Request(url, headers=headers or {"User-Agent": user_agent()})
    return build_opener(_CheckedRedirect).open(request, timeout=timeout)  # nosec B310 - scheme/host checked


def fetch_public_text(url: str, *, timeout: float = 15.0, max_bytes: int = 1_000_000) -> str:
    with open_public(url, timeout=timeout) as response:
        return response.read(max_bytes).decode("utf-8", errors="replace")


def user_agent(suffix: str = "") -> str:
    try:
        from importlib.metadata import version

        base = f"impact-vision/{version('impact-vision')}"
    except Exception:  # noqa: BLE001 - source checkout
        base = "impact-vision/dev"
    return f"{base} ({suffix})" if suffix else base


__all__ = ["UnsafeUrlError", "ensure_public_url", "fetch_public_text", "open_public", "user_agent"]
