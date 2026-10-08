# Changelog

All notable changes to Impact Vision are recorded here. **This is the
single source of truth for release history** — please do not duplicate
version banners, "What's new" blocks, phase status tables, or
verification matrices in `README.md`. See
[`CLAUDE.md`](CLAUDE.md#documentation-conventions-keep-readmemd-newcomer-focused)
for documentation conventions.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.18.0] - 2026-10-08 - Measured (roadmap v8 Waves 1–5, first pass)

Scores now say how much impact, for whom and how sure we are; a company is
followed from first deck to exit; every claim cites its page; and the
project ships like a product (PyPI/Docker pipeline, security gates).
`docs/roadmap-v8.md` lists what is done and what remains.

### Added — company record (roadmap v8 Wave 3)
- **Company record:** every assessment is filed on the company (pipeline
  stages sourcing → screening → DD → IC → invested → monitoring → exited).
  Expected impact before investment is kept as the expectation; assessments
  after investment are actuals, compared with it (within / below / above
  the expected range, variance %). Comments, corrections and IC approvals or
  declines (a reviewer name is required) are attributed and time-stamped.
- Web **Companies** tab and company view; `/api/v1/chat/companies…` API.
- **Portfolio home** splits portfolio from pipeline and totals expected
  impact in natural units; per-company Impact P50 and Evidence columns.
- **Excel / CSV KPI import:** drop a spreadsheet next to the deck; IRIS+ IDs
  or metric names become reported metrics (latest period wins, series kept,
  unmatched labels listed).
- **Page citations:** every claim from a PDF or PowerPoint carries its page /
  slide, shown in the evidence ledger (24/24 on the sample decks).

### Added — platform (roadmap v8 Wave 5)
- Versioned SQLite migrations (`PRAGMA user_version`); assessment history is
  kept instead of overwritten.
- **Ed25519-signed assurance manifests** (`[assurance]` extra): verifiers
  check with the public key and cannot forge; HMAC remains the fallback.
- `import openharness.impact` 1.6 s → 0.6 s (lazy tool loading).
- CI: Python 3.11/3.12/3.13, coverage floor 85 % for the impact engine, mypy
  on the v8 modules, pip-audit and bandit gates, weekly knowledge-freshness
  run. `release.yml` publishes tags to PyPI (trusted publishing) and GHCR;
  `Dockerfile` runs `serve-web` as a non-root user.

### Removed
- The deprecated `roadmap_v2`, `questionnaire_v2` and `frameworks.sfdr_v2`
  shims; import from the modules they re-exported.

### Security
- The legacy report header rendered company names with Jinja autoescape off
  (XSS); the claim verifier fetched document-supplied URLs without the SSRF
  guard. Both fixed; `utils/safe_fetch.py` is the one place that fetches
  untrusted URLs (every redirect re-checked).

### Fixed
- Company names from lowercase title words ("— Seed pitch") and Chinese
  titles; the installed wheel no longer needs numpy (methodology 2.0 uses
  the standard library).

### Added — methodology 2.0 (roadmap v8 Wave 1)
- **Expected impact with ranges.** `impact/expected_impact.py` reads the
  reported quantities (people reached, depth of change, tCO2e avoided, the
  funding ask) from the claims, skipping problem statements and keeping
  targets apart, and computes reach × depth × duration × (1 − deadweight) ×
  attribution × probability of success. Every factor's spread follows the
  NESTA level of the claim behind it; a seeded Monte Carlo gives
  P10 / P50 / P90 in depth-weighted person-years and tCO2e (and per US$1m
  raised when the ask is stated). Parameters, all labelled illustrative
  until calibrated, are in `data/methodology/v2.yaml`.
- **Evidence quality (0–100)** and **data completeness** are reported next
  to impact, never multiplied in.
- **Gate 2.0:** Ready for IC / Evidence plan required / Fails thesis.
  Failing needs something found (a greenwashing finding, an exclusion); an
  evidence plan lists the inputs that drive most of the uncertainty and how
  to close them. The report verdict, KPI tiles, "What would change our
  mind", a new "Expected impact" section (all audiences, en / zh-HK /
  zh-CN), the IC memo (HTML and Word), the CLI summary, the web card and the
  portfolio home all use it. `IMPACT_VISION_METHODOLOGY_VERSION=1` restores
  the v1 verdict.
- Perturbation and gaming tests (W2.5): scaling reach scales impact,
  buzzwords change nothing, a comparison group narrows the range and nets
  out deadweight (`tests/test_v8_methodology2.py`).

### Added — standards (roadmap v8 Wave 4)
- **Machine-readable AI marking (EU AI Act Art 50, ahead of 2026-12-02).**
  Every output carries the IPTC Digital Source Type (`algorithmicMedia` for
  the rules engine, `compositeWithTrainedAlgorithmicMedia` when an LLM
  extracted, tagged or drafted): HTML `<meta>` + schema.org JSON-LD
  (report, IC memo, DD report, portfolio and engagement pages), PDF document
  info + XMP `Iptc4xmpExt:DigitalSourceType`, Word and Excel core
  properties, and `ai_marking` in `summary.json`.

### Changed
- The 5D "sector benchmark" is labelled an illustrative prior: GIIN
  publishes no Five Dimensions scores (W1.8, first step).

### Fixed
- NESTA levels were described wrongly (an RCT is level 3, causality, not
  level 5). Comparison groups, matched comparisons and 對照研究 / 对照组 are
  now recognised as level 3 evidence.

## [0.17.2] - 2026-10-08 - Secure & honest (roadmap v8 Wave 0)

The post-v7 review found that the local server could be driven by any web
page, that missing data was scored as greenwashing, and that advice did not
generalise beyond the three sample decks. This release fixes all three. See
`docs/roadmap-v8.md` §4 Wave 0.

### Security
- **Secure by default (W0.1).** Without `IMPACT_VISION_API_KEY` the server
  refuses requests whose `Host` isn't local (stops DNS rebinding) and
  cross-site state-changing requests / WebSocket handshakes (Origin check).
  CORS is same-origin by default (was `*`); opt in with
  `IMPACT_VISION_CORS_ORIGINS`. Binding beyond loopback without a key mints
  a one-time launch token. The WebSocket token can travel as a subprotocol
  and is compared in constant time.
- Repointing a provider profile that holds a saved key now requires the key
  again, so a changed endpoint can never receive the old key.
- **Guarded routes (W0.2).** Legacy `/api/v1/pitch-deck` and
  `/api/v1/decision-workflow` refuse server paths/URLs like
  `/api/v1/tools/*`; deck URL fetches re-validate every redirect; webhooks
  must target public addresses.
- **Contained agent (W0.3).** Web "fund" sessions may read only the
  workspace and upload folders (kept across permission changes);
  `full_auto` can't be set over the web API. Uploads go to the web home
  (`~/.openharness/web-uploads`) with a document-type allow-list; downloads
  serve report/document types only and never hidden files.

### Changed — methodology 1.2.0
- **Absence is not a finding (W0.4).** Missing verification, missing
  negative-impact metrics or few metrics can no longer make a greenwashing
  finding: without a conduct signal (vague, unquantified claims) the score
  is capped below the finding threshold and labelled an evidence gap.
  Disclosed risk controls and accreditations count. One finding threshold
  (60) and pass line (40) in `data/methodology/v1.yaml`, used by the gate,
  verdict engine, portfolio home and display; IC-gate defaults moved there
  with a written rationale.
- **Whole document (W0.5).** Scorers read the full document minus
  problem / market / team / ask sections instead of the first 1,000
  characters; problem statements no longer cost Risk. 5D is clamped to
  1–5. SDG keywords match whole words; own-emissions disclosure is no
  longer SDG 13, corporate governance no longer SDG 16, a business
  partnership no longer SDG 17; financial inclusion leads with SDG 1;
  geography no longer raises relevance. Spanish, French, Portuguese and new
  Chinese keyword maps are now used.
- **Relevant advice (W0.6).** Metric suggestions are ranked by sector core
  set, themes, goal specificity and document wording (they were
  alphabetical); generic metrics tagged to most themes no longer appear as
  dimension gaps. Unknown sectors get the universal core set instead of the
  microfinance default; technology, retail, tourism and transport sets added.

### Added
- Word (`.docx`) and PowerPoint (`.pptx`) decks; several files about one
  company are assessed together (CLI `assess_files`, web drag-and-drop).
- Web "Correct and re-run": fix the company name, sector, geography or
  stage on a result card and re-score the same files.
- Sector/geography detection: waste & circular, retail & fashion,
  manufacturing, tourism, housing, heat pumps; Hong Kong, Singapore, UK, EU
  countries and more, including Chinese place names.
- Portfolio-home deadlines follow the fund's domicile
  (`IMPACT_VISION_FUND_DOMICILE`) plus where its companies operate.
- DD questions for the investment team (`ask: fund`) are no longer sent to
  founders or counted in coverage.
- Ten golden decks across sectors, regions and Chinese
  (`tests/golden_decks/`, `tests/test_v8_golden_decks.py`).
- Pre-filled provider profiles (see below) and Claude 5.5 defaults.

### Fixed
- `/health` alias; "122 questions" in the DD tool text; one AI disclosure
  per report (the footer links to the appendix); same gate label in the
  web panel and card.

### Added (provider presets)
- Pre-filled provider profiles: OpenAI, OpenRouter, DeepSeek, Alibaba Qwen
  (DashScope), Mistral, xAI (Grok), Groq, Together AI, Ollama (local, no key)
  and a Custom endpoint (any OpenAI-compatible URL). Each has its base URL,
  a default model and model suggestions filled in, and keeps its key in its
  own slot. Keys can also come from `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`,
  `XAI_API_KEY` and the other provider env vars.
- Web Settings groups the profiles (Anthropic / Hosted / Subscriptions /
  Local & custom), shows "add key" vs ✓, lists models for the chosen
  provider and names the env var you can set instead of pasting a key.
  `impact-vision setup` offers the same presets.
- Endpoints on `localhost` (Ollama, LM Studio, vLLM) work without a key.

### Changed
- Claude defaults move to the 5.5 family: `sonnet` → `claude-sonnet-5-5`,
  `opus` → `claude-opus-5-5`; new installs default to `claude-sonnet-5-5`.
  A model you pinned explicitly is left as is.

### Fixed
- `/version` slash command reported "OpenHarness 0.1.6" (wrong package lookup);
  it now prints the installed Impact Vision version. The OpenAI-compatible
  client's `User-Agent` no longer hard-codes `impact-vision/0.14.0`.
- Evidence ledger: fixed column widths so the claim text no longer collapses
  to one word per line in the PDF.
- 5 Dimensions notes read "1 metric reported · 1 of 16 reference metrics"
  instead of "Reporting 1 metrics (1 theme-specific, 16 available)".
- Report masthead keeps the generated date on one line on mobile.
- zh-HK / zh-CN language note now says DD questions are shown in the original.

### Docs
- Removed four unused images from `docs/images/`; regenerated the demo bundle
  and every screenshot. Section screenshots that
  are height-capped are cut at a row boundary, not mid-row.

## [0.17.1] - 2026-10-07 - Report styling pass

Every deliverable in `demo/` was reviewed in the browser, in Word (via a
LibreOffice render) and in Excel, and the issues found were fixed at the
source.

### Fixed
- **Broken `--warning` token in the IC memo and DD report.** The shared
  stylesheet aliased `--warning` to itself, which made it invalid.
  Warning-coloured callouts, tiles and bars had been rendering black or
  transparent.
- **IC memo tones.** Data-gap checks show an amber "Needs data" instead of
  a red FAIL. The callout reads "Evidence to collect before IC" rather than
  "Blocking failures". The recommendation is green only for a pass. The gate
  tile counts "need data".
- **IC memo Word file.** It used to contain literal `**asterisks**` and
  pipe-text tables. It now has real bold/italic runs, Word tables with shaded
  headers, brand headings and a page-numbered footer. The DD questionnaire
  `.docx` shares the same house style.
- **Grade colours** use the ink tokens: the C-grade yellow was 1.9:1
  contrast.

### Changed
- **Decision report.**
  - The evidence ledger names every mapped IRIS+ metric, and its evidence
    pills no longer wrap.
  - Greenwashing components at or over the finding threshold are drawn in
    the warning colour, with a ▲ marker and legend entry.
  - Near-duplicate action-plan rows are merged, and bare IRIS+ IDs are named.
  - "Other goals" are sorted.
- **Shared styles.** Flat token bars instead of gradients. Tile accents only
  when the tile carries a status. Pills never wrap. Callout lists sit inside
  the box.
- **DD report** dimension tags are readable ("How much", not `HOW_MUCH`).
- **Investee portal** sits in a centred 820px column with token colours
  (dark-mode safe) and focus rings.
- **Demo and screenshots regenerated.** The visual QA covers the
  engagements page.

## [0.17.0] - 2026-10-07 - "Trusted, Effortless & Beautiful"

Roadmap v7 (`docs/roadmap-v7.md`), Waves 0–5 plus follow-ups, shipped as one
release. The 0.16.1 / 0.16.2 / 0.18 / 0.19 increments planned in the roadmap
were folded into it. Highlights:

- **Trust fixes:** claims kept as evidence, sector-aware DD, plausible SDG
  scores, an insufficient-evidence verdict instead of false negatives, and
  escaped user text.
- **First run:** `impact-vision demo` / `assess`, `assess_deal` +
  `assessment_id`, the fund tool profile, and lean installs with extras.
- **Reports:** a decision-first report on one design system, five audiences,
  zh-HK / zh-CN, Chromium PDF, IC memo `.docx`, accessibility CI, and
  XLSX/JSON/CSV exports.
- **Surfaces:** REST / MCP / console generated from the tool registry; the
  web app with deck analysis, report viewer, share links, portfolio home and
  engagement view.
- **Standards currency (Oct 2026):** revised ESRS / VSME law, SFDR 2.0
  variants, UK SRS, Hong Kong profile + taxonomy, AI-provenance disclosure on
  every output, ISSA / HKSSA 5000, ECGT, SB 253 alert.
- **Platform:** sourced YAML knowledge with a freshness gate, a versioned
  methodology stamp, persistent consultant state, a real extraction
  benchmark gate, the `impact_vision` import path, and generated docs.

Upgrade notes:
- **Scores move (methodology 1.1.0).** The per-SDG core metric sets were
  rebuilt. Previously about half the IDs pointed at the wrong IRIS+ metric:
  "GHG emissions avoided" was listed as `OI4112` (Scope 1), and
  "renewable energy generated" as `OI1479`. Own-footprint metrics (Scope 1/2
  GHG, water consumed) and footprint-only sentences no longer count as SDG 13
  contribution.
  - Effect on the samples: the solar company now leads with SDG 7, and the
    microfinance lender with SDG 1 instead of SDG 13.
  - Reports carry the new methodology version and hash, so earlier reports are
    distinguishable.
- Assurance packs default to ISSA 5000 for periods from 2026-12-15.
- `roadmap_v2`, `questionnaire_v2` and `frameworks.sfdr_v2` are deprecated
  shims, to be removed in 0.18.
- `ImpactVision()` uses the LLM extractor when `OPENAI_API_KEY` is set
  (`IMPACT_VISION_EXTRACTOR=regex` keeps it deterministic).
- Consultant state is written to `~/.impact-vision/state.db`
  (`IMPACT_VISION_STATE_STORE=memory` disables it).

### Added — follow-ups after Wave 5

- **Engagement view** (the W3.2 deferral, unblocked by W5.3 persistence).
  - `GET /api/v1/chat/engagements[/view]` and an **Open engagements** button
    in the chat panel.
  - Shows per-engagement status, deliverable and checklist completion,
    overdue items and items due within 14 days (`impact/engagement_home.py`).
- **Persisted evidence-review queues.**
  - `evidence_review` takes `queue_name`; `list_review_queues()` is new.
  - The portfolio home lists pending items from every queue (radar, DDQ
    drafts, deal queues).

### Fixed

- **Engagement view completion percentages** showed 0% because the model
  fractions were not scaled. Engagements without a checklist now say so.
- **Demo and screenshots regenerated.** The README shows the engagement view
  and SDG alignment. `scripts/capture_screenshots.py --seed-web` makes the
  web-app shots reproducible.
- **Data-room bundle defaults cite correctly labelled IRIS+ IDs.**
  - `OI4112` was used as "beneficiaries"; it is Scope 1 GHG.
  - `PD5833` was used as "GHG"; it is affordable housing.
  - Sample benchmark observations and the website teaser had the same
    mistake.
  - A guard test now checks that ID and label agree.
- **The portfolio home route includes Hong Kong deadlines by default.**

### Added — v7 Wave 5: platform hardening

- **Knowledge as data (W5.1).**
  - `data/regulatory/{watchlist,jurisdictions,packs}.yaml`,
    `data/standards_registry.yaml` and `data/benchmarks.yaml`; the crosswalk
    is folded into `data/concordance.yaml`.
  - `impact/knowledge.py` adds provenance inheritance and
    `freshness_report()`. `scripts/check_knowledge.py` is a CI gate (180
    days).
  - `impact/benchmark_provider.py` is one provider for every benchmark set.
- **Methodology versioning (W5.2).**
  - `data/methodology/v1.yaml` and `impact/methodology.py`.
  - `methodology_version` + `config_hash` appear on assessments, 5D,
    greenwashing, the report, IC memo, XLSX/CSV/JSON and `summary.json`.
  - `IMPACT_VISION_METHODOLOGY` selects a custom file.
- **Persistence (W5.3).** `impact/state_store.py` (SQLite default,
  Postgres, memory). The engagement workspace, audit trail, radar/DDQ review
  queues and `PersistentRBACStore` survive restarts. Configure with
  `IMPACT_VISION_STATE_STORE`, `IMPACT_VISION_STATE_DB` and
  `IMPACT_VISION_STATE_DSN`.
- **Extraction (W5.6).**
  - Real benchmark over 18 gold docs, with a blocking CI gate at F1 ≥ 0.95
    (measures 0.978).
  - SDG keyword hints now match inflections ("emissions", "recycling").
  - The regex extractor reads "500 low-income customers".
  - New mapper rules: Scope 1 (OI4112) and jobs created (PI3687), with rule
    priority and `none_in_sentence`.
  - Extractor `auto` picks the LLM when `OPENAI_API_KEY` is set
    (`IMPACT_VISION_EXTRACTOR` overrides).
- **Docs (W5.7).**
  - `scripts/build_tool_reference.py` → `docs/reference/tools.md`.
  - `tests/test_docs_counts.py`.
  - Web-first `docs/fund-manager-guide.md`.
  - `.gitattributes`.

### Changed

- **`impact_vision` is the supported import path (W5.5).**
  - Console scripts are `impact_vision.cli:app`.
  - The wheel excludes `openharness/channels` and `openharness/vim`.
- **`roadmap_v2` helpers moved (W5.4).**
  - They now live in `investee_collection`, `ai_review`,
    `climate_accounting`, `frameworks.pcaf`, `disclosure_packs`,
    `regulatory_calendar` (`DISCLOSURE_PROFILES`), `cross_reference`,
    `standards_registry`, `report_governance`, `contribution`,
    `exit_impact`, `portfolio_nlq` and `regulatory_radar`.
  - `questionnaire_v2` → `questionnaire_branching`; `frameworks.sfdr_v2` →
    `frameworks.sfdr_recast`.
