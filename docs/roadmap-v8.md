# Impact Vision — Roadmap v8.0

**Date:** 2026-10-08
**Status:** 0.17.2 (Wave 0) and 0.18.0 (first pass of Waves 1–5) released 2026-10-08. See "Progress (2026-10-08)" in §5 for what remains
**Audience:** product, engineering, fund managers, consultants, LPs, verifiers
**Builds on:** `roadmap-v7.md` (released as 0.17.0/0.17.1). The v6 capability
backlog stays valid for anything not superseded here.

**Thesis.** v7 made the product *look* trustworthy. A deck becomes a
beautiful, bilingual, provenance-stamped report in about 3 seconds. The
post-v7 review shows three deeper problems:

1. **The scores measure disclosure, not impact.** 5D and SDG scores mostly
   reflect how many IRIS+ IDs were reported, plus keyword guesses. The
   reported quantities (households reached, tCO2e avoided) are never read.
   A matched-control study does not move Contribution. Every deck gets the
   same verdict.
2. **The web server is unsafe by default.** With no API key set, any
   webpage the user visits can repoint the stored provider key at an attacker.
3. **The product stops at screening.** It has no company record over time,
   no way to edit and re-run an assessment, and no path from screening into
   portfolio monitoring, LP reporting and exit.

v8 is a **credibility + lifecycle** wave:

1. **Secure by default.** Lock the server down first, as a patch release.
2. **Measure impact.** Methodology 2.0 scores expected impact with
   uncertainty. Evidence quality is a separate axis. It is calibrated
   against expert ratings.
3. **Generalise.** Evidence-aware extraction and relevance-ranked advice.
   A held-out evaluation set replaces tuning on three golden decks.
4. **Follow the investment.** One company record from pipeline to exit,
   with human review and edits, annual investee data, and expected vs
   actual results.
5. **Stay current and ship like a product.** Absorb the 2026-12 → 2027
   regulatory calendar. Remove the inherited coding-agent scaffolding.
   Publish to PyPI/Docker.

Engineering rules (unchanged): **extend / wrap, never fork**; every surface
is generated from the tool registry; every number carries provenance and
methodology version. v8 adds two more:
- **Every score must respond to the evidence it claims to measure.** This is
  enforced by perturbation tests in CI.
- **Nothing that changes provider, file or network behaviour is reachable
  from a non-local caller without authentication.**

---

## 1. Review summary (October 2026)

Four parallel reviews were run against `main@01e104a` (0.17.1):
- architecture, security and performance;
- hands-on product (3 golden + 4 new decks, offline paths);
- methodology rigour (a methodologist's read, plus perturbation
  experiments);
- a regulatory, market and AI-tech outlook to end-2027.

Scratch evidence is kept outside the repo.

### 1.1 What is already strong (keep)

- **Speed and polish.** `assess` takes 2.6–3.1 s per deck. PDF takes 5.5 s
  (9-page report + 5-page memo). There is one design system, axe-clean,
  in en / zh-HK / zh-CN.
- **Engineering discipline.** 1,673 tests green in ~80 s. ruff is clean.
  CI gates exist for the wheel, visual QA, knowledge freshness and
  extraction (F1 ≥ 0.95).
- **Trust primitives.** Methodology version + config hash on every output,
  sourced YAML knowledge with a 180-day freshness gate, AI provenance on
  every deliverable, persisted engagements and audit chain.
- **Unused assets.** The magnitude modules already exist but are not wired
  in: `impact_quantifier.py`, `counterfactual.py`, `causal.py`, `sroi.py`,
  `impact_valuation.py`, `frameworks/pcaf.py`. So do `monitoring`,
  `investee_portal`, `trend_analysis` and `exit_impact`.
- **A strategic position nobody else holds** (see §2.2): an impact-first
  (not ESG-first), offline-capable, open-source, bilingual tool with an
  SFDR 2.0 "impact claim → ToC + measurable outcome" test and ISSA 5000 /
  AI Act provenance.

### 1.2 Diagnosis — six problems

