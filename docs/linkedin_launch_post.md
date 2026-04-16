# LinkedIn Launch Post - Impact Vision v0.6.0

*(Copy below for LinkedIn. ~2,200 words. Formatting preserved for LinkedIn.)*

---

**I've spent 8 years in impact investment. Now I'm giving the tools away for free.**

After nearly a decade in this space—evaluating deals, writing DD memos, mapping SDGs, wrestling with IRIS+ spreadsheets, and explaining to LPs why our metrics don't perfectly map to theirs—I've come to a frustrating conclusion:

The impact measurement tools we need either cost US$50-100k/year or don't exist.

I've always been enthusiastic about what AI can do. So during evenings and weekends, I built what I wish I'd had on Day 1 of my career. Today I'm releasing v0.6.0—the most comprehensive open-source impact measurement platform available.

**The Problem Nobody Wants to Talk About**

Impact investing has grown to over US$1 trillion in AUM. We have 14 ESG frameworks, 787 IRIS+ metrics, 169 SDG targets, and 14 mandatory EU disclosure indicators. Yet the typical early-stage impact fund still runs their DD on Excel spreadsheets and Word documents.

I've been in that room. Probably so have you:

- A founder claims alignment with 5 SDGs but can't name a single metric they track
- Your DD analyst spends 3 days cross-referencing IRIS+ codes with GRI disclosures
- Your LP asks for EDCI-formatted data, but your system uses SFDR categories
- You know the company *could* be impactful, but the evidence is at NESTA Level 1 (anecdotal)
- Your pipeline lives in a spreadsheet, your monitoring is ad-hoc, and your LP report is a manual cut-and-paste job every quarter

The enterprise platforms solve this—if you can afford them. The rest of us cobble together spreadsheets and hope we're not missing anything.

**So I Built Impact Vision**

Impact Vision is an open-source, AI-powered impact measurement and SDG alignment platform. Think of it as your entire impact analytics team—one that has memorized every IRIS+ metric, every SDG target, every framework cross-reference, and can run a full DD checklist in seconds.

After 10 phases and 197 features, here's what it does:

📄 **Upload a pitch deck** → It extracts impact claims, maps them to IRIS+ metrics and SDG targets, runs a 122-question DD checklist (GIIN, PCV, Seraf, IMP, AFME + 15 sector-specific modules), scores evidence using NESTA levels 1-5, detects greenwashing risk, and suggests follow-up questions. One command.

📊 **Interactive impact reports** → HTML reports with 5-Dimension radar plots, SDG alignment bars in UN colors, clickable overlays showing tracked vs. untracked metrics, evidence chain visualization (claim → metric → evidence → SDG target), and impact pathway diagrams. Also exports to PDF, Excel, CSV, and JSON.

🎯 **Real-time score improvement** → Check boxes for impact practices and watch scores update live. The AI agent asks targeted questions and shows exactly how each answer improves specific dimensions.

🏗️ **Full pipeline management** → Manage 8 investment stages (sourcing → screening → DD → IC review → invested → monitoring → exited → passed) with transition tracking, decision logs, and an interactive HTML dashboard with Plotly funnel charts.

📈 **Continuous monitoring** → Set quarterly/semi-annual schedules, record metric updates with automatic deviation detection, trigger alerts when scores drop or targets are missed, and run automated re-assessments.

🤖 **AI-powered recommendations** → The improvement advisor analyzes each weak dimension and generates specific recommendations: metrics to track, programs to implement, partnerships to pursue—with peer comparison insights from your sector.

🔗 **Cross-reference 59 metrics across 11 frameworks** → "What's the GRI equivalent of IRIS+ OI4112?" → "GRI 305-1, EDCI-E1, SFDR PAI #1, TCFD MET-B, ISSB S2, ESRS E1, SDG 13." One lookup. Seven standards.

🔌 **MCP Server for AI agents** → Run `impact-vision serve-mcp` and all 25 tools are instantly available in Claude Desktop, Cursor IDE, VS Code, or any MCP-compatible AI client.

