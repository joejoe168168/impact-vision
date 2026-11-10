# Impact Vision — development plan and technical specification

Companion to [`IMPROVEMENTS.md`](IMPROVEMENTS.md) (the review of 0.19.1). Item IDs are the ones
used there: **R** regulations and frameworks, **U** report UX, **C** content quality, **F** new
features.

- **Part 1** — as-built notes for what is already implemented on `claude-improvements-20261110`.
- **Part 2** — a specification for every item not yet implemented.
- **Part 3** — the phased roadmap: order of work and dependencies.
- **Part 4** — status log, updated whenever work stops.

Written 2026-11-10 against `7db47e2`.

## Rules that apply to every item

These come from `CLAUDE.md` and the roadmaps. Each spec below assumes them and does not repeat them.

1. **Extend or wrap, never fork.** New behaviour goes into the module that owns the concept, or a
   small new module beside it.
2. **No regulatory date, weight, threshold or benchmark in Python.** It goes into YAML under `data/`
   with `as_of` and `source_url`. Scoring parameters go into `data/methodology/v1.yaml` or `v2.yaml`;
   any file that can change a score must be listed in `methodology.HASHED_FILES`.
3. **Every score responds to the evidence it claims to measure.** A scoring change ships with a
   perturbation test: change the evidence, the score moves; change only the wording, it does not.
4. **Held-out results must not regress.** `scripts/run_heldout_eval.py` and
   `tests/test_v8_heldout_eval.py` (tolerance 0.02 against `tests/golden/heldout/baseline.json`).
   When a change is meant to move a held-out number, update the baseline in the same commit and say
   so in the commit message.
5. **A scoring change bumps the methodology version** (`v2.yaml` `version`, with a dated comment)
   and is listed under "Breaking" or "Changed" in `CHANGELOG.md`.
6. **Generated sentences are translated.** A new English sentence the engine writes gets a pattern
   in `scripts/build_phrasebook.py`; a new label gets keys in all three tables of
   `report_templates/design/strings.py`. `tests/test_i18n_consistency.py` enforces parity.
7. **Docs stay in step.** New tool, CLI command or framework module: README tables (README stays at
   or below 850 lines), `CLAUDE.md` tree, `python scripts/build_tool_reference.py`.
8. **Checks before each commit:** `pytest tests/`, `uvx "ruff>=0.15,<0.16" check src/`, the CI mypy
   list, `scripts/check_knowledge.py`, `scripts/build_tool_reference.py --check`.

Effort: **S** under a day, **M** 1–3 days, **L** a week or more.

---

# Part 1 — As built

## C1. Negated or planned evidence is not evidence — `483b614`

- **What shipped.** A cue that is denied ("we have no control group yet", "has not been audited") or
  only planned ("we plan to run an RCT") no longer earns evidence credit.
- **Design.** `impact/negation.py` is a clause-level rule, not a parser. `asserted(text, start, end)`
  looks 50 characters back and 60 forward within the same clause. A negator or plan marker before
  the match, or a narrow "has not been established / is pending" after it, makes the match
  unasserted. A comma breaks the clause only when a conjunction follows, so "no RCT, control group
  or baseline" stays negated while "no debt, and an RCT showed …" does not. Chinese negators bind
  only when they sit within six characters before the match. When unsure it keeps the match.
- **Used by.** `extractors/regex_extractor.evidence_signals`, `negative_impacts.assess_negative_impacts`
  (control phrases), `greenwashing._score_verification` and `_count_controls`.
- **Tests.** `tests/test_negated_evidence.py` (18): 13 sentence cases, signal extraction, an
  end-to-end perturbation (denied control group earns no deadweight netting), verification risk,
  negative-impact controls.
- **Follow-ups.** `tools/impact/common.keyword_match_with_context` is an older negation helper used
  by exclusion screening; C7 should make it call `negation.asserts_phrase` so there is one rule.
  DD-checklist coverage (`dd_checklist.py:260-310`) still counts keywords without negation.

## R1. HKEX ESG Code gap check — `d3849db`

- **What shipped.** `impact-vision framework hkex-esg <report> [--issuer largecap|main_board|gem]
  [--lang en|zh-HK] [--json]`; `framework_assess` with `framework="hkex_esg"` (`list`, `assess`);
  `hkfrs_s1` exposed the same way; registry rows `HKEX_ESG_CODE` and `HKFRS_S1`.
- **Design.** `data/regulatory/hkex_esg_code.yaml` holds 65 scored provisions plus one informational
  row: Part B paras 13–15 (7 rows), Part C aspects A1–A3 and B1–B8 with every KPI (45 rows), Part D
  by IFRS S2 pillar (13 rows). Each row has `id`, `part`, `ref`, `title`, `zh`, `cues`. Status per
  provision: *addressed* (two cues, or one cue plus the KPI code cited), *partly*, *explained*,
  *gap*. "Not applicable / not material" counts as *explained* only where the basis is
  comply-or-explain, so a mandatory item cannot be explained away. Part D's basis comes from the
  `phasing` block by issuer type; `mandatory_all: true` marks Scope 1 and 2. A statement of ISSB
  compliance is reported (`issb_statement`) and never taken as proof.
- **Files.** `frameworks/hkex_esg.py`, the YAML, `cli.py`, `tools/impact/framework_tool.py`
  (`FRAMEWORK_CATALOG`, also the source of `framework list` now), `knowledge.KNOWLEDGE_FILES`.
- **Tests.** `tests/test_hkex_esg_code.py` (9).
- **Follow-ups.** Cue lists are heuristics (`cue_status: illustrative`); a run against 5–10 real
  HKEX ESG reports would tune them. Part D paragraph numbers beyond 19 and 37–40 need the Appendix
  C2 text. See R9 (HKFRS S2) and F9 (one HK command).

## R2. Knowledge refresh — `ae0a423` (and registry rows in `d3849db`)

- **What shipped.** ISSB nature Exposure Draft published, comments to 2027-02-19; SFDR 2.0
  Parliament mandate and trilogue, with the taxonomy-alignment floors recorded as
  `taxonomy_alignment_floor`; PCAF registry row at `2025-12`; legal basis and source on the
  `EU-SFDR` and `HK-HKEX-ESG` packs; a 2028-01-01 watchlist row for HKFRS-based reporting.
- **Design.** Only facts checked against a source were changed (IMPROVEMENTS §1.3). The alignment
  floors are recorded, not applied by the classifiers, because they are an open trilogue point.
- **Follow-ups.** Whether the first trilogue took place is unverified. R3, R5 and R8 finish the job.

## U1. Data exports carry the headline — `53008ed`

- **What shipped.** Workbook sheets *Expected impact*, *Impact factors*, *Evidence plan*, *Negative
  impacts*; Summary rows for the gate, top plan step, P50 and range; matching CSV rows plus the
  contribution split; `exports.CSV_ENCODING = "utf-8-sig"`; counts no longer formatted `0.0`; AI
  provenance split into two sheets.
