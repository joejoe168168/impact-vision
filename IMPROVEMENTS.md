# Impact Vision — suggested improvements (review of 0.19.1)

Reviewed on 2026-11-10 against `main@a1f5ed7` (release 0.19.1): code, data packs, report
templates, tests, README, CHANGELOG, CLAUDE.md / AGENTS.md and the roadmaps. The review
combined a read of the code with hands-on runs (`assess` on the three sample decks in
en / zh-HK, all 40 golden and held-out decks, `scripts/check_knowledge.py`) and a check of
a few regulatory facts against primary sources (listed in §1.3).

**How to read this.** §0 is the priority shortlist: the highest-value, reasonably scoped
items across all four areas, in the order I would do them. §1–§4 hold the full findings per
area. Effort is S (under a day), M (1–3 days), L (a week or more). Priority is P0 (wrong or
misleading output today), P1 (clear user value), P2 (worth doing, not urgent).

**Baseline.** `pytest tests/`: 1,784 passed, 11 skipped, 1 xfailed, 2 failed. Both failures
are local-environment leftovers, not code defects (a stale `impact_vision 0.16.0` stub in
`.venv/site-packages` breaks `python -m impact_vision` in a subprocess; an `ohmo/` folder
holding only `__pycache__` trips the "removed packages" check). `check_knowledge.py`: 343
rows, 0 stale.

---

## 0. Priority shortlist