| # | Problem | Evidence | Severity |
|---|---|---|---|
| **E1** | **The local server is exploitable by any webpage.** With no `IMPACT_VISION_API_KEY`, every route is open and CORS is `*`. There is no Host or WebSocket Origin check, so DNS rebinding works too. `POST /api/v1/chat/providers` sets a `base_url` and keeps the stored key, so the next chat sends the user's Anthropic/OpenAI key to the attacker. The legacy `/api/v1/pitch-deck` route bypasses the path guard: a caller can read any `.pdf/.txt/.md` on the server, and redirects bypass the SSRF check. Webhooks have no URL check. The web "fund" tool profile auto-allows `file_read` + `web_fetch`, so prompt injection in a deck can read `~/.openharness/credentials.json` and send it out. `full_auto` can be set from the web. Uploads land in `cwd/.impact-vision/uploads` (inside the repo, not git-ignored, any extension). `/artifacts/download` serves any file under cwd | `api_gateway/router.py:73-80,127,769-783,1016`; `web/chat_api.py:59,86,197,365`; `tools/__init__.py:30-40`; `permissions/checker.py:133` | **Critical** |
| **E2** | **Scores measure disclosure, not impact.** In all sample decks, every 5D dimension equals the keyword baseline: `max(metric_score, baseline)` with a 2.5 cap below 3 matched metrics. Changing "42,000 households / 20,000 tCO2e" to "420 / 200" changes nothing. NESTA levels never reach 5D/SDG/gate. Only the first 1,000 chars of the deck feed 5D (`text[:1000]`), so evidence and risk sections are invisible, while the *problem statement* is penalised as the company's own adverse impact. Buzzwords at the top ("unique, catalytic") lift Contribution 1.5 → 2.1. SDG relevance rewards self-assertion (+0.7) and geography (+0.3 for "Kenya"). Risk has no consistent direction. 5D can fall below its own 1–5 scale (0.5) | `five_dimensions.py:224,289-301,376,400-410`; `pipeline.py:167`; `sdg_mapper.py:242-250`; `scoring_config.yaml` | **Critical** |
| **E3** | **The verdict is uninformative and "absence" is punished.** All 3 golden decks and 2 of 4 new ones come out "INSUFFICIENT EVIDENCE" (5D 1.6–1.7). A strong Indonesian edtech deck (186k students, 0.21 SD vs comparison schools, disclosed privacy risk) comes out **FAIL / Do not proceed**, greenwashing 66, driven by "no verification" + "missing negatives". That breaks v7 principle 2. Missing-negatives = 90 for every deck because only specific IRIS+ IDs count, not disclosed controls. The greenwashing threshold lives in four places with four values (YAML 20/40/60/80, gate 40, `deal_gate.py:96` 60, `verdict_engine.py` 30/70). 59.7 displays as "60 — Moderate" next to "≥60 is a finding". Gate thresholds (`fund_thesis.py:27-30`) are outside the versioned methodology | `greenwashing.py:330,396,416,453,480`; `deal_gate.py:96`; `verdict_engine.py:28-33`; `fund_thesis.py:27-30` | **High** |
| **E4** | **Advice doesn't generalise beyond the three tuned decks.** Metric suggestions are picked **alphabetically**, not by relevance. So an edtech is told to report "Racial Equity Negative Screen", a HK circular-fashion firm "Client Protection Policy (OI4753)", and every deck "Start with: Social and Environmental Targets, Board of Directors…". There is a hard-coded "(e.g., GHG emissions, client protection)" for every sector. The HK fashion deck is classified *technology / geography unknown* although "Hong Kong" appears twice, and the web UI can't override sector or geography. Generic PI4060 counts as evidence for SDGs 1, 2, 4 and 10 at once, so SDG 2 shows as material for solar, edtech and microfinance. Extraction misses comparison studies, accreditations (SafeCare) and risk sections. Most claims show NESTA "—" | `sdg_mapper.py:471`; `five_dimensions.py` (`gap_ids = sorted(...)`); `gap_analysis.py:276`; `greenwashing.py:524`; `chat_ui.py:1057` | **High** |
| **E5** | **The product stops at screening.** There is no company record over time, and screened deals and portfolio companies are not separated. Users can't correct the extraction and re-run, there are no reviewer comments or IC approvals, and assessments are not linked to annual investee submissions. There is no expected-vs-actual, and the portal, monitoring, trend and exit tools are only reachable as agent tools. There is no Excel/CSV import or CRM/data-room/Drive connector, and no reminders. Portfolio home shows **California SB 253** to a one-company Kenyan portfolio (no applicability filter). zh-HK translates the chrome only, so claims, action plan and DD questions stay English. `.docx` is advertised in the web UI but rejected by the pipeline (422). Only the first dropped file is analysed | `pipeline.py:23`; `chat_ui.py:673,1014`; `portfolio_home`; `regulatory_calendar` | **High** |
| **E6** | **The platform isn't ready to be hosted or released.**<br>• **Inherited scaffolding:** 29% of the 119k LOC is inherited coding-agent code (about 13.6k with no product use, plus `ohmo/`), and about half the tests guard it.<br>• **Multi-tenancy:** `tenancy.py` has no importers and `tenant_id` is passed nowhere. Verification workspace, LP Q&A, consent, engagement suite, decision workflow and exit tools have no persistence. Gateway webhooks and batch jobs are process-memory dicts. Schemas have no migrations.<br>• **Signing and secrets:** assurance "signatures" are symmetric HMAC, so anyone who can verify can also forge. Keys are plaintext on disk without a keyring.<br>• **Performance and size:** `impact → tools` imports make `import openharness.impact` take 1.6 s. The 4.1k-LOC classic report was never split.<br>• **Duplication and dead code:** four benchmark providers, of which the W5.1 one has zero importers, and four regulatory modules.<br>• **Release and CI:** no PyPI/Docker release, mypy, coverage, pip-audit or 3.12/3.13 matrix. The freshness gate is not scheduled | `impact/tenancy.py`; `state_store.py:27`; `signed_feed.py:106`; `auth/storage.py:140`; `impact/metric_records.py:10`; `tools/impact/impact_report_tool.py`; `benchmark_provider.py` | **High** |

---

## 2. Outlook (Nov 2026 → end 2027)

### 2.1 Standards & regulatory calendar

v7 §2 and `data/regulatory/watchlist.yaml` already hold most of these. Rows
marked † need verification at implementation time.

