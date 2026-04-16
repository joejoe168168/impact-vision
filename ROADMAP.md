# Impact Vision: Improvement Roadmap

> **Purpose**: Actionable checklist for AI agents and developers to systematically improve Impact Vision.
> **Derived from**: `IMPACT_MANAGER_REVIEW.md` — full impact manager review of the codebase.
> **Convention**: Check the box `[x]` when complete. Each item includes the affected file(s) and review reference.

---

## Phase 1: Critical Fixes 🔴

> These address fundamental accuracy and credibility issues. Do these first.

### 1.1 Score Provenance & Transparency

- [x] **1.1.1** Add `provenance` field to `FiveDimensionScore` model — label each dimension score as `"estimated"` or `"evidence-based"`
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1

- [x] **1.1.2** Add `provenance` field to SDG alignment results — label each SDG score as `"inferred_from_description"` or `"supported_by_metrics"`
  - File: `src/openharness/impact/sdg_mapper.py`
  - Ref: Review §2.1

- [x] **1.1.3** Surface provenance labels in tool outputs — include `"⚠️ Estimated"` or `"✅ Evidence-based"` in text output
  - Files: `src/openharness/tools/impact/five_dimension_assess_tool.py`, `sdg_mapper_tool.py`
  - Ref: Review §2.1

- [ ] **1.1.4** Add provenance section to HTML impact reports — visual indicator (badge/icon) for estimated vs. evidence-based scores
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §2.1

- [ ] **1.1.5** Add explicit disclaimers to reports when scores are primarily keyword-estimated
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §2.1

### 1.2 Minimum Metric Threshold

- [x] **1.2.1** Add minimum metric threshold logic — require ≥3 reported metrics before allowing above-baseline 5D scores
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1

- [ ] **1.2.2** Add configurable threshold constant (default=3) that can be overridden per fund
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1

- [ ] **1.2.3** Emit warning in tool output when scores are capped at baseline due to insufficient metrics
  - Files: `src/openharness/tools/impact/five_dimension_assess_tool.py`, `portfolio_tool.py`, `lp_ddq_export_tool.py`, `sdg_mapper_tool.py`
  - Ref: Review §2.1

### 1.3 Externalize Keyword Dictionaries to YAML

- [x] **1.3.1** Create `data/scoring_config.yaml` — all scoring config in one file (sector baselines, keyword boosts, theme hints, risk/opportunity rules)
  - Files: `data/sector_baselines.yaml` (new), `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1, §6.2

- [ ] **1.3.2** Create `data/sdg_keyword_map.yaml` — extract `_KEYWORD_SDG_MAP` from `sdg_mapper.py` (consolidated into scoring_config.yaml)
  - Files: `data/sdg_keyword_map.yaml` (new), `src/openharness/impact/sdg_mapper.py`
  - Ref: Review §2.1, §6.2

- [x] **1.3.3** Create `data/theme_hints.yaml` — extract `_THEME_HINTS` from `common.py` (consolidated into scoring_config.yaml)
  - Files: `data/theme_hints.yaml` (new), `src/openharness/tools/impact/common.py`
  - Ref: Review §6.2

- [x] **1.3.4** Create `data/risk_rules.yaml` — extract risk/opportunity rules (consolidated into scoring_config.yaml)
  - Files: `data/risk_rules.yaml` (new), `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §2.8, §6.2

- [x] **1.3.5** Add YAML loader utility — `_load_scoring_config()` with fallback to hardcoded defaults
  - File: `src/openharness/tools/impact/common.py`
  - Ref: Review §6.2

- [ ] **1.3.6** Update all consuming modules to use YAML-loaded dictionaries instead of hardcoded ones
  - Files: `five_dimensions.py`, `sdg_mapper.py`, `risk_opportunity.py`, `common.py`
  - Ref: Review §6.2

### 1.4 Add Geography/Country to Company Model

- [x] **1.4.1** Add `geography`, `stage`, `founded_year`, `employees`, `impact_targets`, `reporting_period`, `exclusion_flags`, `metric_history` to `Company` model
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.1

- [x] **1.4.2** Update `SdgMapperInput` to accept geography fields
  - File: `src/openharness/tools/impact/sdg_mapper_tool.py`
  - Ref: Review §5.1

