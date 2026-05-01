# Impact Vision Whole-Codebase Debug Plan

Created: 2026-05-01
Protocol: Dev-Flow v3.0 / Debug Mode
Scope: all repository runtime surfaces from v0.01 through v0.15.0

## Runtime Evidence Baseline

- Diagnostic inventory: 491 Python files, 348 under `src`, 123 under `tests`.
- Pytest-discovered test files: 106, spanning impact, v3, API, MCP, UI, tools, services, swarm, commands, bridge, config, plugins, sandbox, tasks, and OHMO.
- Duplicate normalized Python paths: 0.
- Post-fix critical imports: all checked modules import cleanly.
- Post-fix default registry: 71 tools registered; all 8 v3 tools present.
- Post-fix metadata: API version `0.15.0`, MCP version `0.15.0`.
- Verification commands executed:
  - `python -m pytest tests -q --maxfail=20` -> 1073 passed / 15 skipped / 1 xfailed.
  - `python -m pytest tests\test_impact.py ... tests\test_v3_tool_wrappers.py -q` -> 105 passed.
  - `python -m ruff check src tests project_document\debug\full_codebase_debug_probe.py` -> clean.
  - `python scripts\check_imports.py --all` -> all checks passed.

## Initial Hypotheses And Outcomes

H1: Import/bootstrap drift exists across package boundaries.
Outcome: Initially confirmed in the local environment because the package was not installed and `mcp` was missing. After `pip install -e ".[dev]"`, post-fix probe showed all critical imports ok.

H2: Tool registry silently drops tools when optional dependencies are absent.
Outcome: Partially confirmed before dependency install; registry count was 66. After dev install, registry count is 71 and all v3 tools are present. Keep this as a CI guard because `_register_if_available()` intentionally suppresses import errors.

H3: Windows/POSIX path duplication or duplicated test files cause collection ambiguity.
Outcome: Rejected by runtime probe: duplicate normalized Python path count is 0.

H4: Public runtime metadata is stale after the 0.15.0 release work.
Outcome: Confirmed and fixed. `api_gateway.router` exposed `0.14.0`; `impact.mcp_server` exposed `0.7.0`. Both now expose `0.15.0`.

H5: Full-suite failure is likely environment/config rather than v3 logic.
Outcome: Confirmed. Before installing dev dependencies, collection failed on missing `typer`, `mcp`, `croniter`, and missing pytest-asyncio recognition. After installing declared dev dependencies, the full suite passed.

## Bugs Fixed During This Pass

- Removed unused imports from `tests/test_impact.py`, resolving 7 ruff F401 findings.
- Updated FastAPI app version from `0.14.0` to `0.15.0`.
- Updated Impact MCP server metadata version from `0.7.0` to `0.15.0`.
- Added `project_document/debug/full_codebase_debug_probe.py`, a non-production diagnostic probe that writes Debug Mode NDJSON evidence to `debug-7de8c7.log`.

## Residual Risks

- The local dependency install upgraded `pydantic` to 2.13.3 and pip reported a conflict with `browser-use 0.1.41`, which requires `<2.11.0`. This did not affect repo tests, but it is a local tooling risk outside the project package.
- Full suite passes on local Python 3.13, but CI is pinned to Python 3.11. Continue validating both when touching async, UI, or dependency-sensitive files.
- The full suite emits Windows/Python 3.13 async transport warnings in subprocess-oriented tests. They did not fail the suite, but they should be tracked if they grow into flaky failures.
- `_register_if_available()` masks import exceptions by design. Add explicit registry tests for every expected production tool before future releases.

## All-Files Debug Strategy

### Phase 0: Environment Reproducibility

Goal: ensure failures are product failures, not missing local setup.

Commands:

```powershell
python -m pip install -e ".[dev]"
python --version
python scripts\check_imports.py --all
```

Checks:

- Python 3.11 in CI and Python 3.13 local both import `openharness`.
- Required runtime dependencies (`typer`, `mcp`, `croniter`, `pytest-asyncio`) are present.
- Import smoke is clean before deeper debugging.