🌐 **Full REST API** → 25+ FastAPI endpoints with API key auth, batch processing for multi-company assessment, and HMAC-signed webhooks.

🌍 **6 languages** → Reports, DD questionnaires, and agent persona in English, Spanish, French, Portuguese, Chinese, and Arabic.

**What's Under the Hood**

This isn't a ChatGPT wrapper with a prompt. It's a structured impact measurement engine:

- **787 IRIS+ 5.3c metrics** fully parsed, with SDG mappings, 5-Dimension tags, and smart search
- **11 ESG framework modules**: SASB, GRI, TCFD/IFRS S2, SFDR PAI, EDCI, UNPRI, Theory of Change, ISSB S1, ISSB S2, EU CSRD/ESRS, IFC OPIM
- **122 DD questions** across 34 categories, including sector-specific questions for 15 sectors
- **Greenwashing detection** with 5 sub-scores, Green Authenticity Index, Cheap Talk Index, and regulatory compliance checks (EU Green Claims, UK FCA Anti-Greenwashing)
- **25 LLM-callable tools** that work as an AI agent—natural language conversation about impact, and it runs the right analyses
- **SQLite persistence** for assessments, pipeline, monitoring schedules, and alerts
- **Sector benchmarks** for 18 sectors with GIIN survey data
- **Exclusion screening** against UNGC violations, controversial weapons, fossil fuels, and more

Built on HKU's OpenHarness agent framework. Python, MIT-licensed, runs locally. Works with OpenRouter (free models), Anthropic Claude, OpenAI, or fully offline via Ollama.

**Who Is This For**

🔹 **Emerging market fund managers** who can't afford enterprise ESG platforms but face the same LP reporting standards

🔹 **Early-stage startups** who need guidance on which metrics matter for their sector and SDG claims

🔹 **Impact analysts** who spend days on manual DD and cross-referencing that could take minutes

🔹 **LP reporting teams** who need DDQ responses in ILPA, GIIN, EDCI, and SFDR formats from the same data

🔹 **AI/developer community** who want to build impact-aware AI agents using the MCP server or REST API

🔹 **Impact ecosystem builders** who believe measurement should be accessible, not proprietary

**The Theory of Change**

If we want capital to flow more efficiently toward impact—especially in emerging markets and for early-stage ventures—we need to make measurement accessible.

Impact Vision won't replace deep impact expertise, but it can eliminate manual cross-referencing, standardize the DD baseline, and give every fund manager the same analytical foundation that well-resourced funds take for granted.

**Try It**