- [x] **1.4.3** Update `FiveDimensionAssessInput` to accept geography fields
  - File: `src/openharness/tools/impact/five_dimension_assess_tool.py`
  - Ref: Review §5.1

- [ ] **1.4.4** Update `PortfolioInput` / `_dict_to_company()` to pass geography fields
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §5.1

- [x] **1.4.5** Update `LpDdqExportInput` to accept geography fields
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §5.1

- [ ] **1.4.6** Use geography in SDG relevance scoring — adjust SDG relevance by country/region context
  - File: `src/openharness/impact/sdg_mapper.py`
  - Ref: Review §5.1

- [ ] **1.4.7** Update `pitch_deck_analyze_tool` auto-extracted Company model to include geography
  - File: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`
  - Ref: Review §5.1

- [ ] **1.4.8** Update sample data files to include geography fields
  - Files: `examples/sample_company.yaml`, `examples/sample_portfolio.csv`
  - Ref: Review §5.1

### 1.5 Write Tests for New Tools

- [ ] **1.5.1** Add tests for `DataQualityTool` — unknown IDs, placeholders, non-numeric, quality score, missing required
  - File: `tests/test_impact.py` (extend) or `tests/test_data_quality_tool.py` (new)
  - Ref: Review §6.3

- [ ] **1.5.2** Add tests for `ImpactRiskOpportunityTool` — risk scoring, opportunity scoring, keyword triggers, metric checks
  - File: `tests/test_impact.py` (extend) or `tests/test_risk_opportunity_tool.py` (new)
  - Ref: Review §6.3

- [ ] **1.5.3** Add tests for `MetricRecommenderTool` — multi-signal scoring, core-set priority, theme/SDG match
  - File: `tests/test_impact.py` (extend) or `tests/test_metric_recommender_tool.py` (new)
  - Ref: Review §6.3

- [ ] **1.5.4** Add tests for `PortfolioTool` — file loading (CSV/YAML/JSON), company conversion, aggregation
  - File: `tests/test_impact.py` (extend) or `tests/test_portfolio_tool.py` (new)
  - Ref: Review §6.3

- [x] **1.5.5** Add tests for input normalization (`common.py`) — `normalize_metric_ids`, `normalize_metric_map`, `normalize_sdg_goals`, `infer_themes`
  - File: `tests/test_impact.py` (extend) or `tests/test_common.py` (new)
  - Ref: Review §6.3

- [ ] **1.5.6** Add edge case tests — empty company, invalid metrics, no catalog loaded, zero metrics
  - File: `tests/test_impact.py` (extend)
  - Ref: Review §6.3

### 1.6 Add Greenwashing Detection

- [x] **1.6.1** Create `src/openharness/impact/greenwashing.py` — core detection engine with 5 sub-scores
  - File: `src/openharness/impact/greenwashing.py` (new)
  - Ref: Review §3.2

- [x] **1.6.2** Implement **claim-metric gap score** — for each SDG claim/theme, check if ≥1 supporting metric exists
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §3.1 (signal #1, #6), §3.2

- [x] **1.6.3** Implement **adverse omission score** — check for missing negative impact metrics by sector
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §3.1 (signal #2), §3.2

- [x] **1.6.4** Implement **specificity score** — detect vague verbs vs. concrete verbs in extracted claims
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §3.1 (signal #4, #5), §3.2

- [x] **1.6.5** Implement **selectivity score** — ratio of positive-only vs. balanced metric reporting
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §3.1 (signal #3), §3.2

- [x] **1.6.6** Implement **verification score** — check for measurement system metrics and verification signals
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §3.1 (signal #8, #9), §3.2

- [x] **1.6.7** Implement composite **greenwashing risk score** (0-100) with weighted sub-scores
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §3.2

- [x] **1.6.8** Implement **5-tier classification** (Genuine Impact Leader → Probable Greenwashing)
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §3.3

- [x] **1.6.9** Create `src/openharness/tools/impact/greenwashing_tool.py` — `GreenwashingDetectorTool` with text/JSON output
  - File: `src/openharness/tools/impact/greenwashing_tool.py` (new)
  - Ref: Review §3

- [x] **1.6.10** Register `GreenwashingDetectorTool` in `tools/impact/__init__.py` and tool registry
  - Files: `src/openharness/tools/impact/__init__.py`, tool registry
  - Ref: Review §3.4

- [ ] **1.6.11** Add greenwashing risk score to `DataQualityTool` payload
  - File: `src/openharness/tools/impact/data_quality_tool.py`
  - Ref: Review §3.4

- [ ] **1.6.12** Add greenwashing signal flags to `PitchDeckAnalyzeTool` claim extraction (vague claims, buzzword density)
  - File: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`
  - Ref: Review §3.4

