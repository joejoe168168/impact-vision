# Impact Vision — Roadmap v4.0

**Date:** 2026-05-02 (amended after extensive review of the consultant landscape
and an audit of existing v3 capabilities; updated after Tracks 1-10 backend ship)  
**Status:** Consultant-Led Product Strategy — Integration Wave (Backend complete for all 10 tracks; frontend + paid-data wiring deferred to Wave 5)  
**Audience:** product, engineering, impact consultants, fund operators  
**Thesis:** v3 already shipped most of the discrete capabilities a consultant
needs (evidence graph, OPIM verification workspace, LP narrative, stakeholder
voice, exit impact, regulatory packs, IRIS+/EDCI/ESRS/ISSB/GRI/SASB/TCFD/SFDR
frameworks, climate accounting, MCP + REST API, monitoring, pipeline). What is
**missing is the engagement layer that ties them together**: a consultant
project workspace, a Tideline-style Impact Management Compass scaffold, a
Holtara-style "service across the investment cycle" navigation, a BlueMark
3-pillar verification bundle, and a public website that productises the
methodology. v4 should therefore be **mostly an integration, packaging, and
workflow wave**, not a re-implementation wave.

---

## 1. Market Signals From Impact Consultants

### TSIC: Consultant-Led Impact Strategy And IMM

Public TSIC positioning emphasises a high-touch consulting model:

- Social impact measurement and management frameworks tailored to stakeholder
  needs.
- Integrated measurement models across programme and organisation levels.
- Impact evaluation using data-backed quantitative and qualitative methods.
- Social investment strategy for funders and impact investors, including ROI
  in financial and social terms.
- ESG strategy, E&S management systems, governance capability, KPI frameworks,
  due diligence, verification, reporting, and staff capacity building.
- Stakeholder engagement, field accountability, equity-led facilitation,
  learning loops, and training.

Implication for Impact Vision: a strong product cannot only generate scores. It
must support the consultant's end-to-end engagement: diagnose, scope, facilitate,
train, collect data, validate evidence, report, and recommend management action.

### Rimm Sustainability: ESG Platform And Automation

Rimm's public positioning points to a platform-led model:

- A full-stack AI ESG management platform centralising data collection,
  analytics, workflow automation, and reporting.
- Framework-aligned reporting across GRI, CSRD, ISSB, TCFD, SDGs, and other
  standards.
- Benchmarking against very large company datasets.
- ESG/risk analytics, risk ratings, financed-emissions support, supply-chain
  workflows, and API-driven data products.
- One-click reports and automation for SMEs through larger enterprises.
- Impact management as a funding and credibility unlock, including DFI/carbon
  credit/REC opportunities.

Implication for Impact Vision: v4 should productise the analyst workflow around
data intake, benchmarking, scenario analysis, report automation, and advisory
dashboards while keeping v3's evidence-governance advantage.

### Tideline + BlueMark: Impact Management Compass And Three-Pillar Verification

Tideline (200+ projects, 130+ clients, $200B+ in capital) is structured around
five service lines under its **Impact Management Compass**:

1. **Strategy Development** — investment thesis, impact themes, lens design.
2. **Impact Management System Design** — governance, IMM policies, KPIs.
3. **Impact Due Diligence** — pre-investment screening and impact thesis test.
4. **Impact Monitoring & Reporting** — IRIS+/EDCI/ILPA-aligned reporting.
5. **Impact Verification (BlueMark)** — independent assurance against OPIM,
   IMP, GIIN IRIS+, GRI, PRI, SDG Impact, SDR, and SFDR.

BlueMark's verification methodology splits assurance into **three pillars**:

- **Impact Mandate verification** — does the strategy itself credibly target
  impact?
- **Impact Management Practice verification** — are the OPIM-aligned processes
  actually being executed?
- **Impact Reporting verification** — is what is published to LPs honest,
  complete, and tied to evidence?

Implication for Impact Vision: package v3's modules into the **Compass + 3-pillar**
shape consultants and their LPs already recognise, rather than asking the market
to learn a new mental model.

### Holtara, Impact Institute, ImpactMapper, ImpactVC: One-Stop-Shop Pattern

- **Holtara** (Apex Group): explicit "one-stop-shop, services across the
  investment cycle" structured as **Impact strategy → Regulatory support →
  Screening & DD → Monitoring & data (Holtara.io platform) → Independent
  verification → Reporting impact**, plus training for investment teams and
  portfolio companies, and explicit impact VDD/exit reports for value at exit.
- **Impact Institute**: modular DD (Light / Mid / Full) anchored in the
  Impact-Weighted Accounts framework, with monetisation, attribution, and IMM
  (Impact Multiple of Money) as headline outputs; one Impact Investor Tool
  (IIT) covers calculation models, periodic data requests, and aggregated
  fund reporting.
- **ImpactMapper**: bundles **Reports + Advisement + Software** with custom
  surveys, outcome harvesting, and human-stories storytelling alongside
  metrics. Recently published a Responsible AI approach.
- **ImpactVC** (incubated at Better Society Capital): publishes open-source
  **Founders Playbook** and **VC Playbook** plus impact coaching and training
  programmes for VCs. Validates the open-source playbook + community surface
  as a credible go-to-market pattern.

### Broader Consultant Pattern

Impact Institute, ImpactMapper, Impact ROI, Holtara, Tideline/BlueMark, ImpactVC,
TSIC, and investor IMM guidance converge around the same needs:

- Theory of Change and logic-chain design.
- Practical KPI frameworks linked to strategy.
- Outcomes and impact measurement, not just activity/output metrics.
- Portfolio and programme evaluation.
- Impact reporting adapted to different audiences.
- Training and capacity building.
- Business-case / value-creation playbooks tied to alpha generation.
- Impact due diligence, verification, value creation, and exit reporting.
- Regulatory advisory across SFDR, SDR, SEC climate, CSRD/ESRS, and ISSB.

Implication for Impact Vision: v4 should be less "tool menu" and more
"consulting workflow engine."

### The Sopact Counter-Position (And Why It Matters For v4)

Sopact has explicitly argued (2026-04 page on Theory of Change) that
"consultation-driven Theory of Change is over" because AI now collapses
qualitative analysis, framework extraction, and IRIS+/SROI alignment from
months to seconds. They reposition the bottleneck as **persistent stakeholder
identity and longitudinal data ownership**, not framework facilitation.

This is a direct attack on the value proposition of every consultant Impact
Vision plans to serve. v4 must not pretend it isn't happening. Our response:

1. **Don't out-Sopact Sopact on framework auto-generation** — they already
   ship that. Instead, position Impact Vision's ToC builder (Track 2) as
   **AI-drafted, consultant-curated, evidence-bound**: AI extracts the
   first-pass ToC from intake docs, the consultant interrogates and rewrites
   it in a workshop, and every assumption/outcome is bound to evidence in the
   v3 evidence graph so it can be verified later.
2. **Make the consultant's judgement legible** — every consultant override of
   an AI suggestion should be logged as a reviewer event in `audit_trail.py`
   so the workshop output is itself an auditable artefact.
3. **Lean into governance and assurance** — Sopact has no audit trail, no
   immutable manifest, no OPIM-aligned verification workspace. Those are
   v3 strengths the v4 surface should make obvious.
4. **Take the persistent-identity critique seriously** — extend
   `stakeholder_voice.py` so beneficiaries get a stable ID across rounds,
   not a per-survey row. (See Track 3.X amendment below.)

---

## 2. V4 North Star

**Impact Vision should become the AI workbench for impact consultants and fund
operators who need to turn messy client data into credible strategy, evidence,
management action, and reports.**

Strategic moves:

1. **Consultant workflow layer** — proposal → diagnostic → ToC → KPI framework
   → collection → validation → reporting → learning loop.
2. **Client-ready website/product surface** — guided public-facing workflows,
   dashboards, downloadable outputs, and role-specific portals.
3. **Benchmark and value-creation intelligence** — turn ESG/impact data into
   peer context, risk, opportunity, business case, and recommended action.
4. **Capacity-building layer** — training packs, workshops, founder guidance,
   and investee coaching generated from the actual evidence gaps.
5. **Evidence-governed AI services** — all AI suggestions remain traceable to
   approved evidence, source documents, and human review decisions.

---

## 3. Product Principles

- **Consultant-first, client-safe:** experts can override, annotate, and explain
  every AI output before clients see it.
- **Strategy before metrics:** start with goals, stakeholders, theory of change,
  risks, and decisions, then choose metrics.
- **Evidence beats polish:** every claim, score, benchmark, and recommendation
  should cite source data and confidence.
- **Reusable engagement assets:** every consulting project should produce
  reusable templates, questionnaires, reports, and training modules.
- **Website as product funnel:** public website workflows should demonstrate
  value quickly while routing serious users into deeper assessment flows.

---

## 4. Codebase Reuse Map (v3 → v4 Delta)

Before any new track is started, the engineering team must read this table.
Most v4 user-facing concepts already have a v3 backing module; v4 is mostly
a **packaging, navigation, and workflow** wave on top.