| Priority | Development | Date / status | Action in Impact Vision |
|---|---|---|---|
| **P0** | **EU AI Act Art 50**. Grace period for systems already on the market ends; Code of Practice on AI-generated content final 2026-06-10, deemed adequate 2026-07-08 | **2026-12-02** | Add **machine-readable** AI marking (HTML meta / PDF XMP / DOCX & XLSX core props / JSON) on top of the visible badge, mapped to the Code. Log human reviewer sign-off; human review plus editorial responsibility is an exemption route for deployers |
| **P0** | **ISSA 5000 / HKSSA 5000** effective | Periods ≥ **2026-12-15** | Already framed (W4.6). Add per-figure AI-use + reviewer sign-off to the assurance pack from the W2 evidence model |
| **P0** | **Revised ESRS** in force 2026-11-10, mandatory FY ≥ 2027-01-01. Omnibus I scope >1,000 employees **and** >€450m turnover; transposition due 2027-03-19 | Final | Add a CSRD **scope tester**. Make VSME the default investee ask (most VC investees are out of scope) |
| **P0** | **ESRS XBRL taxonomy**: consultation closes 2026-11-11, to ESMA/EC by year-end, ESMA RTS in 2027 | Q1 2027 | Re-sync `xbrl_export` and replace the screening rows with the annex datapoint codes (v7 carry-over) |
| **P0** | **SFDR 2.0**: plenary Oct 2026, trilogue Q4 2026, political deal ~mid-2027†, application late 2028–mid 2029 | In trilogue | H2 2027 "final text" sprint: merge the commission/council/parliament variants into one classifier. Make the impact-claim → ToC + **pre-defined measurable outcome** test (now backed by Methodology 2.0) the flagship check |
| **P0** | **Hong Kong**: first HKEX LargeCap climate reports land in 2027; HKEX consults on full HKFRS S1/S2 in 2027 (large PAEs ~2028); HK Taxonomy Phase 2B (25 → 39 activities) consultation closed 2026-10-07, final ~H1 2027† | Mixed | 2B screen when final. **HKFRS S1 gap tool** before the HKEX consultation. Native zh terminology from HKFRS/HKEX |
| **P1** | **ILPA Portfolio Company Metrics template** final | **Jan 2027** | Export adapter next to EDCI |
| **P1** | **ISSB**: nature Practice Statement ED (120-day comment, ~Feb 2027); S2 amendments effective 2027-01-01; workforce project | ED Oct 2026 | Map TNFD to the ISSB nature ED in H1 2027 (v7 deferred item) |
| **P1** | **China MoF** Basic Standard + Climate No.1 (trial), implementation targeted 2027 | Trial | Distinct CN profile + zh-CN terminology |
| **P1** | **US**: SB 253 Scope 1+2 due 2026-11-10, Scope 3 2027; SB 261 enjoined (Ninth Circuit pending†); SEC proposed full rescission 2026-05-29 (final vote†) | Mixed | Keep on calendar. **Filter by applicability** (E5) so non-US portfolios don't see it |
| **P2** | GHG Protocol Scope 3 revision (final ~late 2027; 95 % coverage rule, new cat. 16†); Scope 2 final ≥ 2027 | Consultation | Put the Scope 3 logic behind a methodology flag |
| **P2** | PCAF Part A/C update (Dec 2025), 2026–28 cycle | Final | Refresh financed-emissions methods |
| **Watch** | EDCI 2026/27 cycle, GIIN State of the Market 2026, IRIS+ revision, Impact Frontiers norms v2 ("planned for 2026"), Japan SSBJ / Australia / Singapore phasing | Unverified / pending | `regulatory_radar` watch-list. Run the freshness gate **on a schedule** |

### 2.2 Market position

- **Table stakes** (Novata, Sweep, Watershed, Persefoni, Clarity AI, etc.):
  portfolio data-collection portals, SFDR PAI / EDCI / ILPA exports, carbon
  accounting incl. PCAF, CSRD/VSME modules, an AI extraction/copilot layer.
  We have most of these as *tools*, but not as a lifecycle product (E5).
- **The market is consolidating into suites.** A focused tool must
  interoperate through exports, MCP and connectors, not compete on breadth.
- **Our differentiation, in order:**
  1. **Impact, not ESG.** ToC + 5D + stakeholder voice + the SFDR 2.0
     impact-claim test, which v8 makes *quantitatively* credible.
  2. **Assurance-ready AI.** Per-figure provenance, ISSA 5000 framing and
     AI Act marking.
  3. **Offline / self-hosted / bilingual**, aligned to HK Taxonomy, HKFRS
     and China MoF, for HK/GBA data-residency needs.
  4. **The consultant channel.** White-label engagements for boutique
     consultants, whom SaaS sellers underserve.

### 2.3 AI & agent technology

- **MCP is infrastructure.** The 2026-07-28 spec is stateless (per-request
  version negotiation, `server/discover`). Many public servers lack auth, so
  an **authenticated, audited MCP server** is a differentiator.
- **Evaluation practice has moved to trajectory and tool-use evals** across
  model swaps. The new provider presets (0.17.x) make a cross-provider
  agent eval both possible and necessary.
- **Small open document-AI models are competitive.** GLM-OCR and
  LightOnOCR-2 (~1B) lead table and layout benchmarks. A fully offline
  pipeline with **page + bounding-box citations** is now realistic. That is
  what "evidence" will be expected to mean under ISSA 5000 and the AI Act.

---

## 3. North star & principles

**North star (v8):** *An investment team takes a company from first deck to
exit in Impact Vision. At IC they see an expected-impact estimate with an
honest range, and the few pieces of evidence that would move it. Each year
they see expected vs actual. A verifier can trace every figure to a page in
a source document, see who reviewed it and whether AI touched it, and
reproduce it from a pinned methodology.*

Principles added in v8:

1. **Magnitude over coverage.** A score must move when the impact moves
   (reach, depth, duration, counterfactual), and not when the vocabulary
   moves.
2. **Two axes, never blended.** *Expected impact* and *evidence quality*
   are reported separately. Data completeness is a third number, not a
   score input.