- [ ] **1.6.13** Add "impact-washing risk" category to `risk_opportunity.py`
  - File: `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §3.4

- [ ] **1.6.14** Add greenwashing risk section to HTML impact reports with visual classification indicator
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §3.4

- [ ] **1.6.15** Add greenwashing detection tests
  - File: `tests/test_greenwashing.py` (new)
  - Ref: Review §6.3

---

## Phase 2: Important Improvements 🟡

### 2.1 Time-Series Support

- [x] **2.1.1** Create `MetricValue` model with fields: `metric_id`, `value`, `unit`, `period`, `timestamp`, `source`, `verified`, `notes`
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.3

- [ ] **2.1.2** Update `Company.reported_metrics` type from `dict[str, Any]` to support both legacy format and new `MetricValue` list
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.3

- [x] **2.1.3** Add `reporting_period` field to `Company` model
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.1

- [x] **2.1.4** Add trend analysis function — compare metric values across periods, detect improvement/decline
  - File: `src/openharness/impact/trend_analysis.py` (new)
  - Ref: Review §2.7

- [ ] **2.1.5** Add year-over-year comparison to portfolio analysis
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §2.7

- [ ] **2.1.6** Add progress tracking to HTML reports — sparklines or trend arrows for key metrics
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §2.7

### 2.2 Exclusion Screening Tool

- [x] **2.2.1** Create `data/exclusion_criteria.yaml` — UNGC violations, controversial weapons, fossil fuel, tobacco, gambling, deforestation, predatory lending
  - File: `data/exclusion_criteria.yaml` (new)
  - Ref: Review §4.4

- [x] **2.2.2** Create `ExclusionScreeningTool` — check company against exclusion criteria, return pass/fail with flags
  - File: `src/openharness/tools/impact/exclusion_screening_tool.py` (new)
  - Ref: Review §4.4

- [x] **2.2.3** Register `ExclusionScreeningTool` in `__init__.py` and tool registry
  - Files: `src/openharness/tools/impact/__init__.py`, tool registry
  - Ref: Review §4.4

- [x] **2.2.4** Add `exclusion_flags` field to `Company` model
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.1

- [ ] **2.2.5** Add exclusion screening as first step in DD workflow — warn if company fails screening before scoring
  - Files: `five_dimension_assess_tool.py`, `portfolio_tool.py`
  - Ref: Review §4.4

### 2.3 Impact Target Tracking

- [x] **2.3.1** Create `ImpactTarget` model — `metric_id`, `target_value`, `target_date`, `actual_value`, `period`
  - File: `src/openharness/impact/models.py`
  - Ref: Review §4.3

- [ ] **2.3.2** Add `targets` field to `Company` model
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.1

- [ ] **2.3.3** Parse `OD4091` (Social and Environmental Targets) metric value into structured `ImpactTarget` objects
  - File: `src/openharness/tools/impact/common.py`
  - Ref: Review §4.3

- [x] **2.3.4** Add target-vs-actual tracking function with trajectory projection
  - File: `src/openharness/impact/trend_analysis.py`
  - Ref: Review §4.3

- [ ] **2.3.5** Add target tracking section to HTML reports — on-track/at-risk/off-track visual indicators
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §4.3

### 2.4 Improve LP DDQ Responses

- [x] **2.4.1** Add narrative prose generation for DDQ template sections — move from metric lists to paragraph responses
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

- [ ] **2.4.2** Add ILPA DDQ template sections 10.1-10.8 with paragraph-length response scaffolding
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

- [ ] **2.4.3** Add policy/governance structure references in DDQ responses
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

- [ ] **2.4.4** Add specific example/case study placeholders in DDQ output
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

### 2.5 Expand SASB to All 77 Industries

- [x] **2.5.1** Add missing SASB industry definitions — expanded from 17 to 25 industries with disclosure topics
  - File: `src/openharness/impact/frameworks/sasb.py`
  - Ref: Review §2.3

- [ ] **2.5.2** Externalize SASB industry data to YAML for easier maintenance
  - Files: `data/sasb_industries.yaml` (new), `src/openharness/impact/frameworks/sasb.py`
  - Ref: Review §2.3

- [ ] **2.5.3** Add SASB industry auto-detection from company sector/description
  - File: `src/openharness/impact/frameworks/sasb.py`
  - Ref: Review §2.3

### 2.6 Fund-Level Analytics

- [x] **2.6.1** Add fund-level aggregation beyond simple portfolio averages — min/max/median, sector distribution, reporting quality
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.1

- [ ] **2.6.2** Add fund-level SDG contribution metric — weighted by portfolio company materiality
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.1

- [ ] **2.6.3** Add impact-weighted returns calculation stub
  - File: `src/openharness/impact/fund_analytics.py` (new)
  - Ref: Review §4.1

- [ ] **2.6.4** Add portfolio-level additionality assessment heuristic
  - File: `src/openharness/impact/fund_analytics.py`
  - Ref: Review §4.1

### 2.7 Negation/Context Detection in Keyword Matching

- [x] **2.7.1** Add negation detection to keyword matching — 9 negation patterns in 30-char window
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1, §5.2

- [ ] **2.7.2** Add context window check — require keyword to appear in impact-relevant context (within N words of other impact terms)
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1

- [ ] **2.7.3** Add negation detection to SDG keyword matching
  - File: `src/openharness/impact/sdg_mapper.py`
  - Ref: Review §2.1

- [ ] **2.7.4** Add negation detection to claim extraction in pitch deck analysis
  - File: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`
  - Ref: Review §5.2

