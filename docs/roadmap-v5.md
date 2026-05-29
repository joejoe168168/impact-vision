# Impact Vision — Roadmap v5.0

**Date:** 2026-05-29  
**Status:** Regulatory Currency, Frontier Measurement & Decision-Useful Reporting — planning + in-progress build  
**Audience:** product, engineering, fund managers, project owners, impact consultants, LPs  
**Thesis:** v4 shipped the consultant engagement layer; the discrete capability
set (IRIS+, 5D, SDG, 10+ frameworks, evidence graph, audit trail, verification
workspace, LP narrative, engagement suite) is broad and mature. v5 is **not** a
re-implementation wave. It is a **currency + frontier + polish** wave with three
jobs:

1. **Stay legally current** — the EU "Omnibus I" simplification became *law*
   (Directive (EU) 2026/470, in force 18 March 2026) and materially changed who
   reports under CSRD/CSDDD and on what timeline. Our registry still treats it
   as a draft.
2. **Adopt the frontier measurement methods** institutional LPs are now asking
   for — monetary impact accounting (IFVI/VBA), welfare-based comparison
   (GIIN Impact Quantifier / QALYs), gender-lens (2X Criteria), and the emerging
   social-disclosure architecture (TISFD).
3. **Make the deliverable decision-useful** — unify on the modern report chrome,
   reach WCAG 2.2 AA, and surface the evidence-provenance moat we already have
   (evidence graph + audit trail) directly in the report.

Engineering rule (unchanged from v4): if a capability has a backing module,
the v5 ticket is *extend/wrap*, not *fork*. New code lives in
`impact/frameworks/`, `impact/` (new engine modules), `tools/impact/`,
`impact/report_templates/`, and `frontend/`.

---

## 1. Market & Regulatory Signals (2026)

### 1.1 EU Omnibus I is now law — CSRD/CSDDD scope and timeline changed

**Directive (EU) 2026/470** ("Omnibus I") was published 26 Feb 2026 and entered
into force **18 March 2026**, significantly narrowing both the CSRD and the
CSDDD.

- **CSRD scope cut ~80%.** Mandatory reporting now requires **>1,000 employees
  AND >€450M net turnover** (cumulative). Listed SMEs and most former Wave 2/3
  entities fall out of scope. Non-EU groups: >€450M EU turnover with an in-scope
  EU subsidiary/branch.
- **Stop-the-clock / pause.** Former Wave 1 reporters that no longer meet the
  thresholds may pause FY2025–FY2026 reporting (subject to national
  transposition). Wave 2 effectively delayed to FY2027 (reports due 2028).
- **Simplified ESRS** delegated act targeted for **September 2026**, applying
  from **FY2027**; sector-specific ESRS removed; stronger rights to withhold
  commercially prejudicial information.
- **CSDDD** application pushed to **26 July 2029**, scope narrowed to **>5,000
  employees + €1.5B turnover**, climate transition-plan *obligation* removed,
  fines capped at 3% of net global turnover. MS transposition by 26 July 2028.
- **VSME** (EFRAG Voluntary SME standard) becomes the de-facto reporting ask for
  the many investee SMEs now outside mandatory scope but still receiving
  bank/investor/customer data requests.

**Impact for us:** `standards_registry.py` references an *"ESRS Omnibus Draft"*;
`regulatory_packs.py` and `engagements/regulatory.py` describe CSRD/CSDDD on the
old basis. These must reflect final law plus an **"are you still in scope?"**
decision tree, because that is the first question every EU-touching fund and
investee will ask in 2026–2027.

### 1.2 IFVI / VBA monetary impact accounting

The International Foundation for Valuing Impacts (IFVI, with the Value Balancing
Alliance) released **Interim Methodologies** (Air Pollution, Land Use &
Conversion, Waste, Water Pollution), a **GHG Topic Methodology**, and a **Global
Value Factor Database (~100,000 value factors)** in 2024–2025. Impact accounting
— monetising social/environmental outcomes so they sit on one ledger with
financial return — is the fastest-rising institutional methodology
(Impact-Weighted Accounts lineage, Serafeim/Cohen).

**Impact for us:** we have `fund_analytics.impact_weighted_returns_stub` (a
stub) and `sroi.py`. We have no value-factor-based monetisation. This is a clear
frontier addition.

### 1.3 GIIN Impact Lab — Impact Quantifier (QALYs) + Impact Target Setter

GIIN's Impact Lab launched two open-source tools:

- **Impact Quantifier** — converts **breadth × depth × theme × geography** into
  **Quality-Adjusted Life Years (QALYs) / lives improved**, enabling cross-sector
  portfolio comparison on a human-welfare basis (input from 94 organisations).
- **Impact Target Setter** — sets context-driven impact targets from geography,
  capital deployed, and theme, aligned to SDGs and IRIS+.

GIIN also maintains **Impact Performance Benchmarks** (agriculture, clean energy,
financial inclusion, forestry, healthcare) for peer- and SDG-need-contextualised
performance.

**Impact for us:** we have `external_benchmarks.py` (Compass peer quartiles) and
SDG/5D scoring, but no welfare (QALY) quantifier, no context-driven target
setter, and no GIIN performance-benchmark provider.

### 1.4 TISFD — Taskforce on Inequality and Social-related Financial Disclosures

Launched late 2024 (CalPERS, PRI, Manulife, AXA, ING, Generation IM, unions,
NGOs). First **beta draft framework** released for consultation (open to
31 July 2026), structured like TCFD/TNFD (governance / strategy / risk
management / metrics & targets), covering **financial materiality + impact
materiality** of people-related issues (pay, labour conditions, freedom of
association, community, human rights, inequality). Designed to be ISSB/GRI/ESRS
compatible. Final framework due 2027.

**Impact for us:** we have TCFD + TNFD but no social sibling. A
forward-looking TISFD readiness module lets funds pilot early and positions us
ahead of 2027 adoption.

### 1.5 2X Criteria — gender-lens investing standard

2X Global's **2X Criteria** is the global standard for gender-lens investing
(Entrepreneurship / Leadership / Employment / Supply Chain / Products & Services
/ Portfolio / ESG & Governance "minimum requirements"). We carry gender keywords
but no structured 2X assessment.

### 1.6 ILPA / Tideline / Campbell Lutyens — "State of Market Institutionalization" (Jan 2026)

Institutional LPs rate impact data/infrastructure **2.7 / 5**. The single
biggest barrier to institutionalization is **data**: fragmented, non-comparable
impact-outcome data and either *too much* or *too little* coming from GPs. LPs
want harmonized standards, **practitioner-oriented playbooks**, peer
benchmarking, and **third-party assurance**. This validates our v3 trust moat
and points squarely at comparability + benchmarking + assurance-grade reporting.

### 1.7 2026 reporting UX consensus

Investor-grade ESG/impact reporting in 2026 converges on:

- **Dual pathway** — interactive web report + tagged archival PDF (PDF/UA).
- **WCAG 2.2 AA** — ≥4.5:1 contrast, keyboard nav, alt-text on every chart,
  **patterns/labels not color-only** (color-blind safe).
- **Progressive disclosure** — hover/drill-down to manage cognitive load.
- **Clean 2D charts**, consistent color/typography, labeled axes, no 3D/decoration.
- **Data verifiability** — every visual links back to source/audited data.
- **Stakeholder filtering** — toggle the lens (LP / regulator / community / IC).
- **Mobile-first**; **machine-readable** CSV/structured export for analysts.

---

## 2. v5 North Star

**Impact Vision should be the impact workbench that is always legally current,
speaks the institutional LP's frontier-measurement language, and produces a
deliverable that an LP, a regulator, and an independent verifier can all trust at
a glance — because every number links to evidence.**

---

## 3. Product Principles (v5 additions)

- **Currency is a feature.** Regulatory modules carry an explicit `as_of` date,
  legal citation, and "scope decision" logic, not just static keyword lists.
- **Comparability over cleverness.** New measurement methods (QALY, monetary
  valuation, 2X) must roll up to portfolio level and be peer-contextualised.
- **Provenance in the pixel.** If a number appears in a report, its evidence
  (source, confidence, reviewer decision) is one hover/click away.
- **Accessible by default.** Every emitted HTML/PDF meets WCAG 2.2 AA; color is
  never the only signal.
- **Forward-compatible.** Pilot emerging standards (TISFD, simplified ESRS)
  behind clear "beta / draft" labels so funds can prepare without overclaiming.

---

## 4. Codebase Reuse Map (v3/v4 → v5 delta)

