#!/usr/bin/env python3
"""CI smoke checks for package import stability.

Catches regressions like missing __init__.py files, circular imports,
and broken tool registry bootstrap.

Usage:
    python scripts/check_imports.py --verify-init   # Ensure __init__.py exists
    python scripts/check_imports.py --smoke          # Test critical imports
    python scripts/check_imports.py --registry       # Test tool registry
    python scripts/check_imports.py --all            # Run everything
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "openharness"

PACKAGES_REQUIRING_INIT = [
    "",
    "api",
    "auth",
    "bridge",
    "channels",
    "channels/bus",
    "channels/impl",
    "commands",
    "config",
    "coordinator",
    "engine",
    "hooks",
    "impact",
    "impact/frameworks",
    "keybindings",
    "mcp",
    "memory",
    "output_styles",
    "permissions",
    "personalization",
    "plugins",
    "prompts",
    "sandbox",
    "services",
    "services/compact",
    "services/lsp",
    "skills",
    "state",
    "swarm",
    "tasks",
    "themes",
    "tools",
    "tools/impact",
    "ui",
    "utils",
    "vim",
    "voice",
]

CRITICAL_IMPORTS = [
    ("openharness.config", ["load_settings", "save_settings", "Settings", "get_config_file_path"]),
    ("openharness.bridge", ["build_sdk_url", "WorkSecret"]),
    ("openharness.permissions", ["PermissionMode"]),
    ("openharness.hooks", ["HookEvent"]),
    ("openharness.memory", ["find_relevant_memories", "load_memory_prompt", "add_memory_entry"]),
    ("openharness.services", ["estimate_tokens", "compact_messages", "summarize_messages"]),
    ("openharness.engine", ["QueryEngine"]),
    ("openharness.tools", ["ToolRegistry", "create_default_tool_registry"]),
    ("openharness.themes", ["list_themes", "load_theme"]),
    ("openharness.keybindings", ["load_keybindings"]),
    ("openharness.voice", ["extract_keyterms"]),
    ("openharness.output_styles", ["load_output_styles"]),
    ("openharness.commands", ["CommandContext", "create_default_command_registry"]),
    ("openharness.sandbox", ["SandboxUnavailableError"]),
    ("openharness.skills", ["load_skill_registry"]),
    ("openharness.tasks", ["get_task_manager"]),
    ("openharness.plugins", ["load_plugins"]),
    ("openharness.prompts", ["build_runtime_system_prompt"]),
    ("openharness.state", ["AppState", "AppStateStore"]),
    ("openharness.impact", ["Company", "Metric", "Assessment"]),
    ("openharness.services.lsp", ["go_to_definition", "find_references"]),
]


def verify_init_files() -> bool:
    ok = True
    for pkg in PACKAGES_REQUIRING_INIT:
        init_path = SRC_ROOT / pkg / "__init__.py" if pkg else SRC_ROOT / "__init__.py"
        if not init_path.exists():
            print(f"MISSING: {init_path.relative_to(SRC_ROOT.parent.parent)}")
            ok = False
    if ok:
        print(f"OK: all {len(PACKAGES_REQUIRING_INIT)} __init__.py files present")
    return ok


def smoke_test_imports() -> bool:
    ok = True
    for module_path, names in CRITICAL_IMPORTS:
        try:
            mod = importlib.import_module(module_path)
            for name in names:
                if not hasattr(mod, name):
                    print(f"MISSING ATTR: {module_path}.{name}")
                    ok = False
        except Exception as exc:
            print(f"IMPORT FAILED: {module_path} -> {exc}")
            ok = False
    if ok:
        print(f"OK: all {len(CRITICAL_IMPORTS)} import groups verified")
    return ok


def test_registry() -> bool:
    try:
        from openharness.tools import create_default_tool_registry

        registry = create_default_tool_registry()
        tools = registry.list_tools()
        names = sorted(t.name for t in tools)
        print(f"OK: registry bootstrapped with {len(tools)} tools")

        essential = {"bash", "grep", "glob", "read_file", "write_file", "edit_file"}
        missing = essential - set(names)
        if missing:
            print(f"WARNING: essential tools missing from registry: {missing}")
            return False
        return True
    except Exception as exc:
        print(f"REGISTRY FAILED: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Import smoke checks")
    parser.add_argument("--verify-init", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--registry", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if not any([args.verify_init, args.smoke, args.registry, args.all]):
        args.all = True

    results = []

    if args.verify_init or args.all:
        print("=== Verifying __init__.py files ===")
        results.append(verify_init_files())

    if args.smoke or args.all:
        print("\n=== Smoke-testing imports ===")
        results.append(smoke_test_imports())

    if args.registry or args.all:
        print("\n=== Testing tool registry ===")
        results.append(test_registry())

    if all(results):
        print("\nAll checks passed.")
    else:
        print("\nSome checks FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
