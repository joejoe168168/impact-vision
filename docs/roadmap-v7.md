# Impact Vision — Roadmap v7.0

**Date:** 2026-10-06
**Status:** Released as 0.17.0 (2026-10-07) — "Trusted, Effortless & Beautiful"
**Audience:** product, engineering, fund managers, consultants, LPs
**Builds on:** `roadmap-v6.md`, `roadmap-v6-implementation.md`,
`roadmap-updates-2026-07.md` (all still valid for the capability backlog)

**Thesis.** Through v6 we built an unusually *broad* engine: 95 impact
modules, 22 framework modules, 52 agent tools, six user surfaces, and
1,423 passing tests. The bottleneck is no longer capability. What holds us back
now is that **a first-time user can't get a trustworthy, good-looking answer
in five minutes**. v7 is therefore a **consolidation + experience** wave, not
a feature wave:

1. **Make the numbers trustworthy.** Fix the defects that make a
   well-evidenced company look bad: dropped claims, sector-blind DD,
   implausible SDG scores, silent data loss in pip installs.
2. **Make it effortless.** Go from one deck to one report in one command, one
   click or one tool call, with no API key needed for the first run.
3. **Make the output beautiful and decision-first.** Use one design system, a
   verdict on the first screen, evidence shown as prominently as scores,
   print-perfect PDFs, and zh-HK / zh-CN output.
4. **Stay current.** Absorb the Jul–Oct 2026 regulatory changes: ESRS/VSME
   now law, SFDR 2.0 Parliament text, UK SRS comply-or-explain, ISSA 5000,
   HK taxonomy Phase 2B, and Article 50 AI transparency under the EU AI Act.

Engineering rule (unchanged): **extend / wrap, never fork.** v7 adds one more
rule: **every new surface is generated from the tool registry, and every
number shown to a user carries its provenance and methodology version.**

---

## 1. Review summary (October 2026)

Four parallel reviews were run against `main@e55df8e`: UX surfaces, report
output quality, architecture / code health, and a regulatory delta scan.
Sample outputs were generated from `demo/pig_farm_profile.json` and
`examples/sample_company.yaml`.

### 1.1 What is already strong (keep)

- Breadth and correctness discipline: 1,423 tests green, `ruff` clean, and
  deterministic, explainable scoring with no black-box LLM scores.
- Trust primitives: evidence graph, hash-chained audit trail, MetricRecord
  provenance, `is_estimate` badge, standards registry with source URLs.
- The web chat UI (`web/chat_ui.py`) is genuinely polished. It has streaming,
  tool cards, file upload and an artifacts panel, and it persists transcripts.
- `impact_advisor` routing works well and its playbooks are sensible.
- The report already has a provenance legend, chart aria-labels, audience
  filter, dark theme and white-label tokens. The design system has a seed.

### 1.2 Diagnosis — five problems

| # | Problem | Evidence | Severity |
|---|---|---|---|
| **D1** | **Scores can't be trusted on first use.** Extracted claims are dropped unless they carry an IRIS+ ID, so a pitch full of numbers gets "0 tracked / 0% coverage / NO_VERIFICATION". DD runs all 122 questions regardless of sector, so a pig farm gets "Key risk areas: Fintech, Health, Mining". One core metric set is applied to every sector (a pig farm is told to track "Client Protection Policy"). SDG targets aren't filtered by goal, and a microfinance firm scores "high" on SDG 14. The no-LLM CLI returns 0% for realistic text, and `quick_screen` flags a reasonable solar deal as `red_flag`. | `impact/sdk.py:132`, `impact/sdk.py:237`, `impact/gap_analysis.py:138`, `impact/sdg_mapper.py:305-309,423`, `impact/dd_checklist.py:145-171` | **Critical** |
| **D2** | **pip-installed copies silently lose their reference data.** About 20 loaders use `Path(__file__).parents[3]/"data"`, but the wheel ships data under `openharness/_data/`. An installed copy scores using hard-coded fallbacks and gets an empty DD checklist. No CI job tests the built wheel. | `impact/five_dimensions.py:69`, `impact/dd_checklist.py:72`, `impact/sdg_mapper.py:92`; `pyproject.toml:77` | **Critical** |
| **D3** | **Too hard to start.** The default `impact-vision` command needs Node, which isn't documented. No sample deck ships. There is no `assess <file>` CLI. The agent sees 89 tools, 37 of them coding tools like bash and worktree. `engagement_suite` has 65 actions behind an untyped `payload: object`. Tools don't hand off: `pitch_deck_analyze` returns text and no company handle, so the LLM has to re-type 29 params into `impact_report`. Six surfaces (TUI, CLI, web chat, console, Streamlit, REST, MCP) each expose a different tool subset. | `ui/react_launcher.py:75`, `web/chat_session.py:133`, `tools/impact/engagement_suite_tool.py` | **High** |
| **D4** | **Reports look generic and bury the decision.** There are eight separate CSS/chrome systems. The main report is about 1,500 lines of f-strings with 30 KB of inline CSS. The first screen is a hero banner with tag pills and no verdict. Gap lists are duplicated, and recommendations repeat across every SDG. Company and claim text is not HTML-escaped (an XSS payload ran). Plotly loads from a CDN, so reports break offline. There is no real PDF (the WeasyPrint path falls back to HTML), and Chrome prints 20 pages, toolbar included. Dark-mode headings are at about 2:1 contrast. The TOC overlaps the body at 1360–1530 px. Tables overflow on mobile. There is no zh-HK/zh-CN. `lp_ready` and `audience="public"` produce the same report as `full`. | `tools/impact/impact_report_tool.py:2488-2930,1402,2312,2773,3599`; `report_templates/*` | **High** |
| **D5** | **State and knowledge are fragile.** Engagement workspace, audit trail, review queues and RBAC are all in memory. `import_state` is never called, so a restart loses consultant work. HMAC signing keys are hard-coded, so the "signed" assurance manifests can be forged. Regulatory dates live in five modules and benchmarks in four. Scoring weights are hard-coded and no output carries a methodology version. Docs have drifted from the code: "10 frameworks" vs 22, "46 actions" vs 65, `/health` reports v0.15.0 / 39 tools, and README is 1,004 lines. | `audit_trail.py:75`, `engagements/verification_bundle.py:327`, `engagements/workspace.py:99`, `api_gateway/router.py:349`, `greenwashing.py:268` | **High** |