3. **Absence is a plan, not a verdict.** Missing data produces an evidence
   plan. Only contradictory or misleading evidence produces a finding.
4. **Ranges, not points.** Every headline number carries P10/P50/P90
   driven by evidence level. Gates act on the conservative end.
5. **Human in the loop by design.** Every extracted fact can be confirmed or
   corrected, and the correction is versioned, attributed and re-scored.
6. **Applicable by default.** Regulations, metrics and questions are
   filtered by sector, geography, fund domicile and stage.
7. **Secure by default.** A fresh install is safe on a laptop with a
   browser open.

---

## 4. Waves & tracks

Effort: S ≤ 3 days, M ≤ 2 weeks, L ≤ 4 weeks.

### Wave 0 — Secure & honest (week 1–2, P0; ship as 0.17.2)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W0.1 | **Server lockdown.** Without `IMPACT_VISION_API_KEY`: bind to loopback only and auto-generate a per-launch token (printed in the console, injected into the served UI). CORS is same-origin by default. Add a Host-header allow-list (stops DNS rebinding), a WebSocket Origin check, and token in a header or subprotocol rather than the query string, compared in constant time. Changing `base_url` / `api_format` of a profile with a stored key requires re-entering the key | `api_gateway/router.py`, `web/chat_api.py`, `web/chat_ui.py` | S |
| W0.2 | **Guard every route.** Send legacy `/api/v1/pitch-deck` (and siblings) through `surfaces.run_tool` (path guard). URL fetch re-validates every redirect with `network_guard.ensure_public_http_url`, and so do webhooks. `/artifacts/download` serves only the reports/uploads folders | `router.py:769-783,1016`, `pitch_deck_analyze_tool.py:918` | S |
| W0.3 | **Contain the web agent.** The fund profile confines `file_read` to the workspace and uploads folders and gates `web_fetch` behind a prompt. `full_auto` can't be set from the web. Uploads go to the web home (`~/.impact-vision/uploads`) with an extension allow-list; add `.impact-vision/` to `.gitignore` | `tools/__init__.py`, `permissions/checker.py`, `chat_api.py:59,86` | S |
| W0.4 | **Absence ≠ finding.** Greenwashing components driven only by missing data ("no verification", "missing negatives", "selective") are capped below the finding threshold and labelled *evidence gap*. Disclosed narrative controls (caps, contractors, accreditations) count toward the negatives and verification components. One threshold set in `methodology` YAML, read by gate, verdict and display. Round consistently (59.7 never shows as 60) | `greenwashing.py`, `deal_gate.py:96`, `verdict_engine.py:28`, `fund_thesis.py:27` | S |
| W0.5 | **Cheap correctness fixes.**<br>• Full text instead of `text[:1000]`, sectioned by role (problem / solution / evidence / risk). Problem statements are excluded from the adverse-impact check.<br>• Clamp 5D to 1–5.<br>• Fix the NESTA labels (`models.py:572`: an RCT or controlled study is L3, not L5).<br>• Fix the "GIIN 5D average" attribution: GIIN publishes no 5D scores, so label it *illustrative house prior* until W1.8.<br>• Drop the geography and self-assertion boosts behind methodology 1.2.0 | `pipeline.py:167`, `five_dimensions.py`, `models.py`, `benchmarks.yaml`, `sdg_mapper.py:242-250` | S |
| W0.6 | **Relevance-ranked advice.** Replace every `sorted(...)[:n]` metric pick with a ranking by sector core set → theme → SDG specificity → cross-cutting last. Remove the hard-coded "(e.g., GHG emissions, client protection)". Generic metrics like PI4060 can't make an SDG material on their own | `sdg_mapper.py:471`, `five_dimensions.py`, `gap_analysis.py:276`, `greenwashing.py:524` | S |
| W0.7 | **Small UX fixes found in review.**<br>• `.docx` in the pipeline (or stop advertising it); analyse every dropped file together.<br>• Sector, geography and stage overrides in the web "Analyze" flow.<br>• "Hong Kong" detection.<br>• Regulatory items filtered by portfolio jurisdiction.<br>• DD questionnaire drops fund-side questions.<br>• `/health` alias, "1 company" pluralisation, one AI disclosure, consistent "N scores estimated" between CLI and web, consistent verdict wording | `pipeline.py:23`, `chat_ui.py:1014,1057`, `portfolio_home`, `dd_report_html.py` | M |
| W0.8 | **Generalisation goldens.** Add the review's 4 new decks (edtech ID, clinics KE, circular fashion HK, vague greenwasher) + 6 more (zh-language deck, climate-tech EU, agri India, fintech LatAm, housing UK, water SEA). Assert plausibility bands for sector, top-3 SDGs, no irrelevant metric in the actions, the verdict class, and the greenwasher being the only finding | `tests/golden/` | M |

**Exit criterion:** an unauthenticated cross-origin page can't read or change
anything. The edtech deck is no longer a FAIL. No golden output recommends a
metric from another sector.

**Wave 0 status (2026-10-08):** done and released as **0.17.2**.
- **W0.1–W0.3:** `api_gateway/security.py` adds the Host allow-list, Origin
  check and same-origin CORS. The launch token, the provider re-key rule,
  guarded legacy routes, redirect-checked URL fetches, public-only
  webhooks, upload/download allow-lists and fund-profile file confinement
  are covered by `tests/test_v8_security.py`.
- **W0.4–W0.6:** methodology **1.2.0**.
- **W0.7:** `.docx` / `.pptx`, multi-file assess, the web "Correct and
  re-run" form, applicability-filtered deadlines, `ask: fund` DD
  questions, and the small fixes.