| v4 Capability | Already shipped in v3 | New work needed in v4 |
|---|---|---|
| Theory of Change canvas | `impact/toc_graph.py`, `frameworks/theory_of_change.py` | Visual canvas, AI-draft from intake docs, consultant override audit |
| KPI framework generator | `tools/impact/metric_recommender_tool.py`, IRIS+ catalog, cross-reference | Bundle by engagement type, lock & version per project |
| Investee data room | `impact/investee_collection.py`, `questionnaire_v2.py`, `surveys.py`, `tools/.../beneficiary_feedback_tool.py` | Client portal UI, dynamic builder, expiry/no-auth links, multi-entity roll-up |
| Evidence graph + audit | `impact/evidence_graph.py`, `audit_trail.py`, `evidence_workflow.py`, `verification_workspace.py` | Engagement-scoped views, deliverable-bound completeness scoring |
| LP narrative + Q&A | `impact/lp_narrative.py`, `lp_portal.py`, `lp_calendar.py`, `tools/.../lp_narrative_tool.py`, `lp_ddq_export_tool.py` | Multi-audience templating (LP/IC/board/regulator), approval workflow |
| Greenwashing review | `impact/greenwashing.py`, `greenwashing_reviewer.py`, `tools/.../greenwashing_*tool.py` | Embed in report builder claim review panel |
| Climate accounting | `impact/climate_accounting.py`, `emission_factors.py` | Supplier questionnaire flow + Scope 3 hotspot UI |
| Causal & contribution | `impact/causal.py`, `counterfactual.py`, `sroi.py`, `bayes.py`, `meta_analysis.py`, `spillover.py` | Surface in ToC validator and value-creation engine |
| Risk / opportunity | `impact/risk_opportunity.py`, `tools/.../impact_risk_opportunity_tool.py` | Material risk register and mitigation actions per engagement |
| Benchmarks | `impact/benchmarks.py`, `external_benchmarks.py` | Pluggable provider interface, peer dashboard, anonymised teaser |
| Pipeline / monitoring | `tools/.../pipeline_tool.py`, `monitoring_tool.py`, `trend_analysis_tool.py` | Engagement workspace overlay, deliverable tracker |
| Exit impact | `impact/exit_impact.py`, `tools/.../exit_impact_tool.py` | Wrap as Impact VDD / exit report bundle |
| Frameworks (10+) | `frameworks/{sasb,gri,tcfd,sfdr_pai,edci,unpri,issb_ifrs_s1,issb_ifrs_s2,esrs,ifc_opim,tnfd}.py` | Regulatory wizard navigation (Track 9) |
| MCP / API surface | `impact/mcp_server.py`, `api_gateway/router.py`, `sdk.py`, `plugins.py`, `marketplace.py`, `tenancy.py`, `soc2_checklist.py` | Engagement-scoped tokens, white-label tenancy, partner portal |
| Stakeholder voice | `impact/stakeholder_voice.py`, `worker_voice.py`, `tools/.../stakeholder_voice_tool.py` | Persistent stakeholder ID across rounds (Sopact-counter) |
| Document intelligence | `tools/.../document_analysis_tool.py`, `pitch_deck_analyze_tool.py`, `impact/extractors/` | Meeting-note ingestion, decision/action extraction |
| AI governance | `impact/evidence_workflow.py`, AI extraction review queue, `evidence_review_tool.py` | Prompt/version/model metadata on every output, copilot review queue |
| Improvement advice | `tools/.../improvement_advisor_tool.py`, `narrative_tool.py`, `guided_assessment_tool.py` | Reframe as Value Creation Plan deliverable |

**Engineering rule for v4:** if a feature has a v3 backing module, the v4
ticket is *integration only*, not re-implementation. New code lives in
`impact/engagements/`, `tools/impact/engagement_*`, and the public website
(`frontend/`). Avoid forking existing modules.

---

## 4a. Engagement-Type Bundles (Productised Service Lines)

Tideline, Holtara, Impact Institute, and TSIC all sell *named* engagements.
v4 should ship the same packaged offerings on top of existing tools so a
consultant can launch a project without picking 30 tools by hand.

| Engagement | Compass step | Bundled tools (existing) | New v4 wrapper |
|---|---|---|---|
| **Impact Strategy / IMM Baseline** | Strategy + System Design | ToC builder, fund_thesis, KPI generator, sdg_mapper, five_dimension_assess | "Strategy Engagement" template, workshop pack |
| **Impact DD (Light)** | DD | dd_checklist, pitch_deck_analyze, exclusion_screening, greenwashing | DD-Light report template, 3-day SLA scaffold |
| **Impact DD (Mid)** | DD | + 5D, sdg_mapper, framework_tool, risk_opportunity, benchmarks | DD-Mid template with KPI term-sheet annex |
| **Impact DD (Full / IWA-style)** | DD | + sroi, causal, counterfactual, scenario_modeling, climate_accounting | Quantified IMM (Impact Multiple of Money) report |
| **ESG Baseline** | System Design | framework_tool (CSRD/ESRS, ISSB, SASB, GRI, TCFD), data_quality, exclusion_screening, regulatory_packs | ESG Baseline workspace + materiality matrix |
| **Annual Impact Report** | Monitoring & Reporting | impact_report, lp_narrative, narrative_tool, trend_analysis, monitoring_tool | Multi-audience report builder (Track 5) |
| **LP DDQ Response Pack** | Monitoring & Reporting | lp_ddq_export_tool, lp_portal, evidence_workflow | LP Q&A workspace constrained to verified data |
| **Impact Verification (3-pillar)** | Verification | verification_workspace, verification_prep, evidence_graph, audit_trail, ifc_opim | BlueMark-style 3-pillar bundle (Track 10) |
| **Impact VDD / Exit Report** | Exit | exit_impact, lp_narrative, evidence_graph, returns | Exit-ready bundle, OPIM Principle 7 narrative |
| **Regulatory Compliance** | Regulatory | sfdr_pai, esrs, csrd_wizard, regulatory_packs, climate_accounting | SFDR/SDR/SEC/CSRD wizard navigator (Track 9) |
| **Stakeholder Voice Study** | Cross-cutting | stakeholder_voice, worker_voice, surveys, beneficiary_feedback | Persistent stakeholder ID (Sopact-counter) |
| **Capacity Building / Training** | Cross-cutting | improvement_advisor, narrative_tool, dd_checklist, evidence_workflow | Workshop pack generator (Track 6) |

---

## 4b. V4 Strategic Tracks

### Track 1: Consultant Engagement Workspace

