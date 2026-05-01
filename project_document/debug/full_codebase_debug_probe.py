"""Runtime probe for whole-codebase debug planning.

This script is intentionally outside production code. It records compact NDJSON
evidence for broad hypotheses about imports, registry wiring, duplicate paths,
and test surface distribution.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
LOG_PATH = ROOT / "debug-7de8c7.log"
SESSION_ID = "7de8c7"


#region agent log
def agent_log(run_id: str, hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
#endregion


def _normalised_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix().lower()


def probe_inventory(run_id: str) -> None:
    py_files = [p for p in ROOT.rglob("*.py") if ".git" not in p.parts and ".venv" not in p.parts]
    test_files = [p for p in py_files if "tests" in p.parts]
    src_files = [p for p in py_files if "src" in p.parts]
    duplicates = [
        rel for rel, count in Counter(_normalised_relative(p) for p in py_files).items() if count > 1
    ]
    agent_log(
        run_id,
        "H3",
        "project_document/debug/full_codebase_debug_probe.py:probe_inventory",
        "Python inventory and duplicate normalized paths",
        {
            "python_files": len(py_files),
            "src_python_files": len(src_files),
            "test_python_files": len(test_files),
            "duplicate_normalized_paths": duplicates[:50],
            "duplicate_count": len(duplicates),
        },
    )


def probe_imports(run_id: str) -> None:
    modules = [
        "openharness",
        "openharness.impact",
        "openharness.tools",
        "openharness.tools.impact",
        "openharness.api_gateway.router",
        "openharness.impact.mcp_server",
        "openharness.impact.emission_factors",
        "openharness.impact.evidence_workflow",
        "openharness.impact.exit_impact",
        "openharness.impact.greenwashing_reviewer",
        "openharness.impact.lp_narrative",
        "openharness.impact.portfolio_nlq",
        "openharness.impact.stakeholder_voice",
        "openharness.impact.verification_workspace",
    ]
    results: dict[str, str] = {}
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            results[module_name] = "ok"
        except Exception as exc:  # noqa: BLE001 - this is diagnostic evidence
            results[module_name] = f"{type(exc).__name__}: {exc}"
    agent_log(
        run_id,
        "H1",
        "project_document/debug/full_codebase_debug_probe.py:probe_imports",
        "Critical package and v3 import smoke results",
        {"results": results, "failures": {k: v for k, v in results.items() if v != "ok"}},
    )


def probe_registry(run_id: str) -> None:
    expected_v3 = {
        "emission_factors",
        "evidence_review",
        "exit_impact",
        "greenwashing_reviewer",
        "lp_narrative",
        "portfolio_query",
        "stakeholder_voice",
        "verification_workspace",
    }
    try:
        from openharness.tools import create_default_tool_registry

        registry = create_default_tool_registry()
        tool_names = sorted(tool.name for tool in registry.list_tools())
        missing = sorted(expected_v3 - set(tool_names))
        result = {"tool_count": len(tool_names), "expected_v3_missing": missing, "sample": tool_names[:20]}
    except Exception as exc:  # noqa: BLE001 - this is diagnostic evidence
        result = {"error": f"{type(exc).__name__}: {exc}"}
    agent_log(
        run_id,
        "H2",
        "project_document/debug/full_codebase_debug_probe.py:probe_registry",
        "Default tool registry and v3 tool presence",
        result,
    )


def probe_tests(run_id: str) -> None:
    test_files = sorted((ROOT / "tests").rglob("test*.py"))
    buckets = Counter(
        "v3"
        if "test_v3_" in p.name
        else "impact"
        if "impact" in p.name or "phase" in p.name or "roadmap" in p.name
        else p.relative_to(ROOT / "tests").parts[0]
        if len(p.relative_to(ROOT / "tests").parts) > 1
        else "root"
        for p in test_files
    )
    agent_log(
        run_id,
        "H5",
        "project_document/debug/full_codebase_debug_probe.py:probe_tests",
        "Test surface distribution for phased execution plan",
        {"test_file_count": len(test_files), "buckets": dict(sorted(buckets.items()))},
    )


def probe_metadata(run_id: str) -> None:
    results: dict[str, Any] = {}
    try:
        api = importlib.import_module("openharness.api_gateway.router")
        results["api_version"] = getattr(api.app, "version", None)
    except Exception as exc:  # noqa: BLE001
        results["api_error"] = f"{type(exc).__name__}: {exc}"
    try:
        mcp = importlib.import_module("openharness.impact.mcp_server")
        results["mcp_version"] = getattr(mcp, "IMPACT_VISION_MCP_VERSION", None)
        results["mcp_description"] = getattr(mcp, "IMPACT_VISION_MCP_DESCRIPTION", "")[:120]
    except Exception as exc:  # noqa: BLE001
        results["mcp_error"] = f"{type(exc).__name__}: {exc}"
    agent_log(
        run_id,
        "H4",
        "project_document/debug/full_codebase_debug_probe.py:probe_metadata",
        "Public runtime metadata version consistency",
        results,
    )


def main() -> None:
    run_id = os.environ.get("AGENT_DEBUG_RUN_ID", "initial-study")
    probe_inventory(run_id)
    probe_imports(run_id)
    probe_registry(run_id)
    probe_tests(run_id)
    probe_metadata(run_id)
    print(f"debug probe wrote runtime evidence to {LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
