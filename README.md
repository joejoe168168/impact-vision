# Impact Vision

Open-source AI-powered impact measurement and SDG alignment agent for VC and impact investment funds.

Built on [OpenHarness](https://github.com/HKUDS/OpenHarness), Impact Vision ships a conversational AI agent, a **CLI**, a **REST API**, an **MCP server**, a **Streamlit dashboard**, and a **single-file Web Console** — all backed by the same engine with deep expertise in GIIN's IRIS+ framework, UN SDGs, the 5 Dimensions of Impact, and 10+ ESG / regulatory frameworks (ISSB, ESRS, SFDR, TCFD, SASB, GRI, PCAF, SBTi, EU Taxonomy, TNFD, CDP).

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

## Quick Start (from scratch)

### 1. Prerequisites

You need **Python 3.11+** and **Git**. Check if they're installed:

```bash
python --version    # should show 3.11 or higher
git --version       # any recent version
```

If not installed: [Python](https://www.python.org/downloads/) | [Git](https://git-scm.com/downloads)

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

Install the package:

```bash
pip install -e ".[dev]"
```

After this, you'll have two commands available: `impact-vision` and `iv` (shorthand).

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

The AI agent needs a language model. We recommend **OpenRouter** for beginners -- it's free to start and gives you access to many models.

#### Option A: OpenRouter (recommended -- free models available)

**Step 1.** Create an OpenRouter account:

1. Go to [openrouter.ai](https://openrouter.ai/) and click **Sign Up** (Google or GitHub login works)
2. Go to [openrouter.ai/keys](https://openrouter.ai/keys) and click **Create Key**
3. Copy the key (starts with `sk-or-...`)

**Step 2.** Run the interactive setup wizard:

```bash
impact-vision setup
```

The wizard will guide you through these prompts:

```
? Choose a provider workflow:
  Anthropic-Compatible API  Claude / Kimi / GLM / MiniMax
> OpenAI-Compatible API  OpenAI / OpenRouter          <-- select this
  ...
```

```
? Choose an OpenAI-compatible provider:
  OpenAI official
> OpenRouter                                          <-- select this
```

```
? Base URL: https://openrouter.ai/api/v1              <-- press Enter (default)
? Default model: openai/gpt-oss-120b:free             <-- type a model name
```

```
? Enter API key for OpenRouter: sk-or-your-key-here    <-- paste your key
```

Done! You can now start the agent (Step 4).

> **Free models (verified May 2026):** Browse the live list at
> [openrouter.ai/models?q=free](https://openrouter.ai/models?q=free).
> Impact analysis needs **tool calling**, so stick with these:
>
> | Model | Context | Why we recommend it |
> |-------|--------:|---------------------|
> | `openai/gpt-oss-120b:free` | 131K | OpenAI open-weight MoE, native tool use, strong reasoning |
> | `nvidia/nemotron-3-super-120b-a12b:free` | 1M | 1M-token window for long decks, strong multi-step reasoning |
> | `z-ai/glm-4.5-air:free` | 131K | Hybrid-thinking MoE, cheap + fast, tool-calling |
> | `google/gemma-4-31b-it:free` | 262K | Native function calling, multimodal, Apache 2.0 |
>
> OpenRouter rotates free endpoints monthly — if a model 404s, re-run
> `impact-vision setup` and pick another from the live list.

#### Option B: Anthropic (Claude Sonnet) -- best quality for impact analysis

1. Go to [console.anthropic.com](https://console.anthropic.com/), create an account
2. Go to **API Keys** and create a key
3. Run the wizard and choose **Anthropic-Compatible API** > **Claude official**:

```bash
impact-vision setup
```

4. Paste your API key when prompted (Claude Sonnet is the default model)

#### Option C: OpenAI (GPT-5)

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys), create a key
2. Run the wizard and choose **OpenAI-Compatible API** > **OpenAI official**:

```bash
impact-vision setup
```

3. Paste your API key when prompted

#### Option D: Local Ollama (free, runs on your machine, no internet needed)

1. Install Ollama from [ollama.com](https://ollama.com/)
2. Pull a model: `ollama pull llama3.2`
3. Run setup:

```bash
impact-vision ollama-setup --model llama3.2
```

No API key needed -- everything runs locally on your GPU/CPU.

| Provider | Best for | Cost |
|----------|----------|------|
| [OpenRouter](https://openrouter.ai/models?q=free) | Trying multiple models, free tier | Free + pay-per-use |
| Anthropic (Claude Sonnet) | Best impact analysis quality | Pay-per-use |
| OpenAI (GPT-5) | General purpose | Pay-per-use |
| Ollama (local) | Privacy, offline use | Free (your hardware) |

> **Model quality note:** Impact analysis requires models that support **tool calling** (function calling). Free models vary in quality -- some may not follow the impact expert persona or use the analysis tools correctly. For best results:
> - **Recommended paid:** Claude Sonnet or GPT-5 for production DD work
> - **Recommended free:** `openai/gpt-oss-120b:free`, `nvidia/nemotron-3-super-120b-a12b:free`, `z-ai/glm-4.5-air:free`
> - **May struggle:** Very small models (<9B) or models without tool-calling support

### 4. Start the AI agent

```bash
impact-vision
```

Try asking:
- "Analyze this pitch deck" (provide a path to a PDF)
- "What SDGs does a solar energy company align with?"
- "Run a 5-dimension assessment for a fintech serving 50,000 clients"

### 5. Try the CLI tools (no API key needed)

These commands work without any LLM setup:

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
streamlit run src/openharness/dashboard/app.py
```

Opens a web dashboard at http://localhost:8501 with 5 tabs: Assessment, IRIS+ Catalog, DD Checklist, Framework Scan, and Portfolio.

### Quick reference

| Command | What it does |
|---------|-------------|
| `iv --help` | Show all commands |
| `iv catalog stats` | Show catalog statistics |
| `iv catalog search "query"` | Search IRIS+ metrics |
| `iv framework list` | List all supported ESG / regulatory frameworks |
| `iv framework scan "text"` | Quick multi-framework scan |
| `iv framework xref OI4112` | Cross-reference a metric |
| `iv dd list` | Show all 122 DD questions |
| `iv dd categories` | List DD categories |
| `iv dd analyze "text"` | Check text against DD checklist |
| `iv ollama-setup` | Configure local LLM |
| `iv serve-mcp` | Start MCP server for AI agents (45 impact tools + 5 resources) |
| `iv serve-web` | Start Web Console + REST API at http://127.0.0.1:8787 |
| `iv` | Start interactive AI agent |

(`iv` is a shorthand for `impact-vision`)

## Usage

Impact Vision ships **45 impact agent tools** covering the full investment lifecycle
— pre-screen, due diligence, IC memo, portfolio monitoring, LP reporting,
assurance, and post-exit review. Below are common prompts you can paste
into the interactive agent (or the Web Console at
`http://127.0.0.1:8787`). The agent will pick the right tools for you.

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
> Start an engagement workspace for BrightPath at the "scoping" stage
> Attach a data pack: these metrics came from the audited FY24 statements
> Build a completeness scorecard for the data pack and produce coaching cards
> Run the AI extraction review queue over the claims you flagged as low-confidence
```

### Browsing the IRIS+ Catalog

```
> Search for IRIS+ metrics related to financial inclusion
> Show me metrics mapped to SDG 7 (Clean Energy)
> What metrics are tagged with the "What" dimension?
> Get details for metric OI1479
```

### Running a DD Checklist

```
> Show me the full impact DD checklist
> Which DD questions are about risk assessment?
> Analyze this document against the DD checklist: /path/to/memo.pdf
```

### SDG Alignment Scoring

```
> Map BrightPath Finance to SDG goals. They report metrics PI4060, OI8869, OI6213...
> Which SDGs does this company align with based on their financial inclusion work?
```

### 5-Dimension Assessment

```
> Score this company on the 5 Dimensions of Impact
> What are the gaps in the "Contribution" dimension?
```

### Cross-Reference Lookup

```
> Look up cross-references for IRIS+ metric OI4112
> Search cross-references for "gender" across all frameworks
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

Ask the agent to help you improve your impact scores interactively:

```
> Help me improve my impact scores for this pig farm
> Ask me questions to strengthen the assessment
```

The agent will:
1. Identify your weakest scoring dimensions
2. Ask targeted questions (e.g., "How many direct beneficiaries?", "Do you track emissions?")
3. Map your answers to IRIS+ metrics
4. Re-run the assessment and show exactly how your answers improved each dimension

### ESG Framework Assessment

```
> Scan this company against all ESG frameworks
> What are the material SASB topics for a fintech company?
> Assess TCFD alignment for our climate disclosure
> Check SFDR PAI compliance for the portfolio
> Show the EDCI 2026 private-markets KPI fields and which we're reporting
> Run a UNPRI self-assessment for our fund
> Assess ISSB IFRS S1 general disclosure readiness
> Check ISSB IFRS S2 climate disclosure for our carbon data
> Run EU CSRD/ESRS double materiality assessment
> Classify our fund under SFDR Article 6/8/9
```

### Theory of Change Assessment

```
> Assess our fund's Theory of Change against RS Group's Blended Value principles
> Check our ToC against the GIIN IRIS+ checklist
> Help me develop a Theory of Change for our microfinance investment
> List all RS Group principles and GIIN ToC steps
```

### Greenwashing & Compliance Checks

```
> Run a greenwashing check on this pitch deck
> Assess EU Green Claims Directive compliance
> Check UK FCA Anti-Greenwashing Rule alignment
> Compute the Green Authenticity Index and Cheap Talk Index for this report
```

### Impact Verification & Product Passport

```
> Check our readiness for IFC OPIM verification
> Import Digital Product Passport data from this JSON file
> Map DPP categories to IRIS+ and ESRS metrics
```

### LP DDQ Export

```
> Generate an ILPA DDQ response for BrightPath Finance
> Create a GIIN/IRIS+ impact report template
> Export EDCI annual survey as XLSX: output_path="edci_survey.xlsx"
```

### Portfolio Batch Analysis

```
> Analyze this portfolio CSV file: examples/sample_portfolio.csv
> Generate aggregated SDG coverage for the portfolio
> Run portfolio roll-up with fund-level 5D scores
> Generate an LP report for our fund
> Show impact attribution by sector and geography
```

### Pipeline Management

```
> Add EcoFinance to the pipeline at screening stage
> Transition EcoFinance to DD in progress with rationale "Strong SDG alignment"
> Show the pipeline dashboard
> List all companies at IC review stage
```

### Continuous Monitoring

```
> Set quarterly monitoring for EcoFinance
> Record metric PI4060 = 15000 for EcoFinance
> Check alerts for our portfolio
> Run a full re-assessment for EcoFinance
```

### Guided Assessment

```
> Start a screening assessment for BrightPath Finance
> What's the next step in the assessment?
> Submit company description data for the current step
```

### Stakeholder Voice & Beneficiary Feedback

```
> Build a Lean Data survey template for smallholder farmers in Kenya
> Register GDPR-compliant consent records for 50 beneficiaries
> Score feedback quality and link responses to our outcome claims
```

### Climate Accounting (Scope 1/2/3 + PCAF)

```
> Calculate a Scope 1/2 GHG inventory from this fuel + electricity data
> Apply emission factor catalog v2 with uncertainty bands
> Run PCAF financed-emissions attribution for the loan book
> Check SBTi 1.5 °C alignment
```

### AI Extraction Review & Evidence Governance

```
> Show the AI extraction review queue for BrightPath
> Auto-approve claims above 0.85 confidence that cite audited sources
> Flag any claim without a source URL for human review
> Open a verification workspace for the assurer and share only approved evidence
```

### LP Narrative & Q&A (grounded in verified data)

```
> Generate an LP quarterly narrative for the Inclusive Finance fund
> Answer LP question "what % of beneficiaries are women" using only approved data
> Export the Q&A transcript with citations for the LPAC meeting
```

### Portfolio Natural-Language Query

```
> What was the average CO2e intensity across the climate portfolio last year?
> Top 5 companies by beneficiary reach, verified data only
> Compare SDG 5 coverage between Fund I and Fund II
```

### Exit Impact Assessment (OPIM Principle 8)

```
> Score exit-impact durability for Solar Co with acquirer profile "strategic utility"
> List unmitigated risks and build a 12-month exit impact plan
```

### Consultant Engagements (v4 workspace)

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
subcommand groups plus three service commands. Run any command with
`--help` for full flags.

```bash
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
impact-vision serve-web                                  # Web Console + REST API (http://127.0.0.1:8787)

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
│   │   ├── climate_accounting.py      # Scope 1/2 GHG inventory
│   │   ├── evidence_graph.py          # Claim↔metric↔target↔evidence lineage
│   │   ├── standards_registry.py      # Versioned standards metadata
│   │   ├── roadmap_v2.py              # Collection / disclosure / assurance helpers
│   │   │
│   │   │   # --- v3 Trust Infrastructure (v0.15.0) ---
│   │   ├── emission_factors.py        # Versioned factors + sensitivity bands
│   │   ├── stakeholder_voice.py       # Lean Data + GDPR/PDPA consent
│   │   ├── evidence_workflow.py       # AI extraction review queue
│   │   ├── verification_workspace.py  # Assurer workspace + findings
│   │   ├── lp_narrative.py            # LP narrative + Q&A (approved-data only)
│   │   ├── greenwashing_reviewer.py   # Per-claim explainable review
│   │   ├── portfolio_nlq.py           # NL portfolio queries + ApprovedDataPolicy
│   │   ├── exit_impact.py             # OPIM P7 exit-impact scoring + P8 learning context
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
│   │   ├── frameworks/                # 10 ESG/sustainability frameworks
│   │   │   ├── sasb.py · gri.py · tcfd.py · sfdr_pai.py · edci.py
│   │   │   ├── unpri.py · theory_of_change.py · issb_ifrs_s1.py · issb_ifrs_s2.py
│   │   │   ├── esrs.py · ifc_opim.py · pcaf.py · sbti.py · eu_taxonomy.py
│   │   │   ├── tnfd.py · cdp.py
│   │   │   └── cross_reference.py     # 59 cross-framework metric mappings
│   │   ├── mcp_server.py              # MCP server (FastMCP)
│   │   └── sdk.py                     # High-level ImpactVision SDK facade
│   │
│   ├── tools/impact/                  # 45 LLM-callable impact agent tools (see "Tools" below)
│   ├── api_gateway/router.py          # FastAPI REST API
│   ├── web/                           # Single-file Web Console + SSE streaming
│   ├── dashboard/app.py               # Streamlit 5-tab dashboard
│   ├── skills/bundled/content/        # Agent knowledge (markdown)
│   ├── prompts/system_prompt.py       # Impact Vision persona + instructions
│   └── cli.py                         # CLI (7 subcommand groups + serve-mcp / serve-web)
├── data/
│   ├── raw/                           # IRIS+ Excel file (not committed)
│   ├── processed/                     # JSON catalog cache (auto-generated)
│   ├── dd_checklist.yaml              # 122 DD questions / 34 categories
│   ├── scoring_config.yaml            # Sector baselines + keyword boosts
│   ├── sdg_keywords.yaml              # SDG keyword mappings for 20+ sectors
│   ├── core_metric_set_per_sdg.yaml   # Curated SDG core metric set
│   ├── fund_thesis.*.yaml             # Default + 4 regional thesis packs
│   └── i18n/                          # 6 languages (en/es/fr/pt/zh/ar)
├── docs/
│   ├── fund-manager-guide.md          # Python SDK walkthrough for funds
│   ├── roadmap-v3.md / -v3-implementation.md
│   ├── roadmap-v4.md                  # Consultant-led engagement suite
│   └── cursor-integration.md          # Cursor/VS Code MCP setup
├── examples/                          # Sample company, portfolio, MCP configs
├── tests/                             # Test suite (impact + v2 + v3 + v4)
└── .github/workflows/ci.yml           # Import smoke + tests + ruff
```

## DD Checklist

The built-in due diligence checklist includes **122 questions** across **34 categories**, sourced from:

- **GIIN Impact Toolkit** - The Impact Due Diligence Guide
- **Pacific Community Ventures** - Impact DD Emerging Best Practices
- **Seraf Toolbox** - Impact Investing Due Diligence Checklist
- **Impact Management Project (IMP)** - Five Dimensions of Impact
- **AFME / Neotas / OECD** - ESG Due Diligence frameworks
- **Sector-specific**: 15 sectors including fintech, healthcare, agriculture, energy, education, manufacturing, transport, construction, tourism, retail, mining, media, professional services, waste management, and ICT

Each addressed question is assessed using **NESTA Standards of Evidence** (levels 1-5):

| Level | Description |
|------:|-------------|
| 1 | Narrative / anecdotal only (self-reported, no data) |
| 2 | Output data (quantified activities, e.g. # served) |
| 3 | Outcome data measured (pre/post, surveys, tracked KPIs) |
| 4 | Controlled comparison (quasi-experimental, benchmarks) |
| 5 | Rigorous evaluation (RCT, independent audit, causal attribution) |

Questions are organized into **34 categories** (18 core + 15 sector-specific + 1 SDG):

<details>
<summary><strong>Core Categories (18)</strong></summary>

| Category | Qs | Covers |
|----------|---:|--------|
| Impact Thesis & Theory of Change | 4 | Mission, theory of change, business model alignment |
| What (Outcomes) | 4 | Specific outcomes, positive/negative impacts, outcome data |
| Who (Stakeholders) | 5 | Beneficiaries, underserved status, baseline, feedback |
| How Much (Scale) | 5 | Reach, depth, duration, growth, quantitative metrics |
| Contribution | 4 | Additionality, counterfactual, evidence, investor contribution |
| Risk | 5 | Evidence risk, execution risk, external risk, mitigation, impact washing |
| Measurement Systems | 6 | IMM systems, IRIS+ alignment, data frequency, third-party audit |
| Governance/ESG | 5 | Board oversight, environmental/labor/ethics policies, incentives |
| SDG Alignment | 1 | Specific goals and targets |
| Negative Impact | 3 | Do-no-harm assessment, grievance mechanisms |
| Exit Sustainability | 3 | Impact continuity, mission lock, acquirer risk |
| Financial Sustainability | 5 | Revenue model, impact-return tension, grants dependency, pricing |
| Team & Capability | 4 | Founder experience, community ties, key person risk |
| Market & Context | 4 | Market size, regulation, systemic barriers, competition |
| Product/Service Design | 4 | User-centered design, safety, privacy, affordability |
| Supply Chain | 3 | ESG practices, forced/child labor risk, environmental footprint |
| Stakeholder Voice | 3 | Feedback mechanisms, co-design, transparency |
| Investor Alignment | 3 | Impact covenants, value-add beyond capital, portfolio fit |

</details>

<details>
<summary><strong>Sector-Specific Categories (15 sectors)</strong></summary>

| Sector | Qs | Covers |
|--------|---:|--------|
| Fintech | 5 | Over-indebtedness, client protection, effective interest rate, digital literacy, responsible AI |
| Healthcare | 5 | Health regulations, patient safety, clinical efficacy, affordability, data privacy |
| Agriculture | 5 | Farmer income, sustainable farming, climate resilience, food safety, land tenure |
| Energy | 5 | CO2e avoided, energy access, e-waste, affordability, grid reliability |
| Education | 5 | Learning outcomes, underserved learners, pedagogy, digital safety, employment |
| Manufacturing | 2 | Circular economy, pollution prevention, worker safety |
| Transport & Logistics | 2 | Emissions reduction, last-mile accessibility |
| Construction | 3 | Green building standards, affordable housing, waste diversion |
| Tourism | 2 | Cultural preservation, community benefit-sharing |
| Retail | 3 | Ethical sourcing, plastic waste reduction, fair labor |
| Mining & Extractives | 3 | Tailings management, community consent (FPIC), rehabilitation |
| Media | 2 | Misinformation safeguards, digital inclusion |
| Professional Services | 2 | Pro-bono access, diversity metrics |
| Waste Management | 3 | Recycling rates, informal worker integration, hazardous waste |
| ICT | 3 | E-waste, data sovereignty, digital divide |

</details>

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
| | ISSB IFRS S2 | Climate-related disclosures |
| | EU CSRD / ESRS | 11 standards, double-materiality; current to Omnibus I (Directive (EU) 2026/470) |
| | EFRAG VSME | Voluntary SME standard: Basic B1-B11 + Comprehensive C1-C9 (post-Omnibus default for out-of-scope SMEs) |
| | 2X Criteria | Gender-lens investing standard (6 dimensions + governance/GBVH minimum requirements) |
| | TISFD (beta) | Inequality & Social-related Financial Disclosures readiness: 4 pillars, 13 disclosures, GRI/ESRS crosswalk |
| **Regulatory** | SFDR | 14 mandatory + 9 optional PAI indicators, Article 6/8/9 classification, deadline scheduler |
| | EU Omnibus I scope | CSRD/CSDDD in-scope decision tree (employee + turnover thresholds, FY2025-26 pause, VSME fallback) |
| | CSDDD / HRDD | UNGP + OECD 6-step value-chain human-rights due diligence (salience ranking, grievance score, remediation tracker, readiness band) |
| | EU Taxonomy | 6 environmental objectives, DNSH + Minimum Safeguards |
| | UK FCA Anti-Greenwashing Rule | Fair/clear/not-misleading assessment |
| | EU Green Claims Directive | Evidence, comparability, third-party verification |
| | EU Digital Product Passport (ESPR) | Import + map to IRIS+/ESRS/SDG |
| | Per-jurisdiction packs | EU-SFDR, EU-CSRD, EU-CSDDD, UK-FCA-SDR, US-SEC-ESG, HK-HKEX-ESG, AU-AASB-S2, ISSB-global |
| **Climate & nature** | PCAF | Financed-emissions attribution, sector defaults, weighted data quality |
| | SBTi (Net-Zero Standard v1.2) | 1.5 °C pathway, Scope-3 materiality, 2050 cap |
| | TNFD v1 | 14 LEAP / pillar disclosures |
| | CDP | Climate / water / forests questionnaire intake |
| | GHG Protocol | Scope 1/2 inventory (Scope 3 via PCAF) with versioned factor catalog |
| | NGFS scenarios | Physical/transition portfolio exposure across 7 NGFS pathways + illustrative value-at-risk |
| **Impact management** | IFC OPIM | 9-principle verification readiness + Principle 8 exit-impact |
| | SROI | Deadweight / attribution / displacement / drop-off adjustments |
| | MOI + Impact-adjusted IRR | Newton-Raphson, optional shadow price |
| | IFVI / VBA monetary valuation | Value-factor catalogue → net monetary impact, benefit/cost ratio, impact multiple of money |
| | Welfare quantifier (QALYs) | breadth × depth × theme × geography → QALYs / lives improved + cost-per-QALY + portfolio roll-up |
| | Impact Target Setter | Context-driven conservative/base/stretch IRIS+/SDG target ranges from theme × geography × capital |
| **Greenwashing & NLP** | Standard greenwashing scoring | Vague-language + quantitative-evidence checks |
| | Green Authenticity Index (GAI) | Ratio of substantive to vague claims |
| | Cheap Talk Index (CTI) | Forward-looking vs. evidenced statements |
| | Per-claim explainable reviewer | `concrete` / `mixed` / `vague` / `buzzword_only` classification + severity |
| **Assurance** | ISAE 3000 / AA1000 | Management-assertion + subject-matter + evidence register |
| | SOC 2 Type II / ISO 27001 | Starter control set with readiness report |
| | Verification workspace | Finding lifecycle + threaded comments (v0.15.0) |
| | 3-pillar assurance bundle | HMAC-signed evidence graph + audit trail + workspace (v4) |
| | AI governance (EU AI Act) | Model card + data lineage + human-oversight log + risk classification & obligations |

### Agent Tools (45)

All tools below are exposed through the default OpenHarness tool registry
and `openharness.tools.impact`, so the interactive agent, Web Console,
REST API, and MCP server see the same surface.

**Pre-screen & core assessment (7)**

| Tool | Description |
|------|-------------|
| `pitch_deck_analyze` | PDF/TXT/MD intake with impact-claim extraction + Company model |
| `iris_catalog` | IRIS+ catalog search, browse, filter by SDG/theme |
| `sdg_mapper` | SDG alignment scoring with theme inference and evidence chains |
| `five_dimension_assess` | 5-Dimension assessment with additionality & counterfactual prompts |
| `gap_analysis` | Metric gap analysis vs Core Metric Set |
| `impact_metric_recommender` | Recommend IRIS+ metrics by theme, SDG, and sector |
| `impact_data_quality` | Quality score for reported metrics (placeholders, unknown IDs) |

**Due diligence & evidence (5)**

| Tool | Description |
|------|-------------|
| `dd_checklist` | 122-question DD checklist, document analysis, and targeted suggestions |
| `document_analysis` | Multi-document comparison, change detection, claim verification |
| `guided_assessment` | Step-by-step workflow with deal-stage templates |
| `verification_prep` | IFC OPIM 9-principle readiness assessment |
| `product_passport` | EU Digital Product Passport import and IRIS+/ESRS mapping |

**Risk & credibility (4)**

| Tool | Description |
|------|-------------|
| `greenwashing_detect` | Composite screen (5 sub-scores) + Green Claims / FCA / GAI / CTI |
| `greenwashing_reviewer` | Per-claim explainable review with severity + governance metadata |
| `impact_risk_opportunity` | 14 risk categories on a likelihood × severity matrix |
| `exclusion_screening` | UNGC, weapons, fossil-fuel exclusion lists |

**Frameworks & reporting (5)**

| Tool | Description |
|------|-------------|
| `framework_assess` | Multi-framework ESG assessment (all frameworks in the table above, incl. VSME, 2X Criteria, TISFD) |
| `cross_reference` | Cross-framework metric lookup (59 mappings) |
| `impact_report` | Interactive HTML reports + XLSX/CSV/JSON/text/PDF |
| `impact_valuation` | IFVI/VBA monetary impact accounting: value factors → net monetary impact, benefit/cost ratio, impact multiple of money |
| `lp_ddq_export` | LP DDQ responses in ILPA, GIIN, EDCI, SFDR formats |

**Decision workflow — v5 (2)**

| Tool | Description |
|------|-------------|
| `decision_workflow` | Quick screen, IC memo proof bundle, deal comparison, LP readiness, and context-driven impact target setting (`set_targets`) |
| `regulatory_calendar` | Jurisdiction-specific reporting deadlines for fund and engagement planning |

**Portfolio workflow (5)**

| Tool | Description |
|------|-------------|
| `portfolio_analyze` | Batch analysis, capital-weighted roll-ups, benchmarking |
| `portfolio_query` | Natural-language portfolio queries (`ApprovedDataPolicy`-gated) |
| `pipeline` | 8-stage investment pipeline with transition tracking |
| `monitoring` | Continuous monitoring, metric updates, alerts, re-assessment |
| `trend_analysis` | Time-series metric trend analysis with trajectory projection |

**Stakeholder voice & narrative (4)**

| Tool | Description |
|------|-------------|
| `beneficiary_feedback` | Import and analyze beneficiary feedback data |
| `stakeholder_voice` | Lean Data templates + GDPR/PDPA consent + feedback↔claim links |
| `improvement_advisor` | LLM-guided improvement recs, peer insights, SDG opportunities |
| `narrative` | Impact narrative drafting (exec summary, key findings, case studies) |

**Trust infrastructure — v3 (4)**

| Tool | Description |
|------|-------------|
| `emission_factors` | Versioned factor catalog, sensitivity bands, inventory repricing |
| `evidence_review` | AI extraction review queue with policy-driven auto-approval |
| `verification_workspace` | Assurer workspace with finding lifecycle and threaded comments |
| `lp_narrative` | LP narrative + Q&A constrained to verified data with citations |

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

## Streamlit Dashboard

For a visual alternative to the CLI agent:

```bash
streamlit run src/openharness/dashboard/app.py
```

The dashboard has 5 tabs:
1. **Company Assessment**: Input company data, see 5-Dimension radar chart, SDG bar chart, and gap analysis
2. **IRIS+ Catalog**: Browse, search, and filter the 787-metric catalog
3. **DD Checklist**: Browse questions, paste text to check coverage
4. **Framework Scan**: Run TCFD, SFDR PAI, EDCI, and SASB assessments
5. **Portfolio**: Upload CSV for batch analysis with aggregated charts

## Web Console (power-user UI)

For a browser-native surface to every tool — useful when you want the
full 45-tool set at your fingertips rather than Streamlit's 5 curated
tabs — run the **web console**:

```bash
# Start the console + REST API (defaults to http://127.0.0.1:8787)
impact-vision serve-web

# Or directly via uvicorn
uvicorn openharness.web.app:app --host 127.0.0.1 --port 8787
```

The console is a **single self-contained HTML file** (no build step, no
JS framework) that sits on top of the existing FastAPI gateway:

- Lists every impact tool in a searchable sidebar (`Ctrl/⌘+K` to focus).
- Derives typed forms from `/openapi.json` and `POST`s to `/api/v1/*`.
- Shows JSON results in a syntax-highlighted pane, with copy / save buttons.
- Persists every run to `localStorage` so you can re-hydrate old invocations.
- Optional bearer-token box for `IMPACT_VISION_API_KEY`-protected deployments.
- Links to the live `/docs` (Swagger) and the GitHub repo.

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

### Cursor / VS Code Setup

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "impact-vision": {
      "command": "impact-vision",
      "args": ["serve-mcp"]
    }
  }
}
```

### Claude Desktop Setup

Copy `examples/claude_desktop_config.json` to your Claude Desktop config directory.

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

FastAPI REST gateway backing the Web Console, MCP server, and third-party
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

- [`docs/roadmap-v2.md`](docs/roadmap-v2.md) — April 2026 institutional-readiness
  plan (data contracts, investee collection, climate accounting, LP reporting,
  assurance controls, causal impact, governed AI).
- [`docs/roadmap-v3.md`](docs/roadmap-v3.md) / [`-v3-implementation.md`](docs/roadmap-v3-implementation.md)
  — Trust infrastructure (evidence review, verification workspace, LP
  narrative, portfolio NLQ, exit impact). Shipped.
- [`docs/roadmap-v4.md`](docs/roadmap-v4.md) — Consultant-led engagement
  suite (Tracks 3-10). Backend shipped; frontend + paid-data wiring
  deferred to Wave 5.
- [`ROADMAP.md`](ROADMAP.md) — historical engineering record.
- [`CHANGELOG.md`](CHANGELOG.md) — release notes.

## Contributing

Have ideas? Open an [issue](https://github.com/joejoe168168/impact-vision/issues) or submit a PR!

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

- [AvantFaire Investment Management](https://www.avantfaireim.com/) -- the first impact investment company in Hong Kong that nurtured the creator's passion for impact measurement
- [GIIN](https://thegiin.org/) for IRIS+ and the Impact Due Diligence Guide
- [Pacific Community Ventures](https://www.pacificcommunityventures.org/) for DD emerging best practices
- [Seraf](https://seraf-investor.com/) for the impact investing DD checklist
- [Impact Management Project](https://impactfrontiers.org/) for the 5 Dimensions of Impact
- [OpenHarness](https://github.com/HKUDS/OpenHarness) for the agent infrastructure
