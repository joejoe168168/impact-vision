# ESG Toolbox Implementation Plan

This plan is the handoff contract for integrating the 33-tool ohESG ESG Practice Toolbox into Impact Vision. The ohESG landing page is the canonical source for each tool's initial scope, title, categorization, and short description. Official/public sources are used to support code logic where the tool touches compliance, reporting, rating methodology, or carbon accounting.

Source anchors reviewed:

- ohESG Toolbox landing page: `https://tool.ohesg.com/`
- ohESG GHG Protocol page: `https://tool.ohesg.com/ghg/`
- GHG Protocol official standards and guidance: `https://ghgprotocol.org/standards-guidance`
- GHG Protocol calculation tools and guidance: `https://ghgprotocol.org/calculation-tools`
- EcoVadis public methodology: `https://support.ecovadis.com/hc/en-us/articles/115002531507-What-is-the-EcoVadis-methodology`
- European Commission CBAM legislation and guidance: `https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en`
- IFRS/ISSB sustainability standards knowledge hub: `https://www.ifrs.org/sustainability/knowledge-hub/introduction-to-issb-and-ifrs-sustainability-disclosure-standards/`
- EFRAG ESRS Set 1: `https://www.efrag.org/en/sustainability-reporting/esrs-workstreams/sector-agnostic-standards-set-1-esrs`

## Architecture

- `openharness.impact.toolbox.models`
  - Owns stable data contracts: `ToolboxToolSpec`, `RequirementItem`, `SourceRecord`, `AssessmentQuestion`, `CalculatorMethod`, and `ToolboxAssessmentResult`.
  - All source-backed modules must include source URLs and `as_of`.

- `openharness.impact.toolbox.registry`
  - Static registry for all 33 ohESG tools.
  - Each spec stores: stable `tool_id`, English Impact Vision title/description, ohESG URL, categories, tags, aliases, jurisdiction/sector hints, public sources, requirements, and supported actions.
  - The registry is runtime-safe and does not fetch the website during user tool calls.

- `openharness.impact.toolbox.assessors`
  - Deterministic readiness/checklist logic.
  - It must not claim proprietary rating or legal scoring. It only checks whether user-supplied text, product codes, countries, and Impact Vision metrics appear to evidence public/checklist requirements.

- `openharness.impact.toolbox.ingest`
  - Maintainer-only extraction helpers for refreshing source snapshots from public pages.
  - It extracts the ohESG landing-page `TOOLS` array and page-level JSON such as `window.__GHG_DATA`, `window.__ECOVADIS_DATA`, and `window.__GRI_DATA`.
  - Generated data must be reviewed before committing.
  - `scripts/refresh_ohesg_toolbox_snapshot.py` writes the reviewed source snapshot to `data/raw/ohesg_toolbox_snapshot.json`.
  - The same script writes 33 separate source profiles under `data/raw/ohesg_toolbox/<tool_id>.json` to avoid overcrowding a single registry or script.

- `openharness.impact.toolbox.source_index`
  - Runtime loader for the reviewed per-tool source profiles.
  - Exposes page title, meta description, source tags, source keywords, page headings, links, embedded dataset keys, and embedded dataset summaries.

- `openharness.tools.impact.esg_toolbox_tool`
  - Public agent tool: `esg_toolbox`.
  - Actions: `list`, `get`, `search`, `methodology`, `checklist`, `assess`, `crosswalk`, `source_profile`.
  - Registered in `create_default_tool_registry`, so it is available through CLI, API, MCP, and agent sessions.

## Coding Rules For Follow-up Agents

- Preserve all 33 IDs from ohESG exactly: use kebab-case IDs from the site.
- Use ohESG for core scope and UX terminology, but official sources for compliance/rating/carbon logic.
- Every tool must have at least:
  - 1 ohESG secondary source.
  - 1 official/public methodology or regulator source when available.
  - 3 to 6 normalized requirements.
  - A checklist path and readiness assessment path.
- Completion means:
  - Registry spec reviewed against the ohESG tool page.
  - Official source added where applicable.
  - Requirements are specific enough to drive `checklist` and `assess`.
  - Unit tests cover list/get/search/checklist/assess or a scenario test covers the module.
  - The checklist below is marked complete.

## 33-tool Checklist

