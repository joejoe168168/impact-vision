"""ISSB IFRS S2 — Climate-related Disclosures.

IFRS S2 requires entities to disclose information about climate-related
risks and opportunities. It subsumes and extends the TCFD recommendations,
adding industry-specific metrics based on SASB standards.

Effective 1 January 2024 for early adopters; mandated in many jurisdictions from 2025-2027.

Reference: https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/ifrs-s2-climate-related-disclosures/
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ISSBS2Disclosure(BaseModel):
    code: str
    name: str
    paragraph_ref: str = ""
    guidance: str = ""
    tcfd_equivalent: str = ""
    iris_cross_refs: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)


class ISSBS2Pillar(BaseModel):
    name: str
    description: str = ""
    disclosures: list[ISSBS2Disclosure] = Field(default_factory=list)


class ISSBS2Framework(BaseModel):
    name: str = "ISSB IFRS S2 — Climate-related Disclosures"
    version: str = "2023"
    pillars: list[ISSBS2Pillar] = Field(default_factory=list)


IFRS_S2 = ISSBS2Framework(
    pillars=[
        ISSBS2Pillar(
            name="Governance",
            description="Governance processes, controls and procedures used to monitor, manage and oversee climate-related risks and opportunities.",
            disclosures=[
                ISSBS2Disclosure(
                    code="S2-GOV-1",
                    name="Governance body oversight",
                    paragraph_ref="S2.5-6",
                    guidance="Identify governance body(ies) responsible for oversight of climate-related risks and opportunities.",
                    tcfd_equivalent="TCFD Governance a)",
                    data_requirements=["Board/committee with climate oversight", "Frequency of climate briefings"],
                ),
                ISSBS2Disclosure(
                    code="S2-GOV-2",
                    name="Management's role",
                    paragraph_ref="S2.7",
                    guidance="Describe management's role in governance processes for climate-related risks and opportunities.",
                    tcfd_equivalent="TCFD Governance b)",
                    data_requirements=["Management positions with climate responsibility", "Integration into performance objectives"],
                ),
            ],
        ),
        ISSBS2Pillar(
            name="Strategy",
            description="Strategy for managing climate-related risks and opportunities including transition plans.",
            disclosures=[
                ISSBS2Disclosure(
                    code="S2-STRAT-1",
                    name="Climate-related risks and opportunities",
                    paragraph_ref="S2.10-12",
                    guidance="Describe climate-related risks and opportunities that could reasonably be expected to affect prospects.",
                    tcfd_equivalent="TCFD Strategy a)",
                    data_requirements=["Physical risks identified", "Transition risks identified", "Opportunities identified"],
                ),
                ISSBS2Disclosure(
                    code="S2-STRAT-2",
                    name="Business model and value chain impact",
                    paragraph_ref="S2.13-14",
                    guidance="Describe effects of climate-related risks and opportunities on business model and value chain.",
                    tcfd_equivalent="TCFD Strategy b)",
                    data_requirements=["Products/services affected", "Value chain impacts", "Adaptation/mitigation activities"],
                ),
                ISSBS2Disclosure(
                    code="S2-STRAT-3",
                    name="Strategy and decision-making",
                    paragraph_ref="S2.15-16",
                    guidance="Describe how climate-related risks and opportunities have affected strategy and decision-making.",
                    tcfd_equivalent="TCFD Strategy b)",
                    data_requirements=["Strategic response plans", "Resource allocation for climate"],
                ),
                ISSBS2Disclosure(
                    code="S2-STRAT-4",
                    name="Financial position effects",
                    paragraph_ref="S2.17-19",
                    guidance="Describe effects on financial position, financial performance and cash flows.",
                    tcfd_equivalent="TCFD Strategy b)",
                    data_requirements=["Current period financial effects", "Anticipated financial effects"],
                ),
                ISSBS2Disclosure(
                    code="S2-STRAT-5",
                    name="Climate resilience (scenario analysis)",
                    paragraph_ref="S2.22",
                    guidance="Describe the resilience of strategy and business model to climate-related changes using scenario analysis.",
                    tcfd_equivalent="TCFD Strategy c)",
                    data_requirements=["Scenarios used (including >=1.5C)", "Key assumptions", "Time horizons"],
                ),
                ISSBS2Disclosure(
                    code="S2-STRAT-6",
                    name="Transition plan",
                    paragraph_ref="S2.14(a)",
                    guidance="Disclose transition plan for managing climate-related risks, including GHG targets.",
                    tcfd_equivalent="N/A (extends TCFD)",
                    iris_cross_refs=["OI4112"],
                    data_requirements=["GHG emission reduction targets", "Decarbonization levers", "Investment requirements"],
                ),
            ],
        ),
        ISSBS2Pillar(
            name="Risk Management",
            description="Processes used to identify, assess, prioritise and monitor climate-related risks and opportunities.",
            disclosures=[
                ISSBS2Disclosure(
                    code="S2-RM-1",
                    name="Risk identification and assessment",
                    paragraph_ref="S2.25",
                    guidance="Describe processes for identifying, assessing and prioritising climate-related risks.",
                    tcfd_equivalent="TCFD Risk Management a)",
                    data_requirements=["Risk identification methodology", "Assessment criteria"],
                ),
                ISSBS2Disclosure(
                    code="S2-RM-2",
                    name="Risk management processes",
                    paragraph_ref="S2.26",
                    guidance="Describe processes for managing climate-related risks.",
                    tcfd_equivalent="TCFD Risk Management b)",
                    data_requirements=["Risk mitigation strategies", "Monitoring processes"],
                ),
                ISSBS2Disclosure(
                    code="S2-RM-3",
                    name="Integration with overall risk management",
                    paragraph_ref="S2.27",
                    guidance="Describe how climate risk processes are integrated into overall risk management.",
                    tcfd_equivalent="TCFD Risk Management c)",
                    data_requirements=["Integration with enterprise risk framework"],
                ),
            ],
        ),
        ISSBS2Pillar(
            name="Metrics and Targets",
            description="Metrics and targets used to manage climate-related risks and opportunities, including GHG emissions.",
            disclosures=[
                ISSBS2Disclosure(
                    code="S2-MT-1",
                    name="Cross-industry metrics",
                    paragraph_ref="S2.29",
                    guidance="Disclose GHG emissions (Scope 1, 2, 3), climate-related transition and physical risks, capital deployment.",
                    tcfd_equivalent="TCFD Metrics a)",
                    iris_cross_refs=["OI4112", "OI9604", "OI1479"],
                    data_requirements=[
                        "Scope 1 GHG emissions (tCO2e)",
                        "Scope 2 GHG emissions (tCO2e)",
                        "Scope 3 GHG emissions (tCO2e)",
                        "Amount of assets/activities vulnerable to transition risks",
                        "Amount of assets/activities vulnerable to physical risks",
                        "Capital expenditure for climate change mitigation",
                        "Internal carbon price (if used)",
                        "Remuneration linked to climate considerations",
                    ],
                ),
                ISSBS2Disclosure(
                    code="S2-MT-2",
                    name="Industry-based metrics",
                    paragraph_ref="S2.32",
                    guidance="Disclose industry-based metrics from SASB standards applicable to entity's industry.",
                    tcfd_equivalent="N/A (extends TCFD)",
                    data_requirements=["Industry-specific metrics per SASB/ISSB B appendix"],
                ),
                ISSBS2Disclosure(
                    code="S2-MT-3",
                    name="GHG emissions targets",
                    paragraph_ref="S2.33-36",
                    guidance="Disclose quantitative and qualitative climate-related targets including GHG reduction targets.",
                    tcfd_equivalent="TCFD Metrics c)",
                    iris_cross_refs=["OD4091"],
                    data_requirements=[
                        "Target scope (Scope 1/2/3)", "Target metric and methodology",
                        "Base year and base year emissions", "Target year",
                        "Whether target is science-based", "Progress against target",
                    ],
                ),
            ],
        ),
    ]
)


def get_ifrs_s2_framework() -> ISSBS2Framework:
    return IFRS_S2


def assess_ifrs_s2_readiness(
    description: str = "",
    reported_metrics: dict | None = None,
    has_scenario_analysis: bool = False,
    has_transition_plan: bool = False,
    ghg_scopes_reported: list[int] | None = None,
    targets_set: bool = False,
) -> dict:
    """Quick climate disclosure readiness screening against IFRS S2.

    This is not a compliance opinion. It separates readiness signals from the
    source-linked disclosure evidence needed for external reporting.
    """
    reported_metrics = reported_metrics or {}
    ghg_scopes_reported = ghg_scopes_reported or []
    text = description.lower()

    pillar_scores: list[dict] = []

    def _status(score: float) -> str:
        if score >= 75:
            return "evidence_ready"
        if score >= 50:
            return "partial"
        return "gaps"

    gov_score = 0.0
    gov_keywords = ["board", "committee", "governance", "oversight", "director"]
    gov_score += min(40, sum(10 for k in gov_keywords if k in text))
    climate_keywords = ["climate", "carbon", "emission", "ghg", "net zero", "net-zero"]
    gov_score += min(30, sum(10 for k in climate_keywords if k in text))
    if "management" in text and any(k in text for k in climate_keywords):
        gov_score += 30
    gov_score = min(100, gov_score)
    pillar_scores.append({"pillar": "Governance", "score": gov_score, "max": 100, "status": _status(gov_score)})

    strat_score = 0.0
    if "transition" in text or "physical risk" in text:
        strat_score += 20
    if has_scenario_analysis:
        strat_score += 30
    if has_transition_plan:
        strat_score += 25
    strat_keywords = ["resilience", "scenario", "pathway", "decarboni"]
    strat_score += min(25, sum(8 for k in strat_keywords if k in text))
    strat_score = min(100, strat_score)
    pillar_scores.append({"pillar": "Strategy", "score": strat_score, "max": 100, "status": _status(strat_score)})

    rm_score = 0.0
    rm_keywords = ["risk management", "risk assessment", "risk identification", "enterprise risk"]
    rm_score += min(50, sum(15 for k in rm_keywords if k in text))
    if any(k in text for k in climate_keywords):
        rm_score += 20
    if "integration" in text or "integrated" in text:
        rm_score += 30
    rm_score = min(100, rm_score)
    pillar_scores.append({"pillar": "Risk Management", "score": rm_score, "max": 100, "status": _status(rm_score)})

    mt_score = 0.0
    normalized_metric_ids = {str(metric_id).strip().upper() for metric_id in reported_metrics}
    ghg_ids = {"OI4112", "OI1479"}
    energy_ids = {"OI8825", "OI3324", "OI1496", "OI9624"}
    if ghg_ids & normalized_metric_ids:
        mt_score += 20
    if energy_ids & normalized_metric_ids:
        mt_score += 10
    mt_score += len(ghg_scopes_reported) * 15
    if targets_set:
        mt_score += 20
    if "science" in text and "based" in text:
        mt_score += 10
    mt_score = min(100, mt_score)
    pillar_scores.append({"pillar": "Metrics and Targets", "score": mt_score, "max": 100, "status": _status(mt_score)})

    overall = round(sum(p["score"] for p in pillar_scores) / len(pillar_scores), 1) if pillar_scores else 0
    readiness_level = "evidence_ready" if overall >= 75 else "partial" if overall >= 50 else "screening_gaps"

    recommendations: list[str] = []
    if pillar_scores[0]["score"] < 40:
        recommendations.append("Establish board-level climate governance and oversight processes")
    if pillar_scores[1]["score"] < 40:
        recommendations.append("Conduct scenario analysis (including >=1.5C pathway) and develop transition plan")
    if pillar_scores[2]["score"] < 40:
        recommendations.append("Integrate climate risks into enterprise risk management framework")
    if pillar_scores[3]["score"] < 40:
        recommendations.append("Report GHG emissions (Scope 1, 2, 3) and set science-based targets")

    return {
        "framework": "ISSB IFRS S2 — Climate-related Disclosures",
        "overall_readiness": overall,
        "readiness_level": readiness_level,
        "assessment_basis": "screening_readiness_not_compliance_opinion",
        "pillar_scores": pillar_scores,
        "recommendations": recommendations,
        "tcfd_equivalence": "IFRS S2 fully subsumes TCFD recommendations with additional requirements",
        "limitations": [
            "Keyword and metric presence do not prove IFRS S2 disclosure compliance.",
            "Use source-linked answers, GHG methodology details, and reviewer sign-off for reporting or assurance.",
        ],
    }
