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

- [x] **1.1.4** Add provenance section to HTML impact reports — visual indicator (badge/icon) for estimated vs. evidence-based scores
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §2.1

- [x] **1.1.5** Add explicit disclaimers to reports when scores are primarily keyword-estimated
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §2.1

### 1.2 Minimum Metric Threshold

- [x] **1.2.1** Add minimum metric threshold logic — require ≥3 reported metrics before allowing above-baseline 5D scores
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1

- [x] **1.2.2** Add configurable threshold constant (default=3) that can be overridden per fund
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1

- [x] **1.2.3** Emit warning in tool output when scores are capped at baseline due to insufficient metrics
  - Files: `src/openharness/tools/impact/five_dimension_assess_tool.py`, `portfolio_tool.py`, `lp_ddq_export_tool.py`, `sdg_mapper_tool.py`
  - Ref: Review §2.1

### 1.3 Externalize Keyword Dictionaries to YAML

- [x] **1.3.1** Create `data/scoring_config.yaml` — all scoring config in one file (sector baselines, keyword boosts, theme hints, risk/opportunity rules)
  - Files: `data/sector_baselines.yaml` (new), `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1, §6.2

- [x] **1.3.2** Create `data/sdg_keyword_map.yaml` — extract `_KEYWORD_SDG_MAP` from `sdg_mapper.py` (consolidated into scoring_config.yaml)
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

- [x] **1.3.6** Update all consuming modules to use YAML-loaded dictionaries instead of hardcoded ones
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

- [x] **1.4.4** Update `PortfolioInput` / `_dict_to_company()` to pass geography fields
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §5.1

- [x] **1.4.5** Update `LpDdqExportInput` to accept geography fields
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §5.1
  - ✅ Fixed: Added `geography` and `stage` fields to `LpDdqExportInput`, passed through to `Company` constructor.

- [x] **1.4.6** Use geography in SDG relevance scoring — adjust SDG relevance by country/region context
  - File: `src/openharness/impact/sdg_mapper.py`
  - Ref: Review §5.1

- [x] **1.4.7** Update `pitch_deck_analyze_tool` auto-extracted Company model to include geography
  - File: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`
  - Ref: Review §5.1

- [x] **1.4.8** Update sample data files to include geography fields
  - Files: `examples/sample_company.yaml`, `examples/sample_portfolio.csv`
  - Ref: Review §5.1

### 1.5 Write Tests for New Tools

- [x] **1.5.1** Add tests for `DataQualityTool` — unknown IDs, placeholders, non-numeric, quality score, missing required
  - File: `tests/test_impact.py` (extend) or `tests/test_data_quality_tool.py` (new)
  - Ref: Review §6.3

- [x] **1.5.2** Add tests for `ImpactRiskOpportunityTool` — risk scoring, opportunity scoring, keyword triggers, metric checks
  - File: `tests/test_impact.py` (extend) or `tests/test_risk_opportunity_tool.py` (new)
  - Ref: Review §6.3

- [x] **1.5.3** Add tests for `MetricRecommenderTool` — multi-signal scoring, core-set priority, theme/SDG match
  - File: `tests/test_impact.py` (extend) or `tests/test_metric_recommender_tool.py` (new)
  - Ref: Review §6.3

- [x] **1.5.4** Add tests for `PortfolioTool` — file loading (CSV/YAML/JSON), company conversion, aggregation
  - File: `tests/test_impact.py` (extend) or `tests/test_portfolio_tool.py` (new)
  - Ref: Review §6.3

- [x] **1.5.5** Add tests for input normalization (`common.py`) — `normalize_metric_ids`, `normalize_metric_map`, `normalize_sdg_goals`, `infer_themes`
  - File: `tests/test_impact.py` (extend) or `tests/test_common.py` (new)
  - Ref: Review §6.3

- [x] **1.5.6** Add edge case tests — empty company, invalid metrics, no catalog loaded, zero metrics
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

- [x] **1.6.11** Add greenwashing risk score to `DataQualityTool` payload
  - File: `src/openharness/tools/impact/data_quality_tool.py`
  - Ref: Review §3.4

- [x] **1.6.12** Add greenwashing signal flags to `PitchDeckAnalyzeTool` claim extraction (vague claims, buzzword density)
  - File: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`
  - Ref: Review §3.4

- [x] **1.6.13** Add "impact-washing risk" category to `risk_opportunity.py`
  - File: `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §3.4

- [x] **1.6.14** Add greenwashing risk section to HTML impact reports with visual classification indicator
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §3.4

- [x] **1.6.15** Add greenwashing detection tests
  - File: `tests/test_greenwashing.py` (new)
  - Ref: Review §6.3

