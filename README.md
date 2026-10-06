# Impact Vision

Open-source AI-powered impact measurement and SDG alignment agent for VC and impact investment funds.

Built on [OpenHarness](https://github.com/HKUDS/OpenHarness), Impact Vision ships a conversational AI agent, a **CLI**, a **REST API**, an **MCP server**, a **Streamlit dashboard**, and a **single-file web chat UI** — all backed by the same engine with deep expertise in GIIN's IRIS+ framework, UN SDGs, the 5 Dimensions of Impact, and 20+ ESG / regulatory frameworks (ISSB, ESRS, SFDR, TCFD, SASB, GRI, PCAF, SBTi, EU Taxonomy, TNFD, CDP, TISFD, VSME, 2X, and SBTN).

Release history lives in [CHANGELOG.md](CHANGELOG.md). Strategy and engineering plans live in [`docs/`](docs/).

![Impact Vision Banner](docs/images/banner.png)

## Screenshots

<table>
<tr>
<td width="50%"><img src="docs/images/agent-greeting.png" alt="AI Agent greeting"><br><em>AI agent with full impact measurement toolkit</em></td>
<td width="50%"><img src="docs/images/dd-scoring.png" alt="DD questions and 5D scoring"><br><em>Due diligence questions + 5-Dimension scoring</em></td>
</tr>
<tr>
<td><img src="docs/images/iris-metrics.png" alt="IRIS+ metric recommendations"><br><em>Recommended IRIS+ metrics by category</em></td>
<td><img src="docs/images/html-5d-radar.png" alt="HTML report 5D radar chart"><br><em>HTML report: 5-Dimension radar chart with scores</em></td>
</tr>
<tr>
<td><img src="docs/images/html-sdg-chart.png" alt="SDG alignment chart"><br><em>SDG alignment scoring (17 goals, official UN colors)</em></td>
<td><img src="docs/images/html-opportunities-risks.png" alt="Impact opportunities and risks"><br><em>Sector-specific opportunities & risks analysis</em></td>
</tr>
</table>

> **Try it yourself:** See a [sample HTML report](examples/sample_impact_report.html) generated for a pig farm in Malaysia.
>
> **More samples:** Browse the full set of generated deliverables — impact report (light / dark / white-label), IC memo, DD report and investee portal — in [`demo/`](demo/) (open [`demo/index.html`](demo/index.html) for the gallery).

## What is Impact Investing?

Impact investing means investing with the intention to generate **positive, measurable social and environmental impact** alongside a financial return. Unlike traditional investing (financial return only) or philanthropy (social good only), impact investing seeks both.

Key concepts Impact Vision helps with:

| Concept | What it means |
|---------|---------------|
| **IRIS+** | The "GAAP for impact" -- ~787 standardized metrics for measuring social/environmental outcomes (maintained by GIIN) |
| **SDGs** | 17 UN Sustainable Development Goals (e.g., No Poverty, Clean Energy, Climate Action) with 169 targets |
| **5 Dimensions** | The standard framework for assessing impact quality: What outcome? Who benefits? How much? Would it happen anyway? What could go wrong? |
| **Impact DD** | Due diligence focused on whether an investment will actually generate the claimed impact |
| **ESG** | Environmental, Social, Governance -- risk management frameworks (SASB, GRI, TCFD, SFDR, EDCI, UNPRI, ISSB, ESRS) |
| **NESTA Evidence** | 5 levels rating how strong the evidence is: Level 1 (narrative) to Level 5 (rigorous RCT) |

## Core Use Case

**Upload a pitch deck or investment memo** and Impact Vision will:

1. Extract and classify impact claims (outcome / output / activity / intent / risk)
2. Map claims to relevant **IRIS+ metrics** from the 787-metric catalog
3. Detect **SDG goal/target alignment** from the content
4. Run an **impact DD checklist** (122 questions across 34 categories from GIIN, PCV, Seraf, IMP, AFME + sector-specific for 15 sectors)
5. Assess **evidence strength** using NESTA Standards of Evidence (levels 1-5)
6. Auto-extract a **Company model** for immediate use with downstream assessment tools
7. Compare against **sector benchmarks** from GIIN survey data
8. Suggest the most important **follow-up questions** for the investment team
9. Generate reports in **HTML** (with Plotly charts), **XLSX**, CSV, JSON, or text

> **Using Impact Vision in your fund workflow?** See the
> [Fund Manager Quick Reference](docs/fund-manager-guide.md) for a
> Python-first 60-second SDK walkthrough (deal scoring, IC memo,
> DD questionnaire, portfolio roll-up, LP calendar).
>
> New to the jargon (5D, NESTA, OPIM, SFDR …)? See the
> [plain-language glossary](docs/glossary.md); every HTML report also ends
> with definitions of the terms it uses.

## Quick Start (from scratch)

### 1. Prerequisites

You need **Python 3.11+** and **Git**. The interactive terminal agent
(`impact-vision` with no arguments) also needs **Node.js 20+**; `demo`,
`assess`, the browser chat and the other CLI commands don't.

```bash
python --version    # should show 3.11 or higher
git --version       # any recent version
node --version      # only for the interactive terminal agent
```

If not installed: [Python](https://www.python.org/downloads/) | [Git](https://git-scm.com/downloads) | [Node.js](https://nodejs.org)

### 2. Clone and install

```bash
git clone https://github.com/joejoe168168/impact-vision.git
cd impact-vision
```

Create a virtual environment (recommended):

```bash
python -m venv .venv

# Activate it:
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Windows CMD:         .venv\Scripts\activate.bat
# Mac/Linux:           source .venv/bin/activate
```

Install the package (`dev` includes every optional extra plus the test tools):

```bash
pip install -e ".[dev]"
```

The core install is enough for `demo`, `assess`, reports and the agent.
Optional extras add the other surfaces: `[web]` (browser chat + REST API),
`[dashboard]` (Streamlit), `[office]` (Word/PowerPoint exports), `[tui]`,
`[pdf]` (PDF export; then run `playwright install chromium`), or `[all]`. For example: `pip install -e ".[web,office]"`.

> **`'impact-vision' is not recognized`?** Run the auto-fix script:
>
> ```bash
> # Windows PowerShell
> powershell -ExecutionPolicy Bypass -File scripts\add-to-path.ps1
>
> # Windows CMD
> scripts\add-to-path.bat
>
> # Mac/Linux
> bash scripts/add-to-path.sh
> ```
>
> **Important:** After running the script, you must **close and reopen your terminal** (CMD/PowerShell/Terminal) for the PATH change to take effect. Then try `impact-vision --help`.
>
> **Alternative:** Use `python -m openharness` instead (works without PATH changes):
>
> ```bash
> python -m openharness --help
> python -m openharness catalog stats
> python -m openharness dd list
> ```

### 3. Set up an LLM provider

The AI agent needs a tool-calling language model. Run the setup wizard and
choose a provider; credentials are stored locally and must never be committed.

```bash
impact-vision setup
```

| Provider | Setup choice | Best for |
|----------|--------------|----------|
| OpenRouter | OpenAI-Compatible API | Trying multiple hosted models, including free tiers |
| Anthropic | Anthropic-Compatible API | Highest-quality production impact analysis |
| OpenAI | OpenAI-Compatible API | General-purpose hosted analysis |
| Ollama | `impact-vision ollama-setup --model llama3.2` | Local, private, offline analysis |

For hosted providers, select a model with reliable function/tool calling and
enough context for the documents you analyze. Local Ollama needs no API key;
the other providers require a credential from their service.

### 4. Start the AI agent

```bash
impact-vision
```

Try asking:
- "Analyze this pitch deck" (provide a path to a PDF)
- "What SDGs does a solar energy company align with?"
- "Run a 5-dimension assessment for a fintech serving 50,000 clients"

### 5. Try the CLI tools (no API key needed)

The fastest first result: assess three bundled (fictional) pitch decks and
open the reports in your browser:

```bash
impact-vision demo
```

Then assess your own deck or memo (`.pdf`, `.txt`, `.md`). This writes an
impact report, IC memo, DD report, DD questionnaire (`.docx`) and a JSON
summary:

```bash
impact-vision assess path/to/deck.pdf --open
impact-vision assess memo.pdf --sector agriculture --audience lp -o reports/
```

These commands also work without any LLM setup:

```bash
# See all available commands
impact-vision --help

# Browse IRIS+ metrics (all 787 metrics included out of the box)
impact-vision catalog stats
impact-vision catalog search "climate"
impact-vision catalog search "gender"

# List ESG/sustainability frameworks
impact-vision framework list

# Quick multi-framework scan of a company description
impact-vision framework scan "Solar energy company providing clean power to 50,000 rural households"

# Cross-reference a metric across all frameworks
impact-vision framework xref OI4112

# Browse the Due Diligence checklist (122 questions across 34 categories)
impact-vision dd list
impact-vision dd categories

# Analyze text against the DD checklist
impact-vision dd analyze "We serve 45,000 clients across 3 countries. Our NPS score is 72."
```

### 6. Update the IRIS+ Catalog (optional)

All 787 IRIS+ 5.3c metrics are already bundled and work out of the box. If GIIN releases a newer version of the catalog:

1. Download the new Excel file from [GIIN IRIS+](https://iris.thegiin.org/) (free registration)
2. Place it in `data/raw/`
3. Run:

```bash
impact-vision catalog load    # Parse Excel into JSON cache
impact-vision catalog stats   # Verify metric count
```

### 7. Launch the dashboard (optional)

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

The primary workflow: upload a PDF and let the agent analyze it.

```
> Analyze this pitch deck for impact: /path/to/pitch_deck.pdf
```

The agent will use the `pitch_deck_analyze` tool which:
- Extracts text from all PDF pages
- Identifies impact claims and maps them to IRIS+ metrics and SDGs
- Runs the full DD checklist against the document
- Presents addressed questions vs. gaps
- Suggests follow-up questions to ask the investment team

Follow-up prompts that chain the v3/v4 tools on the same deal:

```
> Run a 5-dimension assessment for BrightPath Finance with the claims you just extracted
> Draft a Theory of Change for BrightPath and link it to IRIS+ metrics
> Score greenwashing risk per-claim and show which claims need verification
> Build a completeness scorecard for the data pack and produce coaching cards
> Run the AI extraction review queue over the claims you flagged as low-confidence
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
> Generate an HTML impact report for BrightPath Finance (includes Plotly charts)
> Export the assessment as XLSX for our LP report
> Generate a report with sector benchmark comparison
```

HTML reports include an **Interactive Score Improvement** section -- check boxes for practices your organization follows (e.g., "We track beneficiaries", "We have a Theory of Change") and watch scores update in real-time with a before/after radar chart.

Reports are built for sharing with investment committees, LPs, and regulators: an **audience filter** (LP / IC / regulator / public) tailors which sections show, an **executive tear sheet** gives an at-a-glance summary, **confidence bands** surface evidence quality, and every section is **collapsible** with copy-link anchors for deep-linking. The reading chrome (progress bar, scrollspy table of contents, sticky company/grade header) is **WCAG 2.2 AA accessible** -- skip links, keyboard navigation, and reduced-motion support -- with an in-browser **dark mode** toggle and **white-label branding**. Print and PDF output ships a cover page, running page numbers, and a confidentiality footer, and the **PDF export is tagged (PDF/UA-1)** for accessibility.

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
├── src/openharness/
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
│   │   ├── greenwashing.py            # Greenwashing detection (standard + Green Claims + FCA + NLP)
│   │   ├── risk_opportunity.py        # Risk/opportunity (likelihood × severity)
│   │   ├── storage.py                 # SQLite persistence for assessments
│   │   ├── pipeline.py                # Document → full assessment → reports (assess / demo)
│   │   ├── claim_metric_mapper.py     # Pitch quantities → IRIS+ metric IDs
│   │   ├── glossary.py                # Plain-language glossary (docs + report appendix)
│   │   ├── _paths.py                  # Bundled-data resolver (source checkout + wheel)
│   │   │
│   │   │   # --- Fund workflow (v0.8+) ---
│   │   ├── fund_thesis.py             # Fund impact thesis, IC gate, adverse thresholds
│   │   ├── ic_memo.py                 # IC memo rendering (MD/HTML/DOCX/PPTX)
│   │   ├── deal_gate.py               # Deal scorecard (pass/warn/fail gate)
│   │   ├── portfolio_rollup.py        # Capital-weighted portfolio roll-up
│   │   ├── lp_calendar.py             # 12-month LP reporting calendar
│   │   ├── tenancy.py                 # Multi-tenant + RBAC
│   │   ├── plugins.py                 # Entry-point plug-in discovery
│   │   ├── signed_feed.py             # Hash-chained LP report feed (HMAC)
│   │   ├── lp_portal.py               # ILPA-compatible LP portal
│   │   ├── marketplace.py             # Thesis marketplace (publish/subscribe)
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
│   │   │
│   │   │   # --- v2 institutional backbone (v0.13+) ---
│   │   ├── metric_records.py          # Canonical MetricRecord contract
│   │   ├── investee_collection.py     # Questionnaire schema + submission lifecycle
│   │   ├── climate_accounting.py      # Entity carbon calculator: Scope 1/2/3, intensity, trends
│   │   ├── lca.py                      # LCA/LCSA, lifecycle costs, social hotspots, LCM plans
│   │   ├── evidence_graph.py          # Claim↔metric↔target↔evidence lineage
│   │   ├── standards_registry.py      # Versioned standards metadata
│   │   ├── roadmap_v2.py              # Collection / disclosure / assurance helpers
│   │   │
│   │   │   # --- v3 Trust Infrastructure (v0.15.0) ---
│   │   ├── emission_factors.py        # Versioned factors + sensitivity/provenance bands
│   │   ├── stakeholder_voice.py       # Lean Data + GDPR/PDPA consent
│   │   ├── evidence_workflow.py       # AI extraction review queue
│   │   ├── verification_workspace.py  # Assurer workspace + findings
│   │   ├── lp_narrative.py            # LP narrative + Q&A (approved-data only)
│   │   ├── greenwashing_reviewer.py   # Per-claim explainable review
│   │   ├── portfolio_nlq.py           # NL portfolio queries + ApprovedDataPolicy
│   │   ├── exit_impact.py             # OPIM Principle 8 exit-impact scoring + learning context
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
│   │   ├── frameworks/                # 20+ ESG/sustainability frameworks
│   │   │   ├── sasb.py · gri.py · tcfd.py · sfdr_pai.py · edci.py
│   │   │   ├── unpri.py · theory_of_change.py · issb_ifrs_s1.py · issb_ifrs_s2.py
│   │   │   ├── esrs.py · ifc_opim.py · pcaf.py · sbti.py · eu_taxonomy.py
│   │   │   ├── tnfd.py · cdp.py
│   │   │   └── cross_reference.py     # 59 cross-framework metric mappings
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
│   ├── esrs_simplified_2026.yaml      # Revised-ESRS screening fixture with provenance metadata
│   ├── issb_s2_amendments.yaml        # Issued IFRS S2 amendments and effective dates
│   ├── standard_articles/             # Article-level standards/regulatory summaries
│   ├── scoring_config.yaml            # Sector baselines + keyword boosts
│   ├── sdg_keywords.yaml              # SDG keyword mappings for 20+ sectors
│   ├── core_metric_set_per_sdg.yaml   # Curated SDG core metric set
│   ├── core_metric_sets_by_sector.yaml # Core metric set per sector (gap analysis)
│   ├── claim_metric_map.yaml          # Rules mapping pitch quantities to IRIS+ IDs
│   ├── glossary.yaml                  # Plain-language glossary (source of docs/glossary.md)
│   ├── sample_decks/                  # Fictional sample pitch decks for `impact-vision demo`
│   ├── fund_thesis.*.yaml             # Default + 4 regional thesis packs
│   └── i18n/                          # 6 languages (en/es/fr/pt/zh/ar)
├── docs/
│   ├── fund-manager-guide.md          # Python SDK walkthrough for funds
│   ├── roadmap-v3.md / -v3-implementation.md
│   ├── roadmap-v4.md                  # Consultant-led engagement suite
│   ├── roadmap-updates-2026-07.md     # Current regulatory and implementation delta
│   ├── roadmap-v7.md                  # Current roadmap: trust, ease of use, reports, standards
│   ├── glossary.md · dd-checklist.md · climate-and-lca.md
│   └── cursor-integration.md          # Cursor/VS Code MCP setup
├── examples/                          # Sample company, portfolio, MCP configs
├── tests/                             # Test suite (impact + v2 + v3 + v4)
└── .github/workflows/ci.yml           # Import smoke + tests + ruff
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
`cross_reference` module (59 concept mappings).

| Category | Framework | Coverage |
|----------|-----------|----------|
| **Core taxonomy** | GIIN IRIS+ 5.3c | ~787 metrics, SDG mappings, 5-Dimension tags |
| | UN SDGs | 17 Goals, 169 Targets |
| | Impact DD Checklist | 122 questions / 34 categories (GIIN, PCV, Seraf, IMP, AFME + 15 sectors) with NESTA evidence (1-5) |
| | Sector Benchmarks | 18 sectors (GIIN survey data) with aggregated 5D scores and coverage |
| | Cross-Reference Mapping | 59 concepts mapped across IRIS+/GRI/EDCI/SFDR PAI/SASB/TCFD/ESRS/ISSB/PCAF/SBTi/TNFD/CDP/EU Taxonomy |
| **ESG disclosure** | SASB | 17 industries, 77+ material topics |
| | GRI | 34 standards (Universal + Topic), 120+ disclosures |
| | TCFD / IFRS S2 | 4 pillars, 11 disclosures, scenario analysis, Scope 1/2/3 |
| | EDCI | 2026 PE/VC KPI fields, including non-core cybersecurity testing |
| | UNPRI | 6 Principles, 27 actions |
| | Theory of Change | RS Group 8 Blended Value Principles + GIIN 8-step ToC Checklist |
| | ISSB IFRS S1 | General sustainability disclosure (4 pillars) |
| | ISSB IFRS S2 | Climate-related disclosures plus an issued-amendments register (effective 2027-01-01) |
| | EU CSRD / ESRS | 11 standards, double-materiality; revised-ESRS screening fixture marked adopted pending Official Journal, with FY2027 effective-date metadata |
| | EFRAG VSME | Voluntary SME standard: Basic B1-B11 + Comprehensive C1-C9 (post-Omnibus default for out-of-scope SMEs) |
| | 2X Criteria | Gender-lens investing standard (6 dimensions + governance/GBVH minimum requirements) |
| | TISFD (beta) | Inequality & Social-related Financial Disclosures readiness: 4 pillars, 13 disclosures, GRI/ESRS crosswalk |
| **Regulatory** | SFDR | 14 mandatory + 9 optional PAI indicators, Article 6/8/9 classification, deadline scheduler |
| | SFDR 2.0 preview | Sustainable / Transition / ESG Basics category preview (70% threshold + exclusions + Art 8/9 migration; proposed law, ~2029) |
| | EU Omnibus I scope | CSRD/CSDDD in-scope decision tree (employee + turnover thresholds, FY2025-26 pause, VSME fallback) |
| | CSDDD / HRDD | UNGP + OECD 6-step value-chain human-rights due diligence (salience ranking, grievance score, remediation tracker, readiness band) |
| | EU Taxonomy | 6 environmental objectives, DNSH + Minimum Safeguards |
| | UK FCA Anti-Greenwashing Rule | Fair/clear/not-misleading assessment |
| | EU green claims (ECGT 2024/825) | Substantiation checks per the Empowering Consumers Directive (applies Sep 2026), plus stricter suspended-GCD best practice |
| | EU Digital Product Passport (ESPR) | Import + map to IRIS+/ESRS/SDG |
| | Per-jurisdiction packs | EU-SFDR, EU-CSRD, EU-CSDDD, UK-FCA-SDR, US-SEC-ESG, HK-HKEX-ESG, AU-AASB-S2, ISSB-global |
| **Climate & nature** | PCAF | Financed-emissions attribution, sector defaults, weighted data quality |
| | SBTi (Net-Zero Standard v1.2) | 1.5 °C pathway, Scope-3 materiality, 2050 cap |
| | TNFD v1 | 14 LEAP / pillar disclosures |
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
| | AI governance (EU AI Act) | Model card + data lineage + human-oversight log + risk classification & obligations |

### Agent Tools (48)

All tools below are exposed through the default OpenHarness tool registry
and `openharness.tools.impact`, so the interactive agent, web chat UI,
REST API, and MCP server see the same surface.

**Tool routing (1)**

| Tool | Description |
|------|-------------|
| `impact_advisor` | Tool router: ranks the most relevant tools for a free-text request and suggests multi-step playbooks (deal screening, LP reporting, regulatory compliance, verification, portfolio review, supply-chain HRDD, carbon & climate, data collection, theory of change) |
| `assess_deal` | Start here for a pitch deck or memo: one call runs the full offline screen (claims, IRIS+ metrics, 5D, SDGs, gaps, DD coverage, greenwashing, IC gate), optionally writes the reports, and returns an `assessment_id` that `impact_report`, `sdg_mapper`, `five_dimension_assess`, `gap_analysis` and `greenwashing_detect` accept instead of re-typed fields |

**Pre-screen & core assessment (7)**

| Tool | Description |
|------|-------------|
| `pitch_deck_analyze` | PDF/TXT/MD intake with impact-claim extraction + Company model; `action='compare_documents' / 'detect_changes' / 'verify_claims'` for multi-document checks |
| `iris_catalog` | IRIS+ catalog search, browse, filter by SDG/theme |
| `sdg_mapper` | SDG alignment scoring with theme inference and evidence chains |
| `five_dimension_assess` | 5-Dimension assessment with additionality & counterfactual prompts |
| `gap_analysis` | Metric gap analysis vs Core Metric Set |
| `impact_metric_recommender` | Recommend IRIS+ metrics by theme, SDG, and sector |
| `impact_data_quality` | Quality score for reported metrics (placeholders, unknown IDs) |

**Due diligence & evidence (4)**

| Tool | Description |
|------|-------------|
| `dd_checklist` | 122-question DD checklist, document analysis, and targeted suggestions |
| `product_passport` | EU Digital Product Passport import and IRIS+/ESRS mapping |

**Risk & credibility (3)**

| Tool | Description |
|------|-------------|
| `greenwashing_detect` | Composite screen (5 sub-scores) + Green Claims / FCA / GAI / CTI; `action='review_claims'` runs the per-claim explainable review with severity + governance metadata |
| `impact_risk_opportunity` | 14 risk categories on a likelihood × severity matrix |
| `exclusion_screening` | UNGC, weapons, fossil-fuel exclusion lists |

**Frameworks & reporting (6)**

| Tool | Description |
|------|-------------|
| `framework_assess` | Multi-framework ESG assessment (all frameworks in the table above, incl. VSME, 2X Criteria, TISFD, CDP questionnaire readiness) |
| `esg_toolbox` | Unified 33-module ESG toolbox for disclosure, ratings, export compliance, supplier ESG, sustainable finance, water stewardship, responsible mining, and carbon accounting; supports `list`, `search`, `get`, `methodology`, `checklist`, `assess`, `crosswalk`, `source_profile`, `recommend`, `workflow`, and `input_plan` |
| `cross_reference` | Cross-framework metric lookup (59 mappings) |
| `impact_report` | Interactive HTML reports + XLSX/CSV/JSON/text/PDF; `narrative_mode='narrative_prompt'` appends LLM narrative prompts (exec summary, key findings, impact narrative, case study) |
| `impact_valuation` | IFVI/VBA monetary impact accounting: value factors → net monetary impact, benefit/cost ratio, impact multiple of money |

**Decision workflow — v5 (2)**

| Tool | Description |
|------|-------------|
| `decision_workflow` | Quick screen, IC memo proof bundle, deal comparison, LP readiness, and context-driven impact target setting (`set_targets`) |
| `regulatory_calendar` | Jurisdiction-specific reporting deadlines, ISSB S2 amendment summaries, and a market-wide milestone watch-list (ECGT, revised ESRS, ISSA 5000, EUDR, CSDDD, SFDR 2.0); `action='radar_*'` is the review-gated regulatory-change radar |

**Portfolio workflow (5)**

| Tool | Description |
|------|-------------|
| `portfolio_analyze` | Batch analysis, capital-weighted roll-ups, benchmarking |
| `portfolio_query` | Natural-language portfolio queries (`ApprovedDataPolicy`-gated) |
| `pipeline` | 8-stage investment pipeline with transition tracking; `action='guided_*'` runs step-by-step assessments with deal-stage templates |
| `monitoring` | Continuous monitoring, metric updates, alerts, re-assessment |
| `trend_analysis` | Time-series metric trend analysis with trajectory projection |

**Stakeholder voice & narrative (3)**

| Tool | Description |
|------|-------------|
| `stakeholder_voice` | Lean Data templates + GDPR/PDPA consent + feedback↔claim links; `action='feedback_import' / 'feedback_analyze'` for beneficiary feedback data |
| `improvement_advisor` | LLM-guided improvement recs, peer insights, SDG opportunities |

**Trust infrastructure — v3 (4)**

| Tool | Description |
|------|-------------|
| `emission_factors` | Versioned factors and sensitivity; entity carbon inventory, Scope 2 certificate adjustment, selected manufacturing Scope 3, intensity, and trend outputs |
| `evidence_review` | AI extraction review queue with policy-driven auto-approval |
| `verification_workspace` | Verification prep (BlueMark / IFC OPIM / AA1000 readiness, evidence map) + assurer workspace with finding lifecycle and threaded comments |
| `lp_narrative` | LP narrative + Q&A constrained to verified data with citations |

**Lifecycle & climate (1)**

| Tool | Description |
|------|-------------|
| `lca_assessment` | ISO-aligned goal/scope, LCI/LCIA hotspots, sensitivity, lifecycle cost/social dimensions, readiness, and life-cycle-management plan; uses caller-supplied factors |

**Exit & assurance (1)**

| Tool | Description |
|------|-------------|
| `exit_impact` | OPIM Principle 8 scoring + exit plan |

**Consultant engagement suite — v4 (3)**

| Tool | Description |
|------|-------------|
| `engagement_workspace` | Engagement lifecycle (scoping → delivery → closeout) + artifact audit |
| `toc_builder` | ToC canvas + logic-chain validator + multi-framework KPI generator (wraps v3 `toc_graph` + `metric_recommender`) |
| `engagement_suite` | Umbrella tool for Tracks 3-10: proposal, data room, value-creation, reporting studio, training/readiness, public website, governed AI copilot, regulatory deadlines, 3-pillar assurance bundle |

**Frontier measurement & governance — v5 (5)**

| Tool | Description |
|------|-------------|
| `impact_quantifier` | Welfare quantifier (GIIN Impact Lab lineage): breadth × depth × theme × geography → QALYs + lives improved, cost-per-QALY, portfolio roll-up |
| `hrdd_assess` | Human-rights & value-chain due diligence (UNGP + OECD 6-step + CSDDD): salience ranking, grievance score, remediation tracker, CSDDD readiness band |
| `climate_scenario_risk` | NGFS physical/transition scenario screen with portfolio-weighted exposure, combined score, and illustrative value-at-risk per scenario |
| `ai_governance` | AI governance artifact (EU AI Act-aware): model card, data lineage, human-oversight log from the copilot review queue, risk classification + obligations |
| `investee_portal` | Generate a self-contained offline HTML data-collection portal (guided questionnaire, SFDR PAI plain language, validation, "why we ask", JSON export) |

**Comparable, assured & connected — v6 (7)**

| Tool | Description |
|------|-------------|
| `contribution_tracker` | Pre-register and monitor contribution claims, evidence, staleness, and attribution inflation |
| `carbon_credit_integrity` | ICVCM/VCMI carbon-credit and biodiversity-credit integrity screens |
| `impact_linked_finance` | KPI credibility, payment-by-results verification, and carry/SAFI simulations |
| `dmrv_evidence` | Hash, anchor, summarise, and verify digital MRV evidence |
| `survey_delivery` | Consent-gated WhatsApp, SMS, voice, and web survey delivery |
| `ddq_responder` | ILPA DDQ 2.0 / PRI 2026 answer drafting from approved evidence only; `action='template_generate'` fills ILPA / GIIN / EDCI / SFDR DDQ templates |

## Streamlit Dashboard

For a curated visual workflow, run:

```bash
streamlit run src/openharness/dashboard/app.py
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
| `/console` | **Tool console** — typed forms for every REST endpoint |
| `/docs` | OpenAPI explorer |
| `/api/v1/*` | REST gateway |

The chat UI runs the *same* agent runtime as the CLI — same tools, skills,
slash commands and permission model — with streaming markdown replies,
collapsible tool-call cards, drag-and-drop file upload for pitch decks and
data rooms, a downloadable artifacts panel, a conversation history sidebar,
and in-browser provider/model/API-key settings so you can point it at Claude,
OpenAI, Ollama or any compatible endpoint without touching a config file.

Both surfaces are **single self-contained HTML files** — no build step, no JS
framework, no CDN.

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

Impact Vision can run as an **MCP server**, exposing the full impact
tool surface and 5 read-only resources to any MCP-compatible AI client.

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
uvicorn openharness.api_gateway.router:app --reload

# Authenticated (set env var for production)
IMPACT_VISION_API_KEY=your-secret-key uvicorn openharness.api_gateway.router:app
```

Key endpoints: `/api/v1/score`, `/api/v1/sdg-map`, `/api/v1/greenwashing`,
`/api/v1/report`, `/api/v1/pipeline`, `/api/v1/batch`, and more.
See the auto-generated OpenAPI docs at `/docs`.

## Roadmap

Strategy and engineering plans live in [`docs/`](docs/):

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