---

## 2. Standards & market delta (Jul → Oct 2026)

Items the knowledge base **must** absorb. The July update covered everything
before 2026-07-03.

| Priority | Development | Status (2026-10-06) | Action in Impact Vision |
|---|---|---|---|
| **P0** | **Revised ESRS + VSME are law.** Delegated Regs (EU) 2026/1563 (ESRS) and 2026/1560 (VSME) | Published OJ 2026-09-21. In force 2026-11-10. Mandatory for FY starting ≥ 2027-01-01. Value-chain cap: CSRD reporters can't demand more than VSME from partners with ≤1,000 employees | Drop the "adopted-pending" flag. Refresh `frameworks/esrs.py` + `csrd_wizard.py` datapoints (replace synthetic rows). Add a **VSME investee template** to `investee_collection`. Enforce the VSME ceiling as a hard rule in `engagements/data_room` request packs |
| **P0** | **EFRAG draft ESRS XBRL taxonomy** | Consultation 2026-09-17 → 2026-11-11. Final to ESMA by year-end | Point `xbrl_export` at the 2026 draft, pin the version, schedule a re-sync for Q1 2027 |
| **P0** | **SFDR 2.0** — EP ECON mandate | Adopted 2026-09-10. Plenary Oct 2026. Trilogue from Q4 2026. Application ~2029. ECON: "impact" language only in Art 7/9 with pre-defined, measurable outcomes and a disclosed theory of impact | Add a Parliament variant alongside the Council one in `classify_sfdr2_category`. New check: **impact-claim → Art 7/9 + ToC + measurable outcome**, built from `toc_builder` + 5D evidence. This is a natural differentiator |
| **P0** | **UK SRS for listed issuers** — FCA PS26/19 | Final 2026-09-30. **Comply-or-explain** for periods from 2027-01-01. Scope 3 relief 1 yr, wider S1 relief 2 yrs | Update the UK profile in `engagements/regulatory.py`. Keep transition-plan rules on the watch-list |
| **P0** | **EU AI Act Digital Omnibus** — Reg (EU) 2026/1744 | In force 2026-07-27. Art 50 transparency applies from 2026-08-02. Annex III deferred to 2027-12 | Put an AI-provenance badge (extracted / estimated / drafted by AI) on **every** output: HTML, XLSX, PDF, DOCX, not only LP Q&A |
| **P0** | **Hong Kong** (core users) | HKEX LargeCap climate disclosure mandatory from FY2026; full HKFRS S1/S2 consultation in 2027 targeting ~2028. HK Taxonomy Phase 2A final (Jan 2026). Phase 2B prototype consultation closes 2026-10-07. HKSSA 5000 effective for periods ≥ 2026-12-15 | Add an **HK Taxonomy alignment screen** (2A now, 2B when final). Add HKSSA 5000 to assurance readiness. Add HKEX milestones to the calendar. Add a TPT/ISSB-aligned transition-plan template |
| **P1** | **ISSA 5000** effective 2026-12-15 | Confirmed. ISAE 3000/3410 retire for sustainability engagements | Switch the assurance-pack / verification-bundle framing to ISSA 5000. Record *where* AI was used per figure (extraction / calc / tagging / drafting) |
| **P1** | **ISSB** | S2 amendments effective 2027-01-01 (already in the KB). Taxonomy "Update 1" consultation closed 2026-09-28. Human Capital project renamed "Workforce-related Disclosures" (2026-09-24). **Nature Practice Statement ED** expected Oct 2026 with 120-day comment period. TNFD pausing new work | Rename the project in the registry. Plan `frameworks/tnfd.py` → ISSB nature mapping and relabel TNFD "feeding ISSB" |
| **P1** | **California SB 253** | First Scope 1+2 deadline reset to **2026-11-10**. SB 261 still enjoined | Show a live calendar alert now (5 weeks out) |
| **P1** | **ECGT Directive** applies 2026-09-27; Green Claims Directive shelved | Operative law against generic claims | Greenwashing modules should cite ECGT + UCPD as operative and label GCD "shelved" |
| **P2** | GHG Protocol Scope 2 revision | Feedback summary 2026-07-29. Further consultation likely. Final ≥2027 | Keep annual market-based as the default. Hourly matching goes on the watch-list |
| **P2** | ILPA Portfolio Company Metrics template refresh | Comments closed 2026-10-02. Final early 2027 | Export adapter alongside EDCI once final |
| **P2** | Asia ISSB adoption: Japan SSBJ (Prime ¥3tn+ from FY Mar-2027), China MoF Climate Standard No.1 (trial, Dec 2025), Singapore phasing (non-STI ≥S$1bn FY2028), Australia AASB S2 Group 2 (FY from 2026-07-01) | Final | Refresh `issb_adoption.yaml` rows and add a distinct China MoF profile |
| **Watch** | GIIN State of the Market 2026, IRIS+ revision, Impact Frontiers norms v2, SBTN v2, Ninth Circuit SB 261 ruling, SEC rescission vote, PACM credits | Unconfirmed / pending | `regulatory_radar` watch-list |

