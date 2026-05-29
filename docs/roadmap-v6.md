# Impact Vision — Roadmap v6.0

**Date:** 2026-05-29
**Status:** Comparable, Assured & Connected — planning
**Audience:** product, engineering, fund managers, project owners, impact
consultants, LPs, verifiers
**Thesis:** v3 built the trust infrastructure, v4 built the consultant
engagement layer, and v5 made us **legally current**, **frontier-measurement
capable**, and **decision-useful** (Omnibus I, IFVI valuation, QALYs, 2X,
TISFD, target setter, accessible/provenance-aware reports). The capability set
is now exceptionally broad. v6 is therefore **not** a re-implementation wave —
it is the **"comparable, assured, and connected"** wave with four jobs:

1. **Be comparable & machine-readable.** The single biggest barrier LPs cite to
   institutionalisation is *data* — fragmented, non-comparable, human-only.
   v6 makes our outputs **interoperable** (one assessment → ISSB / ESRS / GRI /
   IRIS+) and **machine-readable** (XBRL / iXBRL digital tagging), and scores
   data **comparability** explicitly.
2. **Be assurance-grade.** Sustainability assurance is going global
   (**ISSA 5000**, effective Dec 2026; CSRD limited→reasonable; CA limited
   assurance). v6 turns our evidence graph + audit trail into an **ISSA 5000
   engagement-ready** package.
3. **Track the fast-moving frontier.** The labelling, nature, carbon and social
   frontiers all moved in 2025–26: **SFDR 2.0** (a labelling regime),
   **SBTN science-based targets for nature** + **biodiversity credit
   integrity**, **carbon-credit integrity** (ICVCM CCP / VCMI / Article 6),
   **Just Transition metrics**, and the maturation of **outcomes-based /
   impact-linked finance**. We extend, never fork, the modules that already
   touch these areas.
4. **Make the AI governed and self-updating.** Move from a static knowledge base
   to a **regulatory radar** (auto-detect framework changes), an **extraction
   eval/benchmark harness**, and **dMRV-grade evidence ingestion** (remote
   sensing / IoT / time series → evidence graph, hash-anchored).

Engineering rule (unchanged since v4): **if a capability has a backing module,
the v6 ticket is _extend / wrap_, not _fork_.** New code lives in
`impact/frameworks/`, `impact/` (new engine modules), `tools/impact/`,
`impact/report_templates/`, and `frontend/`. Every track below names the
existing module it builds on.

---

## 1. Market & Regulatory Signals (2026)

### 1.1 The market is institutionalising — and asking for comparable data

