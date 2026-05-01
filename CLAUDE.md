# Impact Vision

Impact Vision is an open-source AI-powered impact measurement and SDG alignment agent for VC and impact investment funds, built on top of OpenHarness.

Current release: **0.15.0 (Trust Infrastructure)**. The v3 roadmap
(`docs/roadmap-v3.md`) and engineering plan
(`docs/roadmap-v3-implementation.md`) describe the strategic shift toward
causal-style claims, stakeholder voice as evidence, governed AI, and an
LP-grade assurance bundle.

## Core Workflow

1. User uploads a pitch deck / investment memo PDF
2. `pitch_deck_analyze` extracts text, identifies impact claims, maps to IRIS+/SDGs, runs DD checklist, auto-extracts a Company model
3. Agent presents gaps and asks the most important unanswered DD questions (with NESTA evidence levels)
4. Deeper scoring via `sdg_mapper`, `five_dimension_assess`, `gap_analysis` with sector benchmarks
5. `cross_reference` tool maps metrics across all 10 frameworks
6. Greenwashing detection (standard + EU Green Claims + UK FCA + NLP) and regulatory compliance checks
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

## Engineering housekeeping (deferred refactor)

**Package rename**: the project is `impact-vision` (pyproject) but the
importable package is still `openharness` and carries many unused HKUDS-era
sub-packages (`swarm`, `vim`, `coordinator`, `engine`, `themes`, `ui`,
`bridge`, `frontend/terminal`). They inflate the wheel and the import-time
attack surface. Plan:

1. Add a top-level `impact_vision` namespace that re-exports everything in
   `openharness.impact.*` (keep `openharness` as a deprecated alias).
2. Trim `[tool.hatch.build.targets.wheel.force-include]` to ship only
   `impact/`, `tools/impact/`, `api_gateway/`, `prompts/`, `cli.py`.
3. Delete the unused submodules in a separate PR once downstream callers
   (Streamlit dashboard, examples) have been updated.

This is intentionally **not** done in the same PR as the Phase-11
correctness fixes to keep the diff readable.

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
│   ├── roadmap_v2.py              # v2 institutional-readiness helpers
│   ├── emission_factors.py        # v3 versioned emission factors + sensitivity
│   ├── stakeholder_voice.py       # v3 Lean Data templates + consent + claim linking
│   ├── evidence_workflow.py       # v3 AI extraction review queue + policies
│   ├── verification_workspace.py  # v3 verifier workspace + findings + comments
│   ├── lp_narrative.py            # v3 LP narrative generator + Q&A workspace
│   ├── greenwashing_reviewer.py   # v3 per-claim explainable greenwashing review
│   ├── portfolio_nlq.py           # v3 NL query engine + ApprovedDataPolicy
│   ├── exit_impact.py             # v3 OPIM P8 exit-impact scoring + plan
│   ├── report_templates/          # Jinja2-based HTML report template engine
│   │   └── html_template.py       # Shared CSS, header/footer, SDG colors
│   └── frameworks/                # ESG/sustainability frameworks (10 frameworks)
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
│       ├── ifc_opim.py            # IFC Operating Principles for Impact Management
│       └── cross_reference.py     # 59 cross-framework metric mappings
├── tools/impact/                  # Agent tools for LLM orchestration
│   ├── pitch_deck_analyze_tool.py # PDF/TXT/MD intake + full pipeline + Company extraction
│   ├── dd_checklist_tool.py       # DD question list/analyze/suggest
│   ├── iris_catalog_tool.py       # Search/filter IRIS+ catalog
│   ├── sdg_mapper_tool.py         # SDG alignment mapping
│   ├── five_dimension_assess_tool.py  # 5-Dimension assessment + additionality
│   ├── gap_analysis_tool.py       # Gap analysis vs Core Metrics
│   ├── impact_report_tool.py      # Report generation (HTML/CSV/JSON/text/XLSX)
│   ├── framework_tool.py          # Multi-framework ESG assessment (10 frameworks)
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

59 concepts mapped across IRIS+, GRI, EDCI, SFDR PAI, TCFD, SASB, ESRS, and ISSB.
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
