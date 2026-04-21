"""Combined web application — console SPA + REST gateway in one process.

Launch with either::

    impact-vision serve-web                       # via the CLI helper
    uvicorn openharness.web.app:app --reload      # directly via uvicorn

The resulting FastAPI app exposes:

  * ``GET  /``             — the web console SPA
  * ``GET  /console``      — alias of ``/``
  * ``*    /api/v1/*``     — the full REST gateway (26 tools)
  * ``GET  /docs``         — Swagger UI for the REST gateway
  * ``GET  /openapi.json`` — OpenAPI schema
"""
from __future__ import annotations

try:
    from openharness.api_gateway.router import app as _gateway_app
    from openharness.web.console import console_router
    from openharness.web.streaming import build_sse_router
except ImportError as _exc:  # pragma: no cover — optional
    raise ImportError(
        "FastAPI is required for the web console. "
        "Install with: pip install fastapi uvicorn"
    ) from _exc


# Reuse the existing REST gateway and graft the console + SSE routes onto it.
app = _gateway_app
app.include_router(console_router())
app.include_router(build_sse_router())


__all__ = ["app"]
