# LinkedIn Launch Post - Impact Vision

*(Copy below for LinkedIn. ~1,800 words. Formatting preserved for LinkedIn.)*

---

**The Impact Measurement Problem Nobody Wants to Talk About**

I was sitting in a due diligence call last week when the founder said something that stopped me cold: "We align with SDG 1, 3, 5, 8, and 10." Five goals. A 12-person startup. And not a single metric to back it up.

Here's the thing—they weren't trying to greenwash. They genuinely believed in their mission. They just didn't have the tools. And honestly? Neither did we.

That's the dirty secret of impact investing: we have 14 different ESG frameworks, 787 IRIS+ metrics, 169 SDG targets, and 14 mandatory EU disclosure indicators—and almost no free, open-source tools to actually use them. The industry is drowning in standards and starving for infrastructure.

**The Scale of the Gap**

If you're an impact fund manager today, here's what your "toolbox" looks like:

- GIIN's IRIS+ catalog: 787 metrics across 263 columns in an Excel spreadsheet. Free, comprehensive, essential—and nearly impossible to work with manually.
- SASB: 77 materiality topics across 17 industries. Different taxonomy, different naming.
- GRI: 34 standards, 120+ disclosures. Yet another mapping system.
- SFDR PAI: 14 mandatory indicators for EU compliance. Required by law, reported in yet another format.
- EDCI: 17 core PE/VC metrics. Overlaps with some of the above, but with its own codes.
- TCFD/IFRS S2: 11 climate disclosures across 4 pillars. Critical for climate-focused funds.
- UNPRI: 6 principles, 27 action items. Self-assessment with no standardised scoring.

And every LP wants their DDQ in a slightly different format.

The funds that can afford it pay US$50-100k/year for proprietary platforms. The rest? They cobble together Excel spreadsheets, hope they're not missing anything, and lose countless hours on manual cross-referencing.

**Why This Matters**

This isn't just an operational headache. It's a market failure that actively harms the impact ecosystem:

🔹 **Early-stage startups** rarely have ESG teams. They need guidance on *which* metrics matter for *their* sector and *their* SDG claims. Instead, they get a 787-row Excel file.

🔹 **Emerging market fund managers** can't afford enterprise ESG platforms but are held to the same LP reporting standards as billion-dollar funds.

🔹 **Impact claims go unverified** because there's no scalable way to cross-check a pitch deck against a DD checklist, score evidence quality, or compare against sector benchmarks.

🔹 **LP DDQ responses** are copy-pasted between funds, often using outdated data, because nobody has automated the data pipeline from assessment to disclosure.

**So We Built Something About It**

Today I'm open-sourcing **Impact Vision**—an AI-powered impact measurement and SDG alignment engine, purpose-built for VC and impact investment funds.

It's built on HKU's OpenHarness agent framework (shoutout to the team for creating such a clean, extensible agent infrastructure) and uses GIIN's IRIS+ 5.3c as the foundational standard.

What it does:

📄 **Upload a pitch deck** → Impact Vision extracts claims, maps them to IRIS+ metrics and SDG targets, runs a 96-question DD checklist, scores evidence quality (NESTA levels 1-5), identifies gaps, and suggests follow-up questions. Automatically.

📊 **Generate reports** with Plotly radar charts for the 5 Dimensions of Impact, SDG alignment bars with official UN colors, gap analysis coverage trackers, and sector benchmark comparisons. In HTML, Excel, CSV, or plain text.

🔗 **Cross-reference any metric** across 6 frameworks instantly. "What's the GRI equivalent of IRIS+ OI4112?" → "GRI 305-1 (GHG Emissions - Scope 1), also mapped to EDCI-E1, SFDR PAI #1, TCFD MET-B, SDG 13." One lookup. Six standards.

📋 **LP DDQ generation** in ILPA, GIIN/IRIS+, EDCI, or custom formats—pulling directly from your assessment data. No more copy-paste.

🏢 **Portfolio batch analysis** with aggregated SDG coverage, 5-Dimension scoring, and grade distributions across your entire portfolio.

**What's Under the Hood**

This isn't a wrapper around ChatGPT. It's a structured impact measurement engine with:

- **787 IRIS+ metrics** fully parsed from the official 263-column catalog, with SDG mappings, 5-Dimension tags, and stakeholder classifications
- **7 ESG framework modules**: SASB, GRI, TCFD/IFRS S2, SFDR PAI, EDCI, UNPRI, and Theory of Change (incorporating RS Group's Blended Value approach)
- **96 DD questions** across 24 categories—including sector-specific questions for fintech, healthcare, agriculture, energy, and education—sourced from GIIN, PCV, Seraf, IMP, and AFME
- **NESTA Standards of Evidence** scoring (1-5 scale) that automatically assesses whether claims are backed by narrative, output data, outcome measurement, controlled comparison, or rigorous evaluation
- **40+ cross-reference mappings** between IRIS+, GRI, EDCI, SFDR PAI, SASB, and TCFD
- **Sector benchmarks** for 8 industries from GIIN survey data
- **12 LLM-callable tools** that work together as an AI agent—you can have a conversation about impact assessment, and the agent knows which tools to invoke

All of it is Python, MIT-licensed, and runs locally. You can plug in Anthropic Claude, OpenAI, or spin up Ollama with a single CLI command for fully local, private assessment.

**The Theory of Change for Open-Source Impact Infrastructure**

I believe the impact investing ecosystem has a structural underinvestment in shared infrastructure. Every fund reinvents the same measurement workflows. Every LP reporting cycle is a manual reconciliation exercise. Every DD process starts from scratch.

If we want capital to flow more efficiently toward impact—especially in emerging markets and for early-stage ventures—we need to make measurement accessible, not proprietary.

Impact Vision is one step in that direction. It won't replace deep impact expertise, but it can eliminate the hours of manual cross-referencing, standardize the DD baseline, and give emerging fund managers the same analytical foundation that well-resourced funds take for granted.

**Try It**

The repo is live:

🔗 [GitHub - Impact Vision] (link)

Quick start:
```
pip install -e .
impact-vision catalog load
impact-vision
```

Then just say: "Analyze this pitch deck for impact: /path/to/deck.pdf"

Or try the visual dashboard: `streamlit run src/openharness/dashboard/app.py`

**What's Next**

This is v0.1. The roadmap includes:
- LLM-enhanced claim extraction with chain-of-thought reasoning
- Automated LP reporting pipelines
- Integration with data rooms (not just individual documents)
- Community-contributed sector DD question packs
- Multilingual support (starting with Chinese, French, Spanish)

If you work in impact investing, fund management, ESG advisory, or impact measurement—I'd love your feedback. If you're a developer who cares about this space, PRs are welcome.

The standards exist. The data exists. The gap is in the tooling. Let's close it.

---

#ImpactInvesting #OpenSource #SDG #ImpactMeasurement #ESG #IRIS #GIIN #SustainableFinance #VentureCapital #ImpactDD #ClimateFinance #DueDiligence #TheoryOfChange #OpenHarness #HKU