| v5 capability | Existing backing | New v5 work |
|---|---|---|
| Omnibus I currency | `standards_registry.py`, `regulatory_packs.py`, `engagements/regulatory.py`, `csrd_wizard.py` | Final thresholds/dates, CSDDD revision, in-scope decision tree |
| VSME voluntary standard | `frameworks/esrs.py`, `framework_tool.py` | New `frameworks/vsme.py` + `framework_assess` mode |
| CSDDD / HRDD | DD checklist supply-chain category, `risk_opportunity.py` | New `impact/hrdd.py` (salient issues, value-chain, grievance, remediation) + tool |
| Monetary impact valuation | `fund_analytics.impact_weighted_returns_stub`, `sroi.py` | New `impact/impact_valuation.py` (IFVI value factors) + `impact_valuation` tool |
| Welfare quantifier (QALY) | `five_dimensions.py`, `sdg_mapper.py`, `benchmarks.py` | New `impact/impact_quantifier.py` + `impact_quantifier` tool |
| Impact target setter | `fund_thesis.py`, `monitoring.py`, `decision_workflow_tool.py` | Target-setting helper + `decision_workflow` action |
| 2X gender-lens | gender keywords in `sdg_keywords.yaml` | New `frameworks/two_x.py` + `framework_assess` mode |
| TISFD readiness | `frameworks/tcfd.py`, `frameworks/tnfd.py` pillar pattern | New `frameworks/tisfd.py` + `framework_assess` mode |
| GIIN performance benchmarks | `external_benchmarks.py`, `engagements/value_creation.BenchmarkProvider` | New seeded provider + benchmark lookup |
| Report chrome unification | `report_templates/report_v2.py`, `impact_report_tool._to_html` | Migrate flagship report onto v2 chrome |
| Accessibility | `report_v2.REPORT_CSS_V2` | WCAG 2.2 AA: contrast, ARIA, alt-text, patterns, focus states |
| Evidence provenance UI | `evidence_graph.py`, `audit_trail.py`, `metric_records.py` | Inline provenance badges/tooltips in report sections |

---

## 5. Tracks

### Track A — Regulatory Currency (P0/P1/P2)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| A1 | EU Omnibus I update: final CSRD/CSDDD thresholds + dates in `standards_registry`, `regulatory_packs`, `engagements/regulatory`; CSDDD revision; **`assess_eu_omnibus_scope`** decision tree (in/out of CSRD, pause eligibility, VSME fallback) | Critical | M | **Done** — registry now cites Directive (EU) 2026/470; new `EU-CSDDD` pack + CSDDD standard; `assess_eu_omnibus_scope` wired into `engagement_suite` (action `assess_eu_omnibus_scope`) |
| A2 | VSME voluntary SME standard: Basic + Comprehensive modules, B/C disclosure datapoints, `framework_assess` mode | High | M | **Done** — `frameworks/vsme.py` (B1-B11 + C1-C9, 20 disclosures) + `framework_assess` `vsme` mode (`category=basic\|comprehensive`) |
| A3 | CSDDD / HRDD workflow: salient human-rights issues, value-chain tiers, grievance mechanism, remediation tracker, OECD/UNGP alignment | Medium | L | **Done** — `impact/hrdd.py` (UNGP salience ranking with gross-risk escalation, value-chain tier mapping, UNGP P31 grievance score, remediation state machine, OECD 6-step coverage, CSDDD readiness band) + `hrdd_assess` tool (`assess`, `seed_from_text`) |

### Track B — Frontier Impact Measurement (P1/P2)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| B1 | IFVI monetary impact valuation: seeded value-factor catalogue (GHG, air, water, land, waste, wages, health), monetise outcomes, net impact, **impact ratio** vs financial return; promote the `impact_weighted_returns_stub` | High | L | **Done** — `impact/impact_valuation.py` (value factors → net monetary impact, benefit/cost ratio, impact intensity, impact-weighted return / IMM) + new `impact_valuation` tool; `fund_analytics` stub now computes a real impact-weighted IRR |
| B2 | GIIN Impact Quantifier (QALY): breadth × depth × theme × geography → QALYs / lives improved; portfolio roll-up | Medium | M | **Done** — `impact/impact_quantifier.py` (breadth×depth×theme×geography×duration×additionality → QALYs + lives improved, cost-per-QALY, monetised welfare, portfolio roll-up by theme/geography) + `impact_quantifier` tool |
| B3 | 2X Criteria gender-lens screener: 7 dimensions + minimum requirements; pass/qualify output; SDG 5 link | High | M | **Done** — `frameworks/two_x.py` (6 dimensions + mandatory governance/GBVH minimum requirements) + `framework_assess` `two_x` mode |
| B4 | TISFD readiness: 4-pillar (gov/strategy/risk/metrics) social-disclosure self-assessment; ISSB/GRI/ESRS crosswalk; explicit beta label | Medium | M | **Done** — `frameworks/tisfd.py` (13 beta disclosures across 4 pillars, keyword-driven readiness, GRI/ESRS crosswalk, explicit beta notice) + `framework_assess` `tisfd` mode |
| B5 | Impact Target Setter: context-driven target ranges from theme/geography/capital; wired into thesis + monitoring | Medium | M | **Done** — `impact/impact_target_setter.py` (theme×geography×capital → conservative/base/stretch IRIS+/SDG target ranges + annual trajectory) wired into `decision_workflow` (`action='set_targets'`) |

