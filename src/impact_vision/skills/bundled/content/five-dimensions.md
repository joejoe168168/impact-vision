# five-dimensions

Assess impact using the 5 Dimensions of Impact framework (What/Who/How Much/Contribution/Risk).

## When to use

Use when conducting impact due diligence, assessing a company's impact depth, 
or when the user needs to evaluate impact quality beyond simple metric counts.

## Context

The 5 Dimensions of Impact (developed by the Impact Management Project, adopted by GIIN) 
provide the most comprehensive framework for understanding impact:

1. **WHAT**: What outcome occurs? Is it positive or negative? How important is it to stakeholders?
2. **WHO**: Who experiences the outcome? Are they underserved? What is their geography/demographics?
3. **HOW MUCH**: 
   - Scale: How many stakeholders are affected?
   - Depth: How significant is the change for each?
   - Duration: How long does the outcome last?
4. **CONTRIBUTION**: Would the outcome have happened anyway? What is the enterprise's additionality?
5. **RISK**: What is the risk that impact does not occur as expected? (Evidence risk, execution risk, external risk)

Each dimension is scored 0-5 based on reported IRIS+ metrics coverage.

## Workflow

1. Collect the company's reported metrics (IRIS+ IDs and values)
2. Use `five_dimension_assess` tool to score across all 5 dimensions
3. Review gaps: which dimensions score lowest?
4. Use `iris_catalog` with "filter_dimension" to find metrics that address gaps
5. Provide recommendations to improve weak dimensions

## Scoring Guide

- **5.0 (A)**: Comprehensive evidence, well-documented metrics, clear outcomes
- **4.0 (B+)**: Strong coverage with minor gaps
- **3.0 (B)**: Adequate coverage, some important metrics missing
- **2.0 (C+)**: Basic coverage, significant gaps in evidence
- **1.0 (D)**: Minimal evidence, major dimensions unaddressed
- **0.0 (F)**: No relevant metrics reported

## Rules

- Contribution is the hardest dimension to score; few companies have counterfactual data
- Risk assessment should consider evidence quality, not just the company's claims
- "How Much" combines three sub-dimensions (Scale, Depth, Duration); weight them equally
- A company scoring well on What/Who but poorly on How Much may have good intentions but weak evidence
- Always recommend at least one action per weak dimension
