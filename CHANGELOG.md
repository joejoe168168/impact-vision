# Changelog

All notable changes to Impact Vision are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/).

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
- EDCI (17 core PE/VC ESG metrics with cross-references)
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
