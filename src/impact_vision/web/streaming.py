"""Server-Sent Events (SSE) streaming endpoint (Phase 15.6).

Turns any callable that emits a stream of events into an HTTP SSE
response that the Web Console JavaScript can consume with the built-in
``EventSource`` API. Used to stream progress from long-running tools
(portfolio roll-ups, full report renders, bulk claim extraction).

Design
------
* Pure standard-library in the event wire format — no ``sse-starlette``
  dependency needed.
* Works both sync (a generator) and async (an async-generator) streams.
* Every event has a ``type`` field (``progress`` / ``log`` / ``result``
  / ``error`` / ``done``) so the client can route cleanly.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Iterable

log = logging.getLogger(__name__)


def sse_format(event_type: str, data: Any) -> str:
    """Encode a single Server-Sent Event frame."""
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    # SSE grammar: ``event: <type>\ndata: <payload>\n\n``
    lines = [f"event: {event_type}"]
    for line in str(payload).splitlines() or [""]:
        lines.append(f"data: {line}")
    lines.append("")  # terminator
    return "\n".join(lines) + "\n"


async def sync_to_async(stream: Iterable[tuple[str, Any]]) -> AsyncIterator[tuple[str, Any]]:
    """Run a blocking iterator inside a threadpool so we don't block the event loop."""
    loop = asyncio.get_event_loop()
    it = iter(stream)
    while True:
        try:
            item = await loop.run_in_executor(None, next, it)
        except StopIteration:
            return
        except Exception as exc:  # noqa: BLE001
            yield ("error", {"message": str(exc)})
            return
        yield item


async def stream_as_sse(
    stream: AsyncIterator[tuple[str, Any]] | Iterable[tuple[str, Any]],
) -> AsyncIterator[str]:
    """Consume a stream of ``(event_type, payload)`` pairs and yield SSE frames."""
    if hasattr(stream, "__aiter__"):
        async_stream = stream  # type: ignore[assignment]
    else:
        async_stream = sync_to_async(stream)  # type: ignore[arg-type]
    try:
        async for event_type, payload in async_stream:
            yield sse_format(event_type, payload)
    except asyncio.CancelledError:  # pragma: no cover
        raise
    except Exception as exc:  # noqa: BLE001
        yield sse_format("error", {"message": str(exc)})
    finally:
        yield sse_format("done", {"status": "complete"})


def build_sse_router() -> Any:
    """Return a FastAPI ``APIRouter`` exposing ``POST /api/v1/stream/echo``.

    The echo endpoint is intentionally trivial — it proves the wire format
    and gives the console a non-destructive target to smoke test against.
    Funds that need to stream real tools register additional endpoints
    through :func:`register_sse_endpoint`.
    """
    from fastapi import APIRouter
    from fastapi.responses import StreamingResponse

    router = APIRouter()

    @router.get("/api/v1/stream/echo", response_model=None)
    async def echo(msg: str = "hello", n: int = 3) -> Any:
        async def agen() -> AsyncIterator[tuple[str, Any]]:
            yield ("progress", {"percent": 0, "message": "starting"})
            for i in range(1, max(1, min(n, 10)) + 1):
                await asyncio.sleep(0.05)
                yield ("log", {"i": i, "message": f"{msg} #{i}"})
            yield ("result", {"echoed": msg, "count": n})

        return StreamingResponse(
            stream_as_sse(agen()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # Allow plug-ins to register their own tool streams
    for name, handler in _REGISTERED.items():
        _install_handler(router, name, handler)

    return router


_REGISTERED: dict[str, Callable[..., AsyncIterator[tuple[str, Any]]]] = {}


def register_sse_endpoint(
    name: str,
    handler: Callable[..., AsyncIterator[tuple[str, Any]]],
) -> None:
    """Register an additional streaming handler at ``/api/v1/stream/<name>``."""
    if not name or "/" in name:
        raise ValueError("name must be a simple URL segment")
    _REGISTERED[name] = handler


def _install_handler(router: Any, name: str, handler: Callable) -> None:
    from fastapi.responses import StreamingResponse

    async def endpoint() -> Any:
        return StreamingResponse(
            stream_as_sse(handler()),  # type: ignore[misc]
            media_type="text/event-stream",
        )
    router.add_api_route(
        f"/api/v1/stream/{name}",
        endpoint,
        methods=["GET"],
        response_model=None,
    )


__all__ = [
    "sse_format",
    "stream_as_sse",
    "sync_to_async",
    "build_sse_router",
    "register_sse_endpoint",
]
