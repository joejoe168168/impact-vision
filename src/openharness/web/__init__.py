"""Web console for Impact Vision.

Exposes a lightweight single-page web UI that sits on top of the existing
FastAPI gateway (``openharness.api_gateway.router``). The console is a
single HTML file (no build step) that uses vanilla JavaScript + HTMX-style
fetch calls to drive every REST endpoint provided by the gateway.

The console mirrors the functionality of the ``impact-vision`` CLI and
the MCP server — think of it as a web-native equivalent to projects like
``sst/opencode``, ``getAsterisk/claudia`` or ``siteboon/claudecodeui``,
but bound to the Impact Vision tool surface rather than a generic shell.

Launch:

    impact-vision serve-web             # defaults to port 8787
    uvicorn openharness.web.app:app     # equivalent manual invocation

If the FastAPI gateway is already running, the console is also mounted at
``/`` of that app so a single process can serve both the REST API and the
UI.
"""

from openharness.web.console import (
    console_router,
    render_console_html,
)

__all__ = [
    "console_router",
    "render_console_html",
]