- **Design.** `exports._decision_rows(data)` builds the tidy rows once; the CSV and the *All
  figures* sheet share them. `_table` gives whole numbers `#,##0` whatever the column format.
- **Tests.** `tests/test_exports.py` (+3).
- **Follow-ups.** Headers are English in every language (part of U3). No print setup on sheets (U9).

## U2. Dark theme prints dark on white — `edf8c81`

- **What shipped.** A final `@media print` block in `design/tokens.css` resets every colour token
  the dark theme changes; `pdf._chromium` asks for the light colour scheme.
- **Design.** In `tokens.css` because the IC memo and DD report share that sheet. The block must
  stay last to win over both dark selectors.
- **Tests.** A CSS test that fails if a dark token is not reset; a Chromium test in `tests/visual`.

## C2. Methodology stamp — `468da25`

- **What shipped.** `methodology.HASHED_FILES` adds `methodology/v2.yaml`,
  `methodology/contribution_rubric.yaml` and `negative_impacts.yaml`; the stamp gains
  `expected_impact_version`; `stamp_text()` renders one line used by the report footer (three
  languages), the memo and its Markdown.
- **Design.** `methodology_version` keeps meaning the v1 file so existing consumers do not break.
  The new key is absent when `IMPACT_VISION_METHODOLOGY_VERSION=1`.
- **Tests.** `tests/test_v7_wave5_methodology.py` (+2), including "edit each file, the hash moves".
- **Follow-ups.** Add `exclusion_criteria.yaml` to the list with C7. `demo/` needs regenerating.

## C3, F1 (first half), C4, F5 (part). IC memo — `44c71d1`

- **What shipped.** One verdict in Markdown, Word, PowerPoint and HTML; suggested investment
  conditions in section 7; the bundled example thesis labelled; `assess --thesis`.
- **Design.** Each evidence-plan item carries a `kind`. `expected_impact.suggest_conditions(block)`
  maps kinds through `v2.yaml` `conditions.kinds` to a type (condition precedent, covenant,
  reporting) and a timing, and adds up to two of the company's stated targets as covenants. Binding
  `TargetCondition`s passed by a caller take precedence; nothing is suggested when the gate is
  *fails thesis*. `FundThesis.is_example` is set when the loader falls through to
  `fund_thesis.example.yaml`. An explicit thesis path that does not exist raises.
- **Tests.** `tests/test_ic_memo_conditions.py` (8).
- **Follow-ups.** F1 second half (conditions feed annual monitoring); the memo is still English (U3).

## C5 (part). Parsing — `09db1ba`

- **What shipped.** Goals are not reach (`_GOAL_BEFORE`); the ask is read from the whole document;
  prefixed dollar signs resolve to their own currency and fall back to `fx.StaticFXRateProvider`;
  a running total of tonnes sets `Figure.cumulative` and Duration becomes 1 with reason
  `why_cumulative`.
- **Tests.** `tests/test_outcome_parsing.py` (16).
- **Follow-ups.** C5b below.

## U3 (part). Chinese reports — `33f95ed`

- **What shipped.** Claim types and target statuses through the string table (`_label`), corrected
  language note, translated logo alt text, mainland wording in the zh-CN phrasebook (`CN_VOCAB`).
- **Tests.** `tests/test_i18n_consistency.py` (6).
- **Follow-ups.** U3b below.

## C6 (part), C15 (part). Conflicting figures — `7958cb4`

- **What shipped.** `impact/consistency.py`: `find_conflicts(claims)` keeps every value per IRIS+
  metric and reports pairs more than `consistency.tolerance` (10 %) apart; figures that name
  different years are growth, not a conflict. `report_data["figure_conflicts"]`, a ledger block in
  the report, a leading `reconcile` plan item, a CSV row. `bayes.fold` materialises its stream.
- **Tests.** `tests/test_figure_conflicts.py` (7).
- **Follow-ups.** C6b plausibility checks.

## Second pass and parallel branches (2026-11-10)

Landed after this spec was first written: C7 `1ebba38`, C11 part 1 `58b2949`, C6b `3adde10`, then four
parallel branches (`iv-par-1..4`) merged without conflicts, then three fix-up commits for the test
failures the merge exposed (`1be5120`, `6fda138`, `3d8bce1`).

- **U3b zh-HK pack** — `9196e30`, `11d2caf`, `af641dd`. The IC memo and DD report chrome is localised by
  a post-render pass, and a Traditional Chinese DD checklist file is used with `--lang zh-HK`.
  **Not done:** some English strings remain in both documents; the `impact/i18n.py` helpers and their
  YAML may still be unused.
- **C8 readiness gate** — `5e2b3f6`, fix `6fda138`. `_gate` can return *Ready for IC*; core-metric
  completeness is a `note`, not a condition. The pig-farm sample deck is now Ready for IC. Fix-up: the
  ready verdict keeps the evidence `plan` when it has items (the core-metric reporting follow-up), so
  exports keep their "Evidence plan" rows and `pipeline` uses the first plan action as the
  recommendation. **Not done:** held-out eval / baseline not revisited for the new verdicts;
  `v2.yaml` is still `2.1.0` (rule 5 asks for a bump); the note is shown on the one-pager but not
  checked on the report's verdict card or the IC memo.
- **U4 share links** — `22f4751`. Read-only notice, view audit, per-link revocation. **Not done:** the
  UI does not reuse one link per audience / language; the banner and error page are not translated;
  `web/chat_ui.py` not updated.
- **F2 compare** — `631da75`. `impact-vision compare`: deals side by side, no composite, range
  overlap stated. **Not done:** `decision_workflow.compare_deals` still uses the old v1 composite; the
  per-US$1m figure is often blank.
- **F3 IC one-pager** — `0e81e7f`, fix `3d8bce1`. `report_templates/onepager.py`, written next to the
  memo and linked in the gallery as "IC one-pager". Fix-up: on screen the page is fluid
  (`max-width: 100%`, single column below 210mm) so it no longer overflows a 390px viewport; print
  keeps `@page { size: A4 }` and a 210mm × 297mm page. **Not done:** strings are inline in the module
  rather than shared templates; no Chromium test that the printed PDF is exactly one page.
- **C5b parsing** — `072f1ba`. Reach by stakeholder, effect sizes ("0.21 SD") not read as percentages,
  spaced thousands ("12 000"), Chinese numerals. **Not done:** `other_reach` in the factor basis line;
  the `regex_extractor._NUMBER_UNIT` side; held-out baseline update.
- **R6 / R7 packs** — `cad95fb`, `abf0e3d`. Sourced `updates.yaml` rows for GRI 101–103, SBTi
  Net-Zero V2 and EU Taxonomy 2026/73 (`frameworks/pack_updates.py`, the 25th framework module);
  the taxonomy and SBTi checks cite them. **Not done:** `frameworks/gri.py` still hard-codes the 2016
  list; SBTi still applies V1 thresholds; no standards-registry rows; not exposed through
  `framework_tool`.

---