- **W0.8:** ten golden decks, including one in Chinese
  (`tests/test_v8_golden_decks.py`).

Two things were found and fixed along the way:
- The es/fr/pt SDG keyword files were never loaded; zh was added.
- Metrics tagged to most IRIS+ themes (e.g. OI9101, 27 themes) matched
  every company.

Still true, and the reason for Wave 1: every deck except the greenwasher is
"INSUFFICIENT EVIDENCE", and 5D still mostly measures disclosure.

### Wave 1 — Methodology 2.0: measure impact (weeks 2–10)

Ships as `data/methodology/v2.yaml`. v1.x remains selectable
(`methodology="1.2"`) for one release, and every output already carries the
version.

| ID | Item | Extends | Effort |
|---|---|---|---|
| W1.1 | **Two axes + completeness.**<br>• *Expected impact* (magnitude, below).<br>• *Evidence quality* (NESTA-weighted, per claim → per outcome).<br>• *Data completeness* (core metric coverage), shown as a percentage, never a score input.<br>The 1–5 5D average is retired from the headline; per-dimension narratives stay | `five_dimensions.py`, `decision_report.py`, templates | M |
| W1.2 | **Outcome model.** Each claim becomes an `Outcome`: stakeholder, indicator, baseline, reported value, unit, period, reach, source span. The extractor fills it. Values are read, not just IDs counted | `models.py`, `extractors/`, claim→IRIS+ mapper | M |
| W1.3 | **Expected-impact core (IMM-style).** Per outcome: reach × depth (change vs baseline) × duration × (1 − deadweight) × attribution × probability of success. Normalised to a common unit per theme: tCO2e (PCAF attribution), people-years of material change, and optionally wellbeing-years/QALY via `impact_quantifier`. Expressed per $ invested and against the fund's own thresholds. Wires in the existing `impact_quantifier`, `counterfactual`, `causal`, `sroi`, `pcaf` | those modules, `pipeline.py` | L |
| W1.4 | **Contribution split.** *Enterprise* contribution (counterfactual from evidence level and comparison-group claims) and *investor* contribution (signal / engage / grow new markets / flexible capital), each on an explicit rubric. Adjectives no longer count; only evidence does | `five_dimensions.py`, `counterfactual.py` | M |
| W1.5 | **Uncertainty.** Each input carries a distribution whose width follows its evidence level (e.g. L1 ±80 % … L4 ±15 %; parameters in YAML). Monte Carlo gives **P10/P50/P90** for every headline number. Gates act on P10. Reports show ranges and the 3 inputs that drive the most variance ("what would change our mind", now quantitative) | new `impact/uncertainty.py`, `improvement_advisor` | M |
| W1.6 | **Negative impacts.** Severity × likelihood per ESRS impact materiality. Structured SFDR PAI values. Per-sector DNSH tests with numeric thresholds. Exclusion-list hard flags instead of small score deductions. Risk has one direction everywhere (likelihood that impact differs from expected, as in IMP) | `risk_opportunity.py`, `frameworks/sfdr_pai.py`, `eu_taxonomy` | M |
| W1.7 | **Gate 2.0.** Three states: **Ready** / **Evidence plan required** (with the plan) / **Fails thesis**. Every threshold lives in the methodology YAML with a written rationale and appears in the appendix | `deal_gate.py`, `verdict_engine.py`, `fund_thesis.py` | S |
| W1.8 | **Benchmarks you can defend.** Company-level distributions only, with n, IQR, licence and source. Percentile with CI, or no comparison at all. Collapse the four benchmark providers into `benchmark_provider` | `benchmark_provider.py`, `external_benchmarks.py`, `giin_benchmarks.py`, `value_creation.py` | M |
| W1.9 | **Greenwashing 2.0.** Per claim: specificity × evidence level × materiality, built on `greenwashing_reviewer`. Company score = worst material claims, not an average of absences. Keep the ECGT/UCPD legal checks | `greenwashing.py`, `greenwashing_reviewer.py` | M |
| W1.10 | **Portfolio aggregation.** Natural units weighted by capital × attribution. Never average ordinal scores. SDG contribution is weighted by impact, not by number of metrics | `portfolio_tool.py:369`, `fund_analytics.py:9` | M |
| W1.11 | **Alignment.** IRIS+ CMS strategic goals (and the coming revision). SFDR 2.0 pre-defined KPIs. Ex-ante targets are stored so W3 can show expected vs actual (Impact Frontiers performance-reporting norms) | `core_metric_set_per_sdg.yaml`, `sfdr2` | S |

**Wave 1 status (2026-10-08):**
- Done:
  - W1.1: two axes plus completeness.
  - W1.2: outcomes read from claims, as a company-level reach, depth and
    tCO2e bundle.
  - W1.3: IMM-style expected impact, people and climate, per US$1m.
  - W1.5: seeded Monte Carlo producing P10/P50/P90, with variance drivers.
  - W1.7: Gate 2.0 in the report, IC memo, CLI, web and portfolio home.
- Partly done:
  - W1.4: enterprise contribution comes in through deadweight netting by
    evidence level. Investor contribution needs the fund's data (W3).
  - W1.11: targets are kept as ex-ante commitments.
- Still to do: W1.6, W1.8, W1.9 and W1.10. All parameters stay
  "illustrative" until the W2.6 calibration study.

