# Impact Vision — Product Roadmap v3.0

**Date:** 2026-04-28  
**Status:** Evidence-Driven & Governance-First Strategic Plan  
**Audience:** Technical leads, product managers, fund operators  
**Thesis:** Impact Vision's competitive moat is **trust infrastructure**—not dashboards. Build audit-ready, evidence-governed, AI-assisted assessment that the 90% of impact data without verification can rely on.

---

## Strategic Context: Sopact & Novata Competitive Analysis (April 2026)

### Sopact's Positioning Shift

**What Sopact Owns:**
- **Persistent stakeholder identity engine** — every response (survey, application, interview, document) links back to one record across the lifecycle
- **Document intelligence at scale** — reads 50–200 DD documents per investee, extracts risk flags, codes qualitative responses without manual coding
- **AI-native qualitative analysis** — four-layer system (Intelligent Cell, Row, Column, Grid) that processes open-ended responses, sentiment, and cross-record patterns in real-time
- **Stakeholder Intelligence as a category** — moved beyond "measurement tools" to "decision-useful intelligence" with continuous updates (vs. quarterly snapshots)
- **Enterprise-grade multi-program support** — single platform handles surveys, applications, grant intake, portfolio tracking, and alumni follow-up

**Sopact's Gaps (Opportunities for Impact Vision):**
1. **No evidence governance layer** — Sopact excels at collecting and analyzing data but does NOT provide audit trails, version control, or assurance-ready evidence packs
2. **Missing causal/counterfactual logic** — no contribution analysis, no SROI, no difference-in-differences (despite being the #1 gap in impact investing)
3. **Limited framework coverage** — strong for qualitative analysis, weak for IRIS+, carbon accounting, SFDR/CSRD compliance automation
4. **No investee data collection workflows** — Sopact handles *funder* data collection but not structured portfolio company self-reporting portals
5. **Carbon and regulatory compliance are bolt-ons** — not core capabilities (Novata's domain)

### Novata's Positioning

**What Novata Owns:**
- **ESG data collection platform for private markets** — 4,000+ metrics aligned to EDCI, SFDR, TCFD, ISSB, Invest Europe, GRI
- **Carbon Navigator** — Scope 1+2+3 calculations, PCAF financed-emissions workflow, audit trails
- **Comprehensive framework library** — Novata supports 10+ frameworks with built-in definitions, calculators, guardrails
- **Benchmarking and proxy data** — real peer data from 14K+ companies enables comparison and gap flagging
- **Risk Intelligence** — ESG due-diligence risk scoring, climate risk disclosures, regulatory compliance readiness
- **Enterprise controls** — admin/analyst/LP roles, version control, data governance

**Novata's Gaps (Opportunities for Impact Vision):**
1. **No persistent stakeholder record** — treats each quarter/cycle as separate; no lifecycle continuity like Sopact's
2. **Weak qualitative analysis** — no document intelligence, no theme extraction, no sentiment tracking (this is Sopact's superpower)
3. **No counterfactual or causal logic** — IRIS+ metrics only; no contribution analysis, no impact attribution (same gap as Sopact)
4. **Limited beneficiary voice integration** — no built-in Lean Data survey templates, no multi-language LLM-powered analysis
5. **Siloed reporting workflows** — strong for compliance packs but weak for narrative LP reporting with stakeholder insights
6. **No assurance-ready evidence manifests** — carbon audit trail exists but broader evidence graph does not

### Market Gaps Identified in v3 Research

| Gap | Severity | Sopact | Novata | Impact Vision Opportunity |
|---|---|---|---|---|
| **Evidence governance & audit trails** | Critical | ❌ Missing | ✅ Partial (carbon only) | **Moat opportunity** — build full evidence graph with immutable manifests |
| **Counterfactual & causal analysis** | Critical | ❌ Missing | ❌ Missing | **Blue ocean** — no competitor offers this; paired with evidence governance, this is the moat |
| **Persistent stakeholder identity + compliance data** | High | ✅ Sopact | ✅ Novata (separate) | **Integration** — combine Sopact's identity model with Novata's frameworks |
| **Beneficiary/stakeholder voice as evidence** | High | ✅ Sopact (partial) | ❌ Missing | **Strengthen** — 60 Decibels integrations + Lean Data templates + LLM analysis |
| **Investee self-service data collection** | High | ❌ Missing | ✅ Novata (core) | **Differentiate** — add evidence governance + guidance cards + anomaly detection |
| **AI governance & output reviewability** | High | ⚠️ Emerging | ❌ Missing | **Moat** — every AI extraction = confidence + prompt version + human reviewer state |
| **Exit impact & sustainability post-exit** | Medium | ❌ Missing | ❌ Missing | **Adjacent** — combine causal logic + stakeholder follow-up + OPIM Principle 7 |
| **Multi-framework interoperability** | High | ❌ Missing | ✅ Strong | **Match** — implement Novata's breadth with Impact Vision's evidence layer |

---

## V3 North Star

**Impact Vision should become the system of record for evidence-governed impact assessment in private markets.**

**Three strategic moves:**
1. **Build the evidence backbone that neither Sopact nor Novata provides** — claims → metrics → sources → approvals → audit trail
2. **Own the causal impact space** — counterfactual, SROI, contribution analysis integrated with evidence governance
3. **Connect stakeholder voice to evidence** — beneficiary feedback is not just "intelligence" (Sopact) but verified evidence for impact claims (evidence governance + voice)

---

## V3 Strategic Tracks (Q2 2026 – Q2 2027)

### Track 1: Evidence Graph & Audit-Ready Assurance
**Timeline:** Q2 2026 (Foundation)  
**Goal:** Make every impact claim traceable, reviewable, and verifiable.

| # | Item | Priority | Effort |
|---|---|---|---|
| 1.1 | Canonical metric record model: metric ID, value, unit, period, source, owner, quality score, verification status | Critical | M |
| 1.2 | Evidence graph: claim → metric → source document → reviewer decision → report section | Critical | L |
| 1.3 | Data-quality scoring rubric covering completeness, recency, consistency, source type, and verification level (PCAF bands 1-5) | Critical | M |
| 1.4 | Versioned standards registry for IRIS+, EDCI, ISSB, ESRS, GHG Protocol, PCAF, SFDR, and OPIM | High | M |
| 1.5 | Audit-log events for metric creation, edits, imports, approvals, and report publication | High | M |
| 1.6 | Golden regression fixtures for representative company, fund, and portfolio reports | High | S |
| 1.7 | Immutable report manifest with content-addressable hashes for source documents and data exports | Critical | M |
| 1.8 | AI extraction review gates: approve, reject, edit, or request evidence for every LLM-derived claim | Critical | M |

**Key Differentiator:** This is where Impact Vision owns the competitive moat. Neither Sopact nor Novata provides immutable evidence lineage + AI governance together.

---

### Track 2: Investee Data Collection Portal
**Timeline:** Q2–Q3 2026  
**Goal:** Close the Novata gap with structured, guidance-rich self-service data collection.

| # | Item | Priority | Effort |
|---|---|---|---|
| 2.1 | Dynamic questionnaire generator from selected IRIS+/EDCI metrics, sector templates, and period | Critical | L |
| 2.2 | Public secure collection links with expiry, submission tokens, and no-auth basic workflow | Critical | M |
| 2.3 | Investee guidance cards: definition, unit, examples, acceptable evidence, common mistakes | Critical | M |
| 2.4 | Multi-period collection tracker with missing, stale, submitted, reviewed, and approved states | High | M |
| 2.5 | Analyst review queue with statistical anomaly flags (vs. portfolio peer data), comments, resubmission requests | High | L |
| 2.6 | Sector onboarding templates for energy, financial inclusion, healthcare, agriculture, education, circular economy | Medium | M |
| 2.7 | CSV/XLSX bulk import with intelligent column mapping, duplicate detection, validation preview | Medium | M |
| 2.8 | AI normalization layer: map investee-provided text to canonical metric IDs with confidence scoring | High | L |

**Differentiation:** Combine Novata's framework coverage with Sopact's persistent identity model + Impact Vision's evidence governance.

---

### Track 3: Carbon & Climate Accounting Core
**Timeline:** Q3 2026  
**Goal:** Credible Scope 1+2+proxy Scope 3, financed emissions, and data-quality scoring without replacing Persefoni.

| # | Item | Priority | Effort |
|---|---|---|---|
| 3.1 | Scope 1 and Scope 2 calculator with activity-data inputs, emission factors, units, factor versioning | Critical | L |
| 3.2 | Proxy Scope 3 estimates by sector and spend/revenue/activity where direct data is missing | Critical | L |
| 3.3 | PCAF financed-emissions workflow with attribution factor, data-quality score (bands 1-5), portfolio rollup | Critical | L |
| 3.4 | Emission-factor catalog loader with EPA/DEFRA/IEA metadata and update provenance | High | M |
| 3.5 | Carbon intensity metrics: tCO2e/revenue, tCO2e/employee, tCO2e/unit, ownership-adjusted footprint | High | M |
| 3.6 | Climate data-quality dashboard showing actual vs. estimated coverage by scope and company | High | M |
| 3.7 | Evidence lineage for every carbon calculation: source emission factor, activity data source, uncertainty bounds | Critical | M |
| 3.8 | Scope 3 emission factor sensitivity analysis — flag calculations where 20%+ data gaps exist | High | S |

**Differentiation:** Novata's Carbon Navigator is strong. Impact Vision's advantage: evidence governance (proof of calculation, audit trail, factor versioning) + causal impact (what portfolio changes reduce Scope 3).

---

### Track 4: Stakeholder Voice & Beneficiary Intelligence
**Timeline:** Q3 2026  
**Goal:** Integrate beneficiary feedback as verified evidence, not just "intelligence."

| # | Item | Priority | Effort |
|---|---|---|---|
| 4.1 | Lean Data survey builder: 15-min standardized templates (60 Decibels model) with multi-language support | High | M |
| 4.2 | Beneficiary satisfaction tracking: NPS, likelihood-to-recommend, and demographic disaggregation | High | M |
| 4.3 | Qualitative theme extraction: LLM-powered coding of open-ended responses + sentiment analysis | High | M |
| 4.4 | Beneficiary feedback as evidence: link survey responses back to impact claims in the evidence graph | Critical | M |
| 4.5 | Worker voice integration: employee satisfaction, wage equity tracking, working conditions (ESRS S1 aligned) | Medium | M |
| 4.6 | Community feedback dashboard with trend detection by geography, demographic, and time period | Medium | M |
| 4.7 | GDPR/PDPA-compliant consent management for survey data collection and storage | Medium | M |
| 4.8 | Beneficiary feedback quality score: completion rate, response depth, time-on-survey, demographic coverage | High | S |

**Differentiation:** Sopact owns qualitative analysis; Impact Vision owns linking that feedback to evidence governance. "Beneficiary voice is verified evidence, not just insight."

---

### Track 5: Causal Impact & Outcome Attribution
**Timeline:** Q4 2026  
**Goal:** Differentiate by helping funds understand whether outcomes are attributable. This is the #1 gap across all platforms.

| # | Item | Priority | Effort |
|---|---|---|---|
| 5.1 | Contribution analysis workflow: structured IMP / Impact Frontiers logic with evidence-strength ladder | Critical | L |
| 5.2 | Counterfactual framework engine: generate structured counterfactual questions per company/business model | Critical | L |
| 5.3 | Evidence-strength grading (NESTA 1-5 levels): from opinion to RCT; paired with evidence graph | Critical | M |
| 5.4 | SROI calculator with sensitivity ranges and value-bank source tracking (HACT, NEF, AAVS) | High | L |
| 5.5 | Difference-in-differences calculator for pre/post with control group proxy data from sector benchmarks | Medium | L |
| 5.6 | Exit impact assessment framework: sustained impact post-exit (OPIM Principle 7) | Medium | M |
| 5.7 | Impact learning loop: hypothesis → metric → result → management action → follow-up, all versioned and audited | High | M |
| 5.8 | Spillover & displacement detection: identify potential negative spillovers across portfolio | Medium | M |

**Differentiation:** No paid platform offers this. Sopact and Novata are "reporting tools." Impact Vision becomes "impact verification platform."

---

### Track 6: Standards Interoperability & Disclosure Packs
**Timeline:** Q3–Q4 2026  
**Goal:** Turn fragmented frameworks into versioned, governed rule sets.

| # | Item | Priority | Effort |
|---|---|---|---|
| 6.1 | EDCI export validator and completeness dashboard (reported vs. proxy vs. missing) | Critical | M |
| 6.2 | ISSB S1/S2 disclosure pack with source-linked answers and climate metric dependencies | Critical | L |
| 6.3 | ESRS/CSRD pack with versioning for waves + simplified ESRS for smaller entities | High | L |
| 6.4 | SFDR PAI autofill with direct, proxy, missing, and not-applicable classifications + evidence links | High | L |
| 6.5 | Framework crosswalk explorer: IRIS+ ↔ EDCI ↔ ISSB ↔ ESRS ↔ PCAF ↔ GRI | High | M |
| 6.6 | Jurisdiction profile selector: EU, UK, Singapore, Japan, Australia, Canada, US/state climate reporting | Medium | M |
| 6.7 | Rule-pack versioning and test harness — standards changes can be applied without breaking old reports | Critical | M |
| 6.8 | Regulatory change tracker: monitor SFDR, CSRD, ISSB updates and flag portfolio impact | Medium | M |

**Differentiation:** Match Novata's breadth; add Impact Vision's versioning and governance.

---

### Track 7: LP Reporting & Institutional Portal
**Timeline:** Q4 2026  
**Goal:** Make Impact Vision useful for quarterly LP workflows.

| # | Item | Priority | Effort |
|---|---|---|---|
| 7.1 | Fund-level LP dashboard: portfolio coverage, impact score distribution, top SDGs, carbon footprint, data-quality warnings | Critical | L |
| 7.2 | ILPA-aligned impact appendix + EDCI attachment for quarterly reporting | Critical | M |
| 7.3 | LP export bundle: PDF/HTML, XLSX, JSON, source index, and evidence manifest | High | L |
| 7.4 | Fund/vintage/sector/geography self-serve filters for LP dashboard | High | M |
| 7.5 | LP question-answer workspace with citations back to approved evidence | Medium | L |
| 7.6 | Report publication workflow: draft → reviewer approved → published → superseded states | High | M |
| 7.7 | White-label branding by fund (logo, color, disclaimer, contact metadata) | Medium | S |
| 7.8 | AI-generated LP narrative: highlight portfolio impact, risk mitigation, and comparative benchmarks (vs. GIIN medians) | High | M |

**Differentiation:** Sopact's continuous intelligence + Impact Vision's evidence governance = LP reports that survive audit.

---

### Track 8: Assurance, Verification & Controls
**Timeline:** Q1 2027  
**Goal:** Make third-party verification and internal control review practical.

| # | Item | Priority | Effort |
|---|---|---|---|
| 8.1 | Assurance pack builder: metric sample selection, evidence files, reviewer notes, management assertions | Critical | L |
| 8.2 | Verification provider workspace: read-only evidence access, comment resolution, audit trail | High | L |
| 8.3 | Control checks: segregation of duties, late edits, unreviewed AI outputs, unsupported claims | Critical | M |
| 8.4 | Exception register: unresolved gaps, management overrides, known limitations | Medium | M |
| 8.5 | Proof of review: every assertion linked to reviewer identity, timestamp, confidence level | Critical | S |
| 8.6 | Third-party verification API: verification providers can request evidence bundles, submit findings | High | M |

**Differentiation:** Enable assurance **at the infrastructure level**, not just in reporting.

---

### Track 9: AI Governance & Market Intelligence
**Timeline:** Q1–Q2 2027  
**Goal:** Use AI to reduce analyst workload while preserving explainability.

| # | Item | Priority | Effort |
|---|---|---|---|
| 9.1 | AI metric harmonizer: map messy investee uploads to canonical records with confidence and rationale | Critical | L |
| 9.2 | Natural-language portfolio query engine constrained to approved data and source citations | High | L |
| 9.3 | Greenwashing reviewer: claim specificity, evidence gap, selectivity, adverse-impact omission explanations | High | M |
| 9.4 | AI output governance: prompt version log, source grounding, human reviewer, confidence threshold policy | Critical | M |
| 9.5 | Peer benchmark assistant using GIIN snapshots and internal anonymized portfolio data | Medium | L |
| 9.6 | Regulatory-change monitor: flags affected rule packs, report templates, and portfolio companies | Medium | L |

**Differentiation:** "AI with controls" — every LLM output is reviewable and traceable.

---

## Execution Roadmap

### Q2 2026: Foundation (Track 1 + Track 2 Start)
- Canonical metric record + evidence graph MVP
- Audit logging and immutable manifests
- Investee questionnaire generator + sector templates
- Integration testing with v1 tools

### Q3 2026: Data Collection + Intelligence (Track 2 Complete + Track 3 + Track 4 Start)
- Complete investee portal + multi-period tracking
- Scope 1+2 calculator + PCAF financed emissions
- Lean Data surveys + beneficiary feedback collection
- Standards versioning (EDCI, ISSB, ESRS)

### Q4 2026: Causal Impact + Compliance (Track 4 Complete + Track 5 Start + Track 6 Complete)
- Contribution analysis + counterfactual framework
- SFDR/CSRD/EDCI compliance packs
- Evidence-strength grading system
- LP reporting beta

### Q1 2027: Assurance-Ready (Track 5 Continue + Track 7 + Track 8 Start)
- SROI calculator + exit impact assessment
- Assurance pack builder + verification API
- LP portal MVP + white-label support
- Regulatory change tracker

### Q2 2027: Intelligence Layer (Track 8 Complete + Track 9)
- AI metric harmonizer + governance controls
- Greenwashing reviewer
- Natural-language query engine
- Enterprise multi-tenant architecture

---

## Success Metrics

| Metric | Target | Validation |
|---|---|---|
| **Investee completion time** | < 30 min for quarterly submission | UX testing with 5+ portfolio companies |
| **Metric data coverage** | 95%+ of reported metrics have unit, period, source, owner, quality score | Audit of 100+ random metrics across reports |
| **AI extraction reviewability** | 100% of AI-derived claims have confidence, rationale, reviewer state | Regression tests for all 26 tools + new AI outputs |
| **Evidence graph completeness** | Every fund report links claims → metrics → sources → reviews → approval | Template report validation |
| **Carbon coverage** | Scope 1+2 available for 90%+ of active portfolio companies | Portfolio dashboard coverage report |
| **Causal attribution coverage** | 80%+ of companies have counterfactual assessment + evidence grading | Spot checks during LP reporting cycles |
| **Assurance readiness** | Every published LP report includes immutable manifest + evidence index | Third-party auditor feedback |
| **LP satisfaction** | < 5% follow-up questions after report delivery | LP survey post-publication |

---

## Competitive Positioning Summary

| Dimension | Sopact | Novata | Impact Vision (v3) |
|---|---|---|---|
| **Persistent stakeholder identity** | ✅ Superpower | ❌ Missing | ✅ Adopted + extended |
| **Qualitative analysis & AI** | ✅ Superpower | ❌ Weak | ✅ Integrated with evidence |
| **ESG framework breadth** | ❌ Weak | ✅ 4,000+ metrics | ✅ Full coverage |
| **Carbon accounting** | ❌ Bolt-on | ✅ Carbon Navigator | ✅ Evidence-governed |
| **Causal/counterfactual** | ❌ Missing | ❌ Missing | ✅ **Moat** |
| **Evidence governance** | ❌ Missing | ⚠️ Partial (carbon) | ✅ **Moat** |
| **AI governance + reviewability** | ⚠️ Emerging | ❌ Missing | ✅ **Moat** |
| **Investee data collection** | ❌ Missing | ✅ Core | ✅ With evidence governance |
| **Beneficiary voice as evidence** | ✅ Voice data | ❌ Missing | ✅ Verified evidence link |
| **Assurance-ready reports** | ❌ Missing | ⚠️ Carbon audit trail | ✅ **Full system** |

---

## What v3 Replaces & Extends From v1–v2

- **v1 Phase 12 (Investee Portal)** → **Track 2**: Add evidence governance + AI harmonization
- **v1 Phase 13 (Carbon)** → **Track 3**: Add evidence lineage + PCAF integration
- **v1 Phase 14 (Causal Impact)** → **Track 5**: Full realization with contribution analysis + SROI
- **v1 Phase 15 (LP Reporting)** → **Track 7**: Add evidence manifests + AI narratives
- **v1 Phase 16 (Stakeholder Voice)** → **Track 4**: Connect voice to evidence governance
- **v1 Phase 18 (Regulatory)** → **Track 6**: Versioned rule packs + jurisdiction profiles
- **v2 all tracks** → **v3 reorganized**: Foundation-first (evidence) + parallel workstreams (collection, intelligence, assurance)

---

## Key Bets

1. **Evidence governance is the moat.** Neither Sopact nor Novata provides immutable audit trails + AI governance + stakeholder voice integration. Impact Vision owns this.

2. **Causal impact is the differentiator.** No competitor offers structured counterfactual + SROI + contribution analysis. Paired with evidence governance, this makes Impact Vision the reference platform for serious impact funds.

3. **Investee self-service closes the Novata gap** but *with* evidence governance. Sopact's persistent identity + Novata's questionnaire + Impact Vision's evidence layer = unmatched experience.

4. **AI governance enables trust at scale.** Every LLM extraction must be reviewable. This is how Impact Vision survives institutional scrutiny.

5. **Beneficiary voice is evidence, not just insight.** Sopact provides intelligence; Impact Vision provides verified evidence.

---

_Last updated: 2026-04-28. Tracks 1-9 sequenced; competitive gaps identified; success criteria defined._