### Phase 1: Repository Inventory And Static Gates

Goal: cover every Python file cheaply before running slower behavior tests.

Commands:

```powershell
python project_document\debug\full_codebase_debug_probe.py
python -m ruff check src tests
python -m mypy src
```

Checks:

- No duplicate normalized paths.
- No unused imports, undefined names, syntax issues, broad accidental regressions.
- Type risks triaged by subsystem, starting with `src/openharness/impact` and `src/openharness/tools/impact`.

### Phase 2: Import, Packaging, And Registry

Goal: catch broken package boundaries, missing `__init__.py`, stale public exports, and silently skipped tools.

Commands:

```powershell
python scripts\check_imports.py --all
python -m pytest tests\test_entrypoints tests\test_install tests\test_tools\test_impact_tools_enhancements.py -q
```

Checks:

- Every package listed in `scripts/check_imports.py` has `__init__.py`.
- `openharness.impact.__all__` exports all v2/v3 public types.
- `openharness.tools.impact.__all__` exports all impact wrappers.
- `create_default_tool_registry()` contains all mandatory core, impact, and v3 tools.

### Phase 3: Impact Engine Core

Goal: protect the analyst-facing measurement core.

Commands:

```powershell
python -m pytest tests\test_impact.py tests\test_report_generation.py tests\test_data_quality.py tests\test_metric_records.py -q
```

Coverage:

- `models`, `catalog`, `database`, `sdg_mapper`, `five_dimensions`, `gap_analysis`, `dd_checklist`, `benchmarks`.
- Report generation in text, HTML, CSV, JSON, XLSX where covered.
- Metric quality, verification status, evidence refs, and canonical record conversions.

Debug focus:

- Score inflation gates.
- Missing/invalid metric IDs.
- Unit parsing and numeric coercion.
- Report rendering regressions.
- Data quality scoring edge cases.

### Phase 4: Frameworks And Standards

Goal: prevent cross-framework mapping drift.

Commands:

```powershell
python -m pytest tests\test_impact.py tests\test_standards_registry.py tests\test_edci_completeness.py -q
```

Coverage:

- IRIS+, SDG, GRI, SASB, TCFD, SFDR PAI, EDCI, UNPRI, ISSB S1/S2, ESRS, OPIM.
- Cross-reference mapping integrity.
- Standards registry version and jurisdiction handling.

Debug focus:

- Stale framework IDs.
- Missing mapping directions.
- Jurisdiction case sensitivity.
- Required field completeness and source references.

### Phase 5: v2 Institutional Readiness Backbone

Goal: protect the foundation used by v3 trust infrastructure.

Commands:

```powershell
python -m pytest tests\test_roadmap_v2_completion.py tests\test_climate_accounting.py tests\test_evidence_graph.py tests\test_audit_trail_events.py tests\test_investee_collection.py -q
```

Coverage:

- Audit trail hash chain.
- Evidence graph lineage.
- Collection link lifecycle.
- Submission review and canonical metric conversion.
- GHG/PCAF calculations.

Debug focus:

- Temporal normalization.
- Zero baseline anomalies.
- PCAF ownership caps.
- Source-node quality downgrades.
- Review queue source-reference enforcement.

### Phase 6: v3 Trust Infrastructure

Goal: test every v3 module and wrapper as a release gate.

Commands:

```powershell
python -m pytest tests\test_v3_emission_factors.py tests\test_v3_evidence_workflow.py tests\test_v3_exit_impact.py tests\test_v3_greenwashing_reviewer.py tests\test_v3_lp_narrative.py tests\test_v3_portfolio_nlq.py tests\test_v3_stakeholder_voice.py tests\test_v3_verification_workspace.py tests\test_v3_tool_wrappers.py -q
```

Coverage:

