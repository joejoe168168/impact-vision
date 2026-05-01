# Logic Audit Report

Generated: 2026-05-01T02:24:38.771582+00:00

## Summary

- Python files scanned: 492
- API routes discovered: 24
- Tools discovered: 71
- Large files: 18
- Long functions: 95
- Broad exception handlers: 187
- Silent broad handlers: 61
- Bare exception handlers: 0
- `datetime.utcnow()` calls: 2
- CORS wildcard locations: 0
- Stale version literals: 5
- Syntax errors: 0

## Priority Follow-Ups

- Add explicit regression tests around any broad exception handler that can hide a user-visible failure.
- Break up long functions/files only when touching them for product work, starting with report/tool/API surfaces.
- Replace `datetime.utcnow()` with timezone-aware UTC in touched files.
- Keep CORS wildcard acceptable for local/open-source defaults only if documented; gate stricter deployments via environment.
- Keep version metadata tied to package metadata to prevent future release drift.

## Executed Static Logic Gates

- `python -m ruff check src tests project_document\debug` -> pass.
- `python scripts\check_imports.py --all` -> pass.
- `python -m pytest tests -q --maxfail=20` -> latest observed pass in this session.
- `python -m mypy --explicit-package-bases src\openharness\impact src\openharness\tools\impact` with `MYPYPATH=src` -> known staged hardening backlog, not a current runtime failure.

## Latest Confirmed Fix Themes

- API CORS wildcard no longer enables credentials by default.
- Copilot User-Agent version comes from installed package metadata.
- Mochat synthetic/cursor timestamps use timezone-aware UTC.
- Optional channel helpers are importable via `openharness.utils.helpers`.
