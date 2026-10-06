# Glossary

Plain-language definitions of the terms Impact Vision uses in its reports.
Generated from `data/glossary.yaml` by `scripts/build_glossary.py` — edit the
YAML, not this file.

## Evidence

**Impact claim** — A statement in a pitch deck or report about the change a company creates ("we connected 42,000 households"). Impact Vision extracts each claim, maps it to a metric where possible and grades how well it is evidenced.

**NESTA standards of evidence** — A five-level scale for how strong evidence of impact is: 1 = a narrative, 2 = data showing change, 3 = a comparison or control group suggesting the company caused it, 4-5 = independent or replicated rigorous evaluations.

**Third-party verification** — An independent organisation (auditor, certifier, regulator) has checked a figure or practice. It raises confidence in a claim and lowers greenwashing risk.

**Lean Data** — Short, low-cost surveys of a company's customers or beneficiaries, usually by phone or SMS (approach popularised by 60 Decibels), to hear directly whether their lives changed.

## Metrics

**IRIS+** — The Global Impact Investing Network's catalogue of standard impact metrics (about 790 in version 5.3c), each with a short ID such as OI2764 for "Greenhouse Gas Emissions Avoided". Using the same IDs makes results comparable across companies and funds.

**Core metric set** — The short list of IRIS+ metrics a company in a given sector should report. Coverage is the share of that list the company reports; Impact Vision picks the list by sector.

## Scoring

**Five Dimensions of Impact (5D)** — The Impact Management Project's framework for describing impact: What outcome occurs, Who experiences it, How Much change (scale, depth, duration), the investor's and company's Contribution compared with what would have happened anyway, and the Risk that impact doesn't happen. Impact Vision scores each dimension from 1 to 5.

**Evidence-based / partial / estimated** — How a score was derived. Evidence-based scores rest on several reported metrics; partial scores on a few; estimated scores only on the text of the documents. Treat estimated scores as a starting hypothesis, not a finding.

**SDG alignment** — How strongly the company's activities and metrics relate to each of the 17 UN Sustainable Development Goals (0-100). A goal is "material" when the company claims it, its business clearly relates to it, or it reports a goal-specific metric; other goals are context only.

**Additionality** — Whether the outcome would have happened anyway without the company or investor. Strong additionality means the impact depends on them.

## Risk

**Greenwashing (impact-washing) risk** — A 0-100 score of how far a company's claims run ahead of its evidence: vague language, claims without metrics, missing negative impacts, selective reporting and no verification. Below 60 it mostly reflects missing data; at 60 or above it is a finding in itself.

## Process

**Due diligence (DD) coverage** — The share of the impact due-diligence questions (universal plus the company's sector) that the documents already answer. Low coverage means more questions to ask, not a bad company.

**IC gate** — The fund's minimum thresholds before a deal goes to the investment committee (5D score, top SDG score, DD coverage, greenwashing risk, exclusions). "Insufficient evidence" means the failures are missing data; "Fail" means a negative finding.

**Theory of change** — The chain from what a company does (activities) to what it produces (outputs) to the changes people or the planet experience (outcomes), with the assumptions that must hold along the way.

## Climate

**Scope 1, 2 and 3 emissions** — Greenhouse-gas emissions from a company's own operations (Scope 1), from the energy it buys (Scope 2) and from its value chain (Scope 3), as defined by the GHG Protocol.

**tCO2e** — Tonnes of carbon-dioxide equivalent: a common unit that converts all greenhouse gases to the warming effect of CO2.

## Regulation

**SFDR (Article 6 / 8 / 9)** — The EU Sustainable Finance Disclosure Regulation. Article 8 funds promote environmental or social characteristics; Article 9 funds have sustainable investment as their objective. A recast ("SFDR 2.0") with product categories is being negotiated for application around 2029; only Transition or Sustainable products with a measurable impact objective and a theory of change may use the word "impact".

**ESRS / CSRD / VSME** — The EU sustainability reporting rules (CSRD) and their standards (ESRS). The revised ESRS became law in September 2026 and apply from 2027. VSME is the voluntary standard for smaller companies; from 2027 large reporters may not ask partners with up to 1,000 employees for more than VSME data.

**ISSB (IFRS S1 / S2)** — The International Sustainability Standards Board's global disclosure standards: S1 for general sustainability information, S2 for climate. Adopted or being adopted in Hong Kong, Singapore, Japan, Australia, the UK and elsewhere.

## Standards

**OPIM** — The Operating Principles for Impact Management: nine principles for how an investor manages impact across the deal cycle, independently verified (for example by BlueMark).

## Using Impact Vision

**Assessment ID** — The number assess_deal returns for a saved assessment. Pass it to other tools (impact_report, sdg_mapper, greenwashing_detect, ...) instead of re-typing the company's details.