**Timeline:** Q2 2026  
**Status:** Wave-1 foundation landed (see `impact.engagements` + `engagement_workspace` tool).  
**Goal:** Convert Impact Vision from a collection of tools into a managed
consulting engagement workspace.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 1.1 | Engagement model: client, fund, programme, scope, timeline, deliverables, owner, review status | Critical | M | Done (`engagements.models.Engagement`) |
| 1.2 | Proposal builder: turn intake notes into scope, workplan, assumptions, fees, outputs, and risk caveats | High | M | Done (`engagements.proposal.build_proposal`) |
| 1.3 | Consultant checklist: discovery, data request, stakeholder map, ToC workshop, KPI design, reporting, training | Critical | S | Done (`engagements.checklist.build_consultant_checklist`) |
| 1.4 | Engagement evidence vault: all uploaded docs, interview notes, data files, decisions, and outputs linked to audit trail | Critical | M | Done (`EngagementWorkspace.attach_document` / `record_decision` / `record_override` with `AuditTrail` integration) |
| 1.5 | Client-ready deliverable tracker with draft/review/final states and export bundles | High | M | Done for state machine; export bundle deferred to Wave 4 reporting studio |
| 1.6 | Reusable template library by client type: fund, corporate CSR, foundation, nonprofit, social enterprise | High | M | Done (`engagements.templates.CLIENT_TEMPLATE_LIBRARY`) |

**Value add:** TSIC-style advisory work becomes repeatable, auditable, and
faster to deliver.

### Track 2: Theory Of Change And Strategy Builder

**Timeline:** Q2-Q3 2026  
**Status:** Critical items (2.1-2.3) shipped in Wave 2; 2.4-2.6 partially stubbed.  
**Goal:** Make ToC and strategy design a guided, evidence-backed workflow.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 2.1 | Interactive ToC canvas: problem, stakeholders, inputs, activities, outputs, outcomes, impact, assumptions | Critical | L | Done — `engagements.toc_builder.ToCCanvas` + `draft_toc_from_intake` (data model + Mermaid render via v3 `toc_graph`) |
| 2.2 | Logic-chain validator: flags missing assumptions, weak causal links, unmeasured outcomes, and risk blind spots | Critical | M | Done — `validate_toc_canvas` (11 rule codes covering problem statement, outcomes/impact existence, input-traceability, IRIS+ indicator coverage, assumption attachment + testing, causal strength, stakeholders, equity lens, risk mitigations) |
| 2.3 | KPI framework generator: maps ToC outcomes to IRIS+, SDGs, EDCI, ESRS, GRI, ISSB, and custom KPIs | Critical | M | Done — `generate_kpi_framework` wraps the v3 IRIS+ scoring logic and `cross_reference.lookup_by_iris` to expand each pick across GRI / EDCI / SASB / TCFD / ISSB / ESRS / TNFD / PCAF / EU Taxonomy / CDP / SBTi / SFDR PAI |
| 2.4 | Strategy-options simulator: compare target groups, geographies, interventions, and impact themes | High | L | Not started |
| 2.5 | Stakeholder workshop pack: agenda, facilitation prompts, interview guide, and consensus scoring | High | M | Partially — `engagements.checklist` "Stakeholder Map" / "ToC Workshop" phases ship facilitation prompts; full consensus scoring outstanding |
| 2.6 | Equity and inclusion lens: checks who benefits, who is excluded, and whose voice is missing | High | M | Partially — canvas carries `equity_notes` + per-node `equity_segment`; validator enforces an equity lens rule; structured equity dashboard outstanding |

**Value add:** Impact Vision supports strategy facilitation, not just reporting.

### Track 3: Client And Investee Data Room

**Timeline:** Q3 2026  
**Status:** Critical items (3.3-3.6) shipped; 3.1/3.2/3.7 backend-only (data models ready, frontend outstanding).  
**Goal:** Productise Rimm-style data collection while preserving evidence
governance.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 3.1 | Client portal for data requests, questionnaires, file uploads, comments, and status tracking | Critical | L | Partially — backend data contracts landed (`DataRequestPack`, `DataRoomSubmission`, `issued_links`); UI deferred to Wave 5 frontend |
| 3.2 | Dynamic assessment builder with 4,000-question ambition: standards, geography, sector, fund thesis, client maturity | High | L | Partially — bundle-aware field catalogue + `extra_fields` override; 4k-question taxonomy is later work |
| 3.3 | Smart data request packs by engagement type: DD, annual impact report, ESG baseline, CSR strategy, exit impact | Critical | M | Done — `build_data_request_pack` keyed to every v4 engagement bundle |
| 3.4 | Automated evidence completeness scoring by deliverable and framework | High | M | Done — `score_completeness` (per-entity coverage, required/submitted counts) + `overall_coverage_pct` computed field |
| 3.5 | Data quality exception workflow: missing, stale, inconsistent, proxy, unverified, outlier | Critical | M | Done — `DataQualityException` with all six exception kinds and status lifecycle |
| 3.6 | Client guidance cards: definition, examples, source docs, acceptable evidence, common mistakes | High | M | Done — every field carries guidance cards; `build_coaching_cards` lifts exceptions into investee-facing prescriptions |
| 3.7 | Multi-entity consolidation: business units, portfolio companies, programmes, geographies | High | L | Done — `rollup_multi_entity` with per-entity coverage + per-metric fill rate + computed overall fill rate |

**Value add:** consultants spend less time chasing spreadsheets and more time
interpreting results.

### Track 4: Benchmarking, Risk And Value Creation Intelligence