# Part 2 — Specifications for the remaining items

## 2.1 Content quality

### C7. Exclusion screening inside `assess`

- **Goal.** A deck that describes an excluded activity fails the thesis from the CLI path too, with
  the sentence that triggered it. Today `exclusion_criteria.yaml` is read only by the agent tool.
- **Design.** Move the matching into a library function, `impact/exclusions.py`:
  `screen_exclusions(text, *, severities=("mandatory",)) -> dict` returning
  `{"passed": bool, "hits": [{"category", "label", "severity", "keyword", "sentence", "sfdr_pai"}]}`.
  It splits the text into sentences and uses `negation.asserts_phrase` with word boundaries, so
  "we do not finance coal mining" and "our no-tobacco policy" do not fire. The agent tool calls the
  same function (keeps its output). `pipeline.assess_document` calls it on the scoring text, stores
  `report_data["exclusions"]` and passes `exclusion_pass` to `evaluate_deal_against_thesis`; the v2
  gate already turns a failed exclusion check into *fails thesis* (`expected_impact._gate`).
  Only `mandatory` severity fails the gate; `common` and `watch` hits are listed as questions.
- **Files.** New `impact/exclusions.py`; `tools/impact/exclusion_screening_tool.py`; `pipeline.py`;
  `expected_impact._gate` (reason text names the category); `decision_report.py` and the template
  (verdict reasons already render); `exports._decision_rows`.
- **Data.** Add `as_of`, `source`, `source_url` to `exclusion_criteria.yaml`; add it to
  `methodology.HASHED_FILES` and `knowledge.KNOWLEDGE_FILES`.
- **CLI / API.** None new. `summary()` gains `exclusions`.
- **Report UX.** Verdict reason "Exclusion: Fossil fuel exposure — “…sentence…”". A "watch" list
  in the risks section.
- **Tests.** A solar deck plus "we also operate a coal mining subsidiary" → gate *fails thesis*,
  reason quotes the sentence. "We do not finance coal mining" → unchanged. All golden and held-out
  decks unchanged (run the 40 decks; any new hit is reviewed by hand before the baseline moves).
  Perturbation: removing the sentence restores the gate.
- **Risks.** False positives from single words ("petroleum jelly", "tobacco-free"). Mitigation:
  sentence-level match with negation, mandatory only, and a held-out check before commit.
- **Effort.** S–M.

### C11. One NESTA ladder

- **Goal.** The DD checklist and the extractor grade evidence on the same scale as `models.py` and
  `v2.yaml`.
- **Design.** `dd_checklist._assess_evidence_level` still rates an RCT as 5 and "kpi / tracked" as 3.
  Replace its table with a call to the shared mapping: signals from `evidence_signals(snippet)`
  → level via one function `extractors.base.level_for_signals(signals, has_number)`. In that
  function: controlled evaluation = 3; independent replication or evaluation by a named external
  evaluator on top of a controlled design = 4; third-party verification alone does **not** raise the
  level (it sets `verified`, which `v2.yaml` already rewards through `verified_bonus`); a bare number
  = 2 only when the sentence shows change (a `_DEPTH_RE` hit or a baseline cue), else 1.
- **Files.** `extractors/base.py`, `dd_checklist.py`, `expected_impact._sentence_level` (use the same
  function).
- **Data.** Level definitions move to `v2.yaml` `evidence_levels` (ids and one-line meanings), which
  the report's methodology appendix prints.
- **Tests.** "RCT" snippet → 3 in both paths. "We have 42,000 customers" → 1. "Costs fell 35 % against
  baseline" → 2. "Verified by KPMG" alone → level unchanged, `verified` true. Held-out: evidence
  quality scores will move; record before and after for the 40 decks in the commit message.
- **Risks.** This lowers evidence quality for decks that relied on counts and verification. It is
  the intended reading of the scale, but it is a methodology change: bump `v2.yaml` to 2.2.0.
- **Effort.** S–M.

### C6b. Plausibility checks

- **Goal.** Flag figures that cannot be right before they drive the headline.
- **Design.** `consistency.plausibility_flags(inputs, geography, ask_usd) -> list[dict]`, each flag
  `{kind, figure, limit, sentence}`:
  1. `reach_exceeds_population` — reach above the population of the stated country.
  2. `percentage_over_100` — a depth figure above 100 % (now capped silently at
     `expected_impact.py:217`; keep the cap, add the flag).
  3. `tonnes_per_usd` — tCO2e per US$1m raised above a cap.
  Each flag adds a plan item (`kind: "plausibility"`, condition precedent) and widens the factor's
  sigma by a YAML multiplier, so an implausible figure cannot produce a narrow range.
- **Files.** `consistency.py`, `expected_impact.py` (`read_outcomes` returns raw depth before the
  cap; `_factors` applies the multiplier), `pipeline.py`, `decision_report.py` (ledger block shared
  with conflicts), `build_phrasebook.py`.
- **Data.** New `data/population.yaml` (country → population, `as_of`, `source_url` UN WPP), covered
  by the freshness gate. `v2.yaml` `plausibility: {max_tco2e_per_usd_1m, sigma_multiplier}`.
- **Report UX.** Under "Figures that disagree", a second list "Figures to check".
- **Tests.** "120 million people in Kenya" → flag and plan item; "150 % increase" → flag, depth still
  capped; a normal deck → none; spread with the flag > spread without.
- **Risks.** Regional geographies ("Sub-Saharan Africa") have no single population: skip silently.
- **Effort.** M.

### C5b. Remaining parsing errors

- **Goal.** Reach, depth and thousands separators read the way a person would.
- **Design.**
  1. *Reach by stakeholder, not by size.* `read_outcomes` keeps the largest figure **per noun**, then
     picks the headline by a noun priority from YAML (`v2.yaml` `reach_noun_priority`: beneficiary
     nouns such as households, patients, farmers, students before generic nouns such as users,
     members, customers; "registered", "downloads", "visits" contexts are skipped). Other nouns are
     kept in `inputs.other_reach` and shown in the factor's basis line.
  2. *Effect sizes.* "0.21 SD" is stored as `Figure(effect_size=0.21)`, not a depth of 21 %.
     Conversion to a depth uses one documented factor in `v2.yaml`
     (`effect_size_to_depth`), labelled as a conversion in the factor's basis.
  3. *Numbers.* `_NUM` gains a left boundary `(?<![\d.,])` so a year does not bleed in, and accepts
     a thin or regular space as a thousands separator only in the `ddd ddd` shape.
  4. *Chinese numerals.* `3.2萬`, `1.5 億`, `三千` with unit characters (roadmap known miss).
- **Files.** `expected_impact.py`; `extractors/regex_extractor._NUMBER_UNIT` for (3) and (4).
- **Tests.** "5,000 farmers … 900,000 users registered" → reach 5,000 farmers. "0.21 SD" → not 21 %.
  "12 000 households" → 12,000. "Cohort of 2023 120 students" → 120. "服務 3.2 萬名長者" → 32,000.
  Held-out Chinese fact recall should rise (huanxin, anxin, xuehai); update the baseline.
