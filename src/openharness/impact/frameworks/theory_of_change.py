"""Theory of Change (ToC) framework for impact investing.

Structures impact hypotheses as causal pathways from inputs to long-term impact.
Includes RS Group's Total Portfolio Approach as a reference model, plus GIIN IRIS+
Simple ToC Checklist and standard components.

Sources:
- RS Group (rsgroup.asia): Blended Value, Total Portfolio Approach
- GIIN IRIS+ Simple Theory of Change Checklist
- Impact Management Project (IMP) framework
- NESTA Standards of Evidence
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToCComponent(BaseModel):
    """A component in the Theory of Change causal chain."""
    stage: str  # inputs, activities, outputs, outcomes, impact
    description: str = ""
    indicators: list[str] = Field(default_factory=list)
    iris_metrics: list[str] = Field(default_factory=list)
    sdg_targets: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    evidence_level: str = ""  # none, anecdotal, correlational, causal, systematic


class TheoryOfChange(BaseModel):
    """A structured Theory of Change for an investment or company."""
    name: str = ""
    problem_statement: str = ""
    target_population: str = ""
    geographic_focus: str = ""
    components: list[ToCComponent] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    risks_to_thesis: list[str] = Field(default_factory=list)
    blended_value_approach: str = ""
    impact_areas: list[str] = Field(default_factory=list)
    sdg_alignment: list[int] = Field(default_factory=list)


class ToCPrinciple(BaseModel):
    """A guiding principle for impact investing ToC."""
    name: str
    description: str
    assessment_question: str = ""
    indicators: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


# ============================================================================
# RS Group Theory of Change Framework
# Reference: rsgroup.asia, Impact Investing Institute case study
# ============================================================================

RS_GROUP_PRINCIPLES: list[ToCPrinciple] = [
    ToCPrinciple(
        name="Blended Value",
        description=(
            "Value creation is not an either/or proposition. Organizations produce "
            "economic, social, and environmental performance simultaneously. Capital "
            "rests along a continuum -- there is no trade-off between doing well and "
            "doing good, only different degrees of performance in an integrated capital market."
        ),
        assessment_question="Does the investment create blended value (financial + social/environmental) rather than treating these as trade-offs?",
        indicators=["Financial returns achieved", "Social outcomes measured", "Environmental impact tracked", "Integrated value reporting"],
        keywords=["blended value", "integrated", "financial and social", "no trade-off", "holistic"],
    ),
    ToCPrinciple(
        name="Total Portfolio Approach",
        description=(
            "Manage ALL capital under management as a single integrated portfolio. "
            "Different allocations (public equity, direct debt/equity, impact investing, "
            "strategic philanthropy) each maximize an appropriate mix of social, economic, "
            "and environmental performance. The overall intent is to manage all allocations "
            "for greatest possible impact."
        ),
        assessment_question="Is the portfolio managed holistically across all asset classes with integrated impact targets?",
        indicators=["Total assets aligned with mission %", "Impact targets across asset classes", "Unified portfolio policy statement", "Cross-allocation impact reporting"],
        keywords=["total portfolio", "all capital", "asset allocation", "integrated portfolio", "unified"],
    ),
    ToCPrinciple(
        name="Systemic Change Focus",
        description=(
            "Focus on identifying root causes of problems and investing in solutions "
            "that foster long-term systemic change, rather than just mitigating negative "
            "impacts. Build the ecosystem and infrastructure for impact, not just individual deals."
        ),
        assessment_question="Does the investment address root causes and contribute to systemic change rather than surface-level mitigation?",
        indicators=["Root cause analysis documented", "Systems-level outcomes targeted", "Field-building activities", "Policy/regulatory engagement"],
        keywords=["systemic change", "root cause", "ecosystem", "field-building", "infrastructure", "long-term"],
    ),
    ToCPrinciple(
        name="Values-Based Investing",
        description=(
            "Apply a values-based lens to all investment decisions. Set specific criteria "
            "for companies and funds to ensure alignment with mission and core values. "
            "The investment portfolio should work 'for good' across all holdings."
        ),
        assessment_question="Are investment decisions guided by explicit, documented values criteria beyond financial returns?",
        indicators=["Values-based screening criteria", "Negative screen list", "Positive inclusion criteria", "Values alignment assessment"],
        keywords=["values-based", "mission-aligned", "screen", "criteria", "for good", "values"],
    ),
    ToCPrinciple(
        name="Catalytic Capital",
        description=(
            "Use capital (both investment and philanthropic) to catalyze further "
            "investment and build the broader impact ecosystem. Provide concessionary "
            "capital where needed (design funding, subordinated debt, first-loss) to "
            "attract mainstream institutional capital to underfunded sectors."
        ),
        assessment_question="Does the capital play a catalytic role -- enabling deals or sectors that wouldn't otherwise receive investment?",
        indicators=["Leverage ratio (capital mobilized per $ invested)", "First-loss or concessionary terms", "Follow-on investment attracted", "Market-building role"],
        keywords=["catalytic", "concessionary", "first-loss", "mobiliz", "leverage", "crowd-in", "market-building"],
    ),
    ToCPrinciple(
        name="Unrestricted Funding & Capacity Building",
        description=(
            "Allocate capital to support growth and capacity building of organizations, "
            "not just specific projects. Provide flexible, unrestricted funding that "
            "enables partners to build sustainable operations and adapt to changing needs."
        ),
        assessment_question="Does the funding model support organizational capacity building, not just project-specific deliverables?",
        indicators=["% unrestricted funding", "Capacity building support", "Operating cost coverage", "Multi-year commitments"],
        keywords=["unrestricted", "capacity building", "flexible", "general operating", "organizational strength"],
    ),
    ToCPrinciple(
        name="Do, Learn, Share",
        description=(
            "Adopt an iterative approach: take action, learn from results, and share "
            "insights openly. Require investees and fund managers to report on both "
            "financial and impact performance. Use learning to improve practice across "
            "the portfolio and the broader field."
        ),
        assessment_question="Does the fund operate with a learning mindset -- tracking, adapting, and openly sharing results?",
        indicators=["Regular impact reporting", "Adaptive management practices", "Public knowledge sharing", "Community of practice participation"],
        keywords=["do learn share", "iterative", "adaptive", "learning", "reporting", "open", "transparent", "share"],
    ),
    ToCPrinciple(
        name="Active Ownership & Engagement",
        description=(
            "Engage actively with investees and fund managers on impact performance. "
            "Be willing to divest if mission drift occurs. Use board seats, reporting "
            "requirements, and dialogue to maintain impact integrity."
        ),
        assessment_question="Does the investor engage actively with portfolio companies/funds on impact performance?",
        indicators=["Board representation", "Impact reporting requirements in term sheets", "Engagement log", "Divestment criteria"],
        keywords=["active ownership", "engagement", "board seat", "stewardship", "mission drift", "divest"],
    ),
]

RS_GROUP_IMPACT_AREAS = [
    {"name": "Sustainability & Climate Change", "description": "Promoting a greener, more sustainable world", "sdgs": [7, 12, 13, 14, 15]},
    {"name": "Systemic Change in Philanthropy", "description": "Building capacity of the philanthropic sector, particularly in Asia", "sdgs": [17]},
    {"name": "Social Development", "description": "Poverty alleviation, youth education, aging, disability inclusion, mental health", "sdgs": [1, 3, 4, 10]},
    {"name": "Impact Investing Ecosystem", "description": "Supporting organizations that build the impact investing market", "sdgs": [17]},
]


# ============================================================================
# GIIN IRIS+ Simple Theory of Change Checklist
# Reference: iris.thegiin.org/theory-of-change-checklist
# ============================================================================

GIIN_TOC_CHECKLIST = [
    {"step": 1, "name": "Define the Problem", "question": "What specific social or environmental problem are you trying to address?",
     "guidance": "Be precise. Describe the root cause, not just symptoms. Quantify the problem's scale if possible."},
    {"step": 2, "name": "Identify Stakeholders", "question": "Who is affected by the problem? Who are the target beneficiaries?",
     "guidance": "Define demographics, geographic location, vulnerability status. Estimate the addressable population."},
    {"step": 3, "name": "Describe Your Entry Point", "question": "What is the specific product, service, or intervention you offer?",
     "guidance": "Focus on what is unique about your approach. How does it address the root cause?"},
    {"step": 4, "name": "Map the Pathway", "question": "What are the steps from your activities to the desired impact?",
     "guidance": "Map: Activities -> Outputs (immediate deliverables) -> Outcomes (behavior/condition changes) -> Impact (systemic change)."},
    {"step": 5, "name": "State Your Assumptions", "question": "What must be true for your pathway to work?",
     "guidance": "List critical assumptions. What external conditions, behaviors, or partnerships are needed?"},
    {"step": 6, "name": "Identify Risks", "question": "What could prevent your theory of change from working?",
     "guidance": "Consider: execution risks, market risks, stakeholder behavior, regulatory changes, unintended consequences."},
    {"step": 7, "name": "Define Metrics", "question": "How will you measure progress at each stage of the pathway?",
     "guidance": "Assign specific IRIS+ metrics or KPIs to each stage: outputs, outcomes, and impact."},
    {"step": 8, "name": "Plan for Learning", "question": "How will you use data to test and improve your theory?",
     "guidance": "Define feedback loops, reporting frequency, and decision criteria for adapting your approach."},
]


# ============================================================================
# Assessment Functions
# ============================================================================

def get_rs_group_principles() -> list[ToCPrinciple]:
    return RS_GROUP_PRINCIPLES


def get_giin_toc_checklist() -> list[dict]:
    return GIIN_TOC_CHECKLIST


def assess_toc_alignment(
    description: str = "",
    document_text: str = "",
    principles: list[ToCPrinciple] | None = None,
) -> dict:
    """Assess how well a fund/company aligns with Theory of Change principles.

    Uses RS Group principles by default but accepts custom principle sets.
    """
    if principles is None:
        principles = RS_GROUP_PRINCIPLES

    text = f"{description} {document_text}".lower()
    result = {
        "framework": "Theory of Change (RS Group Blended Value)",
        "total_principles": len(principles),
        "principles": [],
        "addressed": 0,
        "recommendations": [],
    }

    for p in principles:
        hits = [kw for kw in p.keywords if kw.lower() in text]
        addressed = len(hits) >= 2

        p_result = {
            "name": p.name,
            "addressed": addressed,
            "evidence": hits,
            "question": p.assessment_question,
        }
        result["principles"].append(p_result)

        if addressed:
            result["addressed"] += 1
        else:
            result["recommendations"].append(
                f"{p.name}: {p.assessment_question}"
            )

    result["coverage_pct"] = round(
        result["addressed"] / result["total_principles"] * 100, 1
    ) if result["total_principles"] > 0 else 0

    return result


def assess_toc_completeness(
    toc: TheoryOfChange | None = None,
    document_text: str = "",
) -> dict:
    """Assess completeness of a Theory of Change against the GIIN checklist."""
    text = document_text.lower()

    checklist_keywords = {
        1: ["problem", "challenge", "issue", "root cause", "gap"],
        2: ["stakeholder", "beneficiar", "target population", "community", "who"],
        3: ["product", "service", "intervention", "solution", "approach"],
        4: ["pathway", "output", "outcome", "activity", "logic model", "theory of change"],
        5: ["assumption", "if-then", "precondition", "must be true"],
        6: ["risk", "barrier", "challenge", "unintended", "prevent"],
        7: ["metric", "indicator", "KPI", "measure", "IRIS", "data"],
        8: ["learn", "adapt", "feedback", "improve", "iterate", "monitor"],
    }

    result = {
        "framework": "GIIN IRIS+ Theory of Change Checklist",
        "total_steps": 8,
        "steps": [],
        "addressed": 0,
    }

    for step_data in GIIN_TOC_CHECKLIST:
        step_num = step_data["step"]
        kws = checklist_keywords.get(step_num, [])
        hits = [kw for kw in kws if kw in text]
        addressed = len(hits) >= 2

        result["steps"].append({
            "step": step_num,
            "name": step_data["name"],
            "addressed": addressed,
            "evidence": hits,
            "guidance": step_data["guidance"],
        })

        if addressed:
            result["addressed"] += 1

    result["coverage_pct"] = round(result["addressed"] / 8 * 100, 1)
    return result
