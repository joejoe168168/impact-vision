# Memory Bank

## Project Snapshot

Impact Vision is an open-source AI-powered impact measurement and SDG alignment
agent for VC and impact investment funds. The importable package remains
`openharness`; the project package/version is `impact-vision`.

## Current Release Work

- Target release: `0.15.0` ("Trust Infrastructure").
- Source roadmap: `docs/roadmap-v3.md`.
- Implementation plan: `docs/roadmap-v3-implementation.md`.
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

- Broad impact + v2/v3 regression suite: `290 passed / 4 skipped`.
- v3 + climate focused suite: `65 passed`.
- Roadmap v2 focused suite: `10 passed`.
- Ruff clean on `src/openharness/impact`, `src/openharness/tools/impact`, and
  the v2/v3 related tests.

## Notes

- Full repository `pytest` collection still includes unrelated legacy areas
  (`auth`, `mcp`, `ohmo`, `ui`, etc.) that already fail during collection in
  the current local environment.
- Package rename / removal of unused HKUDS-era modules remains deliberately
  deferred per `CLAUDE.md`.