- [x] `carbon-calculator` | ohESG: "碳计算器" | Core: ISO 14064-1 and GHG Protocol, general manufacturing, Scope 1/2/3 accounting. Build complete: calculator-specific requirements for Scope 1 fixed/mobile/process/fugitive emissions, Scope 2 purchased energy and green certificates, manufacturing Scope 3 categories, transparent formulas, official GHG/ISO sources, checklist, readiness assessment, and tests.
- [x] `material` | ohESG: "双重重要性评估" | Core: impact materiality + financial materiality, visual matrix. Build: double-materiality checklist and ESRS/GRI mapping.
- [x] `msci` | ohESG: "MSCI ESG 评级助手" | Core: MSCI key issue interpretation for 160 industries. Build: industry materiality and evidence gap assistant.
- [x] `ecovadis` | ohESG: "EcoVadis 评级助手" | Core: four themes, 21 criteria, first/reassessment workflow. Build: evidence readiness across policies, actions, results, and theme coverage.
- [x] `cdp` | ohESG: "CDP 评级助手" | Core: CDP questionnaire modules, scoring focus, evidence preparation. Build: climate/water/forest questionnaire readiness.
- [x] `csa` | ohESG: "CSA 评级助手" | Core: S&P Global CSA 62 industry methodology lookup. Build: CSA topic readiness by sector.
- [x] `gri` | ohESG: "GRI 标准学习与速查" | Core: 41 standards, 140 disclosures, 96 sector topics. Build: search, content-index checklist, disclosure evidence gaps.
- [x] `esrs` | ohESG: "ESRS 标准速查" | Core: 12 ESRS standards, disclosure requirements, interactions. Build: ESRS readiness and CSRD export/customer request support.
- [x] `iss` | ohESG: "ISS 评级助手" | Core: ISS STOXX corporate assessment methodology query. Build: rating evidence checklist.
- [x] `cbam-export` | ohESG: "CBAM 商品出口查询" | Core: CBAM covered goods lookup, CN code search, bilingual. Build: CN/HS applicability input path.
- [x] `cbam-steel` | ohESG: "CBAM 钢、铝业碳核算" | Core: CBAM steel/aluminum product emissions preparation. Build: embedded emissions data checklist.
- [x] `cbam` | ohESG: "CBAM 合规助手" | Core: regulation navigation, Omnibus revisions, decision tree, cost estimator, carbon price. Build: EU CBAM applicability and deadline readiness.
- [x] `glossary` | ohESG: "ESG 速查工具" | Core: ESG topics/indicators + GICS lookup. Build: terminology/search helper and framework-routing suggestions.
- [x] `sbti` | ohESG: "SBTi 助手" | Core: corporate standards, sector resource states, terms, reading path, criteria/tools, thresholds, methods, five-year review. Build complete: target-boundary readiness, near-term ambition, net-zero ambition, Scope 3/supplier engagement, sector routing, validation/status/five-year review planning, SBTi methods, official sources, checklist, readiness assessment, and tests.
- [x] `smeta` | ohESG: "SMETA 审计准备" | Core: Sedex SMETA 7 framework, workplace requirements, management-system self-check. Build: supplier audit preparation.
- [x] `sa8000` | ohESG: "SA8000 助手" | Core: SA8000:2026 decent-work standard, management system and performance criteria. Build: labor certification readiness.
- [x] `aa1000` | ohESG: "AA1000 标准学习" | Core: AccountAbility principles and assurance standards. Build: assurance-scope readiness.
- [x] `eu-green-deal` | ohESG: "欧盟绿色协议法规速查" | Core: EU Green Deal laws, clauses, compliance timeline for China exporters. Build: regulation router.
- [x] `battery` | ohESG: "EU 电池法规合规工具包" | Core: battery classifier, DPP fields, carbon-footprint guidance, checklist, timeline. Build: product passport + carbon-footprint readiness.
- [x] `eudr` | ohESG: "EUDR 反毁林法规合规工具包" | Core: product query, country risk, DDS fields, geolocation. Build: deforestation due-diligence checklist.
- [x] `csddd` | ohESG: "CSDDD 供应链尽职调查工具包" | Core: impact assessment, risk-area identification, supplier self-check. Build: HRDD/CSDDD supplier readiness.
- [x] `espr` | ohESG: "ESPR 生态设计可持续产品工具包" | Core: product category query, DPP, ecodesign requirements. Build: ESPR/DPP readiness and `product_passport` mapping.
- [x] `amfori-bsci` | ohESG: "amfori BSCI 评级助手" | Core: 13 performance areas, 81 audit questions, A-E rating, improvement. Build: audit gap assessment.
- [x] `rba` | ohESG: "RBA 评级助手" | Core: Code 8.0 five sections, 42 clauses, VAP 200 score, conflict minerals, forced labor. Build: RBA supplier evidence checklist.
- [x] `icma` | ohESG: "可持续债券导航" | Core: GBP/SBP/SBG/SLBP/CTB, decision tree, KPI library, SPO, panda bonds. Build: sustainable bond framework readiness.
- [x] `issb` | ohESG: "可持续披露助手" | Core: ISSB/IFRS S1+S2 four pillars, SASB groups, interoperability. Build: ISSB readiness and crosswalk.
- [x] `climate-bonds` | ohESG: "气候债券导航" | Core: CBI Climate Bonds Standard v4.3, taxonomy, certification, verifier matrix. Build: taxonomy/certification readiness.
- [x] `nav` | ohESG: "ESG 生态导航" | Core: 103 ESG institutions, five roles, 1997-2026 timeline, 28 filters. Build: source/institution router.
- [x] `carbon-iso` | ohESG: "碳相关 ISO 标准学习指南" | Core: ISO 14064/14067/14068/14090/14091/14092, selectors and checklists. Build complete: ISO standard selector, mitigation/adaptation routing, 14064-1 organization inventory readiness, 14067 product CFP readiness, 14068 carbon-neutrality claim readiness, 14090/14091 adaptation-risk readiness, methods, official ISO sources, checklist, readiness assessment, and tests.
- [x] `aws` | ohESG: "水资源管理标准助手" | Core: AWS Standard V3.0, five steps, 50 Core + 15 Gold + Platinum certification. Build: water stewardship readiness.
- [x] `irma` | ohESG: "IRMA （负责任采矿）助手" | Core: IRMA mining standard v1.0, 4 principles, 26 chapters, achievement levels, chain of custody. Build: responsible mining supplier checklist.
- [x] `conflict-minerals` | ohESG: "冲突矿产合规助手" | Core: OECD five-step due diligence, RMI tools, Dodd-Frank, EU 2017/821, EU CRMA, CCCMC, 3TG/cobalt/mica. Build: minerals traceability checklist.
- [x] `ghg` | ohESG: "GHG Protocol 导航" | Core: GHG Protocol standards family, Scope 1/2/3, official calculation tools and emission factors, China grid factors, 8-step inventory path. Build complete: registry spec, official GHG Protocol sources, checklist, readiness assessment, metric crosswalk, default tool registration, and tests.