*Sources are listed in §9. Regulatory facts need re-verification at
implementation time; every changed row must carry `as_of` + `source_url`
(see W5).*

---

## 3. North star & product principles

**North star:** *A Hong Kong-based consultant drags a pitch deck into the web
chat and, within five minutes and without reading docs, receives an
IC-ready, bilingual report that they would send to a client unedited, in which
every number can be traced to a source sentence.*

Principles added in v7:

1. **Verdict first, evidence second, detail last.** Every deliverable opens
   with a decision card (what, why, how confident, what would change our mind).
2. **No false negatives from missing keywords.** Low evidence produces
   "insufficient evidence", never a 0% score or a `red_flag`.
3. **One registry, many surfaces.** CLI, REST, MCP, console and web are
   generated from `create_default_tool_registry()` and can't drift.
4. **Every number is stamped:** source, provenance class, methodology
   version, as-of date.
5. **Sector-aware by default.** Questions, core metrics, risks and
   benchmarks are filtered by canonical sector.
6. **Works offline and prints well.** No CDN dependency in deliverables. PDF
   is a first-class output.
7. **Bilingual by design.** en / zh-HK / zh-CN strings come from a catalogue,
   with CJK font stacks.

---

## 4. Waves & tracks

Each item names the module it extends. Effort: S ≤ 3 days, M ≤ 2 weeks,
L ≤ 4 weeks.

### Wave 0 — Trust fixes (weeks 1–3, P0; ship as 0.16.x patch releases)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W0.1 | **Data path fix.** One `impact/_paths.py` resolver using `importlib.resources` (`openharness/_data` → repo `data/` fallback). Replace every `parents[3]/"data"`. Stop shipping `data/impact_vision.db`. Default the SQLite path to `~/.impact-vision/`. Add a **wheel smoke-test CI job** (build → install in a clean venv → score the sample company → assert non-empty DD + config) | all loaders, `storage.py:17`, CI | S |
| W0.2 | **Claims → evidence.** Keep extracted claims without an IRIS ID as `ImpactClaim` evidence on the Company. Fix decimal splitting ("1.8 GWh"). Render the claims section. Feed claims into 5D provenance and greenwashing verification (named verifiers like SIRIM/SEDEX count) | `sdk.py:132`, `extractors/`, `greenwashing.py` | M |
| W0.3 | **Sector-aware DD and core metrics.** Filter `dd_checklist.yaml` by canonical sector plus universal questions. Add per-sector core metric sets in YAML. Derive risks from the document text, with templates only as fallback | `sdk.py:237`, `gap_analysis.py:138`, `risk_opportunity.py` | M |
| W0.4 | **SDG plausibility.** Filter `matched_targets` by goal. Rank theme suggestions by relevance, not alphabet. Add a materiality cap (show material SDGs only, with "other goals" collapsed). Add a sanity rule that no goal scores "high" without a goal-specific metric | `sdg_mapper.py:305,423` | S |
| W0.5 | **Low-evidence guard.** Below a minimum text/evidence threshold, return `insufficient_evidence` instead of 0% or `red_flag`. Add synonym + partial matching for DD/framework scan, and `dd analyze --sector --json` | `dd_checklist.py:145`, `deal_gate.py`, `cli.py` | M |
| W0.6 | **Escape all user text.** Interim fix: `html.escape` at the 61 sites. Permanent fix in W2 (Jinja autoescape). Add an XSS regression test | `impact_report_tool.py` | S |
| W0.7 | **Report options that do nothing.** Fix the `target_progress` crash. Make `lp_ready` / `audience=public` real variants (no confidentiality banner, no internal flags) | `impact_report_tool.py:456,2312,3214` | S |
| W0.8 | **Fail-closed signing keys.** Read HMAC keys from env/KMS and refuse to sign with the default in non-dev mode | `audit_trail.py:75`, `lp_portal.py:84`, `data_room.py:675`, `verification_bundle.py:327` | S |
| W0.9 | **Golden-output tests.** Pig farm, BrightPath and a solar deck, with assertions on *plausibility*: the pig farm shows ≥5 tracked claims, no fintech risk areas, and solar is not red-flagged | `tests/` | S |

**Exit criterion:** the three golden companies produce results a domain
expert would sign off on, and an installed wheel matches a source checkout
byte-for-byte on scores.

**Status (2026-10-06):** W0.1–W0.9 are implemented on branch `v7-wave0`. See
CHANGELOG `[Unreleased]`. While doing this we found that the SDK ran without
the IRIS+ catalog, and fixed that too. One follow-up, **W0.10**, is pulled
forward from W5.6: map extracted claims to IRIS+ metric IDs (unit + context
→ ID, e.g. "920 tonnes CO2e avoided" → OI2764). Without it, an evidence-rich
pitch with no IRIS+ IDs still scores "estimated" on 5D/SDG. The pig-farm IC
gate still fails on those estimated scores, even though `quick_screen` now
correctly calls this `insufficient_evidence`. The IC memo/deal gate should
adopt the same data-gap rule.