### Wave 2 — Evidence, extraction & evaluation (weeks 3–12, parallel)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W2.1 | **Evidence-aware extraction.** Bullets and tables, comparison/control studies → NESTA L3, accreditations and certifications (SafeCare, Gold Standard, B Corp, SIRIM) → verification, "risks we manage" → disclosed controls, funding lines are not outputs, and sector statistics are context rather than company outcomes | `extractors/`, `claim_mapper` | M |
| W2.2 | **Grounded citations.** Every extracted fact carries document, page and bounding box. The evidence ledger links to a page thumbnail with the span highlighted. This is the AI Act / ISSA 5000 evidence model | `extractors/`, `evidence_graph.py`, report templates | M |
| W2.3 | **Pluggable document AI.** Interface for local parsers (PyMuPDF today; optional small open OCR/layout models such as GLM-OCR / LightOnOCR-class for scanned decks, tables and charts), plus an LLM structured-output extractor with a schema. Pick per document; fully offline is possible | `extractors/` | M |
| W2.4 | **Held-out eval set.** 30+ decks across ≥ 10 sectors, ≥ 6 regions, en + zh, including deliberate greenwashers. Never used for tuning. CI reports F1 for facts, sector/SDG agreement and verdict agreement per release | `extraction_eval.py`, `tests/golden/` | M |
| W2.5 | **Perturbation and gaming tests (CI).** Scale reported values ×0.01 → expected impact drops. Inject buzzwords → no change. Add an RCT → evidence quality rises. Swap the problem statement → no adverse-impact penalty. Move the evidence section to page 9 → same result | `tests/methodology/` | S |
| W2.6 | **Expert calibration study.** 50–100 decks rated by 2–3 practitioners (reuse the consultant network). Krippendorff α target ≥ 0.67. Calibrate W1 weights by ordinal regression and publish the study with methodology 2.0 | `docs/methodology/` | L |
| W2.7 | **Agent evals across providers.** Trajectory and tool-use evals (tool-call count, correct `assessment_id` hand-off, no hallucinated figures, refusal to invent evidence) on Claude Sonnet 5.5 and Opus 5.5, GPT-class, DeepSeek, Qwen and a local Ollama model. Results drive which models the presets recommend | new `evals/agent/` | M |

### Wave 3 — Lifecycle spine (weeks 6–16)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W3.1 | **Company record.** One entity with stages *pipeline → IC → invested → exited*. Assessments, engagements, submissions, reports and documents hang off it. Portfolio home separates pipeline from portfolio | `storage.py`, `state_store`, `portfolio_home` | M |
| W3.2 | **Review, edit & re-run.** In the web app the user confirms or corrects sector, geography, stage, each claim and each outcome value. Re-scoring creates a new version with a diff ("Contribution P50 +0.4 because you confirmed the comparison study"). Corrections are attributed and audit-chained | `chat_ui.py`, `reports_api.py`, `evidence_workflow.py` (persisted now) | L |
| W3.3 | **Collaboration & approvals.** Comments on any claim, score or section. IC approval workflow (prepare → review → approve / decline with reasons), with reviewer sign-off recorded for the AI Act / ISSA 5000 | `report_governance`, `ai_review` | M |
| W3.4 | **Annual monitoring.** The investee portal is linked to the company record. The yearly request is generated from the ex-ante outcomes (W1.11) and VSME. Submissions update actuals and evidence levels. **Expected vs actual** view with variance explanations. Reminders by email and webhook | `investee_portal.py`, `monitoring`, `trend_analysis`, `investee_collection` | L |
| W3.5 | **Import & connectors.** Excel/CSV metric import with column mapping. Read-only connectors behind one interface: Google Drive / SharePoint folders, a data-room export folder and a CRM (Affinity / DealCloud) for pipeline sync. Exports: ILPA template (Jan 2027), EDCI, SFDR PAI | new `impact/connectors/`, `exports.py` | L |
| W3.6 | **LP report & exit from the record.** The fund-level LP report is built from invested companies (W1.10 aggregation). `exit_impact` (OPIM P8) runs on the record and pre-fills from monitoring history | `lp_narrative.py`, `exit_impact.py` | M |
| W3.7 | **Send-unedited zh.** The full body is localised: action plan, DD questions, sector risks, methodology appendix. Claims stay in the original with a translated gloss. The terminal summary is localised. Native-speaker review of HKFRS/HKEX terminology | `strings.py`, `dd_checklist.yaml` (zh fields), `pipeline.py` | M |

### Wave 4 — Standards currency 2027 (parallel; one engineer)

Order follows the calendar in §2.1:
- AI Act machine-readable marking + reviewer log by **2026-12-02**;
- ISSA 5000 pack additions by 2026-12-15;
- CSRD scope tester + VSME-default (Q4 2026);
- ILPA template adapter (Jan 2027);
- ESRS XBRL re-sync + annex datapoint codes (Q1 2027);
- ISSB nature ED mapping (H1 2027);
- HK Taxonomy 2B screen + HKFRS S1 gap tool (when final, ~H1 2027);
- China MoF profile;
- PCAF Dec-2025 refresh;
- GHG Scope 3 flag;
- SFDR 2.0 final-text sprint (after the political agreement, ~H2 2027).

Every row carries `as_of` and `source_url`, and the freshness gate runs
**weekly** on a schedule, not only on push.

### Wave 5 — Platform: secure, hostable, shippable (weeks 4–20)