**Timeline:** Q3-Q4 2026  
**Status:** All seven items shipped as deterministic backend engines; paid-dataset wiring is a Wave 5 concern.  
**Goal:** Add business-value and peer-context intelligence to impact data.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 4.1 | Benchmark provider interface: offline sample now, pluggable paid/open datasets later | Critical | M | Done — `BenchmarkProvider` protocol + seeded `InMemoryBenchmarkProvider` + global default override hooks |
| 4.2 | Peer benchmark dashboard by sector, geography, company size, fund strategy, and metric | High | L | Done — `PeerDashboard` bundled from provider results; filter fields available on `BenchmarkQuery` |
| 4.3 | ESG/impact risk rating with material risk categories and mitigation actions | Critical | M | Done — `ImpactRiskRating` with 14 categories, likelihood×severity scoring, and `material_risks` computed field |
| 4.4 | Value-creation plan: recommends operational actions tied to KPI gaps, risk, and expected outcomes | Critical | L | Done — `build_value_creation_plan` ties actions to KPI gaps / risks / peer gaps with effort + timing |
| 4.5 | ESG/impact business-case model: estimate revenue, cost, risk, valuation, funding, and impact upside | High | L | Done — `BusinessCase` with revenue / cost / risk-avoidance / valuation-multiple inputs and computed uplift |
| 4.6 | Scenario and sensitivity engine for impact and ESG interventions | High | L | Done — `run_scenario` compound-multiplier sensitivity engine (downside / base / upside) |
| 4.7 | Supply-chain and Scope 3 assessment workflow for supplier questionnaires and hotspot analysis | Medium | L | Done — `score_supply_chain_hotspots` with spend×intensity → estimated tCO2e ranking |

**Value add:** move from "what is your score?" to "what should management do
next and why does it matter commercially?"

### Track 5: Consultant-Grade Reporting Studio

**Timeline:** Q4 2026  
**Status:** All six items shipped (deck export = outline; PPTX render deferred to Wave 5 frontend).  
**Goal:** Make reports configurable by audience and engagement type.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 5.1 | Report builder with sections, audience, tone, evidence depth, visuals, and approval workflow | Critical | L | Done — `Report` + `ReportSection` (audience / evidence_depth / tone / visuals) with draft → in_review → approved → published → superseded state machine |
| 5.2 | Engagement-specific templates: IMM baseline, impact DD, ESG baseline, portfolio deep dive, annual report, exit report | Critical | M | Done — 6 named templates (`REPORT_TEMPLATES`) with section titles + tool references + default evidence depth |
| 5.3 | One-click executive deck: board/IC-ready PowerPoint from verified data | High | M | Done — `build_executive_deck` outline (cover + per-section slides + recommendations); PPTX render is a later wiring concern |
| 5.4 | Public website impact microsite generator for client-facing case studies and claims | Medium | L | Done — `build_public_microsite` returns a `PublicMicrositeBundle` of slug-keyed pages |
| 5.5 | Claim review panel embedded in reports: approved, caveated, rejected, needs evidence | Critical | M | Done — `ClaimReview` + `decide_claim` with `claim_status_counts` and `claim_ready_pct` computed fields |
| 5.6 | Multi-audience narratives: founder, IC, LP, board, public, regulator, verifier | High | M | Done — `rewrite_for_audiences` + `AUDIENCE_HINTS` covering all seven audiences |

**Value add:** consultants can deliver polished outputs without losing evidence
discipline.

### Track 6: Training And Capacity-Building Engine

**Timeline:** Q4 2026-Q1 2027  
**Status:** 5 / 6 shipped; consultant knowledge base (6.5) still backed by inline prompts only.  
**Goal:** Productise consultant training and client enablement.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 6.1 | Training-plan generator from client maturity, gaps, and engagement objectives | High | M | Done — `build_training_plan` keyed to `MaturityStage` with effort scaling |
| 6.2 | Workshop packs: ToC, KPI design, ESG baseline, data quality, stakeholder voice, reporting | High | M | Done — 6 `WorkshopPack`s with agendas + facilitation prompts + deliverables |
| 6.3 | Investee coaching cards tied to failed validations and missing evidence | Critical | S | Done — `InvesteeCoachingCard` via `build_coaching_card` + `engagements.data_room.build_coaching_cards` |
| 6.4 | Learning loop: training assigned → action completed → data improves → score updates | Medium | M | Done — `LearningLoopEntry` + `record_learning_loop` captures the four-step loop |
| 6.5 | Consultant knowledge base: reusable explanations, examples, case studies, and facilitation notes | High | M | Partially — `PLAYBOOK_PAGES` (Track 7) ships 5 playbooks; consultant-only KB still inline in workshop pack prompts |
| 6.6 | Certification/readiness badges: data-ready, report-ready, assurance-ready, LP-ready | Medium | M | Done — `ReadinessBadge` via `issue_readiness_badge` with per-kind threshold enforcement |

**Value add:** Impact Vision becomes a way for consultants to scale their
expertise, not just run analyses.

### Track 7: Website Productisation And Conversion