**W0.10 status (2026-10-06):** implemented on branch `v7-w0.10` (claim →
IRIS+ mapper + gate `data_gap` / `evidence_status`). New follow-up,
**W0.11**, is the `pitch_deck_analyze` front door. On the pig-farm pitch it
names the company "Pig", detects the sector as *education*, adds unrelated
themes/SDGs (Affordable Housing, SDG 4/11), and routes ESG modules on
stop-words ("the, of, and, to"). Sector/theme detection needs the same
word-boundary + weighting treatment as W0.3.

**Wave 0 complete (2026-10-06):** W0.1–W0.11 are done and merged to `main`.

### Wave 1 — Effortless first run (weeks 3–7)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W1.1 | **`impact-vision demo`**: no API key. Bundles 3 sample decks (PDF) in `examples/decks/`, writes an HTML + PDF report and opens the browser | `cli.py`, `sdk.py` | S |
| W1.2 | **`impact-vision assess <file> [--sector] [--lang zh-HK] [--audience ic\|lp\|public] [--out report.html\|.pdf\|.docx]`**: one deck to one report, LLM optional (it improves extraction when a key is present) | `sdk.py`, `pitch_deck_analyze_tool.py` | M |
| W1.3 | **`assess_deal` macro tool.** Chains the 7-step `deal_screening` playbook and returns a saved `assessment_id`. All downstream tools (`impact_report`, `greenwashing_detect`, `lp_narrative`, …) accept `assessment_id` instead of 29 re-typed fields | `advisor_tool.py`, `storage.py` | M |
| W1.4 | **Fund-mode tool profile** (default in web chat + MCP). Exposes impact tools only, hides bash/file/worktree/team/cron. Developer mode is opt-in | `tools/__init__.py`, `web/chat_session.py:133` | S |
| W1.5 | **Split `engagement_suite`** into ~6 typed tools (data_room, value_creation, reporting_studio, training, regulatory, assurance), with a pydantic model per action. Merge or deprecate duplicate pairs: `beneficiary_feedback`/`stakeholder_voice`, `lp_ddq_export`/`ddq_responder`, `regulatory_calendar`/`regulatory_radar`, `pipeline`/`guided_assessment`/`decision_workflow`. Target **≤40 well-typed tools**, all reachable via `impact_advisor` | `tools/impact/*`, `tool_advisor.py` | L |
| W1.6 | **Install split.** Lean core + extras `[web]`, `[dashboard]`, `[mcp]`, `[pdf]`, `[llm]`. Default the TUI to Python, or document Node. Add `pipx install impact-vision` and Docker one-liners. Remove the obscure provider profiles from the default README table | `pyproject.toml`, `ui/react_launcher.py` | M |
| W1.7 | **Plain-language layer.** A glossary (NESTA, OPIM, Lean Data, 5D, …) with in-report tooltips. Name sections by task, not by release ("v3 Trust Infrastructure" → "Evidence & assurance") | `docs/glossary.md`, i18n catalogue | S |

**Wave 1 status (2026-10-06):** done on branch `v7-wave1`. W1.1 `demo`,
W1.2 `assess`, W1.3 `assess_deal` + `assessment_id`, W1.4 fund tool profile,
W1.5 `engagement_suite` catalogue/validation + five duplicate tools merged
(53 → 48; the ≤40 target was deliberately not pursued), W1.6 extras +
dashboard command + Node guidance, W1.7 glossary + task-named docs.
Not done: Docker image and `pipx` instructions (W1.6), which wait for a
PyPI release.

