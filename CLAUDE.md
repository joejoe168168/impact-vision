# Impact Vision

Impact Vision is an open-source AI-powered impact measurement and SDG alignment agent for VC and impact investment funds, built on top of OpenHarness.

## Core Workflow

1. User uploads a pitch deck / investment memo PDF
2. `pitch_deck_analyze` extracts text, identifies impact claims, maps to IRIS+/SDGs, runs DD checklist, auto-extracts a Company model
3. Agent presents gaps and asks the most important unanswered DD questions (with NESTA evidence levels)
4. Deeper scoring via `sdg_mapper`, `five_dimension_assess`, `gap_analysis` with sector benchmarks
5. `cross_reference` tool maps metrics across all 10 frameworks
6. Greenwashing detection (standard + EU Green Claims + UK FCA + NLP) and regulatory compliance checks
7. `impact_report` generates the final assessment (HTML with Plotly charts, XLSX, CSV, JSON)

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
├── tools/impact/                  # Agent tools for LLM orchestration (17 tools)
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