- **Risks.** Noun priority can pick a smaller, truer figure and move P50 down on real decks. That is
  the point; list the affected held-out decks in the commit.
- **Effort.** M.

### C15b. Two remaining bugs

- **Goal.** Portfolio totals and actual results are computed on the right basis.
- **Design.**
  1. `company_record.lp_report_view` sums P50s across companies and stakeholder types. Group by
     `(kind, stakeholder)` and report each group; show a single total only for tCO2e. Sum of P50s is
     labelled "sum of central estimates", with no pooled range.
  2. `annual_monitoring` re-scores actuals through the forward-looking model. Add
     `expected_impact.assess_actual_impact(...)`: probability of success = 1, deadweight netted only
     when the result has a comparison, depth from the reported value, sigma from the evidence level
     of the actual. Same output shape, `"basis": "actual"`.
- **Files.** `company_record.py`, `annual_monitoring.py`, `expected_impact.py`,
  `design/templates/lp_report.html.j2`.
- **Tests.** Two companies (households, tCO2e) → two rows, no cross-type total. An actual equal to
  the expected reach with the same evidence → actual P50 ≥ expected P50 (no success discount).
- **Risks.** Stored company records hold results computed the old way; recompute on read and keep
  the stored number as `legacy_p50`.
- **Effort.** M.

### C10. Weights still in Python

- **Goal.** Every number that can change a score lives in versioned YAML and in the hash.
- **Design.** Move, with no change in value: `expected_impact.py:518` (60, ≥ 2) →
  `v2.yaml gate.fails.claim_risk_min / flagged_min`; `greenwashing_reviewer._SPECIFICITY_W`,
  `_EVIDENCE_W`, materiality 1.0 / 0.8 / 0.6 → `v2.yaml greenwashing_claims`;
  `negative_impacts.MATERIAL_AT` → `negative_impacts.yaml material_at`;
  `greenwashing.py` specificity base and steps, verification base and steps, recommendation cut-off
  → `v1.yaml greenwashing.specificity / verification / recommend_above`;
  `contribution_split.py:103` bonuses → `contribution_rubric.yaml`;
  `decision_workflow.compare_deals` composite → removed by F2.
- **Tests.** For each: edit the YAML value in a temp copy → the output and `config_hash` change.
  A guard test greps the listed functions for numeric literals other than 0, 1 and 100.
  Golden and held-out unchanged (values are the same).
- **Risks.** Low. Pure move; do it before C8 so the gate change is a YAML diff.
- **Effort.** M.

### C8. A verdict that discriminates

- **Goal.** "Ready" is reachable for a deck with good evidence. Today 0 of 40 decks are ready; the
  two labelled ready are blocked only by core-metric coverage.
- **Design.** Completeness leaves the gate. `gate.ready` keeps `min_evidence_quality` and
  `require_quantified_outcome` and gains two conditions that are about evidence, not disclosure:
  `min_headline_level: 2` (the headline figure shows change) and
  `max_spread: 8` (P90 / P10; a range that wide is not a basis for a decision). Low completeness
  becomes a **note** on a ready verdict ("ready, with 6 % of the core metric set reported") and
  stays in the evidence plan as a reporting item. `heldout_eval.evaluate` reports per-class recall
  and the majority-class baseline; the test asserts recall for *ready* > 0.
- **Files.** `expected_impact._gate`, `v2.yaml`, `heldout_eval.py`, `scripts/run_heldout_eval.py`,
  `decision_report.py` (verdict note), `ic_memo.py`.
- **Data.** `v2.yaml gate.ready`: remove `min_data_completeness` from the conditions, add the two
  above, add `completeness_note_below: 40`. Version 2.2.0 (with C11).
- **Report UX.** Verdict card gains an optional note line under the reasons.
- **Tests.** nilegrid_eg and edupath_in → ready. A deck with one unverified count and no depth →
  evidence plan. Perturbation: adding core metrics to a weak-evidence deck does not make it ready.
  Baseline updated; verdict accuracy and per-class recall recorded in the commit.
- **Risks.** More "ready" verdicts while every parameter is still `illustrative`. Mitigation: the
  verdict card keeps the "illustrative methodology" label; the calibration study (F10) sets the
  final thresholds.
- **Effort.** M. Depends on C10 and C11.

### C9. The plan follows the uncertainty; "what would make this ready"

- **Goal.** The evidence plan addresses the factor that drives most of the range, and says which
  item would change the verdict.
- **Design.** `_evidence_plan` iterates the outcome's `drivers` (variance shares). For each driver
  above a share threshold it emits one item from a table in `v2.yaml` (`plan.by_factor`):
  Reach → verify reach; Depth → measure depth; Duration → "show how long the benefit lasts
  (retention, repeat use, product life)"; Attribution → "show what part others played
  (co-funders, partners)"; Deadweight → comparison group. Each item carries `share`.
  `gate_flip(block, item) -> state` re-runs `_gate` with that input upgraded (level → 3, depth
  measured, factor sigma halved) and returns the resulting state; items that flip to ready get
  `"unlocks": "ready"`.
- **Files.** `expected_impact.py`, `v2.yaml`, `decision_report._mind`, template, `ic_memo._impact_*`,
  `build_phrasebook.py`, `suggest_conditions` (new kinds `duration`, `attribution`).
- **Report UX.** In "What would change our mind": a small tag "would make this ready for IC" and the
  share of uncertainty per item.
- **Tests.** Pig-farm deck (Duration 57 %) → first item is about duration. For a deck one step from
  ready, exactly the unlocking item is tagged. Plan length still ≤ 4.
- **Risks.** `_gate` must be pure for re-running; it is. Monte Carlo is not re-run (the flip uses
  the analytic sigma), so the tag is approximate — say "likely".
- **Effort.** M. Depends on C8.

### F6. DD questions ranked by what moves the verdict

- **Goal.** The DD report opens with the questions tied to the gate reasons and the top drivers.
- **Design.** `data/dd_checklist.yaml` questions gain an optional `addresses:` list of plan kinds
  (`verify_reach`, `measure_depth`, `comparison`, `duration`, `attribution`, `negative_control`,
  `core_metrics`). `dd_checklist.select_questions_for_document(..., plan=None)` sorts by: addresses
  an open plan kind (in plan order) → static priority → phase. Tag the ~30 questions where the link
  is clear; untagged questions keep today's order.
- **Files.** `dd_checklist.py`, `data/dd_checklist.yaml`, `report_templates/dd_report_html.py`
  (`_question_sort_key`, a "why this question" line), `pipeline.py`.
- **Tests.** Solar deck: the first question addresses the first plan item. With no plan, order is
  unchanged (snapshot of ids). The 122-question count test still passes.
- **Effort.** M. Depends on C9 for the full kind list.

### C12. Stale evidence

