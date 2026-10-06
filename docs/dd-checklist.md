# Impact DD checklist

The built-in due diligence checklist includes **122 questions** across **34 categories**, sourced from:

- **GIIN Impact Toolkit** - The Impact Due Diligence Guide
- **Pacific Community Ventures** - Impact DD Emerging Best Practices
- **Seraf Toolbox** - Impact Investing Due Diligence Checklist
- **Impact Management Project (IMP)** - Five Dimensions of Impact
- **AFME / Neotas / OECD** - ESG Due Diligence frameworks
- **Sector-specific**: 15 sectors including fintech, healthcare, agriculture, energy, education, manufacturing, transport, construction, tourism, retail, mining, media, professional services, waste management, and ICT

Each addressed question is assessed using **NESTA Standards of Evidence**,
from level 1 (narrative/anecdotal only) through level 3 (measured outcome
data) to level 5 (rigorous evaluation — RCT, independent audit, causal
attribution).

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

## Sector filtering

Since v7 (Wave 0), DD coverage runs the universal questions plus only the
company's own sector set. `sector="auto"` (the default in the SDK, CLI and
`assess`) infers the sector from the document; pass `--sector all` /
`sector=None` to run every sector's questions.