### Wave 2 — Report design system & decision-first deliverables (weeks 5–12)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W2.1 | **One design system.** `report_templates/design/` contains `tokens.css` (light/dark via `prefers-color-scheme` + manual toggle, brand overrides), `base.css`, and Jinja2 partials with **autoescape** (hero, verdict card, KPI strip, score bar with confidence band, evidence badge, data table, callout, chart frame, footer). Port the impact report (#1) and `report_v2` (IC memo, DD, investee portal) onto it. Delete `html_template.py` CSS. Restyle the portfolio + pipeline dashboards. Break `impact_report_tool.py` (4k LOC) into `report_builders/` + templates | `report_templates/`, `impact_report_tool.py`, `ic_memo.py`, `investee_portal.py`, `portfolio_report.py`, `pipeline_tool.py` | L |
| W2.2 | **Decision-first layout** (all audiences): | | M |
| | ① **Verdict card**: Proceed / Conditional / Decline, IC-gate result, top 3 reasons, confidence band, methodology version | `verdict_engine.py`, `deal_gate.py` | |
| | ② **KPI strip** (4 max) → ③ **"What would change our mind"** (3 highest-value missing evidence items, each with score impact) | `improvement_advisor` | |
| | ④ 5D radar **with sector-benchmark overlay** and one plain-English sentence per dimension | `benchmarks.py` | |
| | ⑤ **SDG wheel** (official colours, accessible text) limited to material goals | `sdg_mapper.py` | |
| | ⑥ **Evidence ledger**: every claim with source quote, page, NESTA level, verification, AI-provenance badge. Click a score to filter the claims that drive it | `evidence_chain_renderer.py`, `evidence_graph.py` | |
| | ⑦ **One action plan**: merged gaps + recommendations, de-duplicated, each with owner / due / score lift | `gap_analysis.py` | |
| | ⑧ Risks from documents → greenwashing findings tied to claims → ⑨ appendix (methodology, metrics, frameworks, audit hash, QR to verify) | `greenwashing_reviewer.py`, `audit_trail.py` | |
| W2.3 | **Real audience variants**: IC memo (2–4 pp), LP report (6–10 pp), public/microsite (no internal flags), regulator (framework-indexed). Driven by one `ReportSpec` | `reporting_studio.py`, `lp_narrative.py` | M |
| W2.4 | **Print & offline.** Vendor minified Plotly (or static SVG via kaleido) so there is no CDN. Add a print stylesheet (hide modebar, dock, interactive checklist, page breaks, running header/footer, page numbers). Generate PDF via Playwright/Chromium (`[pdf]` extra) with WeasyPrint+SVG fallback. Also a **DOCX** export of the IC memo for consultants who edit in Word | `impact_report_tool.py:3599`, new `report_templates/pdf.py` | M |
| W2.5 | **Bilingual output.** `lang` param, string catalogue (en / zh-HK / zh-CN) for all chrome + recommendation text, Noto Sans TC/SC font stack, locale number/date formatting, `lang` attribute set correctly | `impact/i18n.py` | M |
| W2.6 | **White-label done properly.** Logo, fund name, footer and disclaimer from `branding.py`. Charts take brand palette. Optional "Generated by Impact Vision" footer | `branding.py` | S |
| W2.7 | **Accessibility & responsive QA.** WCAG 2.2 AA: table `scope`/`caption`, real buttons instead of `tr[role=button]`, contrast ≥4.5:1 in both themes (white-on-SDG-7-yellow fixed), TOC breakpoint ≥1560 px, no dead TOC links, mobile hero shows the verdict above the fold, tables scroll inside their container. **CI: axe-core + Playwright screenshot diff at 390 / 1024 / 1440 px, light & dark** | new `tests/visual/` | M |
| W2.8 | **Better data exports.** XLSX with frozen headers, autofilter, column widths, numeric cells and a methodology sheet. JSON with `schema_version` and a `slim` mode (no evidence chains, 509 KB → ~50 KB). CSV numeric columns + separate display columns | `impact_report_tool.py` | S |

**Wave 2 status (2026-10-06):** done on branch `v7-wave2`. W2.1–W2.3
decision-first report on one design system (tokens, Jinja2 autoescape, five
audience `ReportSpec`s; IC memo, DD report and portal share the tokens),
W2.4 Chromium PDF + print CSS + IC memo `.docx`, W2.5 zh-HK / zh-CN, W2.6
white-label (fund name, logo, colour, footer, optional attribution; charts
deliberately keep the validated palette), W2.7 axe-core + responsive CI, W2.8
XLSX/JSON/CSV exports (`impact/exports.py`). Plotly was dropped rather than
vendored: charts are inline SVG/CSS with table twins. Not done: splitting
`impact_report_tool.py` into `report_builders/` (the classic report remains
for one release), restyling the portfolio and pipeline dashboards, and
click-to-filter in the evidence ledger.

### Wave 3 — One product, many surfaces (weeks 8–14)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W3.1 | **Registry-generated surfaces.** REST routes, MCP tools/prompts and console forms are generated from tool schemas. `/health` reads `__version__` and the live tool count. MCP gains the advisor, the new typed engagement tools and **MCP prompts** for the top playbooks | `api_gateway/router.py`, `impact/mcp_server.py`, `web/console.py` | M |
| W3.2 | **Web chat as the primary app.** "Analyze a pitch deck" starter card (drag-drop). **Inline report viewer** (iframe in the artifacts panel) with language/audience switch. A "Share" button producing a signed read-only link. Consistent connection/credential status. Engagement view (deliverables, checklist, deadlines) | `web/chat_ui.py`, `web/chat_api.py` | L |
| W3.3 | **Position the other UIs.** Streamlit becomes the no-LLM portfolio dashboard (sector dropdown, metric picker by name instead of IRIS IDs, deck upload, `impact-vision dashboard` command). Retire `/console` once W3.1 makes the chat's tool cards cover it | `dashboard/app.py` | M |
| W3.4 | **Portfolio home.** One page per fund: pipeline, portfolio 5D/SDG heat-map, deadlines (SB 253, ESRS, SFDR), evidence-review queue, and the companies whose data is stale | `portfolio_rollup.py`, `regulatory_calendar.py`, `evidence_workflow.py` | M |

**Wave 3 status (2026-10-06):** done on branch `v7-wave3`.
- **W3.1:** `impact/surfaces.py` feeds every surface. REST gets
  `/api/v1/tools/{name}` with path/URL fields blocked for remote callers;
  MCP exposes all 48 tools with typed schemas plus 10 playbook prompts; the
  console builds a form per registry tool.
- **W3.2:** offline "Analyze a pitch deck" in the web chat, a sandboxed
  inline viewer with audience/language/theme switches, signed and
  revocable share links, and a Reports tab.
- **W3.3:** the Streamlit dashboard takes deck uploads and has pickers by
  name.
- **W3.4:** portfolio home.

Deliberately different from the plan:
- `/console` was kept (now generated) rather than retired.
- The engagement view (deliverables, checklist, deadlines per engagement)
  was not built at first, because the engagement store needed persistence.
  It shipped as a follow-up after W5.3.
- The evidence-review queue on the portfolio home is derived from saved
  reports, because `evidence_workflow.ReviewQueue` is not persisted.

### Wave 4 — Standards currency (weeks 2–10, parallel; one engineer)