- **`ImpactVision()` defaults to `extractor_id="auto"`.**
- **SB 261 filing cadence corrected to biennial** in the US-CA-CLIMATE pack.
- **SFDR 2.0: both classifiers read `data/regulatory/sfdr2.yaml`.**
  - ESG Basics now excludes tobacco in the holdings check.
  - Sustainable applies the Paris-aligned benchmark exclusions.
  - Transition applies the fossil-expansion and coal phase-out exclusions.
  - The label is "ESG Basics" (was "ESG collection").

### Deprecated

- `openharness.impact.roadmap_v2`, `openharness.impact.questionnaire_v2` and
  `openharness.impact.frameworks.sfdr_v2` (DeprecationWarning; removed in 0.18).

### Added — v7 Wave 4: standards currency

Facts re-verified 2026-10-06; see `docs/roadmap-v7.md` (Wave 4 status) for
sources and the five corrections to the original §2 table.

- **ESRS / VSME are law (W4.1).**
  - Revised ESRS metadata names Delegated Reg (EU) 2026/1563 and computes
    `legal_status` from the OJ, entry-into-force and application dates.
    Generated `*-DRAFT-nnn` filler rows were removed.
  - VSME (Reg 2026/1560) gains `VSME_LEGAL_BASIS`, a template
    (`generate_investee_questionnaire_schema(sector="vsme")`), and
    `vsme_basic` / `vsme_comprehensive` data-request packs.
  - The value-chain cap is a hard rule: with `requester_in_csrd_scope=True`
    and `counterparty_employees ≤ 1000`, fields outside VSME become
    voluntary.
- **SFDR 2.0 (W4.2).** `SFDR2Input.position`
  (`commission` / `council` / `parliament`) and a new
  `check_sfdr2_impact_claim`. "Impact" wording needs:
  - Transition/Sustainable (Art 7/9) status;
  - a pre-defined objective;
  - a theory of impact (a passing `toc_builder` validation counts);
  - measured outcomes (5D `evidence-based` counts).

  Council ramp-up relief is now modelled only for the Council text.
- **UK SRS (W4.3)** comply-or-explain obligation (FCA PS26/19) in the UK
  profile and pack.
- **Hong Kong (W4.4).**
  - New `HK` jurisdiction profile: HKEX climate, HK Taxonomy, HKSSA 5000,
    transition plan.
  - New `frameworks/hk_taxonomy.py` plus `framework_assess
    framework=hk_taxonomy`.
  - Jurisdiction aliases ("Hong Kong", "United Kingdom", …). The portfolio
    home includes HK deadlines by default.
- **AI-provenance disclosure on every output (W4.5, EU AI Act Art 50).**
  - New `impact/ai_provenance.py`.
  - The decision report shows a localised badge, an appendix table and a
    footer line. The IC memo (HTML/DOCX), DD outputs, the shared v2 footer,
    the classic report and the portfolio home carry the disclosure.
  - XLSX gains an "AI provenance" sheet; CSV/JSON/`summary.json` include it.
  - `ImpactClaim.extracted_by` records the extractor.
  - `impact_report` takes an `ai_usage` declaration.
- **ISSA 5000 framing (W4.6).**
  - `recommended_assurance_standard()` picks ISSA 5000 for periods from
    2026-12-15, HKSSA 5000 in HK, and ISAE 3000/3410 for earlier periods.
  - `build_assurance_pack` defaults to it and infers the period from labels
    like "FY2027".
  - Packs carry a per-figure `ai_use` register.
- **ECGT is operative (W4.7).**
  - `assess_green_claims_compliance` splits `ecgt_breaches` (UCPD Annex I
    4a/4c, Art 6(2)(d)) from `best_practice_gaps` (shelved GCD).
  - `greenwashing_detect` now reports it; it previously had no caller.
- **ISSB / Asia (W4.8–W4.9).**
  - Registry entries for revised ESRS, VSME, ISSA 5000, ECGT, UK SRS, the
    HK Taxonomy, ISSB Workforce-related Disclosures and the nature ED.
  - TNFD is labelled "feeding ISSB".
  - Refreshed adoption rows (Japan, China MoF, Singapore, Australia, HK,
    UK, EU) carry deep links and `last_verified`.
- **SB 253 alert (W4.10).**
  - Obligations can carry a `fixed_due_date` / `due_offset_days`. SB 253 is
    due 2026-11-10 and raises calendar `alerts` and a portfolio-home
    attention item.
  - The watch-list was refreshed (VSME, ESRS entry into force, XBRL
    consultation, AI Act dates, HKSSA 5000, UK SRS, SSBJ, Singapore) and
    every row has a `source_url`.

### Changed

- Assurance packs without an explicit `standard` now default to ISSA 5000
  for current/future periods (ISAE 3000 remains for periods before
  2026-12-15).
- `load_simplified_datapoints()` returns only named disclosure rows; callers
  that relied on the 430-row padded fixture will see fewer rows.

### Added — v7 Wave 3: one product, many surfaces

- **Registry-generated surfaces (W3.1).** New `impact/surfaces.py` reads the
  fund-profile tool registry once and feeds every surface.
  - **REST**: `GET /api/v1/tools` (add `?schemas=true` for JSON schemas),
    `GET`/`POST /api/v1/tools/{name}` runs any of the 48 impact tools with
    pydantic validation (422 on bad input), and `GET /api/v1/playbooks`.
    Remote callers cannot set `file_path`, `url`, `output_path`,
    `output_dir` or `thesis_path` (the server would read its own files or
    fetch URLs) unless `IMPACT_VISION_API_ALLOW_PATHS=1`. The OpenAPI version
    now comes from the package instead of a hard-coded 0.16.0. New
    `tool_complete` webhook event.
  - **MCP**: every tool without a hand-written wrapper (25, including
    `assess_deal`, `impact_advisor`, `engagement_suite` and `toc_builder`) is
    registered with its real typed schema (enums, defaults, descriptions),
    and each of the 10 advisor playbooks is an MCP prompt.
  - **Console**: `/console` adds a schema-driven form for every registry
    tool, labelled by task area, next to the existing named endpoints.
- **Web chat as the primary app (W3.2).** New `web/reports_api.py`.
  - **Analyze a pitch deck** is the first welcome card (click or drop a
    file). It runs the offline pipeline, with no model or API key needed,
    and shows a verdict card: gate, recommendation, 5D, greenwashing, top
    SDGs, evidence, and downloads (report, IC memo + .docx, DD report +
    questions .docx, data .xlsx/.csv, summary .json). "Ask the agent"
    pre-fills a prompt with the new `assessment_id`.
  - **Inline report viewer**: a full-screen, sandboxed viewer with
    audience, language (en / zh-HK / zh-CN) and theme switches, plus "Open
    in new tab". Reports persist in a new **Reports** tab.
  - **Share**: `POST /api/v1/chat/reports/{id}/share` returns a signed,
    expiring (1–90 days) read-only link at `/shared/{token}`. It defaults to
    the LP edition and sends `no-store`, `noindex`, `no-referrer` and a
    strict CSP. Links are signed with `IMPACT_VISION_SHARE_HMAC_KEY` /
    `IMPACT_VISION_HMAC_KEY`, or a random per-install secret (mode 0600) —
    never the public development key, which would make links forgeable.
    Deleting a report revokes its links.
  - `/api/v1/chat/assess` only reads files from the uploads folder.
  - `pipeline.save_bundle()` is shared by `assess_deal` and the web app.
- **Streamlit dashboard repositioned as the no-LLM workbench (W3.3).**
  - Company Assessment now starts from **a pitch deck or memo**: upload a
    PDF / Word / Markdown / text file and get the IC gate, 5D, greenwashing
    and SDG tiles, the embedded decision report (edition and language
    switches), and HTML / Excel / CSV / slim-JSON downloads.
  - The "data I enter" path uses a sector dropdown (the 18 benchmark
    sectors), an SDG picker by goal title, and a searchable IRIS+ metric
    picker by name with a value table, instead of free-text IDs and
    `ID=value` lines. New `dashboard/forms.py` holds the testable helpers.
  - `/console` stays as the power-user tool runner (now generated from the
    registry, W3.1) rather than being retired.
- **Portfolio home (W3.4).** New `impact/portfolio_home.py` and
  `portfolio_home.html.j2` build one page per fund from saved assessments.
  - Headline tiles: companies, average 5D, IC-ready, greenwashing flags,
    deadlines in the next 90 days.
  - Pipeline by IC gate, plus CRM stages when the AssessmentStore has them.
  - A 5 Dimensions + material-SDG **heat-map**. It uses the validated
    ordinal ramp, with black or white ink per step checked by axe in both
    themes.
  - **Regulatory deadlines** for the fund's jurisdictions (SFDR, CSRD/ESRS,
    California SB 253/261, UK SDR, …).
  - **Evidence to review**: AI-extracted claims under 50% confidence.
  - **Needs attention**: stale (>180 days), data-limited and
    greenwashing-flagged companies.
  - In the web app: **Reports → Open portfolio home** (newest report per
    company), served at `GET /api/v1/chat/portfolio/view`. The demo writes
    `demo/portfolio_home.html`, which the gallery links to. It is covered by
    the axe / responsive QA suite.

### Added — v7 Wave 2: report design system & decision-first deliverables

- **Decision-first impact report (W2.1–W2.3).** New default HTML layout
  (`report_templates/decision_report.py`):
  - Order: verdict card (Proceed / Conditional / Not IC-ready — insufficient
    evidence / Do not proceed, with the top three reasons and a confidence
    line) → four stat tiles → "what would change our mind" → 5 Dimensions →
    SDG alignment → evidence ledger → greenwashing review → risks → action
    plan → methodology and glossary.
  - Material SDGs only. The other goals are listed as context.
  - Every claim and metric is shown with its NESTA level, evidence signals
    and origin (reported / extracted / derived).
  - One de-duplicated action plan, with sector-specific first actions
    instead of "Revenue, Total Clients".

  Built on one design system:
  - `design/tokens.css`: the validated data-viz palette, with dark mode
    selected per surface and every text token at WCAG AA or better.
  - `design/report.css`, plus a Jinja2 template with autoescaping.
  - HTML/CSS bar charts with benchmark ticks and threshold lines. Each
    chart has an `aria-label` and a table twin.
  - No Plotly or CDN: the report works offline, is about 30 KB instead of
    about 150 KB, and has a print stylesheet that expands every table.

  Audience variants (`full` / `ic` / `lp` / `regulator` / `public`) are
  declarative `ReportSpec`s, and gate and greenwashing content is omitted
  from the HTML (methodology and glossary included). White-label branding
  only accepts a hex colour and an https/data logo.

  `impact-vision assess`, `demo` and `impact_report` (`style="decision"`)
  use it. `style="classic"` keeps the old report for one release.
- **IC memo, DD report and investee portal share the tokens.** `report_v2`
  now maps its variable names onto `design/tokens.css`, so every deliverable
  has the same palette and type. They gain real dark mode
  (`prefers-color-scheme`, or `data-theme="dark"` when rendered with
  `theme="dark"`), and the gradient hero becomes the same masthead as the
  impact report. The IC-gate tile reads "NOT READY" for insufficient
  evidence instead of overflowing.