### Track C — Benchmarking & Data Comparability (P1)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| C1 | GIIN Impact Performance Benchmark provider: seeded sector KPI quartiles (ag, clean energy, financial inclusion, forestry, healthcare) behind the existing `BenchmarkProvider` protocol | High | M | **Done** — `impact/giin_benchmarks.py` (13 sector KPI distributions + SDG-need framing + `contextualise_kpi`) + `GIINImpactBenchmarkProvider`; wired into `engagement_suite` (`benchmark provider="giin"`, `list_giin_benchmarks`, `giin_kpi_context`) |
| C2 | Investee data-collection front-end (frontend/): guided questionnaire with validation, PAI plain-language translation, "why we need this" feedback loop | Medium | L | **Done** — `impact/investee_portal.py` emits a self-contained, offline, single-file HTML portal (guided questionnaire, client-side validation, SFDR PAI plain-language rewrites, per-field "why we ask", progress bar, WCAG 2.2 AA structure, local JSON export) + `investee_portal` tool (`generate`/`schema`). Shipped as a generated single-file portal rather than a React SPA, consistent with the project's HTML-deliverable pattern. |

### Track D — Decision-Useful Reporting & Deliverable UX (P0)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| D1 | Unify flagship `impact_report._to_html` on the `report_v2` chrome (sticky TOC, KPI strip, print CSS, callouts/pills) | Critical | M | **Partial** — shared `report_v2` chrome upgraded (skip link, `<main>` landmark, dark-mode `theme` param, reusable `render_provenance_badge`/`render_evidence_legend`); flagship `_to_html` brought to a11y/provenance parity additively rather than a risky full rewrite (flagship keeps its richer interactive chrome) |
| D2 | WCAG 2.2 AA pass: contrast tokens, ARIA roles/landmarks, chart alt-text + table fallback, keyboard focus states, **pattern + label, not color-only** | Critical | M | **Done** — flagship report + `report_v2` now ship a skip link, `<main>` landmark, `aria-label`ed nav, `role="img"`+alt-text on every Plotly chart (with adjacent data table fallback), keyboard-operable (`role="button"`/`tabindex`/Enter+Space/`aria-expanded`) 5D, SDG and claim disclosure rows, focus-visible outlines, and a `prefers-reduced-motion` guard |
| D3 | Inline evidence-provenance badges: per-metric/section badge linking source + confidence + reviewer decision (evidence graph / audit trail) | Critical | M | **Done** — `.evidence-badge` component (verified / reported / estimated / proxy / unverified / suggested) with label-not-color-only styling + accessible tooltip; wired into the 5D table's score-provenance column with a legend; `render_provenance_badge()`/`render_evidence_legend()` exported from `report_templates` for reuse across IC memo + DD report |
| D4 | Audience filter toggle (LP / IC / regulator / public) reusing `reporting_studio` multi-audience hints | High | M | **Done** — accessible toolbar (`role=group`, `aria-pressed`) + section-to-audience map + JS that segments the report by `<h2>` and shows/hides per lens; `audience` report input pre-selects the lens; hidden in print |
| D5 | Uncertainty visualization: confidence intervals / error bars where bands exist (emission factors, Bayesian) | Medium | S | **Done** — provenance-derived confidence band rendered as an accessible error-bar (`role=img` + alt-text) in the tear sheet (evidence-based→narrow, partial→moderate, estimated→wide), clearly labelled as illustrative |
| D6 | Executive one-pager / LP tear sheet (single-screen) | High | S | **Done** — `_render_tear_sheet` "At a glance" block (grade, score+uncertainty band, top SDGs, greenwashing risk, sector percentile, claim count) with `page-break-after` for a clean one-page PDF |
| D7 | PDF/UA tagging + bookmarks in `_to_pdf`; dark mode + white-label theme tokens (`branding.py`) | Medium | M | **Done** — `_to_pdf` now writes a tagged **PDF/UA-1** document (WeasyPrint `pdf_variant`, graceful fallback) with heading bookmarks; flagship report gains a `theme="dark"` palette and wires the existing `branding.py` white-label tokens via a `branding` input |

