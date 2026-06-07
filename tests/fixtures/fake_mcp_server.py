"""Small stdio MCP server used by integration tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mcp.server.fastmcp import FastMCP

from openharness.mcp.compat import patch_fastmcp_func_metadata

patch_fastmcp_func_metadata()

server = FastMCP("fixture-demo")


@server.tool()
def hello(name: str) -> str:
    return f"fixture-hello:{name}"


@server.resource("fixture://readme", name="Fixture Readme")
def readme() -> str:
    return "fixture resource contents"


if __name__ == "__main__":
    server.run("stdio")
