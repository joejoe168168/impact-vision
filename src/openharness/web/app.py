"""Combined web application — chat UI + tool console + REST gateway, one process.

Launch with either::

    impact-vision serve-web                       # via the CLI helper
    uvicorn openharness.web.app:app --reload      # directly via uvicorn

The resulting FastAPI app exposes:

  * ``GET  /``                  — the conversational chat UI (ChatGPT-style)
  * ``GET  /chat``              — alias of ``/``
  * ``WS   /ws/chat``           — live agent stream (deltas, tools, prompts)
  * ``*    /api/v1/chat/*``     — sessions, provider config, uploads, artifacts
  * ``GET  /console``           — the power-user tool console (typed forms)
  * ``*    /api/v1/*``          — the full REST gateway (26 impact tools)
  * ``GET  /docs``              — Swagger UI for the REST gateway
  * ``GET  /openapi.json``      — OpenAPI schema

Set ``IMPACT_VISION_API_KEY`` to require a bearer token on every REST call and
on the WebSocket handshake (the browser passes it as a ``token`` query param,
since the WebSocket API cannot set request headers).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

try:
    from openharness.api_gateway.router import app as _gateway_app
    from openharness.api_gateway.router import verify_api_key
    from openharness.web.chat_api import build_chat_router, build_chat_ws_router
    from openharness.web.chat_ui import chat_ui_router
    from openharness.web.console import console_router
    from openharness.web.streaming import build_sse_router
except ImportError as _exc:  # pragma: no cover — optional
    raise ImportError(
        "FastAPI is required for the web console. "
        "Install with: pip install fastapi uvicorn"
    ) from _exc


# Reuse the existing REST gateway and graft the chat UI, console and streams on.
app = _gateway_app

# Chat first: it owns "/" and registers the WebSocket.
app.include_router(build_chat_router(auth_dependency=verify_api_key))
app.include_router(build_chat_ws_router())
app.include_router(chat_ui_router())

# The original tool console keeps working, now at /console.
app.include_router(console_router(root_path=False))
app.include_router(build_sse_router())


def _wrap_lifespan(previous: Any) -> Any:
    """Chain a shutdown hook onto the gateway's existing lifespan."""

    @asynccontextmanager
    async def lifespan(scope_app: Any) -> AsyncIterator[None]:
        async with previous(scope_app):
            try:
                yield
            finally:
                from openharness.web.chat_session import get_session_manager

                await get_session_manager().shutdown()

    return lifespan


app.router.lifespan_context = _wrap_lifespan(app.router.lifespan_context)


__all__ = ["app"]
