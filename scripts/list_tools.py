#!/usr/bin/env python3
"""Print the registered Impact Vision tool surface as a Markdown table."""

from __future__ import annotations

from openharness.tools import create_default_tool_registry


def main() -> None:
    tools = [
        tool
        for tool in create_default_tool_registry().list_tools()
        if type(tool).__module__.startswith("openharness.tools.impact.")
    ]
    print(f"Impact tools: {len(tools)}\n")
    print("| Tool | Description |")
    print("|------|-------------|")
    for tool in sorted(tools, key=lambda item: item.name):
        description = " ".join(tool.description.split()).replace("|", "\\|")
        print(f"| `{tool.name}` | {description} |")


if __name__ == "__main__":
    main()
