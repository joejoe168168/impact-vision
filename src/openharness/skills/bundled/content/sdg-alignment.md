# sdg-alignment

Map investments and companies to UN Sustainable Development Goals (SDGs).

## When to use

Use when the user asks about SDG alignment, SDG mapping, or wants to understand 
how a company or investment contributes to specific Sustainable Development Goals.

## Context

The 17 UN Sustainable Development Goals (SDGs) with 169 targets provide the universal 
framework for measuring development impact. IRIS+ metrics are directly mapped to SDG 
targets, enabling evidence-based alignment scoring.

The SDG alignment score (0-100) is computed from:
- Metric coverage (60%): How many SDG-mapped IRIS+ metrics are reported
- Theme alignment (20%): Overlap between company themes and SDG-relevant themes
- Data depth (20%): Quality of metric definitions and reporting

## Workflow

1. Gather the company's reported IRIS+ metrics and claimed SDG goals
2. Use `sdg_mapper` tool to compute alignment scores per SDG
3. Review the results: focus on goals with "high" confidence first
4. Use `iris_catalog` with action "filter_sdg" to find additional metrics to strengthen weak alignments
5. Generate a report with `impact_report` for stakeholder communication

## Common SDG Mappings for VC/Impact Funds

- **SDG 1 (No Poverty)**: Microfinance, financial inclusion, affordable housing
- **SDG 3 (Good Health)**: Healthtech, telemedicine, diagnostics
- **SDG 4 (Quality Education)**: Edtech, workforce training, digital literacy
- **SDG 5 (Gender Equality)**: Gender lens investing, women-led businesses
- **SDG 7 (Clean Energy)**: Renewable energy, energy efficiency, clean cooking
- **SDG 8 (Decent Work)**: Job creation, fair wages, SME lending
- **SDG 9 (Innovation)**: Infrastructure, industrialization, technology access
- **SDG 13 (Climate Action)**: Carbon reduction, climate adaptation, resilience

## Rules

- Don't let companies claim SDG alignment without metric evidence
- Distinguish between "contribution" (causal link) and "alignment" (thematic overlap)
- SDG washing is a real risk; emphasize depth of evidence over breadth of claims
- Always show which specific targets (e.g. 1.1, 5.a) are matched, not just the goal
- Encourage companies to report metrics that strengthen their weakest claimed SDGs
