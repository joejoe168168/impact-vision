# theory-of-change

Guide for developing and assessing Theory of Change (ToC) for impact investments.
Incorporates RS Group's Blended Value framework and GIIN IRIS+ ToC Checklist.

## When to use

Use when the user wants to develop, evaluate, or refine a Theory of Change for an
investment, company, or fund. Also use when assessing whether an impact thesis is
robust and evidence-based.

## Context

A Theory of Change is a causal pathway that explains how and why an intervention
leads to desired impact. For impact investing, it connects investment capital to
social/environmental outcomes through a chain of activities, outputs, outcomes,
and impact.

## RS Group's Blended Value Framework

RS Group (Hong Kong) operates on the premise that capital should be used to improve
the world. Their approach rejects the "either/or" between financial returns and
impact, instead embracing "blended value":

### 8 Core Principles

1. **Blended Value**: No trade-off between doing well and doing good -- only different
   degrees of performance in an integrated capital market
2. **Total Portfolio Approach**: Manage ALL capital as a single integrated portfolio
   across public equity, direct equity, impact investing, and philanthropy
3. **Systemic Change**: Address root causes, not just symptoms. Build ecosystems.
4. **Values-Based Investing**: Apply explicit values criteria to every investment decision
5. **Catalytic Capital**: Use concessionary terms to crowd-in mainstream capital
6. **Unrestricted Funding**: Support organizational capacity, not just project deliverables
7. **Do, Learn, Share**: Iterate, track, adapt, and openly share learnings
8. **Active Ownership**: Engage with investees on impact; divest if mission drift occurs

### RS Group Impact Areas
- Sustainability & Climate Change (SDGs 7, 12, 13, 14, 15)
- Systemic Change in Philanthropy (SDG 17)
- Social Development: poverty, education, aging, disability, mental health (SDGs 1, 3, 4, 10)
- Impact Investing Ecosystem building (SDG 17)

## GIIN IRIS+ Theory of Change Checklist

8-step process for developing a robust ToC:
1. Define the Problem
2. Identify Stakeholders
3. Describe Your Entry Point
4. Map the Pathway (Activities -> Outputs -> Outcomes -> Impact)
5. State Your Assumptions
6. Identify Risks
7. Define Metrics (using IRIS+)
8. Plan for Learning

## Workflow

1. Use `framework_assess` with framework='toc' and action='list' to show all principles
2. Use `framework_assess` with framework='toc' and action='assess' to evaluate a company's
   ToC against both RS Group principles and GIIN checklist
3. Present gaps and recommendations
4. Help the user develop missing elements

## Rules

- Always assess both the RS Group principles AND the GIIN checklist
- Distinguish between activities, outputs, outcomes, and impact in the causal chain
- Challenge assumptions explicitly -- the ToC is only as strong as its weakest assumption
- Recommend specific IRIS+ metrics for each stage of the ToC
- Be constructive: help build better ToCs, not just critique them
- A good ToC explains WHY the pathway works, not just WHAT the steps are