- Versioned emission factors, uncertainty bands, inventory repricing.
- Stakeholder voice templates, consent, feedback quality, claim linkage.
- AI extraction review queue policy decisions.
- Verification workspace findings/comments lifecycle.
- LP narrative and verified-data Q&A.
- Explainable greenwashing review.
- Approved-data portfolio NLQ.
- OPIM Principle 8 exit-impact scoring.

Debug focus:

- Verified-only data enforcement.
- Audit event recording.
- Evidence-reference validation.
- Consent revocation state.
- Quantified-but-unmapped claim classification.
- Unverified metric warning behavior.

### Phase 7: Agent Tools, MCP, CLI, API

Goal: verify every user-facing automation surface wraps the same engine safely.

Commands:

```powershell
python -m pytest tests\test_tools tests\test_mcp tests\test_commands tests\test_api -q
python scripts\check_imports.py --all
```

Coverage:

- Base tool input models and output normalization.
- Impact tool wrappers.
- MCP client/server flows.
- Typer CLI commands.
- FastAPI gateway endpoints.

Debug focus:

- Wrapper input coercion.
- ToolResult error semantics.
- MCP schema drift.
- API auth behavior.
- Runtime metadata version consistency.

### Phase 8: UI, Dashboard, Web Console, OHMO, Legacy OpenHarness

Goal: keep legacy surfaces from silently breaking while the product focus remains Impact Vision.

Commands:

```powershell
python -m pytest tests\test_ui tests\test_ohmo tests\test_bridge tests\test_services tests\test_swarm -q
```

Coverage:

- Textual UI, React backend launchers, runtime API key behavior.
- OHMO loading/gateway/CLI.
- Bridge session flow.
- Compaction, cron, storage services.
- Swarm/team/worktree orchestration.

Debug focus:

- Async subprocess cleanup on Windows.
- Optional MCP availability.
- Session storage lifetime.
- CLI dependency drift.
- Legacy package attack surface slated for future refactor.

### Phase 9: Data, Config, And Generated Outputs

Goal: protect externalized product data and generated artifacts.

Commands:

```powershell
impact-vision catalog stats
impact-vision dd categories
impact-vision framework list
python -m pytest tests\test_config tests\test_prompts tests\test_report_generation.py -q
```

Coverage:

- `data/dd_checklist.yaml`, `data/scoring_config.yaml`, `data/sdg_keywords.yaml`.
- Prompt construction and CLAUDE.md sync.
- Report templates and static data packaging.

Debug focus:

- Bad YAML tolerance.
- Missing packaged data.
- Broken default paths after editable/wheel install.
- Report snapshot drift.

### Phase 10: Release Hardening

Goal: catch bugs not visible in deterministic unit tests.

Checks:

- Build wheel and inspect included files.
- Run full suite on Python 3.11 and 3.13.
- Run `ruff`, `mypy`, import smoke, and full pytest in CI.
- Add property/fuzz tests for metric coercion, SDG claim normalization, framework IDs, date/time parsing, and evidence references.
- Run security-oriented review for file path handling, report output paths, external URL fetches, API auth, and secret redaction.

## Debug Loop For Any New Failure

1. Generate 3-5 precise hypotheses for the failure.
2. Add 2-6 targeted logs wrapped in `#region agent log` / `#endregion`.
3. Delete only `debug-7de8c7.log` before the run.
4. Reproduce with the smallest command that exercises the failure.
5. Classify each hypothesis as confirmed, rejected, or inconclusive using log lines.
6. Fix only confirmed causes.
7. Keep instrumentation active for post-fix verification.
8. Rerun the same command and compare pre/post evidence.
9. Remove debug instrumentation only after verification and user confirmation.

## Recommended Release Gate

Before tagging the next release:

```powershell
python -m pip install -e ".[dev]"
python scripts\check_imports.py --all
python -m ruff check src tests
python -m pytest tests -q
```

Expected current baseline:

- Import smoke: pass.
- Ruff: pass.
- Pytest: 1073 passed / 15 skipped / 1 xfailed.