- **Print & PDF (W2.4).** `report_templates/pdf.py` prints any deliverable
  with headless Chromium (new `[pdf]` extra, or set
  `IMPACT_VISION_CHROMIUM`), falling back to WeasyPrint. Pages are A4 with a
  title and page-number footer. `impact-vision assess --pdf` writes PDFs of
  the impact report and IC memo; `impact_report output_format="pdf"` uses
  the same path, or saves print-ready HTML with an install hint. In print,
  cards may split across pages (rows and tiles don't), chart table twins
  stay on screen and the glossary prints expanded. The pig-farm impact
  report is 9 A4 pages (was 20 via browser print), the IC memo 5.
  Deliverables now include the IC memo as `.docx` when python-docx is
  installed (`[office]`).
- **Traditional and Simplified Chinese reports (W2.5).** `--lang zh-HK` /
  `zh-CN` on `assess`, and `lang=` on `impact_report` and
  `render_decision_report`. Covered: every label, verdict, gate reason,
  greenwashing class, confidence level, SDG name (official UN Chinese
  titles) and common sector name. Fonts put the right CJK face first
  (PingFang / Noto Sans HK·TC vs SC), and `<html lang>` is set. Quoted
  claims, engine recommendations and DD questions stay in the source
  language, and the report says so. Aliases like `zh_hk`, `zh-Hant` and
  `zh` resolve automatically.
- **More graphical reports.**
  - Masthead with a company monogram and a verdict pill.
  - Headline tiles with mini-visuals: a 5D meter, the official SDG badge, a
    greenwashing meter with status colour and a 60 threshold tick, and an
    evidence strip of claims by NESTA level (validated ordinal blue ramp,
    light and dark).
  - New **Impact at a glance** section: a 17-wedge SDG wheel (material
    goals in official colours, with the count in the centre) next to ranked
    score bars, and an impact-pathway flow (What they do → Outputs →
    Outcomes → Targets) built from the extracted claims.
  - NESTA pips and verified-evidence chips in the ledger, section icons,
    and priority badges in the action plan.
  - All inline SVG/CSS, so it stays offline and print-ready.
- **Demo bundle, screenshots and README refreshed.**
  - `demo/` is regenerated by the rewritten `demo/generate_demo.py`. It
    produces per-company folders for the three fictional sample decks:
    HTML and PDF impact reports and IC memos, Word files, DD reports and
    JSON summaries.
  - The pig farm adds LP, public, dark, white-label, zh-HK and zh-CN
    editions plus the investee portal.
  - A redesigned gallery uses the shared design system.
  - New `scripts/capture_screenshots.py` refreshes `docs/images` and
    `demo/screenshots` from the bundle, including the browser chat UI.
  - README revamp: a hero screenshot, a 60-second quick start, a 14-image
    screenshot grid (browser chat, report sections, PDF, Chinese, dark,
    mobile, IC memo, DD report, portal, gallery, terminal agent), a
    task-based "What it does", and a condensed install section (Windows
    PATH help moved to `docs/install-troubleshooting.md`).
  - Retired the classic-report screenshots and `docs/screenshots/`.
  - `examples/sample_impact_report.html` is now a decision-first report.
- **Accessibility & responsive QA in CI (W2.7).** New `tests/visual` runs
  every deliverable in Chromium: impact report (all audiences, zh-HK, zh-CN,
  dark), IC memo, DD report, investee portal and gallery.
  - axe-core must report no serious or critical violations, in light and dark.
  - There must be no horizontal scrolling at 390, 1024 and 1440 px.
  - The tests skip locally without Playwright and run in the new
    `report-qa` CI job.

  Fixes the checks found:
  - SDG pills use a colour swatch with neutral text, and numeric SDG badges
    use large text with black or white ink chosen per colour (white failed
    on SDGs 2, 6, 7, 11, 12 and 15).
  - Footer links are underlined in the link colour, and dark-mode red text
    uses the text-safe red.
  - The duplicate `<main>` landmark is gone from the IC memo and DD report.
  - Gallery navigation is labelled.
  - Wide tables scroll inside themselves on phones.
- **Better data exports (W2.8).** New `impact/exports.py` is shared by
  `impact_report` and the CLI deliverables.
  - **XLSX**: Summary, 5 Dimensions, SDG Alignment, Gap Analysis, Claims,
    All figures and Methodology sheets. Headers are frozen and filtered,
    columns are sized, and scores and reported values are real numbers
    (`1,200 tCO2e` becomes 1200 with the unit in its own column).
  - **JSON** carries `schema_version` and `export_mode`. `slim=True` drops
    evidence chains, IRIS+ definitions and the duplicate `sdg_alignment` key
    (pig farm: 160 KB to 27 KB).
  - **CSV** keeps the `Section, Metric, Value, Details` display columns and
    adds `Numeric`, `Max` and `Unit`, plus the greenwashing score.
  - `assess` / `demo` deliverables now include `*_data.xlsx` and
    `*_data.csv`.
- **Browser chat polish.**
  - A friendly setup card replaces the red monospace "No API credentials"
    error, and points to the offline `demo` / `assess` commands.
  - The header says "no model configured" instead of "connected".
  - "Screen a pitch deck" is the first starter card.
  - The REST `/health` endpoint reports the real version and tool count
    instead of a hard-coded 0.15.0 / 39.

### Added — v7 Wave 1: effortless first run

- **`impact-vision demo` (W1.1).** Assesses three bundled, fictional sample
  pitch decks (PDF: pig farm / Malaysia, pay-as-you-go solar / Kenya,
  microfinance / Sub-Saharan Africa) offline, with no API key, and opens a
  results gallery that links each company's impact report, IC memo, DD
  report, DD questionnaire and JSON summary. It runs in about 3 s and works
  from a pip-installed wheel (checked in the `wheel-smoke` CI job). Deck
  sources live in `data/sample_decks/*.md`; rebuild the PDFs with
  `scripts/build_sample_decks.py`.
- **`impact-vision assess <file>` (W1.2).** One pitch deck / memo (`.pdf`,
  `.txt`, `.md`) in; impact report, IC memo, DD report, DD questionnaire and
  summary out. Options: `--sector`, `--geography`, `--name`,
  `--audience full|ic|lp|regulator|public`, `--out-dir`, `--json`, `--open`.
  Built on the new `impact.pipeline` module (`assess_document`,
  `assess_file`, `write_deliverables`). The examples/demo scripts now reuse
  it instead of hand-assembling the pipeline.
- **`assess_deal` agent tool + `assessment_id` hand-off (W1.3).** One tool
  call runs the full offline screen on a pitch deck or memo, optionally writes
  the reports, saves the result and returns an `assessment_id`.
  `impact_report`, `sdg_mapper`, `five_dimension_assess`, `gap_analysis` and
  `greenwashing_detect` accept that id: empty fields (name, description,
  sector, geography, themes, metrics, SDG claims, extracted claims) are filled
  from the saved assessment, and explicitly passed fields win. `company_name`
  is now optional on those tools when an `assessment_id` is given. The
  `deal_screening` playbook drops from seven tool calls to three. The impact
  tool count is 53.
- **Fund-manager tool profile (W1.4).** `create_default_tool_registry(profile=
  "fund")` exposes the impact tools plus safe helpers (read, glob, grep, web
  search/fetch, ask-user, to-do list, skills, tool search): 62 tools instead
  of 90, and no bash, file writes, worktrees, plan mode, tasks, sub-agents,
  cron or teams. The web chat defaults to it. The terminal agent keeps the
  `developer` profile. `IMPACT_VISION_TOOL_PROFILE` overrides either.
- **`engagement_suite` is discoverable and validated (W1.5, part 1).** Its 65
  actions took an untyped `payload`, so agents guessed keys and typos were
  silently ignored. The new `engagement_suite_catalog` derives each action's
  payload keys from the dispatcher source (including fields of the pydantic
  models a payload is handed to), so it can't drift. `action='describe'` lists
  actions by area with their keys. Unknown keys are rejected with the
  accepted list. The tool description now names the areas instead of
  "Tracks 3-10".
- **Duplicate tools merged (W1.5, part 2).** A generic `tools/impact/merge.py`
  folds one tool into another with a typed union schema and unchanged
  behaviour. Each absorbed tool lives on as actions of the kept tool:
  - `beneficiary_feedback` → `stakeholder_voice` (`feedback_*`)
  - `lp_ddq_export` → `ddq_responder` (`template_*`;
    `output_format` → `template_output_format`)
  - `regulatory_radar` → `regulatory_calendar` (`radar_*`)
  - `guided_assessment` → `pipeline` (`guided_*`)
  - `document_analysis` → `pitch_deck_analyze` (`compare_documents`,
    `detect_changes`, `verify_claims`; default `analyze`)

  The old names stay registered for one release as `[Deprecated: …]` aliases
  in the `developer` profile only. Impact tools: 53 → 48; fund profile:
  62 → 57.
- **Lean install with extras (W1.6).** Streamlit, pandas, Plotly
  (dashboard), FastAPI/uvicorn/python-multipart (web) and Textual (legacy
  TUI) are now extras: `[web]`, `[dashboard]`, `[tui]`, `[office]`
  (python-docx / python-pptx) and `[all]`. `[dev]` includes `[all]`. The core
  install runs `demo`, `assess`, reports and the agent. `serve-web` and the
  new `impact-vision dashboard` command print the extra to install instead
  of a traceback. Without Node.js, the interactive terminal agent now
  explains the requirement and lists alternatives instead of crashing in
  `npm install`. The README lists Node.js as a prerequisite for the
  terminal agent, documents the extras, and drops the NaxtClaude proxy from
  the default provider table.
- **Plain-language layer (W1.7).** `data/glossary.yaml` (21 terms: 5D,
  NESTA, IC gate, evidence-based/partial/estimated, SFDR, ESRS/VSME, ISSB,
  OPIM, …) is the single source for the generated `docs/glossary.md` and a
  new "Terms used in this report" appendix in every HTML impact report. The
  appendix lists only terms that appear in the sections that audience sees.
  README sections are named by task ("Evidence, assurance & LP questions"
  instead of "Trust Infrastructure (v3)"). The DD category tables and the LCA
  walkthrough moved to `docs/dd-checklist.md` and `docs/climate-and-lca.md`,
  bringing the README from 1,030 to about 960 lines. The fund-manager guide
  now opens with the no-code `demo` / `assess` path.

### Security

- Removed hard-coded API key defaults from
  `examples/generate_pig_farm_reports.py` and four upstream test files. The
  keys remain in git history and must be revoked at the provider.

### Fixed

- PDF text is reflowed before extraction, so wrapped lines ("142\nstaff")
  don't split facts and headings don't bleed into the next sentence.
  Company names are matched within a single line, and title lines
  ("X — Investor Memo") are recognised. IRIS+ IDs the document cites
  explicitly are merged into the assessment.

### Fixed — v7 Wave 0 trust fixes (see `docs/roadmap-v7.md` §4)

- **Pitch-deck front door (W0.11).** `pitch_deck_analyze` named the pig-farm
  company "Pig" (from the filename), detected its sector as *education*
  (one mention of "school attendance"), added Affordable Housing / SDG 4 / 11
  ("slatted housing", "school") and routed ESG modules on "the, of, and, to".
  Names now come from legal-entity suffixes or the opening "X is a …"
  sentence. Sectors are scored by whole-word frequency, with the opening text
  counting double. Themes and SDG hints match whole words only (no hyphen
  compounds). Explicit SDG lists ("SDG 2/6/7/8/12/13", "SDGs 1, 5 and 8") are
  parsed and, when present, are the claims. ESG toolbox routing ignores
  stop-words and generic tags, and CBAM tools require a CBAM good
  (steel, cement, aluminium, …), not just "tCO2e" and "EU".
- **Pitch numbers reach the scoring engines (W0.10).** New
  `impact.claim_metric_mapper` maps quantities in extracted claims to IRIS+
  IDs using conservative, data-driven rules (`data/claim_metric_map.yaml`):
  unit + clause context must match exactly one rule; targets, study samples
  and ambiguous quantities are never mapped; units are converted (GWh → MWh)
  and "38% of 142 staff are women" yields a labelled derived OI6213. The SDK
  and `pitch_deck_analyze` feed these into `reported_metrics` (explicit IDs
  win). The pig-farm demo now reports OI2496, OI2764, OI8869, OI6213 and
  PI9991, and its greenwashing risk drops from 61.8 to 48.2.
- **IC gate distinguishes missing evidence from negative findings.**
  `GateCheck.data_gap` marks fails driven by non-evidence-based 5D/SDG scores,
  uncovered DD questions, or greenwashing below the High-Risk band.
  When every blocking failure is a data gap, `DealScorecard.evidence_status`
  is `insufficient`, `display_status` reads "INSUFFICIENT EVIDENCE" and the
  recommendation asks for data instead of "BLOCK IC submission"
  (`overall_status` stays `fail`, so nothing becomes IC-eligible).
  The IC memo and `quick_screen` use the same rule.
- **Installed wheels lost their reference data (W0.1).** About 20 loaders
  resolved `Path(__file__).parents[3] / "data"`, which points outside
  site-packages, so a pip-installed copy silently scored with hard-coded
  fallbacks and an empty DD checklist. All loaders now go through
  `impact._paths.data_path()` (`IMPACT_VISION_DATA_DIR` → repo `data/` →
  wheel `openharness/_data`). The empty `data/impact_vision.db` is no longer
  tracked or shipped; the SQLite default moves to `~/.impact-vision/`
  (`IMPACT_VISION_DB` overrides; an existing `./data/impact_vision.db` is
  still used). New CI job `wheel-smoke` builds the wheel, installs it in a
  clean venv and runs `scripts/wheel_smoke.py` from outside the repo.
- **The SDK ran without the IRIS+ catalog.** `ImpactVision()` only read the
  processed JSON cache, so on fresh installs its metric store was empty and
  SDG/gap scoring ran on keywords alone. It now uses `get_metric_store()`.
- **Extracted claims are evidence (W0.2).** Claims without an IRIS+ ID were
  dropped, so an evidence-rich pitch reported "0 tracked / NO_VERIFICATION".
  `assess_company_text()` now returns them as `Assessment.impact_claims`
  (NESTA level from evidence signals), `screen_greenwashing()` accepts the
  `Assessment` and counts verification signals, and claim cards show
  evidence badges. The regex extractor no longer splits decimals
  ("1.8 GWh" → "8 GWh"), recognises GWh/MW/tonnes/staff/clients, tags
  forward-looking targets as commitments, and detects third-party
  verification, audits and controlled evaluations.
- **Sector-aware DD, core metrics and risks (W0.3).** DD runs universal
  questions plus the company's sector set (`sector="auto"` infers it), so a
  pig farm no longer gets Fintech/Health/Mining questions. Gap analysis uses
  per-sector core sets from `data/core_metric_sets_by_sector.yaml`
  (unknown sectors keep the historical set) and reports
  `core_metric_set_basis`. Risks now lead with risks disclosed in the
  document; sector templates match on the canonical sector and word
  boundaries ("energy" no longer fires on "synergy").
- **Plausible SDG results (W0.4).** Matched targets are filtered to the goal;
  curated per-SDG core sets are intersected with the catalog's own SDG tags;
  cross-cutting metrics (tagged to 6+ goals) count at 0.4 weight and cannot
  alone produce "high" confidence; theme suggestions are ranked by relevance
  instead of alphabetically. New `SDGAlignment.material` flag; gap
  recommendations skip non-material goals.
- **No false red flags from thin input (W0.5).** `quick_screen` returns
  `insufficient_evidence` (with follow-ups) when input is too thin, or when
  every failed gate check is a threshold on text-only estimated scores.
  Exclusion failures remain red flags. DD matching tolerates inflections,
  adds synonyms and gives partial credit per keyword hit (a clear solar pitch
  went from 0% to 16%). `impact-vision dd analyze` gains `--sector` and
  `--json`, and both it and `framework scan` warn on short input instead of
  printing a bare 0%. `dd analyze` no longer crashes on long pasted text.
- **HTML escaping (W0.6).** Company names, claim text, evidence-chain
  values, targets, beneficiary-feedback methodology and document titles
  are escaped in the impact report and the shared report chrome; a
  regression test injects payloads into every user-supplied field.
- **Report options that did nothing (W0.7).** HTML reports with impact
  targets crashed (`AttributeError` on the target summary). `report_type=
  "lp_ready"` now renders the LP view; any single-audience report is filtered
  server-side (sections and their data, e.g. greenwashing flags for public),
  drops the audience toggle, and carries an audience-appropriate
  distribution notice. The table of contents is built from the sections
  actually rendered, in page order.
- **Signing keys fail closed in production (W0.8).** Audit trail, LP portal,
  LP data room, assurance bundle and dMRV signers resolve keys from
  `IMPACT_VISION_<PURPOSE>_HMAC_KEY` / `IMPACT_VISION_HMAC_KEY`. Without one
  they fall back to the public development key, labelled `hmac-sha256-dev`
  (assurance manifests carry `key_id="development-default"`), and refuse to
  sign when `IMPACT_VISION_ENV=production` or
  `IMPACT_VISION_ALLOW_DEV_KEYS=0`. Keys resolve lazily, so the tool
  registry still loads in production without them.
- **Golden-company tests (W0.9).** Pig farm, BrightPath and a solar deck
  are pinned with plausibility assertions (`tests/test_golden_companies.py`).

### Added

- **Just Transition, SBTN and biodiversity-credit content.** Replaced
  placeholder metric/principle names with the 19 Shift/WBA/WBCSD/LSE Just
  Transition metrics, a full SBTN five-step (AR3T) questionnaire, and the
  21 IAPB/BCA/WEF biodiversity-credit principles. Coverage now matches
  keywords and IRIS+ hints instead of looking for synthetic `JT-01` IDs.

- **Living-wage geography aliases and FX fallback.** Benchmark lookup
  accepts `nairobi, kenya` / `HK` / China-city aliases, converts non-USD
  wages through the offline FX table instead of raising, and the FX snapshot
  now covers common impact-fund currencies (KES, PHP, VND, XOF, …).

- **Lifecycle assessment surface.** Added `impact.lca` and the
  `lca_assessment` tool for transparent ISO 14040/14044-style goal/scope,
  caller-supplied LCI/LCIA factors, hotspots, sensitivity, lifecycle cost and
  social indicators, readiness scoring, and life-cycle-management actions.
  The engine intentionally does not bundle licensed databases such as
  ecoinvent; every characterization factor remains caller-provenanced.

- **v6 data-quality and regulatory currency review.** The simplified-ESRS
  loader now exposes Commission adoption status, FY2027 effective timing,
  official provenance, and an explicit `synthetic` flag for generated
  screening rows. Added the issued IFRS S2 targeted-amendment register
  (effective 2027-01-01, early application permitted) and a
  `regulatory_calendar` `s2_amendments` action. The watch-list now includes
  the EUDR micro/small-operator deadline (2027-06-30), and SFDR v2 outputs
  label the proposal's `ESG collection` category while retaining the
  backwards-compatible `esg_basics` code.

### Fixed

- **Greenwashing claim–metric gap.** SDG claims are no longer treated as
  substantiated just because *any* metrics were reported. Support is counted
  only when a reported IRIS+ ID maps to that SDG (or a theme family).

- **Carbon-credit integrity.** Removed invented `icvcm-method-01`…`36`
  IDs, added programme/methodology aliases (`Verra`, `VM-0042`), and stopped
  treating “eligible programme + approved method” as a CCP label.

- **Pitch-deck reported metrics.** Explicit `OI4112: 1,200 tCO2e` values are
  now extracted; metric *suggestions* still stay out of `reported_metrics`.
  Company models uppercase canonical IRIS+ IDs on intake.

- **MCP SDK pin.** Constrained the `mcp` dependency to `>=1.0.0,<2` so
  `impact.mcp_server` keeps importing FastMCP. Uncapped `mcp>=1.0.0` resolved
  to 2.x, which removed `mcp.server.fastmcp` and broke every MCP tool/resource.

- **Fintech sector vs GIIN benchmarks.** `Company.sector` canonicalises to
  `fintech`, which never matched `SECTOR_BENCHMARKS["Financial Services"]`.
  Reports and the improvement advisor now resolve via a reverse map.

- **Greenwashing verification.** A pile of unrelated metrics no longer
  drives the verification sub-score to zero. `CUSTOM:*` and `EDCI-*`
  adverse IDs survive tool normalisation.

- **5D / SDG sector inference.** `"energy"` no longer matches `"synergy"`;
  baselines key off the canonical sector, and description keywords use
  word-boundary + negation matching.

- **Pitch-deck claim metrics.** `mapped_metrics` only attach IRIS+ IDs that
  appear in the claim sentence. Missing catalog now errors instead of
  looking like “no impact”.

- **ILPA/PRI DDQ bank.** Replaced generated “intent {i}” strings with 80
  paraphrased ILPA DDQ 2.0, PRI 2026, and climate-module questions. The
  approved-data responder is unchanged.

- **GIIN KPI snapshot.** Added education, water, housing, manufacturing,
  waste, and transport quartile rows so the offline snapshot covers the
  same sector set as 5D benchmarks.

- **Impact report beneficiary feedback.** `beneficiary_feedback` is now an
  input field and invalid metric/claim rows surface in `input_warnings`
  instead of being dropped silently.

- **Empty catalog on tools.** Data quality, LP DDQ export, narrative,
  monitoring, IRIS catalog, and metric recommender now use
  `ensure_catalog_loaded()` so a missing catalog errors instead of scoring
  an empty store.

- **Concordance expansion.** `data/concordance.yaml` now carries the
  LP-comparable core (Scope 2/3, energy, water, waste, gender, living wage,
  jobs, PAI/EDCI, climate transition) so iXBRL tagging and CIDS/ask-once
  have taxonomy qnames. Legacy 59-concept merge is unchanged.

- **Biome-aware geospatial stub + dMRV.** Tree-cover loss is capped by
  biome (Amazon ≠ Dubai); dMRV HMAC key comes from
  `IMPACT_VISION_DMRV_HMAC_KEY`; satellite observations can be ingested as
  remote-sensing series. Climate-claim classifier is heuristic with optional
  ClimateBERT.

- **Simplified ESRS named disclosures.** Screening rows now include the
  EFRAG Set 1 disclosure catalogue (GOV/SBM/IRO/E1–E5/S1–S4/G1) as
  non-synthetic; generated fillers remain labelled `synthetic=true`.

- **iXBRL document shell.** Facts emit schemaRef, units, and transformation
  format; still a screening prototype, not an Arelle-validated filing.

- **MCP v1/v2 import shim.** `openharness.mcp.highlevel` loads FastMCP
  (SDK 1.x) or MCPServer (SDK 2.x). The HTTP/stdio *client* still targets
  1.x, so the dependency stays `mcp>=1.0.0,<2` until that handshake is
  ported.

- **`impact_vision` namespace.** `import impact_vision.impact` re-exports
  `openharness.impact`. `openharness` remains the implementation package.

- **Concordance enrichment.** Canonical YAML entries now merge with the
  legacy 59-concept map instead of replacing its cross-framework references;
  the canonical Scope 1 concept ID is aligned so EDCI/SFDR/SASB/TCFD links are
  retained. Article fixtures and ISSB adoption rows now disclose whether they
  are generated summaries or authority-name-only tracking records.

- **Regulatory status wording.** Updated the July roadmap intelligence and
  standards registry to distinguish Commission adoption from Official Journal
  entry into force for revised ESRS.

- **July-2026 roadmap-update items shipped** (see
  `docs/roadmap-updates-2026-07.md`):
  - *SFDR 2.0 category preview* — `classify_sfdr2_category()` in
    `frameworks/sfdr_pai.py` previews the proposed Sustainable / Transition /
    ESG Basics labels (70% strategy-alignment threshold, mandatory-exclusion
    screen, Art 8/9 migration map) and models the Council-position
    flexibility (ramp-up phase-in, delayed illiquid-asset divestment) as
    caveats. Exposed via `framework_assess` with `framework='sfdr2'`;
    every output carries an explicit "proposed law, ~2029" status note.
  - *AI-estimate provenance flag* — `MetricRecord` gains
    `estimation_methodology` plus a serialized `is_estimate` computed field;
    `estimate_disclosure_label()` / `flag_undisclosed_estimates()` in
    `metric_records.py` produce the mandatory "ESTIMATE — methodology"
    badge, which now travels through LP Q&A answers (`lp_narrative`) and 5D
    evidence chains (`evidence_chain_renderer.MetricLink`).
  - *EDCI-first collection scaffold* — `bundle_id='edci_core'` on
    `build_data_request_pack()` scaffolds a data-room request pack from the
    full EDCI metric set (core fields required, non-core optional, estimate
    labelling guardrail on every field); `edci_core_iris_metric_ids()` +
    the `sector='edci'` questionnaire template give collection flows the
    IRIS+ equivalents of the core EDCI set.
  - *Regulatory milestone watch-list* — `regulatory_watchlist()` in
    `regulatory_calendar.py` tracks 11 market-wide milestones verified
    2026-07 (ECGT, revised ESRS/VSME, ISSB nature ED, California SB 253,
    ISSA 5000, EUDR, CSRD/CSDDD transposition, SFDR 2.0), surfaced through
    the `regulatory_calendar` tool's new `watchlist` action.

- **`impact_advisor` tool router.** New deterministic router for the 44-tool
  impact surface (`impact.tool_advisor` + `tools/impact/advisor_tool.py`).
  `action='route'` ranks the most relevant tools for a free-text request via
  an auditable keyword routing table (no LLM call) and suggests one of nine
  multi-step playbooks (deal screening, LP reporting, regulatory compliance,
  verification & assurance, portfolio review, supply-chain HRDD, carbon &
  climate, data collection, theory of change); `action='playbook'` /
  `'list_playbooks'` / `'catalog'` expose the plans and the categorised tool
  catalog. A registry-sync test guarantees every routed tool name exists in
  `create_default_tool_registry()`.

### Changed

- **README tidy-up (July 2026).** Trimmed ~140 lines of duplication: merged
  the small prompt sections into grouped ones (catalog/DD/scoring, ESG
  frameworks/ToC/compliance, pipeline/monitoring, v3 trust infrastructure),
  condensed the provider-setup wizard transcripts, removed the CLI
  quick-reference table (the CLI Reference section is the single source),
  corrected the tool count (44), replaced the stale "EU Green Claims
  Directive" row with ECGT (EU) 2024/825, and added SFDR 2.0 preview +
  roadmap v5/v6/2026-07 pointers.

- **ESG toolbox knowledge refresh (all 33 modules audited, June 2026 facts).**
  Every `impact.toolbox` module was reviewed for content depth and taxonomy
  pairing; thin and stale modules were enriched with verified current facts:
  - *CBAM* — replaced the stale transition-period quarterly-reporting
    requirement with definitive-period obligations per the CBAM Omnibus
    (Regulation (EU) 2025/2083): 50-tonne annual mass de minimis, authorised
    declarant, first annual declaration due 30 Sep 2027, certificate sales
    from 1 Feb 2027, 50% coverage ratio, harmonised €100–500/tCO₂e penalties.
  - *EUDR* — new application-timeline requirement (30 Dec 2026 for
    large/medium + timber-sector micro/small, 30 Jun 2027 for other
    micro/small; one-time simplified declaration per Regulation (EU)
    2025/2650).
  - *ESRS/CSRD & CSDDD* — **taxonomy fix**: both modules previously inherited
    the generic export template (CN/HS customs-code applicability screen),
    which is the wrong applicability taxonomy for company-size-based laws.
    Replaced with post-Omnibus scope thresholds (CSRD: >1,000 employees +
    >€450M turnover, first reports FY2027; CSDDD: >5,000 employees + >€1.5B,
    application 26 Jul 2029) per Omnibus I Directive (EU) 2026/470, plus a
    simplified-ESRS datapoint note (~60% datapoint cut expected 2026).
  - *EU Battery Regulation* — new milestone-timeline requirement (CFP
    declarations: EV Feb 2025, industrial >2 kWh Feb 2026, LMT Aug 2028;
    battery passport mandatory 18 Feb 2027; recycled-content minimums from
    Aug 2031).
  - *SBTi* — validation requirement now tracks the V1.3/V5.3 → Corporate
    Net-Zero Standard V2 transition (V2 mandatory for new targets from
    1 Jan 2028).
  - *CDP* — questionnaire-scope requirement updated to the 2026 cycle
    (13-module integrated questionnaire; climate/forests/water scored;
    plastics/biodiversity/ocean unscored; 7 scored forest commodities).
  - *MSCI* — new rating-scale requirement (AAA–CCC, industry-adjusted
    weighted key-issue scores, exposure vs management, controversy drag).
  - *EcoVadis* — new scoring requirement (21 criteria, 0–100, percentile
    medals: Platinum 1% / Gold 5% / Silver 15% / Bronze 35%) and filled
    empty theme descriptions with framework refs.
  - *SMETA* — SMETA 7.0 facts (Management Systems Assessment, Collaborative
    Action Required categories, ETI Base Code, 2- vs 4-pillar).
  - *AWS* — **source fix**: methodology link pointed at the retired V2.0
    page while content described V3.0; now cites AWS Standard V3.0
    (launched 18 Mar 2026, transition to 18 Mar 2027).
  - Filled 10 empty requirement descriptions (materiality matrix,
    stakeholder inputs, GRI content index, AA1000 assurance scope, CSDDD
    grievance/remedy, ICMA UoP/KPI framework, Climate Bonds taxonomy
    eligibility, AWS stewardship plan, EcoVadis themes, conflict-minerals
    traceability) and added missing `framework_refs` throughout.

- **Tool surface consolidated 46 → 44 (3 merges + 1 router).**
  - `greenwashing_reviewer` merged into `greenwashing_detect`: the new
    `action='review_claims'` runs the per-claim explainable reviewer
    (specificity, evidence gaps, severity, follow-up DD questions,
    AI-governance metadata) on top of the existing company-level screen.
  - `verification_prep` merged into `verification_workspace`: prep actions
    `readiness_check` / `evidence_map` / `ifc_alignment` (BlueMark, IFC OPIM,
    AA1000) now live alongside the verifier workspace actions, so one tool
    covers prepare → verify.
  - `narrative` merged into `impact_report`: `narrative_mode='narrative_prompt'`
    plus the new `narrative_section` / `narrative_audience` /
    `narrative_word_limit` fields generate audience-tuned executive-summary,
    key-findings, impact-narrative, and case-study prompts.
  - The underlying modules (`greenwashing_reviewer_tool.py`,
    `verification_prep_tool.py`, `narrative_tool.py`) remain importable for
    the MCP server, REST API, and Web Console, but are no longer registered
    as standalone agent tools. Engagement bundles, the reporting studio
    claim-review checklist, and the ESG-toolbox handoffs now reference the
    merged tool names.

- **ESG toolbox knowledge integrated into existing tools (consolidation wave).**
  The 33-module ohESG toolbox now enriches the host tools instead of living
  only behind the standalone `esg_toolbox` surface:
  - **Unified metric crosswalk.** `toolbox.crosswalk_reported_metrics` now
    derives mappings from the 59-concept `frameworks.cross_reference` map
    (GRI/ESRS/ISSB/SFDR PAI/TCFD/SASB/CDP/SBTi/PCAF/EDCI columns, scoped per
    toolbox category) and merges the curated export/supplier uses — coverage
    grows from 7 curated metric IDs to every IRIS+-mapped concept.
  - **`framework_assess` enrichment.** GRI match/assess now appends a
    disclosure-level quick reference and GRI 11-14 sector topics from the
    294-record ohESG GRI index (with English sector routing for oil & gas /
    coal / agriculture / mining); a new `cdp` framework handler runs CDP
    questionnaire readiness with a metric→CDP-code crosswalk.
  - **EU regulatory calendar export-compliance obligations.** The EU
    jurisdiction profile adds CBAM annual declarations, EUDR due-diligence
    system review, EU Battery Regulation passport/carbon-footprint readiness,
    and an ESPR/DPP applicability screen.
  - **`hrdd_assess` audit-scheme readiness.** When the supplier context
    matches, HRDD results now include scheme-specific readiness
    (SMETA/SA8000/amfori BSCI/RBA/conflict minerals/IRMA/CSDDD) with evidence
    gaps and official sources.
  - **AA1000 verification target.** `verification_target='aa1000'` (now via
    `verification_workspace` readiness actions) appends an AccountAbility
    principles/assurance readiness section.
  - **`product_passport` regulatory readiness.** The `assess` action now
    appends EU Battery Regulation (for battery categories) or ESPR readiness
    from the toolbox requirement sets.
  - **`pitch_deck_analyze` ESG compliance routing.** The main intake tool now
    appends the same `build_esg_workflow` routing block as gap_analysis /
    impact_report, so compliance modules are surfaced from first contact.
  - **`esg_toolbox` is now a router.** `get` / `checklist` / `assess` outputs
    include a `host_tool_handoff` pointing to the deeper Impact Vision tool
    (GRI/ESRS/ISSB/CDP → `framework_assess`, supplier schemes → `hrdd_assess`,
    battery/ESPR → `product_passport`, AA1000 → `verification_workspace`,
    CBAM/EUDR/Green Deal deadlines → `regulatory_calendar`, GHG →
    `emission_factors`), and a new `toolbox.search_source_index()` helper
    exposes the rich embedded datasets (GRI 294 / SBTi 363 / ISS 344 / CSA 62
    / AWS 33 records) to any tool.

- **Roadmap v5 — regulatory currency + frontier measurement.** See
  [`docs/roadmap-v5.md`](docs/roadmap-v5.md). Shipped so far:
  - **EU Omnibus I currency (Track A1).** `standards_registry` now cites
    Directive (EU) 2026/470 (ESRS Omnibus active + new CSDDD standard);
    `regulatory_packs` carries refreshed CSRD thresholds, a new `EU-CSDDD`
    pack, and `as_of` / `legal_basis` provenance fields; new
    `engagements.regulatory.assess_eu_omnibus_scope` decision tree (CSRD/CSDDD
    in-scope, FY2025-26 pause eligibility, VSME fallback) exposed via the
    `engagement_suite` tool (`assess_eu_omnibus_scope` action).
  - **EFRAG VSME voluntary standard (Track A2).** `frameworks.vsme` with the
    Basic (B1-B11) + Comprehensive (C1-C9) disclosure catalogue and a
    coverage screen, exposed via `framework_assess` (`vsme`, with
    `category=basic|comprehensive`).
  - **2X Criteria gender-lens screen (Track B3).** `frameworks.two_x` scoring
    the six 2X dimensions plus the mandatory governance + GBVH minimum
    requirements, exposed via `framework_assess` (`two_x`).
  - **IFVI/VBA monetary impact valuation (Track B1).** New
    `impact.impact_valuation` (value-factor catalogue → monetised benefit/cost
    ledger, net monetary impact, benefit/cost ratio, impact intensity, and an
    impact-weighted return / impact multiple of money) and the
    `impact_valuation` agent tool. `fund_analytics.impact_weighted_returns_stub`
    now computes a real impact-weighted IRR when financial returns are supplied.
  - **GIIN Impact Performance Benchmarks (Track C1).** New
    `impact.giin_benchmarks` with seeded sector KPI quartile distributions
    (agriculture, clean energy, financial inclusion, forestry, healthcare),
    SDG-need contextualisation, and a `GIINImpactBenchmarkProvider` that plugs
    into the engagement-suite benchmark protocol. Exposed via `engagement_suite`
    (`benchmark` with `provider="giin"`, `list_giin_benchmarks`,
    `giin_kpi_context`).
  - **Accessible, provenance-aware reports (Track D2 + D3).** The flagship
    HTML impact report and the shared `report_v2` chrome now meet WCAG 2.2 AA:
    a "skip to main content" link, a `<main>` landmark, an `aria-label`led
    table of contents, `role="img"` + descriptive alt-text on every Plotly
    chart (each backed by an adjacent data table), keyboard-operable
    disclosure rows (5D / SDG / impact-claim) with `role="button"`,
    `tabindex`, Enter/Space handlers and `aria-expanded`, visible focus
    outlines, and a `prefers-reduced-motion` guard. Evidence provenance is now
    surfaced inline via an `.evidence-badge` component (verified / reported /
    estimated / proxy / unverified / suggested) that uses label + shape, not
    colour alone, with an accessible source/confidence tooltip and a legend;
    the 5D table's score-provenance column renders these badges. New
    `render_provenance_badge()` / `render_evidence_legend()` helpers and a
    `theme="dark"` option on `wrap_document()` are exported from
    `report_templates` for reuse by the IC memo and DD report (Track D1
    chrome unification landed additively rather than as a risky rewrite).
  - **Welfare quantifier — QALYs / lives improved (Track B2).** New
    `impact.impact_quantifier` converts breadth × depth × theme × geography ×
    duration × additionality into Quality-Adjusted Life Years and "lives
    meaningfully improved", with cost-per-QALY, monetised welfare, and a
    portfolio roll-up by theme/geography. New `impact_quantifier` agent tool.
  - **Human-rights & value-chain due diligence (Track A3).** New `impact.hrdd`
    aligned to UNGP (Protect/Respect/Remedy), the OECD 6-step cycle, and EU
    CSDDD: salience ranking (severity × likelihood with gross-risk escalation
    for forced/child labour & modern slavery), value-chain tier mapping, a
    UNGP-Principle-31 grievance-effectiveness score, a remediation state
    machine, OECD step coverage, and a CSDDD readiness band. New `hrdd_assess`
    agent tool (`assess`, `seed_from_text`).
  - **TISFD readiness (Track B4).** New `frameworks.tisfd` — a beta,
    forward-looking Inequality & Social-related Financial Disclosures readiness
    screen across the 4 TCFD-style pillars (13 disclosures; pay, labour
    conditions, freedom of association, community, inequality) with a GRI/ESRS
    crosswalk and an explicit beta label. Exposed via `framework_assess`
    (`tisfd`).
  - **Context-driven impact target setter (Track B5).** New
    `impact.impact_target_setter` derives conservative / base / stretch IRIS+/SDG
    target ranges (plus an annual trajectory) from theme × geography × capital.
    Wired into `decision_workflow` as `action='set_targets'`.
  - **NGFS climate scenario risk (Track E1).** New `impact.climate_scenario`
    scores portfolio physical & transition exposure across seven NGFS scenarios
    (orderly / disorderly / hot-house / too-little-too-late) using sector
    sensitivities, returning a combined risk score, an illustrative value-at-risk
    haircut per scenario, and the most-exposed holdings. New
    `climate_scenario_risk` agent tool.
  - **AI governance artifact (Track E2).** New `impact.ai_governance` produces a
    model card, per-artefact data-lineage records, and a human-oversight log
    assembled from the copilot review queue, plus an EU AI Act risk
    classification (unacceptable / high / limited / minimal) and the
    transparency / human-oversight / record-keeping obligation checklist. New
    `ai_governance` agent tool; builds on `engagements.copilot`.
  - **Investee data-collection portal (Track C2).** New
    `impact.investee_portal` generates a self-contained, offline, single-file
    HTML questionnaire (client-side validation, SFDR PAI plain-language
    rewrites, a per-field "why we ask" feedback loop, a progress bar, WCAG 2.2
    AA structure, and local JSON export — no server). New `investee_portal`
    agent tool (`generate`, `schema`).
  - **Decision-useful report UX (Tracks D4-D7).** The flagship HTML report now
    ships an accessible **audience filter** (LP / IC / regulator / public
    toolbar that segments sections by lens, hidden in print), an **executive
    tear sheet** ("At a glance" single-screen summary with a `page-break-after`
    for a clean one-page PDF), **uncertainty visualization** (a
    provenance-derived confidence band rendered as an accessible error-bar), a
    **dark theme** (`theme="dark"`), **white-label branding** wiring
    (`branding` input → `branding.py` tokens), and a tagged **PDF/UA-1** export
    with heading bookmarks from `_to_pdf`.
  - **Interactive reading chrome (Track D polish).** The HTML report gained a
    top **reading-progress bar**, a floating **utility dock** (in-browser
    light/dark toggle that persists the reader's choice in `localStorage`, a
    "save as PDF / print" button, and a back-to-top control), **scrollspy**
    that highlights the current section in the on-page table of contents,
    **copy-link anchors** on every section heading for deep-linking an LP or IC
    straight to a section, and **collapsible major sections** (per-section
    carets plus "Expand all / Collapse all" controls), and a scroll-activated
    **sticky mini-header** (company name + overall grade/score) for orientation
    in long reports. Collapse state survives audience-filter switches and
    auto-expands for print/PDF so nothing is lost. All of it is
    keyboard-accessible, respects `prefers-reduced-motion`, the sticky header is
    `aria-hidden` (it duplicates the main header already in the a11y tree), and
    the interactive chrome is hidden in print/PDF output.
  - **Print/PDF polish (Track D).** Added a print-only **cover page** (title,
    company, sector, overall grade/score, generation date, standard, and a
    confidentiality notice) plus `@page` **running footer** with "Page X / Y"
    page numbers and a confidentiality line, a running header that repeats the
    company name (via `string-set`/`string()`), and `break-inside: avoid` on
    cards/tables/charts so the WeasyPrint PDF deliverable paginates cleanly. The
    cover is hidden on screen and the on-screen header is suppressed in print to
    avoid duplication.
- **v5 decision workflow suite for fund managers, project owners, and
  Impact / ESG consultants.** Added decision-useful workflows that turn
  the existing assessment engine into investment committee and LP-ready
  outputs:
  - `impact.decision_workflow` with quick screen, IC workflow summary,
    deal comparison, and LP readiness scoring.
  - `impact.evidence_chain_renderer` to link reported metrics and claims
    back to the IMP five dimensions without changing the scoring model.
  - `impact.verdict_engine` for pass / caution / fail verdict cards with
    top findings, strengths, and next steps.
  - `impact.regulatory_calendar` as a planning-friendly wrapper around
    jurisdiction deadline scheduling.
  - New agent tools `decision_workflow` and `regulatory_calendar`,
    registered in the default tool registry and exposed through the SDK,
    MCP server, REST API, and Web Console.
  - IC memo renderers now accept verdict cards and a "Proof of Rigor"
    appendix so reviewers can see the evidence, claim gaps, and warnings
    behind the recommendation.
  - 5-Dimension assessment metadata now includes evidence chains, and
    impact report JSON now enriches each dimension with tracked metrics
    plus gap-analysis metric suggestions.
  - Pitch-deck extraction now keeps suggested metrics separate from
    reported evidence, including explicit metadata and saved YAML fields
    that prevent recommendations from being treated as verified data.
  - README and the fund-manager guide now document the 39-tool impact
    surface and the new v5 workflows.
  - Added regression coverage for decision workflows, regulatory
    calendars, REST/MCP public surfaces, report metric enrichment, and
    pitch-deck evidence integrity. Verified full suite:
    **1202 passed, 7 skipped, 1 xfailed**.

### Changed

- **README.md deep cleanup (2026-05-02).** Removed all changelog-style
  banners, "What's new in v0.14.0 / v0.15.0" blocks, "System Review
  (v0.14.0)", phase-by-phase roadmap history, and verification-status
  tables from `README.md`. Moved the Python SDK 60-second walkthrough to
  a new [`docs/fund-manager-guide.md`](docs/fund-manager-guide.md).
  Consolidated the four "Standards Supported" sub-tables into one single
  framework table. Rewrote the Architecture tree, CLI Reference, and
  Agent Tools section against the current codebase (37 impact tools,
  including v3 trust-infrastructure and v4 engagement-suite tools).
  Verified the recommended OpenRouter free models against the live list
  (May 2026) — swapped out stale `google/gemini-2.5-flash:free` and
  `meta-llama/llama-4-maverick:free` for current free models with
  verified tool-calling support. Codified the "README = newcomer
  docs only, changelog lives here" rule in `CLAUDE.md` so future
  edits don't regress.

### Fixed

- **v4 Tracks 3-10 deep review — 3 logic bugs + 1 name collision fixed.**
  - `engagements.data_room.score_completeness` previously counted an
    empty-value submission as *covering* a required metric, inflating
    coverage and hiding the gap. Empty values now correctly leave the
    metric in the missing set and are surfaced as a single (not
    duplicated) `missing` exception.
  - `engagements.data_room.build_coaching_cards` used to fall back to
    `entity_name="Unknown"` for any exception whose metric was not in
    the caller's missing list (`unverified`, `stale`, `proxy`, etc.).
    The helper now takes an optional ``submissions`` argument and
    resolves the entity via `submission_id`, keeping the coaching card
    routed to the right investee.
  - `engagements.website.score_diagnostic` previously incremented
    ``max_score`` per answer, so a caller sending duplicate answers
    for the same question inflated the denominator. The scorer now
    collapses duplicates (last-wins) and computes ``max_score`` from
    the question catalogue.
  - Renamed `engagements.regulatory.JurisdictionProfile` →
    `RegulatoryJurisdictionProfile` to resolve a public-API collision
    with the leaner v3 `roadmap_v2.JurisdictionProfile`. v3 call sites
    (`select_jurisdiction_profile`) are unchanged; v4's richer profile
    now has a distinct name and no longer shadows the v3 export.

### Added

- `EngagementWorkspace.record_artifact(engagement_id, kind=..., ...)` —
  generic audit-trail anchor used by Tracks 3-10 callers (data packs,
  reports, assurance bundles, verifier tokens, etc.). Every invocation
  appends a hash-chained event to the v3 `AuditTrail`, closing the
  Sopact-counter "consultant override must be legible" requirement for
  the new integration-wave modules.
- Security note added to `build_assurance_bundle` / `verify_assurance_bundle`
  docstrings clarifying that the default HMAC secret mirrors the v3
  `AuditTrail` demo default and MUST be replaced with a KMS/HSM key in
  production.
- 9 new regression tests in `tests/test_v4_tracks_3_to_10.py` covering
  the three logic bugs, the workspace `record_artifact` audit event,
  the suite tool's error surface (missing payloads / invalid
  transitions / unknown templates), an exhaustive SFDR classification
  matrix, deadline scheduling under overdue/due-soon fiscal year ends,
  and the copilot queue's unsafe-approval blockers. v4 test count is
  now **88 (23 + 18 + 47)**; full suite is **1165 passing, 15 skipped, 1 xfailed, 0 failures**.

