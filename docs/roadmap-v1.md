# Impact Vision — Product Roadmap v1.0

**Date:** 2026-04-25  
**Audience:** Contributors, fund managers evaluating the platform, potential partners  
**Status:** Living document — updated quarterly

---

## Market Context

Impact investing AUM has grown at **21% CAGR** to over $1.5T (GIIN 2025). Yet 80% of fund IMM time is still spent cleaning disconnected data (Sopact), and fewer than 20% of impact funds have a connected measurement architecture. The $25K–$250K/year paid platforms (Novata, Sopact Sense, Proof, Sametrica) dominate but leave significant gaps that an open-source, AI-native tool can fill.

### Source-Informed Product Baseline: What Good Impact Tools Need

The 2026-04-25 review added a web research pass across current impact-management standards and market guidance. A strong impact tool should do more than produce reports; it should operate as a decision-useful impact management system.

| Baseline Capability | Why It Matters | Reference Standard / Source |
|---------------------|----------------|-----------------------------|
| Standard metric catalog with clear definitions, units, and sector guidance | Enables comparability and avoids ad hoc KPI sprawl | [GIIN IRIS+ Catalog](https://iris.thegiin.org/metrics/) and [IRIS+ Standards](https://iris.thegiin.org/standards/) |
| Outcome model across What, Who, How Much, Contribution, and Risk | Keeps assessment focused on actual changes for people and planet, including negative and unintended impacts | [Impact Frontiers Five Dimensions](https://impactfrontiers.org/norms/five-dimensions-of-impact/) |
| Lifecycle integration from strategy, origination, portfolio management, exit, and verification | Prevents impact from becoming an annual reporting exercise disconnected from investment decisions | [Operating Principles for Impact Management](https://www.impactprinciples.org/) |
| SDG impact governance, management, transparency, and assurance readiness | Makes SDG claims auditable and decision-useful instead of marketing labels | [UNDP SDG Impact Standards for Private Equity Funds](https://sdgfinance.undp.org/resource-library/sdg-impact-standards-private-equity-funds) |
| GHG accounting with Scope 1, Scope 2, Scope 3, financed emissions, and data quality scores | Carbon data is now a baseline LP and regulatory requirement | [GHG Protocol Corporate Standard FAQ](https://ghgprotocol.org/corporate-standard-frequently-asked-questions) and [PCAF Global GHG Standard](https://carbonaccountingfinancials.com/files/downloads/PCAF-Global-GHG-Standard.pdf) |
| Private-market ESG data convergence and LP-ready exports | Reduces duplicative data requests and supports comparable GP/LP reporting | [ILPA ESG Data Convergence Initiative](https://ilpa.org/ilpa_esg_roadmap/esg_data_convergence_project/) |
| Materiality, stakeholder engagement, and transparent management of impacts | Ensures reports cover significant positive and negative impacts, not only fund-favorable claims | [GRI Standards](https://www.globalreporting.org/standards) and [GRI 3: Material Topics](https://www.globalreporting.org/publications/documents/english/gri-3-material-topics-2021/) |

**Implication for Impact Vision:** the roadmap should prioritize data collection, evidence lineage, workflow controls, stakeholder voice, carbon/financed-emissions coverage, and assurance-ready exports before adding more narrative-only features.

### What Fund Managers Need (Research Summary)

| Need | Pain Level | Paid Platform Coverage | Impact Vision Coverage |
|------|------------|----------------------|----------------------|
| Pitch deck / memo intake & claim extraction | High | Sopact (partial) | ✅ Strong |
| IRIS+ / SDG mapping & 5D scoring | High | Sopact, Sametrica | ✅ Strong |
| Multi-framework ESG compliance (SFDR, CSRD, TCFD, ISSB) | Critical | Novata, Position Green, Workiva | ✅ Good (10 frameworks) |
| Greenwashing / impact-washing detection | High | None (gap) | ✅ Strong |
| Portfolio-level analytics & LP reporting | Critical | Novata, Allvue FPPM | 🟡 Basic |
| Real-time monitoring & alerts | High | Sopact (partial) | 🟡 Basic |
| Beneficiary / stakeholder voice integration | Medium | 60 Decibels, Sopact | 🟡 Basic |
| Counterfactual / causal analysis | High | None (gap) | 🔴 Stub only |
| Investee data collection portal | Critical | Novata (core feature) | 🔴 Missing |
| CRM / deal pipeline integration | High | Allvue, Dialllog | 🟡 Basic |
| Carbon accounting (Scope 1-2-3) | Critical | Novata, Persefoni, Watershed | 🔴 Missing |
| Blended finance modeling | Medium | None (gap) | 🔴 Stub only |
| Exit impact assessment | Medium | None (gap) | 🔴 Missing |
| Multi-language report generation | Medium | Sopact (6 langs) | 🟡 Basic (6 langs) |

### Competitive Positioning

**Impact Vision's differentiators vs. paid platforms:**
1. **Open source** — no vendor lock-in, $0 license cost, community-driven
2. **AI-native** — LLM-first architecture; pitch deck → full assessment in one tool call
3. **Framework breadth** — 10 ESG frameworks + IRIS+ + SDGs in one tool (vs. Novata's ESG-only or Sopact's IMM-only)
4. **Greenwashing detection** — no paid platform offers systematic NLP + regulatory greenwashing scoring
5. **Agent-first** — MCP server, works inside Claude/Cursor/any AI agent natively

**Where paid platforms lead (our gaps to close):**
1. Investee data collection workflows & portal (Novata's core value)
2. Carbon accounting engine with Scope 1-2-3 (Persefoni, Watershed)
3. Benchmarking with real peer data (Novata 14K+ companies)
4. Enterprise SSO, SOC2, audit trail (Novata, Workiva)
5. Dedicated LP portal with self-serve dashboards (Novata, Allvue)

### 2026-04-25 Tool Review Findings

All 26 impact tools were reviewed and smoke-tested through their Python tool interfaces. The second pass also covered MCP/API wrappers because several higher-risk bugs were integration issues where wrapper field names had drifted from the current Pydantic input models.

| Area | Severity | Status | Notes |
|------|----------|--------|-------|
| MCP/API wrapper field drift | High | ✅ Fixed | `pipeline`, `monitoring`, `narrative`, `beneficiary_feedback`, `dd_checklist`, `cross_reference`, `document_analysis`, `portfolio_analyze`, `trend_analysis`, and `product_passport` now pass current input fields instead of silently ignored legacy names. |
| Framework OPIM handler drift | High | ✅ Fixed | `framework_assess` now uses the current OPIM framework API and no longer imports removed helper names. |
| Pitch deck text intake | High | ✅ Fixed | `pitch_deck_analyze` now supports raw `text` and `url` inputs in addition to `file_path`, matching MCP/API wrapper contracts. |
| Product Passport JSON handling | High | ✅ Fixed | Valid JSON arrays/scalars now return clear validation errors instead of crashing on `.get()`. MCP now maps `product_data` into `dpp_data`. |
| Monitoring deviation alerts | Medium | ✅ Fixed | Metric IDs and thresholds are normalized, and prior values like `100 tCO2e` are parsed for alert comparisons. |
| Document analysis metric extraction | Medium | ✅ Fixed | Metric IDs are now extracted case-insensitively and normalized to uppercase. |
| Beneficiary feedback zero values | Medium | ✅ Fixed | Valid zero values such as NPS `0` are preserved instead of displayed as `N/A`. |
| Advisor/narrative SDG handling | Medium | ✅ Fixed | SDG claim normalization and theme inference now execute without tuple/list misuse. |
| Registry coverage | High | ✅ Fixed | All 26 impact tools are registered and exported in the default registry and impact package. |

---

## Roadmap Phases

### Phase 11: Data Quality & Reliability Foundation 🔧
**Timeline:** Q2 2026 (Current)  
**Theme:** _"Trust the numbers before you scale them"_

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 11.1 | ✅ Fix: suggested metrics counted as reported evidence (C1) | Critical | Done |
| 11.2 | ✅ Fix: contribution_duration ignored in 5D scoring (C2) | Critical | Done |
| 11.3 | ✅ Fix: report key mismatches — SDG/coverage data lost (C3) | Critical | Done |
| 11.4 | ✅ Fix: greenwashing gap zeroed by unrelated metrics (C4) | Critical | Done |
| 11.5 | ✅ Fix: inconsistent sector taxonomy across tools (I1) | Important | Done |
| 11.6 | ✅ Fix: report tool missing input normalization (I2) | Important | Done |
| 11.7 | ✅ Fix: silent warning drops in all tools (I13) | Important | Done |
| 11.8 | ✅ Fix: model validation gaps — metric IDs, NPS, satisfaction (I15) | Important | Done |
| 11.9 | ✅ Fix: portfolio median, JSON support, CSV normalization (I9-I11) | Important | Done |
| 11.10 | ✅ Fix: greenwashing selectivity uses ID prefixes (I12) | Important | Done |
| 11.11 | ✅ Fix: empty catalog silent failure (I14) | Important | Done |
| 11.12 | ✅ Fix: SDG loop optimization, claim confidence calibration (M2-M3) | Minor | Done |
| 11.13 | ✅ Add snapshot regression tests for `_to_html()` and `_to_text()` report outputs | Important | Done |
| 11.14 | ✅ Add `impact_targets` and `metric_history` to `ImpactReportInput` to enable `target_progress` report type (I4) | Important | Done |
| 11.15 | ✅ Wire impact claims data through to report renderer end-to-end | Important | Done |
| 11.16 | ✅ Register and export all 26 impact tools in default registry and impact package | Critical | Done |
| 11.17 | ✅ Fix MCP/API wrapper field drift for pipeline, monitoring, narrative, DD checklist, cross-reference, beneficiary feedback, document analysis, and Product Passport | Critical | Done |
| 11.18 | ✅ Fix Product Passport MCP data mapping and reject non-object JSON inputs safely | Critical | Done |
| 11.19 | ✅ Fix document analysis metric ID extraction to handle lowercase/mixed-case IRIS+ IDs | Important | Done |
| 11.20 | ✅ Fix monitoring alerts to normalize metric IDs and parse prior values with units | Important | Done |
| 11.21 | ✅ Fix beneficiary feedback import/display so NPS `0` is not treated as missing | Important | Done |
| 11.22 | ✅ Add regression tests for 26-tool registry plus high/medium wrapper and normalization fixes | Important | Done |
| 11.23 | ✅ Fix OPIM framework handler, pitch deck raw-text intake, and MCP aliases for portfolio/trend analysis | Critical | Done |

---

### Phase 12: Investee Data Collection & LP Portal 🏢
**Timeline:** Q3 2026  
**Theme:** _"Close the Novata gap — let investees self-report"_

This is the #1 feature gap vs. paid platforms. Novata's entire value proposition is structured data collection from portfolio companies.

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 12.1 | Investee questionnaire engine — dynamic forms from metric definitions with guidance, validation, and units | Critical | L |
| 12.2 | Multi-period data collection — track which metrics have been collected per period, highlight missing | Critical | M |
| 12.3 | Email/link-based collection — generate unique collection links for investee contacts (no auth required for basic) | High | M |
| 12.4 | Data review & approval workflow — analyst reviews investee submissions, flags anomalies, approves for scoring | High | L |
| 12.5 | LP self-serve portal — authenticated dashboard where LPs view portfolio reports, download XLSX/PDF, filter by fund/vintage | High | L |
| 12.6 | Investee onboarding templates — pre-built questionnaire templates by sector (fintech, healthcare, agriculture, energy, education) | Medium | M |
| 12.7 | Bulk import from existing systems — CSV/Excel/JSON upload with intelligent column mapping and deduplication | Medium | S |

---

### Phase 13: Carbon Accounting & Climate Intelligence 🌍
**Timeline:** Q3–Q4 2026  
**Theme:** _"Carbon is table stakes — every LP asks for it"_

Scope 1-2-3 accounting is now a baseline expectation. Novata, Persefoni, and Watershed all lead here. We need at minimum Scope 1+2 with proxy-based Scope 3 estimates.

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 13.1 | GHG Protocol calculator — Scope 1 (direct) and Scope 2 (location/market-based) from activity data | Critical | L |
| 13.2 | Scope 3 estimation engine — proxy-based estimates using PCAF methodology for financial institutions, sector emission factors for others | High | L |
| 13.3 | Emission factor database — bundled EPA/DEFRA/IEA factors with annual update mechanism | High | M |
| 13.4 | Carbon intensity metrics — tCO2e/revenue, tCO2e/employee, tCO2e/unit for portfolio benchmarking | High | M |
| 13.5 | Science-based target alignment — check portfolio trajectory against SBTi 1.5°C pathway | Medium | M |
| 13.6 | PCAF scoring — assign data quality scores (1-5) per financed emission, aggregate at portfolio level | Medium | M |
| 13.7 | Climate scenario analysis — NGFS scenario integration for transition and physical risk (complement existing TCFD framework) | Medium | L |
| 13.8 | Portfolio carbon footprint report — Scope 1+2+3 waterfall chart, hotspot analysis, year-over-year trend | High | M |

---

### Phase 14: Causal Impact & Counterfactual Analysis 🔬
**Timeline:** Q4 2026  
**Theme:** _"Move from correlation to causation — what the market can't do yet"_

This is the #1 gap across ALL platforms. No paid tool offers systematic counterfactual analysis. GIIN 2026 trends explicitly call for this. Wellington Management emphasizes KPI benchmarking and feedback loops. This is Impact Vision's blue ocean opportunity.

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 14.1 | Counterfactual framework engine — for each company, generate structured counterfactual questions and assessment rubric | Critical | L |
| 14.2 | Difference-in-differences calculator — pre/post intervention with control group proxy data from sector benchmarks | High | L |
| 14.3 | SROI calculator — monetize social outcomes using standardized proxy values (HACT/NEF social value bank) | High | M |
| 14.4 | Contribution analysis workflow — structured IMP/Impact Frontiers contribution assessment with evidence grading | High | M |
| 14.5 | Spillover & displacement detection — identify potential negative spillovers and displacement effects across portfolio | Medium | M |
| 14.6 | Bayesian impact estimation — combine prior sector data with company-specific evidence for credible interval estimates | Medium | L |
| 14.7 | Natural experiment detection — flag portfolio companies in contexts where quasi-experimental evaluation is feasible | Low | M |

---

### Phase 15: Advanced LP Reporting & Fund Analytics 📊
**Timeline:** Q1 2027  
**Theme:** _"Reports that make LPs re-up"_

LP reporting is where fund managers spend the most time and where quality matters most. Novata and Sopact charge premium prices for this. Impact Vision needs to match and exceed with AI-generated narratives.

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 15.1 | ILPA-compliant fund report template — standardized sections (strategy, portfolio, performance, impact, ESG) | Critical | L |
| 15.2 | GIIN IRIS+ Aligned Fund Report — auto-fill from portfolio data with framework-specific sections | High | M |
| 15.3 | EDCI export automation — auto-populate all 17 EDCI metrics from collected data + proxy estimates | High | M |
| 15.4 | Quarterly impact newsletter generator — LLM-drafted narrative with key metrics, portfolio highlights, case studies | High | M |
| 15.5 | Impact-weighted returns analysis — overlay impact scores on financial IRR/MOIC, compute impact-adjusted performance | Medium | L |
| 15.6 | Vintage year comparison — compare fund impact performance across vintages with normalized metrics | Medium | M |
| 15.7 | Peer fund benchmarking — anonymized comparison against GIIN survey medians and sector benchmarks | Medium | M |
| 15.8 | Exit impact assessment — structured framework for measuring sustained impact post-exit (IFC OPIM Principle 7) | Medium | L |

---

### Phase 16: Stakeholder Voice & Beneficiary Intelligence 🗣️
**Timeline:** Q1–Q2 2027  
**Theme:** _"Impact that's verified by the people it claims to serve"_

60 Decibels and Sopact lead here. GIIN 2026 emphasizes that outcomes-focused IMM requires beneficiary data. This moves Impact Vision from "desk-based assessment" to "ground-truth verified."

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 16.1 | Survey builder — structured beneficiary survey templates (Lean Data inspired) with multi-language support | High | L |
| 16.2 | Satisfaction & NPS tracking — automated scoring with demographic disaggregation (gender, age, income) | High | M |
| 16.3 | Qualitative theme extraction — LLM-powered theme coding from open-ended responses (replaces manual coding) | High | M |
| 16.4 | Voice-to-insight pipeline — audio/transcript intake → sentiment analysis → theme extraction → report section | Medium | L |
| 16.5 | Worker voice integration — employee feedback, working conditions, wage equity tracking (aligned with ESRS S1) | Medium | M |
| 16.6 | Community feedback dashboard — aggregate beneficiary insights across portfolio with trend detection | Medium | M |
| 16.7 | Beneficiary consent & data governance — GDPR/PDPA-compliant consent management for survey data | Medium | M |

---

### Phase 17: Deal Pipeline Intelligence 🎯
**Timeline:** Q2 2027  
**Theme:** _"From assessment tool to investment workflow engine"_

Move beyond single-company assessment into the full deal lifecycle. This is where Allvue FPPM and Dialllog operate. Impact Vision can differentiate by deeply integrating impact scoring at every stage.

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 17.1 | IC memo generator — auto-generate investment committee memo from DD findings, 5D score, SDG alignment, risk assessment | Critical | L |
| 17.2 | Deal scoring model — configurable scoring rubric combining financial (if provided), impact, ESG, and risk dimensions | High | L |
| 17.3 | Deal gate criteria — automated pass/fail at each pipeline stage with configurable thresholds per fund thesis | High | M |
| 17.4 | Fund thesis alignment checker — score each deal against the fund's stated impact thesis, SDG targets, and geography focus | High | M |
| 17.5 | Comparable deal finder — surface similar past deals from the fund's history for precedent analysis | Medium | M |
| 17.6 | CRM integration layer — sync pipeline data with Salesforce, HubSpot, or custom CRM via webhooks | Medium | L |
| 17.7 | Deal room document management — organize DD documents per company with auto-linking to claims and metrics | Medium | L |

---

### Phase 18: Regulatory Compliance Automation 📜
**Timeline:** Q2–Q3 2027  
**Theme:** _"Compliance without consultants"_

SFDR reform, CSRD implementation, and ISSB adoption are creating massive compliance burden. Novata and Workiva charge premium for this. Impact Vision can offer the same with AI automation.

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 18.1 | SFDR PAI auto-fill — automatically populate all 14+9 PAI indicators from collected data + proxies | Critical | L |
| 18.2 | CSRD/ESRS report generator — produce disclosure-ready ESRS outputs from double materiality assessment | Critical | L |
| 18.3 | EU Taxonomy alignment checker — classify activities against EU Taxonomy technical screening criteria | High | L |
| 18.4 | SFDR Article 8/9 product categorization — assess fund's Article 6/8/9 classification with evidence | High | M |
| 18.5 | California SB 253/261 climate disclosure — automated GHG and climate risk disclosure preparation | Medium | M |
| 18.6 | Regulatory change tracker — monitor SFDR/CSRD/ISSB regulatory updates and flag impacts on current assessments | Medium | M |
| 18.7 | Audit trail & assurance readiness — structured evidence packs with data lineage for third-party verification | High | L |

---

### Phase 19: Enterprise & Scale 🏗️
**Timeline:** Q3–Q4 2027  
**Theme:** _"Ready for institutional adoption"_

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 19.1 | Multi-tenant architecture — fund-level data isolation with configurable access controls | Critical | XL |
| 19.2 | SSO integration — SAML/OIDC authentication for enterprise deployment | High | L |
| 19.3 | Role-based access control — analyst/partner/LP/admin roles with granular permissions | High | L |
| 19.4 | SOC2 compliance readiness — audit logging, data encryption at rest, access monitoring | High | XL |
| 19.5 | Bulk assessment API — process 100+ companies in parallel with job queue and progress tracking | High | L |
| 19.6 | Real-time collaboration — multi-user concurrent assessment with conflict resolution | Medium | L |
| 19.7 | White-label deployment — customizable branding, domain, and report templates per fund | Medium | M |
| 19.8 | Package rename — `openharness` → `impact_vision` namespace (deferred from CLAUDE.md engineering housekeeping) | Low | M |

---

### Phase 20: AI Intelligence Layer 2.0 🤖
**Timeline:** Q4 2027+  
**Theme:** _"From reactive assessment to proactive intelligence"_

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 20.1 | Predictive impact scoring — ML model trained on historical assessments to predict likely 5D scores from minimal input | High | XL |
| 20.2 | Impact anomaly detection — auto-flag companies with impact metrics that deviate significantly from sector norms | High | L |
| 20.3 | Natural language querying — "Which portfolio companies have declining gender metrics?" → structured answer | High | L |
| 20.4 | Auto-generated case studies — LLM drafts 2-page impact case study per company for LP comms | Medium | M |
| 20.5 | Satellite/geospatial impact verification — integrate satellite imagery for land-use, deforestation, infrastructure verification | Medium | XL |
| 20.6 | Impact knowledge graph — connected graph of companies, metrics, SDGs, claims, evidence for graph-based reasoning | Medium | XL |
| 20.7 | ClimateBERT integration — model-based greenwashing detection using fine-tuned NLP models | Medium | L |
| 20.8 | Market intelligence feed — scrape news, regulatory updates, peer reports to surface relevant impact signals | Low | L |

---

## Summary

| Phase | Timeline | Items | Theme |
|-------|----------|-------|-------|
| **11: Data Quality** 🔧 | Q2 2026 | 23 | Trust the numbers |
| **12: Investee Portal** 🏢 | Q3 2026 | 7 | Close the Novata gap |
| **13: Carbon Accounting** 🌍 | Q3–Q4 2026 | 8 | Carbon is table stakes |
| **14: Causal Impact** 🔬 | Q4 2026 | 7 | Blue ocean — no competitor does this |
| **15: LP Reporting** 📊 | Q1 2027 | 8 | Reports that make LPs re-up |
| **16: Stakeholder Voice** 🗣️ | Q1–Q2 2027 | 7 | Ground-truth verification |
| **17: Deal Pipeline** 🎯 | Q2 2027 | 7 | Full investment workflow |
| **18: Regulatory** 📜 | Q2–Q3 2027 | 7 | Compliance without consultants |
| **19: Enterprise** 🏗️ | Q3–Q4 2027 | 8 | Institutional adoption |
| **20: AI 2.0** 🤖 | Q4 2027+ | 8 | Proactive intelligence |
| **Total** | | **90** | |

---

## Key Bets

1. **Causal impact analysis (Phase 14) is our moat.** No paid platform offers this. It's what separates "reporting" from "proving impact works." If we nail counterfactual + SROI + contribution analysis, we become the tool serious impact funds recommend to each other.

2. **Investee data collection (Phase 12) is our biggest gap.** Until we solve self-service data collection, we're a desk-assessment tool. Novata's 14K+ reporting companies prove this is what GPs will pay for.

3. **Carbon accounting (Phase 13) is non-negotiable.** Every LP DDQ asks for it. Every regulatory framework requires it. We don't need to be Persefoni — we need Scope 1+2 with proxy Scope 3.

4. **AI-generated LP reports (Phase 15) are our speed advantage.** Sopact claims "months to minutes." We can do "minutes to seconds" with structured data + LLM narratives.

---

_Last updated: 2026-04-28. Phases 1-11 complete; 26 impact tools reviewed, high/medium wrapper bugs addressed, and report renderer regressions covered._
