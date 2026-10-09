"""Authenticated, stateless MCP over HTTP (roadmap v8 W5.6).

``impact-vision serve-mcp --transport http`` wraps the MCP Streamable HTTP
app in this ASGI layer:

* **Bearer tokens.** Tokens are random 32-byte strings shown once at creation.
  Only their SHA-256 is stored (``~/.openharness/mcp_tokens.json``, mode 0600),
  each with a label, scopes and an optional expiry.
* **Per-tool scopes.** ``read`` (reference lookups), ``assess`` (scoring),
  ``write`` (pipeline / monitoring state), ``files`` (tools that read or write
  local files or fetch URLs) and ``admin`` (everything). A ``tools/call`` the
  token isn't scoped for gets HTTP 403 and a JSON-RPC error; the tool never runs.
* **Audit log.** Every ``tools/call`` (allowed or denied) is appended to the
  hash-chained audit trail: who (token label), which tool, a hash of the
  arguments (not the arguments themselves) and the outcome.
* **Stateless.** No MCP session is kept between requests (``stateless_http``),
  so the server can run behind a load balancer. ``server/discover`` and
  ``GET /.well-known/mcp.json`` describe the server, its tools, the scope
  each needs and the auth scheme, without a session.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

SCOPES = ("read", "assess", "write", "files", "admin")

# Tools that only look up reference data.
_READ = {"iris_catalog", "dd_checklist", "cross_reference", "regulatory_calendar", "esg_toolbox"}
# Tools that change saved state.
_WRITE = {"pipeline", "monitoring", "guided_assessment"}
# Tools that read or write local files or fetch URLs.
_FILES = {"pitch_deck_analyze", "impact_report", "lp_ddq_export", "product_passport", "document_analysis"}


def tool_scope(name: str) -> str:
    """The scope a tool needs; anything unlisted is an assessment."""
    if name in _READ:
        return "read"
    if name in _WRITE:
        return "write"
    if name in _FILES:
        return "files"
    return "assess"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def default_token_path() -> Path:
    from impact_vision.config.paths import get_config_dir

    return Path(get_config_dir()) / "mcp_tokens.json"


@dataclass
class Principal:
    label: str
    scopes: frozenset[str]
    tenant_id: str = "default"

    def allows(self, scope: str) -> bool:
        return "admin" in self.scopes or scope in self.scopes


class TokenStore:
    """Hashed bearer tokens in a JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_token_path()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        data: dict[str, dict[str, Any]] = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        return data

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    def create(self, label: str, scopes: list[str], *, days: int | None = None, tenant: str = "default") -> str:
        """Create a token and return it. It is not stored and can't be shown again."""
        from impact_vision.impact.identity import valid_tenant_id

        if not valid_tenant_id(tenant):
            raise ValueError(f"invalid tenant id {tenant!r}")
        bad = [s for s in scopes if s not in SCOPES]
        if bad or not scopes:
            raise ValueError(f"unknown scope(s) {bad}; choose from {', '.join(SCOPES)}")
        data = self._load()
        if any(v["label"] == label for v in data.values()):
            raise ValueError(f"a token labelled {label!r} already exists")
        token = "ivmcp_" + secrets.token_urlsafe(32)
        data[_hash(token)] = {"label": label, "scopes": sorted(set(scopes)), "tenant": tenant,
                              "created": int(time.time()),
                              "expires": int(time.time() + days * 86400) if days else None}
        self._save(data)
        return token

    def list(self) -> list[dict[str, Any]]:
        return [{"label": v["label"], "scopes": v["scopes"], "tenant": v.get("tenant", "default"),
                 "created": v["created"], "expires": v.get("expires")}
                for v in self._load().values()]

    def revoke(self, label: str) -> bool:
        data = self._load()
        keep = {k: v for k, v in data.items() if v["label"] != label}
        if len(keep) == len(data):
            return False
        self._save(keep)
        return True

    def verify(self, token: str) -> Principal | None:
        if not token:
            return None
        entry = self._load().get(_hash(token))
        if not entry or (entry.get("expires") and entry["expires"] < time.time()):
            return None
        return Principal(entry["label"], frozenset(entry["scopes"]), entry.get("tenant", "default"))


def discovery(tool_names: list[str], version: str) -> dict[str, Any]:
    """What a client needs before its first call: tools, scopes, auth."""
    return {
        "name": "Impact Vision",
        "version": version,
        "transport": "streamable-http",
        "stateless": True,
        "endpoint": "/mcp",
        "auth": {"scheme": "bearer", "header": "Authorization", "scopes": list(SCOPES)},
        "tools": [{"name": n, "scope": tool_scope(n)} for n in sorted(tool_names)],
    }