- **Goal.** A 2019 figure in a 2026 deck is marked as old.
- **Design.** `ImpactClaim` gains `period_year: int | None` (kept from `ExtractedClaim.metric_year`
  in `to_impact_claims`). `expected_impact` adds a flag when the headline figure's year is more than
  `v2.yaml staleness.max_age_years` (3) before the document year (latest year mentioned, else the
  run date), widens sigma and adds a plan item "give the latest figure".
- **Files.** `models.py`, `extractors/base.py`, `expected_impact.py`, `decision_report.py` (ledger
  column "Period").
- **Tests.** "In 2019 we reached 40,000 households" in a deck dated 2026 → flag; with 2025 → none.
- **Risks.** Year extraction mistakes ("ISO 14001:2015"); only accept a year adjacent to the figure
  or introduced by "in / during / FY".
- **Effort.** M.

### C13. SDG confidence and targets

- **Goal.** "Medium confidence" means evidence, and target suggestions are relevant.
- **Design.** (a) Confidence needs at least one goal-specific metric for *medium*; without one it is
  *low* whatever the score (`sdg_mapper.py:446-452`, parameter in `v1.yaml`). (b) Complete the
  taxonomy to 169 targets from the UN list. (c) `sdg_mapper.py:545` picks targets by keyword overlap
  with the business description, not `targets[:3]`.
- **Files.** `sdg_mapper.py`, `sdg_taxonomy.py` (or move the list to `data/sdg/targets.yaml`),
  `v1.yaml` (bump to 1.3.0).
- **Tests.** SDG 1 at 30 with no metric → low. 169 targets, 17 goals. A solar deck's SDG 7
  suggestions include 7.1, not 7.a by position.
- **Risks.** Changes the "top SDG" pill wording on many reports; held-out SDG accuracy is on goals,
  not confidence, so it should not move.
- **Effort.** M.

### C14. Residual keyword effects

- **Goal.** No score moves on vocabulary alone.
- **Design.** (a) In `scoring_config.yaml` the Risk dimension is higher-is-better, yet "evidence"
  lowers it and "pollution" raises it. Fix the signs and state the direction in the file header.
  (b) `five_dimensions.py:219-224` keyword boosts apply only to dimensions with no reported metric
  and are capped at the baseline clamp (already partly true; make it explicit and tested).
  (c) `_count_controls` matches whole phrases through `negation.asserts_phrase(word_boundary=True)`.
- **Tests.** Perturbation: adding the words "evidence, monitoring, robust" to a deck changes no 5D
  score by more than 0.1. Adding a sentence describing a real control lowers omission risk.
- **Risks.** 5D scores shift slightly on text-only decks; bump `v1.yaml`.
- **Effort.** M.

### C16. Sector and Chinese extraction

- **Goal.** Held-out sector accuracy from 77 % towards 90 %; Chinese fact recall above 2 of 3.
- **Design.** (a) Sector: score sectors on the "what we do" section first (`text_sections` role
  `solution`), fall back to the whole text; add water / sanitation and circular-economy keyword
  sets; return "unknown" with the two best candidates rather than a wrong guess when the margin is
  small. (b) Chinese: C5b (4) numerals; unit words (戶, 人次, 公頃, 噸); sentence split on 、；.
- **Files.** `tools/impact/common.normalize_sector` and the inference in `pipeline`/`sdk`,
  `data/sdg_keywords_zh.yaml`, `extractors/regex_extractor.py`.
- **Tests.** The seven mis-sectored held-out decks (agua_viva, kisima, rehome, stitchright and the
  three greenwashers) — at least four fixed, none broken. Baseline updated.
- **Risks.** Over-fitting to the held-out set. Mitigation: write rules from the calibration corpus
  (57 decks, not the held-out 30) and only then run the held-out evaluation once.
- **Effort.** M–L.

### C17. Citations carried to the headline and the memo

- **Goal.** Every figure the IC reads can be traced to a page.
- **Design.** `_outcome_row` gains `page` (filled in `attach_citations` by matching `source`, as done
  for conflicts). The memo gains an "Evidence" section: the claims table (claim, page, NESTA level,
  signals), the variance drivers, the contribution split and the top negative impacts, reusing the
  view built by `decision_report.build_view` so there is one source of truth.
- **Files.** `expected_impact.py`, `pipeline.attach_citations`, `ic_memo.py`,
  `decision_report.build_view` (expose the pieces).
- **Report UX.** Page tag next to each outcome's source sentence; memo section "Evidence behind the
  numbers".
- **Tests.** Solar PDF: both outcomes carry a page; the memo HTML contains "p. 4" next to the reach
  sentence; Markdown has the table.
- **Effort.** M.

## 2.2 Report UX

### U3b. A fully translated pack

- **Goal.** `--lang zh-HK` or `zh-CN` gives a Chinese IC memo and DD report, and Chinese headers in
  the workbook.
- **Design.** (a) `report_v2.wrap_document(..., lang="en")` sets `<html lang>`, "On this page" and
  the skip link from the string table. (b) `render_ic_memo_html(..., lang="en")`: every literal goes
  through `t = translator(lang)` with keys prefixed `memo_`; generated sentences (gate reasons, plan
  items, 5D notes) go through `i18n_phrasebook.localize`, exactly as `decision_report._localize_view`
  does — factor that helper out and share it. (c) `render_dd_report_html(..., lang)`: labels through
  the table; question text from `data/i18n/dd_checklist_zh.yaml` where present (this is what makes
  `impact/i18n.py` live code: keep `load_dd_checklist_localized`, delete the unused
  `get_report_strings` / `get_dashboard_strings` and their YAML). (d) `exports.build_workbook(data,
  lang)`: sheet names stay English (they are identifiers); header rows and Summary labels
  translated. (e) `write_deliverables` passes `lang` to all of them. Markdown, DOCX and PPTX follow
  in a second step using the same keys.
- **Files.** `report_v2.py`, `ic_memo.py`, `dd_report_html.py`, `exports.py`, `pipeline.py`,
  `design/strings.py` (~90 new keys × 3), `i18n.py`, `data/i18n/`.
- **Data.** `dd_checklist_zh.yaml` is Simplified; derive a Traditional file with the build script
  (`s2hk`) and name them `dd_checklist_zh-CN.yaml` / `dd_checklist_zh-HK.yaml`.
- **CLI.** None (`--lang` exists).
- **Tests.** zh-HK memo: `lang="zh-HK"`, no English section heading (regex for
  `<h2[^>]*>[A-Za-z ]+</h2>`), verdict and plan in Chinese, claims verbatim. English memo
  byte-identical to before (golden file). Visual QA adds the zh memo and DD report (axe, no
  horizontal scroll). Key-parity tests cover the new keys automatically.
- **Risks.** `ic_memo.py` is one 470-line f-string function; do the conversion in small commits
  (hero and KPI strip, then each section) with the English golden file guarding each step.
- **Effort.** L.

### U8. LP, regulator and public editions open with a summary

