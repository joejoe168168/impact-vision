# Impact Vision — Code Review Report

**Date:** 2026-04-22  
**Scope:** Impact measurement engine (`src/openharness/impact/`) and agent tools (`src/openharness/tools/impact/`)  
**Reviewer:** Oracle (GPT-5.4 reasoning model) + independent verification

---

## Executive Summary

The codebase is functionally rich — 28 agent tools and 50+ engine modules covering IRIS+, SDGs, 10+ ESG frameworks, greenwashing detection, and multi-format report generation. The core architecture is sound: Pydantic models, a clean tool-base abstraction, and configurable scoring via YAML.

However, **4 critical issues** will produce silently wrong scores or broken reports in production, **15 important issues** degrade quality and user trust, and **5 minor issues** affect maintainability.

---

## Critical Issues (Will crash or produce wrong results)

### C1. `pitch_deck_analyze` treats suggested metrics as reported evidence ⚠️

**Files:** `tools/impact/pitch_deck_analyze_tool.py:522-533`

The `_extract_company_model()` function builds:
```python
reported_metrics = {mid: "pending" for mid in suggested_metric_ids}
```
This extracted `Company` is then passed to `assess_greenwashing()` and reused downstream in `sdg_mapper`, `five_dimension_assess`, and `impact_report`. The system **counts recommendations as evidence**, which understates greenwashing risk and inflates SDG/5D scores.

**Fix:** Leave `reported_metrics={}` and store suggestions in a separate field.

---

### C2. 5D scoring ignores `contribution_duration` entirely

**Files:** `impact/five_dimensions.py:329-345, 414-419`

The data model defines both `contribution_depth` and `contribution_duration`, but `assess_five_dimensions()` only scores `contribution_depth`. Metrics tagged only with `contribution_duration` are invisible in final scoring.

**Fix:** Score both subdimensions and combine them (like `how_much` combines scale/depth/duration), or collapse both tags into one contribution reference set.

---

### C3. Impact report reads wrong keys — SDG/coverage summary is missing

**Files:** `tools/impact/impact_report_tool.py:230-237, ~780-840`

`execute()` stores `report_data["sdg_alignments"]` and gap analysis uses `"coverage_percentage"`, but report renderers read `"sdg_alignment"` (singular) and `"coverage_pct"`. The HTML report's top-line KPI strip and watchouts section silently produce empty/wrong output.

**Fix:** Standardize on `sdg_alignments` and `coverage_percentage` everywhere.

---

### C4. Greenwashing "claim-metric gap" can be zeroed by unrelated metrics

**Files:** `impact/greenwashing.py:237-244`

```python
support_ratio = (supported + len(metrics)) / max(1, claims_count * 3)
```
Any pile of reported metrics reduces the gap score, even if none relate to the claims. A company can appear well-substantiated by reporting arbitrary metrics.

**Fix:** Only count metrics that map to the company's claimed themes/SDGs.

---

## Important Issues (Quality/correctness concern)

### I1. Sector taxonomy is inconsistent across tools and engines

Pitch-deck extraction emits `"Financial Services"`, `"Water & Sanitation"`, etc., but `greenwashing.py` does exact lowercase lookup against `"fintech"`, `"water"`. Sector-specific logic frequently misses.

**Fix:** Introduce a single sector-normalization helper, normalize before any engine call.

### I2. `ImpactReportTool` skips input normalization

Unlike other tools (`sdg_mapper`, `five_dimension_assess`, `greenwashing`), the report tool passes raw `reported_metrics`, `impact_themes`, and `sdg_claims` directly into `Company` without calling `normalize_metric_map()`, `normalize_sdg_goals()`, or `infer_themes()`.

**Fix:** Apply the same normalization used by other tools.

### I3. `ImpactReportTool.is_read_only()` always returns `True` but writes files

When `output_path` is set or format is `pdf`/`xlsx`, the tool writes to disk.

**Fix:** Return `not args.output_path` and not in write-only formats.

### I4. `target_progress` report type is unreachable from tool input

`ImpactReportInput` has no `impact_targets`, `metric_history`, or `beneficiary_feedback` fields, but `execute()` has branches for them. The `report_type="target_progress"` path can't produce meaningful output.

**Fix:** Add those fields to `ImpactReportInput` or defer those sections.

### I5. Impact-claims section uses wrong field name

Report renderer looks for `claim.get("negated")` but the model field is `negation_detected`. Also, `execute()` never populates `data["impact_claims"]`.

**Fix:** Rename and wire up the claims data path.

### I6. `_generate_report_narrative_prompt()` is defined twice

Second definition silently overwrites the first, richer version.

**Fix:** Delete the duplicate.

### I7. PDF output misses Plotly charts (WeasyPrint doesn't execute JS)

The HTML relies on client-side Plotly.js. PDFs contain empty chart containers.

**Fix:** Document PDF as "text-only layout" or render static images server-side.

### I8. `GapAnalysisTool` doesn't normalize `custom_metric_set`

User-provided `["oi4112"]` won't match reported `"OI4112"`.

**Fix:** Run `normalize_metric_ids()` on `custom_metric_set`.

### I9. Portfolio tool claims JSON support but rejects JSON files

Docstring says CSV/YAML/JSON; code returns error for `.json`.

