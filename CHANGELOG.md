# Changelog

All notable changes to Impact Vision are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/).

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