- **Goal.** These editions do not start on bare KPI tiles.
- **Design.** A `summary` section for editions without the verdict: three generated sentences —
  what the company does (first non-claim sentence of the description), the expected-impact range in
  words, and the evidence quality with what is verified. No gate wording, no recommendation.
- **Files.** `decision_report.py` (`SPECS`, `_summary`), template, strings, phrasebook.
- **Tests.** LP edition contains the summary and not "Evidence plan required"; full edition unchanged.
- **Effort.** S.

### U6. Draft and narrative wrappers must not break HTML or PDF

- **Goal.** `impact_report(draft_review=True)` output is still a valid document.
- **Design.** In `impact_report_tool.execute`, wrap only text formats. For HTML and PDF insert a
  `<div class="draft-banner no-print-hide">` after `<body>` and put the narrative prompt in the tool
  result's text, not in the file.
- **Tests.** HTML output starts with `<!DOCTYPE` and ends with `</html>`; the banner is present;
  PDF bytes start with `%PDF`.
- **Effort.** S.

### U5. PDF polish

- **Goal.** A PDF that reads as a document: header on every page, bookmarks, repeated table heads,
  Chinese glyphs.
- **Design.** `pdf._chromium`: `header_template` with company name and the confidentiality notice;
  `tagged=True, outline=True` with a `TypeError` fallback for older Playwright; a font check that
  renders one CJK character and warns (not fails) when it falls back to tofu, with the install hint.
  CSS: `thead { display: table-header-group }`, `.table-wrap { overflow: visible }` in print, a
  printed contents list, `@page { @bottom-right { content: counter(page) " / " counter(pages) } }`
  for WeasyPrint.
- **Files.** `report_templates/pdf.py`, `design/report.css`, `report_v2.py` print rules,
  `docs/install-troubleshooting.md`.
- **Tests.** Mocked `page.pdf` receives the header and `tagged`; CSS assertions; visual test: a
  two-page table repeats its header (page count and text extraction with PyMuPDF).
- **Effort.** S–M.

### U9. Word and PowerPoint

- **Goal.** Office files that match the HTML in content and look like fund documents.
- **Design.** DOCX: `w:tblHeader` on header rows, East Asian font (`w:eastAsia`), landscape for wide
  tables. PPTX: 16:9, a title slide with fund branding, a verdict slide, an expected-impact slide
  with a native range chart, conditions, negative impacts; `ai_provenance.mark_pptx` writes the
  marking into core properties. Workbook: `print_title_rows`, landscape, fit to width.
- **Files.** `ic_memo.py` (`_docx_table`, `docx_house_style`, `render_ic_memo_pptx`),
  `ai_provenance.py`, `exports.py`.
- **Tests.** Open with python-docx / python-pptx and assert the properties; slide count and titles;
  marking present.
- **Effort.** M.

### U7. Report viewer

- **Goal.** What you download is what you see, and you can print it.
- **Design.** `GET /api/v1/chat/reports/{id}/download?file=report|memo|dd|xlsx|csv&lang=&audience=`
  renders on demand from the stored `report.json` (the files written at creation stay as a cache
  for the default). A Print button calls `iframe.contentWindow.print()` (sandbox gains
  `allow-modals`). Sign-off becomes a small form; signing off invalidates the cache so regenerated
  files carry the reviewer.
- **Files.** `web/reports_api.py`, `web/chat_ui.py`, `tests/test_web_reports.py`,
  `tests/test_v8_sign_off.py`.
- **API.** One new route (tenant-scoped, same permission as viewing).
- **Tests.** Download with `lang=zh-HK` returns a zh document; after sign-off the downloaded HTML
  names the reviewer; another tenant gets 404.
- **Risks.** CSP and sandbox changes; keep `allow-scripts` off for shared links.
- **Effort.** M. Depends on U3b for the memo and DD report languages.

### U4. Share links

- **Goal.** A shared report says it is shared, views are logged, and a link can be withdrawn.
- **Design.** The token gains a `jti`. `report.json` keeps `shares: [{jti, audience, lang, created,
  expires, revoked}]`. `shared()` rejects a revoked `jti`, records
  `AuditTrail.record_event("report.share_viewed", …)` (no IP stored; a coarse user-agent family
  only), and passes `share_notice` to the renderer: a banner "Shared read-only · expires 2026-12-01".
  `GET /reports/{id}/shares` and `DELETE /reports/{id}/shares/{jti}`. The UI reuses one link per
  (audience, language) until it expires. Error page translated, with `lang`.
- **Files.** `web/reports_api.py`, `web/chat_ui.py`, `decision_report.py` + template (banner),
  strings.
- **API.** Two routes. Tokens issued before this change have no `jti`: accept until expiry, list
  them as "legacy".
- **Tests.** Revoke → 410; view → one audit event; banner present with the expiry; legacy token
  still opens.
- **Risks.** Audit volume from link previews (messaging apps fetch URLs): count them but mark
  `preview: true` by user-agent family.
- **Effort.** M.

### U10. One branding path

- **Goal.** A fund's name, logo and colour appear on every deliverable from one setting.
- **Design.** `branding.resolve_branding(thesis, override=None) -> Branding` is the only entry.
  `pipeline.write_deliverables`, the web view, share links and `impact_report` call it and pass the
  result to the decision report, memo, DD report, DOCX and PPTX. One URL rule: `https:` and
  `data:image/` only (the stricter of the two). The decision report honours `accent_color` by
  setting `--brand` (with a contrast check against white; fall back to the default when it fails).
- **Files.** `branding.py`, `decision_report.py`, `pipeline.py`, `web/reports_api.py`,
  `impact_report_tool.py` (field description fixed), `docs/fund-manager-guide.md`.
- **Tests.** A thesis with `branding:` → name and logo on all three HTML files; an `http://` logo is
  dropped; a low-contrast colour is ignored.
- **Effort.** M.

### U11. Portfolio home and dashboard

- **Goal.** From the portfolio page you can reach each report; the dashboard exports what the CLI does.
- **Design.** `render_portfolio_page` sets `link` per row; client-side sort on the heat-map (no
  dependency: a 30-line script, progressive enhancement); the footer's AI line comes from the
  records' provenance. Dashboard: PDF and DOCX downloads, a comparison view built on F2.
- **Files.** `web/reports_api.py`, `portfolio_home.py`, `portfolio_home.html.j2`, `dashboard/app.py`.
- **Tests.** Rows link to `/reports/{id}`; the footer says "includes AI-assisted reports" when one
  record used a model.
- **Effort.** M. Comparison depends on F2.

### U12. No CDN in any report path

- **Goal.** Classic and iXBRL reports render offline.
- **Design.** The classic report's charts move to the same HTML/CSS bars the decision report uses,
  or the classic path is retired: `style="classic"` already warns as deprecated; make iXBRL build on
  the decision report and remove the Plotly `<script>` from `impact_report_tool.py:2709` and
  `html_template.py:80-85`.
- **Tests.** No `cdn.` or `https://` script source in any rendered HTML (one test over every
  renderer).
