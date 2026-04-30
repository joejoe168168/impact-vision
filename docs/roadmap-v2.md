# Impact Vision — Product Roadmap v2.0

**Date:** 2026-04-28
**Status:** New planning draft
**Purpose:** Reframe the v1 backlog into an institutional-readiness roadmap for fund managers, LPs, and investees.

> **Implementation note:** Roadmap v2 now has backend MVP coverage through
> `openharness.impact.roadmap_v2` plus the dedicated metric record,
> data-quality, evidence graph, investee collection, EDCI completeness, and
> climate accounting modules. The coverage is intentionally storage-agnostic and
> API-ready; product UI and persistence can be layered on these contracts.

---

## Research Signals From April 2026 Web Review

The v1 roadmap correctly identified investee data collection, carbon accounting, causal impact, and LP reporting as the major product gaps. The 2026 research pass changes the emphasis: buyers are not just asking for more features; they are asking for comparable, governed, assurance-ready data flows.

| Signal | Product Implication | Source |
|---|---|---|
| Impact data remains hard to compare across standards, sectors, and contexts; AI can help harmonize it only when paired with strong governance. | Build an AI-assisted metric normalization and evidence-governance layer before adding more narrative generation. | [World Economic Forum, Apr 2026](https://www.weforum.org/stories/2026/04/impact-investing-has-a-comparability-problem-ai-offers-a-path-forward/) |
| Institutional LPs are pushing impact investing toward market infrastructure, with data, scale, infrastructure, resources, and networks as key readiness pillars. | Treat LP readiness as a system capability: standardized data rooms, reporting APIs, verification packs, and repeatable workflows. | [ILPA, Jan 2026](https://ilpa.org/resources-tools/resource-library/impact-investing-the-state-of-market-institutionalization/) |
| Private-market ESG convergence is now a mainstream LP expectation; EDCI covers greenhouse gas emissions, net zero, renewable energy, diversity, accidents, net new hires, and employee engagement. | Make EDCI export and validation a first-class data contract, not a late reporting template. | [ILPA EDCI](https://ilpa.org/industry-guidance/environmental-social-governance/data-convergence-initiative/) |
| ISSB adoption is moving from voluntary alignment to jurisdictional implementation; IFRS Foundation has published jurisdictional profiles and reports 36 jurisdictions adopting, using, or finalizing ISSB-aligned requirements. | Add jurisdiction-aware disclosure profiles and ISSB/ESRS interoperability mapping. | [IFRS Foundation, Jun 2025](https://www.ifrs.org/content/ifrs/home/news-and-events/news/2025/06/ifrs-foundation-publishes-jurisdictional-profiles-issb-standards.html) |
| EU sustainability reporting is being simplified through amended ESRS drafts, with standards shortened materially after the Omnibus initiative. | Build regulatory packs as versioned rule sets, because requirements are changing fast. | [EFRAG, revised ESRS exposure drafts](https://www.efrag.org/en/news-and-calendar/news/press-release-efrag-shares-revised-esrs-exposure-drafts-and-launches-60day-public-consultation) |
| GHG Protocol Corporate, Scope 2, and Scope 3 standards are under active revision; Scope 3 updates are a live 2026 workstream. | Keep the carbon engine modular, with versioned emission-factor sets and data-quality scoring. | [GHG Protocol update process](https://ghgprotocol.org/ghg-protocol-standards-and-guidance-update-process-0), [Scope 3 March 2026 update](https://ghgprotocol.org/sites/default/files/2026-03/S3-Phase1ProgressUpdate-20260331.pdf) |
| Impact management conversations now include outcomes, stakeholder engagement, impact at exit, framework harmonization, LP/GP expectations, AI, and systems change. | Product should connect origination, monitoring, exit, and verification instead of treating assessment as a one-off report. | [Operating Principles / GIIN Forum 2025](https://www.impactprinciples.org/news/signatory-luncheon-2025-giin-impact-forum/) |

---

## V2 Strategy

**North star:** Impact Vision should become the open-source system of record for impact data quality, evidence lineage, and LP-ready reporting in private markets.

**Primary users:**
- **Fund analysts** who need repeatable impact DD, monitoring, and IC evidence.
- **Portfolio companies** that need simple data requests with clear metric definitions and units.
- **LP relations teams** that need comparable exports, audit trails, and disclosure packs.
- **Verification providers** that need evidence lineage and stable review bundles.

**Product principles:**
1. **Data contracts before dashboards** — every reportable metric should have definition, unit, source, period, owner, quality score, and review status.
2. **AI with controls** — AI may extract, map, and draft, but every inferred value must carry confidence, provenance, and human-review state.
3. **Versioned standards** — IRIS+, EDCI, ISSB, ESRS, SFDR, GHG Protocol, and PCAF mappings must be versioned and testable.
4. **Investee-first UX** — data collection should be easy enough for a CFO or operations lead to complete without IMM training.
5. **Assurance by default** — reports should always be traceable back to source evidence and approvals.

---

## Roadmap Tracks

### Track 1: Data Contract & Evidence Backbone
**Timeline:** Q2 2026
**Goal:** Make reported impact data trustworthy, traceable, and reusable across every tool.

| # | Item | Priority | Effort |
|---|---|---|---|
| 1.1 | Canonical metric record model: metric ID, value, unit, period, source, owner, quality score, verification status | Critical | M |
| 1.2 | Evidence graph: claim → metric → source document → reviewer decision → report section | Critical | L |
| 1.3 | ✅ Data-quality scoring rubric covering completeness, recency, consistency, source type, and verification level | Critical | M |
| 1.4 | ✅ Versioned standards registry for IRIS+, EDCI, ISSB, ESRS, GHG Protocol, PCAF, SFDR, and OPIM | High | M |
| 1.5 | ✅ Audit-log events for metric creation, edits, imports, approvals, and report publication | High | M |
| 1.6 | Golden regression fixtures for representative company, fund, and portfolio reports | High | S |

### Track 2: Investee Data Collection Portal
**Timeline:** Q2-Q3 2026
**Goal:** Close the largest competitive gap by letting investees self-report structured data.

| # | Item | Priority | Effort |
|---|---|---|---|
| 2.1 | Dynamic questionnaire generator from selected metrics, sector template, and reporting period | Critical | L |
| 2.2 | Public secure collection links with expiry, submission tokens, and no-auth basic workflow | Critical | M |
| 2.3 | Investee guidance cards: definition, unit, examples, acceptable evidence, and common mistakes | Critical | M |
| 2.4 | Multi-period collection tracker with missing, stale, submitted, reviewed, and approved states | High | M |
| 2.5 | Analyst review queue with anomaly flags, comments, resubmission requests, and approval history | High | L |
| 2.6 | Sector onboarding templates for energy, financial inclusion, healthcare, agriculture, education, and circular economy | Medium | M |
| 2.7 | CSV/XLSX import with column mapping, duplicate detection, and validation preview | Medium | M |

### Track 3: Carbon & Climate Accounting Core
**Timeline:** Q3 2026
**Goal:** Provide credible Scope 1, Scope 2, proxy Scope 3, and financed-emissions coverage without trying to replace specialist platforms.

| # | Item | Priority | Effort |
|---|---|---|---|
| 3.1 | Scope 1 and Scope 2 calculator with activity-data inputs, emission factors, units, and factor versioning | Critical | L |
| 3.2 | Proxy Scope 3 estimates by sector and spend/revenue/activity where direct data is missing | Critical | L |
| 3.3 | PCAF financed-emissions workflow with attribution factor, data-quality score, and portfolio rollup | Critical | L |
| 3.4 | Emission-factor catalog loader with EPA/DEFRA/IEA-style metadata and update provenance | High | M |
| 3.5 | Carbon intensity metrics: tCO2e/revenue, tCO2e/employee, tCO2e/unit, and ownership-adjusted footprint | High | M |
| 3.6 | Climate data-quality dashboard showing actual vs estimated coverage by scope and company | High | M |
| 3.7 | Version flags for GHG Protocol / PCAF methodology used in every calculation | High | S |

### Track 4: Standards Interoperability & Disclosure Packs
**Timeline:** Q3-Q4 2026
**Goal:** Turn fragmented frameworks into a governed crosswalk and jurisdiction-aware reporting engine.

| # | Item | Priority | Effort |
|---|---|---|---|
| 4.1 | EDCI export validator and completeness dashboard | Critical | M |
| 4.2 | ISSB S1/S2 disclosure pack with source-linked answers and climate metric dependencies | Critical | L |
| 4.3 | ESRS/CSRD pack with amended-ESRS versioning and double-materiality evidence links | High | L |
| 4.4 | SFDR PAI autofill with direct, proxy, missing, and not-applicable classifications | High | L |
| 4.5 | Framework crosswalk explorer: IRIS+ ↔ EDCI ↔ ISSB ↔ ESRS ↔ PCAF ↔ GRI | High | M |
| 4.6 | Jurisdiction profile selector for EU, UK, Singapore, Japan, Australia, Canada, and US/state climate reporting | Medium | M |
| 4.7 | Rule-pack test harness so standards changes can be updated without breaking old reports | High | M |

### Track 5: LP Reporting & Institutional Portal
**Timeline:** Q4 2026
**Goal:** Make Impact Vision useful for quarterly LP workflows, not only company assessment.

| # | Item | Priority | Effort |
|---|---|---|---|
| 5.1 | Fund-level LP dashboard with portfolio coverage, impact score distribution, top SDGs, carbon footprint, and data-quality warnings | Critical | L |
| 5.2 | ILPA-aligned impact appendix and EDCI attachment for quarterly reporting | Critical | M |
| 5.3 | LP export bundle: PDF/HTML, XLSX, JSON, source index, and evidence manifest | High | L |
| 5.4 | Fund/vintage/sector/geography filters for LP self-serve views | High | M |
| 5.5 | LP question-answer workspace with citations back to approved evidence | Medium | L |
| 5.6 | Report publication workflow with draft, reviewer approved, published, and superseded states | High | M |
| 5.7 | White-label branding by fund, including logo, color, disclaimer, and contact metadata | Medium | S |

### Track 6: Assurance, Verification & Controls
**Timeline:** Q1 2027
**Goal:** Make third-party verification and internal control review practical.

| # | Item | Priority | Effort |
|---|---|---|---|
| 6.1 | Assurance pack builder with metric sample selection, evidence files, reviewer notes, and management assertions | Critical | L |
| 6.2 | Verification provider workspace with read-only evidence access and comment resolution | High | L |
| 6.3 | Control checks for segregation of duties, late edits, unreviewed AI outputs, and unsupported claims | High | M |
| 6.4 | AI extraction review gates: approve, reject, edit, or request evidence for every claim and metric | Critical | M |
| 6.5 | Immutable report manifest with hashes for source documents, data exports, and final reports | High | M |
| 6.6 | Exception register for unresolved gaps, management overrides, and known limitations | Medium | M |

### Track 7: Causal Impact & Outcome Intelligence
**Timeline:** Q1-Q2 2027
**Goal:** Differentiate beyond compliance by helping funds understand whether outcomes are likely attributable.

| # | Item | Priority | Effort |
|---|---|---|---|
| 7.1 | Contribution analysis workflow aligned to IMP / Impact Frontiers contribution logic | Critical | L |
| 7.2 | Counterfactual question generator by sector, business model, and claimed outcome | High | M |
| 7.3 | Evidence-strength ladder with study design, sample size, third-party review, and beneficiary voice inputs | High | M |
| 7.4 | SROI model templates with assumptions, sensitivity ranges, and value-bank source tracking | High | L |
| 7.5 | Difference-in-differences calculator for pre/post and comparator data | Medium | L |
| 7.6 | Exit impact assessment template linked to OPIM Principle 8 and post-exit durability | Medium | M |
| 7.7 | Impact learning loop: hypothesis, metric, result, management action, follow-up period | High | M |

### Track 8: Governed AI & Market Intelligence
**Timeline:** Q2 2027
**Goal:** Use AI to reduce analyst workload while preserving explainability, reviewability, and auditability.

| # | Item | Priority | Effort |
|---|---|---|---|
| 8.1 | AI metric harmonizer: map messy investee uploads to canonical metric records with confidence and rationale | Critical | L |
| 8.2 | Natural-language portfolio query engine constrained to approved data and source citations | High | L |
| 8.3 | Regulatory-change monitor that flags affected rule packs, report templates, and portfolio companies | High | L |
| 8.4 | Peer benchmark assistant using GIIN/IRIS+ benchmark snapshots and internal anonymized portfolio data | Medium | L |
| 8.5 | Greenwashing reviewer with claim specificity, evidence gap, selectivity, and adverse-impact omission explanations | High | M |
| 8.6 | AI output governance: prompt/version log, source grounding, human reviewer, and confidence threshold policy | Critical | M |

---

## Sequencing Recommendation

The v2 execution order should be:

1. **Finish Track 1 first.** It creates the data contract needed by every later track.
2. **Build Track 2 and Track 3 in parallel.** Investee collection supplies the data; carbon accounting is the most common LP/regulatory need.
3. **Use Track 4 to turn collected data into standards-ready outputs.**
4. **Ship Track 5 once exports and evidence manifests are stable.**
5. **Add Track 6 controls before scaling to enterprise customers.**
6. **Invest in Track 7 and Track 8 as differentiators after the system is trustworthy.**

---

## Near-Term Development Backlog

These are the first implementation candidates after Phase 11:

| Sprint | Deliverable | Acceptance Criteria |
|---|---|---|
| Sprint 1 | ✅ Canonical `MetricRecord` model and validation helpers | Unit tests cover valid/invalid metric ID, unit, period, source, quality score, and verification state. |
| Sprint 2 | ✅ Investee questionnaire schema generator | Given sector + metrics, returns form sections with labels, guidance, units, evidence requirements, and validation rules. |
| Sprint 3 | ✅ Collection submission model and review states | Submissions can be created, validated, flagged, approved, rejected, and converted into canonical metric records. |
| Sprint 4 | ✅ Target and claims evidence graph | Report output can show which approved evidence supports each target, claim, SDG alignment, and disclosure answer. |
| Sprint 5 | ✅ EDCI completeness report | Portfolio-level output shows available, missing, proxy, and not-applicable values for all EDCI categories. |
| Sprint 6 | ✅ Scope 1/2 calculator MVP | Activity data produces tCO2e with factor source, factor year, scope, method, and data-quality score. |

---

## Success Metrics

| Metric | Target |
|---|---|
| Investee collection completion time | Under 30 minutes for a basic quarterly submission |
| Metric data contract coverage | 95%+ of reported metrics have unit, period, source, and owner |
| AI extraction reviewability | 100% of AI-derived claims and values have confidence, rationale, and reviewer state |
| LP export completeness | EDCI and ISSB packs identify every required field as reported, proxy, missing, or not applicable |
| Carbon coverage | Scope 1+2 available or explicitly marked missing for 90%+ of active portfolio companies |
| Assurance readiness | Every published LP report includes an evidence manifest and immutable report hash |

---

## What This Replaces From v1

This roadmap does not discard v1. It reorganizes v1 priorities around product readiness:

- Phase 12 becomes **Track 2: Investee Data Collection Portal**.
- Phase 13 becomes **Track 3: Carbon & Climate Accounting Core**.
- Phase 15 and Phase 18 become **Track 4 and Track 5**.
- Phase 14 becomes **Track 7: Causal Impact & Outcome Intelligence**.
- Phase 19 controls become **Track 6: Assurance, Verification & Controls**.
- Phase 20 AI features become **Track 8: Governed AI & Market Intelligence**.

The main change is sequencing: Impact Vision should now build the evidence/data backbone before broadening the feature surface.