## GHG Module Completion Notes

The `ghg` module is complete for the first implementation slice:

- Registry has ohESG GHG URL and official GHG Protocol source URLs.
- Requirements cover inventory boundary, activity data/emission factors, and calculation review/assurance.
- `esg_toolbox get tool_id=ghg` returns module metadata and sources.
- `esg_toolbox checklist tool_id=ghg` returns actionable questions.
- `esg_toolbox assess tool_id=ghg` evaluates provided text and metrics without proprietary scoring claims.
- `esg_toolbox crosswalk tool_id=ghg reported_metrics={"OI4112": "..."}` maps Impact Vision GHG metric evidence to GHG/ESRS/ISSB/GRI uses.

## Carbon Calculator Module Completion Notes

The `carbon-calculator` module is complete for the second implementation slice:

- Registry has the ohESG carbon calculator URL and official GHG Protocol/ISO 14064-1 source URLs.
- Requirements reflect the ohESG calculator structure: Scope 1 stationary/mobile/process/fugitive emissions, Scope 2 purchased electricity/thermal energy and certificate treatment, selected manufacturing Scope 3 categories, and summary/intensity/trend outputs.
- Methodology exposes transparent calculation methods: activity data x emission factor, stationary combustion energy conversion, fugitive gas GWP conversion, and Scope 2 location/market calculation.
- `esg_toolbox methodology tool_id=carbon-calculator` returns the calculation methods and source policy.
- `esg_toolbox assess tool_id=carbon-calculator` scores readiness based on user-supplied evidence and metrics without making a verification claim.

## Carbon ISO Module Completion Notes

The `carbon-iso` module is complete for the third implementation slice:

- Registry has the ohESG carbon ISO guide URL and official ISO source URLs for climate standards, ISO 14064-1, ISO 14064-2, ISO 14067, and ISO 14091.
- Requirements reflect the ohESG guide structure: standard selection, 14064-1 organization inventory, 14067 product carbon footprint, 14068 carbon-neutrality claim, and 14090/14091 adaptation-risk readiness.
- Methodology exposes selector/workflow logic: three-question ISO selector, 14064-1 six-step inventory workflow, 14067 seven-step CFP workflow, and 14091 vulnerability logic.
- `esg_toolbox methodology tool_id=carbon-iso` returns routing methods and source policy.
- `esg_toolbox assess tool_id=carbon-iso` scores readiness based on supplied evidence and routes users to missing ISO preparation steps.

## SBTi Module Completion Notes

The `sbti` module is complete for the fourth implementation slice:

- Registry has the ohESG SBTi assistant URL and official SBTi/GHG Protocol source URLs.
- Requirements reflect the ohESG SBTi structure: corporate standards, near-term criteria, net-zero standard, supplier engagement, sector resource routing, validation/status, and five-year review.
- Methodology exposes the six-decision roadmap, threshold screen, sector matrix, and five-year review planner as tool methods.
- `esg_toolbox methodology tool_id=sbti` returns SBTi methods and source policy.
- `esg_toolbox assess tool_id=sbti` scores readiness based on supplied inventory, target, sector, Scope 3, and validation evidence without claiming SBTi approval.

## Follow-up Implementation Order

All 33 modules are now implemented in the unified `esg_toolbox` registry, grounded in the scraped ohESG snapshot and supplemented with public/official sources for compliance, rating, disclosure, carbon, assurance, and supplier-readiness logic.

Remaining follow-up is product depth rather than initial module availability:

1. Refresh `data/raw/ohesg_toolbox_snapshot.json` when ohESG changes the landing page or module pages.
2. Add richer customer-style scenario fixtures for each cluster.
3. Expand API/Web Console examples for `esg_toolbox`.