**Timeline:** Q1 2027  
**Status:** Backend data layer for all 7 items shipped; frontend rendering deferred to Wave 5 frontend wiring.  
**Goal:** Turn the public website into a guided product funnel for funds,
consultants, corporates, and social enterprises.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 7.1 | Public diagnostic quiz: "How mature is your impact measurement system?" with instant recommendations | Critical | M | Done (backend) — 7-question quiz + `score_diagnostic` mapping to `initial → optimising` with category-driven recommendations |
| 7.2 | Sample report gallery: DD, LP report, assurance pack, stakeholder voice, exit impact | High | M | Done (backend) — `REPORT_GALLERY` seeded with 5 items across audiences |
| 7.3 | Interactive benchmark teaser with anonymised sample data | Medium | M | Done (backend) — `build_benchmark_teaser` + `BenchmarkTeaser` structured output |
| 7.4 | Consultant playbook pages: ToC design, KPI framework, stakeholder voice, ESG/impact DD, assurance readiness | High | M | Done (backend) — 5-entry `PLAYBOOK_PAGES` catalogue |
| 7.5 | Lead capture from diagnostic outputs into a scoped engagement workspace | High | M | Done (backend) — `capture_lead` with required consent + valid-email check |
| 7.6 | "Upload a memo" demo flow with redacted sample outputs and clear privacy boundaries | Critical | L | Done (backend) — `run_upload_demo` hashes source text, never echoes, returns sanitised outputs only |
| 7.7 | Partner page for consultants: white-label reporting, template library, methodology governance | Medium | M | Done (backend) — `describe_partner_mode` returns white-label metadata pinned to a methodology version |

**Value add:** the website demonstrates expertise and routes users into the
right workflow instead of acting as a static brochure.

### Track 8: AI Consultant Copilot With Governance

**Timeline:** Q1-Q2 2027  
**Status:** Governance scaffolding shipped; LLM call plane (8.1 / 8.3) wires to Track 8 prompt/model metadata but no LLM invocation yet.  
**Goal:** Give consultants an AI assistant that drafts, checks, and challenges
work without inventing unsupported claims.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 8.1 | Engagement copilot: ask questions across client docs, metrics, evidence, notes, and reports | Critical | L | Partially — `EngagementQuery` + `answer_from_approved_evidence` client-safe scaffold; LLM call plane is wiring work |
| 8.2 | Consultant challenge mode: identifies unsupported claims, weak ToC links, and missing stakeholder perspectives | Critical | M | Done — deterministic `run_challenge` covering 5 finding categories |
| 8.3 | Proposal and SOW copilot grounded in selected deliverables and known assumptions | High | M | Partially — `CopilotOutput.kind` includes `proposal_draft` / `sow_draft` with full provenance; deterministic proposal already in Track 1 (`build_proposal`) |
| 8.4 | Meeting note ingestion: extracts decisions, action items, risks, and evidence references | High | M | Done — prefix-based `extract_meeting_notes` seeds the engagement audit log |
| 8.5 | AI output review queue with prompt/version/model metadata and reviewer decisions | Critical | M | Done — `CopilotOutput` (prompt + model + model_version + source_refs) + `CopilotReviewQueue` that blocks approval of low-confidence / unsourced outputs |
| 8.6 | Client-safe answer mode: only answers from approved evidence and marks gaps explicitly | Critical | M | Done — `answer_from_approved_evidence` returns citations only and escalates when no approved data matches |

**Value add:** consultants get speed without sacrificing credibility.

### Track 9: Regulatory Compliance Workbench

**Timeline:** Q3-Q4 2026  
**Status:** All seven items shipped; double-materiality dashboard (9.4) and ISSB readiness (9.5) compose the existing v3 modules via `JurisdictionProfile.obligations`.  
**Goal:** Match Holtara's "Regulatory support" service line by turning the
existing v3 framework modules into a guided, jurisdiction-aware workbench.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 9.1 | Jurisdiction selector (EU, UK, US, Singapore, Switzerland, Canada) wiring SFDR, SDR, SEC climate, CSRD/ESRS, ISSB, MAS green taxonomy | Critical | M | Done — 8 jurisdictions (adds Japan + Australia) wired via `JURISDICTION_PROFILES` |
| 9.2 | SFDR Article 6/8/9 fund classification wizard with PAI completeness check | Critical | M | Done — `classify_sfdr` with DNSH + good-governance + PAI gap detection |
| 9.3 | UK SDR labelling wizard (Sustainability Focus / Improvers / Impact / Mixed Goals) with anti-greenwashing check | Critical | M | Done — `classify_uk_sdr` enforces anti-greenwashing review + evidence-of-impact gate |
| 9.4 | CSRD/ESRS double-materiality assessment workspace with sector overlay and assurance-ready evidence pack (reuse `impact/csrd_wizard.py`) | High | L | Partially — `csrd_double_materiality` obligation wired; sector overlay + evidence-pack export still reuses v3 `csrd_wizard` directly |
| 9.5 | ISSB IFRS S1/S2 readiness assessment with TCFD legacy mapping | High | M | Done — ISSB S1 + S2 obligations wired; crosswalk handled by `frameworks/cross_reference` |
| 9.6 | Regulatory deadline calendar with portfolio-wide gap dashboard | High | M | Done — `schedule_deadlines` returns a per-obligation `RegulatoryDeadline` list with computed `days_until_due` and status |
| 9.7 | Auto-generated regulator-facing narrative (reuse `regulatory_packs.py` + `lp_narrative.py`) with caveat panel | Critical | M | Done — `build_regulator_narrative` composes jurisdiction obligations into governance / strategy / metrics sections with an explicit caveat panel |

**Value add:** consultants stop maintaining separate spreadsheets per regulator
and clients get a single regulatory view across the engagement.

### Track 10: Impact Verification & Assurance Bundle (BlueMark-Style 3-Pillar)