### 2.8 Add ISSB IFRS S1/S2 Disclosure Mapping

- [x] **2.8.1** Create ISSB S1 (General Requirements) framework module with disclosure topics
  - File: `src/openharness/impact/frameworks/issb.py` (new)
  - Ref: Review §10.4

- [ ] **2.8.2** Create ISSB S2 (Climate-related Disclosures) framework module — subsumes and extends TCFD
  - File: `src/openharness/impact/frameworks/issb.py`
  - Ref: Review §10.4

- [ ] **2.8.3** Add ISSB cross-references to the cross-reference mapping
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §10.4

- [x] **2.8.4** Add ISSB as an option in `FrameworkTool`
  - File: `src/openharness/tools/impact/framework_tool.py`
  - Ref: Review §10.4

- [ ] **2.8.5** Add ISSB to `__init__.py` framework list
  - File: `src/openharness/impact/frameworks/__init__.py`
  - Ref: Review §10.4

- [ ] **2.8.6** Update TCFD references to indicate subsumption by ISSB S2 (keep TCFD for backward compatibility)
  - File: `src/openharness/impact/frameworks/tcfd.py`
  - Ref: Review §10.4

---

## Phase 3: Missing Features 🟢

### 3.1 LLM-Assisted Narrative Generation

- [ ] **3.1.1** Add LLM-assisted DDQ narrative generation mode — use the agent's LLM to write paragraph-length responses
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