| ID | Item | Extends | Effort |
|---|---|---|---|
| W5.1 | **0.18 package move + trim.** Physically move the code to `src/impact_vision/`, with `openharness` as the alias. Remove the `roadmap_v2` / `questionnaire_v2` / `sfdr_v2` shims (0 importers). Remove the inherited scaffolding the product doesn't use (swarm, coordinator, channels, cron/team/worktree/LSP tools, bridge, voice, vim, keybindings, `ohmo/`, about 17k LOC) and its tests | repo-wide | L |
| W5.2 | **Layering & size.** `impact/` must not import `tools/` (move normalisers into `impact/normalize.py`; lazy tool package). Target `import impact_vision.impact` < 0.5 s. Retire the 4.1k-LOC classic report or finish `report_builders/`. One regulatory module instead of four. Delete dead modules (`scenario_modeling`, `i18n`, `toolbox/ingest`) | `impact/metric_records.py:10`, `tools/impact/impact_report_tool.py`, `regulatory_*` | M |
| W5.3 | **Identity & tenancy.** OIDC login (or a local single-user mode). Wire in `tenancy.py` RBAC. `tenant_id` through the tool context. Tenant-scoped sessions, uploads, reports and state | `web/`, `api_gateway/`, `tenancy.py`, `state_store` | L |
| W5.4 | **All state persisted, with migrations.** The remaining stateful tools (verification workspace, LP Q&A, consent, engagement suite, decision workflow, exit, review queues) move to `state_store`. Gateway webhooks and batch jobs go to a store/queue. Add a schema-version table + migration runner for SQLite and Postgres | `state_store.py`, `storage.py`, `router.py:292` | M |
| W5.5 | **Verifiable signatures & secrets.** Ed25519 signatures with a published public key for assurance manifests, share links and feeds (HMAC stays for internal tokens). Secrets come from env, a secret manager or the keyring when hosted; no plaintext fallback in containers | `signed_feed.py`, `verification_bundle.py`, `auth/storage.py` | M |
| W5.6 | **Authenticated MCP server** on the 2026-07-28 spec (stateless, `server/discover`), with token auth, per-tool scopes and audit logging | `impact/mcp_server.py` | M |
| W5.7 | **Release pipeline.** Tag → PyPI + GHCR Docker image + `pipx`. CI adds mypy (impact/), coverage floor for `impact/` (≥ 80 %), pip-audit + bandit, and a 3.11/3.12/3.13 matrix. Harness and visual tests get markers so the default run is fast | `.github/workflows/`, `pyproject.toml`, `Dockerfile` | M |

---

## 5. Build order & releases

### Progress (2026-10-09)

**Released**
- **0.17.2:** Wave 0 complete.
- **0.18.0:**
  - **W1:** Methodology 2.0 — W1.1–W1.3, W1.5, W1.7, W1.10; W1.8 relabelled.
  - **W2:** W2.2 page citations; W2.4 partly (13 golden decks); W2.5 perturbation tests.
  - **W3:** W3.1 company record; W3.2 partly; W3.3 comments and IC decisions; W3.4 core
    (expected vs actual); W3.5 partly (Excel/CSV import).
  - **W4:** AI Act machine-readable marking.
  - **W5:** W5.1 partly; W5.2 partly; W5.4 partly; W5.5 Ed25519; W5.7 release pipeline.
- **0.19.0:**
  - **W1:** W1.4 contribution split (Methodology 2.1.0); W1.6 negative impacts;
    W1.9 greenwashing 2.0.
  - **W2:** W2.1 evidence-aware extraction; W2.3 OCR for scanned pages; W2.4
    30-deck held-out set with a CI report.
  - **W3:** W3.4 annual monitoring (portal, variance, reminders); W3.6 LP report and
    exit from the record; W3.7 zh report bodies.
  - **W5:** W5.1 code moved to `src/impact_vision`; W5.3 OIDC and tenancy; W5.4
    remaining state persisted, with migrations; W5.6 authenticated MCP over HTTP.

**Held-out baseline (0.19.0, 30 decks):** facts F1 0.83 (P 92 %, R 76 %), sector
77 %, geography 100 %, SDG 93 %, greenwashing 90 %, verdict 90 %. Known misses,
to be fixed on other documents and never by tuning on this set:
- Sector detection mistakes sanitation, school water, housing refurbishment and
  garment manufacturing for nearby sectors.
- Numbers in Chinese decks are often missed (e.g. 回收 1,280 公噸).
- Three greenwashers with no data are not flagged as greenwashing findings,
  although two still fail the thesis.
- Strong evidence (an RCT, a verified comparison group) still gives "evidence
  plan" rather than "ready" when core-metric coverage is low.

**Still to do**
- **W2.6:** the expert calibration study. It needs 2–3 practitioners to rate
  50–100 decks.
- **W2.7:** cross-provider agent evals. These need API keys.
- **W3.5:** CRM, Drive and data-room connectors, and the ILPA export once the
  template is final in Jan 2027.
- **Standards (Wave 4):** the dated items in §2.1, scheduled for when each text
  is final.
- **Release setup:** the first PyPI release needs a one-time trusted-publisher
  setup on PyPI.

