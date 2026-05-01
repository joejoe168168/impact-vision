# Memory Bank

## Project Snapshot

Impact Vision is an open-source AI-powered impact measurement and SDG alignment
agent for VC and impact investment funds. The importable package remains
`openharness`; the project package/version is `impact-vision`.

## Current Release Work

- Target release: `0.15.0` ("Trust Infrastructure").
- Source roadmap: `docs/roadmap-v3.md`.
- Implementation plan: `docs/roadmap-v3-implementation.md`.
- Consultant-led v4 draft: `docs/roadmap-v4.md`, based on TSIC, Rimm
  Sustainability, and broader impact-consulting / IMM / ESG consulting
  benchmarks.
- v3 adds eight trust-infrastructure modules under `src/openharness/impact/`:
  `emission_factors.py`, `stakeholder_voice.py`, `evidence_workflow.py`,
  `verification_workspace.py`, `lp_narrative.py`,
  `greenwashing_reviewer.py`, `portfolio_nlq.py`, `exit_impact.py`.
- v3 adds eight matching tools under `src/openharness/tools/impact/`:
  `emission_factors`, `stakeholder_voice`, `evidence_review`,
  `verification_workspace`, `lp_narrative`, `greenwashing_reviewer`,
  `portfolio_query`, `exit_impact`.

## Review Fixes Applied

- Portfolio NLQ no longer lets `include_unverified=True` bypass the default
  `ApprovedDataPolicy`; explicit `allow_unverified_with_warning=True` is
  required.
- LP Q&A answers now require at least one verified metric citation; free text
  may only add context.
- AI extraction review approval now enforces `min_source_refs`.
- Verification workspaces validate finding evidence refs against visible
  evidence and prevent terminal findings from receiving management responses.
- Stakeholder voice quality scoring clamps inconsistent counts to 0-100 and
  emits reconciliation flags.
- Greenwashing reviewer treats quantified but unmapped claims as evidence gaps
  and uses word-aware unit detection.
- GHG data-quality scoring now rewards verified activity data.
- Roadmap v2 review fixes: collection-link datetime normalization,
  latest-submission tracking, zero-baseline anomaly detection, PCAF
  attribution cap, ISSB source-node downgrade, case-insensitive jurisdiction
  profiles, source-reference enforcement for v2 AI approvals, and portfolio
  query citation de-duplication.

## Verification

- 2026-05-01 whole-codebase debug pass:
  - Diagnostic/logic-audit inventory: `492` Python files (`349` under `src`,
    `124` under `tests`), `0` duplicate normalized Python paths.
  - Full suite after hardening fixes: `1077 passed / 15 skipped / 1 xfailed`
    on local Python 3.13.
  - Focused impact + v3 suite: `105 passed`.
  - Import smoke: all `37` package `__init__.py` files present, all `21`
    import groups verified, default registry bootstrapped with `71` tools.
  - Ruff clean on `src`, `tests`, and
    `project_document/debug/full_codebase_debug_probe.py`.
- Previous broad impact + v2/v3 regression suite: `290 passed / 4 skipped`.
- Previous v3 + climate focused suite: `65 passed`.
- Previous roadmap v2 focused suite: `10 passed`.

## Notes

- Detailed all-files debug/testing plan:
  `project_document/debug/codebase_debug_plan.md`.
- Structured memory bank database:
  `project_document/memory_bank_db.json`, including `knowledge_gained`
  sections for architecture, confirmed fixes, verification evidence,
  residual logic-risk interpretation, recommended next work, and
  documentation outputs.
- Logic issue/improvement plan and execution report:
  `project_document/debug/logic_issue_improvement_plan.md` and
  `project_document/debug/logic_audit_report.md`.
- Debug probe retained for this session:
  `project_document/debug/full_codebase_debug_probe.py`; it writes NDJSON
  evidence to `debug-7de8c7.log`.
- Logic audit summary: `492` product Python files scanned, `24` API routes,
  `71` tools, `18` large files, `95` long functions, `187` broad exception
  handlers, `61` silent broad handlers, `2` remaining test-only
  `datetime.utcnow()` occurrences, `0` CORS wildcard findings, `5` stale
  version literals, and `0` syntax errors.
- Mypy logic gate with `MYPYPATH=src` and explicit package bases currently
  reports `506` errors in `77` impact/tool files, led by generic type args,
  untyped defs, object attribute access, untyped imports, `Any` returns, and
  object arithmetic. Treat this as a staged hardening backlog rather than a
  current runtime failure; pytest/import/ruff gates pass.
- Full repository `pytest` collection originally failed in the local
  environment because declared dependencies (`typer`, `mcp`, `croniter`,
  `pytest-asyncio`) were not installed. After `python -m pip install -e
  ".[dev]"`, full suite passed. Pip reported a local tooling conflict:
  `browser-use 0.1.41` requires `pydantic<2.11.0`, while the project install
  resolved `pydantic 2.13.3`; repo tests were unaffected.
- Debug pass fixes applied: removed stale unused imports from
  `tests/test_impact.py`, aligned FastAPI runtime version to `0.15.0`, aligned
  Impact MCP server metadata version to `0.15.0`, disabled credentials for
  wildcard API CORS defaults, switched Copilot User-Agent to installed package
  metadata, made Mochat timestamps timezone-aware, and restored optional
  channel helper imports via `openharness.utils.helpers`.
- Remaining warning class: Python 3.13 / Windows async subprocess cleanup emits
  non-failing `PytestUnraisableExceptionWarning` in a few UI/tool tests.
- Package rename / removal of unused HKUDS-era modules remains deliberately
  deferred per `CLAUDE.md`.

## Roadmap v4 Research Notes

- TSIC-style value drivers: tailored impact measurement frameworks,
  integrated programme/organisation measurement models, impact evaluation,
  social investment strategy, ESG/E&S management systems, KPI frameworks,
  due diligence, verification, reporting, stakeholder engagement, training,
  and capacity building.
- Rimm-style value drivers: AI-enabled ESG data collection, workflow
  automation, framework reporting, peer benchmarking, risk ratings, supply
  chain and Scope 3 workflows, one-click reports, and impact management tied
  to funding opportunities.
- v4 product thesis: evolve Impact Vision into an impact-consultant operating
  system with engagement workspaces, theory-of-change strategy design, client
  data rooms, benchmarking/risk/value-creation intelligence, consultant-grade
  reporting, training engines, website productisation, and a governed AI
  consultant copilot.