- [ ] **3.1.2** Add LLM-assisted impact report narratives — executive summary, key findings, recommendations
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §7 (rec #13)

- [ ] **3.1.3** Add "draft review" mode — generate narrative, then flag for human review before final output
  - Files: `lp_ddq_export_tool.py`, `impact_report_tool.py`
  - Ref: Review §9.4

### 3.2 Beneficiary Feedback Integration

- [ ] **3.2.1** Add `beneficiary_feedback` field to `Company` model — structured data (satisfaction scores, NPS, qualitative themes)
  - File: `src/openharness/impact/models.py`
  - Ref: Review §4.2, §10.3

- [ ] **3.2.2** Add beneficiary feedback data import — accept 60 Decibels Lean Data format
  - File: `src/openharness/tools/impact/beneficiary_feedback_tool.py` (new)
  - Ref: Review §4.2, §10.3

- [ ] **3.2.3** Integrate beneficiary feedback into DD checklist responses (SV01-SV03)
  - File: `src/openharness/tools/impact/dd_checklist_tool.py`
  - Ref: Review §4.2

- [ ] **3.2.4** Include beneficiary feedback section in HTML impact reports
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §4.2

### 3.3 Real Benchmarking with Peer Data

- [ ] **3.3.1** Add peer data upload capability — accept anonymized CSV/JSON peer metrics for comparison
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.8

- [ ] **3.3.2** Add percentile ranking calculation — "this company is in the Xth percentile for sector Y"
  - File: `src/openharness/impact/benchmarks.py`
  - Ref: Review §4.8

- [ ] **3.3.3** Add GIIN Annual Impact Investor Survey data as benchmark source
  - File: `src/openharness/impact/benchmarks.py`
  - Ref: Review §10.2

- [ ] **3.3.4** Add fund-level benchmarking — compare portfolio aggregate against GIIN survey data
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.8

### 3.4 API / Data Pipeline Integration

- [ ] **3.4.1** Add REST API endpoints for key tools — impact scoring, SDG mapping, data quality
  - File: `src/openharness/gateway/router.py` (extend)
  - Ref: Review §4.7

- [ ] **3.4.2** Add webhook support for metric update events
  - File: `src/openharness/gateway/router.py` (extend)
  - Ref: Review §4.7

- [ ] **3.4.3** Add data validation pipeline for incoming metric data
  - File: `src/openharness/tools/impact/data_quality_tool.py` (extend)
  - Ref: Review §4.7

### 3.5 Scenario Modeling

- [ ] **3.5.1** Add "what-if" analysis — calculate portfolio score change when adding/removing a company
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.6

- [ ] **3.5.2** Add metric optimization — suggest which metrics each company should add to maximize portfolio SDG coverage
  - File: `src/openharness/tools/impact/metric_recommender_tool.py` (extend)
  - Ref: Review §4.6

- [ ] **3.5.3** Persist interactive HTML checkbox state — save and reload scenario changes
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §4.6

### 3.6 Audit Trail & Verification

- [ ] **3.6.1** Add `verification_status` field to `MetricValue` model — enum: `self_reported`, `management_verified`, `third_party_verified`
  - File: `src/openharness/impact/models.py`
  - Ref: Review §4.5

- [ ] **3.6.2** Add audit trail — who reported what, when, with what evidence
  - File: `src/openharness/impact/models.py` (extend)
  - Ref: Review §4.5

- [ ] **3.6.3** Add pre-verification preparation mode — organize evidence and gaps for BlueMark/IFC OPIM verification
  - File: `src/openharness/tools/impact/verification_prep_tool.py` (new)
  - Ref: Review §10.5

- [ ] **3.6.4** Add IFC Operating Principles alignment checker
  - File: `src/openharness/impact/frameworks/ifc_opim.py` (new)
  - Ref: Review §10.4

### 3.7 Localization

- [ ] **3.7.1** Add multi-language document support for pitch deck analysis (PDF text extraction with encoding detection)
  - File: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`
  - Ref: Review §7 (rec #19)

- [ ] **3.7.2** Add localized keyword dictionaries — at minimum Spanish, French, Portuguese for emerging markets
  - Files: `data/sdg_keyword_map_es.yaml`, `data/sdg_keyword_map_fr.yaml`, etc.
  - Ref: Review §7 (rec #19)

### 3.8 Dashboard Enhancement

- [ ] **3.8.1** Expand Streamlit dashboard — portfolio overview, fund-level KPIs, trend charts
  - File: `src/openharness/dashboard/app.py`
  - Ref: Review §7 (rec #20)

- [ ] **3.8.2** Add interactive drill-down from portfolio to company to metric level
  - File: `src/openharness/dashboard/app.py`
  - Ref: Review §7 (rec #20)

---

## Phase 4: Regulatory & Advanced 📜

### 4.1 EU CSRD / ESRS Double Materiality

- [ ] **4.1.1** Create ESRS framework module with ~1,200 data points across E/S/G topics
  - File: `src/openharness/impact/frameworks/esrs.py` (new)
  - Ref: Review §10.4

- [ ] **4.1.2** Implement double materiality assessment — both financial and impact materiality
  - File: `src/openharness/impact/frameworks/esrs.py`
  - Ref: Review §10.4

- [ ] **4.1.3** Add ESRS as framework option in `FrameworkTool`
  - File: `src/openharness/tools/impact/framework_tool.py`
  - Ref: Review §10.4

- [ ] **4.1.4** Add ESRS cross-references to cross-reference mapping
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §10.4

### 4.2 EU Green Claims Directive Compliance

- [ ] **4.2.1** Add green claims substantiation checker — verify claims have scientific evidence and independent verification
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §10.4

- [ ] **4.2.2** Add life-cycle assessment requirement flag for environmental claims
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §10.4

- [ ] **4.2.3** Add UK FCA anti-greenwashing rule compliance check
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §10.4

### 4.3 SFDR Enhancements

- [ ] **4.3.1** Add Article 6/8/9 fund classification support
  - File: `src/openharness/impact/frameworks/sfdr_pai.py`
  - Ref: Review §2.5

- [ ] **4.3.2** Add optional PAI indicators (biodiversity, water, waste, social/employee)
  - File: `src/openharness/impact/frameworks/sfdr_pai.py`
  - Ref: Review §2.5

- [ ] **4.3.3** Add entity-level vs. fund-level PAI reporting distinction
  - File: `src/openharness/impact/frameworks/sfdr_pai.py`
  - Ref: Review §2.5

- [ ] **4.3.4** Add SFDR Annex III/IV table generation
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.5

### 4.4 NLP-Enhanced Greenwashing Detection

- [ ] **4.4.1** Integrate ClimateBERT for climate-specific greenwashing detection
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5, §10.6

- [ ] **4.4.2** Implement Green Authenticity Index (GAI) — Stacey Matrix evaluation of claims
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5, §10.6

- [ ] **4.4.3** Implement Cheap Talk Index — proportion of non-specific commitments
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5, §10.6

- [ ] **4.4.4** Add sentiment deflection detection — overly positive tone deflecting from negative information
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5

- [ ] **4.4.5** Add claim decomposition and fact-checking — break claims into verifiable sub-claims
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5

### 4.5 Digital Product Passport Integration

- [ ] **4.5.1** Add EU ESPR / Digital Product Passport data import
  - File: `src/openharness/tools/impact/product_passport_tool.py` (new)
  - Ref: Review §10.4

- [ ] **4.5.2** Map product passport data to IRIS+ metrics for product-level impact assessment
  - File: `src/openharness/tools/impact/product_passport_tool.py`
  - Ref: Review §10.4

---

## Phase 5: Scoring Engine Improvements 🎯

### 5.1 Expand Sector Coverage

- [ ] **5.1.1** Add 5D sector baselines for: Manufacturing, Transport/Logistics, Construction, Tourism, Retail, Mining/Extractives, Media, Professional Services, Waste Management, ICT
  - File: `data/sector_baselines.yaml` (after §1.3.1)
  - Ref: Review §2.2

- [ ] **5.1.2** Add SDG sector relevance for all new sectors
  - File: `data/sdg_keyword_map.yaml` (after §1.3.2)
  - Ref: Review §2.2

- [ ] **5.1.3** Add benchmark data for new sectors
  - File: `src/openharness/impact/benchmarks.py`
  - Ref: Review §2.2

- [ ] **5.1.4** Add sector-specific DD questions for new sectors (manufacturing, transport, etc.)
  - File: `data/dd_checklist.yaml`
  - Ref: Review §2.2

### 5.2 Improve Contribution / Additionality Assessment

- [ ] **5.2.1** Add additionality heuristics — check for "unique", "first-of-kind", "underserved market", "no existing solution" language
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.9

- [ ] **5.2.2** Add benchmark comparison for contribution — compare against market alternatives
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.9

- [ ] **5.2.3** Add counterfactual prompt — flag for human review: "What would happen without this intervention?"
  - File: `src/openharness/tools/impact/five_dimension_assess_tool.py`
  - Ref: Review §2.9

### 5.3 Add Negative Impact / Do No Harm Assessment

- [ ] **5.3.1** Add negative impact penalty to 5D risk dimension — reduce score when adverse impact risks are identified without mitigation
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.10

- [ ] **5.3.2** Add controversy check integration stub — placeholder for external data source
  - File: `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §2.10

- [ ] **5.3.3** Integrate exclusion screening results into risk scoring
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.10

### 5.4 Expand Cross-Reference Map

- [ ] **5.4.1** Add cross-references for: land use, community development, training/education outcomes, financial inclusion depth, access metrics, product safety, customer satisfaction
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §2.4

- [ ] **5.4.2** Add metric-level SASB cross-references (not just dimension-level)
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §2.4

- [ ] **5.4.3** Expand GRI cross-references for IRIS+ metrics that currently lack equivalents
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §2.4

### 5.5 Enhance Risk/Opportunity Assessment

- [ ] **5.5.1** Add missing risk categories: concentration risk, regulatory/policy risk, reputational risk, exit risk, data integrity risk
  - File: `data/risk_rules.yaml` (after §1.3.4)
  - Ref: Review §2.8

- [ ] **5.5.2** Add risk matrix (likelihood × severity) instead of severity-only
  - File: `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §2.8

- [ ] **5.5.3** Add more opportunity triggers — beyond 6 keywords
  - File: `data/risk_rules.yaml` (after §1.3.4)
  - Ref: Review §2.8

### 5.6 Improve ImpactClaim Model

- [ ] **5.6.1** Fix confidence calculation — replace `min(1.0, keyword_hits * 0.15)` with more calibrated formula
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.2

- [ ] **5.6.2** Add `evidence_strength` field — NESTA-inspired 1-5 scale
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.2

- [ ] **5.6.3** Add `negation_detected` field — flag claims with negation context
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.2

- [ ] **5.6.4** Add `entities` field — extracted stakeholders, geographies, outcomes
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.2

---

## Phase 6: Architecture & Quality 🏗️

### 6.1 Refactor Report Generation

- [ ] **6.1.1** Extract `_to_html()` from `impact_report_tool.py` into separate template engine
  - File: `src/openharness/impact/report_templates/` (new directory)
  - Ref: Review §6.2

- [ ] **6.1.2** Create Jinja2 or string-template based HTML report system
  - File: `src/openharness/impact/report_templates/html_template.py` (new)
  - Ref: Review §6.2

### 6.2 Add Persistence Layer

- [ ] **6.2.1** Add SQLite-based persistence for company assessments — save/retrieve between sessions
  - File: `src/openharness/impact/storage.py` (new)
  - Ref: Review §6.2

- [ ] **6.2.2** Add session history — track all tool invocations and results per company
  - File: `src/openharness/impact/storage.py`
  - Ref: Review §6.2

### 6.3 Fix Circular Import Risks

- [ ] **6.3.1** Audit all inter-framework imports and replace lazy method-level imports with proper module structure
  - Files: `src/openharness/impact/frameworks/*.py`
  - Ref: Review §6.2

### 6.4 Test Coverage Expansion

- [ ] **6.4.1** Add tests for report generation (HTML, CSV, XLSX)
  - File: `tests/test_report_generation.py` (new)
  - Ref: Review §6.3

- [ ] **6.4.2** Add tests for LP DDQ export
  - File: `tests/test_lp_ddq_export.py` (new)
  - Ref: Review §6.3

- [ ] **6.4.3** Add tests for pitch deck analysis (create PDF/TXT/MD fixtures)
  - File: `tests/test_pitch_deck.py` (new)
  - Ref: Review §6.3

- [ ] **6.4.4** Add tests for ISSB framework (once implemented)
  - File: `tests/test_impact.py` (extend)
  - Ref: Review §6.3

- [ ] **6.4.5** Add tests for ESRS framework (once implemented)
  - File: `tests/test_impact.py` (extend)
  - Ref: Review §6.3

---

## Summary Statistics

| Phase | Items | Category |
|-------|-------|----------|
| Phase 1: Critical 🔴 | 38 | Scoring accuracy, greenwashing, tests, data model |
| Phase 2: Important 🟡 | 39 | Time-series, exclusion screening, targets, ISSB, DDQ |
| Phase 3: Missing Features 🟢 | 27 | Narratives, feedback, benchmarking, API, audit |
| Phase 4: Regulatory 📜 | 14 | CSRD/ESRS, Green Claims, SFDR, NLP, DPP |
| Phase 5: Scoring Engine 🎯 | 23 | Sectors, additionality, risk, cross-refs, claims |
| Phase 6: Architecture 🏗️ | 8 | Refactoring, persistence, tests |
| **Total** | **149** | |

---

*Last updated: 2025-01. Derived from `IMPACT_MANAGER_REVIEW.md`.*