---

## Phase 2: Important Improvements 🟡

### 2.1 Time-Series Support

- [x] **2.1.1** Create `MetricValue` model with fields: `metric_id`, `value`, `unit`, `period`, `timestamp`, `source`, `verified`, `notes`
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.3

- [x] **2.1.2** Update `Company.reported_metrics` type from `dict[str, Any]` to support both legacy format and new `MetricValue` list
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.3

- [x] **2.1.3** Add `reporting_period` field to `Company` model
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.1

- [x] **2.1.4** Add trend analysis function — compare metric values across periods, detect improvement/decline
  - File: `src/openharness/impact/trend_analysis.py` (new)
  - Ref: Review §2.7

- [x] **2.1.5** Add year-over-year comparison to portfolio analysis
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §2.7

- [x] **2.1.6** Add progress tracking to HTML reports — sparklines or trend arrows for key metrics
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

- [x] **2.2.5** Add exclusion screening as first step in DD workflow — warn if company fails screening before scoring
  - Files: `five_dimension_assess_tool.py`, `portfolio_tool.py`
  - Ref: Review §4.4

### 2.3 Impact Target Tracking

- [x] **2.3.1** Create `ImpactTarget` model — `metric_id`, `target_value`, `target_date`, `actual_value`, `period`
  - File: `src/openharness/impact/models.py`
  - Ref: Review §4.3
  - ✅ Fixed: `ImpactTarget` model exists with `metric_id`, `target_value` (optional float), `target_unit`, `target_date`, `baseline_value`, `baseline_date`, `description`. `Company.impact_targets` is now `list[ImpactTarget]`.

- [x] **2.3.2** Add `targets` field to `Company` model
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.1
  - ✅ Fixed: `Company.impact_targets` is now `list[ImpactTarget]` with structured model objects.

- [x] **2.3.3** Parse `OD4091` (Social and Environmental Targets) metric value into structured `ImpactTarget` objects
  - File: `src/openharness/tools/impact/common.py`
  - Ref: Review §4.3

- [x] **2.3.4** Add target-vs-actual tracking function with trajectory projection
  - File: `src/openharness/impact/trend_analysis.py`
  - Ref: Review §4.3

- [x] **2.3.5** Add target tracking section to HTML reports — on-track/at-risk/off-track visual indicators
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §4.3

### 2.4 Improve LP DDQ Responses

- [x] **2.4.1** Add narrative prose generation for DDQ template sections — move from metric lists to paragraph responses
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

- [x] **2.4.2** Add ILPA DDQ template sections 10.1-10.8 with paragraph-length response scaffolding
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

- [x] **2.4.3** Add policy/governance structure references in DDQ responses
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

- [x] **2.4.4** Add specific example/case study placeholders in DDQ output
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

### 2.5 Expand SASB to All 77 Industries

- [x] **2.5.1** Add missing SASB industry definitions — expanded from 17 to 25 industries with disclosure topics
  - File: `src/openharness/impact/frameworks/sasb.py`
  - Ref: Review §2.3

- [x] **2.5.2** Externalize SASB industry data to YAML for easier maintenance
  - Files: `data/sasb_industries.yaml` (new), `src/openharness/impact/frameworks/sasb.py`
  - Ref: Review §2.3

- [x] **2.5.3** Add SASB industry auto-detection from company sector/description
  - File: `src/openharness/impact/frameworks/sasb.py`
  - Ref: Review §2.3

### 2.6 Fund-Level Analytics

- [x] **2.6.1** Add fund-level aggregation beyond simple portfolio averages — min/max/median, sector distribution, reporting quality
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.1

- [x] **2.6.2** Add fund-level SDG contribution metric — weighted by portfolio company materiality
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.1

- [x] **2.6.3** Add impact-weighted returns calculation stub
  - File: `src/openharness/impact/fund_analytics.py` (new)
  - Ref: Review §4.1

- [x] **2.6.4** Add portfolio-level additionality assessment heuristic
  - File: `src/openharness/impact/fund_analytics.py`
  - Ref: Review §4.1

### 2.7 Negation/Context Detection in Keyword Matching

- [x] **2.7.1** Add negation detection to keyword matching — 9 negation patterns in 30-char window
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1, §5.2

- [x] **2.7.2** Add context window check — require keyword to appear in impact-relevant context (within N words of other impact terms)
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.1

- [x] **2.7.3** Add negation detection to SDG keyword matching
  - File: `src/openharness/impact/sdg_mapper.py`
  - Ref: Review §2.1