| # | Item | Why it matters | Impact | Effort | Pri |
|---|---|---|---|---|---|
| 1 | **Negated evidence counts as evidence** (C1) | "We have no control group yet" is read as a controlled evaluation: NESTA 3, deadweight netted out, evidence quality "good", and the sentence is quoted as proof. "Not been audited" lowers verification risk. "We do not yet have a client protection policy" marks the harm as controlled. | Removes the easiest way to get a wrong, over-confident verdict | S | P0 |
| 2 | **HKEX ESG Code gap check** (R1) | The repo has one climate-only pack row for HKEX. There is no check against Appendix C2 itself (Part B mandatory, Part C A1–A3 / B1–B8 KPIs, Part D climate), which is what every HK-listed issuer and their investors work to. | Fills the main gap for the HK / GBA audience the product targets | M | P0 |
| 3 | **Knowledge refresh for events since 2026-10-06** (R2) | ISSB published the nature Exposure Draft (comments to 2027-02-19); the European Parliament endorsed its SFDR 2.0 mandate and trilogues opened; the PCAF registry row still says 2022 while the code implements Dec-2025. | Keeps the "current as of" promise true | S | P0 |
| 4 | **The headline number is missing from the data exports** (U1) | XLSX and CSV carry 5D, SDG and greenwashing, but not expected impact (P10 / P50 / P90), the evidence plan, negative impacts or the contribution split. Chinese text in the CSV opens as mojibake in Excel (no BOM). | Analysts can use the workbook for the figure the IC actually reads | S | P0 |
| 5 | **Methodology stamp does not cover what drives the verdict** (C2) | The footer and exports say "Methodology v1.2.0". The verdict comes from v2.yaml (2.1.0). `contribution_rubric.yaml` and `negative_impacts.yaml` are in no hash, so editing them changes scores without changing any stamp. | Restores "two reports are comparable only when the stamp matches" | S | P0 |
| 6 | **Dark-theme reports print white-on-white** (U2) | The print stylesheet forces a white page but leaves the dark ink tokens in place. | Print-ready really means print-ready | S | P0 |
| 7 | **One verdict in every memo format; suggested IC conditions** (C3, F1) | The HTML memo shows the v2 gate; Markdown / DOCX section 8 and the PPTX still print the v1 recommendation. Every memo says "No binding impact targets were set" although the deck's own targets and the evidence plan are at hand. | The memo becomes consistent and gives the IC conditions to adopt | M | P1 |
| 8 | **Example fund thesis applied silently** (C4) | With no `fund_thesis.yaml`, every memo is headed "Fund: Example Climate Fund I" and gated on its climate SDG weights, including a microfinance deck. `assess` has no `--thesis` option. | Stops a placeholder from looking like the fund's own policy | S | P1 |
| 9 | **Reach, ask and tCO2e parsing errors** (C5) | A funding goal ("USD 10m to reach 1 million students") becomes reach; the ask is not found under a "# The ask" heading; R$ / S$ / A$ are read as US$; cumulative tCO2e is multiplied by duration. | Fixes the inputs with the largest effect on expected impact | M | P1 |
| 10 | **Only the impact report is translated** (U3) | With `--lang zh-HK` the IC memo and DD report are byte-identical to English. Inside the translated report, claim types, the methodology footer and target status stay English; the zh-CN phrasebook carries Hong Kong wording (量度, 甚么, 「」). | A Chinese-reading IC gets a full pack | M–L | P1 |
| 11 | **Contradicting figures are dropped silently** (C6) | Two different values for the same metric: the first wins, the second vanishes. No plausibility checks (reach above a country's population, percentages above 100). | Catches the errors a human reviewer looks for first | M | P1 |
| 12 | **Exclusion screening is not run by `assess`** (C7) | `exclusion_criteria.yaml` is only read by the agent tool, so the "fails thesis: exclusion" path can only fire through the thesis's forbidden-sector list. | The gate does what the methodology says | S–M | P1 |
| 13 | **Gate almost never says "ready"** (C8) | Across 40 golden and held-out decks: 0 ready, 35 evidence plan, 5 fails. The two decks labelled "ready" are held back only by core-metric coverage (6 % vs 40 %), which the methodology says is never a score input. | A verdict that discriminates | M | P1 |
| 14 | **Share links: no notice, no audit, no revocation** (U4) | A shared report carries no "shared, read-only, expires" line; views are not logged; a link can only be revoked by deleting the report. | LP-grade sharing | M | P2 |
| 15 | **Deal comparison and IC one-pager** (F2, F3) | No `compare` command; `compare_deals` uses v1 scores and an arbitrary composite. No one-page IC summary. | Two of the most-asked IC artefacts | M | P2 |

---

## 1. Regulations and frameworks

### 1.1 What the repo has, and its state

| Standard | In the repo | State |
|---|---|---|
| **SFDR 1.0 PAI** | `frameworks/sfdr_pai.py` (14 mandatory + optional indicators, hard-coded), registry row `SFDR` 2022-RTS | OK for current law. The `EU-SFDR` row in `data/regulatory/packs.yaml:31-49` has no `notes`, `as_of`, `legal_basis`, `last_verified` or `source_url`, unlike its neighbours. |
| **SFDR 2.0 (proposal)** | `data/regulatory/sfdr2.yaml`, `frameworks/sfdr_recast.py`, `sfdr_pai.classify_sfdr2_category` | **Stale by one step.** Says "plenary October 2026; trilogue from Q4 2026". Parliament has since endorsed the mandate and trilogues opened (§1.3). Parliament's 20 % taxonomy-alignment floor for "Sustainable" (Council 15 %) is not recorded. `sfdr_pai.py:715` and `sfdr_recast.py:60` repeat YAML values in Python. |
| **ISSB / IFRS S1, S2** | `frameworks/issb_ifrs_s1.py`, `issb_ifrs_s2.py`, `data/issb_s2_amendments.yaml`, `data/issb_adoption.yaml` | Mostly OK. Version strings disagree ("Effective 2024-01-01", "2023", registry "S1-S2-2023"). `issb_s2_amendments.yaml` (`as_of 2025-12`) is outside the freshness gate and would fail it. `issb_reporting.py:135` hard-codes 2027-01-01. |
| **ISSB nature** | Registry row `ISSB_NATURE` "ED targeted for October 2026"; watchlist row dated 2026-10-31 | **Stale.** The ED is published (§1.3). `frameworks/tnfd.py` has no mapping to it yet. |
| **HKFRS S1** | `frameworks/hkfrs_s1.py` + `data/regulatory/hkfrs_s1.yaml`, CLI `framework hkfrs-s1` | Good tool. **Missing:** registry row, freshness-gate coverage, `framework_tool` exposure, `framework list` entry. No HKFRS S2 check. |
| **HKEX ESG Code (Appendix C2)** | Pack row `HK-HKEX-ESG` (climate metrics only, no `source_url`); HK jurisdiction profile | **Missing as an assessment.** Nothing covers Part B (paras 13–15), Part C (A1–A3, B1–B8) or Part D as a checklist. |
| **HK Taxonomy** | `frameworks/hk_taxonomy.py` + `data/hk_taxonomy.yaml` | **Inconsistent.** Registry says phase-2a; all 12 activities in the YAML are tagged phase 1. |
| **EU Taxonomy** | `frameworks/eu_taxonomy.py` | **Stale and unwired.** Cites only 2020/852, 2021/2139, 2023/2485, 2023/2486; nothing on the Omnibus simplification of Taxonomy reporting. Fully hard-coded, no registry row, not in `framework_tool`, no CLI. `docs/roadmap-v6.md:276` still lists the refresh as planned. |
| **ESRS / CSRD** | `frameworks/esrs.py`, `data/esrs_simplified_2026.yaml`, packs `EU-CSRD`, `EU-CSDDD` | OK and current (Omnibus I, revised ESRS 2026/1563). `engagements/regulatory.py:357` still says the simplified ESRS act is "targeted 2026-09"; thresholds at `:298-301` are hard-coded. |
| **VSME** | `frameworks/vsme.py`, `data/monitoring/vsme_basic.yaml` | **Inconsistent.** Legal basis hard-coded in Python (`vsme.py:321-331`); the YAML cites the 2024 EFRAG draft, not Delegated Regulation 2026/1560; datapoint ids differ between the two (`energy_mwh` vs `total_energy_mwh`). |
| **TCFD** | `frameworks/tcfd.py` | **Stale framing.** No note that the TCFD disbanded and monitoring moved to the ISSB. Still listed as a live framework in `jurisdictions.yaml` (EU, UK, Japan). No registry row. |
| **SASB** | `frameworks/sasb.py`, `data/sasb_overrides.yaml` | **Stale.** Docstring says 77 industries, about 25 are encoded; no version, no reference to ISSB stewardship; overrides file has no `as_of` / `source`. |
| **GRI** | `frameworks/gri.py` | **Stale.** Encodes Biodiversity 2016, Energy 2016, Emissions 2016. No GRI 101 (Biodiversity 2024), GRI 102 (Climate Change 2025), GRI 103 (Energy 2025), no sector standards. |
| **PCAF** | `frameworks/pcaf.py` (`pcaf-2025-12`) | Code current; **registry row says 2022** (`standards_registry.yaml:340`). Not in `framework_tool`. |
| **SBTi** | `frameworks/sbti.py` | **Stale.** Net-Zero Standard v1.2 and criteria v5.1; thresholds hard-coded (`:51-58`); nothing on Corporate Net-Zero Standard v2. No registry row. |
| **IRIS+** | `impact/catalog.py`, registry `IRIS_PLUS` 5.3c | OK. Watch-list entry exists. |
| **EDCI** | `frameworks/edci.py` 2026 | OK; hard-coded; watch the 2027 cycle. |
| **ILPA** | Watchlist row; DDQ exporter | OK. Final Portfolio Company Template due January 2027: needs an export adapter then. |
| **China MoF / SSE** | CN profile, `data/cn_sse_topics.yaml`, `data/standard_articles/sse_g14.yaml` | Profile current. `sse_g14.yaml` (`as_of 2024-05-01`) is outside the gate and its article text is synthetic (`standards_registry.py:46`). |
| **EU AI Act Art 50** | `impact/ai_provenance.py`, reviewer sign-off | OK. Art 50 marking applies from 2026-12-02 for existing systems; PPTX exports carry no marking (`mark_pptx` does not exist). |
| **California SB 253** | Pack `US-CA-CLIMATE`; `regulatory_packs.py:264-286` | Due date 2026-11-10 (today) is hard-coded in Python. The `US-SEC-ESG` pack says "in litigation" while `jurisdictions.yaml:141` records the proposed rescission of 2026-05-29. |

### 1.2 Suggested work

- **R1. HKEX ESG Code gap check** — P0, M. `data/regulatory/hkex_esg_code.yaml` (Part B paras 13–15; Part C aspects A1–A3 and B1–B8 with their KPIs; Part D by pillar), a `frameworks/hkex_esg.py` that reuses the HKFRS S1 cue pattern, `framework hkex-esg` in the CLI, `framework_tool` exposure, en / zh-HK labels. Report "comply or explain" honestly: a KPI can be met, explained, or silent. Note the phasing (LargeCap mandatory for Part D from FY2026; Scope 1 and 2 mandatory for all) and that an ISSB-compliant report is deemed to meet Part D.
- **R2. Knowledge refresh** — P0, S. Update `standards_registry.yaml` (`ISSB_NATURE`, `PCAF`; add `HKFRS_S1`, `HKEX_ESG_CODE`), `watchlist.yaml` (ISSB nature comment deadline; SFDR 2.0 trilogue), `sfdr2.yaml` status and Parliament position, the `EU-SFDR` and `HK-HKEX-ESG` pack rows (provenance, source URL).
- **R3. Widen the freshness gate** — P1, S. `knowledge.KNOWLEDGE_FILES` skips `regulatory/hkfrs_s1.yaml`, `issb_s2_amendments.yaml`, `monitoring/vsme_basic.yaml`, `methodology/ghg.yaml`, `tracked_standards.yaml`, `living_wage_benchmarks.yaml`, `disclosure_checklists/climate.yaml`, `standard_articles/sse_g14.yaml`. Add them (fixing the three that would fail). `hkfrs_s1.yaml` uses `status: illustrative` where the gate reads `data_status`.
- **R4. `framework list` is out of date** — P1, S. The CLI lists 7 frameworks (`cli.py:838-853`); `framework_tool` has 20. Generate the list from one table.
- **R5. Registry completeness** — P1, S–M. Nine modules have no registry row (EU Taxonomy, SBTi, TCFD, SASB, GRI, TNFD, CDP, UNPRI, 2X). Add rows with version, `as_of` and source, and a test that every framework module has one.
- **R6. GRI 101 / 102 / 103 and SBTi v2** — P1, M each. Move the standards lists into sourced YAML while updating them, per the repo rule against regulatory values in Python.
- **R7. EU Taxonomy refresh** — P1, M. Encode the simplified reporting rules, move NACE hints and thresholds to YAML, expose through `framework_tool`.
- **R8. Remaining hard-coded regulatory values** — P2, M. `regulatory_packs.py:264-286`, `engagements/regulatory.py:286-301`, `vsme.py:321-331`, `regulatory_calendar.py:275-283` (which also has no HK or CN disclosure profile), `csrd_wizard.py:18`.
- **R9. HKFRS S2 check and ISSB nature mapping** — P2, M. Clone the S1 tool for S2; map `tnfd.py` to the Practice Statement once the ED text is final.
- **R10. ILPA template adapter (January 2027), EDCI 2027, SFDR 2.0 final text** — watch; build when published.

### 1.3 Facts checked outside the repo

| Fact | Source |
|---|---|
| ISSB published the Exposure Draft *IFRS Sustainability Disclosure Practice Statement 1 Nature-related Disclosures* in October 2026; 120-day comment period closing 2027-02-19; a Practice Statement is not required for a statement of compliance; draws on TNFD | https://www.ifrs.org/projects/work-plan/biodiversity-ecosystems-and-ecosystem-services/ed-cl-nature-related-disclosures/ |
| SFDR 2.0: ECON report adopted 2026-09-10; Parliament endorsed it as its negotiating mandate in early October 2026 (sources give 5 or 7 October); first trilogue expected 2026-10-22; Parliament 20 % taxonomy alignment for "Sustainable" vs Council 15 %; both back a 24-month implementation period; application late 2028 to 2029 | https://www.arthurcox.com/knowledge/sfdr-2-0-update/ (2026-10-16); https://www.legal500.com/intelligence/european-union/finance-and-banking/sfdr-20-the-overhaul-takes-shape (2026-11-09) |
| HKEX ESG Code structure: Part B paras 13 (governance), 14 (reporting principles), 15 (boundary); Part C aspects A1–A3 and B1–B8 with their KPIs (KPI A1.2 and Aspect A4 moved to Part D); Part D para 19 governance, paras 37–40 targets; ISSB-compliant reports deemed to comply with Part D (para 8); LargeCap mandatory from 2026-01-01; HKEX to consult in 2027 on HK Standards for listed PAEs, expected effective 2028-01-01 | HKEX, *Linking the ISSB Standards and HKEX ESG Reporting Code*, September 2025: https://www.hkex.com.hk/-/media/HKEX-Market/Listing/Rules-and-Guidance/Environmental-Social-and-Governance/Exchanges-guidance-materials-on-ESG/ISSBstd_esgcode.pdf |

Not verified (no source reached): whether the first SFDR trilogue took place; Part D paragraph
numbers other than 19 and 37–40; the current state of GRI 102/103, SBTi v2 and the EU Taxonomy
simplification act. Those items above rest on the code's own stated versions.

---

## 2. Report UX / UI

**Already good:** one decision-first HTML report with a verdict card, offline charts (no CDN),
A4 print rules, light and dark themes, axe-clean visual QA in CI, zh-HK / zh-CN strings with
full key parity (277 keys), signed share links with tenant and expiry, XLSX with frozen
headers and number formats.

- **U1. Data exports miss the headline** — P0, S. `exports.py:251-347`: add sheets and CSV rows for expected impact (P10 / P50 / P90, factors, drivers), the evidence plan, negative impacts and the contribution split. Write the CSV with a UTF-8 BOM (`exports.py:190`, `pipeline.py:576`). The Summary sheet formats every number as `0.0`, so a claim count reads "12.0" (`exports.py:289`). The AI provenance sheet's second table moves the freeze pane and filter (`:339-344`).
- **U2. Dark theme prints white-on-white** — P0, S. `report.css:274` sets a white page; `tokens.css:74-100` keeps `--ink: #fff`. Reset the tokens to light inside `@media print`.
- **U3. Translation coverage** — P1, M–L. (a) `--lang` reaches only the impact report (`pipeline.py:505`); the IC memo and DD report are English, `lang="en"` hard-coded in `report_v2.py:480`. (b) In the translated report: claim type (`outcome`, `intent`), the methodology footer (`report.html.j2:332`), target status, geography and the logo alt text stay English; `lang_note` still says recommendations are shown in the original language, which stopped being true in 0.19. (c) zh-CN phrasebook carries Hong Kong usage: 量度, 甚么, 「」, 最少, 受惠, 连结. (d) `impact/i18n.py` and `data/i18n/{report_strings,dashboard_keys,dd_checklist_*}.yaml` are used by nothing but one test; DD questions therefore stay English. (e) No test for placeholder parity or for Simplified characters in zh-HK.
- **U4. Share links** — P2, M. No "shared · read-only · expires" notice on the page, no view audit (`reports_api.py` `shared()` records nothing), no per-link revocation or list of live links, a new token on every edition change, English-only error page.
- **U5. PDF polish** — P1, S–M. No running header (company, "Confidential") on pages 2+ (`pdf.py:45`); no tagged PDF or bookmarks (`pdf.py:39-53`); the WeasyPrint path has no page numbers; no CJK font check, so a server without CJK fonts prints boxes; no `thead` repeat rule; the table of contents is hidden in print.
- **U6. Draft and narrative wrappers break HTML and PDF** — P1, S. `impact_report_tool.py:618-645, 968-987` put text before `<!DOCTYPE>` and after `</html>`; both reach the PDF.
- **U7. Viewer** — P1, M. No print / PDF button; downloads are always the English full edition whatever is on screen; sign-off uses two `prompt()` dialogs and does not regenerate the stored files, so the downloaded HTML and DOCX lack it.
- **U8. LP / regulator / public editions open without a summary** — P1, S. The verdict and "change our mind" sections are dropped (`decision_report.py:51-56`) and nothing replaces them.
- **U9. DOCX and PPTX** — P2, M. DOCX: table header rows do not repeat, no East Asian font, English only. PPTX: four text slides on the 4:3 default, no branding, no expected impact, no AI disclosure, no tests.
- **U10. Branding is split** — P2, M. `branding.py` (from the fund thesis) feeds only the classic report; the decision report takes only `args.branding`; the web view, share links and `assess` pass none. URL rules differ between the two.
- **U11. Portfolio home and dashboard** — P2, M. Heat-map rows do not link to their reports (`reports_api.py:199-207`); no sort or filter; the footer always says "no generative AI". Dashboard: no PDF / DOCX download, CSV upload fails on a BOM, comparison is one table.
- **U12. Classic report still loads Plotly from a CDN** (`impact_report_tool.py:2709`), as does the iXBRL path built on it — P2, S. Offline, charts are blank.

---

## 3. Content quality: evidence, scoring, narrative

**Already good:** expected impact with seeded Monte Carlo ranges and variance drivers;
parameters in versioned YAML; evidence quality kept apart from impact; page citations on every
claim from a PDF; negative impacts by severity × likelihood with quoted controls; perturbation
tests; a 30-deck held-out set gating CI.

- **C1. Negation** — P0, S. `extractors/regex_extractor.py:70` (`counterfactual` alone triggers `controlled_evaluation`), `negative_impacts.py:50` (control phrases), `greenwashing.py` `_score_verification`. Add one negation-window helper and use it in all three. Tests: the three sentences in §0 item 1.
- **C2. Stamp** — P0, S. `methodology.py:40` hashes v1 + scoring config + SDG keywords. Add `methodology/v2.yaml`, `contribution_rubric.yaml`, `negative_impacts.yaml`, `exclusion_criteria.yaml`; show the expected-impact version in the footer, summary and exports.
- **C3. One verdict across memo formats** — P1, S. `ic_memo.py:263` (Markdown / DOCX) and `:540` (PPTX) print the v1 recommendation while the header shows the v2 label.
- **C4. Example thesis** — P1, S. `fund_thesis._candidates` falls back to `fund_thesis.example.yaml` without setting `is_default`. Mark it, say so in the memo, add `assess --thesis`.
- **C5. Parsing** — P1, M. `expected_impact.py`: targets leak into reach (`_TARGET_WORDS`, `:96`); reach is the largest people-count whatever the noun (`:204`); "0.21 SD" becomes a 21 % depth (`:212`); any tCO2e is per-year (`:221`); the ask is read from text that excludes "The ask / Funding / Raise" sections (`:228`, `text_sections.py:27`); `R$`, `S$`, `A$` map to USD and MXN, ZAR, NGN, BRL are unsupported; a second FX table duplicates `fx.py`; "12 000 households" yields nothing.
- **C6. Contradictions and plausibility** — P1, M. `sdk.py:154,161` uses `setdefault`: keep every value per metric and report differences above 10 % in the ledger and the evidence plan. Flag reach above national population, percentages above 100 (now capped silently, `expected_impact.py:217`), implausible tCO2e per US$.
- **C7. Exclusions in `assess`** — P1, S–M. `pipeline.py:326-331` never passes `exclusion_pass`.
- **C8. Verdict spread** — P1, M. The completeness condition (`expected_impact.py:533`, `v2.yaml:89-93`) blocks "ready" for decks with strong evidence. Either drop it from the gate (the methodology already says completeness is not a score input) or lower it and say so. Report per-class verdict recall in the held-out evaluation: 90 % accuracy is close to the 77 % a constant "evidence plan" would get, and recall for "ready" is 0 of 2.
- **C9. Evidence plan ignores the dominant driver** — P1, M. When Duration or Attribution drive most of the variance (57 % on the pig-farm deck) the plan still says "report core metrics". Add plan items for every driver, and a "this would move the gate to Ready" marker by re-running the gate with that input upgraded.
- **C10. Weights still in Python** — P1, M. `expected_impact.py:518` (60 / ≥ 2), `greenwashing_reviewer.py:227-246`, `negative_impacts.py:23`, `greenwashing.py:472-477, 540-546, 605-613`, `contribution_split.py:103`, `decision_workflow.py:403-405`.
- **C11. NESTA ladders disagree** — P1, S. `dd_checklist.py:407-419` still rates an RCT as level 5 and "kpi / tracked" as level 3; `extractors/base.py:181-187` gives level 3 for third-party verification (assurance is not causality) and level 2 for any number.
- **C12. Stale evidence** — P2, M. `extractors/base.py:223-231` drops `metric_year`; `ImpactClaim` has no period, so a 2019 figure in a 2026 deck cannot be flagged.
- **C13. SDG confidence and targets** — P2, S–M. "Medium confidence" is a score band: SDG 1 scores 30 "medium" with no matching metric. The taxonomy has 153 of 169 targets; recommendations take `goal.targets[:3]` by position (`sdg_mapper.py:545`).
- **C14. Residual keyword effects** — P2, M. 5D keyword boosts (`five_dimensions.py:219-224`); in `scoring_config.yaml` "evidence" lowers the (higher-is-better) Risk score while "pollution" raises it; `_count_controls` is a substring match.
- **C15. Bugs** — P1, S. `bayes.fold` iterates its stream twice, so a generator loses contradicting evidence (`bayes.py:77-78`). `lp_report_view` sums P50s across companies and stakeholder types (`company_record.py:228-238`). Annual actuals are re-scored through the forward-looking model, so probability of success and deadweight priors are applied to results that already happened (`annual_monitoring.py:216-218`).
- **C16. Sector and Chinese extraction** — P2, M. Held-out sector accuracy 77 % (water read as education or waste; three greenwashers get no sector); Chinese fact recall 0–1 of 3 on three decks.
- **C17. Citations stop at the claim** — P2, M. Expected-impact rows carry the sentence but no page; the IC memo shows no claims, pages, drivers, contribution split or negative impacts.

---

## 4. New features for an impact fund or IC

- **F1. Suggested IC conditions** — P1, M. Turn the deck's own targets and the top evidence-plan items into conditions precedent, covenants and term-sheet KPIs (`TargetCondition` exists, only the agent tool uses it), print them in memo section 7, and build the annual results request from them (`annual_monitoring.py:82-108` asks fixed questions today).
- **F2. `impact-vision compare a.pdf b.pdf`** — P2, M. Side-by-side expected impact, evidence quality, gate, top negatives; replace the composite in `decision_workflow.compare_deals`.
- **F3. IC one-pager** — P2, M. One printed page: verdict, expected impact range, three reasons, three conditions, top negative impact.
- **F4. Re-run diff** — P2, M. "What changed since the last assessment" for a company record (roadmap W3.2 lists it; not found).
- **F5. `assess` options** — P1, S. `--thesis`, `--stage`, several files at once (`assess_files` already supports it), `--save`; the help text still says ".pdf, .txt, .md" though DOCX and PPTX work.
- **F6. DD questions ranked by what moves the verdict** — P1, M. Order `select_questions_for_document` by the variance drivers and gate reasons instead of static priority.
- **F7. Benchmarks in v2 units** — P2, L. Person-years and tCO2e per US$1m by sector, so the headline number has a comparator. Needs data and the calibration study.
- **F8. Portfolio view of expected vs actual** — P2, M. A fund-level page from the company records, grouped by stakeholder type rather than summed.
- **F9. HK-specific pack** — P2, M. One command that runs HKEX ESG Code + HKFRS S1 + HK Taxonomy on an issuer's report and prints a single gap list in Traditional Chinese.
- **F10. Calibration study** — needs people. Every v2 parameter is still `status: illustrative`; the kit is ready (0.19.1) and waits for 2–3 practitioner raters.

---

## DONE notes (2026-11-10)

Branch `claude-improvements-20261110`, 12 commits on top of `a1f5ed7` (0.19.1): this review, ten
implementation commits and these notes. Nothing was pushed.

### What was implemented

| Shortlist item | Status | Commit |
|---|---|---|
| — this review | written first, committed on its own | `3c02d92` |
| 1. Negated evidence (C1) | Done. `impact/negation.py`, used by the evidence-signal extractor, negative-impact controls, greenwashing verification and control counting. English and Chinese; planned evidence ("we plan to run an RCT") is treated the same way. | `483b614` |
| 2. HKEX ESG Code gap check (R1) | Done. 65 provisions in `data/regulatory/hkex_esg_code.yaml` (en + zh-HK), `frameworks/hkex_esg.py`, `impact-vision framework hkex-esg`, `framework_assess` (`hkex_esg`, and `hkfrs_s1` exposed too), registry rows. Also R4: `framework list` now comes from one table. | `d3849db` |
| 3. Knowledge refresh (R2), part of R3 | Done for the facts verified in §1.3. The freshness gate now covers both HK checklists (427 rows). | `d3849db`, `ae0a423` |
| 4. Exports (U1) | Done. Four new workbook sheets, Summary rows, CSV rows, UTF-8 BOM, whole-number formats, AI provenance split. | `53008ed` |
| 5. Methodology stamp (C2) | Done. Both versions shown; the hash covers v2.yaml, the contribution rubric and the negative-impact catalogue. | `468da25` |
| 6. Dark-theme print (U2) | Done, and checked in Chromium (h1 was white in print, now dark). | `edf8c81` |
| 7. One verdict; suggested IC conditions (C3, F1 first half) | Done for Markdown, Word, PowerPoint and HTML. Conditions come from the evidence plan and the company's stated targets. | `44c71d1` |
| 8. Example thesis (C4), `assess --thesis` (part of F5) | Done. | `44c71d1` |
| 9. Parsing (C5) | Done for goals read as reach, the ask's location, currency symbols and cumulative tonnes. **Not done:** reach as "largest people-count whatever the noun", effect sizes ("0.21 SD") read as a percentage, "12 000 households". | `09db1ba` |
| 10. Translation (U3) | **Partly.** Done: claim types, target statuses, language note, logo alt text, zh-CN wording, three consistency tests. **Not done:** the IC memo and DD report are still English with `--lang`; `impact/i18n.py` and its YAML files are still unused. | `33f95ed` |
| 11. Contradictions (C6) | Done for conflicting figures (`impact/consistency.py`). **Not done:** plausibility checks (reach above population, percentages above 100). Also fixed here: `bayes.fold` (C15, first bug). | `7958cb4` |
| 12–15 (exclusions in `assess`, verdict spread, share links, compare / one-pager) | Not started. | |

Everything else in §1–§4 is untouched.

### Tests and builds

Run from the repo root with the project's `.venv` (Python 3.13):

| Command | Result |
|---|---|
| `pytest tests/` (with `IMPACT_VISION_CHROMIUM` set so `tests/visual` runs) | **1,864 passed**, 7 skipped, 1 xfailed, **2 failed** |
| `ruff check src/` (ruff 0.15.22, the CI pin) | clean |
| `mypy --ignore-missing-imports` on the CI list plus the three new modules | clean |
| `python scripts/check_knowledge.py` | 427 rows, 0 stale, 0 missing |
| `python scripts/build_tool_reference.py --check` | up to date |
| `python -m impact_vision.impact.extraction_eval --extractor regex --summary` | F1 0.976 (gate 0.95) |
| `python scripts/run_heldout_eval.py` | unchanged: facts F1 0.83, sector 77 %, geography 100 %, SDG 93 %, greenwashing 90 %, verdict 90 % |
| `python scripts/check_imports.py --verify-init / --smoke / --registry` | pass |
| `bandit -q -ll -r src/impact_vision/{impact,web,api_gateway}` | no findings |

The baseline on `a1f5ed7` was 1,784 passed, 11 skipped, 2 failed. The pass count rose by 80: the tests
added on this branch (10 new or extended test files), plus existing tests that were skipped at baseline
because `playwright`, `python-docx` and `python-pptx` were not installed.

**The two failures are the same two as on `main` and come from this machine, not the code.** I left both alone:

- `tests/test_v7_wave5_package.py::test_module_entry_points` — `.venv/lib/python3.13/site-packages/impact_vision/`
  holds a leftover stub (`__init__.py` only) from a 0.16 install that shadows `src/` in a subprocess. With
  `PYTHONPATH=src` the test passes. Fix: delete that folder or `pip install -e ".[dev]"` again.
- `tests/test_v7_wave5_package.py::test_wheel_excludes_unused_subpackages` — a top-level `ohmo/` folder
  containing only `__pycache__` remains from before the package was removed. Fix: delete it.

Not run: the frontend TypeScript check (no frontend files changed), `pip-audit`, the wheel smoke test.

### Things to know

- **Every report's config hash changes once** (commit `468da25` widens what is hashed, and `v2.yaml` gained
  two blocks). Reports made before and after this branch are not comparable by stamp.
- **`demo/` was not regenerated.** Its committed HTML / JSON still show the old stamp and lack the new
  sections. Run `python demo/generate_demo.py` at release.
- **Scores did not move** on the three sample decks, the 10 golden decks or the 30 held-out decks. The fixes
  change results only for decks that deny evidence, state a goal as reach, give a running total of tonnes,
  or contradict themselves.
- **The HKEX checklist's cues are heuristics** (`cue_status: illustrative`). The provisions and their
  wording are sourced from HKEX; whether a report satisfies one still needs a reader. Part D paragraph
  numbers are given only where HKEX's linkage document cites them (19, 37–40).
- **Local environment changes** (inside `.venv`, not committed): installed `playwright`,
  `axe-playwright-python`, `python-docx`, `python-pptx` and `opencc-python-reimplemented` (all already
  named by the project's extras or build script) to run the visual, Office and phrasebook paths.
- `AGENTS.md` is still at 0.17.1 wording (22 framework modules); `CLAUDE.md` and `README.md` are current.
- Version and release: `pyproject.toml` is still 0.19.1 and the CHANGELOG entries sit under "Unreleased".
