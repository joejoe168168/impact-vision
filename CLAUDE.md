# Impact Vision

Impact Vision is an open-source AI-powered impact measurement and SDG alignment agent for VC and impact investment funds, built on top of OpenHarness.

Current release: **0.16.0 (Comparable, Assured & Connected)**. The v3 roadmap
(`docs/roadmap-v3.md`) and engineering plan
(`docs/roadmap-v3-implementation.md`) describe the strategic shift toward
causal-style claims, stakeholder voice as evidence, governed AI, and an
LP-grade assurance bundle.

**v4 (Consultant-Led Product Strategy)** — see `docs/roadmap-v4.md`. v4 is an
integration / packaging wave, not a re-implementation wave: engineering rule
is that new code lives in `impact/engagements/`, `tools/impact/engagement_*`
/ `tools/impact/toc_*`, and `frontend/`, and must never fork an existing v3
module. Progress so far:

- **Wave 1 / Track 1 — Consultant Engagement Workspace** (shipped). The
  `impact.engagements` package ships 12 productised engagement bundles, a
  proposal builder, a 7-phase consultant checklist, an audit-logged
  deliverable state machine, client-type templates, and the
  `engagement_workspace` agent tool.
- **Wave 2 / Track 2 — Theory of Change + KPI framework builder** (shipped).
  `impact.engagements.toc_builder` wraps the existing v3 `toc_graph`
  renderer and the 61-concept cross-reference map into a consultant-facing
  ToC canvas, an 11-rule logic-chain validator (missing assumptions, weak
  causal links, unmeasured outcomes, risk blind spots, equity lens), and
  a multi-framework KPI generator, exposed through the `toc_builder`
  agent tool.
- **Tracks 3-10 — Integration Wave** (shipped). Eight backend modules in
  `impact.engagements` plus a consolidated `engagement_suite` agent tool
  (65 actions; action='describe' lists payload keys) covering the consultant workflow end-to-end:
  - `engagements.data_room` (Track 3) — data request packs, completeness
    scoring, exception workflow, multi-entity rollup, coaching cards.
  - `engagements.value_creation` (Track 4) — pluggable `BenchmarkProvider`,
    peer dashboard, impact risk rating, value-creation plan, business
    case + scenario engine, supply-chain hotspot ranker.
  - `engagements.reporting_studio` (Track 5) — 6 named report templates,
    approval state machine, claim review panel, executive deck outline,
    public microsite bundle, multi-audience rewrite scaffold.
  - `engagements.training` (Track 6) — training plan generator (maturity
    stage aware), 6 workshop packs, investee coaching cards, learning
    loop, readiness badges with threshold enforcement.
  - `engagements.website` (Track 7, backend-only) — 7-question diagnostic
    quiz + scoring, productised-engagement gallery, benchmark teaser,
    playbook library, privacy-preserving upload demo, GDPR/PDPA-aware
    lead capture, white-label partner metadata.
  - `engagements.copilot` (Track 8) — AI output provenance
    (`CopilotOutput` + `CopilotReviewQueue`), deterministic challenge
    mode, client-safe answer mode bound to approved evidence only,
    prefix-based meeting-note ingestion.
  - `engagements.regulatory` (Track 9) — 10 jurisdiction profiles
    (EU / UK / US / Singapore / Switzerland / Canada / Japan / Australia /
    CN / HK),
    SFDR + UK SDR classifiers, deadline calendar, regulator-facing
    narrative composer.
  - `engagements.verification_bundle` (Track 10) — BlueMark-style
    3-Pillar Verification Bundle (Mandate / Practice / Reporting) with a
    HMAC-signed assurance manifest, verifier token + expiry, verifier
    marketplace directory, assurance-ready badge.

## Core Workflow

1. User uploads a pitch deck / investment memo PDF
2. `pitch_deck_analyze` extracts text, identifies impact claims, maps to IRIS+/SDGs, runs DD checklist, auto-extracts a Company model
3. Agent presents gaps and asks the most important unanswered DD questions (with NESTA evidence levels)
4. Deeper scoring via `sdg_mapper`, `five_dimension_assess`, `gap_analysis` with sector benchmarks
5. `cross_reference` tool maps metrics across all 22 framework modules
6. Greenwashing detection (standard + EU ECGT green claims + UK FCA + NLP) and regulatory compliance checks
7. `impact_report` generates the final assessment (HTML with Plotly charts, XLSX, CSV, JSON)

## v3 Trust Infrastructure (since 0.15.0)

