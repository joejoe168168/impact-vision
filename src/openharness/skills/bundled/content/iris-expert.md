# iris-expert

Deep knowledge of GIIN's IRIS+ 5.3c Catalog of Metrics for impact measurement.

## When to use

Use when the user asks about IRIS+ metrics, metric definitions, reporting formats, 
or needs help choosing the right metrics for their impact measurement framework.

## Context

The IRIS+ system is the generally accepted system for measuring, managing, and optimizing 
impact. It provides a catalog of ~787 standardized metrics organized by:
- **Impact Categories**: Financial Services, Food & Agriculture, Health, Education, etc.
- **Impact Themes**: 44+ themes like Financial Inclusion, Clean Energy, Affordable Housing
- **Sections**: Product Impact, Operational Impact, Financial Performance
- **Metric Types**: Metrics and Sub-metrics with specific reporting formats

Each metric has: ID, Name, Definition, Calculation guidance, Usage guidance, SDG mappings, 
and 5-Dimension tags.

## Workflow

1. Use `iris_catalog` tool with action "search" to find relevant metrics by keyword
2. Use action "get" with a specific metric ID to retrieve full details
3. Use action "filter_sdg" to find metrics aligned with specific SDG goals
4. Use action "filter_theme" to browse metrics by impact theme
5. Use action "stats" to get an overview of the catalog

## Key Metric IDs to Know

- **PI4060**: Clients: Total (core metric for all organizations)
- **PI9468**: Revenue (financial performance baseline)
- **OI6024**: Direct Employees: Total
- **PI5957**: Greenhouse Gas Emissions: Total
- **PI1349**: Direct Beneficiaries: Total
- **OI4112**: Social and Environmental Objectives
- **PI2088**: Client Individuals: Female (gender lens)
- **PI2740**: Client Individuals: Living in Poverty

## Rules

- Always cite specific IRIS+ metric IDs when recommending metrics
- Explain the metric definition and why it's relevant to the user's context
- Suggest Core Metric Sets before theme-specific metrics
- Reference SDG alignments when discussing metric relevance
- Use the 5 Dimensions of Impact framework to guide metric selection