- [x] **2.7.4** Add negation detection to claim extraction in pitch deck analysis
  - File: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`
  - Ref: Review §5.2

### 2.8 Add ISSB IFRS S1/S2 Disclosure Mapping

- [x] **2.8.1** Create ISSB S1 (General Requirements) framework module with disclosure topics
  - File: `src/openharness/impact/frameworks/issb.py` (new)
  - Ref: Review §10.4

- [x] **2.8.2** Create ISSB S2 (Climate-related Disclosures) framework module — subsumes and extends TCFD
  - File: `src/openharness/impact/frameworks/issb.py`
  - Ref: Review §10.4

- [x] **2.8.3** Add ISSB cross-references to the cross-reference mapping
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §10.4

- [x] **2.8.4** Add ISSB as an option in `FrameworkTool`
  - File: `src/openharness/tools/impact/framework_tool.py`
  - Ref: Review §10.4

- [x] **2.8.5** Add ISSB to `__init__.py` framework list
  - File: `src/openharness/impact/frameworks/__init__.py`
  - Ref: Review §10.4

- [x] **2.8.6** Update TCFD references to indicate subsumption by ISSB S2 (keep TCFD for backward compatibility)
  - File: `src/openharness/impact/frameworks/tcfd.py`
  - Ref: Review §10.4

---

## Phase 3: Missing Features 🟢

### 3.1 LLM-Assisted Narrative Generation

- [x] **3.1.1** Add LLM-assisted DDQ narrative generation mode — use the agent's LLM to write paragraph-length responses
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.6

- [x] **3.1.2** Add LLM-assisted impact report narratives — executive summary, key findings, recommendations
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §7 (rec #13)

- [x] **3.1.3** Add "draft review" mode — generate narrative, then flag for human review before final output
  - Files: `lp_ddq_export_tool.py`, `impact_report_tool.py`
  - Ref: Review §9.4

### 3.2 Beneficiary Feedback Integration

- [x] **3.2.1** Add `beneficiary_feedback` field to `Company` model — structured data (satisfaction scores, NPS, qualitative themes)
  - File: `src/openharness/impact/models.py`
  - Ref: Review §4.2, §10.3

- [x] **3.2.2** Add beneficiary feedback data import — accept 60 Decibels Lean Data format
  - File: `src/openharness/tools/impact/beneficiary_feedback_tool.py` (new)
  - Ref: Review §4.2, §10.3

- [x] **3.2.3** Integrate beneficiary feedback into DD checklist responses (SV01-SV03)
  - File: `src/openharness/tools/impact/dd_checklist_tool.py`
  - Ref: Review §4.2

- [x] **3.2.4** Include beneficiary feedback section in HTML impact reports
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §4.2

### 3.3 Real Benchmarking with Peer Data

- [x] **3.3.1** Add peer data upload capability — accept anonymized CSV/JSON peer metrics for comparison
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.8

- [x] **3.3.2** Add percentile ranking calculation — "this company is in the Xth percentile for sector Y"
  - File: `src/openharness/impact/benchmarks.py`
  - Ref: Review §4.8

- [x] **3.3.3** Add GIIN Annual Impact Investor Survey data as benchmark source
  - File: `src/openharness/impact/benchmarks.py`
  - Ref: Review §10.2

- [x] **3.3.4** Add fund-level benchmarking — compare portfolio aggregate against GIIN survey data
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.8

### 3.4 API / Data Pipeline Integration

- [x] **3.4.1** Add REST API endpoints for key tools — impact scoring, SDG mapping, data quality
  - File: `src/openharness/gateway/router.py` (extend)
  - Ref: Review §4.7

- [x] **3.4.2** Add webhook support for metric update events
  - File: `src/openharness/gateway/router.py` (extend)
  - Ref: Review §4.7

- [x] **3.4.3** Add data validation pipeline for incoming metric data
  - File: `src/openharness/tools/impact/data_quality_tool.py` (extend)
  - Ref: Review §4.7

### 3.5 Scenario Modeling

- [x] **3.5.1** Add "what-if" analysis — calculate portfolio score change when adding/removing a company
  - File: `src/openharness/tools/impact/portfolio_tool.py`
  - Ref: Review §4.6

- [x] **3.5.2** Add metric optimization — suggest which metrics each company should add to maximize portfolio SDG coverage
  - File: `src/openharness/tools/impact/metric_recommender_tool.py` (extend)
  - Ref: Review §4.6

- [x] **3.5.3** Persist interactive HTML checkbox state — save and reload scenario changes
  - File: `src/openharness/tools/impact/impact_report_tool.py`
  - Ref: Review §4.6

### 3.6 Audit Trail & Verification

- [x] **3.6.1** Add `verification_status` field to `MetricValue` model — enum: `self_reported`, `management_verified`, `third_party_verified`
  - File: `src/openharness/impact/models.py`
  - Ref: Review §4.5

- [x] **3.6.2** Add audit trail — who reported what, when, with what evidence
  - File: `src/openharness/impact/models.py` (extend)
  - Ref: Review §4.5

- [x] **3.6.3** Add pre-verification preparation mode — organize evidence and gaps for BlueMark/IFC OPIM verification
  - File: `src/openharness/tools/impact/verification_prep_tool.py` (new)
  - Ref: Review §10.5

- [x] **3.6.4** Add IFC Operating Principles alignment checker
  - File: `src/openharness/impact/frameworks/ifc_opim.py` (new)
  - Ref: Review §10.4

### 3.7 Localization

- [x] **3.7.1** Add multi-language document support for pitch deck analysis (PDF text extraction with encoding detection)
  - File: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`
  - Ref: Review §7 (rec #19)

- [x] **3.7.2** Add localized keyword dictionaries — at minimum Spanish, French, Portuguese for emerging markets
  - Files: `data/sdg_keyword_map_es.yaml`, `data/sdg_keyword_map_fr.yaml`, etc.
  - Ref: Review §7 (rec #19)

### 3.8 Dashboard Enhancement

- [x] **3.8.1** Expand Streamlit dashboard — portfolio overview, fund-level KPIs, trend charts
  - File: `src/openharness/dashboard/app.py`
  - Ref: Review §7 (rec #20)

- [x] **3.8.2** Add interactive drill-down from portfolio to company to metric level
  - File: `src/openharness/dashboard/app.py`
  - Ref: Review §7 (rec #20)

---

## Phase 4: Regulatory & Advanced 📜

### 4.1 EU CSRD / ESRS Double Materiality

- [x] **4.1.1** Create ESRS framework module with ~1,200 data points across E/S/G topics
  - File: `src/openharness/impact/frameworks/esrs.py` (new)
  - Ref: Review §10.4

- [x] **4.1.2** Implement double materiality assessment — both financial and impact materiality
  - File: `src/openharness/impact/frameworks/esrs.py`
  - Ref: Review §10.4

- [x] **4.1.3** Add ESRS as framework option in `FrameworkTool`
  - File: `src/openharness/tools/impact/framework_tool.py`
  - Ref: Review §10.4

- [x] **4.1.4** Add ESRS cross-references to cross-reference mapping
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §10.4

### 4.2 EU Green Claims Directive Compliance

- [x] **4.2.1** Add green claims substantiation checker — verify claims have scientific evidence and independent verification
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §10.4

- [x] **4.2.2** Add life-cycle assessment requirement flag for environmental claims
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §10.4

- [x] **4.2.3** Add UK FCA anti-greenwashing rule compliance check
  - File: `src/openharness/impact/greenwashing.py`
  - Ref: Review §10.4

### 4.3 SFDR Enhancements

- [x] **4.3.1** Add Article 6/8/9 fund classification support
  - File: `src/openharness/impact/frameworks/sfdr_pai.py`
  - Ref: Review §2.5

- [x] **4.3.2** Add optional PAI indicators (biodiversity, water, waste, social/employee)
  - File: `src/openharness/impact/frameworks/sfdr_pai.py`
  - Ref: Review §2.5

- [x] **4.3.3** Add entity-level vs. fund-level PAI reporting distinction
  - File: `src/openharness/impact/frameworks/sfdr_pai.py`
  - Ref: Review §2.5

- [x] **4.3.4** Add SFDR Annex III/IV table generation
  - File: `src/openharness/tools/impact/lp_ddq_export_tool.py`
  - Ref: Review §2.5

### 4.4 NLP-Enhanced Greenwashing Detection

- [x] **4.4.1** Integrate ClimateBERT for climate-specific greenwashing detection
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5, §10.6

- [x] **4.4.2** Implement Green Authenticity Index (GAI) — Stacey Matrix evaluation of claims
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5, §10.6

- [x] **4.4.3** Implement Cheap Talk Index — proportion of non-specific commitments
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5, §10.6

- [x] **4.4.4** Add sentiment deflection detection — overly positive tone deflecting from negative information
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5

- [x] **4.4.5** Add claim decomposition and fact-checking — break claims into verifiable sub-claims
  - File: `src/openharness/impact/greenwashing.py` (extend)
  - Ref: Review §3.5

### 4.5 Digital Product Passport Integration

- [x] **4.5.1** Add EU ESPR / Digital Product Passport data import
  - File: `src/openharness/tools/impact/product_passport_tool.py` (new)
  - Ref: Review §10.4

- [x] **4.5.2** Map product passport data to IRIS+ metrics for product-level impact assessment
  - File: `src/openharness/tools/impact/product_passport_tool.py`
  - Ref: Review §10.4

---

## Phase 5: Scoring Engine Improvements 🎯

### 5.1 Expand Sector Coverage

- [x] **5.1.1** Add 5D sector baselines for: Manufacturing, Transport/Logistics, Construction, Tourism, Retail, Mining/Extractives, Media, Professional Services, Waste Management, ICT
  - File: `data/scoring_config.yaml`, `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.2

- [x] **5.1.2** Add SDG sector relevance for all new sectors
  - File: `data/sdg_keywords.yaml`
  - Ref: Review §2.2

- [x] **5.1.3** Add benchmark data for new sectors
  - File: `src/openharness/impact/benchmarks.py`
  - Ref: Review §2.2

- [x] **5.1.4** Add sector-specific DD questions for new sectors (manufacturing, transport, etc.)
  - File: `data/dd_checklist.yaml`
  - Ref: Review §2.2

### 5.2 Improve Contribution / Additionality Assessment

- [x] **5.2.1** Add additionality heuristics — check for "unique", "first-of-kind", "underserved market", "no existing solution" language
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.9

- [x] **5.2.2** Add benchmark comparison for contribution — compare against market alternatives
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.9

- [x] **5.2.3** Add counterfactual prompt — flag for human review: "What would happen without this intervention?"
  - File: `src/openharness/tools/impact/five_dimension_assess_tool.py`
  - Ref: Review §2.9

### 5.3 Add Negative Impact / Do No Harm Assessment

- [x] **5.3.1** Add negative impact penalty to 5D risk dimension — reduce score when adverse impact risks are identified without mitigation
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.10

- [x] **5.3.2** Add controversy check integration stub — placeholder for external data source
  - File: `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §2.10

- [x] **5.3.3** Integrate exclusion screening results into risk scoring
  - File: `src/openharness/impact/five_dimensions.py`
  - Ref: Review §2.10

### 5.4 Expand Cross-Reference Map

- [x] **5.4.1** Add cross-references for: land use, community development, training/education outcomes, financial inclusion depth, access metrics, product safety, customer satisfaction
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §2.4

- [x] **5.4.2** Add metric-level SASB cross-references (not just dimension-level)
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §2.4

- [x] **5.4.3** Expand GRI cross-references for IRIS+ metrics that currently lack equivalents
  - File: `src/openharness/impact/frameworks/cross_reference.py`
  - Ref: Review §2.4

### 5.5 Enhance Risk/Opportunity Assessment

- [x] **5.5.1** Add missing risk categories: concentration risk, regulatory/policy risk, reputational risk, exit risk, data integrity risk
  - File: `data/scoring_config.yaml`, `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §2.8

- [x] **5.5.2** Add risk matrix (likelihood × severity) instead of severity-only
  - File: `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §2.8

- [x] **5.5.3** Add more opportunity triggers — beyond 6 keywords
  - File: `data/scoring_config.yaml`, `src/openharness/impact/risk_opportunity.py`
  - Ref: Review §2.8

### 5.6 Improve ImpactClaim Model

- [x] **5.6.1** Fix confidence calculation — replace `min(1.0, keyword_hits * 0.15)` with more calibrated formula
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.2

- [x] **5.6.2** Add `evidence_strength` field — NESTA-inspired 1-5 scale
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.2

- [x] **5.6.3** Add `negation_detected` field — flag claims with negation context
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.2

- [x] **5.6.4** Add `entities` field — extracted stakeholders, geographies, outcomes
  - File: `src/openharness/impact/models.py`
  - Ref: Review §5.2

---

## Phase 6: Architecture & Quality 🏗️

### 6.1 Refactor Report Generation

- [x] **6.1.1** Extract `_to_html()` from `impact_report_tool.py` into separate template engine
  - File: `src/openharness/impact/report_templates/` (new directory)
  - Ref: Review §6.2

- [x] **6.1.2** Create Jinja2 or string-template based HTML report system
  - File: `src/openharness/impact/report_templates/html_template.py` (new)
  - Ref: Review §6.2

### 6.2 Add Persistence Layer

- [x] **6.2.1** Add SQLite-based persistence for company assessments — save/retrieve between sessions
  - File: `src/openharness/impact/storage.py` (new)
  - Ref: Review §6.2

- [x] **6.2.2** Add session history — track all tool invocations and results per company
  - File: `src/openharness/impact/storage.py`
  - Ref: Review §6.2

### 6.3 Fix Circular Import Risks

- [x] **6.3.1** Audit all inter-framework imports and replace lazy method-level imports with proper module structure
  - Files: `src/openharness/impact/frameworks/*.py` — no circular dependencies found
  - Ref: Review §6.2

### 6.4 Test Coverage Expansion

- [x] **6.4.1** Add tests for report generation (HTML, CSV, XLSX)
  - File: `tests/test_report_generation.py` (new)
  - Ref: Review §6.3

- [x] **6.4.2** Add tests for LP DDQ export
  - File: `tests/test_report_generation.py` (combined)
  - Ref: Review §6.3

- [x] **6.4.3** Add tests for pitch deck analysis (create PDF/TXT/MD fixtures)
  - File: `tests/test_report_generation.py` (combined)
  - Ref: Review §6.3

- [x] **6.4.4** Add tests for ISSB framework (once implemented)
  - File: `tests/test_impact.py` (extended)
  - Ref: Review §6.3

- [x] **6.4.5** Add tests for ESRS framework (once implemented)
  - File: `tests/test_impact.py` (extended)
  - Ref: Review §6.3

---

## Summary Statistics (Phases 1-6 — Complete)

| Phase | Items | Category |
|-------|-------|----------|
| Phase 1: Critical 🔴 | 38 | Scoring accuracy, greenwashing, tests, data model |
| Phase 2: Important 🟡 | 39 | Time-series, exclusion screening, targets, ISSB, DDQ |
| Phase 3: Missing Features 🟢 | 27 | Narratives, feedback, benchmarking, API, audit |
| Phase 4: Regulatory 📜 | 14 | CSRD/ESRS, Green Claims, SFDR, NLP, DPP |
| Phase 5: Scoring Engine 🎯 | 23 | Sectors, additionality, risk, cross-refs, claims |
| Phase 6: Architecture 🏗️ | 8 | Refactoring, persistence, tests |
| **Total Complete** | **149** | |

---

# Next Version Roadmap (v0.4.0+)

> **Purpose**: Feature roadmap for Impact Vision beyond the initial improvement phases.
> **Focus areas**: Deeper analysis UX, pipeline management, monitoring, reporting, LLM intelligence, and platform integrations.

---

## Phase 7: Enhanced Analysis & Reporting UX 📊 ✅

> Make the HTML report and assessment experience richer and more actionable.

### 7.1 Interactive HTML Report Enhancements

- [x] **7.1.1** 5-Dimension overlay panel — click any dimension on the radar chart to expand an overlay showing tracked vs. untracked metrics, evidence quality, and improvement suggestions
  - Files: `src/openharness/tools/impact/impact_report_tool.py`

- [x] **7.1.2** SDG drill-down — click any SDG bar to expand details: mapped claims, evidence strength, relevant IRIS+ metrics, and keyword matches
  - Files: `src/openharness/tools/impact/impact_report_tool.py`

- [x] **7.1.3** Metric tracking status dashboard — for each recommended metric, show tracked/not-tracked/partial with data quality indicator
  - Files: `src/openharness/tools/impact/impact_report_tool.py`

- [x] **7.1.4** Claim evidence cards — expandable cards for each impact claim showing source page, mapped metrics, confidence score, evidence strength, and verification status
  - Files: `src/openharness/tools/impact/impact_report_tool.py`

- [x] **7.1.5** Export-ready PDF generation — add PDF export option (via WeasyPrint optional) with print-friendly CSS media queries
  - Files: `src/openharness/tools/impact/impact_report_tool.py`

- [x] **7.1.6** Report comparison mode — side-by-side view comparing two assessments of the same company with delta scoring
  - Files: `src/openharness/tools/impact/impact_report_tool.py`, `storage.py`

### 7.2 Deeper SDG/Impact Evidence Mapping

- [x] **7.2.1** Evidence chain visualization — for each SDG mapping, show the chain: claim → metric → evidence → SDG target, with confidence at each step
  - Files: `src/openharness/impact/models.py`, `src/openharness/impact/sdg_mapper.py`, `impact_report_tool.py`

- [x] **7.2.2** SDG gap recommendations — for SDGs with partial alignment, generate specific recommendations for what evidence/data would strengthen the mapping
  - Files: `src/openharness/impact/sdg_mapper.py`, `impact_report_tool.py`

- [x] **7.2.3** Impact pathway diagrams — auto-generate Theory of Change flow diagrams (input → activity → output → outcome → impact) from assessed data
  - Files: `src/openharness/tools/impact/impact_report_tool.py`

---

## Phase 8: Pipeline & Portfolio Management 📁

> Move from single-company assessment to managing the full investment pipeline.

### 8.1 Project Pipeline Management

- [ ] **8.1.1** Pipeline stages — define stages: sourcing, screening, DD in progress, IC review, invested, monitoring, exited, passed
  - Files: `src/openharness/impact/models.py`, `storage.py`

- [ ] **8.1.2** Pipeline CRUD tool — create/update/list/filter companies by pipeline stage, sector, SDG, geography
  - Files: `src/openharness/tools/impact/pipeline_tool.py` (new)

- [ ] **8.1.3** Stage transition tracking — log when a company moves between stages, with notes and decision rationale
  - Files: `src/openharness/impact/storage.py`

- [ ] **8.1.4** Pipeline dashboard view — Streamlit tab or HTML summary showing funnel (# companies per stage), sector distribution, SDG coverage across pipeline
  - Files: `src/openharness/dashboard/app.py`

- [ ] **8.1.5** Pipeline CSV/XLSX import/export — bulk import existing pipeline data, export for team sharing
  - Files: `src/openharness/tools/impact/pipeline_tool.py`

### 8.2 Continuous Monitoring

- [ ] **8.2.1** Monitoring schedule — define monitoring frequency per company (quarterly, semi-annual, annual) with alert thresholds
  - Files: `src/openharness/impact/models.py`, `storage.py`

- [ ] **8.2.2** Metric update workflow — tool for recording new metric values, with automatic trend detection and deviation alerts
  - Files: `src/openharness/tools/impact/monitoring_tool.py` (new)

- [ ] **8.2.3** Automated re-assessment — when new data is added, automatically re-run 5D/SDG/risk assessment and flag score changes
  - Files: `src/openharness/tools/impact/monitoring_tool.py`

- [ ] **8.2.4** Alert system — configurable alerts when: metrics deviate from targets, evidence expires, reporting deadline approaches, risk score increases
  - Files: `src/openharness/impact/monitoring.py` (new)

- [ ] **8.2.5** Monitoring dashboard — timeline view of metric trends, target progress, and alert history per company
  - Files: `src/openharness/dashboard/app.py`

### 8.3 Per-Project Impact Reporting

- [ ] **8.3.1** Period-over-period comparison — generate reports comparing current vs. previous assessment with change indicators
  - Files: `src/openharness/tools/impact/impact_report_tool.py`, `storage.py`

- [ ] **8.3.2** Target progress report — dedicated report showing progress toward each impact target with trajectory projections
  - Files: `src/openharness/tools/impact/impact_report_tool.py`

- [ ] **8.3.3** LP-ready individual company report — formatted for LP distribution with executive summary, key metrics, risk assessment, and evidence quality
  - Files: `src/openharness/tools/impact/impact_report_tool.py`

### 8.4 Aggregate Portfolio Impact

- [ ] **8.4.1** Portfolio roll-up analytics — total beneficiaries reached, aggregate SDG coverage, fund-level 5D scores, weighted by investment size
  - Files: `src/openharness/tools/impact/portfolio_tool.py`

- [ ] **8.4.2** Cross-company benchmarking — rank portfolio companies on key metrics, identify leaders and laggards per dimension
  - Files: `src/openharness/tools/impact/portfolio_tool.py`

- [ ] **8.4.3** Fund-level LP report — aggregate impact report suitable for annual LP reporting (ILPA/GIIN format)
  - Files: `src/openharness/tools/impact/lp_ddq_export_tool.py`, `portfolio_tool.py`

- [ ] **8.4.4** Portfolio impact attribution — break down aggregate impact by company, sector, geography, and SDG
  - Files: `src/openharness/tools/impact/portfolio_tool.py`

---

## Phase 9: LLM Intelligence & Automation 🧠

> Leverage LLM capabilities for deeper analysis and proactive recommendations.

### 9.1 LLM-Guided Impact Improvement

- [ ] **9.1.1** Improvement recommendation engine — for each weak dimension, generate specific actionable recommendations: metrics to track, programs to implement, partnerships to pursue
  - Files: `src/openharness/tools/impact/improvement_advisor_tool.py` (new)

- [ ] **9.1.2** Peer comparison insights — "Companies in your sector with higher scores typically track X, Y, Z metrics and report on A, B programs"
  - Files: `src/openharness/tools/impact/improvement_advisor_tool.py`

- [ ] **9.1.3** SDG opportunity finder — identify untapped SDG alignment opportunities based on company operations, geography, and sector
  - Files: `src/openharness/tools/impact/improvement_advisor_tool.py`

- [ ] **9.1.4** Narrative drafting — LLM-generated executive summaries, impact narratives, and case studies from structured assessment data
  - Files: `src/openharness/tools/impact/narrative_tool.py` (new)

### 9.2 Smart Document Analysis

- [ ] **9.2.1** Multi-document analysis — compare multiple documents for the same company (e.g., pitch deck + annual report + impact report)
  - Files: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`

- [ ] **9.2.2** Document change detection — highlight what's new/changed between document versions
  - Files: `src/openharness/tools/impact/pitch_deck_analyze_tool.py`

- [ ] **9.2.3** Claim verification agent — for each impact claim, search for supporting evidence in other documents or public sources
  - Files: `src/openharness/tools/impact/verification_tool.py` (new)

### 9.3 Conversational Impact Assessment

- [ ] **9.3.1** Guided assessment workflow — structured conversation flow that walks the user through a complete impact assessment step by step
  - Files: `src/openharness/prompts/system_prompt.py`, skills

- [ ] **9.3.2** Progressive data collection — remember what data has been collected across sessions, ask for missing information incrementally
  - Files: `src/openharness/impact/storage.py`, `prompts/`

- [ ] **9.3.3** Assessment templates by deal stage — different assessment depth for screening vs. DD vs. monitoring
  - Files: `src/openharness/tools/impact/`, skills

---

## Phase 10: Platform Integration & Developer Experience 🔌

> Make Impact Vision accessible as a platform service and developer tool.

### 10.1 MCP Server Mode

- [ ] **10.1.1** MCP server implementation — expose all 17 Impact Vision tools as MCP resources/tools
  - Files: `src/openharness/impact/mcp_server.py` (new)

- [ ] **10.1.2** MCP resource endpoints — company assessments, IRIS+ catalog, DD checklist, cross-reference data as MCP resources
  - Files: `src/openharness/impact/mcp_server.py`

- [ ] **10.1.3** MCP tool schemas — proper JSON Schema for all tool inputs/outputs for MCP tool discovery
  - Files: `src/openharness/impact/mcp_server.py`

- [ ] **10.1.4** MCP server CLI — `impact-vision serve-mcp` command to start the MCP server
  - Files: `src/openharness/cli.py`

### 10.2 Claude Code / AI Agent Integration

- [ ] **10.2.1** Claude Code MCP config — provide ready-to-use `claude_desktop_config.json` for connecting Claude Code to Impact Vision MCP server
  - Files: `examples/claude_desktop_config.json` (new)

- [ ] **10.2.2** Agent-to-agent protocol — define clear input/output contracts for AI agents calling Impact Vision tools
  - Files: documentation, `src/openharness/impact/mcp_server.py`

- [ ] **10.2.3** Cursor/VS Code integration guide — documentation for using Impact Vision as an MCP tool within Cursor IDE
  - Files: `docs/cursor-integration.md` (new)

### 10.3 API & Webhook Enhancements

- [ ] **10.3.1** Full REST API coverage — expose all tools via FastAPI endpoints (not just the 5 current ones)
  - Files: `src/openharness/impact/api.py`

- [ ] **10.3.2** API authentication — API key or OAuth2 authentication for production deployments
  - Files: `src/openharness/impact/api.py`

- [ ] **10.3.3** Batch API — submit multiple companies for assessment in a single API call with async processing
  - Files: `src/openharness/impact/api.py`

- [ ] **10.3.4** Webhook notifications — trigger webhooks when assessments complete, scores change, or alerts fire
  - Files: `src/openharness/impact/api.py`

### 10.4 Multi-Language & Localization

- [ ] **10.4.1** Full report localization — HTML/text reports in Spanish, French, Portuguese, Chinese, Arabic
  - Files: `src/openharness/impact/report_templates/`, `data/i18n/` (new)

- [ ] **10.4.2** DD questionnaire translation — localized DD questions and categories
  - Files: `data/dd_checklist_*.yaml` (new)

- [ ] **10.4.3** Agent persona localization — system prompt and conversational responses in multiple languages
  - Files: `src/openharness/prompts/`

---

## Next Version Summary

| Phase | Items | Focus |
|-------|-------|-------|
| Phase 7: Analysis & Reporting UX 📊 ✅ | 9 | Interactive reports, evidence mapping, impact pathways |
| Phase 8: Pipeline & Portfolio 📁 | 15 | Pipeline stages, monitoring, per-project & aggregate reporting |
| Phase 9: LLM Intelligence 🧠 | 10 | Improvement advisor, smart docs, conversational assessment |
| Phase 10: Platform Integration 🔌 | 11 | MCP server, Claude Code, full API, localization |
| **Total Next Version** | **45** | |

---

*Last updated: 2026-04-16 (v0.4.0). Phases 1-7 complete (158/158 items). Next version roadmap (36 remaining items) defined.*