Implements §2. Order: ESRS/VSME law + VSME template → SFDR 2.0 EP variant +
impact-language check → UK SRS → HK taxonomy screen + HKSSA 5000 → AI
provenance badge on all outputs → ISSA 5000 framing → ECGT in greenwashing →
ISSB naming / nature mapping prep → Asia adoption rows → SB 253 alert.

**Wave 4 status (2026-10-06):** done on branch `v7-wave4`. The §2 facts were
re-checked against the §9 sources (and EUR-Lex, HKMA, HKICPA, FSA, ACRA,
AASB) on implementation day. Five corrections were applied:
- VSME (Reg 2026/1560) has been in force since 2026-09-24, not 2026-11-10.
- China's MoF Basic Standard (trial) dates from 2024-11-20. Only Climate
  Standard No.1 is from December 2025.
- The Green Claims Directive is "shelved, withdrawal announced but not
  formalised", not "withdrawn".
- The SFDR 2.0 "impact" add-on is common to all three institutions'
  texts, not ECON-only.
- AI Act content marking has a 2026-12-02 grace period for systems already
  on the market.

What shipped:
- **W4.1 ESRS/VSME law:**
  - Revised-ESRS metadata carries the legal instrument and a date-aware
    `legal_status`.
  - The generated `*-DRAFT-nnn` filler rows are gone.
  - VSME investee template (`sector="vsme"`) and `vsme_basic` /
    `vsme_comprehensive` request packs.
  - The value-chain cap is a hard rule in `build_data_request_pack`:
    fields beyond VSME become voluntary for partners with ≤1,000 employees.
- **W4.2 SFDR 2.0:** `position=commission|council|parliament`, plus an
  "impact"-wording check. It requires Art 7/9, a pre-defined objective, a
  passing `toc_builder` validation (or a disclosed theory) and
  evidence-based measurement.
- **W4.3 UK SRS:** a PS26/19 comply-or-explain obligation in the UK profile
  and pack.
- **W4.4 Hong Kong:**
  - New `HK` jurisdiction profile (HKEX climate, HK Taxonomy, HKSSA 5000,
    transition plan).
  - `frameworks/hk_taxonomy.py` screen (wraps the EU Taxonomy maths), also
    exposed as `framework_assess framework=hk_taxonomy`.
  - HKEX pack refreshed.
- **W4.5 AI provenance:** `impact/ai_provenance.py` stamps every output
  with one disclosure:
  - decision report (badge, appendix and footer, in en / zh-HK / zh-CN),
    and PDF through it;
  - IC memo (HTML and DOCX), DD report and questionnaire DOCX, shared v2
    footer, classic report and portfolio home;
  - XLSX "AI provenance" sheet, CSV, JSON and `summary.json`.
  - Claims carry `extracted_by`; `impact_report` accepts an `ai_usage`
    declaration.
- **W4.6 ISSA 5000:**
  - Assurance packs default to ISSA 5000 for periods beginning on or after
    2026-12-15, or HKSSA 5000 in HK (inferred from labels like "FY2027").
  - Packs carry a per-figure AI-use register; the ISSA 5000 pack does too.
- **W4.7 ECGT:** `greenwashing_detect` now reports possible ECGT/UCPD
  breaches (Annex I 4a/4c, Art 6(2)(d)). Shelved-GCD tests are reported
  separately as best practice.
- **W4.8 ISSB:** registry entries for Workforce-related Disclosures (alias
  "Human Capital") and the nature Practice Statement ED. TNFD is labelled
  "feeding ISSB".
- **W4.9 Asia rows:** Japan, China (MoF), Singapore, Australia, Hong Kong,
  UK and EU adoption rows refreshed with deep links and `last_verified`.
  The placeholder ISSB watch URL is fixed.
- **W4.10 SB 253:** obligations can carry a `fixed_due_date`. SB 253 shows
  at 2026-11-10 with a live calendar alert and a portfolio-home "needs
  attention" item. Watch-list rows carry `source_url`.

Not done:
- Pointing `xbrl_export` at the EFRAG 2026 draft taxonomy. It waits for
  the taxonomy files; the consultation closes 2026-11-11.
- Replacing ESRS screening rows with the Regulation's annex datapoint codes.
- ISSB nature mapping (out of scope until the ED text lands).
- Adding ISSA 5000 to the verifier-marketplace listings. Those are claims
  about real firms and need confirmation from them.