- **Risks.** iXBRL tagging positions are tied to the classic markup.
- **Effort.** M.

## 2.3 Regulations and frameworks

### R3b. Freshness gate covers every sourced file

- **Goal.** No reference file can go stale unnoticed.
- **Design.** Add to `knowledge.KNOWLEDGE_FILES`: `issb_s2_amendments.yaml`, `monitoring/vsme_basic.yaml`,
  `methodology/ghg.yaml`, `tracked_standards.yaml`, `living_wage_benchmarks.yaml`,
  `disclosure_checklists/climate.yaml`, `standard_articles/sse_g14.yaml`, `exclusion_criteria.yaml`,
  `population.yaml` (C6b). Give each the missing `as_of` / `source_url`; mark synthetic content
  (`sse_g14.yaml`) `data_status: illustrative` rather than claiming a source. A test lists every
  YAML under `data/` and fails when a file is neither in `KNOWLEDGE_FILES` nor in an explicit
  `NOT_KNOWLEDGE` list (scoring config, i18n, fund theses).
- **Tests.** The inventory test; the gate passes today and fails for a file with no `as_of`.
- **Risks.** Three files would fail on age (`issb_s2_amendments`, `living_wage_benchmarks`,
  `sse_g14`): each needs a real re-verification against its source, not a date bump.
- **Effort.** S–M (the re-verification is the work).

### R5. Registry completeness

- **Goal.** Every framework module has a registry row with version, date and source.
- **Design.** Rows for EU_TAXONOMY, SBTI, TCFD (status `superseded`, pointing to ISSB), SASB, GRI,
  TNFD, CDP, UNPRI, TWO_X, TISFD, SBTN. Each module exposes `REGISTRY_ID`; a test walks
  `frameworks/*.py` and requires a row. Version strings in modules (`issb_ifrs_s1.py:37`,
  `disclosure_packs.py:55`) read from the registry.
- **Files.** `data/standards_registry.yaml`, each framework module (one constant),
  `tests/test_standards_registry.py`.
- **Risks.** Writing a version without checking it. Each row is verified against the issuer's page
  and carries `last_verified`; a row that cannot be verified is added with `status: unverified` and
  listed in the commit.
- **Effort.** M.

### R8. Regulatory values out of Python

- **Goal.** Thresholds and dates in `regulatory_packs.py:264-286`, `engagements/regulatory.py:286-301`,
  `vsme.py:321-331`, `regulatory_calendar.py:275-283`, `csrd_wizard.py:18`, `sfdr_pai.py:715`,
  `sfdr_recast.py:60`, `issb_reporting.py:135` come from YAML.
