"""High-level MCP server class for SDK v1 (FastMCP) and v2 (MCPServer)."""

from __future__ import annotations

from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:  # mcp 2.x renamed FastMCP → MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore[assignment]


def create_highlevel_server(name: str, **kwargs: Any) -> FastMCP:
    """Instantiate FastMCP / MCPServer, dropping kwargs the class rejects."""
    try:
        return FastMCP(name, **kwargs)
    except TypeError:
        return FastMCP(name)


__all__ = ["FastMCP", "create_highlevel_server"]