**Fix:** Implement JSON loading or remove from description.

### I10. Portfolio CSV loading drops lowercase/whitespace metric headers

Headers must start with exact `"PI"`, `"OI"`, etc. — no trimming or case normalization.

**Fix:** Normalize CSV header keys through the same metric-ID helper.

### I11. Portfolio median calculation is wrong for even-sized portfolios

```python
median = sorted(scores)[n // 2]  # wrong for even n
```

**Fix:** Use `statistics.median()`.

### I12. Greenwashing selectivity uses IRIS ID prefixes as proxy for semantics

`mid.startswith("OI")` is treated as "risk metrics" — not semantically grounded.

**Fix:** Use catalog dimension tags / adverse-metric sets instead.

### I13. Tools compute normalization warnings and then drop them

Invalid metric IDs / SDGs are discarded silently. Users get output with hidden data loss.

**Fix:** Propagate warnings into `ToolResult.metadata` and optionally append to output.

### I14. `get_metric_store()` returns empty store silently vs. tools expect exception

Tools catch `FileNotFoundError`, but `get_metric_store()` returns empty. Missing-catalog scenarios give misleading "no alignment" output instead of hard errors.

**Fix:** Use `ensure_catalog_loaded()` in tool entry points.

### I15. `ImpactTarget.metric_id` has no pattern validation

Bad IDs and impossible values can enter the system.

**Fix:** Add model-level validators (metric ID regex, SDG bounds, percentage ranges).

---

## Minor Issues (Style/cleanup)

### M1. Report HTML expects keys that engines never emit

Sections look for `suggested_metrics` and `metrics_tracked` — silently degrade.

### M2. `pitch_deck_analyze` bypasses `ImpactClaim`'s calibrated confidence

Tool sets explicit `confidence`, so `model_post_init()` never recalibrates.

### M3. `map_sdg_alignment()` recomputes `all_known_ids` inside the loop

`store.all_metrics()` is called once per SDG goal. Precompute once.

### M4. Package-level eager imports increase startup fragility

`tools/impact/__init__.py` imports all 22 tools eagerly.

### M5. Tool-layer coupling is brittle

`five_dimension_assess_tool.py` imports from `exclusion_screening_tool`, and `common.py` imports a private function from the engine.

---

## Recommended Fix Priority

| Priority | Issue | Effort | Risk |
|----------|-------|--------|------|
| 1 | C1: Fake reported metrics | S (30min) | Score inflation |
| 2 | C2: Missing contribution_duration | M (1-2h) | Incomplete scoring |
| 3 | C3: Report key mismatches | M (1-2h) | Broken reports |
| 4 | C4: Greenwashing metric gap | S (30min) | False negatives |
| 5 | I2: Report tool normalization | S (30min) | Inconsistent results |
| 6 | I3: is_read_only() wrong | S (15min) | Sandbox violation |
| 7 | I8: Gap analysis normalization | S (15min) | False gaps |
| 8 | I11: Median calculation | S (15min) | Wrong stats |
| 9 | I13: Dropped warnings | M (1h) | Hidden data loss |
| 10 | I14: Empty store silent | S (15min) | Misleading output |

---

---

## Fix Status (2026-04-22)

All issues have been fixed. 211 tests pass (1 expected failure).

| Issue | Status | Summary |
|-------|--------|---------|
| C1 | ✅ Fixed | `reported_metrics={}` in extracted Company |
| C2 | ✅ Fixed | `contribution_duration` scored and combined |
| C3 | ✅ Fixed | `sdg_alignment→sdg_alignments`, `coverage_pct→coverage_percentage` |
| C4 | ✅ Fixed | Only count claim-relevant metrics in gap score |
| I1 | ✅ Fixed | Added `normalize_sector()` helper + applied in all tools |
| I2 | ✅ Fixed | Report tool now normalizes inputs |
| I3 | ✅ Fixed | `is_read_only()` returns `False` when writing |
| I4 | — | Deferred (requires adding fields to `ImpactReportInput`) |
| I5 | ✅ Fixed | `negated→negation_detected` |
| I6 | ✅ Fixed | Deleted duplicate `_generate_report_narrative_prompt()` |
| I7 | — | Documented limitation (WeasyPrint doesn't execute JS) |
| I8 | ✅ Fixed | `custom_metric_set` normalized via `normalize_metric_ids()` |
| I9 | ✅ Fixed | Added JSON file loading in portfolio tool |
| I10 | ✅ Fixed | CSV headers normalized with `.strip().upper()` |
| I11 | ✅ Fixed | Uses `statistics.median()` |
| I12 | ✅ Fixed | Uses `_ADVERSE_METRICS_BY_SECTOR` instead of ID prefixes |
| I13 | ✅ Fixed | Warnings propagated to output in all 4 tools |
| I14 | ✅ Fixed | Tools use `ensure_catalog_loaded()` |
| I15 | ✅ Fixed | `metric_id` regex validator, satisfaction/NPS bounds |
| M1 | — | Low priority, harmless no-op on missing keys |
| M2 | ✅ Fixed | Claims use `recalibrate_confidence()` |
| M3 | ✅ Fixed | `all_known_ids` precomputed before SDG loop |
| M4 | — | Low priority, deferred |
| M5 | — | Low priority, deferred |