### Wave 5 — Platform hardening (weeks 6–16)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W5.1 | **Knowledge as data.** Move the standards registry, regulatory dates (5 modules → one `data/regulatory/*.yaml`), benchmarks (4 → one `BenchmarkProvider`) and the crosswalk (`cross_reference.py` merged into `concordance.yaml`) into versioned YAML. Every row has `as_of`, `source_url`, `last_verified`. A CI check fails on rows older than 180 days without re-verification. Fix the placeholder ISSB URL in `tracked_standards.yaml` | `standards_registry.py`, `regulatory_*.py`, `benchmarks.py`, `concordance.py` | L |
| W5.2 | **Methodology versioning.** Move scoring weights/thresholds (5D, SDG, greenwashing) into `data/methodology/v1.yaml`. Every output stamps `methodology_version` + config hash. A "Methodology" appendix is auto-generated from the YAML | `five_dimensions.py`, `sdg_mapper.py`, `greenwashing.py:268` | M |
| W5.3 | **Persistence.** A pluggable store (SQLite default, Postgres optional) with `tenant_id` for engagement workspace, audit trail, review queues, RBAC and radar queue. Auto-persist and restore on startup | `storage.py`, `engagements/workspace.py`, `tenancy.py` | L |
| W5.4 | **Retire `roadmap_v2.py`.** Dissolve it into the modules it duplicates (PCAF, jurisdictions, review queue, emission factors, crosswalk), keeping import shims for one release. Same treatment for `questionnaire_v2`/`sfdr_v2` naming | `roadmap_v2.py` + 9 importers | M |
| W5.5 | **Package rename & trim** (the deferred CLAUDE.md plan). Make `impact_vision` the real package. Drop `channels/` (5.5k LOC, no importers), `vim/`, `themes`/`voice`/`bridge`/`keybindings` from the wheel. Trim `force-include` | `pyproject.toml` | M |
| W5.6 | **Extraction quality.** Expand the `extraction_eval` gold set (outcome vs activity classification, units, decimals, SDG recall). Make the CI gate blocking (currently `continue-on-error`). Use the LLM extractor by default when a key exists | `extraction_eval.py`, `extractors/` | M |
| W5.7 | **Docs hygiene.** A generated `docs/reference/tools.md` and counts. CI asserts that README/CLAUDE.md numbers match code. Trim README to ≤850 lines. Rewrite `fund-manager-guide.md` as web-first task recipes. Add `.gitattributes` (LF). Fold the five untracked root strategy files into this roadmap and delete them | docs, CI | S |


**Wave 5 status (2026-10-06):** done on branch `v7-wave5`.

- **W5.1 Knowledge as data.**
  - Watch-list, jurisdiction profiles, regulatory packs, standards
    registry, benchmarks and the 61-concept crosswalk now live in YAML
    under `data/`.
  - Rows inherit file-level `as_of` / `source_url` and set their own
    `last_verified`. `scripts/check_knowledge.py` (CI) fails when a row has
    no source or is more than 180 days past its last verification.
  - The gate caught two stale packs on day one: US-CA-CLIMATE and EU-CSDDD,
    both re-verified. It also found that SB 261 was mis-coded as
    semi-annual (it is biennial).
  - `benchmark_provider.ImpactBenchmarkProvider` serves all four benchmark
    sets. The seed distributions are labelled `illustrative`, never
    "verified".
- **W5.2 Methodology versioning.**
  - Every 5D / SDG / greenwashing weight and threshold is in
    `data/methodology/v1.yaml`.
  - Assessments, 5D and greenwashing results, the report, IC memo, exports
    and `summary.json` carry `methodology_version` plus a `config_hash`.
    The appendix text is generated from the YAML.
  - Scores are unchanged.
- **W5.3 Persistence.**
  - New `state_store` (SQLite by default, Postgres optional, in-memory for
    tests).
  - The engagement workspace auto-saves and restores, and the tools use
    the persistent one. The audit trail keeps one hash chain across writers
    and restarts.
  - The radar and DDQ review queues and RBAC (`PersistentRBACStore`) are
    persisted too.
- **W5.4 Retire `roadmap_v2`.**
  - Its 56 helpers moved verbatim into the modules they duplicated, or into
    `ai_review` / `disclosure_packs` / `report_governance`.
  - `roadmap_v2`, `questionnaire_v2` and `frameworks.sfdr_v2` remain as
    deprecation shims until 0.18.
- **W5.5 Package.**
  - `impact_vision.*` is the supported import path: the same module objects
    via an alias finder. Console scripts use `impact_vision.cli`.
  - The wheel drops `channels/` and `vim/`.
- **W5.6 Extraction quality.**
  - The CI gate previously scored an empty stub. It now runs the production
    chain on an 18-document gold set covering claims, metrics, SDGs,
    categories and quantities.
  - The gate is blocking at F1 ≥ 0.95; the regex extractor measures 0.978
    after the follow-up SDG-hint fix.
    Three gold expectations that contradicted the methodology were fixed.
  - Extractor `auto` uses the LLM when `OPENAI_API_KEY` is set.
- **W5.7 Docs hygiene.**
  - Generated `docs/reference/tools.md` (checked in CI).
  - `tests/test_docs_counts.py` guards the README/CLAUDE.md numbers; it
    fixed 59 → 61 concepts and 10 → 22 framework modules.
  - README is 846 lines. The fund-manager guide is rewritten as web-first
    recipes. `.gitattributes` (LF) plus a one-time renormalisation.

Not done / deferred:
- **The physical move of the code to `src/impact_vision/`.** This waits for
  the 0.18 shim removal; until then `impact_vision` is the alias.
- **Dropping `themes` / `voice` / `bridge` / `keybindings` from the wheel.**
  The slash-command registry imports them, so those imports must become
  lazy first.
- **The "five untracked root strategy files" (W5.7).** They are not present
  in this repository.
- **SDG inference recall without explicit "SDG n" mentions.** It measured
  0.71. A follow-up fixed the inflection bug in the keyword hints; it is now
  0.89, and the gate was raised to 0.95.

---

## 5. Build order & releases