Layered on top of the v2 institutional-readiness backbone (canonical
`MetricRecord`, evidence graph, audit trail, standards registry):

- **Versioned emission factors** (`impact.emission_factors`) – multi-revision
  factor catalogue with uncertainty bands, sensitivity rollups, and
  inventory-repricing helpers.
- **Stakeholder voice as evidence** (`impact.stakeholder_voice`) – Lean Data
  templates, GDPR/PDPA-compliant `ConsentRecord`, beneficiary feedback
  quality scoring, and feedback↔claim linkage.
- **AI extraction review queue** (`impact.evidence_workflow`) – policy-driven
  review with bulk/auto decisions and audit-trail integration.
- **Verification workspace** (`impact.verification_workspace`) – read-only
  assurance-pack workspace with finding lifecycle and threaded comments.
- **LP narrative + Q&A** (`impact.lp_narrative`) – audit-friendly LP
  narratives and a Q&A workspace constrained to verified data.
- **Greenwashing reviewer** (`impact.greenwashing_reviewer`) – per-claim
  explainable review with specificity classification and severity scoring.
- **Portfolio NLQ** (`impact.portfolio_nlq`) – natural-language portfolio
  queries enforced by an `ApprovedDataPolicy`, returning citations only.
- **Exit impact assessment** (`impact.exit_impact`) – OPIM Principle 8
  workflow scoring durability of post-exit impact.

Each module ships with a matching agent tool registered in
`create_default_tool_registry()` (see `tools/impact/__init__.py`).

## Documentation conventions (keep README.md newcomer-focused)

The project has an explicit preference for a **short, newcomer-friendly
`README.md`**. When you edit docs, obey these rules:

1. **Changelog content belongs in `CHANGELOG.md`, not `README.md`.**
   Do not add or restore any of the following to `README.md`:
   - Top-of-file blockquote banners like `> **v0.x.y · YYYY-MM-DD** — ...`.
   - "What's new in v0.x.y" sections.
   - "Maintenance note · YYYY-MM-DD", "Roadmap update · ...", or
     "Hardening note · ..." style blockquotes.
   - Phase-by-phase implementation checklists (e.g. "Phase 12 — Fund
     Workflow (P1) — **shipped (v0.8.0)**" blocks).
   - "Verification status" / test-count tables tied to a specific version.
   - "System Review (v0.x.y)" retrospectives.

   Version tags are allowed **inline inside feature tables** (e.g.
   "Verification workspace (v0.15.0)") because they describe capability
   provenance rather than a release log.

2. **Keep release notes in one place.** New version stories go in
   `CHANGELOG.md`. Strategic direction goes in `docs/roadmap-*.md`. The
   `README.md` links to both with one-line pointers.

3. **Fund-manager / LP / consultant "how do I…" walkthroughs belong in
   `docs/fund-manager-guide.md`** (or a new `docs/*.md`). The `README.md`
   links to them from the "Core Use Case" section.

4. **Don't bloat the `README.md` with exhaustive test tables, CI output,
   or QA verification matrices.** A one-liner that CI runs import smoke
   + pytest + ruff is enough.

5. **Tool / CLI / architecture sections must be kept current.** When you
   add or remove an agent tool, CLI subcommand, or top-level package,
   update the README's grouped "Agent Tools" summary (every tool listed once)
   and architecture tree, then run `python scripts/build_tool_reference.py`
   to regenerate `docs/reference/tools.md`. `tests/test_docs_counts.py`
   fails when a number quoted in `README.md` / `CLAUDE.md` (tool count,
   currently **48**; crosswalk concepts; DD questions; …) drifts from the code.

6. **Frameworks & Standards is a single consolidated table.** Do not
   split it back into "Core / ESG / Regulatory / Greenwashing /
   Assurance" H3 subsections — the one-table view is easier for new
   users to scan.

7. When in doubt about a piece of content, ask: *would a first-time
   user clicking into the repo on GitHub benefit from seeing this in the
   first scroll?* If not, move it to `CHANGELOG.md`, `docs/`, or
   `ROADMAP.md`.

The current `README.md` is ~846 lines; keep it at or below 850. If it
grows past ~1000, trim before shipping.

## Engineering housekeeping (package rename status)

**`impact_vision` is the supported import path** (v7 W5.5). Every
`impact_vision.*` module is the same object as its `openharness.impact.*`
implementation (plus `impact_vision.tools` / `.cli` / `.web` /
`.api_gateway` / `.dashboard`), and the console scripts point at
`impact_vision.cli:app`. Write new docs and examples against `impact_vision`.

Still deferred, to land with the 0.18 shim removal:

1. Physically move the code under `src/impact_vision/` and turn `openharness`
   into the alias (the reverse of today).
2. `channels/` and `vim/` are already excluded from the wheel. `themes`,
   `voice`, `bridge` and `keybindings` are still imported by the slash-command
   registry / TUI, so make those imports lazy before dropping them.
3. Remove the deprecated shims: `roadmap_v2`, `questionnaire_v2`,
   `frameworks.sfdr_v2`.

**Knowledge, methodology and state (v7 Wave 5):** reference data lives in
sourced YAML under `data/` (`regulatory/`, `standards_registry.yaml`,
`benchmarks.yaml`, `concordance.yaml`, `methodology/v1.yaml`).
`scripts/check_knowledge.py` fails CI on rows not re-verified in 180 days.
Never hard-code a regulatory date, weight or benchmark in Python: add it to
the YAML with `as_of` / `source_url`. Consultant state persists through
`impact.state_store` (SQLite by default; tests use the memory backend).

## Project Structure

```
src/openharness/
├── impact/                        # Impact measurement engine
│   ├── models.py                  # Pydantic models (Metric, Company, Assessment, SDG, ImpactClaim)
│   ├── catalog.py                 # IRIS+ 5.3c Excel ETL (263-column parser)
│   ├── database.py                # In-memory MetricStore with query API
│   ├── sdg_taxonomy.py            # UN SDG 17 goals + 169 targets reference data
│   ├── five_dimensions.py         # 5-Dimension scoring logic + additionality assessment
│   ├── sdg_mapper.py              # SDG alignment scoring algorithm
│   ├── gap_analysis.py            # Core Metric Set gap analysis
│   ├── dd_checklist.py            # DD checklist engine (load YAML, analyze, suggest, evidence scoring)
│   ├── benchmarks.py              # Sector benchmarks for 18 sectors (GIIN survey data)
│   ├── greenwashing.py            # Greenwashing detection (standard + Green Claims + FCA + NLP)
│   ├── risk_opportunity.py        # Risk/opportunity with likelihood x severity matrix
│   ├── storage.py                 # SQLite persistence layer for assessments & session history
│   ├── evidence_graph.py          # v2 claim/metric/target/evidence graph
│   ├── audit_trail.py             # v2 hash-chained audit events
│   ├── standards_registry.py      # v2 versioned standards registry
│   ├── metric_records.py          # v2 canonical MetricRecord contract + helpers
│   ├── investee_collection.py     # v2 questionnaire schema + submission lifecycle
│   ├── climate_accounting.py      # v2 Scope 1/2 GHG inventory calculator
│   ├── roadmap_v2.py              # DEPRECATED shim (W5.4) → ai_review / disclosure_packs / report_governance / …
│   ├── knowledge.py               # v7 W5.1: YAML knowledge loader + freshness gate
│   ├── benchmark_provider.py      # v7 W5.1: one provider over data/benchmarks.yaml
│   ├── methodology.py             # v7 W5.2: versioned scoring methodology + stamp
│   ├── state_store.py             # v7 W5.3: tenant-scoped SQLite/Postgres/memory state
│   ├── emission_factors.py        # v3 versioned emission factors + sensitivity
│   ├── stakeholder_voice.py       # v3 Lean Data templates + consent + claim linking
│   ├── evidence_workflow.py       # v3 AI extraction review queue + policies
│   ├── verification_workspace.py  # v3 verifier workspace + findings + comments
│   ├── lp_narrative.py            # v3 LP narrative generator + Q&A workspace
│   ├── greenwashing_reviewer.py   # v3 per-claim explainable greenwashing review
│   ├── portfolio_nlq.py           # v3 NL query engine + ApprovedDataPolicy
│   ├── exit_impact.py             # v3 OPIM P8 exit-impact scoring + plan
│   ├── ai_provenance.py           # v7 W4: AI/automation disclosure on every output (AI Act Art 50)
│   ├── engagements/               # v4 W1+W2: consultant workspace + ToC builder
│   │   ├── models.py              # Engagement / Deliverable / Checklist / Override
│   │   ├── bundles.py             # 12 productised engagement bundles (§4a)
│   │   ├── checklist.py           # 7-phase consultant checklist generator
│   │   ├── proposal.py            # Proposal builder (scope/workplan/fees/risk)
│   │   ├── templates.py           # Reusable client-type template library
│   │   ├── toc_builder.py         # v4 W2: ToC canvas + validator + KPI generator
│   │   ├── data_room.py           # v4 T3: data request packs + completeness + coaching
│   │   ├── value_creation.py      # v4 T4: benchmarks + risk + value plan + scenarios
│   │   ├── reporting_studio.py    # v4 T5: multi-audience report + claim review + deck
│   │   ├── training.py            # v4 T6: training plan + workshops + readiness badges
│   │   ├── website.py             # v4 T7: diagnostic + gallery + playbooks + leads
│   │   ├── copilot.py             # v4 T8: AI output provenance + challenge + safe answer
│   │   ├── regulatory.py          # v4 T9: jurisdictions + SFDR/UK SDR + deadlines
│   │   ├── verification_bundle.py # v4 T10: BlueMark 3-pillar bundle + signed manifest
│   │   └── workspace.py           # In-memory store + audit-trail integration
│   ├── report_templates/          # Jinja2-based HTML report template engine
│   │   └── html_template.py       # Shared CSS, header/footer, SDG colors
│   └── frameworks/                # ESG/sustainability frameworks (22 framework modules)
│       ├── sasb.py                # SASB industry-specific materiality (17 industries)
│       ├── gri.py                 # GRI Universal + Topic Standards (34 standards)
│       ├── tcfd.py                # TCFD / IFRS S2 climate disclosure (4 pillars)
│       ├── sfdr_pai.py            # SFDR 14+9 PAI indicators + Article 6/8/9
│       ├── edci.py                # EDCI 17 PE/VC ESG metrics
│       ├── unpri.py               # UNPRI 6 Principles (27 actions)
│       ├── theory_of_change.py    # RS Group + GIIN ToC framework
│       ├── issb_ifrs_s1.py        # ISSB IFRS S1 General Requirements
│       ├── issb_ifrs_s2.py        # ISSB IFRS S2 Climate Disclosures
│       ├── esrs.py                # EU CSRD/ESRS Double Materiality (11 standards)
│       ├── hk_taxonomy.py         # v7 W4: Hong Kong Taxonomy eligibility/alignment screen
│       ├── ifc_opim.py            # IFC Operating Principles for Impact Management
│       └── cross_reference.py     # 61 cross-framework metric mappings
├── tools/impact/                  # Agent tools for LLM orchestration
│   ├── pitch_deck_analyze_tool.py # PDF/TXT/MD intake + full pipeline + Company extraction
│   ├── dd_checklist_tool.py       # DD question list/analyze/suggest
│   ├── iris_catalog_tool.py       # Search/filter IRIS+ catalog
│   ├── sdg_mapper_tool.py         # SDG alignment mapping
│   ├── five_dimension_assess_tool.py  # 5-Dimension assessment + additionality
│   ├── gap_analysis_tool.py       # Gap analysis vs Core Metrics
│   ├── impact_report_tool.py      # Report generation (HTML/CSV/JSON/text/XLSX)
│   ├── framework_tool.py          # Multi-framework ESG assessment (22 framework modules)
│   ├── cross_reference_tool.py    # Cross-framework metric lookup
│   ├── data_quality_tool.py       # Metric data quality assessment
│   ├── metric_recommender_tool.py # IRIS+ metric recommendation engine
│   ├── impact_risk_opportunity_tool.py # Risk/opportunity with 14 risk categories
│   ├── lp_ddq_export_tool.py      # LP DDQ exporter (ILPA/GIIN/EDCI/SFDR, XLSX/CSV)
│   ├── beneficiary_feedback_tool.py # Beneficiary feedback import & analysis
│   ├── verification_prep_tool.py  # Impact verification readiness (IFC OPIM)
│   ├── product_passport_tool.py   # EU Digital Product Passport import/mapping
│   ├── emission_factors_tool.py   # v3 emission factor catalog + sensitivity
│   ├── stakeholder_voice_tool.py  # v3 Lean Data + consent + feedback quality
│   ├── evidence_review_tool.py    # v3 AI extraction review queue
│   ├── verification_workspace_tool.py # v3 verifier workspace + findings/comments
│   ├── lp_narrative_tool.py       # v3 LP narrative + Q&A workspace
│   ├── greenwashing_reviewer_tool.py  # v3 explainable greenwashing review
│   ├── portfolio_query_tool.py    # v3 portfolio NL query engine
│   ├── exit_impact_tool.py        # v3 OPIM P8 exit-impact scoring + plan
│   ├── engagement_workspace_tool.py # v4 W1 Track 1 consultant workspace
│   ├── toc_builder_tool.py        # v4 W2 Track 2 ToC canvas + KPI framework
│   ├── engagement_suite_tool.py   # v4 Tracks 3-10 consolidated surface (65 actions; action='describe' lists payload keys)
│   ├── common.py                  # Shared input normalization helpers
│   └── portfolio_tool.py          # Portfolio batch analysis + scenario modeling
├── dashboard/                     # Streamlit dashboard (5 tabs, optional auth)
│   └── app.py
├── skills/bundled/content/        # Agent skills (markdown knowledge)
│   ├── iris-expert.md
│   ├── sdg-alignment.md
│   ├── five-dimensions.md
│   ├── impact-dd-guide.md
│   └── theory-of-change.md
├── prompts/system_prompt.py       # Impact Vision persona + workflow instructions
└── cli.py                         # CLI with catalog, framework, dd subcommands

data/
├── raw/                           # IRIS+ Excel file
├── processed/                     # JSON catalog cache
├── dd_checklist.yaml              # 122 DD questions (GIIN/PCV/Seraf/IMP/AFME + 15 sectors)
├── scoring_config.yaml            # Sector baselines, keyword boosts, risk/opportunity rules
├── sdg_keywords.yaml              # SDG keyword mappings for 20+ sectors
└── sdg/                           # SDG reference data
```

## Key Commands

```bash
impact-vision catalog load          # Load IRIS+ catalog from Excel
impact-vision catalog stats         # Show catalog statistics
impact-vision catalog search "query" # Search metrics
impact-vision framework list        # List all ESG frameworks
impact-vision framework scan "desc" # Quick multi-framework scan
impact-vision framework xref OI4112 # Cross-reference lookup
impact-vision dd list               # List DD checklist questions
impact-vision dd categories         # List categories with counts
impact-vision dd analyze "text"     # Analyze text against DD checklist
impact-vision ollama-setup          # Configure local LLM via Ollama
impact-vision                       # Start interactive agent session
```

## DD Checklist

122 questions across 34 categories sourced from GIIN, PCV, Seraf, IMP, AFME,
plus sector-specific questions for 15 sectors (fintech, healthcare, agriculture,
energy, education, manufacturing, transport, construction, tourism, retail,
mining, media, professional services, waste management, ICT).
Stored in `data/dd_checklist.yaml`. Includes NESTA Standards of Evidence
scoring (levels 1-5) for assessing evidence quality.

## Cross-Reference Mapping

61 concepts mapped across IRIS+, GRI, EDCI, SFDR PAI, TCFD, SASB, ESRS, and ISSB.
Enables lookup in any direction (e.g., "what GRI disclosure corresponds to
IRIS+ OI4112?").

## Sector Benchmarks

18 sectors with benchmark data from GIIN survey: Financial Services, Healthcare,
Education, Agriculture, Energy, Technology, Real Estate, Water & Sanitation,
Manufacturing, Transport & Logistics, Construction, Tourism, Retail,
Mining & Extractives, Media, Professional Services, Waste Management, ICT.
Used for comparing 5D scores and metric coverage.

## Dependencies

Core: pydantic, openpyxl, pandas, pymupdf, jinja2, plotly, pyyaml
Agent: anthropic/openai, typer, rich, httpx, mcp
Dashboard: streamlit

## Runtime versions

**Python**: 3.11 (CI-pinned). 3.12 and 3.13 work locally; CI sticks to 3.11 to match
the lowest-support bound declared in `pyproject.toml`.

**Node.js**: **24 (Active LTS)** everywhere — the `frontend/terminal` TypeScript
build, the GitHub Actions JavaScript runtime, and any developer machine.
GitHub announced on 2025-09-19 that Node.js 20 actions are deprecated; from
2026-06-02 actions will be forced to Node 24, and from 2026-09-16 Node 20
will be removed from the runner. **Do not pin to Node 20 for new work.**
Our CI therefore uses:

```yaml
- uses: actions/checkout@v5       # Node 24 runtime
- uses: actions/setup-python@v6   # Node 24 runtime
- uses: actions/setup-node@v5     # Node 24 runtime
  with:
    node-version: "24"            # Node 24 for the frontend build
```

If you add a new workflow, use the same `v5 / v6 / v5` majors; older `v4 / v5 / v4`
work today but will emit the Node 20 deprecation warning.