def _audit(principal: Principal | None, tool: str, args: Any, outcome: str) -> None:
    try:
        from impact_vision.impact.audit_trail import AuditTrail
        from impact_vision.impact.state_store import get_state_store

        digest = hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()
        AuditTrail(fund_id="mcp", store=get_state_store()).record_event(
            event_type="mcp_tool_call", actor=principal.label if principal else "anonymous",
            payload={"tool": tool, "scope": tool_scope(tool), "args_sha256": digest, "outcome": outcome})
    except Exception:  # noqa: BLE001 - auditing must never take the server down
        import logging

        logging.getLogger(__name__).exception("MCP audit write failed")


async def _send_json(send: Send, status: int, body: Any, headers: list[tuple[bytes, bytes]] | None = None) -> None:
    raw = json.dumps(body).encode("utf-8")
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(raw)).encode()),
                            *(headers or [])]})
    await send({"type": "http.response.body", "body": raw})


class AuthenticatedMCP:
    """ASGI wrapper: bearer auth, per-tool scopes, audit, discovery."""

    def __init__(self, app: ASGIApp, store: TokenStore, *, tool_names: list[str], version: str) -> None:
        self.app, self.store = app, store
        self.info = discovery(tool_names, version)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if scope["method"] == "GET" and scope["path"] == "/.well-known/mcp.json":
            await _send_json(send, 200, self.info)
            return
        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode("latin-1")
        token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        principal = self.store.verify(token)
        if principal is None:
            await _send_json(send, 401, {"error": "invalid_token"},
                             [(b"www-authenticate", b'Bearer realm="impact-vision-mcp"')])
            return

        from impact_vision.impact.identity import Identity, acting_as

        who = Identity(sub=f"mcp:{principal.label}", tenant_id=principal.tenant_id,
                       roles=("tenant_admin",) if principal.allows("admin") else ("analyst",), auth="mcp")
        body = b""
        more = True
        while more:
            message = await receive()
            body += message.get("body", b"")
            more = message.get("more_body", False)
        try:
            payload = json.loads(body) if body else None
        except ValueError:
            payload = None
        messages = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []

        for msg in messages:
            if msg.get("method") == "server/discover":
                await _send_json(send, 200, {"jsonrpc": "2.0", "id": msg.get("id"), "result": self.info})
                return
        calls = [m for m in messages if m.get("method") == "tools/call"]
        for msg in calls:
            params = msg.get("params") or {}
            name = str(params.get("name", ""))
            if not principal.allows(tool_scope(name)):
                with acting_as(who):
                    _audit(principal, name, params.get("arguments"), "denied")
                await _send_json(send, 403, {"jsonrpc": "2.0", "id": msg.get("id"), "error": {
                    "code": -32003, "message": f"token '{principal.label}' lacks scope '{tool_scope(name)}' for {name}"}})
                return

        status: dict[str, int] = {}

        async def replay() -> Message:
            nonlocal body
            chunk, body = body, b""
            return {"type": "http.request", "body": chunk, "more_body": False}

        async def watch(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        with acting_as(who):  # tools and the state store see the token's tenant (W5.3)
            await self.app(scope, replay, watch)
            for msg in calls:
                params = msg.get("params") or {}
                _audit(principal, str(params.get("name", "")), params.get("arguments"),
                       "ok" if status.get("code", 500) < 400 else f"http_{status.get('code')}")


def build_app(store: TokenStore | None = None, *, allowed_hosts: list[str] | None = None) -> AuthenticatedMCP:
    """The authenticated, stateless Streamable HTTP app.

    ``allowed_hosts`` (``host:port`` patterns) extends the SDK's DNS-rebinding
    guard when the server is reached by a name other than localhost.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    from impact_vision.impact.mcp_server import IMPACT_VISION_MCP_VERSION, mcp

    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*", *(allowed_hosts or [])]
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=hosts,
        allowed_origins=[f"http://{h}" for h in hosts] + [f"https://{h}" for h in hosts])

    mcp.settings.stateless_http = True
    mcp.settings.json_response = True
    mcp._session_manager = None  # noqa: SLF001 - a session manager runs once; each app gets its own
    inner = mcp.streamable_http_app()
    names = [t.name for t in mcp._tool_manager.list_tools()]  # noqa: SLF001
    return AuthenticatedMCP(inner, store or TokenStore(), tool_names=names, version=IMPACT_VISION_MCP_VERSION)


__all__ = ["SCOPES", "AuthenticatedMCP", "Principal", "TokenStore", "build_app", "discovery", "tool_scope"]