The repo is live: 🔗 [github.com/joejoe168168/impact-vision](https://github.com/joejoe168168/impact-vision)

Quick start:
```
pip install -e ".[dev]"
impact-vision setup      # Configure your LLM (free models available via OpenRouter)
impact-vision            # Start the AI agent
```

Then just say: *"Analyze this pitch deck for impact: /path/to/deck.pdf"*

Or use it as an MCP tool in Claude/Cursor:
```
impact-vision serve-mcp  # All 25 tools available to your AI agent
```

Or try the CLI (no API key needed):
```
impact-vision catalog search "climate"
impact-vision dd categories
impact-vision framework scan "Solar energy company providing clean power to 50,000 rural households"
```

**What I Learned Building This**

Building this over evenings and weekends, the biggest surprise wasn't the technical challenge—it was how much domain knowledge is locked up in expensive platforms and consulting engagements. The IRIS+ catalog alone took weeks to parse properly (263 columns in the Excel file!). Cross-referencing 59 metrics across 11 frameworks required reading thousands of pages of standards documentation.

This knowledge should be open. Impact measurement shouldn't be a competitive advantage—it should be infrastructure.

**What's Next**

This is v0.6.0. The entire 10-phase roadmap (197 items) is complete. Looking ahead:
- Community-contributed sector DD question packs
- More regional benchmark data
- Integration with portfolio management systems
- Mobile-friendly dashboard
- Real-time data connectors (APIs for external data sources)

If you work in impact investing, fund management, ESG advisory, or impact measurement—I'd love your feedback. If you're a developer who cares about this space, PRs and contributions are welcome.

The standards exist. The data exists. The gap is in the tooling. Let's close it together.

---

#ImpactInvesting #OpenSource #SDG #ImpactMeasurement #ESG #IRIS #GIIN #SustainableFinance #VentureCapital #ImpactDD #ClimateFinance #DueDiligence #TheoryOfChange #AI #MCP #OpenHarness #CSRD #SFDR #Greenwashing

---

## Image Generation Prompts for LinkedIn Post

Use these prompts with an AI image generator (Midjourney, DALL-E, etc.) to create visuals for the LinkedIn post:

### 1. Hero/Banner Image
**Prompt:** "A clean, modern data visualization dashboard showing SDG goal icons (the 17 colorful squares) flowing into a radar chart and bar graphs. Professional tech style, dark blue and teal gradient background, subtle grid lines, holographic effect. Text overlay area on the left side. Aspect ratio 1200x627 (LinkedIn link preview). No text in the image."

### 2. Before/After Comparison
**Prompt:** "Split-screen infographic: Left side shows a messy desk covered in Excel spreadsheets, printed PDFs, highlighters, and sticky notes labeled 'IRIS+ Metrics', 'SDG Mapping', 'DD Checklist' in a frustrated office setting. Right side shows a sleek laptop with a clean dashboard displaying a radar chart, colorful SDG bars, and a pipeline funnel chart. Arrow in the middle with text area. Modern flat illustration style, professional colors."

### 3. Impact Measurement Framework Visualization
**Prompt:** "An elegant circular diagram showing interconnected nodes: IRIS+ (center), surrounded by orbiting circles for GRI, SASB, TCFD, SFDR, EDCI, UNPRI, ISSB, ESRS, SDGs. Lines connecting related frameworks. Dark background, glowing neon connections in teal and gold. Modern data science aesthetic. Clean, minimal, professional."

### 4. Pipeline Funnel
**Prompt:** "A stylized investment pipeline funnel illustration: companies entering at the top (sourcing), flowing through stages (screening, due diligence, IC review), with green-glowing companies emerging at the bottom as 'invested'. Each stage shows a small icon of analysis (magnifying glass, charts, checkmarks). Impact metrics floating around the funnel. Clean vector illustration, blue and green palette."

### 5. Global Impact Map
**Prompt:** "A world map visualization with glowing nodes at major impact investing hubs (London, New York, Singapore, Nairobi, Mumbai, Sao Paulo, Hong Kong). Connection lines between nodes. SDG icons floating above different regions. Data streams flowing between continents. Dark background, warm orange and teal glow. Professional data visualization style."

### 6. AI Agent Conversation
**Prompt:** "A clean mockup of a terminal/chat interface showing an AI conversation about impact assessment. The AI response shows a formatted impact report with a small radar chart, SDG alignment scores, and a greenwashing risk badge. Professional dark theme with syntax highlighting. Realistic but stylized. No actual text readable - just the visual impression of a professional tool."

### 7. Carousel Post - Feature Highlights (set of 4-5 slides)

**Slide 1 (Cover):** "Bold text design: '25 Impact Tools. Zero Cost.' with subtle SDG color gradient background. Professional, minimal, LinkedIn carousel style."

**Slide 2:** "Infographic showing the 5 Dimensions of Impact (What, Who, How Much, Contribution, Risk) as an elegant pentagon/radar shape with score indicators. Clean white background, professional blue accents."

**Slide 3:** "Visual showing 11 ESG frameworks as connected cards/tiles: IRIS+, SASB, GRI, TCFD, SFDR, EDCI, UNPRI, ISSB S1, ISSB S2, ESRS, IFC OPIM. Each with its logo mark. Dark background, organized grid layout."

**Slide 4:** "Pipeline stage visualization: 8 colored stages from sourcing to exited, with company cards at each stage, transition arrows, and alert indicators. Dashboard aesthetic."

**Slide 5 (CTA):** "Simple design with GitHub logo and text area for the repo link. 'MIT Licensed. Try it today.' Professional, minimal."