### Track E — Risk & Governance (P2)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| E1 | Climate scenario risk module: NGFS-style physical/transition scenarios with portfolio exposure | Medium | L | **Done** — `impact/climate_scenario.py` (7 NGFS scenarios across orderly/disorderly/hot-house/too-little-too-late × sector transition & physical sensitivities → portfolio-weighted exposure, combined score, illustrative VaR, most-exposed holdings) + `climate_scenario_risk` tool |
| E2 | AI governance artifact for our own extraction: model card, data lineage, human-oversight log (EU AI Act-aware), extend `copilot.py` | Medium | M | **Done** — `impact/ai_governance.py` (model card, per-artefact data lineage, human-oversight log assembled from the copilot review queue, EU AI Act risk classification + obligation checklist) + `ai_governance` tool; builds on `engagements/copilot.py` |

---

## 6. Build Order (one-by-one)

1. **Roadmap doc** (this file). ✅
2. **A1 — Omnibus I currency** (legal currency; nothing else should ship stale law).
3. **D1 + D2 + D3 — report unification, accessibility, provenance** (every other
   output flows through the report).
4. **A2 — VSME** (most-requested investee standard post-Omnibus).
5. **B1 — IFVI monetary valuation** (promote the stub; LP-frontier).
6. **B3 — 2X Criteria** (discrete, high-demand, low risk).
7. **C1 — GIIN benchmark provider** (comparability).
8. **B2 / B4 / B5 — QALY quantifier / TISFD / target setter.** ✅
9. **A3 — CSDDD/HRDD; E1/E2 — risk & AI governance.** ✅
10. **C2 + frontend UX — data-collection portal, web report polish.** ✅

> **Status (2026-05-29):** all v5 tracks are now **Done** except D1, which was
> intentionally delivered additively (a11y + provenance + dark mode + audience
> filter + tear sheet were layered onto the flagship report rather than
> rewriting it onto the `report_v2` chrome, to avoid a risky migration).

After each track: register any new tool in `create_default_tool_registry()`
and `tools/impact/__init__.py`, run `scripts/check_imports.py --all`,
`ruff check src/`, and the relevant `pytest` subset; update README tool table +
count and `CHANGELOG.md`.

---

## 7. Success Metrics

- **Currency:** EU regulatory modules carry `as_of >= 2026-03-18` and cite
  Directive (EU) 2026/470; a fund can answer "am I in CSRD scope?" in one call.
- **Frontier adoption:** monetary impact value, QALYs, and a 2X flag all roll up
  to portfolio level alongside existing 5D/SDG scores.
- **Comparability:** ≥5 sectors have peer-benchmark context available to DD.
- **Accessibility:** flagship HTML report passes automated WCAG 2.2 AA checks
  (contrast, alt-text, landmarks) and a keyboard-only walkthrough.
- **Provenance:** ≥90% of report metrics show an evidence/confidence badge.
- **No regressions:** import smoke + ruff + full pytest stay green; zero new
  modules duplicate an existing one (Codebase Reuse Map enforced in review).

---

## 8. Sources Reviewed (2026)

- Directive (EU) 2026/470 ("Omnibus I") — entry into force 18 Mar 2026; CSRD/CSDDD
  scope and timeline changes (DLA Piper, Gibson Dunn, Arendt, Simont Braun,
  financialregulations.eu summaries).
- International Foundation for Valuing Impacts (IFVI) — Interim Methodologies,
  GHG Topic Methodology, Global Value Factor Database: <https://ifvi.org/>
- GIIN Impact Lab — Impact Quantifier (QALYs) + Impact Target Setter:
  <https://thegiin.org/publication/research/flm-tools/> and
  <https://thegiin.org/publication/opinion/centering-human-well-being-in-impact-investing-introducing-the-impact-quantifier/>
- GIIN Impact Performance Benchmarks: <https://thegiin.org/benchmarks/>
- TISFD — beta draft framework + consultation:
  <https://www.morganlewis.com/blogs/finreg/2025/01/tisfd-a-new-framework-for-inequality-and-social-related-financial-disclosures>
- 2X Global — 2X Criteria (gender-lens standard).
- ILPA / Tideline / Campbell Lutyens — "Impact Investing: The State of Market
  Institutionalization" (Jan 2026).
- 2026 ESG/impact report design + accessibility (WCAG 2.2 AA, dual-pathway,
  data verifiability, progressive disclosure) — The Ethical Agency, Inkbot Design.