| Release | Target | Contents |
|---|---|---|
| **0.17.2 "Secure"** | +1–2 wks (late Oct 2026) | Wave 0 (W0.1–W0.8). Methodology 1.2.0 (input and gaming fixes, absence ≠ finding) |
| **0.18.0 "Measured"** | Dec 2026 | Methodology 2.0 behind `methodology="2.0"` (W1.1–W1.7, W1.9), W2.1, W2.4, W2.5, AI Act machine-readable marking (by 2026-12-02), ISSA 5000 additions, W5.1 package move + trim, W5.2, W5.7 release pipeline (**first PyPI release**) |
| **0.19.0 "Connected"** | Feb–Mar 2027 | W3.1–W3.4, W3.7. Methodology 2.0 becomes the default. W1.8, W1.10, W1.11, W2.2, W2.3, W2.7. ILPA adapter, ESRS XBRL re-sync, CSRD scope tester |
| **0.20.0 "Hosted"** | Q2 2027 | W3.5, W3.6, W5.3–W5.6, W2.6 calibration study published. ISSB nature mapping, HK 2B + HKFRS S1 gap tool, China MoF profile |
| **1.0** | H2 2027 | SFDR 2.0 final-text sprint once trilogue concludes. Stability and API freeze. Methodology 2.x calibrated |

Re-run the outlook scan monthly via `regulatory_radar` and publish deltas
as `docs/roadmap-updates-YYYY-MM.md`.

## 6. Success metrics

| Metric | Today (0.17.1) | v8 target |
|---|---|---|
| Unauthenticated cross-origin page can change provider / read files | **yes** | **no** (CI security test) |
| Score change when reported reach is scaled ×0.01 | 0 % | expected impact ↓ proportionally (CI perturbation test) |
| Score change from injected buzzwords | Contribution +0.6 | **0** |
| Golden + held-out decks with the *same* verdict | 5 / 7 identical | verdict classes spread; agreement with expert class ≥ 80 % |
| Decks FAILed purely for missing data | 1 / 7 (edtech) | **0** |
| Actions recommending an off-sector metric | most decks | **0** on the held-out set |
| Headline numbers with P10/P50/P90 | 0 % | **100 %** |
| Claims with page-level citation | 0 % | **≥ 95 %** (bbox where the parser supports it) |
| Inter-rater agreement, engine vs experts | not measured | Krippendorff α ≥ 0.67 |
| Company tracked expected vs actual across years | not possible | **yes**, from the record |
| zh-HK report sendable without edits (native review) | chrome only | **full body** |
| Persisted stateful tools | 9 modules | **all** |
| `import impact_vision.impact` | 1.6 s | **< 0.5 s** |
| LOC of inherited non-product scaffolding | ~17 k | **0** |
| `pip install impact-vision` / Docker image | not published | **published per tag** |

## 7. Out of scope for v8

- A billing / SaaS commercial layer. W5.3 makes hosting possible; running
  it as a business is a separate decision.
- Public-markets ESG ratings and data feeds. We stay impact-first and
  private-markets-first.
- Hourly Scope 2 matching (waits for the GHG Protocol final).
- Native mobile apps.
- Writing our own OCR or layout model. We integrate open ones behind an
  interface.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Methodology 2.0 changes every score and alarms existing users | Ship it behind a version flag for one release with a side-by-side "v1 vs v2" appendix. Publish the calibration study. Every output already carries the methodology version |
| Expected-impact numbers look falsely precise | Always show ranges (P10–P90) and the evidence level beside them. Gates act on P10. "Illustrative" labelling until calibrated |
| Expert calibration panel is slow or small | Start recruiting in Wave 0 through the consultant network. Accept a 50-deck first round and grow it |
| Security lockdown breaks existing integrations (open REST/CORS) | `IMPACT_VISION_CORS_ORIGINS` and an explicit `--allow-remote` flag. Document the migration in CHANGELOG. 0.17.2 prints a one-line notice |
| Removing inherited scaffolding breaks the TUI or slash commands | Make imports lazy first (v7 carry-over). Run the TUI smoke test before deleting. Delete in one release with a CHANGELOG list |
| Connectors pull in heavy dependencies | Each connector is an optional extra; the core stays lean |
| Regulatory dates move (SFDR trilogue, HK 2B, ISSB nature) | Model them as variants with `status`. Scheduled freshness gate. Monthly outlook delta |

## 9. Sources (outlook, retrieved 2026-10-08)

- SFDR 2.0 trilogue timing — <https://clarity.ai/research-and-insights/regulatory-compliance/sfdr-2-0-in-trilogue-where-the-negotiations-stand-and-when-the-rules-will-apply/>; <https://www.debevoise.com/insights/publications/2026/09/sfdr-20-recap-briefing>
- ESRS XBRL taxonomy — <https://www.xbrl.org/news/efrag-advances-the-revised-esrs-toward-a-digital-taxonomy/>
- EU AI Act Digital Omnibus / Code of Practice — <https://www.hunton.com/privacy-and-cybersecurity-law-blog/eu-digital-omnibus-on-ai-enters-into-force>; <https://www.jonesday.com/en/insights/2026/06/european-commission-publishes-final-code-of-practice-on-marking-and-labelling-aigenerated-content>
- HK Taxonomy Phase 2B — <https://www.info.gov.hk/gia/general/202609/07/P2026090700249.htm>
- ISSA 5000 — <https://www.iaasb.org/consultations-projects/issa-5000-adoption-and-implementation>
- ISSB updates — <https://www.ifrs.org/news-and-events/updates/issb/2026/issb-update-july-2026/>
- ILPA metrics template — <https://ilpa.org/news/portfolio-company-metrics-template-refresh/>
- China MoF climate standard — <https://www.xbrl.org/news/china-moves-closer-to-ifrs-aligned-climate-disclosures/>
- GHG Protocol Scope 3 progress — <https://ghgprotocol.org/sites/default/files/2026-03/S3-Phase1ProgressUpdate-20260331.pdf>
- PCAF standard — <https://carbonaccountingfinancials.com/standard>
- MCP versioning — <https://modelcontextprotocol.io/specification/versioning>
