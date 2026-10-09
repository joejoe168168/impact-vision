# impact-dd-guide

Guide for conducting impact due diligence on startups and investment opportunities.

## When to use

Use when the user wants to conduct a full impact assessment for an investment decision,
analyze a pitch deck for impact claims, or prepare an impact DD memo.

## Context

Impact due diligence evaluates whether an investment will generate positive, measurable 
social and environmental outcomes alongside financial returns. This is critical for:
- Impact/VC funds making investment decisions
- LP reporting on portfolio impact
- Startups seeking to demonstrate their impact thesis

The DD checklist is based on frameworks from GIIN, Pacific Community Ventures, Seraf, IMP,
and AFME ESG frameworks. It covers 71 questions across 19 categories covering the 5 Dimensions
of Impact plus financial sustainability, team capability, market context, product design,
supply chain, stakeholder voice, and investor alignment.

## Workflow

### Phase 1: Document Intake
1. When a user provides a pitch deck or investment memo PDF, use `pitch_deck_analyze` immediately
2. This tool does everything in one pass:
   - Extracts text from all pages
   - Identifies and classifies impact claims (outcome/output/activity/intent/risk)
   - Maps claims to relevant IRIS+ metric IDs
   - Detects SDG goal alignment from content
   - Runs the DD checklist to find which questions are addressed vs. gaps
   - Suggests the most important follow-up questions
3. Present the results to the user with a clear summary

### Phase 2: DD Question Triage
4. Review the DD checklist gaps identified by pitch_deck_analyze
5. Use `dd_checklist` with action='suggest' if you need more targeted questions
6. Present unanswered high-priority questions to the user:
   - Group by category (Theory of Change, Stakeholders, Risk, etc.)
   - Mark priority levels (!!!=high, !!=medium)
   - Ask the user to answer what they can or flag items for the investment team
7. As the user provides answers, use them to refine the assessment

### Phase 3: Deep Assessment
8. Use `sdg_mapper` to score SDG alignment with any new data
9. Use `five_dimension_assess` for structured 5-Dimension scoring
10. Use `gap_analysis` to identify metric reporting gaps
11. Use `iris_catalog` to suggest specific metrics the company should track

### Phase 4: Reporting
12. Use `impact_report` to generate a formal assessment report
13. Include: 5D scores, SDG alignment, DD gaps, metric recommendations
14. Flag any impact washing concerns or unsupported claims

## DD Checklist Categories (19 categories, 71 questions)

### Five Dimensions of Impact
- **Impact Thesis & Theory of Change**: Core mission, ToC, business model alignment
- **What (Outcomes)**: Specific outcomes vs. outputs, positive/negative impacts
- **Who (Stakeholders)**: Target beneficiaries, underserved status, baseline
- **How Much (Scale)**: Reach, depth of change, duration, growth plans
- **Contribution**: Additionality, counterfactual, evidence
- **Risk**: Evidence risk, execution risk, external risk, mitigation, impact washing

### Impact Infrastructure
- **Measurement Systems**: IMM systems, IRIS+ alignment, data frequency, audits
- **Governance/ESG**: Board oversight, environmental/labor/ethics policies
- **SDG Alignment**: Specific goals and targets, not just claims
- **Negative Impact**: Do-no-harm assessment, grievance mechanisms

### Business Viability
- **Financial Sustainability**: Revenue model, impact-return tension, grants dependency
- **Team & Capability**: Founder experience, community ties, key person risk
- **Market & Context**: Market size, regulation, systemic barriers, competition
- **Product/Service Design**: User-centered design, safety, privacy, affordability

### Operational & Stakeholder
- **Supply Chain**: ESG practices, forced/child labor risk, footprint
- **Stakeholder Voice**: Feedback mechanisms, co-design, transparency
- **Exit Sustainability**: Impact continuity, mission lock, acquirer risk
- **Investor Alignment**: Impact covenants, value-add, portfolio fit

## Red Flags in Impact DD

- Claims of impact across 5+ SDGs without specific metrics
- No outcome metrics, only activity/output metrics
- No target beneficiary definition (the WHO)
- Avoidance of risk discussion
- Confusion between financial metrics and impact metrics
- Claims not supported by the business model

## Green Flags

- Specific, measurable outcome metrics
- Clear theory of change linking activities to outcomes
- Defined target stakeholders with demographic data
- Honest risk assessment with mitigation plans
- Third-party validation or industry benchmarks

## Rules

- Always start with `pitch_deck_analyze` when a document is provided
- Present DD questions conversationally, not as a dump of 40 questions
- Prioritize the 5-10 most critical unanswered questions
- Always distinguish between impact intent, outputs, outcomes, and evidence
- Be constructive: help companies improve their impact measurement, not just criticize
- Use IRIS+ metric IDs as the standard language for metric recommendations
- Consider materiality: focus on the 3-5 most relevant metrics, not all 787
- Generate actionable recommendations, not just scores