### Added

- **v4 Tracks 3-10 — Integration Wave complete**. Eight new modules in
  `impact.engagements` and one consolidated agent tool (`engagement_suite`)
  that dispatches across them. Every module is wired through the v3
  `AuditTrail` singleton and ships deterministic defaults so CI runs
  without external data.
  - `engagements.data_room` (Track 3) — `DataRequestPack` with bundle-aware
    guidance cards (definition, examples, acceptable evidence, common
    mistakes), `DataRoomSubmission` / `FieldSubmission`,
    `score_completeness()` (per-entity coverage + `missing` / `unverified`
    exception detection), `rollup_multi_entity()` (per-metric fill rate
    across entities), and `build_coaching_cards()` that convert exceptions
    into coaching prompts.
  - `engagements.value_creation` (Track 4) — `BenchmarkProvider` protocol
    with a seeded `InMemoryBenchmarkProvider`, `PeerDashboard`,
    `ImpactRiskRating` with material-risk flagging, `ValueCreationPlan`
    that ties actions to KPI gaps / material risks / peer gaps,
    `BusinessCase` (revenue / cost / risk-avoidance upside + valuation
    multiple), `run_scenario()` compound-multiplier sensitivity engine,
    and `score_supply_chain_hotspots()` for Scope 3 supplier ranking.
  - `engagements.reporting_studio` (Track 5) — audience- and
    evidence-depth-aware `Report` + `ReportSection` with 6 named
    templates (IMM Baseline, Impact DD, ESG Baseline, Portfolio Deep Dive,
    Annual Impact, Exit/VDD), `transition_report()` state machine (draft →
    in_review → approved → published → superseded), `ClaimReview` panel
    with `decide_claim()`, `build_executive_deck()` one-click outline,
    `build_public_microsite()` for Track 7 microsites, and
    `rewrite_for_audiences()` deterministic multi-audience rewrites
    covering founder / IC / LP / board / public / regulator / verifier.
  - `engagements.training` (Track 6) — `build_training_plan()` keyed to
    maturity stage, 6 workshop packs (ToC, KPI design, ESG baseline, data
    quality, stakeholder voice, reporting) with agendas + prompts +
    deliverables, `build_coaching_card()` for investees,
    `record_learning_loop()`, and `issue_readiness_badge()` (data /
    report / assurance / LP) with threshold enforcement.
  - `engagements.website` (Track 7, backend-only) — 7-question diagnostic
    quiz with maturity scoring, gallery of productised engagements,
    benchmark teaser, 5-entry playbook library, privacy-preserving upload
    demo (never echoes source text), GDPR/PDPA-aware `capture_lead()`,
    and white-label `PartnerMode` metadata.
  - `engagements.copilot` (Track 8) — `CopilotOutput` with prompt / model /
    model_version / source_refs / reviewer / decision provenance and a
    `policy_passed` computed gate, `CopilotReviewQueue` that blocks
    approval of low-confidence or unsourced outputs, deterministic
    `run_challenge()` mode (unsupported_claim / weak_toc_link /
    missing_stakeholder / missing_evidence / unclear_baseline),
    `answer_from_approved_evidence()` client-safe answer scaffold, and
    `extract_meeting_notes()` prefix-based ingestion.
  - `engagements.regulatory` (Track 9) — 8 `JurisdictionProfile` entries
    (EU, UK, US, Singapore, Switzerland, Canada, Japan, Australia) each
    listing `RegulatoryObligation`s, SFDR Article 6/8/9 classifier,
    UK SDR label classifier with anti-greenwashing enforcement,
    `schedule_deadlines()` calendar tied to fiscal year end, and
    `build_regulator_narrative()` compositor.
  - `engagements.verification_bundle` (Track 10) — BlueMark-style
    3-Pillar Verification: `MandatePack` (6 checks) + `PracticePack`
    (9 OPIM principles) + `ReportingPack` (claim-by-claim review), HMAC
    + SHA-256 signed `AssuranceManifest`, `verify_assurance_bundle()`
    tamper-detection, `VerifierToken` with hashed secret + expiry,
    `VERIFIER_MARKETPLACE` directory (BlueMark, KPMG, DNV), and
    `evaluate_assurance_readiness()` badge driven by per-pillar
    completion thresholds.