| Release | Target | Contents |
|---|---|---|
| **0.16.1** | +2 wks (late Oct 2026) | W0.1, W0.4, W0.6, W0.7, W0.8 + ESRS/VSME law status, UK SRS, SB 253 alert (W4 quick wins) |
| **0.16.2** | +4 wks | W0.2, W0.3, W0.5, W0.9 (trust fixes complete) |
| **0.17.0 "Effortless"** | +8 wks (early Dec 2026) | Wave 1 + W2.1/W2.2 on the impact report + W2.4 PDF + SFDR 2.0 EP variant + ISSA 5000/HKSSA framing (ahead of 2026-12-15) |
| **0.18.0 "Beautiful"** | +12 wks (Jan 2027) | Rest of Wave 2 (audiences, zh-HK/zh-CN, a11y CI, exports) + W3.1/W3.2 |
| **0.19.0 "Durable"** | +16 wks (Feb 2027) | Wave 5 + W3.3/W3.4 + EFRAG/ISSB taxonomy re-sync + ILPA template if final |

**Released (2026-10-07):** Waves 0–5 shipped together as **0.17.0
"Trusted, Effortless & Beautiful"** instead of the four increments above.
**0.18.0** removes the deprecated shims and physically moves the code to
`impact_vision`.

Re-run the regulatory scan (§2) monthly via `regulatory_radar`, and publish the
deltas as `docs/roadmap-updates-YYYY-MM.md`.

## 6. Success metrics

| Metric | Today | v7 target |
|---|---|---|
| Time from install to first HTML report (no API key) | not possible without SDK code | **< 5 min**, one command |
| Tool calls for deck → IC report (agent) | 7+ with re-typed fields | **1–2** |
| Tools exposed to a fund-manager agent | 89 | **≤ 40**, all typed |
| Pig-farm golden test: tracked claims / irrelevant risk areas | 0 / 3 | **≥ 5 / 0** |
| Installed-wheel vs source score parity | broken | **identical** (CI-enforced) |
| CSS/chrome systems for deliverables | 8 | **1** |
| Report first screen contains verdict + confidence | no | **yes**, all audiences |
| PDF page count, impact report | 20 (browser print) | **6–10**, native |
| Deliverables working offline | no (CDN) | **yes** |
| WCAG 2.2 AA (axe-core, light + dark) | not checked; failures | **0 serious violations in CI** |
| Languages | en | **en, zh-HK, zh-CN** |
| Reference-data rows with `as_of` + source | partial | **100 %** |
| Outputs stamped with methodology version | 0 % | **100 %** |
| Consultant work surviving restart | no | **yes** |

## 7. Out of scope for v7

- New measurement methods or frameworks beyond §2. The v6 backlog Tracks
  C/D/G–J continue only after Wave 0 lands.
- Hourly Scope 2 matching (waits for the GHG Protocol final).
- ISSB nature mapping implementation (waits for the ED text; prep only).
- A hosted SaaS / billing layer. W5.3 makes it possible but doesn't build it.
- Native mobile apps. Responsive web is the target.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Template rewrite (W2.1) regresses existing outputs | Golden HTML snapshots + screenshot diffs before porting. Port one deliverable at a time |
| Tool consolidation (W1.5) breaks existing prompts / MCP clients | Keep old tool names as thin deprecated aliases for one minor release, logged in CHANGELOG |
| Sector filtering hides relevant cross-sector questions | Universal question set always included. Add a "show all" toggle |
| Regulatory facts change mid-build (SFDR trilogue, ISSB nature ED) | Model them as variants with `status` flags. Monthly radar delta |
| zh translations of technical terms are wrong | Use official HKFRS / HKEX / MoF Chinese terminology. Native-speaker review before release |

## 9. Sources (regulatory delta, retrieved Oct 2026)

- ESRS/VSME OJ publication — Linklaters, <https://sustainablefutures.linklaters.com/post/102o1ou/eu-csrd-revised-esrs-and-voluntary-reporting-standard-are-published-in-the-offic>
- EFRAG ESRS XBRL taxonomy consultation — <https://www.xbrl.org/news/efrag-advances-the-revised-esrs-toward-a-digital-taxonomy/>
- SFDR 2.0 state of play — Debevoise <https://www.debevoise.com/insights/publications/2026/09/sfdr-20-recap-briefing>; HSF Kramer <https://www.hsfkramer.com/notes/esg/2026-posts/sfdr-2-comparing-the-commission-council-and-parliament-where-the-key-fault-lines-lie>
- FCA PS26/19 — <https://www.fca.org.uk/publications/policy-statements/ps26-19-aligning-listed-issuers-sustainability-disclosures-international-standards>
- EU AI Act Digital Omnibus — Lewis Silkin <https://www.lewissilkin.com/insights/2026/07/27/the-digital-omnibus-on-ai-enters-into-force-today-102nedo>
- HK Taxonomy Phase 2B consultation — <https://www.info.gov.hk/gia/general/202609/07/P2026090700249.htm>; CASG 2026-28 priorities <https://www.info.gov.hk/gia/general/202601/30/P2026012900428.htm>
- ISSA 5000 adoption — <https://www.iaasb.org/consultations-projects/issa-5000-adoption-and-implementation>
- ISSB September 2026 update — <https://www.ifrs.org/content/ifrs/home/news-and-events/updates/issb/2026/issb-update-september-2026.html>
- CARB SB 253 rulemaking — Mayer Brown <https://www.mayerbrown.com/fr/insights/publications/2026/08/california-climate-disclosure-laws-carb-finalizes-its-initial-rulemaking-resets-the-2026-deadline-and-previews-the-2027-framework>
- GHG Protocol Scope 2 feedback summary — <https://ghgprotocol.org/sites/default/files/2026-07/S2-ExecutiveSummary-PublicConsultation%20ummaryofFeedback-2026.07.29.pdf>
- ILPA metrics template refresh — <https://ilpa.org/news/portfolio-company-metrics-template-refresh/>
