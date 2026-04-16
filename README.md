# Impact Vision

Open-source AI-powered impact measurement and SDG alignment agent for VC and impact investment funds.

Built on [OpenHarness](https://github.com/HKUDS/OpenHarness), Impact Vision provides a conversational AI agent with deep expertise in GIIN's IRIS+ framework, UN Sustainable Development Goals, and impact due diligence workflows.

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
? Default model: nvidia/nemotron-3-super-120b-a12b:free  <-- type a model name
```

```
? Enter API key for OpenRouter: sk-or-your-key-here    <-- paste your key
```

```
? Model: nvidia/nemotron-3-super-120b-a12b:free        <-- press Enter to confirm
Setup complete:
- profile: openrouter
- provider: openai
- auth_source: openai_api_key
- model: nvidia/nemotron-3-super-120b-a12b:free
```

Done! You can now start the agent (Step 4).

> **Free models:** Browse all free models at [openrouter.ai/models?q=free](https://openrouter.ai/models?q=free). Some examples:
>
> | Model | Notes |
> |-------|-------|
> | `nvidia/nemotron-3-super-120b-a12b:free` | Strong reasoning, good for impact analysis |
> | `google/gemini-2.5-flash:free` | Fast, good for quick tasks |
> | `meta-llama/llama-4-maverick:free` | Open-source, balanced performance |
>
> You can change your model or update your API key later by running `impact-vision setup` again.

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
> - **Recommended:** Claude Sonnet, GPT-5, or `google/gemini-2.5-flash` (via OpenRouter)
> - **Good free options:** `google/gemini-2.5-flash:free`, `meta-llama/llama-4-maverick:free`
> - **May struggle:** Very small models or models without tool-calling support

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
| `iv framework list` | List all 10 ESG frameworks |
| `iv framework scan "text"` | Quick multi-framework scan |
| `iv framework xref OI4112` | Cross-reference a metric |
| `iv dd list` | Show all 122 DD questions |
| `iv dd categories` | List DD categories |
| `iv dd analyze "text"` | Check text against DD checklist |
| `iv ollama-setup` | Configure local LLM |
| `iv` | Start interactive AI agent |

(`iv` is a shorthand for `impact-vision`)

## Usage

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
> Show the 17 EDCI PE/VC metrics and which we're reporting
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
```

### Single-Prompt Mode

For CI/CD or scripting:

```bash
impact-vision -p "Search IRIS+ catalog for climate-related metrics"
```

## CLI Reference

```bash
# Interactive agent session
impact-vision                              # Start interactive session
impact-vision -p "your prompt"             # Single prompt, then exit
impact-vision --model opus                 # Use a specific model

# Catalog management
impact-vision catalog load [EXCEL_PATH]    # Load IRIS+ catalog from Excel
impact-vision catalog load --force         # Force reload from Excel
impact-vision catalog stats                # Show catalog statistics
impact-vision catalog search "climate"     # Search metrics by keyword

# Framework & DD CLI
impact-vision framework list               # List all ESG frameworks
impact-vision framework scan "description" # Quick multi-framework scan
impact-vision framework xref OI4112        # Cross-reference lookup
impact-vision dd list                      # List DD checklist questions
impact-vision dd categories                # List categories with counts
impact-vision dd analyze "text or file"    # Analyze text against DD checklist

# Local LLM setup
impact-vision ollama-setup                 # Configure Ollama (default: llama3.2)
impact-vision ollama-setup --model mistral # Use a different model

# Provider management
impact-vision setup                        # Interactive provider setup
impact-vision provider list                # List configured providers
impact-vision provider use NAME            # Switch active provider
impact-vision auth login                   # Authenticate with a provider
```

## Architecture

```
impact-vision/
├── src/openharness/
│   ├── impact/                        # Impact measurement engine
│   │   ├── models.py                  # Pydantic: Metric, Company, Assessment, SDG, ImpactClaim
│   │   ├── catalog.py                 # IRIS+ 5.3c Excel ETL (263-column parser)
│   │   ├── database.py                # In-memory MetricStore (search/filter/stats)
│   │   ├── sdg_taxonomy.py            # 17 SDG Goals + 169 Targets reference
│   │   ├── five_dimensions.py         # What/Who/HowMuch/Contribution/Risk scoring
│   │   ├── sdg_mapper.py              # Per-goal SDG alignment scorer (0-100)
│   │   ├── gap_analysis.py            # Core Metric Set coverage analysis
│   │   ├── dd_checklist.py            # DD question engine (load, analyze, suggest, evidence scoring)
│   │   ├── benchmarks.py             # Sector benchmarks for 18 sectors
│   │   ├── greenwashing.py           # Greenwashing detection (standard + Green Claims + FCA + NLP)
│   │   ├── risk_opportunity.py       # Risk/opportunity with likelihood x severity matrix
│   │   ├── storage.py                # SQLite persistence layer for assessments
│   │   ├── report_templates/         # Jinja2-based HTML report template engine
│   │   │   └── html_template.py      # Shared CSS, header/footer, SDG colors
│   │   └── frameworks/               # ESG/sustainability frameworks (10 frameworks)
│   │       ├── sasb.py                # SASB industry materiality (17 industries)
│   │       ├── gri.py                 # GRI Universal + Topic Standards (34 standards)
│   │       ├── tcfd.py                # TCFD / IFRS S2 climate disclosure (4 pillars)
│   │       ├── sfdr_pai.py            # SFDR 14+9 PAI indicators + Article 6/8/9
│   │       ├── edci.py                # EDCI 17 PE/VC ESG metrics
│   │       ├── unpri.py              # UNPRI 6 Principles (27 actions)
│   │       ├── theory_of_change.py   # RS Group + GIIN ToC framework
│   │       ├── issb_ifrs_s1.py       # ISSB IFRS S1 General Requirements
│   │       ├── issb_ifrs_s2.py       # ISSB IFRS S2 Climate Disclosures
│   │       ├── esrs.py               # EU CSRD/ESRS Double Materiality (11 standards)
│   │       ├── ifc_opim.py           # IFC Operating Principles for Impact Management
│   │       └── cross_reference.py    # 59 cross-framework metric mappings
│   ├── tools/impact/                  # Agent tools (17 LLM-callable tools)
│   │   ├── pitch_deck_analyze_tool.py # PDF/TXT/MD intake + full pipeline
│   │   ├── dd_checklist_tool.py       # DD question list/analyze/suggest
│   │   ├── iris_catalog_tool.py       # IRIS+ catalog search/browse
│   │   ├── sdg_mapper_tool.py         # SDG alignment scoring
│   │   ├── five_dimension_assess_tool.py # 5-Dimension assessment + additionality
│   │   ├── gap_analysis_tool.py       # Metric gap analysis
│   │   ├── impact_report_tool.py      # Report generation (HTML/CSV/JSON/text/XLSX)
│   │   ├── framework_tool.py          # Multi-framework ESG assessment (10 frameworks)
│   │   ├── cross_reference_tool.py    # Cross-framework metric lookup
│   │   ├── data_quality_tool.py       # Metric data quality assessment
│   │   ├── metric_recommender_tool.py # IRIS+ metric recommendation engine
│   │   ├── impact_risk_opportunity_tool.py # Risk/opportunity with 14 risk categories
│   │   ├── lp_ddq_export_tool.py      # LP DDQ exporter (ILPA/GIIN/EDCI/SFDR, XLSX/CSV)
│   │   ├── beneficiary_feedback_tool.py # Beneficiary feedback import & analysis
│   │   ├── verification_prep_tool.py  # Impact verification readiness (IFC OPIM)
│   │   ├── product_passport_tool.py   # EU Digital Product Passport import/mapping
│   │   ├── common.py                  # Shared input normalization helpers
│   │   └── portfolio_tool.py          # Portfolio batch analysis + scenario modeling
│   ├── dashboard/                     # Streamlit visual dashboard
│   │   └── app.py                     # 5-tab dashboard (Assessment/Catalog/DD/Framework/Portfolio)
│   ├── skills/bundled/content/        # Agent knowledge (markdown)
│   │   ├── iris-expert.md
│   │   ├── sdg-alignment.md
│   │   ├── five-dimensions.md
│   │   ├── impact-dd-guide.md
│   │   └── theory-of-change.md       # RS Group + GIIN ToC workflow
│   ├── prompts/system_prompt.py       # Impact Vision persona + instructions
│   └── cli.py                         # CLI with catalog subcommands
├── data/
│   ├── raw/                           # IRIS+ Excel file (not committed)
│   ├── processed/                     # JSON catalog cache (auto-generated)
│   ├── dd_checklist.yaml              # 122 DD questions (GIIN/PCV/Seraf/IMP/AFME + 15 sectors)
│   ├── scoring_config.yaml           # Sector baselines, keyword boosts, risk/opportunity rules
│   └── sdg_keywords.yaml             # SDG keyword mappings for 20+ sectors
├── examples/
│   ├── sample_company.yaml            # Example company with IRIS+ metrics
│   └── sample_portfolio.csv           # Portfolio of 5 companies
├── scripts/
│   └── check_imports.py              # CI import smoke checks (verify __init__.py + exports)
├── .github/workflows/
│   └── ci.yml                        # GitHub Actions: import checks, tests, lint
└── tests/
    ├── test_impact.py                # 54+ tests covering impact modules, tools + 10 frameworks
    ├── test_report_generation.py     # 23 tests for reports, templates, and persistence
    └── ...                           # 820+ tests across all subsystems
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

## Standards Supported

### Core (v0.1)
- **GIIN IRIS+ 5.3c**: Full catalog (~787 metrics), SDG mappings, 5-Dimension tags
- **UN SDGs**: 17 Goals, 169 Targets with structured taxonomy
- **Impact DD Checklist**: 122 questions across 34 categories (GIIN, PCV, Seraf, IMP, AFME + 15 sectors) with NESTA evidence scoring
- **Sector Benchmarks**: 18 sectors with aggregated 5D scores, SDG coverage, and metric reporting benchmarks (GIIN survey data)
- **Cross-Reference Mapping**: 59 entries mapping equivalent metrics across IRIS+, GRI, EDCI, SFDR PAI, SASB, TCFD, ESRS, and ISSB

### ESG & Regulatory Frameworks (v0.3)
All accessible via the `framework_assess` tool:

| Framework | Coverage | Cross-references |
|-----------|----------|------------------|
| **SASB** | 17 industries, 77+ material topics (YAML-externalized) | IRIS+ metric IDs |
| **GRI** | 34 standards (Universal + Topic), 120+ disclosures | IRIS+ metric IDs |
| **TCFD / IFRS S2** | 4 pillars, 11 disclosures, scenario analysis | IRIS+, Scope 1/2/3 |
| **SFDR PAI** | 14 mandatory + 9 optional PAI indicators, Article 6/8/9 classification | IRIS+, GRI |
| **EDCI** | 17 core PE/VC metrics (Environment/Social/Governance) | IRIS+, GRI, SFDR PAI |
| **UNPRI** | 6 Principles, 27 actions | ESG integration assessment |
| **Theory of Change** | RS Group 8 Blended Value Principles + GIIN 8-step ToC Checklist | IMP, SDGs |
| **ISSB IFRS S1** | General sustainability disclosure requirements (4 pillars) | TCFD, ESRS |
| **ISSB IFRS S2** | Climate-related disclosures, Scope 1/2/3 | TCFD, ESRS, GRI |
| **EU CSRD/ESRS** | 11 standards, double materiality assessment, data points | IRIS+, GRI, SFDR |

### Regulatory Compliance (v0.2+)
| Standard | Coverage |
|----------|----------|
| **EU Green Claims Directive** | Evidence, comparability, third-party verification, carbon offset rules |
| **UK FCA Anti-Greenwashing Rule** | Fair/clear/not-misleading assessment, sustainability reference checks |
| **EU Digital Product Passport (ESPR)** | Import DPP data, map to IRIS+/ESRS/SDG, assess completeness |
| **IFC Operating Principles for Impact Management** | 9-principle verification readiness assessment |

### Greenwashing & NLP Detection (v0.2+)
| Capability | Description |
|------------|-------------|
| Standard greenwashing scoring | Vague language detection, quantitative evidence checks |
| Green Authenticity Index (GAI) | Ratio of substantive to vague claims |
| Cheap Talk Index (CTI) | Forward-looking vs. evidenced statement analysis |
| Sentiment Deflection | Detects positive-framing bias around negative topics |
| Claim Decomposition | Breaks claims into verifiable components |
| ClimateBERT integration | Stub for deep NLP classification (ready for model integration) |

### Tools (17 Impact Tools)
| Tool | Description |
|------|-------------|
| `pitch_deck_analyze` | PDF/TXT/MD intake with impact claim extraction and Company model |
| `dd_checklist` | DD question list, document analysis, and targeted suggestions |
| `iris_catalog` | IRIS+ catalog search, browse, filter by SDG/theme |
| `sdg_mapper` | SDG alignment scoring with theme inference |
| `five_dimension_assess` | 5-Dimension assessment with additionality & counterfactual prompts |
| `gap_analysis` | Metric gap analysis vs Core Metric Set |
| `impact_report` | Interactive HTML reports with Plotly charts (+ CSV/JSON/XLSX) |
| `framework_assess` | Multi-framework ESG assessment (10 frameworks including ISSB, ESRS) |
| `cross_reference` | Cross-framework metric lookup (59 mappings, PAI-prefix support) |
| `impact_data_quality` | Assess quality of reported metrics -- flags placeholders, unknown IDs |
| `impact_metric_recommender` | Recommend IRIS+ metrics based on themes, SDGs, and sector |
| `impact_risk_opportunity` | Risk/opportunity with 14 risk categories, likelihood x severity matrix |
| `lp_ddq_export` | Generate LP DDQ responses in ILPA, GIIN, EDCI, SFDR formats (XLSX/CSV) |
| `portfolio_analyze` | Portfolio batch analysis with scenario modeling |
| `beneficiary_feedback` | Import and analyze beneficiary feedback data |
| `verification_prep` | Impact verification readiness assessment (IFC OPIM 9 principles) |
| `product_passport` | EU Digital Product Passport data import and IRIS+/ESRS mapping |

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

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/ -v

# Run impact module tests (77+ tests, no external dependencies)
python -m pytest tests/test_impact.py tests/test_report_generation.py tests/test_tools/test_impact_tools_enhancements.py -v

# Run import smoke checks (verifies all package exports work)
python scripts/check_imports.py --all

# Lint
ruff check src/
```

### Testing Coverage

820+ tests across all subsystems:

| Test area | Tests | What it covers |
|-----------|------:|----------------|
| Impact engine | 54+ | IRIS+ catalog, SDG mapping, 5D scoring, gap analysis, DD checklist, benchmarks, 10 frameworks, cross-references, ISSB, ESRS, greenwashing |
| Report generation | 23+ | HTML/CSV/JSON/text report output, Jinja2 template engine, SQLite persistence layer |
| Tools | ~40 | Tool registry bootstrap, file/grep/glob tools, bash tool, MCP tools, integration flows |
| Services | 14 | Compaction system, session storage, token estimation |
| Config/bridge/hooks | ~30 | Settings load/save, work secrets, hook execution, hot reload |
| Commands | ~20 | CLI commands, command registry |
| Other | ~650+ | Permissions, memory, plugins, skills, swarm, coordinator, auth, prompts, sandbox, UI |

### CI

GitHub Actions runs on every push/PR to `main`:
1. **Import smoke check** -- verifies all `__init__.py` files exist and critical imports resolve
2. **Full test suite** -- `pytest tests/ -q --tb=short -x`
3. **Lint** -- `ruff check src/`

## License

MIT License. See [LICENSE](LICENSE) for details.

## Roadmap

Impact Vision v0.3 completed 149 improvement items across 6 phases. Here's what's next:

### Phase 7: Enhanced Analysis & Reporting UX 📊
- **Interactive report overlays** -- Click any 5D dimension or SDG bar to expand detailed overlays showing tracked vs. untracked metrics, evidence quality, claim evidence cards, and improvement suggestions
- **Evidence chain visualization** -- For each SDG mapping, see the full chain: claim → metric → evidence → SDG target, with confidence at each step
- **Impact pathway diagrams** -- Auto-generated Theory of Change flow diagrams from assessed data
- **PDF export** -- LP-ready PDF reports via WeasyPrint/Playwright
- **Report comparison mode** -- Side-by-side diff view comparing two assessments of the same company

### Phase 8: Pipeline & Portfolio Management 📁
- **Investment pipeline** -- Manage deal stages (sourcing → screening → DD → IC review → invested → monitoring → exited) with transition tracking and decision logs
- **Continuous monitoring** -- Schedule metric updates (quarterly/semi-annual/annual), auto-detect deviations, trigger alerts when scores drop or targets are missed
- **Per-project reporting** -- Period-over-period comparison reports, target progress with trajectory projections, LP-ready individual company reports
- **Aggregate portfolio impact** -- Fund-level roll-ups: total beneficiaries, aggregate SDG coverage, weighted 5D scores, cross-company benchmarking, impact attribution by sector/geography/SDG

### Phase 9: LLM Intelligence & Automation 🧠
- **Improvement advisor** -- For each weak dimension, generate specific recommendations: metrics to track, programs to implement, partnerships to pursue, with peer comparison insights
- **Smart document analysis** -- Multi-document comparison, version change detection, and automated claim verification against external sources
- **Conversational assessment** -- Guided step-by-step assessment workflow, progressive data collection across sessions, deal-stage-appropriate assessment templates
- **Narrative drafting** -- LLM-generated executive summaries, impact narratives, and case studies from structured data

### Phase 10: Platform Integration & Developer Experience 🔌
- **MCP server mode** -- Expose all 17 Impact Vision tools as MCP resources/tools for AI agents (Claude Code, Cursor, etc.)
- **Claude Code integration** -- Ready-to-use configs and documentation for using Impact Vision as an MCP tool in Claude Code and Cursor IDE
- **Full REST API** -- Expand from 5 endpoints to full tool coverage, with API auth, batch processing, and webhook notifications
- **Multi-language support** -- Localized reports, DD questionnaires, and agent interactions in Spanish, French, Portuguese, Chinese, and Arabic

See the full [ROADMAP.md](ROADMAP.md) for detailed item-by-item tracking (45 items across 4 phases).

Have ideas? Open an [issue](https://github.com/joejoe168168/impact-vision/issues) or submit a PR!

## Acknowledgments

- [AvantFaire Investment Management](https://www.avantfaireim.com/) -- the first impact investment company in Hong Kong that nurtured the creator's passion for impact measurement
- [GIIN](https://thegiin.org/) for IRIS+ and the Impact Due Diligence Guide
- [Pacific Community Ventures](https://www.pacificcommunityventures.org/) for DD emerging best practices
- [Seraf](https://seraf-investor.com/) for the impact investing DD checklist
- [Impact Management Project](https://impactfrontiers.org/) for the 5 Dimensions of Impact
- [OpenHarness](https://github.com/HKUDS/OpenHarness) for the agent infrastructure
