"""IFC Operating Principles for Impact Management (OPIM).

The 9 principles provide a framework for investors to ensure that
impact considerations are integrated throughout the investment lifecycle.

Reference: https://www.impactprinciples.org/
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OPIMPrinciple(BaseModel):
    id: int
    name: str
    category: str
    description: str
    verification_requirements: list[str] = Field(default_factory=list)


class OPIMFramework(BaseModel):
    name: str = "IFC Operating Principles for Impact Management"
    version: str = "2019"
    total_principles: int = 9
    principles: list[OPIMPrinciple] = Field(default_factory=list)


OPIM_PRINCIPLES = OPIMFramework(
    principles=[
        OPIMPrinciple(
            id=1, name="Strategic Intent", category="Strategic Intent",
            description="Define strategic impact objective(s), consistent with the investment strategy.",
            verification_requirements=[
                "Documented impact thesis",
                "Clear articulation of intended impact outcomes",
                "SDG or thematic alignment documented",
            ],
        ),
        OPIMPrinciple(
            id=2, name="Origination & Structuring", category="Origination & Structuring",
            description="Manage strategic impact on a portfolio basis and target each investment to contribute to the strategy.",
            verification_requirements=[
                "Portfolio-level impact strategy",
                "Investment screening criteria include impact considerations",
                "Impact expectations set during origination",
            ],
        ),
        OPIMPrinciple(
            id=3, name="Manager Contribution", category="Origination & Structuring",
            description="Establish the Manager's contribution to the achievement of impact.",
            verification_requirements=[
                "Theory of Change documented",
                "Contribution pathway described (signaling, engagement, growing markets, providing flexibility)",
                "Counterfactual assessment conducted",
            ],
        ),
        OPIMPrinciple(
            id=4, name="Impact at Entry", category="Portfolio Management",
            description="Assess the expected impact of each investment at entry, based on a systematic approach.",
            verification_requirements=[
                "Pre-investment impact assessment process",
                "5 Dimensions of Impact or equivalent framework applied",
                "Expected outcomes quantified where possible",
            ],
        ),
        OPIMPrinciple(
            id=5, name="Negative Impact Assessment", category="Portfolio Management",
            description="Assess, address, monitor, and manage potential negative impacts of each investment.",
            verification_requirements=[
                "Norms-based exclusion screening",
                "Negative impact identification process",
                "Mitigation strategies documented",
            ],
        ),
        OPIMPrinciple(
            id=6, name="Monitoring", category="Portfolio Management",
            description="Monitor progress of each investment in achieving impact against expectations.",
            verification_requirements=[
                "Regular impact data collection (annual minimum)",
                "IRIS+ or equivalent metrics tracked",
                "Performance against targets reported",
            ],
        ),
        OPIMPrinciple(
            id=7, name="Exit Considerations", category="Portfolio Management",
            description="Conduct exits considering the effect on sustained impact.",
            verification_requirements=[
                "Exit impact assessment process",
                "Sustainability of impact post-exit considered",
                "Exit decisions incorporate impact factors",
            ],
        ),
        OPIMPrinciple(
            id=8, name="Review & Feedback", category="Independent Verification",
            description="Review, document, and improve decisions and processes based on impact and lessons learned.",
            verification_requirements=[
                "Annual impact review process",
                "Lessons learned documentation",
                "Process improvement tracking",
            ],
        ),
        OPIMPrinciple(
            id=9, name="Independent Verification", category="Independent Verification",
            description="Publicly disclose alignment with Principles and arrange for independent verification.",
            verification_requirements=[
                "Public disclosure of Principles alignment",
                "Independent verification completed or scheduled",
                "Verification report publicly available",
            ],
        ),
    ]
)


def get_opim_framework() -> OPIMFramework:
    return OPIM_PRINCIPLES


def assess_opim_alignment(
    has_impact_thesis: bool = False,
    has_theory_of_change: bool = False,
    has_impact_policy: bool = False,
    has_external_audit: bool = False,
    metrics_count: int = 0,
    sdg_count: int = 0,
    has_exclusion_screening: bool = False,
) -> dict:
    """Quick assessment of alignment with IFC Operating Principles."""
    results: list[dict] = []
    aligned = 0

    signals = {
        1: has_impact_thesis and sdg_count > 0,
        2: has_impact_policy,
        3: has_theory_of_change,
        4: metrics_count >= 3 and sdg_count >= 1,
        5: has_exclusion_screening,
        6: metrics_count >= 3,
        7: False,
        8: has_impact_policy,
        9: has_external_audit,
    }

    for p in OPIM_PRINCIPLES.principles:
        is_aligned = signals.get(p.id, False)
        if is_aligned:
            aligned += 1
        results.append({
            "principle": p.id,
            "name": p.name,
            "aligned": is_aligned,
            "requirements": p.verification_requirements,
        })

    return {
        "framework": "IFC Operating Principles for Impact Management",
        "aligned_count": aligned,
        "total_principles": 9,
        "alignment_pct": round(aligned / 9 * 100),
        "principles": results,
    }
