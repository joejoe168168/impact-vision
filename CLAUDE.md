# Impact Vision

Impact Vision is an open-source AI-powered impact measurement and SDG alignment agent for VC and impact investment funds, built on top of OpenHarness.

## Core Workflow

1. User uploads a pitch deck / investment memo PDF
2. `pitch_deck_analyze` extracts text, identifies impact claims, maps to IRIS+/SDGs, runs DD checklist, auto-extracts a Company model
3. Agent presents gaps and asks the most important unanswered DD questions (with NESTA evidence levels)
4. Deeper scoring via `sdg_mapper`, `five_dimension_assess`, `gap_analysis` with sector benchmarks
5. `cross_reference` tool maps metrics across all 7 frameworks
6. `impact_report` generates the final assessment (HTML with Plotly charts, XLSX, CSV, JSON)

## Project Structure

```
src/openharness/
├── impact/                        # Impact measurement engine
│   ├── models.py                  # Pydantic models (Metric, Company, Assessment, SDG, ImpactClaim)
│   ├── catalog.py                 # IRIS+ 5.3c Excel ETL (263-column parser)
│   ├── database.py                # In-memory MetricStore with query API
│   ├── sdg_taxonomy.py            # UN SDG 17 goals + 169 targets reference data
│   ├── five_dimensions.py         # 5-Dimension scoring logic
│   ├── sdg_mapper.py              # SDG alignment scoring algorithm
│   ├── gap_analysis.py            # Core Metric Set gap analysis
│   ├── dd_checklist.py            # DD checklist engine (load YAML, analyze, suggest, evidence scoring)
│   ├── benchmarks.py              # Sector benchmarks for 5D/SDG comparison
│   └── frameworks/                # ESG/sustainability frameworks
│       ├── sasb.py                # SASB industry-specific materiality (17 industries)
│       ├── gri.py                 # GRI Universal + Topic Standards (34 standards)
│       ├── tcfd.py                # TCFD / IFRS S2 climate disclosure (4 pillars)
│       ├── sfdr_pai.py            # SFDR 14 mandatory PAI indicators
│       ├── edci.py                # EDCI 17 PE/VC ESG metrics
│       ├── unpri.py               # UNPRI 6 Principles (27 actions)
│       ├── theory_of_change.py    # RS Group + GIIN ToC framework
│       └── cross_reference.py     # 40+ cross-framework metric mappings
├── tools/impact/                  # Agent tools for LLM orchestration (12 tools)
│   ├── pitch_deck_analyze_tool.py # PDF intake + full pipeline + Company extraction
│   ├── dd_checklist_tool.py       # DD question list/analyze/suggest
│   ├── iris_catalog_tool.py       # Search/filter IRIS+ catalog
│   ├── sdg_mapper_tool.py         # SDG alignment mapping
│   ├── five_dimension_assess_tool.py  # 5-Dimension assessment
│   ├── gap_analysis_tool.py       # Gap analysis vs Core Metrics
│   ├── impact_report_tool.py      # Report generation (HTML/CSV/JSON/text/XLSX)
│   ├── framework_tool.py          # Multi-framework ESG assessment (7 frameworks)
│   ├── cross_reference_tool.py    # Cross-framework metric lookup
│   ├── lp_ddq_export_tool.py      # LP DDQ exporter (ILPA/GIIN/EDCI/custom, XLSX)
│   └── portfolio_tool.py          # Portfolio batch analysis
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
├── dd_checklist.yaml              # 96 DD questions (GIIN/PCV/Seraf/IMP/AFME + sector-specific)
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

96 questions across 24 categories sourced from GIIN, PCV, Seraf, IMP, AFME,
plus sector-specific questions for fintech, healthcare, agriculture, energy,
and education. Stored in `data/dd_checklist.yaml`. Includes NESTA Standards
of Evidence scoring (levels 1-5) for assessing evidence quality.

## Cross-Reference Mapping

40+ concepts mapped across IRIS+, GRI, EDCI, SFDR PAI, TCFD, and SASB.
Enables lookup in any direction (e.g., "what GRI disclosure corresponds to
IRIS+ OI4112?").

## Sector Benchmarks

8 sectors with benchmark data from GIIN survey: Financial Services, Healthcare,
Education, Agriculture, Energy, Technology, Real Estate, Water & Sanitation.
Used for comparing 5D scores and metric coverage.

## Dependencies

Core: pydantic, openpyxl, pandas, pymupdf, jinja2, plotly, pyyaml
Agent: anthropic/openai, typer, rich, httpx, mcp
Dashboard: streamlit