**Timeline:** Q4 2026 - Q1 2027  
**Status:** All seven items shipped. PDF export (10.6) returns the signed JSON manifest; PDF render is a Wave 5 wiring task.  
**Goal:** Productise the verification workspace into the three pillars LPs and
verifiers already recognise from BlueMark / OPIM Principle 9.

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 10.1 | Pillar 1 — Mandate verification workspace: thesis, theory of change, governance, exclusions, additionality, beneficiary lens | Critical | M | Done — `MandatePack` with 6 default `MandateItem`s covering all six pillar-1 checks |
| 10.2 | Pillar 2 — Practice verification workspace: OPIM 9-principle alignment with evidence references and finding lifecycle (reuse `verification_workspace.py` + `ifc_opim.py`) | Critical | M | Done — `PracticePack` ships all 9 OPIM principles; finding lifecycle reuses v3 `verification_workspace` |
| 10.3 | Pillar 3 — Reporting verification workspace: claim-by-claim review of LP narrative against evidence graph and audit trail | Critical | M | Done — `ReportingPack` with per-claim `ReportingClaim` review lifecycle |
| 10.4 | Verifier-facing read-only role with engagement-scoped tokens and immutable manifest export | Critical | M | Done — `issue_verifier_token` (hashed secret, 90-day default expiry, read-only scopes) + `AssuranceManifest` export |
| 10.5 | Independent-verifier marketplace metadata (reuse `marketplace.py`) so consultants can hand off to BlueMark / DNV / KPMG without duplicating data | High | M | Done — `VERIFIER_MARKETPLACE` seeded with BlueMark, KPMG, DNV entries with accreditations + supported methodologies |
| 10.6 | Annual assurance bundle: PDF + JSON-LD + signed manifest (reuse `signed_feed.py`) sufficient for OPIM Principle 9 publication | Critical | M | Done (backend) — `build_assurance_bundle` produces an HMAC-SHA256 signed manifest + per-pillar hash; `verify_assurance_bundle` recomputes and compares; PDF render is a Wave 5 wiring task |
| 10.7 | "Assurance-Ready" badge on engagement workspace driven by completeness scoring and review-queue resolution | High | S | Done — `evaluate_assurance_readiness` issues an `AssuranceReadinessBadge` keyed to per-pillar completion thresholds |

**Value add:** Impact Vision becomes the system the verifier asks for, not just
the system the consultant uses.

---

## 5. Website Feature Recommendations

These are the highest-value public/product website additions:

1. **Impact maturity diagnostic** — gives immediate value and captures leads.
2. **Interactive sample assurance bundle** — shows the v3 trust moat.
3. **Consultant playbook library** — establishes thought leadership like TSIC,
   but product-linked.
4. **Upload-and-preview demo** — shows the AI workflow using sample/redacted
   documents.
5. **Benchmark teaser dashboard** — shows Rimm-style peer context without
   requiring proprietary data on day one.
6. **Report gallery** — LP report, ESG baseline, DD report, stakeholder voice,
   exit impact report.
7. **Partner/consultant mode page** — positions Impact Vision as a white-label
   workbench for impact advisors.
8. **Methodology page** — explain IRIS+, SDGs, 5D, NESTA, OPIM, evidence graph,
   AI governance, and human review.

---

## 6. Implementation Waves

### Wave 1 — Consultant Core (4-6 weeks)

- Engagement model and workspace.
- Consultant checklist and deliverable tracker.
- Public website maturity diagnostic.
- Report gallery using existing v3 outputs.
- Metadata/version tests and registry hardening from the bug-hunt backlog.

### Wave 2 — Strategy And Data Collection (6-10 weeks)

- ToC builder and KPI framework generator.
- Client data room and data request packs.
- Evidence completeness scoring by deliverable.
- Guidance cards and investee coaching.

### Wave 3 — Intelligence And Benchmarking (8-12 weeks)

- Benchmark provider interface.
- Peer dashboard and risk rating.
- Value-creation recommendation engine.
- Scenario/sensitivity analysis.

### Wave 4 — Reporting, Training, Copilot (10-14 weeks)

- Consultant-grade reporting studio.
- Training and workshop pack generator.
- Engagement copilot with client-safe answer mode.
- Website upload-and-preview demo flow.

### Wave 5 — Regulatory & Verification Bundles (8-12 weeks)

- Regulatory Compliance Workbench (Track 9): SFDR, SDR, SEC climate,
  CSRD/ESRS, ISSB wizards across the existing framework modules.
- BlueMark-style 3-Pillar Verification Bundle (Track 10) with verifier
  marketplace handoff and signed assurance manifest.
- Persistent stakeholder-identity layer on `stakeholder_voice.py` to close
  the Sopact gap.
- Partner / consultant white-label tenancy hardening.

---

## 7. Proposed V4 Success Metrics

- **Consultant efficiency:** reduce first-draft report time by 50%.
- **Data completeness:** increase evidence completeness by 30% after guided
  client data requests.
- **Client conversion:** 10%+ diagnostic-to-engagement conversion from website.
- **Assurance readiness:** 80%+ of generated report claims have evidence refs.
- **Training impact:** measurable data-quality improvement after coaching cards.
- **Governance:** 100% of AI-generated client-facing claims pass review queue
  or are explicitly caveated.