GIIN's **State of the Market 2025** puts surveyed impact AUM at **$448B**, a
**21% CAGR over six years** (4× the 5% growth of the same investors' total AUM);
the field has mobilised **>$1.5T** cumulatively. The defining shift is
*institutionalisation*: **pension funds now supply 35% of impact capital**
(growing ~47%/yr since 2019), market-rate-return targeting is up, and capital is
concentrating in "safer" stages and high-income geographies — even as the
largest five-year growth is expected in **South America, Western/Eastern/
Southern Africa, and Southeast Asia**, and **56%** plan to ramp energy.

Institutional capital brings institutional data demands. The recurring LP
complaint (ILPA / Tideline / Campbell Lutyens, Jan 2026) is that impact data is
**fragmented and non-comparable**. That is the centre of gravity for v6.

### 1.2 SFDR 2.0 — from disclosure regime to **labelling regime**

On **20 Nov 2025** the European Commission proposed a major SFDR overhaul
("SFDR 2.0"):

- **Three voluntary product categories** replace the Article 6/8/9 split:
  **Sustainable** (revised Art 9), **Transition** (new Art 7), **ESG Basics**
  (new Art 8). Each requires **≥70%** of the portfolio to follow the relevant
  ESG strategy (some Member States push for 80%).
- The legal **definition of "sustainable investment" is deleted** (it caused
  divergent interpretation).
- **Entity-level PAI disclosures removed**; product-level disclosures
  significantly cut and simplified.
- Each category carries **mandatory exclusions** (e.g. controversial weapons,
  tobacco, UNGC/OECD violators, coal-revenue thresholds).
- Co-legislator negotiations expected to begin **Sept 2026**; application likely
  **2028–2029**.

**Impact for us:** `frameworks/sfdr_pai.py` classifies Article 6/8/9 and
`regulatory_packs.py` carries an `EU-SFDR` pack on the old basis. Funds will
spend 2026–28 **mapping existing Art 8/9 products onto the new
Transition / Sustainable / ESG-Basics labels** and checking the 70% threshold +
exclusions. That mapper is a clear P0 currency item.

### 1.3 ISSB adoption widens + **ISSA 5000** makes assurance global

- **36 jurisdictions** have adopted or are implementing **IFRS S1/S2**
  (Chile, Qatar, Mexico mandatory from 1 Jan 2026; Hong Kong from 1 Aug 2025;
  Brazil phased from FY2026; Australia phasing; Japan from FY2027).
- **ISSA 5000** (IAASB) is the **global baseline for sustainability assurance**,
  effective for periods **beginning on/after 15 Dec 2026**, covering both
  voluntary and mandatory engagements.
- **CSRD** requires limited assurance now, path to reasonable; the **harmonised
  EU assurance standard is due 1 Jul 2027** (interim: CEAOB guidance + ISSA
  5000). Simplified **ESRS** (datapoints cut ~61%, ~1,100 → ~430) is due
  **Sept 2026**, applying from **FY2027**.

**Impact for us:** `assurance.py` builds ISAE 3000 / AA1000 packs and we have a
verification workspace (v3) + 3-pillar bundle (v4). An **ISSA 5000
engagement-readiness** layer (assertions, subject matter, evidence sufficiency,
limited-vs-reasonable gap) is the natural next step, and `frameworks/esrs.py` +
`csrd_wizard.py` need a simplified-ESRS refresh.

### 1.4 Machine-readable reporting & interoperability are now table stakes

- **CSRD digital tagging** (Inline XBRL / iXBRL against the **EFRAG ESRS XBRL
  taxonomy**) is mandatory for sustainability statements for FYs beginning on/
  after **1 Jan 2026**, extending the ESEF regime. The **ISSB published its own
  XBRL taxonomy**; **EFRAG↔ISSB digital interoperability** ("Concordance
  Project") is in flight.
- **GRI ↔ ISSB** and **ESRS ↔ ISSB** alignment work is reducing duplication so a
  company can "report once, satisfy many" (ISSB now positions its standards as a
  "global passport", removing the need for a separate interoperability guide).

**Impact for us:** we emit HTML / PDF / XLSX / CSV / JSON but **no XBRL/iXBRL**
and our `cross_reference.py` (59 concept mappings) is a lookup, not a
"report-once-map-to-many" concordance engine. Machine-readable export +
interoperability is the single highest-leverage answer to the LP comparability
complaint.

### 1.5 Nature moves from disclosure to **targets & credits**

- **SBTN** (Science Based Targets Network) is scaling science-based **targets
  for nature** (5-step Assess → Prioritise → Measure → Act → Track), with
  **V2 methods due mid-2026** and validated targets growing; directly serves
  **GBF Target 15**. TNFD's LEAP feeds SBTN and vice-versa.
- **Biodiversity credits**: the BCA / IAPB / WEF **21 High-Level Principles**
  + an **Assessment Matrix** define high-integrity credits (verified outcomes
  for nature, equity for people, good governance) — the nature analogue of
  carbon's CCPs, anchored to **GBF Target 19**.

**Impact for us:** we have `frameworks/tnfd.py` (disclosure), plus
`ecosystem_services.py` and `geospatial.py` (natural-capital valuation /
geo). We have **no nature target-setter** and **no biodiversity-credit
integrity screen**. Both extend existing nature modules.

### 1.6 Carbon-market integrity consolidates around ICVCM / VCMI / Article 6

- **ICVCM Core Carbon Principles** (10 science-based principles) are now the
  supply-side quality benchmark: **8 programs CCP-eligible**, **38 methodologies
  approved**, ~**105M credits** CCP-labelled, commanding **up to ~25% price
  premia**. **ICROA** is winding down in 2026, leaving CCPs as the reference.
- **VCMI Claims Code** now requires buyers to use **CCP-labelled or Article 6.4
  (PACM)** credits for credible claims.
- **dMRV** (remote sensing, IoT, automated pipelines) is shifting credits from
  static certificates to **data-backed, periodically updated** assets;
  tokenisation matters only when anchored to better data.

**Impact for us:** we have `climate_accounting.py`, `emission_factors.py`,
`climate_scenario.py` and a strong greenwashing engine — but **no carbon-credit
quality / offset-claim credibility screen**. A CCP/VCMI/Article-6 integrity
assessor plugs straight into the greenwashing + climate stack.

### 1.7 Just Transition gets measurable

Shift + Council for Inclusive Capitalism + WBA + WBCSD + LSE Just Transition
Finance Lab published **19 sector-agnostic Just Transition metrics** across
three stakeholder groups (own workforce, communities, value-chain workers) and
four pillars (governance / strategy / risk & impact / metrics & targets) —
outcome-focused: job security, reskilling & redeployment, **living wage**,
worker voice, community consent, supply-chain impact. Aligns with GRI 102
(Climate Change) and TISFD.

**Impact for us:** we have `worker_voice.py`, `stakeholder_voice.py`,
`frameworks/tisfd.py` (v5) and `hrdd.py` (v5) — a Just Transition module ties
the climate transition plan to people outcomes and is a tight fit.

### 1.8 US reality — California fills the federal vacuum

With the SEC climate rule effectively shelved, **California SB 253** (Climate
Corporate Data Accountability Act) and **SB 261** (Climate-Related Financial
Risk Act), amended by SB 219 and administered by **CARB**, are the binding US
regime: SB 253 (>$1B revenue, doing business in CA) → **Scope 1&2 by 10 Aug
2026**, Scope 3 from 2027, assurance phasing limited→reasonable; SB 261 (>$500M)
→ biennial TCFD/IFRS-S2-aligned climate-risk report (enforcement currently
stayed by a Ninth Circuit injunction). Many filers reuse existing TCFD/ISSB/CSRD
disclosures.

**Impact for us:** `regulatory_packs.py` has `US-SEC-ESG` but **no CA pack**;
add `US-CA-CLIMATE` with the scope thresholds + "doing business in CA" decision,
mapped to our existing TCFD/IFRS-S2 modules.

### 1.9 Agentic AI & dMRV reset the data baseline

The market is moving to **agentic, multi-agent ESG analysis** (hierarchical
agents for extraction, regulatory mapping, benchmarking, narrative — e.g.
ESGAgent academic work; commercial pipelines hitting **80%** carbon-data
automation). The differentiators are **traceability** (RAG + knowledge graph,
audit-ready outputs) and **governance** — exactly our evidence-graph + audit-
trail + v5 AI-governance moat. Two concrete pulls: **(a)** real-time
**regulatory change monitoring**, and **(b)** **dMRV** evidence streams.

**Impact for us:** we are already an agent with `ai_governance.py` (v5),
`copilot.py`, `evidence_workflow.py` and `signed_feed.py` (hash-chained
reports). v6 adds a regulatory radar, an extraction eval harness, and dMRV
evidence ingestion + verifiable anchoring.

### 1.10 Outcomes-based / impact-linked finance matures

Impact-linked finance / outcomes-based financing is institutionalising
(~26.6% projected CAGR; blended finance ~4× private-capital leverage), while
**SLBs stay subdued** (weak KPIs, immaterial step-ups) and **SLLs grow**
(~$160B in 2026). The credibility question is shifting to **KPI quality + payment
verification**.

**Impact for us:** `blended_finance.py` already designs impact-linked loans
(`ILLoanTerms`/`RateStep`), social-outcomes contracts (`SOCTerms`) and impact
carry. v6 adds **outcomes verification / payment-by-results tracking** and an
**SLB/SLL KPI-credibility scorer** (does the KPI capture core impact? is the
penalty material?).

---

## 2. v6 North Star

**Impact Vision should produce an impact assessment that an LP can compare
across a portfolio, a verifier can assure to ISSA 5000, and a regulator can
ingest by machine — because the same evidence-linked assessment exports to ISSB,
ESRS, GRI and IRIS+ in both human- and machine-readable form, and because the AI
that produced it is governed, auditable, and keeps itself current.**

---

## 3. Product Principles (v6 additions)

- **Comparable by construction.** Every metric carries enough structure
  (unit, period, boundary, taxonomy ID) to be tagged, benchmarked, and rolled
  up; comparability is *scored*, not assumed.
- **Report once, satisfy many.** A single assessment maps to ISSB / ESRS / GRI /
  IRIS+ via a concordance engine; we never ask the user to re-enter the same
  datapoint per framework.
- **Machine-readable is a first-class output.** XBRL / iXBRL / structured JSON
  ship alongside the HTML/PDF, not as an afterthought.
- **Assurance-ready, not assurance-claiming.** We prepare the engagement
  package and flag the limited-vs-reasonable gap; we never assert assurance we
  cannot evidence.
- **Integrity over inventory for credits.** For carbon/biodiversity credits and
  SLB/SLL KPIs we score *quality/credibility*, never just count them.
- **The AI is governed and current.** Model cards, lineage, oversight logs
  (v5) plus a regulatory radar and an extraction eval harness; every emerging
  standard stays behind a clear "beta / draft / proposed" label.

---

## 4. Codebase Reuse Map (v3/v4/v5 → v6 delta)

| v6 capability | Existing backing | New v6 work (extend, don't fork) |
|---|---|---|
| SFDR 2.0 labelling | `frameworks/sfdr_pai.py`, `regulatory_packs.EU-SFDR`, `engagements/regulatory.py` | Category classifier (Transition/Sustainable/ESG-Basics), 70% threshold + exclusion check, Art 8/9 → category migration map |
| Simplified ESRS + EU Taxonomy refresh | `frameworks/esrs.py`, `csrd_wizard.py`, `frameworks/eu_taxonomy.py`, `standards_registry.py` | Sept-2026 simplified-ESRS datapoint set (~430), `as_of` refresh |
| CA SB 253 / SB 261 | `regulatory_packs.py`, `frameworks/tcfd.py`, `frameworks/issb_ifrs_s2.py`, `regulatory_calendar.py` | `US-CA-CLIMATE` pack + scope decision (>$1B/$500M, "doing business in CA") |
| ISSA 5000 assurance readiness | `assurance.py`, `verification_workspace.py`, `engagements/verification_bundle.py`, `evidence_graph.py`, `audit_trail.py` | ISSA 5000 engagement checklist, evidence-sufficiency scoring, limited↔reasonable gap report |
| XBRL / iXBRL digital tagging | `issb_reporting.py`, `frameworks/esrs.py`, `metric_records.py`, `impact_report_tool.py` | ESRS + ISSB XBRL taxonomy tagging; iXBRL/JSON machine-readable export |
| Interoperability / concordance | `frameworks/cross_reference.py` (59 maps), `metric_records.py` | "Report-once-map-to-many" engine: ISSB↔ESRS↔GRI↔IRIS+ datapoint concordance + gap report |
| SBTN targets for nature | `frameworks/tnfd.py`, `ecosystem_services.py`, `geospatial.py`, `impact_target_setter.py` | 5-step SBTN readiness + science-based nature target ranges (pressure-based) |
| Biodiversity credit integrity | `ecosystem_services.py`, `greenwashing_reviewer.py` | IAPB/BCA 21 High-Level-Principles credit-quality screen |
| Carbon credit integrity | `climate_accounting.py`, `emission_factors.py`, `greenwashing.py`, `greenwashing_reviewer.py` | ICVCM CCP + VCMI Claims Code + Article 6.4 offset-claim credibility screen |
| Just Transition metrics | `worker_voice.py`, `stakeholder_voice.py`, `frameworks/tisfd.py`, `hrdd.py`, `climate_scenario.py` | Shift 19-metric assessment across 3 stakeholder groups + living-wage gap |
| Outcomes / impact-linked finance verification | `blended_finance.py`, `monitoring.py`, `metric_records.py` | Payment-by-results tracker + SLB/SLL KPI-credibility scorer |
| Regulatory radar (governed AI) | `standards_registry.py`, `regulatory_calendar.py`, `ai_governance.py`, `evidence_workflow.py` | Change-detection over tracked standards + impact-on-portfolio alerts |
| Extraction eval / benchmark harness | `extractors/`, `ai_governance.py`, `evidence_workflow.py` | Gold-set eval, accuracy/precision metrics, model-card auto-population |
| dMRV evidence ingestion + anchoring | `signed_feed.py`, `geospatial.py`, `evidence_graph.py`, `metric_records.py` | Time-series/remote-sensing evidence ingest + hash-anchored verifiable claim |
| Portfolio comparability & interactive report | `portfolio_rollup.py`, `portfolio_nlq.py`, `external_benchmarks.py`, `giin_benchmarks.py`, `report_templates/report_v2.py` | Multi-company interactive portfolio report + data-comparability score |

---

## 5. Tracks

> Status legend: **Planned** (not started). Priorities: P0 (currency/critical),
> P1 (high), P2 (frontier/medium). Effort: S/M/L.

### Track A — Regulatory Currency & Labelling (P0/P1)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| A1 | **SFDR 2.0 category classifier** — Transition / Sustainable / ESG-Basics, 70% threshold check, mandatory-exclusion screen, and an **Art 8/9 → new-category migration map**; explicit "proposed law" label | Critical | M | Planned |
| A2 | **Simplified ESRS refresh** — Sept-2026 reduced datapoint set (~430), update `frameworks/esrs.py` + `csrd_wizard.py` + `standards_registry` `as_of`; EU Taxonomy simplification refresh | High | M | Planned |
| A3 | **California SB 253 / SB 261 pack** — `US-CA-CLIMATE` regulatory pack + scope decision tree (revenue thresholds, "doing business in CA"), mapped to existing TCFD / IFRS S2; deadline calendar entries | High | M | Planned |
| A4 | **ISSB adoption tracker refresh** — jurisdiction status (36+), effective dates, assurance posture; surfaced via `regulatory_calendar` | Medium | S | Planned |

### Track B — Assurance & Machine-Readable Data (P0/P1)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| B1 | **ISSA 5000 engagement-readiness** — extend `assurance.py`: management assertions ↔ subject matter ↔ evidence-sufficiency scoring; **limited-vs-reasonable gap report**; wire to verification workspace + 3-pillar bundle | Critical | L | Planned |
| B2 | **XBRL / iXBRL digital tagging export** — tag the assessment against the **ESRS XBRL** + **ISSB XBRL** taxonomies; emit iXBRL + structured JSON from `issb_reporting` / report tool | Critical | L | Planned |
| B3 | **Interoperability / concordance engine** — promote `cross_reference` to a "report-once-map-to-many" mapper (ISSB ↔ ESRS ↔ GRI ↔ IRIS+ datapoint concordance) with a coverage/gap report | High | M | Planned |
| B4 | **Data comparability score** — per-metric structure completeness (unit/period/boundary/taxonomy ID) → portfolio comparability index; LP-facing | High | M | Planned |

### Track C — Frontier Instruments & Integrity (P1/P2)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| C1 | **Carbon-credit integrity screen** — ICVCM **Core Carbon Principles** (10) + **VCMI Claims Code** + **Article 6.4** eligibility → offset-claim credibility score; integrate with greenwashing engine | High | M | Planned |
| C2 | **Biodiversity-credit integrity screen** — IAPB/BCA/WEF **21 High-Level Principles** + Assessment Matrix → credit-quality band (verified nature outcomes / equity / governance) | Medium | M | Planned |
| C3 | **SBTN science-based targets for nature** — 5-step (Assess → Prioritise → Measure → Act → Track) readiness + pressure-based target ranges; GBF Target 15 link; reuse `impact_target_setter` pattern | Medium | L | Planned |
| C4 | **Outcomes / impact-linked finance verification** — payment-by-results tracker on `blended_finance` deals + **SLB/SLL KPI-credibility scorer** (core-impact relevance + penalty materiality) | Medium | M | Planned |

### Track D — Social Frontier (P2)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| D1 | **Just Transition assessment** — Shift **19 metrics** across own-workforce / communities / value-chain workers and 4 pillars; ties climate transition plan (`climate_scenario`) to people outcomes (`worker_voice`, `hrdd`, `tisfd`) | Medium | M | Planned |
| D2 | **Living-wage gap analyser** — wage vs local living-wage benchmark by geography; feeds Just Transition + 2X + S-pillar | Medium | M | Planned |
| D3 | **TISFD disclosure builder** — turn the v5 TISFD readiness into a drafted disclosure (governance/strategy/risk/metrics) with GRI/ESRS crosswalk; keep "beta" label | Low | S | Planned |

### Track E — Governed, Self-Updating AI (P1/P2)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| E1 | **Regulatory radar** — change-detection over tracked standards (`standards_registry`) with "what changed + who's affected in your portfolio" alerts; cite-and-summarise | High | M | Planned |
| E2 | **Extraction eval / benchmark harness** — gold-set + accuracy/precision/recall metrics for our extractors; auto-populate the v5 model card; regression-gate extraction changes | High | M | Planned |
| E3 | **dMRV evidence ingestion + anchoring** — ingest time-series / remote-sensing / IoT evidence into the evidence graph; hash-anchor a **verifiable impact claim** via `signed_feed` | Medium | L | Planned |

### Track F — Comparability & Portfolio Intelligence (P1)

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| F1 | **Multi-company interactive portfolio report** — portfolio roll-up + peer benchmarking + comparability score in one interactive HTML (reuse v5 report chrome: audience filter, dark mode, print/PDF) | High | L | Planned |
| F2 | **LP data-room export** — machine-readable portfolio export (XBRL/JSON + CSV) aligned to emerging LP data asks; build on `lp_ddq_export` + `data_room` | Medium | M | Planned |
| F3 | **Emerging-market / SDG-need context layer** — surface SDG-need + EM context (DFI lens) on portfolio metrics using `giin_benchmarks` + `sdg_taxonomy` | Low | S | Planned |

---

## 6. Build Order (one-by-one)

1. **Roadmap doc** (this file). ✅
2. **A1 — SFDR 2.0 classifier** (the question every EU fund will ask 2026–28;
   discrete, high demand).
3. **B3 — interoperability/concordance engine** (unlocks B2 + B4 + F2; directly
   answers the LP comparability complaint).
4. **B2 — XBRL/iXBRL export** (machine-readable deliverable; depends on B3).
5. **B1 — ISSA 5000 assurance readiness** (assurance is going global Dec 2026;
   high LP value).
6. **A2 / A3 / A4 — simplified ESRS, CA SB253/261, ISSB tracker** (currency
   batch, low risk).
7. **C1 — carbon-credit integrity** (plugs into greenwashing; high demand) then
   **C4 — outcomes/SLB-SLL credibility**.
8. **D1 / D2 — Just Transition + living wage** (social frontier; reuses TISFD +
   HRDD + worker voice).
9. **C2 / C3 — biodiversity credits + SBTN nature targets** (nature frontier).
10. **E1 / E2 — regulatory radar + extraction eval** (governed AI), then
    **F1 / F2 — portfolio report + LP data-room** (comparability payoff).
11. **E3 — dMRV ingestion + anchoring; D3 / F3** (frontier / polish).

After each track: register any new tool in `create_default_tool_registry()` and
`tools/impact/__init__.py`, run `scripts/check_imports.py --all`,
`ruff check src/`, and the relevant `pytest` subset; update the README tool
table + count and `CHANGELOG.md`. **No new module may duplicate an existing
one** — the Codebase Reuse Map (§4) is enforced in review.

---

## 7. Success Metrics

- **Comparability:** every emitted metric carries unit + period + boundary +
  taxonomy ID; a portfolio comparability index is reported, and ≥1 assessment
  exports cleanly to ISSB **and** ESRS from a single input.
- **Machine-readable:** the flagship assessment emits valid **iXBRL** against the
  ESRS and ISSB taxonomies (validates against the published schemas).
- **Interoperability:** the concordance engine maps an IRIS+/5D/SDG assessment
  to ISSB, ESRS and GRI with a coverage/gap report (no double data entry).
- **Assurance:** an assessment produces an **ISSA 5000 engagement-ready** pack
  with an explicit limited-vs-reasonable gap list.
- **Currency:** SFDR 2.0 categories, simplified ESRS (~430 datapoints), and CA
  SB 253/261 all carry an `as_of ≥ 2026` and a legal citation; a fund can map an
  Art 8/9 product to a new SFDR category in one call.
- **Integrity:** carbon and biodiversity credits, and SLB/SLL KPIs, receive a
  credibility/quality score (not just a count).
- **Governed AI:** the model card is auto-populated from a reproducible eval
  harness, and the regulatory radar flags ≥1 tracked-standard change with a
  portfolio impact note.
- **No regressions:** import smoke + ruff + full pytest stay green; zero new
  modules duplicate an existing one.

---

## 8. Explicitly Out of Scope / Deferred for v6

- **Re-implementing v3/v4/v5 capability.** v6 extends; it does not rebuild.
- **A full `report_v2` chrome migration of the flagship report.** v5 reached
  a11y + provenance + interactivity parity additively; a risky rewrite remains
  deferred unless a concrete need appears.
- **Running an on-chain registry / issuing tokens.** E3 anchors *evidence* and
  *claims* (hash/verifiable credential); we do not operate a blockchain or mint
  credits.
- **Acting as an accredited assurance provider.** B1 prepares the engagement
  package; assurance is performed by independent verifiers.
- **The `openharness` → `impact_vision` package rename** (see `CLAUDE.md`
  housekeeping) remains a separate, non-v6 refactor.

---

## 9. Sources Reviewed (2026)

- **GIIN — State of the Market 2025** (impact AUM $448B; 21% 6-yr CAGR; pension
  funds 35% of impact capital): <https://thegiin.org/> and the State of the
  Market 2025 PDF.
- **ILPA / Tideline / Campbell Lutyens** — "Impact Investing: The State of
  Market Institutionalization" (data is the #1 barrier).
- **SFDR 2.0** — European Commission proposal, 20 Nov 2025 (Transition /
  Sustainable / ESG-Basics categories; 70% threshold; "sustainable investment"
  definition deleted): Hogan Lovells, A&O Shearman Global FinReg Blog, Mondaq
  "SFDR 2.0 Engine Room" (Apr 2026), Council WK-487-2026.
- **ISSB adoption + ISSA 5000** — IAASB ISSA 5000 (effective 15 Dec 2026);
  ISSB adoption tracker (36 jurisdictions); CSRD limited→reasonable assurance,
  EU assurance standard due 1 Jul 2027; simplified ESRS (~430 datapoints, Sept
  2026): IAASB, riskpublishing/Socious trackers, ciferi CSRD 2026 guide.
- **Digital tagging / XBRL** — EFRAG ESRS Set 1 XBRL taxonomy; ESMA ESEF RTS for
  sustainability mark-up; IFRS Foundation ISSB XBRL taxonomy; XBRL International
  "Concordance Project".
- **GRI ↔ ISSB / ESRS ↔ ISSB interoperability** — IFRS Foundation + GRI joint
  statements (2024–26); ISSB April 2026 activities update ("global passport",
  removing the interoperability guide).
- **SBTN science-based targets for nature** — SBTN Steps 1&2 V2 consultation
  (Mar–Apr 2026), "Business action for biodiversity via SBTs for nature" (Jan
  2026); TNFD–SBTN interoperability.
- **Biodiversity credits** — BCA / IAPB / WEF "High-Level Principles to Guide
  the Biodiversity Credit Market" + Assessment Matrix; IAPB Framework (COP16,
  Oct 2024); GBF Target 19.
- **Carbon-market integrity** — ICVCM Core Carbon Principles + CCP Impact Report
  2025 (8 programs, 38 methodologies, ~105M CCP credits, ~25% premia); VCMI
  Claims Code of Practice v3.0; Article 6.4 / PACM; dMRV (ClimeCo, GFT, NFT News
  "Carbon 2.0").
- **Just Transition metrics** — Shift / Council for Inclusive Capitalism / WBA /
  WBCSD / LSE Just Transition Finance Lab "19 Just Transition metrics" (2026);
  GRI 102 Climate Change; JUST Capital 2026 rankings.
- **California SB 253 / SB 261** — CARB Initial Regulation (26 Feb 2026); SB 253
  Scope 1&2 deadline 10 Aug 2026, Scope 3 from 2027; SB 261 Ninth Circuit
  injunction + CARB enforcement advisory (PwC, Nelson Mullins, Watershed,
  Persefoni).
- **Agentic AI in ESG** — "ESGAgent" benchmark (arXiv 2601.08676); Manifest
  Climate; Diginex/Matter (carbon-data automation 25%→80%, May 2026).
- **Outcomes / impact-linked finance** — Convergence "Accelerating Impact-Linked
  Finance"; Technavio impact-investing forecast (~26.6% CAGR); ING "Sustainable
  Debt Outlook 2026" (SLBs ~$25bn subdued, SLLs ~$160bn).