- New consolidated agent tool `engagement_suite`
  (`tools/impact/engagement_suite_tool.py`) — one action-dispatched tool
  exposing 46 actions across Tracks 3-10 (data room, value creation,
  reporting studio, training, website, copilot governance, regulatory
  workbench, verification bundle). Registered in
  `create_default_tool_registry()`. Avoids tool-sprawl by composing
  existing modules rather than spawning 8 near-identical tools.
- `tests/test_v4_tracks_3_to_10.py` — 38 new tests covering every
  function from the 8 new modules plus an end-to-end smoke test that
  walks the consolidated tool through at least one action per track
  (including a sign/verify roundtrip for the assurance bundle and a
  tamper detection assertion). After the deep-review regression
  additions (see Fixed section) the Tracks 3-10 count grew to 47 and
  the total v4 test suite stands at **88 tests** (Track 1: 23,
  Track 2: 18, Tracks 3-10: 47), all green.
- **v4 Wave 2 — Theory of Change + KPI Framework Builder (Track 2)**.
  New `impact.engagements.toc_builder` module that wraps the existing v3
  `impact.toc_graph` Mermaid renderer and
  `impact.frameworks.cross_reference` crosswalk to deliver the critical
  items from roadmap-v4 Track 2:
  - `ToCCanvas` + `ToCCanvasNode` + `ToCCanvasEdge` + `ToCAssumption` +
    `ToCRisk` — a consultant-facing ToC canvas with explicit problem,
    stakeholders, inputs, activities, outputs, outcomes, impact,
    assumptions, risks, and an equity & inclusion lens (Track 2.1).
  - `draft_toc_from_intake()` — deterministic first-pass drafting hook so
    the canvas always has something for the consultant to challenge
    (positions us for Track 8's LLM draft without requiring it now).
  - `validate_toc_canvas()` — rules-based logic-chain validator covering
    missing problem/outcomes/impact, weak causal links (untested edges),
    unmeasured outcomes (no IRIS+ mapping), missing or untested
    assumptions, missing stakeholder / equity lens, and risks without
    mitigation plans (Track 2.2).
  - `generate_kpi_framework()` — generates an engagement-scoped
    `KPIFramework` by reusing the v3 IRIS+ metric-recommender scoring
    logic and lifting every pick through the cross-reference map to GRI,
    EDCI, SASB, TCFD, ISSB, ESRS, TNFD, PCAF, EU Taxonomy, CDP, SBTi, and
    SFDR PAI (Track 2.3). `lock_kpi_framework()` freezes a framework so
    downstream tools treat it as immutable.
- `EngagementWorkspace` gained `attach_toc_canvas`, `validate_toc`,
  `mark_toc_node_reviewed`, `generate_kpi_framework_for`,
  `lock_kpi_framework_for`, and `get_kpi_framework` helpers that thread
  every change through the v3 `AuditTrail` (the Sopact counter-position
  requirement that consultant review be legible and audit-logged).
- New agent tool `toc_builder` (`tools/impact/toc_builder_tool.py`)
  exposing the full Track 2 surface — draft, attach, validate, mark
  reviewed, generate KPI, lock KPI, render Mermaid/Markdown — registered
  in `create_default_tool_registry()`.
- `tests/test_v4_toc_builder.py` — 18 new tests covering draft,
  validator rules (all 11 rule codes), cross-reference expansion,
  workspace wiring, audit-trail integration, and full agent-tool smoke
  paths.
- **v4 Wave 1 — Consultant Engagement Workspace (Track 1)**. New
  `impact.engagements` package that packages v3 capabilities into a
  consulting engagement lifecycle per `docs/roadmap-v4.md`:
  - `engagements.models` — canonical `Engagement`, `Deliverable`,
    `ChecklistItem`, `EngagementDocument`, `EngagementNote`,
    `EngagementDecision`, and `ConsultantOverride` contracts. Deliverables
    and engagements ship a validated state machine (planned → in_progress →
    draft → client_review → final; proposal → active → on_hold → closed).
  - `engagements.bundles` — 12 productised engagement bundles from
    roadmap-v4 §4a (Strategy/IMM, DD-Light/Mid/Full IWA, ESG Baseline,
    Annual Impact Report, LP DDQ, BlueMark-style 3-Pillar Verification,
    Exit/VDD, Regulatory, Stakeholder Voice, Capacity Training) each
    referencing the existing v3 agent tools that compose them — no v3
    module is forked, matching the roadmap's "integration wave" rule.
  - `engagements.checklist` — seven-phase consultant checklist generator
    (Discovery → Data Request → Stakeholder Map → ToC Workshop → KPI
    Design → Reporting → Training) with sequential `depends_on` linkage.
  - `engagements.proposal` — deterministic proposal builder turning a
    bundle pick + intake notes into scope, workplan, assumptions, fees,
    outputs, and risk caveats.
  - `engagements.templates` — reusable client-type template library for
    funds, corporate CSR, foundations, nonprofits, and social enterprises.
  - `engagements.workspace` — in-memory `EngagementWorkspace` store that
    hashes document content, routes every state change through
    `AuditTrail`, and captures consultant overrides of AI suggestions as
    first-class records (the Sopact counter-position feature).
- New agent tool `engagement_workspace` (`tools/impact/engagement_workspace_tool.py`)
  exposing the full Track 1 surface to MCP/CLI callers with 18 actions
  (list/browse bundles + templates, build proposal, create engagement,
  drive deliverable + checklist state machines, attach documents, record
  decisions / overrides, export state). Registered in
  `create_default_tool_registry()`.
- `tests/test_v4_engagement_workspace.py` — 23 tests covering the bundle
  catalog, checklist generator, proposal builder, state machines,
  audit-trail integration, and the full agent-tool smoke path.
- Whole-codebase bug/logic audit artifacts under `project_document/`:
  `memory_bank_db.json`, `debug/codebase_debug_plan.md`,
  `debug/logic_issue_improvement_plan.md`, `debug/logic_audit_report.md`,
  and reusable debug probes for import/registry/runtime surface checks.
- `docs/roadmap-v4.md`, a consultant-led product roadmap based on TSIC,
  Rimm Sustainability, and broader impact-consulting market signals. It
  reframes the next phase around consultant engagement workspaces, theory of
  change strategy design, client data rooms, benchmarking/risk intelligence,
  reporting studios, training engines, website productisation, and an
  evidence-governed AI consultant copilot.
- Cross-cutting hardening regression tests in `tests/test_bug_hardening.py`
  covering API CORS defaults, timezone-aware Mochat events, Copilot runtime
  version headers, and optional channel helper utilities.

### Changed

- API CORS configuration now reads `IMPACT_VISION_CORS_ORIGINS` and disables
  credentialed CORS automatically when wildcard origins are active.
- Copilot client `User-Agent` now uses installed package metadata instead of
  a hard-coded release string.
- Mochat cursor/synthetic-event timestamps now use timezone-aware UTC.

### Fixed

- Restored optional channel helper imports by adding
  `openharness.utils.helpers.safe_filename()` and `split_message()`, unblocking
  Discord/Telegram/Matrix channel modules that referenced the helper package.
- Matrix channel now imports `get_data_dir()` from the existing
  `openharness.config.paths` module instead of the nonexistent
  `openharness.config.loader`.
- API gateway and Impact MCP server runtime metadata now report `0.15.0`.
- Cleaned stale unused imports from `tests/test_impact.py`.

### Tests

- Full-suite verification after the hardening pass:
  `1077 passed / 15 skipped / 1 xfailed`.
- Related hardening/channel/API/MCP subset: `85 passed`.
- Import smoke: all `37` package `__init__.py` files present, all `21` import
  groups verified, default registry bootstrapped with `71` tools.
- `ruff check src tests project_document/debug` is clean.
- Logic audit now reports `492` Python files scanned, `24` API routes,
  `71` tools, `0` CORS wildcard findings, `2` remaining test-only
  `datetime.utcnow()` occurrences, and `0` syntax errors.

## [0.16.0] - 2026-07-19

### Added

- Implemented the v6 Comparable, Assured & Connected wave: regulatory currency, canonical concordance, digital tagging, ISSA 5000 readiness, and portfolio comparability.
- Added contribution and target gates, impact-linked economics, integrity screens, nature/social-frontier methods, dMRV, burden reduction, CIDS, and governed regulatory/evaluation workflows.
- Added the China SSE/SZSE reporting suite, climate calculators, mandatory-article scans, and approved-data-only ILPA/PRI DDQ drafting.
- Registered seven v6 agent tools and reconciled the registry, public exports, advisor routing, and generated tool-list check at 51 tools.

## [0.15.0] - 2026-05-01 - "Trust Infrastructure"

This release executes the first wave of the v3 roadmap (`docs/roadmap-v3.md`)
and is the **trust-infrastructure release**: causal-style claims, stakeholder
voice as evidence, governed AI, and an LP-grade assurance bundle. The full
engineering plan is in `docs/roadmap-v3-implementation.md`.

### Added

- **Versioned emission-factor catalogue** (`impact.emission_factors`).
  Multi-revision factors with low/high uncertainty bands, a default catalogue
  for grid electricity and natural gas, `factor_sensitivity()` for ±band
  rollups, `apply_catalog_to_inventory()` for repricing existing GHG
  inventories, and `summarise_sensitivity()` rollups across activities.
- **Stakeholder voice as evidence** (`impact.stakeholder_voice`).
  Lean Data survey templates (`build_lean_data_survey()`),
  GDPR/PDPA-compliant `ConsentRecord` lifecycle (`revoke_consent()`,
  `filter_active_responses()`), beneficiary feedback quality scoring
  (`score_feedback_quality()`), and `link_feedback_to_claims()` for binding
  feedback to impact claims as first-class evidence.
- **AI extraction review queue** (`impact.evidence_workflow`).
  Policy-driven `ReviewQueue` with auto-approval thresholds, single and bulk
  decisions, audit-trail integration, and `build_review_item_from_extraction()`
  that converts agent-extracted claims into queue items.
- **Verification workspace** (`impact.verification_workspace`).
  Read-only assurance-pack workspace with `VerificationFinding` lifecycle
  (`open` → `in_review` → `resolved` / `unresolved`), threaded comments,
  workspace closure with `closed_by`/`closed_at`, and `open_workspace()`
  factory tied to assurance packs.
- **LP narrative + Q&A workspace** (`impact.lp_narrative`).
  `generate_lp_narrative()` builds an audit-friendly narrative grounded in
  approved-data records; `LPQuestionWorkspace` constrains LP Q&A to verified
  evidence with citations and exportable transcripts.
- **Greenwashing reviewer** (`impact.greenwashing_reviewer`).
  Per-claim explainable review with specificity classification (concrete /
  mixed / vague / buzzword-only), severity scoring, evidence/governance
  metadata, and propagation of overall review scores back to the company.
- **Portfolio natural-language query engine** (`impact.portfolio_nlq`).
  `ApprovedDataPolicy` enforces verification-status filters; `parse_intent()`
  extracts `average / total / top_n / compare` intents; `PortfolioNLQEngine`
  answers with citations to canonical metric records only.
- **Exit impact assessment** (`impact.exit_impact`).
  OPIM Principle 7 workflow with Principle 8 learning context,
  `ExitDurabilityRisk` scoring, `score_exit_impact()` for strong vs. weak exit
  plans, `PostExitFollowUp` scheduling, and `build_exit_plan()` flag detection
  (e.g. `unmitigated_risks`).
- **Eight new agent tools** wrapping each module:
  `EmissionFactorsTool`, `StakeholderVoiceTool`, `EvidenceReviewTool`,
  `VerificationWorkspaceTool`, `LPNarrativeTool`, `GreenwashingReviewerTool`,
  `PortfolioQueryTool`, `ExitImpactTool`. All eight are registered in
  `create_default_tool_registry()` and exported from `openharness.impact`.

### Changed

- `openharness.impact` public API expanded with v3 exports for the eight new
  modules. Existing imports remain backwards-compatible.
- `docs/roadmap-v2.md` is unchanged but is now superseded for new tracks by
  `docs/roadmap-v3.md` and the implementation plan.

### Tests

- Added 59 new tests across `test_v3_emission_factors.py`,
  `test_v3_stakeholder_voice.py`, `test_v3_evidence_workflow.py`,
  `test_v3_verification_workspace.py`, `test_v3_lp_narrative.py`,
  `test_v3_greenwashing_reviewer.py`, `test_v3_portfolio_nlq.py`, and
  `test_v3_exit_impact.py`, plus `test_v3_tool_wrappers.py`.
- Impact-suite regression: **290 passed / 4 skipped** across the impact and
  v3 test files.

### Documentation

- `docs/roadmap-v3-implementation.md` (new): module-by-module engineering
  plan, API surface changes, testing strategy, and explicit deferred items.
- `CLAUDE.md` updated with the v3 module map and tool inventory.
- `README.md` updated with the v3 banner, feature list, and links.

### Fixed

- Greenwashing specificity classifier no longer treats single-letter unit
  tokens (`"t"`) as substring matches inside common words like
  "sustainable"; unit detection is now word-aware.
- Greenwashing reviewer now treats quantified but unmapped claims as evidence
  gaps instead of letting a number alone suppress missing IRIS+ evidence.
- Portfolio NLQ `include_unverified=True` can no longer bypass the default
  `ApprovedDataPolicy`; unverified data requires explicit
  `allow_unverified_with_warning=True`.
- LP Q&A now requires at least one verified metric citation for every answer;
  free text can add context but cannot stand alone as an LP-facing answer.
- AI extraction review queues now reject approval when an item lacks the
  minimum source references required by policy.
- Verification workspaces now validate finding evidence references against
  visible evidence and prevent terminal findings from receiving management
  responses.
- Stakeholder voice quality scoring clamps inconsistent survey/consent counts
  to valid 0-100 percentages and emits reconciliation flags instead of
  crashing Pydantic validation.
- GHG activity data-quality scoring now rewards verified activity data instead
  of penalizing it.
- Roadmap v2 collection links now handle both naive and timezone-aware ISO
  expiry timestamps without datetime comparison errors.
- Roadmap v2 collection trackers now select the latest submission by
  `submitted_at` instead of depending on input list order.
- Roadmap v2 review queues now flag zero-baseline period anomalies instead of
  silently skipping them.
- PCAF financed-emissions attribution is capped at 100% when investment value
  exceeds enterprise value.
- ISSB disclosure packs now downgrade answers to `missing` when all supplied
  source nodes are outside the provided evidence graph.
- Jurisdiction profile lookup is now case-insensitive.
- The v2 `decide_ai_extraction()` helper now rejects approvals with no source
  references.
- Roadmap v2 portfolio-query citations are now de-duplicated.

## [0.14.0] - 2026-04 - Roadmap v2 (institutional readiness)

### Added

- New research-backed institutional-readiness roadmap in `docs/roadmap-v2.md`, informed by April 2026 market signals around LP data expectations, standards interoperability, carbon accounting revisions, assurance readiness, and governed AI.
- Canonical `MetricRecord` contract plus validation/conversion helpers for the v2 data backbone. The model enforces metric ID, non-empty value, unit, period, source, owner, quality score, verification status, source type, and evidence references.
- Investee questionnaire schema generator that turns sector templates or explicit metric IDs into form sections with labels, definitions, guidance, expected units, evidence requirements, validation rules, SDG goals, and 5D tags.
- Investee collection submission models with validation, review events, flagged/resubmission/approval states, and conversion from approved submissions into canonical `MetricRecord` rows.
- Evidence graph model and builder linking impact claims, canonical metric records, targets, source evidence references, and report sections, with lineage warnings for unsupported claims and metrics without evidence.
- Reusable `assess_metric_record_quality()` rubric that scores canonical records across completeness, recency, consistency, source type, and verification level, plus `apply_quality_assessment()` for copy-on-write score updates.
- Versioned standards registry for IRIS+, EDCI, ISSB, ESRS, SFDR, GHG Protocol, PCAF, and OPIM, including aliases, status, source URLs, scopes, active-rule-pack selection, and duplicate-version protection.
- Structured hash-chained audit events for metric creation, updates, imports, approvals, and report publication, reusing the existing signed audit trail.
- EDCI completeness reporting that classifies every company/portfolio EDCI field as available, proxy, missing, or not applicable, including category rollups and support for canonical metric records.
- Scope 1/2 GHG inventory calculator with activity-data inputs, emission factor provenance, factor versioning, location- and market-based Scope 2 methods, tCO2e rollups, and data-quality scoring.
- Roadmap v2 institutional-readiness helpers covering secure collection links, multi-period collection tracking, review queues, CSV import previews, Scope 3 proxy estimates, PCAF financed emissions, carbon intensity, climate coverage dashboards, source-linked disclosure packs, jurisdiction profiles, rule-pack tests, LP export bundles, publication workflow states, controls, AI extraction review gates, immutable manifests, exception registers, contribution analysis, counterfactual questions, evidence-strength scoring, difference-in-differences, impact learning loops, metric harmonization, approved-data portfolio queries, regulatory-change monitoring, and AI governance logs.
- Report regression coverage for `_to_html()` and `_to_text()` output paths, including impact-claims rendering, escaped HTML claim text, target-progress display, and REST report input forwarding.

### Fixed

- `impact_report` now renders impact claims in text, CSV, and HTML outputs instead of dropping claim evidence outside the HTML path.
- `/api/v1/report` now forwards `impact_targets`, `metric_history`, and `impact_claims` into `ImpactReportInput`, enabling REST-driven `target_progress` reports and claim evidence rendering.
- Target-progress parsing now reads strings like `150 tCO2e` as `150` rather than accidentally including digits from units such as `CO2e`, and current reported metrics now override older metric-history values for current progress.
- HTML target tracking now displays the normalized target text from `target` when `target_description` is absent.
- MCP server wrapper correctness for all 26 impact tools:
  - `framework_assess` now supplies the required action and OPIM assessments execute against the current OPIM framework API.
  - `guided_assessment` now defaults `list_templates` to a valid template and maps submitted data to `step_data`.
  - `pipeline`, `monitoring`, `narrative`, `beneficiary_feedback`, `dd_checklist`, `cross_reference`, `document_analysis`, `portfolio_analyze`, `trend_analysis`, and `product_passport` now map MCP-friendly parameter names into the current tool input models.
  - `pitch_deck_analyze` accepts raw `text` and `url` inputs in addition to `file_path`, matching the MCP and API contracts.
- Product Passport rejects non-object JSON inputs with a clear error instead of crashing.
- Monitoring deviation alerts normalize metric IDs and parse previous values with units such as `100 tCO2e`.
- Document analysis extracts lowercase or mixed-case IRIS+ metric IDs and normalizes them to uppercase.
- Beneficiary feedback preserves valid zero values such as NPS `0`.

### Documentation

- README now links to `docs/roadmap-v2.md` and notes completion of the Phase 11 report reliability items plus the first six v2 implementation sprints.
- `docs/roadmap-v1.md` now marks Phase 11 report snapshot, target-progress, and impact-claims items as done.
- README MCP section now documents stdio/SSE usage, Cursor/VS Code setup, all 26 MCP tools, all 5 MCP resources, and example MCP prompts.

### Tests

- Full-suite verification after the report and roadmap updates: `1019 passed / 7 skipped / 1 xfailed`.
- Added regression coverage for MCP wrapper field mapping and high/medium impact-tool bug fixes.
- Verified direct MCP smoke coverage for 26 unique tools plus 5 resources.

## [0.14.0] - 2026-04-21

### Added — Phases 15.6 → 20 shipped in one drop

This release closes out the remainder of Phase 15.6 and lands the
scaffolding for **every roadmap item from Phase 15 to Phase 20**.
Each new subsystem ships a Pydantic schema, a deterministic offline
default (so demos and tests work with no network / no secrets), and a
pluggable Protocol so GP integrations can swap in live providers
without touching the core engine.

**Phase 15.6 (remaining):**

- **`LLMClaimExtractor`** (`openharness.impact.extractors.llm_extractor`) — OpenAI-compatible claim extractor with offline-safe regex fallback, `<think>`-tag stripping and strict-JSON schema validation. Registered as `id="llm"`.
- **`LLMSourceVerifier`** (`openharness.impact.extractors.llm_verifier`) — URL-grounded verifier with offline-safe heuristic fallback; never cites a URL the caller didn't pre-register.
- **Report branding from `fund_thesis.yaml`** (`openharness.impact.branding`) — fund-specific colours / logo / footer text injected into every HTML surface via a 4-line CSS override; colour values are validated against `#[0-9a-fA-F]{3,8}` to prevent style injection.
- **DD Questionnaire v2 — branching** (`openharness.impact.questionnaire_v2`) — `BranchRule` engine with `contains` / `equals` / `missing` predicates, follow-up expansion and a Word export that renders only the fired follow-ups.
- **SSE streaming** (`openharness.web.streaming`) — `/api/v1/stream/echo` demo endpoint plus `register_sse_endpoint(name, handler)` for plug-ins. Pure-stdlib wire format, works with browser `EventSource`.

**Phase 15 leftover → Phase 16:**

- **`openharness.impact.registries`** — unified `CreditRegistry` protocol covering Verra (VCS), Gold Standard, Puro.earth (CORCs) and BioCredits, plus `rollup_credits` / `PortfolioCredits` roll-up.
- **`openharness.impact.returns`** — `compute_moi` (Multiple of Impact) and `compute_irr` (Newton-Raphson financial + impact-adjusted IRR, basis-points lift). No scipy / numpy dependency.
- **`openharness.impact.external_benchmarks`** — GIIN Compass-style `ExternalBenchmarkProvider` Protocol with an offline sector-percentile snapshot (10 sectors × 5 dimensions) and `contextualise()` quartile narrative.
- **`openharness.impact.blended_finance`** — term-sheet templates for Impact-Linked Loans (3-step rate schedule), Social Outcomes Contracts / DIBs and Impact-Carry structures.
- **`openharness.impact.lp_portal`** — ILPA-aligned Capital Account Statement, Impact Dashboard and Audit Trail views built on the hash-chained signed-feed.
- **`openharness.impact.marketplace`** — in-memory publish / subscribe / compare for impact theses with Jaccard-based similarity over SDGs, sectors and geographies.

**Phase 17 — Assurance & Audit:**

- **`openharness.impact.assurance`** — ISAE 3000 / AA1000AS / ISAE 3410 input-pack generator (management assertion, subject matter, criteria, evidence index, chain head hash).
- **`openharness.impact.csrd_wizard`** — CSRD / ESRS double-materiality wizard (10 ESRS topics, impact + financial scores, threshold-driven shortlist of ESRS sections).
- **`openharness.impact.issb_reporting`** — IFRS S1 / S2 machine-readable pack (Governance → Strategy → Risk → Metrics & Targets, Scope 1/2/3, physical + transition risks, science-based target).
- **`openharness.impact.audit_trail`** — immutable, hash-chained append-only log for every scoring / classification / DD decision.
- **`openharness.impact.soc2_checklist`** — SOC 2 TSC + ISO/IEC 27001:2022 readiness checklist with 26 default controls and a completion-percentage report.

**Phase 18 — Causal & Scientific Rigor:**

- **`openharness.impact.causal`** — RCT / DID / RDD / IV / PSM study schema plus `update_counterfactual_prior` (design-quality × sample-size weighted posterior).
- **`openharness.impact.bayes`** — beta-binomial conjugate updater with 95% credible interval and `probability_above(threshold)`. Zero external deps — Acklam's inverse-normal approximation built in.
- **`openharness.impact.meta_analysis`** — J-PAL / 3ie / Cochrane schema + fixed-effect inverse-variance pooling and `deviation_flag()` that fires when a claim's stated effect is >2σ from the pooled estimate.
- **`openharness.impact.spillover`** — leakage + spillover adjustment per ToC node, applied in the GHG-Protocol-recommended order.
- **`openharness.impact.sroi`** — SROI ratio with all 4 levers (deadweight, attribution, displacement, drop-off), discounting per HMT Green Book defaults, and a deterministic ±20% per-lever sensitivity matrix.

**Phase 19 — Geospatial & Primary Data:**

- **`openharness.impact.geospatial`** — `SatelliteProvider` Protocol + deterministic hash-based offline stub covering GFW tree-cover-loss, VIIRS nightlights, Sentinel-5P NO2/CH4 and ESA WorldCover.
- **`openharness.impact.surveys`** — CSV loader (SurveyCTO / KoboToolbox / ODK / 60 Decibels shape) + categorical / numeric / worker-voice aggregators.
- **`openharness.impact.worker_voice`** — aggregates survey data into a `[-1, +1]` **Who-lift** using NPS, grievance rate and anonymity-guarantee signals.
- **`openharness.impact.ecosystem_services`** — InVEST / ARIES-shaped ecosystem valuation with offline unit-value defaults for 5 land-cover classes × 4 services.

**Phase 20 — Global Reach:**

- **`data/i18n/dashboard_keys.yaml`** — 6-language parity (en / es / fr / pt / zh / ar) for dashboard + web-console labels, loaded via the new `get_dashboard_strings()` helper.
- **4 regional `fund_thesis.*.yaml` packs** (Climate-First EU, Inclusive-Finance Africa, Gender-Lens South Asia, Indigenous-Led NA) — copy to `data/fund_thesis.yaml` to activate.
- **`openharness.impact.regulatory_packs`** — per-jurisdiction disclosure regime reference for SFDR, CSRD, UK FCA-SDR, US SEC-ESG, HKEX-ESG, AASB-S2 and global ISSB.
- **`openharness.impact.fx`** — `FXRateProvider` Protocol with static USD-pivot snapshot (20+ currencies) and composite-chain provider for live-first / fallback-offline deployments.

**SDK facade:** every new module exposes a one-line entry point on `ImpactVision` (e.g. `iv.compute_moi(...)`, `iv.build_assurance_pack(...)`, `iv.double_materiality(...)`, `iv.regulatory_pack("EU-SFDR")`, `iv.convert_currency(1000, from_ccy="MYR", to_ccy="USD")`).

### Tests

- New `tests/test_phases15_20.py` with 43 regression tests covering every subsystem above.
- Impact subset at v0.14.0 (clean run of `test_impact.py` + `test_phase11_fixes.py` + `test_phases12_15.py` + `test_phases15_20.py`): **150 passed / 4 skipped / 0 failed** (154 collected). Ruff clean.

## [0.13.0] - 2026-04-21

### Added — DD Questionnaire Helper, Word export & Web Console

- **DD Questionnaire Helper** (`openharness.impact.report_templates.dd_report_html.render_dd_questionnaire_html`): the DD HTML output has been re-framed from a *coverage report* to an *actionable questionnaire helper*. Sections are now ordered as **1. Key risk areas → 2. Information request (questionnaire to send) → 3. Evidence & document gaps → 4. Coverage snapshot → 5. By category → 6. Addressed (appendix) → 7. Evidence levels**. The *information request* sorts unanswered questions first by severity (high / medium / low priority callouts), then by the natural DD sequence (Thesis → ToC → What → Who → How-much → Contribution → Risk → Measurement → Governance → Sector → Exit). Each question card carries probe-further prompts, supporting-document asks and an empty "Founder response" slot so the analyst can use it as a live working document.
- **`ImpactVision.render_dd_questionnaire_html(...)`** — SDK shortcut (same kwargs as `render_dd_report_html`, which remains as a backwards-compatible alias).
- **`ImpactVision.render_dd_questionnaire_docx(...)`** + `openharness.impact.report_templates.render_dd_questionnaire_docx`: editable Word `.docx` export of the questionnaire helper (requires optional `python-docx`). Mirrors the HTML information request with heading-level category grouping, evidence checklists, response boxes and a sign-off block.
- **Web Console** (`openharness.web`, `impact-vision serve-web`, default port `8787`): single-file SPA mounted on top of the FastAPI gateway. Lists all 26 tools in a searchable sidebar, renders a dynamic parameter form per tool, and `POST`s to `/api/v1/*`. No build step, no JS framework. Positioned as the Impact-Vision equivalent of `sst/opencode` / `siteboon/claudecodeui` / `getAsterisk/claudia`.
- `openharness.web.console.render_console_html()` and `openharness.web.console.console_router()` for embedding the console into any existing FastAPI app.

### Fixed

- **Impact-report scoring rationale table** no longer overflows on 1080 px / tablet layouts. New `.rationale-table-wrap` scroll container, `<colgroup>` fixed column widths, word-wrapped driver cell and a compact mobile breakpoint (see `impact_report_tool.py`).
- **MCP server bootstrap** (`openharness.impact.mcp_server`) now tolerates both old and new FastMCP constructor signatures (the `version` / `description` kwargs were dropped in recent FastMCP releases). Unblocks `tests/test_phase11_fixes.py::TestMCPResources` on CI.
- **Ruff lint** — trimmed 5 unused imports flagged by CI: `SourceVerifier` / `ClaimExtractor` re-exports now carry explicit `noqa: F401` because they are documented public re-exports, plus unused `typing.Iterable` / `typing.Literal` imports in `signed_feed.py` and `tenancy.py` removed. `ruff check src/` is now clean.

### Tests

- `tests/test_phases12_15.py`: new test classes `TestDDQuestionnaireHelper` (alias parity, risk-first section ordering, docx round-trip) and `TestWebConsole` (SPA markers, `/` + `/console` routes via `FastAPI.TestClient`). Existing `test_dd_report_html_contains_key_sections` updated to match the new `<title>` and section anchors.
- Impact subset total at v0.13.0 (clean run of `test_impact.py` + `test_phase11_fixes.py` + `test_phases12_15.py`): **104 passed / 4 skipped / 0 failed** (108 collected; the 4 skipped cases require the optional `mcp` package).

### CLI

- New `impact-vision serve-web` command wrapping `uvicorn` around `openharness.web.app:app`.

## [0.12.0] - 2026-04-21

### Added — Report visuals overhaul

- `openharness.impact.report_templates.report_v2`: shared HTML chrome (modern hero banner, at-a-glance KPI strip, sticky section TOC, strengths/watch-outs callouts, print-first CSS, SDG colour swatches) used by every HTML surface.
- `openharness.impact.ic_memo.render_ic_memo_html` + `render_ic_memo(output_format="html")`: self-contained, print-ready HTML IC memo with thesis fit, 5-dimension rollup, SDG alignment, DD & greenwashing KPIs, IC gate detail and recommendation blocks.
- `openharness.impact.report_templates.dd_report_html.render_dd_report_html` (+ `save_dd_report_html`): one-page DD coverage briefing with category roll-up, NESTA evidence levels, priority gaps and ready-to-send follow-up prompts.
- `ImpactVision.render_dd_report_html(...)`: SDK shortcut that runs the DD engine and writes the HTML in one call.
- Main Impact Report (`tools/impact/impact_report_tool._to_html`): KPI strip + strengths / watch-outs / next-steps callouts in the Executive Summary, sticky table-of-contents sidebar, anchor IDs on every section (`#sec-5d`, `#sec-sdg`, `#sec-gap`, `#sec-greenwashing`, …).

### Fixed / Changed

- README: removed the superseded **"Correctness & linkage issues found"** checklist and the **"Engineering housekeeping"** block; they were implementation notes that are now tracked privately. Updated every MCP tool count reference from 25 → **26**.
- `ImpactVision.render_ic_memo(...)` now accepts `output_format="html"` (in addition to `markdown` / `docx` / `pptx`). Path-writing semantics match the other formats.

### Tests

- `tests/test_phases12_15.py::TestHtmlRenderers` — 7 new tests covering IC memo HTML (sections, KPI tiles, TOC, file-write), DD HTML (sections, empty-text graceful path, file-write), main Impact Report anchor IDs, and the v2 chrome helpers (`render_hero`, `render_kpi_strip`, `render_toc`, `sdg_swatch`, `wrap_document`).
- Total impact subset: **99 passed / 4 skipped / 0 failed**.

## [0.11.0] - 2026-04-21

### Added — Phase 15: Platform & Collaboration

- `openharness.impact.tenancy`: multi-tenant model with `Tenant`, `User`, `Role`, `Permission`, `RBACPolicy`, `InMemoryRBACStore` and built-in roles (viewer, analyst, ic_member, lp_relations, tenant_admin).
- `openharness.impact.plugins`: per-GP plug-in entry-point discovery for extractors, verifiers, benchmarks, fund-thesis loaders and report renderers.
- `openharness.impact.signed_feed`: HMAC-signed, hash-chained `ReportFeed` for tamper-evident LP report archives. Pluggable `Signer` Protocol for KMS / Ed25519 backends.
- `openharness.impact.sdk.ImpactVision`: single high-level façade for the full impact workflow (assessment → IC gate → IC memo → portfolio rollup → LP calendar → DD coverage → greenwashing screen).

## [0.10.0] - 2026-04-21

### Added — Phase 14: Real Evidence & LLM Intelligence

- `openharness.impact.extractors`: pluggable `ClaimExtractor` and `SourceVerifier` Protocols with a registry; ships with `noop`, `regex` and `heuristic` adapters so the engine has zero hard dependency on any LLM vendor.
- `openharness.impact.toc_graph`: Theory-of-Change → Mermaid `flowchart` renderer (Inputs → Activities → Outputs → Outcomes → Impact) with IRIS+ / SDG node annotations.
- `openharness.impact.counterfactual`: GIIN COMPASS additionality templates (investor / enterprise / beneficiary) with point and range estimates.
- `scripts/refresh_iris_catalog.py`: refreshes the IRIS+ JSON catalog from the latest GIIN Excel and emits a structured diff log.

## [0.9.0] - 2026-04-21

### Added — Phase 13: Regulatory Completeness

- `openharness.impact.frameworks.pcaf`: PCAF Global GHG Accounting & Reporting Standard — per-asset-class attribution + portfolio rollup with weighted data quality score.
- `openharness.impact.frameworks.sbti`: SBTi Net-Zero Standard v1.2 alignment checker (1.5 °C pathway, scope-3 materiality, 2050 cap).
- `openharness.impact.frameworks.eu_taxonomy`: EU Taxonomy alignment % across the 6 environmental objectives, DNSH and Minimum Safeguards.
- `openharness.impact.frameworks.tnfd`: TNFD v1 — all 14 disclosures + LEAP (Locate / Evaluate / Assess / Prepare) progress.
- `openharness.impact.frameworks.cdp`: CDP questionnaire intake (climate / water / forests) with critical-question gap detection.

## [0.8.0] - 2026-04-21

### Added — Phase 12: Fund Workflow

- `data/fund_thesis.example.yaml` + `openharness.impact.fund_thesis`: fund-specific YAML for SDG / 5D weights, IC gate criteria, adverse thresholds, reporting cadence.
- `openharness.impact.deal_gate`: pass / warn / fail IC gate engine with per-check diagnostics.
- `openharness.impact.portfolio_rollup`: capital-weighted aggregation of 5D and SDG scores (replaces meaningless arithmetic mean).
- `openharness.impact.lp_calendar`: 12-month LP report deliverables generator (ILPA-ESG, GIIN-IRIS, EDCI, SFDR PAI, fund letter).
- `openharness.impact.ic_memo`: IC memo generator. Markdown by default; Word (`python-docx`) and PowerPoint (`python-pptx`) renderers behind optional deps.

## [0.7.0] - 2026-04-21

### Fixed — Phase 11: Correctness & Credibility

All 12 issues identified in the v0.6 codebase review have been resolved with regression tests in `tests/test_phase11_fixes.py`:

- MCP resource runtime bugs (`mcp_server.py`) fixed and tested.
- DD evidence-level scoping limited to matched snippets; word-boundary keyword matching enforced.
- `data/core_metric_set_per_sdg.yaml` curated set of IRIS+ metrics per SDG; SDG coverage now uses the core set with `SDGAlignment.scoring_basis` provenance.
- 5-Dimension `_score_dimension` floor inconsistency removed; per-dimension cap applied when too few metrics are reported.
- `_ADVERSE_METRICS_BY_SECTOR` rewritten with genuinely adverse metrics (NPL ratio, GHG intensity, worker fatalities, etc.).
- All 14 mandatory + 9 optional SFDR PAI indicators now have populated `iris_cross_refs`.
- Cross-reference map extended with SASB metric codes plus TNFD / PCAF / EU Taxonomy / CDP / SBTi codes and reverse-lookup helpers.
- Every `SectorBenchmark` now carries `source`, `source_year`, `confidence`.
- Deferred package-rename plan documented in `CLAUDE.md`.

## [0.6.0] - 2026-04-16

### Added — Phase 10: Platform Integration & Developer Experience

**MCP Server** (10.1)
- New `mcp_server.py`: FastMCP-based MCP server exposing all 25 impact tools as MCP tools with proper JSON Schema
- 5 MCP resources: `impact://catalog/stats`, `impact://dd-checklist/categories`, `impact://frameworks/list`, `impact://cross-reference/{metric_id}`, `impact://sdg/goals`
- CLI command: `impact-vision serve-mcp` with stdio (default) and SSE transport options (`--transport sse --port 8765`)

**Claude Code / AI Agent Integration** (10.2)
- Ready-to-use `examples/claude_desktop_config.json` with 3 connection methods (global install, uv, python module)
- `docs/cursor-integration.md`: comprehensive guide for Cursor, VS Code, and Claude Desktop with tool table, resource table, usage examples, agent-to-agent protocol, and troubleshooting

**Full REST API** (10.3)
- Expanded `api_gateway/router.py` from 7 to 25+ endpoints covering all impact tools
- New endpoints: `/api/v1/framework`, `/api/v1/cross-reference`, `/api/v1/risk-opportunity`, `/api/v1/metric-recommend`, `/api/v1/exclusion-screen`, `/api/v1/report`, `/api/v1/pitch-deck`, `/api/v1/ddq-export`, `/api/v1/pipeline`, `/api/v1/monitoring`, `/api/v1/improvement-advisor`, `/api/v1/narrative`
- API key authentication via Bearer token or `X-API-Key` header (env: `IMPACT_VISION_API_KEY`)
- Batch API: `POST /api/v1/batch` for multi-company assessment with async job processing and `GET /api/v1/batch/{job_id}` status polling
- Enhanced webhooks: HMAC signature verification, 5 event types (assessment_complete, score_change, alert_fired, metric_update, threshold_breach), webhook CRUD (create/list/delete)

**Multi-Language & Localization** (10.4)
- New `data/i18n/report_strings.yaml`: 30+ report labels in 6 languages (en, es, fr, pt, zh, ar)
- New `data/i18n/dd_checklist_*.yaml`: localized DD questions and categories in 5 languages (es, fr, pt, zh, ar)
- New `data/i18n/system_prompts.yaml`: agent persona preambles in 6 languages
- New `src/openharness/impact/i18n.py`: i18n utility module with fallback to English

## [0.5.0] - 2026-04-16

### Added — Phase 9: LLM Intelligence & Automation

**LLM-Guided Impact Improvement** (9.1)
- New `improvement_advisor_tool.py`: actionable recommendations per weak dimension (metrics to track, programs to implement, partnerships to pursue)
- Peer comparison insights: sector-specific benchmarking showing typical metric tracking patterns for higher-scoring peers
- SDG opportunity finder: identifies untapped SDG alignments based on company operations, geography, and sector affinity
- New `narrative_tool.py`: LLM-ready structured prompts for executive summaries, key findings, impact narratives, and case studies with audience-adaptive tone

**Smart Document Analysis** (9.2)
- New `document_analysis_tool.py`: multi-document consistency analysis comparing claims and metrics across pitch decks, annual reports, and impact reports
- Document change detection: identifies new/changed/removed metrics, SDG alignments, and quantitative data between document versions
- Claim verification agent: validates impact claims against document text with evidence extraction and gap identification

**Conversational Impact Assessment** (9.3)
- New `guided_assessment_tool.py`: structured step-by-step assessment workflow with predefined templates for screening, due diligence, and monitoring stages
- Progressive data collection: tracks completed/pending data steps across sessions via `AssessmentStore`, incrementally collects missing information
- Assessment templates by deal stage: screening (6 steps), due diligence (8 steps), and monitoring (6 steps) with different depth levels

## [0.4.1] - 2026-04-16

### Added — Phase 8: Pipeline & Portfolio Management

**Pipeline Management** (8.1)
- New `pipeline_tool.py`: CRUD operations for managing companies through 8 pipeline stages (sourcing → screening → DD → IC review → invested → monitoring → exited → passed)
- Pipeline models: `PIPELINE_STAGES`, `PipelineEntry`, `StageTransition`, `MonitoringSchedule`, `MonitoringAlert` in `models.py`
- SQLite tables: `pipeline`, `stage_transitions`, `monitoring_schedules`, `monitoring_alerts` in `storage.py`
- Stage transition tracking with actor, rationale, and audit log
- HTML pipeline dashboard with Plotly funnel chart, sector pie, SDG distribution, and company table
- Pipeline CSV/XLSX import/export with full field mapping

**Continuous Monitoring** (8.2)
- New `monitoring_tool.py`: set monitoring schedules, record metric updates, detect deviations, trigger re-assessments, manage alerts
- Monitoring schedules with configurable frequency (monthly/quarterly/semi-annual/annual) and per-metric alert thresholds
- Automated re-assessment: re-runs 5D/SDG scoring and creates alerts for significant score changes
- Alert system: metric_deviation, target_at_risk, evidence_expired, review_due, score_change, risk_increase

**Per-Project Reporting** (8.3)
- `report_type="target_progress"`: focused target progress report with trajectory projections
- `report_type="lp_ready"`: LP-formatted individual company report with executive summary
- Period-over-period comparison (via Phase 7's comparison mode)

**Aggregate Portfolio** (8.4)
- `portfolio_analyze` new actions: `rollup`, `benchmark`, `lp_report`, `attribution`
- Portfolio roll-up analytics: fund-level 5D scores, SDG coverage, aggregate metrics
- Cross-company benchmarking: rank by 5D score, coverage, dimension leaders/laggards
- Fund-level LP report in ILPA/GIIN format with additionality assessment
- Impact attribution by company, sector, geography, and SDG

## [0.4.0] - 2026-04-16

### Added — Phase 7: Enhanced Analysis & Reporting UX

**Interactive HTML Report** (7.1)
- 5-Dimension overlay panel: click any dimension row to expand tracked/untracked metrics, gaps, and improvement suggestions
- SDG drill-down: click SDG rows to expand evidence chains, matched targets, and gap recommendations
- Metric tracking dashboard: card grid with tracked/gap status for all recommended metrics
- Claim evidence cards: expandable cards for each impact claim with confidence bars, NESTA evidence levels, mapped metrics/SDG targets, and negation warnings
- PDF export: optional WeasyPrint integration with print-friendly CSS `@media print` rules; falls back to HTML with browser-print instructions
- Report comparison mode: side-by-side delta scoring from stored assessments (5D dimensions + SDG scores)

**Evidence & SDG Mapping** (7.2)
- Evidence chain visualization: `SDGAlignment.evidence_chain` field populated in `map_sdg_alignment()` showing claim→metric→evidence→SDG target with confidence
- SDG gap recommendations: `generate_sdg_gap_recommendations()` in `sdg_mapper.py` for partial alignments (missing metrics, weak descriptions, missing themes, unmapped targets)
- Impact pathway diagrams: auto-generated Theory of Change flow (Inputs→Activities→Outputs→Outcomes→Impact) rendered as pure CSS flexbox in HTML reports

### Changed
- `SDGAlignment` model: added `evidence_chain: list[dict]` field
- `ImpactReportInput`: added `output_format="pdf"` option and `compare_assessment_id` field
- SDG alignment data now includes per-goal recommendations in report output
- HTML report CSS: 7 new component styles (overlay, drill-down, metric grid, claim cards, pathway, print, comparison)

## [0.3.2] - 2026-04-16

### Changed — Documentation

- README.md: comprehensive update reflecting all v0.3.1 features (10 frameworks, 17 tools, 18 sectors, 122 DD questions, 59 cross-references, 820+ tests)
- README.md: added new usage examples for ISSB, ESRS, greenwashing, compliance, verification, and product passport
- README.md: DD categories reorganized into collapsible sections (core + 15 sector-specific)
- README.md: added Regulatory Compliance and Greenwashing/NLP detection tables to Standards Supported
- CLAUDE.md: full rewrite to match current v0.3.1 architecture
- ROADMAP.md: added Phase 7-10 next-version roadmap (see below)

## [0.3.1] - 2026-04-16

### Added — Phase 6: Architecture & Quality

**Report Template Engine** (6.1)
- `report_templates/` module with Jinja2-based HTML report generation
- Shared CSS extracted to `REPORT_CSS` constant for reuse across report types
- `render_header()` and `render_footer()` functions with Jinja2 templates and string-format fallback
- `render_html_report()` API entry point for clean report generation
- SDG color map extracted to `get_sdg_colors()` utility

**SQLite Persistence Layer** (6.2)
- `storage.py` with `AssessmentStore` class backed by SQLite
- Company assessment save/retrieve/update/delete with JSON serialization
- Session history logging: track all tool invocations per company per session
- Thread-safe connection management with lazy schema initialization
- `get_assessment_store()` singleton accessor

**Circular Import Audit** (6.3)
- Audited all inter-framework imports — no circular dependencies found
- One intentional lazy import in `risk_opportunity.py` (loads scoring config) documented

**Test Coverage Expansion** (6.4)
- `test_report_generation.py`: 18 tests for HTML, CSV, text, JSON output and template engine
- 5 new tests for `AssessmentStore` persistence layer (save, retrieve, update, delete, session history)
- 5 new framework tests: ISSB S1/S2 readiness, ESRS standards/double materiality/data points
- Total tests: 820 passed (up from 797)

## [0.3.0] - 2026-04-16

### Added — Phase 5: Scoring Engine Improvements

**Expanded Sector Coverage** (5.1)
- 10 new sectors with 5D baselines: Manufacturing, Transport/Logistics, Construction, Tourism, Retail, Mining/Extractives, Media, Professional Services, Waste Management, ICT
- SDG sector relevance mappings for all new sectors in `sdg_keywords.yaml`
- Sector benchmark data for all new sectors (5D averages, SDG primaries, coverage, typical metrics)
- 26 sector-specific DD questions across 10 new categories (manufacturing, transport, construction, tourism, retail, mining, media, waste management, ICT, professional services)
- Theme inference keywords for new sectors in `scoring_config.yaml`

**Improved Contribution / Additionality Assessment** (5.2)
- `assess_additionality()` function with 20+ additionality signal phrases (first-of-kind, catalytic, underserved market, etc.)
- Additionality heuristics boost the contribution baseline when multiple signals detected
- Counterfactual review prompt generated for human review when contribution score is low
- Additionality signals and counterfactual prompt surfaced in 5D assessment tool output

**Negative Impact / Do No Harm Assessment** (5.3)
- Adverse impact penalty (0–1.5) on risk dimension when harm indicators found without mitigation language
- Exclusion flag penalty (0–1.0) reduces risk score for companies with norms-based exclusion flags
- `check_controversy_signals()` stub for future external data source integration (RepRisk, Sustainalytics)

**Expanded Cross-Reference Map** (5.4)
- 15+ new cross-framework mappings: land use, community development, training outcomes, financial inclusion depth, access to services, product safety, customer satisfaction
- Metric-level SASB cross-references: employee turnover, benefits, product design, lifecycle management
- Expanded GRI mappings: tax transparency, indirect economic impact, non-discrimination, freedom of association, indigenous rights, human rights assessment, marketing/labeling

**Enhanced Risk/Opportunity Assessment** (5.5)
- 8 new risk categories: concentration, regulatory/policy, compliance, reputational, greenwashing, exit, data integrity, single-source
- Likelihood x severity risk matrix (low/medium/high) replaces severity-only scoring
- `risk_level` field (critical/high/medium/low) added to each detected risk
- 10 new opportunity triggers: circular economy, digital, affordable housing, clean water, nutrition, climate adaptation, youth, biodiversity, electrification, telemedicine

**Improved ImpactClaim Model** (5.6)
- `calibrated_confidence()` static method: logarithmic curve replacing naive `min(1.0, hits*0.15)`; bonuses for metrics, quantitative data, and evidence level
- `evidence_strength` field: NESTA-inspired 1–5 scale (narrative → RCT/meta-analysis)
- `negation_detected` field: flags claims found in negation context
- `entities` field: extracted stakeholders, geographies, and outcomes from claim text

## [0.2.1] - 2026-04-16

### Added — Phase 4: Regulatory & Advanced Detection

**EU CSRD / ESRS Double Materiality** (4.1)
- `esrs.py` framework module: 11 ESRS standards (cross-cutting, E1–E5, S1–S4, G1) with 84+ data points
- `assess_double_materiality()` evaluates impact and financial materiality per topic using keyword matching and reported metrics
- ESRS integrated as framework option in `FrameworkTool` with full scan/list support
- ESRS cross-references added to `CrossReference` model and mapping table (E1-6, E4-5, S1-6, S1-9, G1-3, etc.)

**EU Green Claims Directive Compliance** (4.2)
- `assess_green_claims_compliance()` checks environmental claim substantiation, LCA requirements, and independent verification needs
- Environmental claim pattern detection ("carbon neutral", "eco-friendly", "net zero", etc.)
- LCA trigger term identification for claims requiring life-cycle assessment evidence

**UK FCA Anti-Greenwashing Rule** (4.2)
- `assess_fca_anti_greenwashing()` checks fund names and descriptions against FCA prohibited terms
- Sustainability Disclosure Labels (SDR) classification: "Sustainability Focus", "Improvers", "Impact"
- Fund naming convention validation per FCA PS23/16 guidance

**SFDR Enhancements** (4.3)
- `classify_sfdr_article()` for Article 6/8/9 fund classification based on description and sustainability objectives
- `OPTIONAL_PAI_INDICATORS` — 9 additional Table 2 indicators (biodiversity, water, waste, social/employee)
- `assess_sfdr_entity_vs_fund()` distinguishes entity-level vs. product-level PAI reporting
- SFDR Annex III/IV disclosure template added to LP DDQ exporter

**NLP-Enhanced Greenwashing Detection** (4.4)
- Green Authenticity Index (GAI) — scores specificity of environmental claims (0–100)
- Cheap Talk Index (CTI) — measures proportion of vague commitments vs. substantive evidence
- Sentiment deflection detection — flags overly positive tone masking negative information
- Claim decomposition — breaks compound claims into verifiable sub-claims with classifications
- ClimateBERT integration stub for future transformer-based climate text analysis

**Digital Product Passport** (4.5)
- `ProductPassportTool` — import EU ESPR / DPP JSON data, map categories to IRIS+ metrics
- 9 DPP categories (durability, recyclability, carbon footprint, etc.) with IRIS+/ESRS/SDG mappings
- Completeness assessment with product-specific priority scoring

## [0.2.0] - 2026-04-16

### Added — Phase 3: Missing Features

**LLM-assisted narrative generation** (3.1)
- `narrative_mode` parameter in DDQ export and impact report tools (`data` or `narrative_prompt`)
- `draft_review` flag wraps output with DRAFT markers for human review before distribution
- Structured prompts for executive summary, key findings, and recommendations

**Beneficiary feedback integration** (3.2)
- `BeneficiaryFeedback` Pydantic model: satisfaction, NPS, QoL improvement, themes, quotes, segments
- `BeneficiaryFeedbackTool`: import (JSON/CSV), analyze (quality scoring + NESTA level), summary
- Beneficiary feedback auto-fills stakeholder voice questions (SV01-SV03) in DD checklist
- Beneficiary feedback section in HTML reports with score cards, themes, and quotes

**Real benchmarking with peer data** (3.3)
- `PeerDataStore` for loading anonymized peer CSV/JSON data and calculating percentile ranks
- Percentile ranking from built-in benchmarks using normal distribution estimation
- GIIN Annual Impact Investor Survey benchmark data (308 respondents, 2023)
- `compare_to_giin_survey()` for fund-level comparison across 5D, coverage, SDG metrics

**REST API gateway** (3.4)
- FastAPI endpoints: `/api/v1/score`, `/sdg-map`, `/data-quality`, `/greenwashing`, `/gap-analysis`
- `/api/v1/validate` — metric data validation pipeline
- `/api/v1/webhook` — register webhook callbacks for metric update events
- CORS support and health check endpoint

**Scenario modeling** (3.5)
- Portfolio `what_if` action: add/remove companies and see score deltas
- Metric recommender `optimize_for_sdg_coverage` mode: prioritizes metrics filling SDG gaps
- Interactive HTML checkbox state persists via localStorage

**Audit trail & verification** (3.6)
- `verification_status` field on MetricValue: `self_reported` / `management_verified` / `third_party_verified` / `audited`
- `AuditTrailEntry` model and `audit_trail` field on Company
- `VerificationPrepTool`: readiness check, evidence map, IFC OPIM alignment
- `ifc_opim.py` framework module: 9 Operating Principles with verification requirements

**Localization** (3.7)
- Multi-language PDF detection (Spanish, French, Portuguese, Chinese markers)
- Localized SDG keyword dictionaries: `sdg_keywords_es.yaml`, `sdg_keywords_fr.yaml`, `sdg_keywords_pt.yaml`

**Dashboard enhancements** (3.8)
- Portfolio overview KPIs: avg 5D score, coverage, company count, total metrics, SDG coverage
- GIIN Survey benchmark comparison in portfolio tab
- Interactive company drill-down: select company → radar chart + SDG alignments + details
- Geography field support in CSV upload

### Changed

- Total registered tools: 20 (added BeneficiaryFeedbackTool, VerificationPrepTool)
- All 112 impact tests passing

---

## [0.1.8] - 2026-04-16

### Added

**Fund-level analytics** (new module `fund_analytics.py`)
- Weighted SDG contribution: materiality-adjusted SDG scoring across portfolio companies
- Impact-weighted returns stub: placeholder for Harvard BSG/GSG methodology integration
- Portfolio additionality assessment: heuristic scoring with classification (strong/moderate/weak)
- All three analytics integrated into portfolio tool aggregate output and text display

**SASB YAML override support**
- SASB module now loads additional industries and keyword overrides from `data/sasb_overrides.yaml`
- Enables fund-specific SASB customization without code changes

**Context window validation for SDG keywords**
- Keywords must appear in substantive context (>=5 words within 80-char window)
- Prevents false SDG matches from isolated keyword mentions in headers or table labels

### Changed

- Portfolio tool text output now includes weighted SDG contribution, additionality assessment, and impact-weighted returns sections
- Portfolio aggregate payload includes `weighted_sdg_contribution`, `additionality`, and `impact_weighted_returns` fields

---

## [0.1.7] - 2026-04-16

### Added

**Provenance badges in HTML reports**
- 5D report now shows Confidence card (Evidence-Based/Partial/Estimated) with color coding
- Per-dimension provenance column in the assessment table
- Disclaimer banner when scores are estimated or partially evidenced

**Configurable scoring threshold**
- `min_metrics_for_above_baseline` now configurable via `data/scoring_config.yaml`
- Funds can set threshold from 1 (seed-stage) to 5+ (growth-stage)

**SDG keywords externalized to YAML**
- Created `data/sdg_keywords.yaml` with sector-SDG relevance and keyword mappings
- SDG mapper now loads keywords from YAML with fallback to hardcoded defaults
- Enables fund-specific SDG keyword customization without code changes

**Geography-aware SDG scoring**
- SDG mapper applies geographic relevance boosts (15 regions/countries)
- Portfolio tool now tracks geography distribution across companies
- Pitch deck analyzer auto-detects geography from document text (19 regions + headquartered pattern)
- Company YAML export includes geography field

**Negation detection in SDG and claim extraction**
- SDG keyword matching now skips negated keywords (30-char window check)
- Pitch deck claim extractor reduces confidence for negated impact claims

**Greenwashing integration expanded**
- DataQuality tool now flags impact-washing risk when >25% of metrics are placeholders
- Pitch deck analyzer detects specific greenwashing signals (aspirational bias, buzzword density, unsubstantiated claims)
- Impact Risk & Opportunity tool includes greenwashing risk score and flags

**Exclusion screening in DD workflow**
- 5D assessment tool now runs quick exclusion check before scoring
- Warning displayed when exclusion flags are triggered

**Target tracking in HTML reports**
- Impact targets displayed as progress bars with on-track/behind/exceeded/at-risk status icons
- Target summary showing overall progress across all metrics

**ISSB IFRS S2 framework** (new)
- Climate-related Disclosures framework with 4 pillars and 13 disclosures
- Maps to TCFD equivalents for backward compatibility
- Readiness assessment covering governance, strategy, risk management, metrics
- Integrated into framework_tool (list + assess) and multi-framework scan
- TCFD module notes subsumption by ISSB S2

**ISSB cross-references**
- Added `issb` field to CrossReference model
- GHG-related cross-references now include ISSB S2-MT-1 mappings
- Cross-reference display includes ISSB column

**LP DDQ improvements**
- ILPA sections 10.1-10.8 now generate policy/governance structure references
- Case study placeholders with structured format (company, outcome, method, attribution)
- Measurement systems, team training, and outcomes sections with scaffolding

**Comprehensive test coverage**
- Added 24 new tests: DataQuality, Risk/Opportunity, MetricRecommender, Portfolio, geography detection, SDG geo boost, SDG YAML loader, configurable threshold, edge cases
- Total test count: 71 tests all passing

## [0.1.6] - 2026-04-16

### Added

**SDG provenance tracking**
- SDG alignment results now include `provenance` field (`evidence-based`, `partial`, `estimated`)
- SDG mapper sets provenance based on matched metric count (≥3 = evidence-based)
- Provenance labels shown in SDG mapper tool output

**Geography field across all tools**
- Added `geography` input to all major tools: SDG mapper, 5D assessment, greenwashing, exclusion screening, risk/opportunity, metric recommender, impact report
- Geography passed through to Company model for all downstream analyses

**Greenwashing integration into pipeline**
- Pitch deck analyzer now runs greenwashing detection automatically (configurable)
- Impact reports (HTML + text) include greenwashing risk section with sub-scores, flags, and recommendations
- HTML report shows visual risk score card with color-coded classification

**Trend analysis engine** (new tool: `trend_analysis`)
- Analyze metric trends over time using `metric_history` data
- Detects direction (improving/declining/stable), percentage change, and volatility
- Supports period sorting across FY, quarterly, and half-year formats
- Tracks verification status of data points

**Impact target tracking**
- Compare current metric values against `impact_targets`
- Status classification: exceeded (≥100%), on_track (≥70%), behind (≥40%), at_risk (<40%)
- Aggregate completion percentage across all targets
- Integrated into trend analysis tool output

**ISSB IFRS S1 framework** (new framework: `issb_s1`)
- Full IFRS S1 General Sustainability Disclosure structure (4 pillars, 12 disclosures)
- Readiness assessment with per-pillar scoring and recommendations
- Integrated into framework tool (`framework='issb_s1'`) and multi-framework scan

**Expanded SASB industries** (17 → 25)
- Added: Hotels & Lodging, Telecommunication Services, Electric Utilities, Water Utilities, Managed Care, Medical Equipment, Mortgage Finance, Consumer Finance
- Updated sector keyword mapping for better matching

**Enhanced fund-level analytics**
- Portfolio aggregation now includes: min/max/median 5D scores, sector distribution, strongest/weakest dimensions, SDG coverage breadth, reporting quality tier
- Richer text output format for portfolio analysis

**Improved LP DDQ narratives**
- Section responses now include provenance labels, geography context, DD coverage, EDCI breakdown, target counts
- Richer narrative structure with better formatting
- Handles `risk`, `dd_checklist`, and `edci_*` data sources

**10 new tests** (47 total): SDG provenance, geography fields, greenwashing integration, trend analysis, target tracking, ISSB S1, expanded SASB

## [0.1.5] - 2026-04-16

### Added

**Greenwashing / impact-washing detection** (new tool: `greenwashing_detect`)
- Core engine with 5 weighted sub-scores: claim-metric gap (30%), adverse omission (20%), language specificity (20%), reporting selectivity (15%), verification signals (15%)
- 5-tier classification: Genuine Impact Leader → Probable Greenwashing
- Vague verb detection (19 aspirational verbs) vs. concrete verbs (21 evidence verbs)
- Buzzword density analysis (16 common greenwashing buzzwords)
- Sector-specific adverse metric checks
- Verification/audit signal detection (12 verification keywords, 12 measurement keywords)
- Actionable flags and recommendations per sub-score

**Exclusion screening** (new tool: `exclusion_screening`)
- Norms-based screening against 8 categories: controversial weapons, fossil fuels, tobacco, gambling, adult entertainment, UNGC violations, deforestation, predatory lending
- SFDR PAI indicator mapping (PAI4, PAI10, PAI14)
- Configurable severity levels: mandatory, common, watch
- YAML-based criteria file (`data/exclusion_criteria.yaml`) for fund-specific customization
- Pass/fail result with detailed flags and matched keywords

**7 new tests** (68 total): greenwashing classification, high/low risk detection, exclusion pass/fail

## [0.1.4] - 2026-04-16

### Added

**Score provenance and transparency**
- Every dimension score now carries a `provenance` field: `evidence-based` (≥3 reported metrics), `partial` (1-2 metrics), or `estimated` (keyword/sector-inferred only)
- Overall assessment includes `overall_provenance` aggregated from all dimensions
- CLI and report outputs clearly label estimated scores with warnings
- Prevents misinterpretation of heuristic-based scores as rigorous assessments

**Enriched Company model**
- New fields: `geography` (country/region), `stage` (pre-seed through mature), `founded_year`, `employees`
- `impact_targets`: forward-looking targets (e.g. "OI4112: 500 tCO2e by 2027")
- `reporting_period`: which period metrics cover (e.g. "FY2025", "Q1 2026")
- `exclusion_flags`: norms-based screening flags (e.g. "fossil_fuel", "controversial_weapons")
- `metric_history`: time-series MetricValue list for progress tracking across periods
- All new fields are optional with backward-compatible defaults

**MetricValue model for time-series tracking**
- New `MetricValue` model with: `metric_id`, `value`, `unit`, `period`, `timestamp`, `source`, `verified`, `notes`
- Foundation for progress tracking, trend analysis, and period-over-period comparison
- Supports verified/unverified distinction for audit trail

**Externalized scoring configuration (`data/scoring_config.yaml`)**
- Sector baselines, keyword dimension boosts, theme hints, risk/opportunity rules all externalized to YAML
- Funds can customize scoring parameters without code changes
- Graceful fallback to hardcoded defaults if YAML not found or invalid

**Negation-aware keyword matching**
- Keyword boosts now check for negation phrases within a 30-character window before the keyword
- Prevents "we do not target women" from boosting gender scores
- Supports 9 negation patterns: "not", "no", "don't", "doesn't", "do not", "does not", "without", "lack", "unable to"

**Minimum metric threshold for above-baseline scores**
- Companies with fewer than 3 reported metrics are capped at 2.5/5.0 per dimension
- Prevents keyword-stuffed descriptions from producing inflated scores
- Clear recommendation to report more metrics when threshold not met

### Changed

- 7 additional tests (61 total): score provenance, negation detection, enriched Company model, MetricValue model

## [0.1.3] - 2026-04-16

### Added

**Input normalization layer (`common.py`)**
- Shared helper module with `normalize_metric_map`, `normalize_metric_ids`, `normalize_sdg_goals`, `normalize_str_list`, and `infer_themes`
- Metric IDs auto-uppercased/validated against IRIS+ pattern; invalid IDs produce warnings
- Theme inference from free text (15 keyword-to-theme mappings: climate, energy, health, agriculture, fintech, gender, etc.)
- Wired into all major impact tools for consistent input handling

**3 new impact tools (14 total)**
- `impact_data_quality`: Assess quality of reported IRIS+ data -- flags unknown IDs, placeholder values (N/A/TBD), non-numeric entries, missing required metrics; produces a quality score and recommended fixes
- `impact_metric_recommender`: Recommend high-relevance IRIS+ metrics based on themes, SDG goals, sector, and description; prioritized shortlist with rationale tags (theme/sdg/keyword/core-set)
- `impact_risk_opportunity`: Structured risk/opportunity assessment using keyword heuristics -- categorized risks with severity levels and mitigation suggestions, opportunities with time horizons

**Broader format and input support**
- `pitch_deck_analyze` now accepts `.txt` and `.md` files (not just PDF)
- `dd_checklist` text extraction supports YAML, JSON, and RST files
- `lp_ddq_export` supports CSV output format
- `iris_catalog` `get` action normalizes metric IDs (case-insensitive); `search` accepts comma-separated metric IDs
- `cross_reference` handles PAI-prefixed SFDR identifiers (e.g., "PAI1")
- `portfolio_tool` uses `Literal` types for action/output_format validation

**13 new tests**
- Enhancement tests covering normalizers, new tool imports, risk/opportunity engine, and data quality assessment (54 total impact tests)

## [0.1.2] - 2026-04-16

### Added

**Interactive impact score improvement**
- HTML reports now include an "Interactive Score Improvement" section with 12 checkboxes for common impact practices (beneficiary tracking, GHG emissions, gender diversity, supply chain policies, Theory of Change, third-party audits, etc.)
- Each checkbox maps to specific 5-Dimension scoring categories with weighted boosts
- Live-updating score cards show grade, overall score, and improvement delta as boxes are checked
- Before/after radar chart overlay using Plotly shows the impact of checked items
- Agent-guided Q&A workflow: the AI agent can now ask targeted questions to improve weak dimensions, map answers to IRIS+ metrics, and re-run assessments to show score changes

**Impact tools auto-approved**
- All 11 impact analysis tools (`impact_report`, `lp_ddq_export`, etc.) are now auto-approved in default permission mode -- no more "Allow impact_report?" confirmation prompts
- These tools only generate analysis output and write harmless report files, not destructive operations

**Custom OpenAI-compatible endpoint support**
- `impact-vision setup` wizard now includes a "Custom endpoint" option for any OpenAI-compatible API
- Users can configure arbitrary base URLs, model names, and provider labels

**API connection validation**
- `impact-vision setup` now tests the API key and endpoint after configuration
- Validates connectivity, handles 401/403/timeout errors, and confirms the key works before finishing

### Fixed

**Tool result overflow causing "API error:" with empty message**
- When saving reports to file, the tool was returning full HTML content (10KB+) back to the LLM, causing it to fail
- Now returns a clean text summary when saving to file, and summarizes HTML reports over 2KB

**Full IRIS+ catalog bundled (787 metrics)**
- Replaced the 16 GIIN Core Metrics fallback with the complete 787-metric IRIS+ 5.3c catalog
- Search now includes synonym expansion (e.g., "climate" -> "greenhouse gas", "carbon", "emissions") and JII tag matching
- Common searches like "water", "climate", "healthcare" now return relevant results immediately

**Sector-aware scoring**
- 5-Dimension and SDG scoring now uses sector baselines and keyword inference from company descriptions
- Companies get meaningful scores even without explicit reported metrics (e.g., a pig farm in agriculture gets baseline scores for food security, local employment, environmental risks)
- Impact reports include sector-specific opportunities and risks

**UI flickering during long responses**
- Wrapped completed messages with Ink's `Static` component to prevent re-renders
- Increased streaming buffer flush intervals to reduce update frequency

**"Your request was blocked" API error**
- Overrode the `openai` Python library's default `User-Agent` header which was being blocked by some proxy endpoints

**Setup wizard improvements**
- Re-entering API key now available even if provider is already configured
- ASCII banner changed from "OH MY HARNESS" to "IMPACT VISION" in green with proper letter spacing

## [0.1.1] - 2026-04-16

### Fixed

**Critical: .gitignore excluding all __init__.py files**
- The `.gitignore` pattern `_*.py` (intended for scratch files) was matching `__init__.py` at every directory depth, silently preventing 50+ package initializer files from being committed to git
- Anyone cloning the repo got a broken project with no package exports
- Narrowed pattern to `/_*.py` (root-only) so `__init__.py` files are properly tracked
- Committed all 50+ existing `__init__.py` files that were on disk but untracked

**Package import stability**
- Fixed circular import between `config.settings` and `permissions.checker` using lazy loading
- Fixed circular import between `engine.query_engine` and `api.client` using lazy loading
- Fixed `skills/__init__.py` importing `get_user_skills_dir` from wrong module (`registry.py` -> `loader.py`)
- Fixed `swarm/__init__.py` eagerly importing `lockfile`, breaking tool registry isolation test
- Added `save_settings` to `config/__init__.py` lazy exports (was missing, broke auth flows)

**services/__init__.py re-exports**
- `services/__init__.py` now properly re-exports compaction functions (`compact_conversation`, `compact_messages`, `build_post_compact_messages`, `summarize_messages`, `estimate_conversation_tokens`) from `services/compact/` -- the real 1580-line compaction system was on disk but never exposed

**tools/__init__.py with resilient registry**
- Added `create_default_tool_registry()` that dynamically imports and registers tools, gracefully skipping any whose optional dependencies are unavailable
- MCP tools/resources still registered when a manager is provided
- Registry now bootstraps 37 tools successfully

**Test branding fixes**
- Updated test assertions from upstream OpenHarness branding to Impact Vision: CLI help text ("Oh my Harness!" -> "Impact Vision"), system prompt persona, and console script names (`openh`/`oh` -> `impact-vision`/`iv`)
- Removed tests for `scripts/install.ps1` which doesn't exist in this project

### Added

**CI workflow**
- GitHub Actions workflow (`.github/workflows/ci.yml`) with 3 jobs: import smoke checks, full test suite, and ruff linting
- `scripts/check_imports.py` -- verifies all 37 `__init__.py` files exist, tests 21 critical import groups, and validates tool registry bootstrap

**pytest configuration**
- Added `pythonpath = ["src", "."]` and `--import-mode=importlib` to `pyproject.toml` for reliable test discovery

**Beginner-friendly onboarding**
- New `impact-101.md` skill with plain-language explanations of IRIS+, SDGs, 5 Dimensions, NESTA evidence levels, ESG frameworks, and common newcomer questions
- Enriched system prompt with guidance for explaining concepts to users new to impact investing
- Added "What is Impact Investing?" section to README with key concept table

**README improvements**
- Fixed OpenHarness credit link (was `novix-sa`, now `HKUDS`)
- Added Development section with testing coverage table and CI documentation
- Added architecture entries for `scripts/` and `.github/workflows/`

## [0.1.0] - 2026-04-15

### Added

**Core Impact Engine**
- IRIS+ 5.3c Catalog ETL parser (263 columns, ~787 metrics) with JSON caching
- In-memory MetricStore with search, SDG/theme/dimension/section/stakeholder filters
- 5 Dimensions of Impact scoring (What/Who/How Much/Contribution/Risk) with letter grades
- SDG alignment mapper (0-100 scoring per goal, theme/metric/depth weighted)
- Gap analysis against IRIS+ Core Metric Set (16 baseline metrics)
- Impact Due Diligence checklist engine (96 questions, 24 categories, YAML-driven)
- NESTA Standards of Evidence scoring (levels 1-5) for DD analysis
- Sector-specific DD questions (fintech, healthcare, agriculture, energy, education)
- Sector benchmarks for 5D scores and SDG alignment (8 sectors)

**ESG/Sustainability Frameworks**
- SASB industry-specific materiality mappings (17 industries, 77+ topics)
- GRI Universal + Topic Standards (34 standards, 120+ disclosures)
- TCFD / IFRS S2 climate disclosure (4 pillars, 11 disclosures)
- SFDR PAI (14 mandatory EU indicators)
- EDCI (2026 private-markets ESG KPI set with cross-references)
- UNPRI self-assessment (6 Principles, 27 actions)
- Theory of Change (RS Group Blended Value + GIIN IRIS+ 8-step checklist)
- Cross-reference mapping (40+ entries across IRIS+, GRI, EDCI, SFDR, SASB, TCFD)

**Agent Tools (12 LLM-callable tools)**
- `pitch_deck_analyze` - PDF intake with full impact analysis pipeline and Company extraction
- `dd_checklist` - List, analyze, suggest DD questions with evidence scoring
- `iris_catalog` - Search, browse, filter the IRIS+ catalog
- `sdg_mapper` - Score SDG alignment per goal
- `five_dimension_assess` - 5-Dimension impact assessment
- `gap_analysis` - Core Metric Set coverage analysis
- `impact_report` - Generate reports (HTML with Plotly charts, XLSX, CSV, JSON, text)
- `framework_assess` - Multi-framework ESG assessment (SASB/GRI/TCFD/SFDR/EDCI/UNPRI/ToC)
- `cross_reference` - Cross-framework metric lookup
- `lp_ddq_export` - LP DDQ exporter (ILPA, GIIN/IRIS+, EDCI, custom; text/JSON/XLSX)
- `portfolio_analyze` - Portfolio batch analysis with aggregated metrics
- `ollama-setup` - CLI command for local LLM configuration

**Visual Output**
- HTML reports with Plotly.js radar charts (5D) and bar charts (SDG), sector benchmark comparison, responsive design with official UN SDG colors
- Interactive Score Improvement section in HTML reports with live score updates and before/after radar chart
- Agent-guided Q&A workflow for improving scores through targeted questions mapped to IRIS+ metrics
- XLSX export for impact reports and LP DDQs (multi-sheet, formatted headers)
- Streamlit dashboard (5 tabs: Assessment, IRIS+ Catalog, DD Checklist, Framework Scan, Portfolio)
- Dashboard includes benchmark comparison charts, evidence level display, and framework overview bar chart
- Optional basic authentication for Streamlit deployment

**CLI**
- `impact-vision catalog load/stats/search` - Manage IRIS+ catalog
- `impact-vision framework list/scan/xref` - ESG framework tools
- `impact-vision dd list/categories/analyze` - DD checklist tools
- `impact-vision ollama-setup` - Local LLM configuration

**Infrastructure**
- Built on HKU OpenHarness agent framework (agent loop, tools, skills, CLI, permissions)
- Agent skills (markdown knowledge): IRIS+ expert, SDG alignment, 5 dimensions, DD guide, Theory of Change
- Custom system prompt with Impact Vision persona and tool descriptions
- 41 automated tests covering all modules and frameworks
