# Impact Vision

**Open-source impact due diligence for VC and impact funds.** Drop in a pitch
deck or investment memo and get an investment-committee-ready verdict, an
evidence ledger, SDG and 5-Dimension scoring, a greenwashing review and
print-ready reports in English, 繁體中文 or 简体中文. Runs offline; an LLM is optional.

Built on [OpenHarness](https://github.com/HKUDS/OpenHarness), with GIIN's IRIS+
catalogue, the UN SDGs, the 5 Dimensions of Impact and 20+ ESG and regulatory
frameworks (ISSB, ESRS/VSME, SFDR, TCFD, SASB, GRI, PCAF, SBTi, EU Taxonomy,
TNFD, CDP, TISFD, 2X, SBTN). Release notes: [CHANGELOG.md](CHANGELOG.md) ·
roadmap: [docs/roadmap-v8.md](docs/roadmap-v8.md).

![Decision-first impact report: verdict, headline numbers and what would change our mind](docs/images/report-overview.png)

## See it in 60 seconds

```bash
git clone https://github.com/joejoe168168/impact-vision.git && cd impact-vision
pip install -e .
impact-vision demo                     # three fictional sample decks → reports in your browser
impact-vision assess your_deck.pdf --open --pdf
```

No API key or setup is needed. Browse ready-made output in [`demo/`](demo/)
(open [`demo/index.html`](demo/index.html)).

## Screenshots

<table>
<tr>
<td width="50%"><img src="docs/images/web-chat.png" alt="Browser chat UI with starter cards"><br><em><b>Browser chat</b> (<code>impact-vision serve-web</code>): <b>Analyze a pitch deck</b> works offline, no API key.</em></td>
<td width="50%"><img src="docs/images/report-glance.png" alt="SDG wheel and impact pathway"><br><em><b>Impact at a glance</b>: SDG wheel of material goals and the impact pathway from the deck's own claims.</em></td>
</tr>
<tr>
<td><img src="docs/images/web-report-viewer.png" alt="Report viewer with share link"><br><em><b>Report viewer</b> in the browser: switch edition, language and theme; <b>Share…</b> makes a signed read-only link.</em></td>
<td><img src="docs/images/portfolio-home.png" alt="Portfolio home"><br><em><b>Portfolio home</b>: pipeline by IC gate, 5D/SDG heat-map, SFDR/CSRD/SB 253 deadlines and evidence to review.</em></td>
</tr>
<tr>
<td><img src="docs/images/engagements.png" alt="Engagement view"><br><em><b>Engagements</b>: deliverables, checklist progress and what is overdue or due soon, saved across restarts.</em></td>
<td><img src="docs/images/report-sdg.png" alt="SDG alignment"><br><em><b>SDG alignment</b>: material goals only, scored from goal-specific evidence.</em></td>
</tr>
<tr>
<td><img src="docs/images/report-5d.png" alt="5 Dimensions with sector benchmark"><br><em><b>5 Dimensions</b> against the sector benchmark, with an evidence label per dimension.</em></td>
<td><img src="docs/images/report-evidence.png" alt="Evidence ledger"><br><em><b>Evidence ledger</b>: every claim with its NESTA level, verification signals and mapped IRIS+ metric.</em></td>
</tr>
<tr>
<td><img src="docs/images/report-pdf.png" alt="A4 PDF pages"><br><em><b>Print-ready PDF</b> (A4, page numbers) via <code>--pdf</code>.</em></td>
<td><img src="docs/images/report-zh-hk.png" alt="Traditional Chinese report"><br><em><b>繁體中文 / 简体中文</b> reports via <code>--lang zh-HK</code> or <code>zh-CN</code>.</em></td>
</tr>
<tr>
<td><img src="docs/images/report-dark.png" alt="Dark theme"><br><em><b>Dark mode</b>: follows the reader's system setting, with a validated palette.</em></td>
<td><img src="docs/images/report-greenwashing.png" alt="Greenwashing review"><br><em><b>Greenwashing review</b>: risk components against the finding threshold.</em></td>
</tr>
<tr>
<td><img src="docs/images/ic-memo.png" alt="IC memo"><br><em><b>IC memo</b> (HTML, PDF, Word) with the gate result and thesis fit.</em></td>
<td><img src="docs/images/dd-report.png" alt="DD questionnaire helper"><br><em><b>DD questionnaire helper</b>: risk-ranked areas and questions to send.</em></td>
</tr>
<tr>
<td><img src="docs/images/investee-portal.png" alt="Investee data portal"><br><em><b>Investee data portal</b>: an offline, single-file form for collecting data.</em></td>
<td><img src="docs/images/gallery.png" alt="Results gallery"><br><em><b>Results gallery</b> produced by <code>impact-vision demo</code>.</em></td>
</tr>
<tr>
<td><img src="docs/images/cli-assess.png" alt="impact-vision assess in a terminal"><br><em><b>One command, no API key</b>: <code>impact-vision assess deck.pdf</code> writes every deliverable.</em></td>
<td><img src="docs/images/report-mobile.png" alt="Report on a phone" width="45%"><br><em>Every report works on a <b>phone</b>.</em></td>
</tr>
</table>

## What it does

**Give it a pitch deck or memo** (PDF, text or Markdown), from the CLI, the
browser chat or the `assess_deal` agent tool. Impact Vision will:

1. **Extract every impact claim** and grade its evidence on the NESTA scale,
   spotting third-party verification, audits and controlled evaluations.
2. **Map the numbers to IRIS+ metrics** (787 in the catalogue), e.g.
   "920 tonnes CO2e avoided" → OI2764.
3. **Estimate expected impact with a range** (people reached × depth of
   change × duration, P10–P50–P90 by evidence level), then score the 5
   Dimensions of Impact and material SDGs.
4. **Run sector-specific impact due diligence** (122 questions from GIIN, PCV,
   Seraf, IMP and AFME) and list what to ask the founders.
5. **Review greenwashing risk** claim by claim.
6. **Give a verdict**: *Ready for IC*, *Evidence plan required* (with what to
   collect first) or *Fails thesis* — only for something found, never for
   missing data.
7. **Write the deliverables**:
   - decision-first impact report (HTML/PDF), in IC, LP, public and regulator
     editions;
   - IC memo (HTML/PDF/Word);
   - DD questionnaire (HTML/Word);
   - JSON summary;
   - XLSX / CSV / iXBRL exports.

   Every output states how AI and automation were used and carries the
   scoring methodology version, so two reports are comparable at a glance.

> **Using Impact Vision in a fund?** The
> [fund-manager guide](docs/fund-manager-guide.md) starts with the no-code
> path, then the Python SDK. New to the jargon (5D, NESTA, OPIM, SFDR…)? See
> the [plain-language glossary](docs/glossary.md); every report also ends with
> definitions of the terms it uses.

<details>
<summary><b>New to impact investing?</b> Key concepts</summary>

| Concept | What it means |
|---------|---------------|
| **IRIS+** | GIIN's "GAAP for impact": about 787 standard metrics for social and environmental outcomes |
| **SDGs** | The 17 UN Sustainable Development Goals and their 169 targets |
| **5 Dimensions** | What outcome, Who benefits, How much, Contribution (would it happen anyway?), Risk |
| **Impact DD** | Due diligence on whether an investment will actually create the claimed impact |
| **ESG** | Environmental, social and governance risk frameworks (SASB, GRI, TCFD, SFDR, EDCI, ISSB, ESRS…) |
| **NESTA evidence** | Five levels of evidence strength: 1 = narrative … 5 = rigorous evaluation |

</details>

## Quick Start

### 1. Install

You need **Python 3.11+** and Git. Node.js 20+ is needed only for the
interactive terminal agent.

```bash
git clone https://github.com/joejoe168168/impact-vision.git && cd impact-vision
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"                                # dev = every extra + test tools
```

The core install (`pip install -e .`) runs `demo`, `assess`, the reports and
the agent. Extras add the other surfaces: `[web]` (browser chat + REST API),
`[dashboard]` (Streamlit), `[office]` (Word/PowerPoint), `[pdf]` (PDF export;
then run `playwright install chromium`), `[tui]` and `[all]`. If
`impact-vision` isn't found, see
[install troubleshooting](docs/install-troubleshooting.md) or use
`python -m impact_vision`.

### 2. Try it without an API key

```bash
impact-vision demo                                     # sample decks → reports + gallery
impact-vision assess deck.pdf --open                   # your own deck or memo
impact-vision assess memo.pdf --sector agriculture --audience lp --lang zh-HK --pdf -o reports/
impact-vision catalog search "climate"                 # 787 IRIS+ metrics, bundled
impact-vision framework xref OI4112                    # metric across frameworks
impact-vision dd analyze memo.txt --sector energy      # DD coverage for a document
```

### 3. Connect a model for the AI agent

```bash
impact-vision setup                                    # provider wizard; keys stay local
```

| Provider | Setup choice | Best for |
|----------|--------------|----------|
| Anthropic | Anthropic-Compatible API (Claude Sonnet 5.5 by default) | Highest-quality impact analysis |
| OpenAI, OpenRouter, DeepSeek, Qwen, Gemini, Kimi, Mistral, xAI, Groq, Together | Pre-filled profile: just paste a key | Hosted models; OpenRouter reaches most of them with one key |
| Your own server | Custom endpoint (OpenAI-compatible) | vLLM, LiteLLM, LM Studio, an internal gateway |
| Ollama | Ollama profile, or `impact-vision ollama-setup --model llama3.2` | Local, private, offline (no key) |

Pick a model with reliable tool calling.

### 4. Chat in the browser or the terminal

```bash
pip install -e ".[web]" && impact-vision serve-web     # http://127.0.0.1:8787
impact-vision                                          # terminal agent (Node.js 20+)
```

Try: *"Screen this pitch deck: ./deck.pdf"*, *"What SDGs does a solar energy
company align with?"* or *"Draft the LP edition of the report for assessment 3."*

### 5. Update the IRIS+ Catalog (optional)

All 787 IRIS+ 5.3c metrics are already bundled and work out of the box. If GIIN releases a newer version of the catalog:

1. Download the new Excel file from [GIIN IRIS+](https://iris.thegiin.org/) (free registration)
2. Place it in `data/raw/`
3. Run:

```bash
impact-vision catalog load    # Parse Excel into JSON cache
impact-vision catalog stats   # Verify metric count
```

### 6. Launch the dashboard (optional)

```bash
pip install -e ".[dashboard]"   # already included in [dev]
impact-vision dashboard
```

Opens the six-tab dashboard at http://localhost:8501. `iv` is shorthand for
`impact-vision`; see the [CLI Reference](#cli-reference) for all subcommands.

## Usage

Impact Vision ships **48 impact agent tools** covering screening, diligence,
monitoring, reporting, assurance, and exit. Paste the examples below into the
agent or the web chat UI; `impact_advisor` routes unfamiliar requests.

### Analyzing a Pitch Deck

```
> Screen this pitch deck: /path/to/pitch_deck.pdf
```

The agent calls `assess_deal`, which runs the whole screen in one step. That
covers claims and evidence, IRIS+ mapping, 5D, SDGs, gaps, sector DD coverage,
greenwashing and the IC gate. It returns the verdict plus an `assessment_id`
that other tools reuse, so follow-ups don't re-type the company:

```
> Write the LP edition of the report for assessment 3, in Traditional Chinese
> Review greenwashing risk claim by claim for assessment 3
> Draft a Theory of Change for the company and link it to IRIS+ metrics
> Which DD questions should we send the founders first?
```

### ESG Toolbox

Use the unified ESG toolbox when you need practical support across
disclosure standards, ESG ratings, export compliance, supplier audits,
sustainable finance, water stewardship, responsible mining, and carbon
accounting. Module knowledge tracks current regulatory milestones
(CBAM Omnibus definitive period, EUDR 2026/27 application dates,
post-Omnibus CSRD/CSDDD thresholds, EU Battery Regulation timeline,
SBTi V2 transition, CDP 2026 cycle, SMETA 7.0, AWS Standard V3.0).

The `esg_toolbox` agent tool supports `list`, `search`, `get`, `methodology`,
`checklist`, `assess`, `crosswalk`, `source_profile`, `recommend`, `workflow`,
and `input_plan` actions. These cover module discovery, evidence planning,
readiness scoring, framework crosswalks, source inspection, and next-question
generation.

The toolbox routes to existing tools where a dedicated implementation exists
(frameworks, HRDD, product passports, verification, regulatory calendars, and
emission factors). It reuses uploaded documents, company profiles, metrics,
product codes, and supplier context; `recommend` selects the best-fit modules
and `input_plan` asks only for unresolved fields.

### Catalog, DD & Scoring

```
# IRIS+ catalog
> Search for IRIS+ metrics related to financial inclusion
> Show me metrics mapped to SDG 7 (Clean Energy)
> Get details for metric OI1479

# DD checklist
> Show me the full impact DD checklist
> Analyze this document against the DD checklist: /path/to/memo.pdf

# SDG alignment + 5 Dimensions
> Map BrightPath Finance to SDG goals. They report metrics PI4060, OI8869, OI6213...
> Score this company on the 5 Dimensions of Impact
> What are the gaps in the "Contribution" dimension?

# Cross-framework lookup
> Look up cross-references for IRIS+ metric OI4112
> What's the GRI equivalent of SFDR PAI indicator #1?
```

### Generating Reports

```
> Generate the IC edition of the impact report for BrightPath Finance as PDF
> Export the assessment as XLSX for our LP report
```

Reports open with the **decision**: a verdict card (Ready for IC / Evidence
plan required / Fails thesis) with its reasons, four headline tiles and *what
would change our mind*. Then come:
- **Expected impact**: P10–P50–P90 per outcome and what drives the range;
- **Impact at a glance**: SDG wheel and impact pathway;
- the **5 Dimensions** against sector benchmarks and the **material SDGs**;
- an **evidence ledger** of every claim and metric;
- the **greenwashing review**, risks and a de-duplicated **action plan**;
- methodology and a glossary.

**Audience editions** (`ic`, `lp`, `regulator`, `public`) leave out
internal content. Every chart has a table twin, and reports follow the
reader's dark mode. They work offline (no CDN), meet WCAG AA contrast,
support white-labelling, and come in English, 繁體中文 and 简体中文. PDFs are
A4 with page numbers (`--pdf`, `[pdf]` extra).
`style="classic"` keeps the pre-v7 interactive report for one release.

### Improving Scores Through Q&A

```
> Help me improve my impact scores for this pig farm
> Ask me questions to strengthen the assessment
```

The agent identifies your weakest dimensions, asks targeted questions
("How many direct beneficiaries?", "Do you track emissions?"), maps your
answers to IRIS+ metrics, and re-runs the assessment to show exactly how
each answer improved the score.

### ESG Frameworks, Theory of Change & Compliance

```
# Multi-framework assessment
> Scan this company against all ESG frameworks
> What are the material SASB topics for a fintech company?
> Assess TCFD / ISSB S1+S2 / EU CSRD-ESRS readiness for our disclosures
> Classify our fund under SFDR Article 6/8/9
> Preview our SFDR 2.0 category (Sustainable / Transition / ESG Basics)

# Theory of Change
> Assess our fund's ToC against RS Group's Blended Value principles and the GIIN checklist
> Help me develop a Theory of Change for our microfinance investment

# Greenwashing & compliance
> Run a greenwashing check on this pitch deck
> Assess EU green-claims (ECGT) and UK FCA Anti-Greenwashing Rule alignment
> Compute the Green Authenticity Index and Cheap Talk Index for this report

# Verification & product passport
> Check our readiness for IFC OPIM verification
> Import Digital Product Passport data and map it to IRIS+/ESRS metrics
```

### LP DDQ Export & Portfolio Batch Analysis

```
> Generate an ILPA DDQ response for BrightPath Finance
> Export EDCI annual survey as XLSX: output_path="edci_survey.xlsx"
> Analyze this portfolio CSV file: examples/sample_portfolio.csv
> Run portfolio roll-up with fund-level 5D scores and generate an LP report
> Show impact attribution by sector and geography
```

### Pipeline, Monitoring & Guided Assessment

```
> Add EcoFinance to the pipeline at screening stage
> Transition EcoFinance to DD in progress with rationale "Strong SDG alignment"
> Set quarterly monitoring for EcoFinance and record metric PI4060 = 15000
> Check alerts for our portfolio and run a full re-assessment for EcoFinance
> Start a screening assessment for BrightPath Finance — what's the next step?
```

### Climate Accounting (Scope 1/2/3 + PCAF)

The carbon calculator supports an entity workflow with revenue-based
intensity, Scope 2 certificate adjustments, manufacturing Scope 3 activity
methods, and three-year comparable emissions. Results retain factor
provenance and verification metadata in the Impact Vision output.

```
> Calculate a Scope 1/2 GHG inventory from this fuel + electricity data
> Run the entity carbon calculator with revenue intensity and valid I-REC coverage
> Estimate Scope 3 from purchased-goods spend, T&D losses, freight tonne-km, and waste
> Compare Scope 1/2/3 totals across the last three reporting years
> Apply emission factor catalog v2 with uncertainty bands
> Run PCAF financed-emissions attribution for the loan book
> Check SBTi 1.5 °C alignment
```

Lifecycle assessment (`lca_assessment`) — goal and scope, inventory, hotspots,
sensitivity and life-cycle-management plans — is covered in
[docs/climate-and-lca.md](docs/climate-and-lca.md).

### Evidence, assurance & LP questions

```
# Stakeholder voice
> Build a Lean Data survey template for smallholder farmers in Kenya
> Register GDPR-compliant consent records and link feedback to outcome claims

# AI extraction review + verification
> Auto-approve claims above 0.85 confidence that cite audited sources
> Open a verification workspace for the assurer and share only approved evidence

# LP narrative + Q&A (verified data only)
> Generate an LP quarterly narrative for the Inclusive Finance fund
> Answer LP question "what % of beneficiaries are women" using only approved data

# Portfolio natural-language query
> What was the average CO2e intensity across the climate portfolio last year?
> Top 5 companies by beneficiary reach, verified data only

# Exit impact (OPIM Principle 8)
> Score exit-impact durability for Solar Co and build a 12-month exit impact plan
```

### Consultant engagements

The v4 engagement suite is a single tool (`engagement_suite`) that covers
scoping, data rooms, ToC/KPI design, reporting studios, training, public
website output, and the three-pillar assurance bundle.

```
> Create an engagement workspace for "Acme Solar Advisory Q2" at scoping stage
> Build a proposal with a fixed-fee rate card and send it for client signature
> Design a Theory of Change + KPI tree and validate it against IRIS+
> Build a client data room, score completeness, and issue coaching cards
> Move the draft report from "in_review" to "published" and log the state change
> Issue a readiness badge once training modules + diagnostic are complete
> Sign the final assurance bundle (evidence graph + audit trail + workspace) with HMAC
```

### Single-Prompt Mode

For CI/CD or scripting:

```bash
impact-vision -p "Search IRIS+ catalog for climate-related metrics"
```

## CLI Reference

`impact-vision` (or the `iv` shorthand) exposes seven top-level
subcommand groups, two quickstart commands and four service commands. Run any command with
`--help` for full flags.

```bash
# No-key quickstart
impact-vision demo [--deck pig-farm|solar|microfinance|all] [--no-open]
impact-vision assess deck.pdf [--sector S] [--audience full|ic|lp|regulator|public] [-o DIR] [--json] [--open] [--pdf]

# Interactive agent
impact-vision                              # Start interactive agent session
impact-vision -p "your prompt"             # Single prompt, then exit
impact-vision --model opus                 # Use a specific model

# Provider / auth setup
impact-vision setup                        # Interactive provider wizard (OpenRouter/Claude/OpenAI/Ollama)
impact-vision ollama-setup --model llama3.2
impact-vision provider list | use | add | edit | remove
impact-vision auth   login | status | logout | switch | copilot-login | codex-login | claude-login

# IRIS+ catalog
impact-vision catalog load [EXCEL_PATH] [--force]
impact-vision catalog stats
impact-vision catalog search "climate"

# ESG / sustainability frameworks
impact-vision framework list
impact-vision framework scan "company description"
impact-vision framework xref OI4112

# Due-diligence checklist (122 questions / 34 categories)
impact-vision dd list [--category "What (Outcomes)"]
impact-vision dd categories
impact-vision dd analyze "text or /path/to/doc.txt"

# Service surfaces
impact-vision serve-mcp                                  # MCP server (stdio)
impact-vision serve-mcp --transport sse --port 8765      # MCP over SSE
impact-vision serve-web                                  # Chat UI + tool console + REST API (http://127.0.0.1:8787)
impact-vision dashboard [--port 8501]                    # Streamlit portfolio dashboard ([dashboard] extra)

# Developer utilities
impact-vision mcp      list | add | remove               # Manage MCP server configs
impact-vision plugin   list | install | remove           # Manage entry-point plug-ins
impact-vision cron     list | add | remove | run         # Cron scheduler for background jobs
```

## Architecture

```
impact-vision/
├── src/impact_vision/
│   ├── impact/                        # Impact measurement engine
│   │   │
│   │   │   # --- Core engine ---
│   │   ├── models.py                  # Pydantic: Metric, Company, Assessment, SDG, ImpactClaim
│   │   ├── catalog.py                 # IRIS+ 5.3c Excel ETL (263-column parser)
│   │   ├── database.py                # In-memory MetricStore (search/filter/stats)
│   │   ├── sdg_taxonomy.py            # 17 SDG Goals + 169 Targets reference
│   │   ├── five_dimensions.py         # What/Who/HowMuch/Contribution/Risk scoring
│   │   ├── sdg_mapper.py              # Per-goal SDG alignment scorer (0-100)
│   │   ├── gap_analysis.py            # Core Metric Set coverage analysis
│   │   ├── dd_checklist.py            # DD question engine + NESTA evidence scoring
│   │   ├── benchmarks.py              # Sector benchmarks for 18 sectors
│   │   ├── greenwashing.py            # Greenwashing detection (standard + EU ECGT + UK FCA + NLP)
│   │   ├── risk_opportunity.py        # Risk/opportunity (likelihood × severity)
│   │   ├── storage.py                 # SQLite persistence for assessments
│   │   ├── pipeline.py                # Document → full assessment → reports (assess / demo)
│   │   ├── claim_metric_mapper.py     # Pitch quantities → IRIS+ metric IDs
│   │   ├── glossary.py · _paths.py    # Plain-language glossary; bundled-data resolver
│   │   │
│   │   │   # --- Fund workflow (v0.8+) ---
│   │   ├── fund_thesis.py · deal_gate.py   # Fund thesis, IC gate, pass/warn/fail scorecard
│   │   ├── ic_memo.py                 # IC memo rendering (MD/HTML/DOCX/PPTX)
│   │   ├── portfolio_rollup.py · lp_calendar.py · lp_portal.py · signed_feed.py
│   │   ├── tenancy.py · plugins.py · marketplace.py   # RBAC, plug-ins, thesis marketplace
│   │   │
│   │   │   # --- Scientific rigor + primary data (v0.14.0) ---
│   │   ├── extractors/                # Pluggable claim extractors (regex/LLM)
│   │   ├── toc_graph.py               # Theory-of-Change graph + Mermaid renderer
│   │   ├── counterfactual.py          # GIIN COMPASS additionality templates
│   │   ├── bayes.py · meta_analysis.py · spillover.py · sroi.py · causal.py
│   │   ├── geospatial.py · surveys.py · worker_voice.py · ecosystem_services.py
│   │   ├── registries.py              # Verra/Gold Standard/Puro/BioCredits
│   │   ├── returns.py                 # MOI + impact-adjusted IRR
│   │   ├── external_benchmarks.py     # GIIN Compass peer quartiles
│   │   ├── blended_finance.py         # IL-Loans, SOC/DIB, impact carry
│   │   ├── assurance.py · csrd_wizard.py · issb_reporting.py · soc2_checklist.py
│   │   ├── audit_trail.py             # Hash-chained lifecycle events
│   │   ├── i18n.py · fx.py · regulatory_packs.py · branding.py
│   │   │   # --- v2 institutional backbone (v0.13+) ---
│   │   ├── metric_records.py          # Canonical MetricRecord contract
│   │   ├── investee_collection.py     # Questionnaire schema + submission lifecycle
│   │   ├── climate_accounting.py      # Entity carbon calculator: Scope 1/2/3, intensity, trends
│   │   ├── lca.py                      # LCA/LCSA, lifecycle costs, social hotspots, LCM plans
│   │   ├── evidence_graph.py          # Claim↔metric↔target↔evidence lineage
│   │   ├── standards_registry.py      # Versioned standards metadata
│   │   ├── expected_impact.py · company_record.py  # methodology 2.0 · pipeline → exit
│   │   │
│   │   │   # --- v3 Trust Infrastructure (v0.15.0) ---
│   │   ├── emission_factors.py · stakeholder_voice.py  # Versioned factors; Lean Data + consent
│   │   ├── evidence_workflow.py       # AI extraction review queue
│   │   ├── verification_workspace.py  # Assurer workspace + findings
│   │   ├── lp_narrative.py · greenwashing_reviewer.py  # LP Q&A (approved data); per-claim review
│   │   ├── portfolio_nlq.py           # NL portfolio queries + ApprovedDataPolicy
│   │   ├── exit_impact.py             # OPIM Principle 8 exit-impact scoring + learning context
│   │   │
│   │   │   # --- v7 trust, currency & platform (0.17.0) ---
│   │   ├── knowledge.py               # Sourced YAML knowledge + 180-day freshness gate
│   │   ├── methodology.py             # Versioned scoring weights; version + hash on every output
│   │   ├── ai_provenance.py           # AI / automation disclosure on every output (AI Act Art 50)
│   │   ├── state_store.py             # Persistent consultant state (SQLite / Postgres)
│   │   ├── benchmark_provider.py      # One provider over data/benchmarks.yaml
│   │   ├── portfolio_home.py · engagement_home.py  # Fund and engagement web pages
│   │   │
│   │   │   # --- v4 Engagement Suite (latest) ---
│   │   ├── engagements/
│   │   │   ├── workspace.py           # EngagementWorkspace + artifact audit hook
│   │   │   ├── proposal.py            # Proposal builder + e-signature
│   │   │   ├── toc_builder.py         # Wraps toc_graph + metric_recommender
│   │   │   ├── data_room.py           # Completeness scorecard + coaching cards
│   │   │   ├── value_creation.py      # Scenario + business case + risk scoring
│   │   │   ├── reporting_studio.py    # Draft → review → published state machine
│   │   │   ├── training.py            # Modules + diagnostic + readiness badge
│   │   │   ├── website.py             # Public diagnostic + lead capture
│   │   │   ├── copilot.py             # Governed AI: review queue + safe answer
│   │   │   ├── regulatory.py          # Jurisdiction profiles + SFDR classification
│   │   │   └── verification_bundle.py # 3-pillar signed assurance bundle (HMAC)
│   │   │
│   │   ├── report_templates/          # Jinja2-based HTML report templates
│   │   ├── frameworks/                # 22 ESG/sustainability framework modules
│   │   │   ├── sasb.py · gri.py · tcfd.py · sfdr_pai.py · sfdr_recast.py · edci.py · unpri.py
│   │   │   ├── issb_ifrs_s1.py · issb_ifrs_s2.py · esrs.py · vsme.py · hk_taxonomy.py
│   │   │   ├── ifc_opim.py · pcaf.py · sbti.py · eu_taxonomy.py · tnfd.py · cdp.py · …
│   │   │   └── cross_reference.py     # 61 cross-framework metric mappings
│   │   ├── mcp_server.py              # MCP server (FastMCP)
│   │   └── sdk.py                     # High-level ImpactVision SDK facade
│   │
│   ├── tools/impact/                  # 48 LLM-callable impact agent tools (see "Tools" below)
│   │   ├── assess_deal_tool.py        #   One-call deal screen → assessment_id
│   │   └── merge.py · merged_tools.py #   Typed tool merges + deprecated aliases
│   ├── api_gateway/router.py          # FastAPI REST API
│   ├── web/                           # Browser surfaces (single-file, no build step)
│   │   ├── chat_ui.py                 #   ChatGPT-style chat UI served at /
│   │   ├── chat_api.py                #   WebSocket + sessions / provider / uploads
│   │   ├── chat_session.py            #   One agent runtime per conversation
│   │   ├── reports_api.py             #   Reports, share links, portfolio home, engagements
│   │   ├── console.py                 #   Tool-form console served at /console
│   │   └── app.py                     #   Mounts everything onto the REST gateway
│   ├── dashboard/app.py               # Streamlit 6-tab dashboard
│   ├── skills/bundled/content/        # Agent knowledge (markdown)
│   ├── prompts/system_prompt.py       # Impact Vision persona + instructions
│   └── cli.py                         # CLI (7 subcommand groups + demo / assess / dashboard / serve-*)
├── data/
│   ├── raw/                           # IRIS+ Excel file (not committed)
│   ├── processed/                     # JSON catalog cache (auto-generated)
│   ├── dd_checklist.yaml              # 122 DD questions / 34 categories
│   ├── regulatory/                    # Watch-list, jurisdictions, packs, SFDR 2.0 facts (sourced)
│   ├── methodology/v1.yaml            # Every scoring weight and threshold (versioned)
│   ├── standards_registry.yaml · benchmarks.yaml · concordance.yaml · hk_taxonomy.yaml
│   ├── esrs_simplified_2026.yaml      # Revised ESRS (Reg 2026/1563) screening rows
│   ├── scoring_config.yaml            # Sector baselines + keyword boosts
│   ├── sdg_keywords.yaml              # SDG keyword mappings for 20+ sectors
│   ├── core_metric_set_per_sdg.yaml · core_metric_sets_by_sector.yaml  # Curated core sets
│   ├── claim_metric_map.yaml          # Rules mapping pitch quantities to IRIS+ IDs
│   ├── glossary.yaml                  # Plain-language glossary (source of docs/glossary.md)
│   ├── sample_decks/                  # Fictional sample pitch decks for `impact-vision demo`
│   ├── fund_thesis.*.yaml             # Default + 4 regional thesis packs
│   └── i18n/                          # 6 languages (en/es/fr/pt/zh/ar)
├── docs/
│   ├── fund-manager-guide.md          # Web-first task recipes for funds and consultants
│   ├── reference/tools.md             # Generated list of all 48 tools
│   ├── roadmap-v8.md                  # Current roadmap (credibility + lifecycle); older: v7, v6, v4, v3
│   ├── glossary.md · dd-checklist.md · climate-and-lca.md
│   └── cursor-integration.md          # Cursor/VS Code MCP setup
├── examples/                          # Sample company, portfolio, MCP configs
├── tests/                             # Test suite (impact + v2 + v3 + v4)
└── .github/workflows/ci.yml           # Import smoke, tests, ruff, knowledge + extraction gates
```

## DD Checklist

**122 questions** across **34 categories** (18 core, 15 sector sets, SDG),
drawn from the GIIN Impact Toolkit, Pacific Community Ventures, Seraf, the
Impact Management Project and AFME/OECD ESG due diligence. Each answered question
is graded on the NESTA standards of evidence (1 = narrative … 5 = rigorous
evaluation). Only the company's own sector set is applied. Full category
tables: [docs/dd-checklist.md](docs/dd-checklist.md).

## Frameworks & Standards

All frameworks below are exposed via the `framework_assess` tool, the
MCP server, the REST API, and the Python SDK. Every framework ships with
cross-references to IRIS+ metric IDs via the shared
`cross_reference` module (61 concept mappings).

| Category | Framework | Coverage |
|----------|-----------|----------|
| **Core taxonomy** | GIIN IRIS+ 5.3c | ~787 metrics, SDG mappings, 5-Dimension tags |
| | UN SDGs | 17 Goals, 169 Targets |
| | Impact DD Checklist | 122 questions / 34 categories (GIIN, PCV, Seraf, IMP, AFME + 15 sectors) with NESTA evidence (1-5) |
| | Sector Benchmarks | 18 sectors (GIIN survey data) with aggregated 5D scores and coverage |
| | Cross-Reference Mapping | 61 concepts mapped across IRIS+/GRI/EDCI/SFDR PAI/SASB/TCFD/ESRS/ISSB/PCAF/SBTi/TNFD/CDP/EU Taxonomy |
| **ESG disclosure** | SASB | 17 industries, 77+ material topics |
| | GRI | 34 standards (Universal + Topic), 120+ disclosures |
| | TCFD / IFRS S2 | 4 pillars, 11 disclosures, scenario analysis, Scope 1/2/3 |
| | EDCI | 2026 PE/VC KPI fields, including non-core cybersecurity testing |
| | UNPRI | 6 Principles, 27 actions |
| | Theory of Change | RS Group 8 Blended Value Principles + GIIN 8-step ToC Checklist |
| | ISSB IFRS S1 | General sustainability disclosure (4 pillars) |
| | ISSB IFRS S2 | Climate-related disclosures plus an issued-amendments register (effective 2027-01-01) |
| | EU CSRD / ESRS | 11 standards, double-materiality; revised ESRS (Delegated Reg 2026/1563, mandatory FY2027) with date-aware legal status |
| | EFRAG VSME | Voluntary SME standard (Delegated Reg 2026/1560): Basic B1-B11 + Comprehensive C1-C9, investee template, value-chain cap enforced on data requests |
| | 2X Criteria | Gender-lens investing standard (6 dimensions + governance/GBVH minimum requirements) |
| | TISFD (beta) | Inequality & Social-related Financial Disclosures readiness: 4 pillars, 13 disclosures, GRI/ESRS crosswalk |
| **Regulatory** | SFDR | 14 mandatory + 9 optional PAI indicators, Article 6/8/9 classification, deadline scheduler |
| | SFDR 2.0 preview | Sustainable / Transition / ESG Basics preview (Commission, Council or Parliament text; 70% threshold, exclusions, "impact"-wording check against ToC + measured outcomes; proposed law, ~2029) |
| | EU Omnibus I scope | CSRD/CSDDD in-scope decision tree (employee + turnover thresholds, FY2025-26 pause, VSME fallback) |
| | CSDDD / HRDD | UNGP + OECD 6-step value-chain human-rights due diligence (salience ranking, grievance score, remediation tracker, readiness band) |
| | EU Taxonomy | 6 environmental objectives, DNSH + Minimum Safeguards |
| | UK FCA Anti-Greenwashing Rule | Fair/clear/not-misleading assessment |
| | EU green claims (ECGT 2024/825) | Likely ECGT/UCPD breaches (generic claims, offset-based neutrality, unplanned future claims) in `greenwashing_detect`; shelved-GCD tests as best practice |
| | Hong Kong Taxonomy (HKMA) | Eligibility candidates from text + alignment % (Phase 1 / 2A; 2B flagged as consultation) |
| | UK SRS (FCA PS26/19) | Listed-issuer comply-or-explain obligation from 2027 in the UK jurisdiction profile |
| | EU Digital Product Passport (ESPR) | Import + map to IRIS+/ESRS/SDG |
| | Per-jurisdiction packs | EU-SFDR, EU-CSRD, EU-CSDDD, UK-FCA-SDR, US-SEC-ESG, HK-HKEX-ESG, AU-AASB-S2, ISSB-global; deadline calendars for 10 jurisdictions incl. Hong Kong |
| **Climate & nature** | PCAF | Financed-emissions attribution, sector defaults, weighted data quality |
| | SBTi (Net-Zero Standard v1.2) | 1.5 °C pathway, Scope-3 materiality, 2050 cap |
| | TNFD v1 | 14 LEAP / pillar disclosures (now feeding the ISSB nature Practice Statement) |
| | CDP | Climate / water / forests questionnaire intake + readiness screen (`framework_assess`) |
| | GHG Protocol | Scope 1/2 inventory (Scope 3 via PCAF) with versioned factor catalog |
| | NGFS scenarios | Physical/transition portfolio exposure across 7 NGFS pathways + illustrative value-at-risk |
| **Impact management** | IFC OPIM | 9-principle verification readiness + Principle 8 exit-impact |
| | SROI | Deadweight / attribution / displacement / drop-off adjustments |
| | MOI + Impact-adjusted IRR | Newton-Raphson, optional shadow price |
| | IFVI / VBA monetary valuation | Value-factor catalogue → net monetary impact, benefit/cost ratio, impact multiple of money |
| | Welfare quantifier (QALYs) | breadth × depth × theme × geography → QALYs / lives improved + cost-per-QALY + portfolio roll-up |
| | Impact Target Setter | Context-driven conservative/base/stretch IRIS+/SDG target ranges from theme × geography × capital |
| | LCA / LCSA | Goal/scope, inventory, impact hotspots, sensitivity, lifecycle cost/social dimensions, and management-plan readiness |
| **Greenwashing & NLP** | Standard greenwashing scoring | Vague-language + quantitative-evidence checks |
| | Green Authenticity Index (GAI) | Ratio of substantive to vague claims |
| | Cheap Talk Index (CTI) | Forward-looking vs. evidenced statements |
| | Per-claim explainable reviewer | `concrete` / `mixed` / `vague` / `buzzword_only` classification + severity |
| **Assurance** | ISAE 3000 / AA1000 | Management-assertion + subject-matter + evidence register |
| | SOC 2 Type II / ISO 27001 | Starter control set with readiness report |
| | Verification workspace | Finding lifecycle + threaded comments (v0.15.0) |
| | 3-pillar assurance bundle | HMAC-signed evidence graph + audit trail + workspace (v4) |
| | AI governance (EU AI Act) | Model card + data lineage + human-oversight log + risk classification & obligations; Art 50 AI/automation disclosure stamped on every report, memo and export |

### Agent Tools (48)

Every tool is registered once and exposed identically to the interactive
agent, web chat, REST API and MCP server. The full generated list, with each
tool's description and the counts quoted in these docs, is in
[docs/reference/tools.md](docs/reference/tools.md).

| Task area | Tools |
|-----------|-------|
| Start here / routing | `assess_deal`, `impact_advisor` |
| Pre-screen & core assessment | `pitch_deck_analyze`, `iris_catalog`, `sdg_mapper`, `five_dimension_assess`, `gap_analysis`, `impact_metric_recommender`, `impact_data_quality` |
| Due diligence & evidence | `dd_checklist`, `product_passport` |
| Risk & credibility | `greenwashing_detect` (incl. EU ECGT, UK FCA), `impact_risk_opportunity`, `exclusion_screening` |
| Frameworks & reporting | `framework_assess` (incl. VSME, HK Taxonomy, SFDR 2.0), `esg_toolbox`, `cross_reference`, `impact_report`, `impact_valuation` |
| Decisions & deadlines | `decision_workflow`, `regulatory_calendar` |
| Portfolio | `portfolio_analyze`, `portfolio_query`, `pipeline`, `monitoring`, `trend_analysis` |
| Stakeholder voice & narrative | `stakeholder_voice`, `improvement_advisor`, `lp_narrative` |
| Evidence & assurance | `emission_factors`, `evidence_review`, `verification_workspace`, `exit_impact` |
| Lifecycle & climate | `lca_assessment`, `climate_scenario_risk` |
| Consultant engagements | `engagement_workspace`, `toc_builder`, `engagement_suite` |
| Frontier measurement & governance | `impact_quantifier`, `hrdd_assess`, `ai_governance`, `investee_portal` |
| Comparable, assured & connected | `contribution_tracker`, `carbon_credit_integrity`, `impact_linked_finance`, `dmrv_evidence`, `survey_delivery`, `ddq_responder` |

## Streamlit Dashboard

For a curated visual workflow, run:

```bash
streamlit run src/impact_vision/dashboard/app.py
```

The six tabs cover company assessment, IRIS+, DD, framework scans, the ESG
toolbox, and portfolio analysis.

## Web Interface

One command serves a browser chat UI, the tool console and the REST API on a
single port:

```bash
impact-vision serve-web --open        # http://127.0.0.1:8787
```

| URL | Surface |
|-----|---------|
| `/` | **Chat UI** — ChatGPT-style conversation with the full agent |
| `/console` | **Tool console** — a form for every impact tool, generated from its schema |
| `/shared/…` | **Read-only shared report** — signed, expiring link; no login needed |
| `/docs` | OpenAPI explorer |
| `/api/v1/*` | REST gateway |

**No API key needed to start:** click **Analyze a pitch deck** (or drop a
PDF/Word/Markdown file on the welcome screen). You get the IC verdict card in
about a second, then **View report** opens the decision report full-screen
with audience (full / IC / LP / regulator / public), language (English /
繁體中文 / 简体中文) and theme switches, plus downloads (IC memo, Word, Excel,
CSV). **Share…** creates a signed read-only link (LP or public edition by
default, 7–90 days); deleting the report revokes it. Set
`IMPACT_VISION_SHARE_HMAC_KEY` to keep links valid across machines.

The chat UI runs the same agent as the CLI (tools, skills, permissions) with
streaming replies, tool cards, uploads, a **Companies** tab (stage, expected
vs actual, IC approvals) and provider settings (Claude, OpenAI, OpenRouter,
DeepSeek, Ollama or any compatible endpoint). No build step, no CDN.

**→ Full walkthrough: [`docs/web-chat-guide.md`](docs/web-chat-guide.md)**

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/ -v

# Focused subsets
python -m pytest tests/test_impact.py -v                    # engine + frameworks
python -m pytest tests/test_v4_tracks_3_to_10.py -v         # v4 engagement suite

# Import smoke checks (verifies all package exports work)
python scripts/check_imports.py --all

# Lint
ruff check src/

# v6 data-quality and lifecycle checks
python -m pytest tests/test_quality_review_v6.py tests/test_lca.py tests/test_climate_accounting.py -v
```

GitHub Actions runs import smoke, full tests, and ruff on every push/PR.

## MCP Server (Use with Claude, Cursor, VS Code)

Impact Vision can run as an **MCP server**, exposing every impact tool
(generated from the tool registry, with real typed schemas), a **prompt per
playbook** (`deal_screening`, `lp_reporting`, `regulatory_compliance`, …)
and 5 read-only resources to any MCP-compatible AI client.

```bash
impact-vision serve-mcp                              # stdio (desktop clients)
impact-vision serve-mcp --transport sse --port 8765  # SSE (remote clients)
```

Use stdio for local desktop clients such as Claude Desktop, Cursor, and
VS Code. Use SSE when the MCP server is started separately and clients
connect over HTTP.

### Client setup

For Cursor or VS Code, add the `impact-vision` stdio server to the client's MCP
configuration. For Claude Desktop, copy
`examples/claude_desktop_config.json` into its configuration directory.

### MCP Resources

| Resource URI | Purpose |
|--------------|---------|
| `impact://catalog/stats` | IRIS+ catalog counts, categories, and themes |
| `impact://dd-checklist/categories` | DD checklist categories and question counts |
| `impact://frameworks/list` | Supported ESG / impact frameworks |
| `impact://cross-reference/{metric_id}` | Cross-framework mapping for one metric |
| `impact://sdg/goals` | UN SDG goal reference data |

See [docs/cursor-integration.md](docs/cursor-integration.md) for the full
setup guide and client-specific notes.

## REST API

FastAPI REST gateway backing the web chat UI, MCP server, and third-party
integrations:

```bash
# Start the API server
uvicorn impact_vision.api_gateway.router:app --reload

# Authenticated (set env var for production)
IMPACT_VISION_API_KEY=your-secret-key uvicorn impact_vision.api_gateway.router:app
```

Every impact tool is one generic route, generated from the tool registry:

```bash
curl localhost:8000/api/v1/tools                       # list tools (add ?schemas=true for JSON schemas)
curl -X POST localhost:8000/api/v1/tools/assess_deal \
     -H 'Content-Type: application/json' \
     -d '{"text": "We sell solar home systems in Kenya...", "company_name": "SunPath"}'
```

For safety, remote callers can't make the server read its own files or fetch
URLs (`file_path`, `url`, `output_path`, …); send content inline, or set
`IMPACT_VISION_API_ALLOW_PATHS=1` on a trusted single-user deployment. The
older named endpoints (`/api/v1/score`, `/api/v1/report`, `/api/v1/batch`, …)
remain, and `/api/v1/playbooks` lists the multi-tool workflows. See the
OpenAPI docs at `/docs`.

## Roadmap

Strategy and engineering plans live in [`docs/`](docs/):

- [`docs/roadmap-v8.md`](docs/roadmap-v8.md) — **current**: secure by default, Methodology 2.0 (expected impact with ranges), evidence-aware extraction, the company lifecycle, 2027 standards.
- [`docs/roadmap-v7.md`](docs/roadmap-v7.md) — trust fixes, effortless first run, decision-first reports, standards currency. Shipped as 0.17.
- [`docs/roadmap-v2.md`](docs/roadmap-v2.md) — Institutional-readiness plan: data contracts, investee collection, climate accounting, LP reporting, assurance, causal impact, and governed AI.
- [`docs/roadmap-v3.md`](docs/roadmap-v3.md) / [`-v3-implementation.md`](docs/roadmap-v3-implementation.md) — Trust infrastructure. Shipped.
- [`docs/roadmap-v4.md`](docs/roadmap-v4.md) — Consultant-led engagement suite. Backend shipped; frontend and paid-data wiring deferred.
- [`docs/roadmap-v5.md`](docs/roadmap-v5.md) — Legally-current and frontier measurement wave. Shipped.
- [`docs/roadmap-v6.md`](docs/roadmap-v6.md) — Comparable, assured, and connected wave. Planning baseline with initial v6 surfaces shipped.
- [`docs/roadmap-updates-2026-07.md`](docs/roadmap-updates-2026-07.md) — July 2026 regulatory and implementation delta; actionable items shipped.
- [`ROADMAP.md`](ROADMAP.md) — historical engineering record.
- [`CHANGELOG.md`](CHANGELOG.md) — release notes.

## Contributing

Have ideas? Open an [issue](https://github.com/joejoe168168/impact-vision/issues) or submit a PR!

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

Thanks to AvantFaire Investment Management, GIIN, Pacific Community Ventures,
Seraf, the Impact Management Project, and OpenHarness for the frameworks,
practices, and infrastructure that inform Impact Vision.
