"""ISSB IFRS S1 — General Requirements for Disclosure of Sustainability-related Financial Information.

IFRS S1 requires entities to disclose information about sustainability-related
risks and opportunities that could reasonably be expected to affect cash flows,
access to finance, or cost of capital over the short, medium, or long term.

Effective 1 January 2024 for early adopters; many jurisdictions mandating from 2025-2027.

Reference: https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/ifrs-s1-general-requirements/
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ISSBS1Disclosure(BaseModel):
    """A specific IFRS S1 disclosure requirement."""
    code: str
    name: str
    paragraph_ref: str = ""
    guidance: str = ""
    iris_cross_refs: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)


class ISSBS1Pillar(BaseModel):
    """One of the 4 core content pillars of IFRS S1."""
    name: str
    description: str = ""
    disclosures: list[ISSBS1Disclosure] = Field(default_factory=list)


class ISSBS1Framework(BaseModel):
    """The full IFRS S1 framework structure."""
    name: str = "ISSB IFRS S1 — General Requirements for Sustainability-related Financial Information"
    version: str = "Effective 2024-01-01"
    pillars: list[ISSBS1Pillar] = Field(default_factory=list)


IFRS_S1 = ISSBS1Framework(pillars=[
    ISSBS1Pillar(
        name="Governance",
        description="Governance processes, controls, and procedures used to monitor and manage sustainability-related risks and opportunities",
        disclosures=[
            ISSBS1Disclosure(
                code="S1-GOV-1",
                name="Governance body oversight",
                paragraph_ref="26-27",
                guidance="Identify governance body(ies) responsible for sustainability oversight and describe their responsibilities",
                data_requirements=[
                    "Governance body/committee responsible",
                    "How responsibilities are reflected in terms of reference or mandates",
                    "Competencies and skills relevant to sustainability",
                    "Frequency of sustainability-related discussions",
                ],
            ),
            ISSBS1Disclosure(
                code="S1-GOV-2",
                name="Management's role",
                paragraph_ref="28",
                guidance="Describe management's role in assessing and managing sustainability-related risks and opportunities",
                data_requirements=[
                    "Management positions or committees responsible",
                    "Controls and procedures for risk oversight",
                    "Integration with other internal functions",
                ],
            ),
        ],
    ),
    ISSBS1Pillar(
        name="Strategy",
        description="Strategy for managing sustainability-related risks and opportunities",
        disclosures=[
            ISSBS1Disclosure(
                code="S1-STR-1",
                name="Sustainability-related risks and opportunities",
                paragraph_ref="30-31",
                guidance="Describe sustainability risks and opportunities that could affect prospects",
                data_requirements=[
                    "Description of risks and opportunities",
                    "Time horizons: short, medium, long term",
                    "Whether concentrated or dispersed across value chain",
                ],
            ),
            ISSBS1Disclosure(
                code="S1-STR-2",
                name="Business model and value chain",
                paragraph_ref="32-33",
                guidance="Describe current and anticipated effects on business model and value chain",
                data_requirements=[
                    "Effects on business model and value chain",
                    "Where risks/opportunities are in the value chain",
                    "How strategy addresses sustainability risks/opportunities",
                ],
            ),
            ISSBS1Disclosure(
                code="S1-STR-3",
                name="Strategy and decision-making",
                paragraph_ref="34-35",
                guidance="Describe how sustainability risks and opportunities affect strategy and decision-making",
                data_requirements=[
                    "How entity responds to sustainability risks/opportunities",
                    "Plans and resource allocation",
                    "Progress against previous plans",
                ],
            ),
            ISSBS1Disclosure(
                code="S1-STR-4",
                name="Financial position, performance, and cash flows",
                paragraph_ref="36-40",
                guidance="Describe effects on financial position, performance, and cash flows",
                data_requirements=[
                    "Current financial effects (quantitative where possible)",
                    "Anticipated financial effects over short/medium/long term",
                    "Assumptions and judgments used",
                ],
            ),
            ISSBS1Disclosure(
                code="S1-STR-5",
                name="Resilience of strategy",
                paragraph_ref="41-42",
                guidance="Describe the resilience of strategy to sustainability-related risks",
                data_requirements=[
                    "Assessment of resilience",
                    "Scenario analysis if appropriate",
                    "Capacity to adjust or adapt",
                ],
            ),
        ],
    ),
    ISSBS1Pillar(
        name="Risk Management",
        description="Processes used to identify, assess, prioritize, and monitor sustainability-related risks and opportunities",
        disclosures=[
            ISSBS1Disclosure(
                code="S1-RM-1",
                name="Processes to identify and assess",
                paragraph_ref="43-44",
                guidance="Describe processes to identify and assess sustainability-related risks and opportunities",
                data_requirements=[
                    "Inputs and parameters used",
                    "How likelihood and magnitude are assessed",
                    "Whether and how processes have changed from prior period",
                    "How risks are prioritized",
                ],
            ),
            ISSBS1Disclosure(
                code="S1-RM-2",
                name="Processes to monitor, manage, and mitigate",
                paragraph_ref="45",
                guidance="Describe processes to monitor, manage, and mitigate sustainability risks",
                data_requirements=[
                    "Policies and actions taken",
                    "How effectiveness of actions is monitored",
                ],
            ),
            ISSBS1Disclosure(
                code="S1-RM-3",
                name="Integration with overall risk management",
                paragraph_ref="46-47",
                guidance="Describe how sustainability risk management is integrated into overall risk management",
                data_requirements=[
                    "Integration with enterprise risk management",
                    "Whether dedicated sustainability risk function exists",
                ],
            ),
        ],
    ),
    ISSBS1Pillar(
        name="Metrics and Targets",
        description="Metrics and targets used to measure, monitor, and manage sustainability-related risks and opportunities",
        disclosures=[
            ISSBS1Disclosure(
                code="S1-MT-1",
                name="Metrics used",
                paragraph_ref="48-51",
                guidance="Disclose metrics used to measure and monitor sustainability-related risks and opportunities",
                data_requirements=[
                    "Metrics required by applicable IFRS Sustainability Disclosure Standards",
                    "Metrics used to measure performance against targets",
                    "Industry-based metrics (SASB reference)",
                ],
                iris_cross_refs=["OI4112", "OI1479", "PI4060", "OI9803"],
            ),
            ISSBS1Disclosure(
                code="S1-MT-2",
                name="Targets set",
                paragraph_ref="52-53",
                guidance="Disclose targets set to monitor progress toward sustainability objectives",
                data_requirements=[
                    "Metric used to set the target",
                    "Whether target is absolute or intensity-based",
                    "Time period over which the target applies",
                    "Base period from which progress is measured",
                    "Milestones and interim targets",
                    "Performance against each target and analysis of trends",
                ],
            ),
        ],
    ),
])


def get_ifrs_s1_framework() -> ISSBS1Framework:
    return IFRS_S1


def assess_ifrs_s1_readiness(
    description: str = "",
    governance_info: str = "",
    reported_metrics: dict[str, str] | None = None,
    targets_set: bool = False,
    risk_process_described: bool = False,
) -> dict:
    """Quick readiness check against IFRS S1 requirements.

    Returns a readiness score (0-100) and per-pillar status.
    """
    desc = f"{description} {governance_info}".lower()
    reported = reported_metrics or {}

    pillar_scores: dict[str, dict] = {}

    gov_score = 0
    if any(w in desc for w in ("board", "committee", "oversight", "governance")):
        gov_score += 40
    if any(w in desc for w in ("management", "ceo", "cfo", "chief", "officer")):
        gov_score += 30
    if any(w in desc for w in ("sustainability", "esg", "climate", "impact")):
        gov_score += 30
    pillar_scores["governance"] = {"score": min(gov_score, 100), "status": "addressed" if gov_score >= 50 else "gaps"}

    str_score = 0
    if any(w in desc for w in ("risk", "opportunity", "threat")):
        str_score += 25
    if any(w in desc for w in ("strategy", "plan", "business model")):
        str_score += 25
    if any(w in desc for w in ("value chain", "supply chain", "stakeholder")):
        str_score += 25
    if any(w in desc for w in ("financial", "revenue", "cost", "cash flow")):
        str_score += 25
    pillar_scores["strategy"] = {"score": min(str_score, 100), "status": "addressed" if str_score >= 50 else "gaps"}

    rm_score = 0
    if risk_process_described:
        rm_score += 50
    if any(w in desc for w in ("risk management", "risk assessment", "risk framework")):
        rm_score += 30
    if any(w in desc for w in ("monitor", "mitigate", "control")):
        rm_score += 20
    pillar_scores["risk_management"] = {"score": min(rm_score, 100), "status": "addressed" if rm_score >= 50 else "gaps"}

    mt_score = 0
    if reported:
        mt_score += min(50, len(reported) * 10)
    if targets_set:
        mt_score += 30
    if any(w in desc for w in ("metric", "kpi", "indicator", "measurement", "baseline")):
        mt_score += 20
    pillar_scores["metrics_and_targets"] = {"score": min(mt_score, 100), "status": "addressed" if mt_score >= 50 else "gaps"}

    overall = round(sum(p["score"] for p in pillar_scores.values()) / 4, 1)

    recommendations = []
    if pillar_scores["governance"]["score"] < 50:
        recommendations.append("Describe board/committee oversight of sustainability topics")
    if pillar_scores["strategy"]["score"] < 50:
        recommendations.append("Document how sustainability risks and opportunities affect business strategy")
    if pillar_scores["risk_management"]["score"] < 50:
        recommendations.append("Describe the process for identifying and managing sustainability risks")
    if pillar_scores["metrics_and_targets"]["score"] < 50:
        recommendations.append("Report IRIS+ metrics and set measurable sustainability targets")

    return {
        "framework": "IFRS S1",
        "overall_readiness": overall,
        "pillar_scores": pillar_scores,
        "total_disclosures": sum(len(p.disclosures) for p in IFRS_S1.pillars),
        "recommendations": recommendations,
    }