- **Bundle adoption:** 70% of new engagements launched from a named template
  (Strategy / DD-Light / DD-Mid / DD-Full / ESG Baseline / Annual / LP DDQ /
  Verification / Exit / Regulatory / Stakeholder Voice / Training).
- **Regulatory coverage:** at least one regulator wizard (SFDR, SDR, CSRD,
  ISSB) used in 50% of EU/UK engagements within two quarters of Wave 5.
- **Verifier handoff:** at least three independent verifiers (BlueMark
  equivalent + two big-4 / DNV / KPMG) able to consume the signed assurance
  manifest without manual re-extraction.
- **Reuse discipline:** zero new modules duplicating an existing v3 module
  (enforced via `Codebase Reuse Map` in PR review).
- **Persistent identity:** every stakeholder feedback record links to a
  stable `stakeholder_id` across at least two collection rounds.

---

## 8. Sources Reviewed

- TSIC — Our Services: <https://www.tsiconsultancy.com/our-services/>
- TSIC — Social impact measurement and management:
  <https://www.tsiconsultancy.com/social-impact-measurement-and-management/>
- TSIC — Impact investing and ESG:
  <https://www.tsiconsultancy.com/impact-investing-and-esg/>
- Rimm Sustainability: <https://rimm.io/>
- Rimm myCSO Platform: <https://rimm.io/mycso-platform-compliance/>
- Rimm Sustainability Report 2024:
  <https://rimm.io/wp-content/uploads/2025/10/Rimm_SR_2024.pdf>
- Impact Institute — Impact Consulting:
  <https://www.impactinstitute.com/impact-consulting/>
- ImpactMapper — Consulting Service:
  <https://www.impactmapper.com/consulting-service>
- Impact ROI — Services: <https://www.impactroiglobal.com/services/>
- Holtara — Impact-Focused ESG Services:
  <https://www.holtara.com/strategy-and-transformation/impact-positive-solutions/>
- Wellington — IMM approach:
  <https://www.wellington.com/en-us/institutional/sustainability/our-approach-to-imm>
- Tideline — Services overview and Impact Management Compass:
  <https://tideline.com/> and <https://tideline.com/services/>
- Tideline — Impact Verification (BlueMark spin-out):
  <https://tideline.com/services/impact-verification/>
- BlueMark — three-pillar verification methodology and ILPA partnership:
  <https://bluemark.co/> and
  <https://bluemark.co/bluemark-and-tideline-to-partner-with-ilpa-to-bring-impact-investing-tools-and-insights-to-limited-partners/>
- Holtara — Impact-focused services (one-stop-shop, six service lines):
  <https://www.holtara.com/solutions/impact/>
- Impact Institute — Impact Due Diligence brochure (Light / Mid / Full
  modular IWA-based DD, Impact Investor Tool):
  <https://www.impactinstitute.com/wp-content/uploads/Impact_Due_Diligence_Website_Download-1.pdf>
- ImpactMapper — Reports + Advisement + Software trio, Responsible AI:
  <https://www.impactmapper.com/>
- ImpactVC (Better Society Capital) — open-source VC and Founders Playbooks:
  <https://www.impactvc.co/>
- Sopact — "Theory of Change" 2026-04 essay arguing the consultation-driven
  era is over: <https://www.sopact.com/use-case/theory-of-change>
- Tideline / Impact Alpha — Impact value-creation playbooks for alpha:
  <https://impactalpha.com/the-xs-and-os-of-impact-how-impact-value-creation-playbooks-can-generate-alpha/>
- Watershed — audit-grade carbon platform with Product Footprints AI:
  <https://watershed.com/>
- EvalCommunity Academy — AI-powered Theory of Change & Logframe Builder
  (intervention logic, indicators, MOV, assumptions):
  <https://academy.evalcommunity.com/tools/ai-powered-theory-of-change-and-logframe-builder/>

---

## 9. Amendment Notes (2026-05-02)

This amendment (vs. the 2026-05-01 original) adds:

1. **Tideline + BlueMark** signal section and a 3-pillar verification track
   (new Track 10) so v4 explicitly sells the verification bundle LPs already
   ask for.
2. **Holtara, Impact Institute, ImpactMapper, ImpactVC** signal section to
   capture the one-stop-shop / modular DD / playbook patterns already proven
   in market.
3. A **direct response to Sopact's "consultation-driven ToC is over"
   argument** — v4 must position the consultant-curated, evidence-bound,
   audit-logged ToC as the differentiator, plus add persistent stakeholder
   identity as a defensive feature.
4. A **Codebase Reuse Map (Section 4)** that lists every v3 module the new
   v4 surface should reuse. Engineering rule: no re-implementation of an
   existing module; v4 work lives in `impact/engagements/`,
   `tools/impact/engagement_*`, and `frontend/`.
5. **Engagement-Type Bundles (Section 4a)** — a productised service catalog
   (Strategy, DD-Light/Mid/Full, ESG Baseline, Annual Report, LP DDQ,
   Verification, Exit / VDD, Regulatory, Stakeholder Voice, Training) that
   maps each engagement to the existing tools that should be wired together.
6. A new **Regulatory Compliance Workbench (Track 9)** wrapping the existing
   SFDR, SDR, SEC, CSRD/ESRS, ISSB modules into a jurisdiction-aware wizard.
7. **Wave 5** in the implementation plan and four new success metrics
   covering bundle adoption, regulatory coverage, verifier handoff, reuse
   discipline, and persistent stakeholder identity.
