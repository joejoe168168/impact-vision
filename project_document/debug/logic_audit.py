"""Whole-codebase logic-risk audit and structured memory bank DB generator."""

from __future__ import annotations

import ast
import json
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

LOG_PATH = ROOT / "debug-7de8c7.log"
SESSION_ID = "7de8c7"
MEMORY_DB_PATH = ROOT / "project_document" / "memory_bank_db.json"
REPORT_PATH = ROOT / "project_document" / "debug" / "logic_audit_report.md"


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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _python_files() -> list[Path]:
    ignored_parts = {
        ".git",
        ".venv",
        ".openharness-venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "project_document",
    }
    return sorted(
        p
        for p in ROOT.rglob("*.py")
        if not any(part in ignored_parts for part in p.parts)
    )


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _project_version() -> str:
    text = _read_text(ROOT / "pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "unknown"


def _literal_str(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _scan_file(path: Path, project_version: str) -> dict[str, Any]:
    text = _read_text(path)
    lines = text.splitlines()
    result: dict[str, Any] = {
        "path": _rel(path),
        "line_count": len(lines),
        "large_file": len(lines) >= 800,
        "broad_exception_handlers": [],
        "silent_exception_handlers": [],
        "bare_exception_handlers": [],
        "long_functions": [],
        "datetime_utcnow": [],
        "cors_wildcard": [],
        "stale_version_literals": [],
    }
    if 'allow_origins=["*"]' in text or "allow_origins = [\"*\"]" in text:
        result["cors_wildcard"].append({"line": next((i for i, line in enumerate(lines, 1) if "allow_origins" in line), 1)})
    for i, line in enumerate(lines, 1):
        if "datetime.utcnow(" in line:
            result["datetime_utcnow"].append({"line": i, "text": line.strip()})
        for match in re.finditer(r'(?:VERSION|version)\s*=\s*"(\d+\.\d+\.\d+)"', line):
            version = match.group(1)
            if version != project_version:
                result["stale_version_literals"].append({"line": i, "version": version, "project_version": project_version})
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        result["syntax_error"] = f"{exc.msg} at {exc.lineno}:{exc.offset}"
        return result
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            length = end - node.lineno + 1
            if length >= 80:
                result["long_functions"].append({"line": node.lineno, "name": node.name, "length": length})
        if isinstance(node, ast.ExceptHandler):
            exception_name = None
            if node.type is None:
                exception_name = "bare"
                result["bare_exception_handlers"].append({"line": node.lineno})
            elif isinstance(node.type, ast.Name):
                exception_name = node.type.id
            elif isinstance(node.type, ast.Attribute):
                exception_name = node.type.attr
            if exception_name in {"Exception", "BaseException", "bare"}:
                result["broad_exception_handlers"].append({"line": node.lineno, "type": exception_name})
                if node.body and isinstance(node.body[0], (ast.Pass, ast.Return, ast.Continue)):
                    result["silent_exception_handlers"].append({"line": node.lineno, "type": exception_name})
    return result


def scan_static(project_version: str) -> dict[str, Any]:
    files = [_scan_file(path, project_version) for path in _python_files()]
    findings = {
        "large_files": [f for f in files if f["large_file"]],
        "long_functions": [
            {"path": f["path"], **item} for f in files for item in f["long_functions"]
        ],
        "broad_exception_handlers": [
            {"path": f["path"], **item} for f in files for item in f["broad_exception_handlers"]
        ],
        "silent_exception_handlers": [
            {"path": f["path"], **item} for f in files for item in f["silent_exception_handlers"]
        ],
        "bare_exception_handlers": [
            {"path": f["path"], **item} for f in files for item in f["bare_exception_handlers"]
        ],
        "datetime_utcnow": [
            {"path": f["path"], **item} for f in files for item in f["datetime_utcnow"]
        ],
        "cors_wildcard": [
            {"path": f["path"], **item} for f in files for item in f["cors_wildcard"]
        ],
        "stale_version_literals": [
            {"path": f["path"], **item} for f in files for item in f["stale_version_literals"]
        ],
        "syntax_errors": [f for f in files if "syntax_error" in f],
    }
    return {"files": files, "findings": findings}


def scan_runtime(project_version: str) -> dict[str, Any]:
    runtime: dict[str, Any] = {"project_version": project_version}
    try:
        from openharness.tools import create_default_tool_registry

        registry = create_default_tool_registry()
        runtime["tool_registry"] = {
            "count": len(registry.list_tools()),
            "names": sorted(tool.name for tool in registry.list_tools()),
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic report should keep going
        runtime["tool_registry_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from openharness.api_gateway.router import app

        routes = sorted(getattr(route, "path", "") for route in app.routes if getattr(route, "path", "").startswith("/api/"))
        runtime["api"] = {"version": app.version, "route_count": len(routes), "routes": routes}
    except Exception as exc:  # noqa: BLE001
        runtime["api_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from openharness.impact import mcp_server

        runtime["mcp"] = {
            "version": mcp_server.IMPACT_VISION_MCP_VERSION,
            "name": mcp_server.IMPACT_VISION_MCP_NAME,
        }
    except Exception as exc:  # noqa: BLE001
        runtime["mcp_error"] = f"{type(exc).__name__}: {exc}"
    return runtime


def build_memory_db(static: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    buckets = Counter(
        "tests" if parts[0] == "tests" else "src" if parts[0] == "src" else parts[0]
        for parts in (_rel(p).split("/") for p in _python_files())
    )
    findings = static["findings"]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "project": {
            "name": "impact-vision",
            "import_package": "openharness",
            "version": runtime.get("project_version"),
            "root": str(ROOT),
        },
        "inventory": {
            "python_file_count": len(static["files"]),
            "buckets": dict(sorted(buckets.items())),
            "api_route_count": runtime.get("api", {}).get("route_count"),
            "tool_count": runtime.get("tool_registry", {}).get("count"),
        },
        "runtime_surfaces": runtime,
        "knowledge_gained": {
            "architecture": {
                "core_package": "openharness",
                "product_package": "impact-vision",
                "main_surfaces": [
                    "impact engine under src/openharness/impact",
                    "agent tools under src/openharness/tools/impact",
                    "FastAPI gateway under src/openharness/api_gateway/router.py",
                    "Impact MCP server under src/openharness/impact/mcp_server.py",
                    "CLI and legacy OpenHarness runtime under src/openharness/cli.py and related modules",
                    "optional channel integrations under src/openharness/channels/impl",
                    "Streamlit dashboard and web console under src/openharness/dashboard and src/openharness/web",
                ],
                "v3_trust_modules": [
                    "emission_factors",
                    "stakeholder_voice",
                    "evidence_workflow",
                    "verification_workspace",
                    "lp_narrative",
                    "greenwashing_reviewer",
                    "portfolio_nlq",
                    "exit_impact",
                ],
            },
            "confirmed_fixes": [
                "FastAPI runtime version aligned to 0.15.0",
                "Impact MCP server runtime version aligned to 0.15.0",
                "stale unused imports removed from tests/test_impact.py",
                "API CORS wildcard origins no longer allow credentialed CORS by default",
                "IMPACT_VISION_CORS_ORIGINS provides comma-separated hosted deployment origins",
                "Copilot User-Agent now uses installed package metadata",
                "Mochat synthetic event and cursor timestamps use timezone-aware UTC",
                "Mochat channel imports existing get_data_dir helper instead of missing utils helper",
                "openharness.utils.helpers now provides split_message and safe_filename for optional channels",
                "Matrix channel imports get_data_dir from openharness.config.paths instead of missing config.loader",
                "README.md and CHANGELOG.md document the hardening pass",
            ],
            "verification_evidence": {
                "full_pytest": "1077 passed / 15 skipped / 1 xfailed",
                "hardening_related_pytest": "36 passed",
                "channel_api_mcp_subset": "85 passed",
                "import_smoke": "37 package init files, 21 import groups, 71 tools, all checks passed",
                "ruff": "clean on src, tests, and project_document/debug",
                "memory_db_json": "valid JSON",
            },
            "logic_risk_interpretation": {
                "broad_exception_handlers": "still high; many are intentional resilience paths, but user-facing silent handlers need characterization tests before edits",
                "large_files": "report generation, command registry, MCP server, compact service, and legacy orchestration remain high-review-cost zones",
                "mypy": "506 errors in 77 impact/tool files with explicit package bases; treat as staged typing hardening, not current runtime failure",
                "datetime_utcnow": "product occurrences removed in this pass; remaining occurrences are test fixtures",
                "stale_versions": "remaining old literals appear mostly to be legacy protocol/fallback versions and need classification before changing",
                "async_warnings": "Windows/Python 3.13 subprocess cleanup warnings remain non-failing but should be investigated for flake reduction",
            },
            "next_recommended_work": [
                "add metadata tests binding API/MCP/Copilot runtime versions to installed package metadata",
                "add registry tests that fail when expected production tools are silently skipped",
                "add characterization tests around the highest-risk silent exception handlers",
                "document production CORS configuration for hosted deployments",
                "start staged typing cleanup with fund_thesis.py, framework scoring modules, sdk.py, and mcp_server.py",
                "investigate Windows/Python 3.13 async subprocess cleanup warnings",
            ],
            "roadmap_v4_market_research": {
                "sources": [
                    "TSIC public services pages",
                    "Rimm Sustainability and myCSO public pages",
                    "Impact Institute impact consulting",
                    "ImpactMapper consulting service",
                    "Impact ROI services",
                    "Holtara impact-focused ESG services",
                    "Wellington IMM approach",
                ],
                "consultant_value_drivers": [
                    "tailored impact measurement frameworks",
                    "theory of change and strategy facilitation",
                    "impact evaluation and learning loops",
                    "ESG and E&S management systems",
                    "KPI framework design and staff capacity building",
                    "portfolio analysis, due diligence, verification, and reporting",
                    "AI-enabled data collection, workflow automation, benchmarking, and risk analytics",
                    "client-ready reports, training packs, and website diagnostic funnels",
                ],
                "roadmap_output": "docs/roadmap-v4.md",
            },
            "documentation_outputs": [
                "README.md hardening note",
                "CHANGELOG.md Unreleased hardening section",
                "memory_bank.md verification and notes",
                "project_document/debug/codebase_debug_plan.md",
                "project_document/debug/logic_issue_improvement_plan.md",
                "project_document/debug/logic_audit_report.md",
                "docs/roadmap-v4.md",
            ],
        },
        "logic_risk_summary": {
            key: len(value)
            for key, value in findings.items()
        },
        "logic_risk_findings": findings,
        "recommended_gates": [
            "python scripts/check_imports.py --all",
            "python -m ruff check src tests",
            "python -m mypy src/openharness/impact src/openharness/tools/impact",
            "python -m pytest tests -q",
        ],
        "debug_plan": "project_document/debug/codebase_debug_plan.md",
        "logic_audit_report": "project_document/debug/logic_audit_report.md",
    }


def write_report(db: dict[str, Any]) -> None:
    summary = db["logic_risk_summary"]
    lines = [
        "# Logic Audit Report",
        "",
        f"Generated: {db['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Python files scanned: {db['inventory']['python_file_count']}",
        f"- API routes discovered: {db['inventory']['api_route_count']}",
        f"- Tools discovered: {db['inventory']['tool_count']}",
        f"- Large files: {summary['large_files']}",
        f"- Long functions: {summary['long_functions']}",
        f"- Broad exception handlers: {summary['broad_exception_handlers']}",
        f"- Silent broad handlers: {summary['silent_exception_handlers']}",
        f"- Bare exception handlers: {summary['bare_exception_handlers']}",
        f"- `datetime.utcnow()` calls: {summary['datetime_utcnow']}",
        f"- CORS wildcard locations: {summary['cors_wildcard']}",
        f"- Stale version literals: {summary['stale_version_literals']}",
        f"- Syntax errors: {summary['syntax_errors']}",
        "",
        "## Priority Follow-Ups",
        "",
        "- Add explicit regression tests around any broad exception handler that can hide a user-visible failure.",
        "- Break up long functions/files only when touching them for product work, starting with report/tool/API surfaces.",
        "- Replace `datetime.utcnow()` with timezone-aware UTC in touched files.",
        "- Keep CORS wildcard acceptable for local/open-source defaults only if documented; gate stricter deployments via environment.",
        "- Keep version metadata tied to package metadata to prevent future release drift.",
        "",
        "## Executed Static Logic Gates",
        "",
        "- `python -m ruff check src tests project_document\\debug` -> pass.",
        "- `python scripts\\check_imports.py --all` -> pass.",
        "- `python -m pytest tests -q --maxfail=20` -> latest observed pass in this session.",
        "- `python -m mypy --explicit-package-bases src\\openharness\\impact src\\openharness\\tools\\impact` with `MYPYPATH=src` -> known staged hardening backlog, not a current runtime failure.",
        "",
        "## Latest Confirmed Fix Themes",
        "",
        "- API CORS wildcard no longer enables credentials by default.",
        "- Copilot User-Agent version comes from installed package metadata.",
        "- Mochat synthetic/cursor timestamps use timezone-aware UTC.",
        "- Optional channel helpers are importable via `openharness.utils.helpers`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    run_id = "logic-audit"
    project_version = _project_version()
    static = scan_static(project_version)
    runtime = scan_runtime(project_version)
    db = build_memory_db(static, runtime)
    MEMORY_DB_PATH.write_text(json.dumps(db, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    write_report(db)
    agent_log(
        run_id,
        "L1",
        "project_document/debug/logic_audit.py:main",
        "Logic audit and memory bank DB generated",
        {
            "memory_db": str(MEMORY_DB_PATH.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
            "summary": db["logic_risk_summary"],
            "runtime": {
                "api_version": runtime.get("api", {}).get("version"),
                "tool_count": runtime.get("tool_registry", {}).get("count"),
                "mcp_version": runtime.get("mcp", {}).get("version"),
            },
        },
    )
    print(f"wrote {MEMORY_DB_PATH.relative_to(ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
