# Impact Vision — Roadmap v3 Implementation Plan

**Date:** 2026-05-01
**Target release:** Impact Vision **0.15.0**
**Source roadmap:** [`docs/roadmap-v3.md`](./roadmap-v3.md)
**Audience:** Engineering, product, agent ops

This document is the engineering-side mirror of `roadmap-v3.md`. It maps each
strategic track to concrete modules, public APIs, agent tools, tests, and
documentation deliverables, and records the decisions taken for the **0.15.0**
"v3 trust infrastructure" drop.

---

## 1. Codebase Audit (what already exists)

The 0.14.x line shipped a wide v2 surface. v3 builds on top of it. The
inventory below pins each v3 track to the modules already in tree so that we
can cleanly identify the **gaps** v3 must fill.

| v3 Track | Track focus | Already in tree | Gap closed in 0.15.0 |
|---|---|---|---|
| **1** Evidence graph & assurance | `evidence_graph.py`, `models.MetricRecord`, `data_quality.py`, `standards_registry.py`, `audit_trail.py`, `assurance.py`, `roadmap_v2.AIExtractionReview/ImmutableReportManifest` | Bulk AI-extraction **review queue** with confidence-threshold policy and batch decisions (`evidence_workflow.py`) |
| **2** Investee data collection | `investee_collection.py`, `roadmap_v2.{issue_collection_link, build_collection_tracker, build_review_queue, preview_csv_metric_import, harmonize_uploaded_metrics}`, `questionnaire_v2.py` | Wider sector starter templates, additional helpers (covered by reusing `default_metric_ids_for_sector` + new tools) |
| **3** Carbon & climate | `climate_accounting.py`, `roadmap_v2.{estimate_scope3_proxy, calculate_pcaf_financed_emissions, calculate_carbon_intensity, build_climate_coverage_dashboard}` | **Versioned emission-factor catalog loader** + sensitivity bounds + named factor revisions (`emission_factors.py`) |
| **4** Stakeholder voice | `surveys.py`, `worker_voice.py`, `tools/impact/beneficiary_feedback_tool.py`, `models.BeneficiaryFeedback` | **Lean Data survey templates**, **GDPR/PDPA consent records**, **feedback-as-evidence** linkage to claims, **feedback quality score** (`stakeholder_voice.py`) |
| **5** Causal & attribution | `counterfactual.py`, `causal.py`, `spillover.py`, `sroi.py`, `roadmap_v2.{run_contribution_analysis, score_evidence_strength, calculate_difference_in_differences, ImpactLearningLoop}` | **OPIM Principle 7 exit-impact** workflow with Principle 8 learning context (`exit_impact.py`) |
| **6** Standards interoperability | `frameworks/*`, `roadmap_v2.{build_issb_disclosure_pack, build_esrs_disclosure_pack, autofill_sfdr_pai, JURISDICTION_PROFILES, run_rule_pack_tests, monitor_regulatory_change}` | (no new module required — surfaced through tools) |
| **7** LP reporting & portal | `lp_portal.py`, `roadmap_v2.build_lp_export_bundle`, `branding.py` | **AI LP narrative** generator + **LP question/answer workspace** with citations to approved evidence (`lp_narrative.py`) |
| **8** Assurance & verification | `assurance.py`, `roadmap_v2.{run_control_checks, ExceptionRegisterEntry, AIExtractionReview}` | **Verifier workspace** (read-only evidence + comment threads + findings + signed API surface) (`verification_workspace.py`) |
| **9** AI governance & intelligence | `roadmap_v2.{harmonize_uploaded_metrics, answer_portfolio_query, AIGovernanceLog}`, `greenwashing.py`, `external_benchmarks.py` | **Greenwashing reviewer** with claim-by-claim explanations (`greenwashing_reviewer.py`) and a **portfolio NL query engine** with structured intents and approved-data citations (`portfolio_nlq.py`) |

Strategy: rather than reorganise `roadmap_v2.py` (a 992-line file already
covered by tests), 0.15.0 adds **eight new focused modules** that fill the
remaining v3 gaps and surface them through agent tools and the package
public API. The big `roadmap_v2.py` is kept as the foundational layer
those new modules build on.

---

## 2. New Modules (this drop)

All modules live under `src/openharness/impact/` and follow the existing
Pydantic-first, deterministic-offline-first conventions.

### 2.1 `emission_factors.py` (Track 3.4 / 3.8)

Versioned emission-factor catalog with provenance metadata, factor revisions,
and sensitivity bounds. Wraps `climate_accounting.DEFAULT_EMISSION_FACTORS`
in a registry-style API and adds:

- `EmissionFactorRevision` — one factor in one catalog at one version, with
  uncertainty band (`low_kg_co2e_per_unit`, `high_kg_co2e_per_unit`),
  geography, and source URL.
- `EmissionFactorCatalogV2` — registry keyed by `(scope, activity_type, unit, region, version)`.
- `default_factor_catalog()` — shipped offline catalog with EPA-, DEFRA-,
  and IEA-style snapshots (clearly labelled "offline-snapshot-2026").
- `factor_sensitivity()` — returns ±band emissions for one calculation,
  exposing the gap when ≥20% of the activity payload is unverified.
- `apply_catalog_to_inventory()` — recomputes a `GHGInventory` against a
  named catalog version (used to test "what changes if we move from
  DEFRA-2024 to DEFRA-2025?").

### 2.2 `stakeholder_voice.py` (Track 4.1 → 4.8)

Stakeholder voice as **verified evidence**, not just an analytics output.
Three sub-pieces:

1. **`LeanDataTemplate`** — 60 Decibels-style 15-minute survey template
   with `quality_of_life`, `recommendation`, `challenges`,
   `inclusion_dimension` items pre-loaded; `build_lean_data_survey()` to
   instantiate it for a sector.
2. **`ConsentRecord`** — GDPR/PDPA-compliant per-respondent consent
   capture with consent text version, lawful basis, retention period,
   and revocation timestamp.
3. **`BeneficiaryFeedbackQuality`** — quality score over completion rate,
   response depth, time-on-survey, and demographic coverage.
4. **`link_feedback_to_claim()`** — emits `EvidenceLink`s connecting
   `BeneficiaryFeedback` themes to `ImpactClaim` IDs in an existing
   `EvidenceGraph`. This is the v3 wedge: feedback isn't analytics, it's
   verifiable evidence.

### 2.3 `evidence_workflow.py` (Track 1.8)

Bulk AI-extraction review queue extending
`roadmap_v2.AIExtractionReview` from a single decision into a managed
**queue with policy**:

- `ExtractionReviewPolicy` — confidence threshold, required source-ref
  count, auto-approve cap, prompt-version pin.
- `ReviewQueue` — adds items, triages by policy, exposes pending /
  flagged / approved buckets.
- `apply_policy()` — auto-flags below threshold, requires more evidence
  if source refs missing, blocks approval if prompt version drifted.
- `bulk_decide()` — approve/reject/edit-required across many items in
  one call, every action recorded as a structured event for
  `AuditTrail.record_event`.

### 2.4 `verification_workspace.py` (Track 8.2 / 8.6)

Read-only verifier portal + findings model + API surface:

- `VerifierWorkspace` — created from an `AssurancePack`, exposes only
  the evidence the assurer needs (no fund-level PII).
- `VerificationFinding` — finding ID, severity, observation, management
  response, status, evidence refs.
- `VerificationComment` — comment thread linked to evidence node IDs.
- `submit_finding()`, `respond_to_finding()`, `resolve_comment()` — state
  transitions with timestamps and signed `AuditTrail` entries.
- `to_api_payload()` — JSON shape ready for a `/api/v1/verification/*`
  endpoint exchange (the network layer itself is left for a separate
  PR).

### 2.5 `lp_narrative.py` (Track 7.5 / 7.8)

LP-facing narrative builder. Two complementary surfaces:

- `LPNarrativeRequest` / `LPNarrativeReport` — composes a deterministic
  highlight-style narrative from an LP impact dashboard view, GIIN peer
  benchmarks (`external_benchmarks`), and an evidence manifest. No LLM
  required: produces an audit-friendly Markdown + JSON output that an
  LLM can later expand under governance controls.
- `LPQuestionWorkspace` — Q&A workspace where an LP question is matched
  to approved metric records (only `is_verified=True`) and returned with
  citations. Keeps a hashed history so question logs can be evidenced.

### 2.6 `greenwashing_reviewer.py` (Track 9.3)

Wraps the existing `greenwashing.py` engine into a per-claim reviewer
output that's actually **explainable**:

- `ClaimReviewItem` — claim text, specificity, evidence-gap reason,
  selectivity flag, adverse-impact omission, suggested follow-up.
- `review_company_claims()` — runs the engine and produces a list of
  `ClaimReviewItem`s with NESTA-style evidence-strength tags,
  recommended follow-up DD questions, and AI-governance metadata
  (`prompt_version`, `model_version`, `confidence`).

### 2.7 `portfolio_nlq.py` (Track 9.2)

Natural-language portfolio query engine **constrained to approved data**:

- `PortfolioNLQEngine` — registers `MetricRecord` corpora per
  fund/period and matches `QueryIntent` (`average`, `total`, `top_n`,
  `coverage`, `compare`).
- `ApprovedDataPolicy` — enforces `is_verified=True` filter unless the
  caller passes `include_unverified=True` and accepts an audit warning.
- `answer()` — returns `QueryAnswer` with the structured intent, the
  numeric / text answer, the records cited, and the
  `ai_governance_log_id` so every answer is reviewable.

### 2.8 `exit_impact.py` (Track 5.6)

OPIM Principle 7 exit-impact assessment workflow:

- `ExitDurabilityRisk` — risk category, likelihood, severity, mitigation
  plan, owner.
- `PostExitFollowUp` — scheduled follow-up checkpoint linked to a
  `MonitoringSchedule` for the surviving entity.
- `ExitImpactPlan` — combines `Company`, `ImpactClaim`s and contribution
  analysis into a structured plan.
- `score_exit_impact()` — rolls durability risks + follow-ups into a
  0-100 residual-impact score and a recommended OPIM evidence trail.

---

## 3. New Tools

Lightweight wrappers under `src/openharness/tools/impact/` so the agent
and the MCP server can drive each new capability:

| Tool | Module | Responsibility |
|---|---|---|
| `evidence_review_tool.py` | `evidence_workflow` | Triage / bulk decide AI extraction items |
| `stakeholder_voice_tool.py` | `stakeholder_voice` | Build Lean Data surveys, score quality, link to claims |
| `verification_workspace_tool.py` | `verification_workspace` | Open verifier workspace, submit / resolve findings |
| `lp_narrative_tool.py` | `lp_narrative` | Generate LP narrative + Q&A from approved data |
| `greenwashing_reviewer_tool.py` | `greenwashing_reviewer` | Per-claim review with evidence/specificity rationale |
| `portfolio_query_tool.py` | `portfolio_nlq` | Constrained NL query against approved metric records |
| `exit_impact_tool.py` | `exit_impact` | Score exit impact + emit follow-up schedule |
| `emission_factors_tool.py` | `emission_factors` | List/select factor revisions, run sensitivity scenarios |

These tools are exported through `openharness/tools/impact/__init__.py`
so they land in the default tool registry and the existing MCP server
auto-registers them.

---

## 4. Public API Surface

`src/openharness/impact/__init__.py` is extended with the v3 entries
above. The v2 exports stay in place; nothing is removed in 0.15.0.

---

## 5. Tests

One new `tests/test_v3_<module>.py` per module, using the existing
deterministic offline-default approach:

- `test_v3_emission_factors.py`
- `test_v3_stakeholder_voice.py`
- `test_v3_evidence_workflow.py`
- `test_v3_verification_workspace.py`
- `test_v3_lp_narrative.py`
- `test_v3_greenwashing_reviewer.py`
- `test_v3_portfolio_nlq.py`
- `test_v3_exit_impact.py`
- `test_v3_tool_wrappers.py` (registry + smoke execution for all eight tools)

Coverage targets: every new public function and every state transition
must have at least one explicit test that drives it end to end.

---

## 6. Documentation & release artifacts

- `CLAUDE.md`: refreshed project structure, v3 module summary, new
  workflow callouts, version bump.
- `README.md`: 0.15.0 banner, v3 capability matrix, new agent
  workflows.
- `CHANGELOG.md`: full 0.15.0 entry under "Added / Changed / Tests".
- `pyproject.toml`: version → `0.15.0`.

---

## 7. Out of scope for 0.15.0 (deliberately)

These items from `roadmap-v3.md` are intentionally deferred:

- Database/persistence migrations beyond the existing `storage.py`
  SQLite layer (verifier workspace persists in memory in 0.15.0).
- Full FastAPI route wiring for `/api/v1/verification/*` and `/api/v1/lp/*`
  (the data contracts ship in this release; HTTP wiring lands in
  0.15.x).
- Front-end UI for verifier workspace and LP Q&A (CLI + MCP only in
  0.15.0).
- Live external benchmark data (the offline GIIN-style snapshot is
  retained; live providers stay pluggable through the existing
  `ExternalBenchmarkProvider` Protocol).

---

## 8. Acceptance checklist

- [x] All eight modules land with public API + Pydantic models.
- [x] All eight tools land and import cleanly.
- [x] `tests/test_v3_*` files added and `pytest` passes the v3 sub-suite.
- [x] `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `pyproject.toml`
      updated.
- [x] `ruff check src tests` runs clean on the new files.
- [x] No regressions in the existing impact tool surface (sanity
      smoke through the MCP wrapper).
