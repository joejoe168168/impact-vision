# LinkedIn Launch Post - Impact Vision

*(Copy below for LinkedIn. ~2,000 words. Formatting preserved for LinkedIn.)*

---

**I've spent 8 years in impact investment. Now I'm giving the tools away for free.**

After nearly a decade in this space—evaluating deals, writing DD memos, mapping SDGs, wrestling with IRIS+ spreadsheets, and explaining to LPs why our metrics don't perfectly map to theirs—I've come to a frustrating conclusion:

The impact measurement tools we need either cost US$50-100k/year or don't exist.

I've always been enthusiastic about what AI can do. So during evenings and weekends, I built what I wish I'd had on Day 1 of my career. Today I'm open-sourcing it.

**The Problem Nobody Wants to Talk About**

Impact investing has grown to over US$1 trillion in AUM. We have 14 ESG frameworks, 787 IRIS+ metrics, 169 SDG targets, and 14 mandatory EU disclosure indicators. Yet the typical early-stage impact fund still runs their DD on Excel spreadsheets and Word documents.

I've been in that room. Probably so have you:

- A founder claims alignment with 5 SDGs but can't name a single metric they track
- Your DD analyst spends 3 days cross-referencing IRIS+ codes with GRI disclosures
- Your LP asks for EDCI-formatted data, but your system uses SFDR categories
- You know the company *could* be impactful, but the evidence is at NESTA Level 1 (anecdotal)

The enterprise platforms solve this—if you can afford them. The rest of us cobble together spreadsheets and hope we're not missing anything.

**So I Built Impact Vision**

Impact Vision is an open-source, AI-powered impact measurement and SDG alignment agent. Think of it as your impact analyst co-pilot—one that has memorized every IRIS+ metric, every SDG target, every framework cross-reference, and can run a full DD checklist in seconds.

Here's what it actually does:

📄 **Upload a pitch deck or investment memo** → It extracts impact claims, maps them to IRIS+ metrics and SDG targets, runs a 96-question DD checklist (sourced from GIIN, PCV, Seraf, IMP, AFME), scores evidence quality using NESTA levels 1-5, and suggests the most important follow-up questions. One command.

📊 **Generate visual impact reports** → HTML reports with interactive Plotly charts: 5-Dimension radar plots, SDG alignment bars in official UN colors, gap analysis trackers, and sector benchmark comparisons. Also exports to Excel, CSV, and JSON for LP reporting.

🎯 **Interactive score improvement** → The HTML report includes checkboxes for impact practices (beneficiary tracking, GHG measurement, Theory of Change, third-party audits). Check what applies to your company and watch the scores update in real-time with a before/after radar overlay. The AI agent can also ask you targeted questions to improve specific weak dimensions—and show you exactly how each answer improves your score.

🔗 **Cross-reference any metric across 6 frameworks** → "What's the GRI equivalent of IRIS+ OI4112?" → "GRI 305-1, EDCI-E1, SFDR PAI #1, TCFD MET-B, SDG 13." One lookup. Six standards.

📋 **LP DDQ generation** in ILPA, GIIN/IRIS+, EDCI, or custom formats—pulling directly from your assessment data. No more copy-paste between reporting cycles.

🏢 **Portfolio batch analysis** → Aggregated SDG coverage, 5D scoring distributions, and framework compliance across your entire portfolio.

**What's Under the Hood**

This isn't a ChatGPT wrapper with a prompt. It's a structured impact measurement engine:

- **787 IRIS+ 5.3c metrics** fully parsed, with SDG mappings, 5-Dimension tags, and smart search (synonym expansion for terms like "climate" → greenhouse gas, carbon, emissions)
- **7 ESG framework modules**: SASB (17 industries), GRI (34 standards), TCFD/IFRS S2 (4 pillars), SFDR PAI (14 mandatory indicators), EDCI (17 PE/VC metrics), UNPRI (6 principles), Theory of Change (RS Group + GIIN)
- **96 DD questions** across 24 categories—including sector-specific questions for fintech, healthcare, agriculture, energy, and education
- **Sector-aware scoring** that infers meaningful baselines from company description and sector, so even a company with zero reported metrics gets an actionable starting assessment (not just all F grades)
- **40+ cross-reference mappings** between all frameworks
- **12 LLM-callable tools** that work as an AI agent—have a natural language conversation about impact, and it knows which analyses to run
- **Interactive HTML reports** with real-time score adjustment via checkboxes

Built on HKU's OpenHarness agent framework. Python, MIT-licensed, runs locally. Works with OpenRouter (free models available), Anthropic Claude, OpenAI, or fully offline via Ollama.

**Who Is This For**

🔹 **Emerging market fund managers** who can't afford enterprise ESG platforms but are held to the same LP reporting standards

🔹 **Early-stage startups** who need guidance on which metrics matter for their sector and their SDG claims—not a 787-row Excel file

🔹 **Impact analysts** who spend days on manual DD and cross-referencing that could take minutes

🔹 **LP reporting teams** who need DDQ responses in multiple formats from the same underlying data

🔹 **Impact ecosystem builders** who believe measurement should be accessible, not proprietary

**The Theory of Change**

The impact investing ecosystem has a structural underinvestment in shared infrastructure. Every fund reinvents the same measurement workflows. Every LP reporting cycle is a manual reconciliation exercise. Every DD process starts from scratch.

If we want capital to flow more efficiently toward impact—especially in emerging markets and for early-stage ventures—we need to make measurement accessible.

Impact Vision won't replace deep impact expertise, but it can eliminate the hours of manual cross-referencing, standardize the DD baseline, and give every fund manager the same analytical foundation that well-resourced funds take for granted.

**Try It**

The repo is live: 🔗 [github.com/joejoe168168/impact-vision](https://github.com/joejoe168168/impact-vision)

Quick start:
```
pip install -e ".[dev]"
impact-vision setup      # Configure your LLM (free models available via OpenRouter)
impact-vision            # Start the AI agent
```

Then just say: *"Analyze this pitch deck for impact: /path/to/deck.pdf"*

Or try the CLI tools (no API key needed):
```
impact-vision catalog search "climate"
impact-vision dd categories
impact-vision framework scan "Solar energy company providing clean power to 50,000 rural households"
```

**What's Next**

This is v0.1.2. The roadmap includes:
- LLM-enhanced claim extraction with chain-of-thought reasoning
- Automated LP reporting pipelines
- Integration with data rooms (not just individual documents)
- Community-contributed sector DD question packs
- Multilingual support (starting with Chinese, French, Spanish)
- More interactive assessment workflows through the AI agent

If you work in impact investing, fund management, ESG advisory, or impact measurement—I'd love your feedback. If you're a developer who cares about this space, PRs and contributions are welcome.

The standards exist. The data exists. The gap is in the tooling. Let's close it together.

---

#ImpactInvesting #OpenSource #SDG #ImpactMeasurement #ESG #IRIS #GIIN #SustainableFinance #VentureCapital #ImpactDD #ClimateFinance #DueDiligence #TheoryOfChange #AI #OpenHarness