- **Design.** Each constant becomes a lookup into the pack or jurisdiction row that already
  describes it (add `thresholds:` to the pack rows). `regulatory_calendar.DISCLOSURE_PROFILES` moves
  to `jurisdictions.yaml` and gains HK and CN. VSME: one datapoint id set (the module's), the YAML
  cites Delegated Regulation 2026/1560.
- **Tests.** Existing tests keep passing with identical values; a guard test greps these modules for
  four-digit years and currency thresholds.
- **Effort.** M.

### R6. GRI 101 / 102 / 103 and SBTi v2

- **Goal.** The GRI and SBTi checks reflect the standards in force.
- **Design.** Move the standards lists to `data/frameworks/gri.yaml` and `data/frameworks/sbti.yaml`
  (id, title, year, effective date, supersedes, disclosures, source). `gri.py` and `sbti.py` become
  loaders plus the matching logic. Add GRI 101 Biodiversity 2024, GRI 102 Climate Change 2025,
  GRI 103 Energy 2025 with their effective dates, mark the 2016 standards they replace as
  superseded from that date, and add the sector standards as a list. SBTi: thresholds per standard
  version; the checker reports against the version in force and notes the transition.
- **Tests.** Before the effective date the old disclosure is expected; after it, the new one.
  Existing GRI and SBTi tests pass against the YAML.
- **Risks.** I could not verify the current state of GRI 102/103 or SBTi v2 from this environment.
  **Do not write content from memory**: fetch the GRI and SBTi pages first; if they cannot be
  reached, ship the YAML move only and leave the new standards as watchlist rows.
- **Effort.** M each.

### R7. EU Taxonomy refresh

- **Goal.** The alignment check reflects the simplified reporting rules and is reachable.
- **Design.** `data/frameworks/eu_taxonomy.yaml`: objectives, activities with NACE codes, the
  delegated acts with dates, materiality thresholds from the simplification act. Expose through
  `framework_assess` (`eu_taxonomy`: list / assess) and `FRAMEWORK_CATALOG`. Registry row.
- **Risks.** As R6: verify the simplification act's status and thresholds at the source first.
- **Effort.** M.

### R9. HKFRS S2 check; ISSB nature mapping

- **Goal.** The climate standard has the same gap tool as S1; nature is ready when the text is final.
- **Design.** `data/regulatory/hkfrs_s2.yaml` in the S1 shape (IFRS S2 paragraphs, en + zh-HK cues),
  with the December 2025 amendments marked by effective date. Generalise `hkfrs_s1.py` into
  `frameworks/hkfrs.py` with `hkfrs_gap(text, standard="S1"|"S2", lang)`; keep `hkfrs_s1_gap` as a
  thin wrapper. Part D rows of the HKEX checklist gain `ifrs_s2_ref` so the two tools agree.
  Nature: no code until the Practice Statement is final; a watchlist row exists.
- **Tests.** As S1's; a report meeting S2 scores high on HKEX Part D too.
- **Effort.** M.

### R10. Watch items

ILPA Portfolio Company Template (January 2027): an export adapter beside
`lp_ddq_export_tool.py` when published. EDCI 2027 metrics. SFDR 2.0 final text: switch the
classifiers from "preview" to the adopted thresholds and record the application date. No work
until the texts exist; `regulatory_radar` and the scheduled freshness gate are the trigger.

## 2.4 New features

### F1b. IC conditions feed annual monitoring

- **Goal.** What the IC decided is what the company is asked about a year later.
- **Design.** `company_record` stores adopted conditions on the IC decision event:
  `conditions: [{id, type, text, timing, kind, status: open|met|waived, evidence}]`
  (`suggest_conditions` output plus an id). `annual_monitoring.build_request` adds one question per
  open condition after the fixed ones, typed by kind (number, yes/no with upload, free text). The
  portal answer updates the condition's status; the variance report lists conditions met and open.
- **Files.** `company_record.py`, `annual_monitoring.py`, `portal.html.j2`, `decision_workflow.py`
  (approve with conditions), `cli.py` (`monitoring request` unchanged).
- **Data.** State store: conditions live inside the existing decision record (no migration; absent
  means none).
- **API.** `POST /companies/{id}/decisions` accepts `conditions`.
- **Tests.** Approve with two conditions → the next request has two extra questions; answering marks
  one met; the LP report shows "1 of 2 conditions met".
- **Effort.** M.

### F5b. `assess` options

- **Goal.** The CLI reaches what the pipeline already supports.
- **Design.** `assess FILE...` (several files → `assess_files`), `--stage`, `--save` (writes the
  company record via `save_bundle`, with `--period`), keeping single-file behaviour identical.
- **Tests.** Two files → one bundle with a combined source label; `--save` creates a record.
- **Effort.** S.

### F3. IC one-pager

- **Goal.** One printed A4 page for the committee pack.
- **Design.** `render_ic_onepager(data, lang, branding)`: verdict and note; expected impact with the
  range bar; three reasons; top three conditions; the top negative impact and whether a control is
  described; evidence quality; stamp and AI disclosure in the footer. Built from
  `decision_report.build_view` so numbers match the report. Written by `write_deliverables` as
  `<stem>_ic_onepager.html` (and PDF with `--pdf`).
- **Files.** `report_templates/onepager.py`, `design/templates/onepager.html.j2`, `pipeline.py`,
  strings, README deliverables list.
- **Report UX.** Fixed A4 layout, no page break; text clamps so it cannot overflow.
- **Tests.** Contains the same P50 as the report; Chromium print: exactly one page for the three
  sample decks in en and zh-HK; axe clean.
- **Effort.** M.

### F2. Deal comparison

- **Goal.** `impact-vision compare a.pdf b.pdf [c.pdf]` puts deals side by side on the things an IC
  weighs.
- **Design.** `impact/compare.py`: `compare_bundles(bundles) -> dict` with one column per deal:
  gate, expected impact P50 and range per outcome kind (never summed across kinds), per-US$1m when
  the ask is known, evidence quality, greenwashing, top negative impact, open plan items. No
  composite score and no "winner": the table states where ranges overlap ("cannot be told apart")
  using the P10–P90 intervals. `decision_workflow.compare_deals` delegates to it and drops the
  `5D*20 - risk*0.25` composite. HTML through the design system; `--json`.
- **Files.** `compare.py`, `cli.py`, `decision_workflow.py`, template, strings, README CLI section.
- **Tests.** Two decks → two columns; overlapping ranges are flagged; different outcome kinds are
  not ranked against each other; the agent tool's output keeps its keys minus `composite`.
- **Risks.** Removing `composite` is a breaking change for the agent tool; list it in CHANGELOG.
- **Effort.** M.

### F4. Re-run diff

- **Goal.** "What changed since the last assessment" for a company.
- **Design.** `company_record.diff(previous, current)`: gate, P50 and range per outcome, evidence
  quality, claims added and removed (by normalised text), metrics changed, conditions met. Shown at
  the top of a re-run report and in the company page.
- **Tests.** Re-assess with one more verified claim → the diff lists it and the evidence-quality change.
- **Effort.** M.

### F8. Portfolio view of expected vs actual

- **Goal.** A fund page from company records: expected against actual by stakeholder type.
- **Design.** Builds on C15b's grouping. One row per company and outcome, a small expected-range bar
  with the actual marked, variance drivers in words, conditions status (F1b).
- **Effort.** M. Depends on C15b and F1b.

### F9. One Hong Kong command

- **Goal.** `impact-vision framework hk-pack report.pdf --issuer largecap --lang zh-HK` prints one
  gap list across the HKEX ESG Code, HKFRS S1 (and S2 with R9) and the HK Taxonomy screen.
- **Design.** `frameworks/hk_pack.py` runs the three, de-duplicates overlapping items through the
  `ifrs_s1_ref` / `ifrs_s2_ref` cross-references, orders by basis (mandatory first) and writes text,
  JSON or an HTML page in the design system.
- **Effort.** M. Better after R9.

### F7. Benchmarks in v2 units; F10. Calibration study

Both need inputs the code cannot produce. F7 needs sector figures for person-years and tCO2e per
US$1m with sources; the schema is a `v2_units` block in `benchmarks.yaml` (sector, unit, p25, p50,
p75, n, source, year), read through `benchmark_provider`. F10 needs two or three practitioners to
rate the 57-deck corpus (`impact-vision calibrate packet`); `calibrate analyze` then proposes the
parameters that C8 and C11 currently carry as `illustrative`.

---

# Part 3 — Roadmap

Order of work. Within a phase, items are listed in the order to do them.

| Phase | Theme | Items | Depends on | Why here |
|---|---|---|---|---|
| **1** | The verdict is right | C7 → C11 → C6b → C5b → C15b | C1 (done) for C7 | Each one is a case where the tool gives a wrong or over-confident answer today. Small, test-backed. |
| **2** | The verdict is useful | C10 → C8 → C9 → F6 | C10 before C8 (thresholds in YAML); C11 before C8 (levels); C8 before C9 (gate conditions); C9 before F6 (plan kinds) | Methodology 2.2.0 lands once, as one coherent change, with one baseline update. |
| **3** | The IC pack | F5b → U8 → C17 → U3b → F3 → F2 → F1b | U3b before F3 (one-pager born translated); F2 before U11's comparison | What a committee actually receives. |
| **4** | Deliverable polish | U6 → U5 → U9 → U10 → U7 → U4 → U11 → U12 | U3b before U7; F2 before U11 | No scoring impact; safe to parallelise. |
| **5** | Standards | R3b → R5 → R8 → R9 → F9 → R6 → R7 | R9 before F9; web access for R5, R6, R7 | Needs source verification; cannot be done from memory. |
| **6** | Needs data or people | C12, C13, C14, C16, F4, F8, F7, F10, R10 | F8 after C15b and F1b; C16 after C5b | Larger, or waiting on inputs. |

**Release shape.** Phase 1 can ship as 0.19.2 (fixes; methodology unchanged except where noted).
Phase 2 is a methodology release (2.2.0) and should ship alone as 0.20.0 so score movements have one
cause. Phases 3 and 4 are additive.

**Dependency notes.**

- C7 adds `exclusion_criteria.yaml` to the hash: one more one-time change of every report's config
  hash. Batch it with the Phase 2 methodology bump if both land in the same release.
- C11 and C8 both move held-out numbers. Update `baseline.json` once, in the C8 commit, and record
  the per-deck changes there.
- U3b touches `ic_memo.py` heavily; C17 adds a section to it. Do C17 first so the new section is
  translated in the same pass.
- R6 and R7 are blocked on reaching the issuers' pages. If they cannot be reached, do the YAML move
  only.

---

# Part 4 — Status

See the end of this file; updated whenever work stops.

*(2026-11-10, at the time of writing the spec)* Implemented: C1, R1, R2, U1, U2, C2, C3, C4,
F1 (first half), F5 (`--thesis`), C5 (part), U3 (part), C6 (conflicts), C15 (`bayes.fold`).
Everything in Part 2 is open.

*(2026-11-10, after the parallel merge)* Also implemented: C7, C11 (part 1), C6b, C8, U3b (part),
U4 (part), F2 (part), F3, C5b (part), R6 / R7 (part). See "Second pass and parallel branches" in
Part 1 for what each still lacks. Everything else in Part 2 is open.
