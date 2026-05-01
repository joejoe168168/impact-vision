# Logic Issue And Improvement Plan

Created: 2026-05-01
Scope: all product Python code, excluding generated caches and `project_document`

## Objective

Find logic issues that can survive a passing test suite, then turn them into an actionable improvement backlog. This complements `codebase_debug_plan.md`, which covers release gates and debug workflow.

## Plan Executed

1. Rebuild runtime baseline.
   - Install editable dev dependencies.
   - Run import smoke.
   - Run focused impact/v3 suite.
   - Run full test suite.

2. Scan product code for logic-risk patterns.
   - Broad and silent exception handlers.
   - Large files and long functions.
   - Stale version literals.
   - Naive UTC timestamps.
   - CORS wildcard exposure.
   - API, MCP, and tool registry runtime surface counts.

3. Generate structured memory.
   - `project_document/memory_bank_db.json` stores inventory, runtime surfaces, risk summaries, and findings.
   - `project_document/debug/logic_audit_report.md` stores the human-readable audit report.

4. Add static logic gate.
   - Run ruff.
   - Run mypy with explicit source path to expose typing and object-shape risks.

## Execution Results

- Full pytest: `1077 passed / 15 skipped / 1 xfailed`.
- Focused impact/v3 pytest: `105 passed`.
- Import smoke: pass, `37` package init files, `21` import groups, `71` tools.
- Ruff: pass on `src`, `tests`, and `project_document/debug`.
- Logic audit: `492` product Python files scanned, `24` API routes, `71` tools.
- Mypy: `506` errors in `77` files after `MYPYPATH=src` and explicit package bases.

## Priority Logic Risks

1. Silent broad exception handling.
   - Evidence: `61` broad handlers start with `pass`, `return`, or `continue`.
   - Risk: user-visible failures can be hidden, especially in tool wrappers, integrations, and service code.
   - Improvement: add focused regression tests before changing behavior; replace silent handling with typed exceptions or structured `ToolResult` errors where applicable.

2. Large functions and large files.
   - Evidence: `18` large files and `95` long functions.
   - Risk: high bug density and low reviewability in command registry, report generation, MCP server, SDK, and legacy orchestration modules.
   - Improvement: only split when touching nearby behavior; use characterization tests first.

3. Type-shape drift.
   - Evidence: mypy found `type-arg=215`, `no-untyped-def=79`, `attr-defined=21`, `import-untyped=19`, `no-any-return=16`, `operator=14`.
   - Risk: runtime logic may rely on `object`/`Any` where structured models are expected.
   - Improvement: start with `fund_thesis.py`, framework scoring modules, `sdk.py`, and `mcp_server.py`; add typed dicts or Pydantic models where data contracts cross module boundaries.

4. Timezone-naive timestamps.
   - Evidence: product `datetime.utcnow()` occurrences were removed from Mochat; `2` remaining occurrences are in tests.
   - Risk: audit trails, signed feeds, and gateway timestamps can become ambiguous across timezone boundaries.
   - Improvement: keep using `datetime.now(UTC)` for product timestamps and clean up legacy test fixtures opportunistically.

5. Version and metadata drift.
   - Evidence: fixed API/MCP/Copilot public version drift; audit still finds `5` older literals, mostly legacy protocol/runtime version constants.
   - Risk: clients and docs may trust stale metadata.
   - Improvement: classify literals as protocol versions vs release versions; bind release metadata to package metadata where intended.

6. Open CORS default.
   - Evidence: wildcard CORS remains allowed for local/open-source defaults, but credentials are now disabled when wildcard origins are active.
   - Risk: acceptable for local open-source defaults, but risky for hosted deployments.
   - Improvement: keep dev default documented and allow production origins via environment configuration.

## Next Execution Order

1. Add regression tests around the highest-risk silent exception handlers in user-facing surfaces.
2. Add a metadata test asserting FastAPI/MCP/Copilot versions match installed package metadata.
3. Add registry tests that fail if expected production tools are silently skipped.
4. Run a staged typing cleanup for `fund_thesis.py` and framework modules before expanding to SDK/MCP.
5. Add stricter hosted-deployment CORS documentation around `IMPACT_VISION_CORS_ORIGINS`.
6. Investigate Windows/Python 3.13 async subprocess cleanup warnings in UI/tool tests.

## Current Verdict

Runtime health is strong: full suite, focused suite, import smoke, registry, and ruff all pass. This pass also fixed concrete logic/import issues in API CORS, Copilot metadata, Mochat timestamps, and optional channel helpers. The remaining backlog is mainly hidden failure modes, type-shape drift, and async warning cleanup.
