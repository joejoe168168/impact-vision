"""TCFD (Task Force on Climate-related Financial Disclosures) / IFRS S2.

The TCFD framework (now subsumed into IFRS S2 under the ISSB) structures
climate disclosure around 4 pillars: Governance, Strategy, Risk Management,
and Metrics & Targets.

Reference: https://www.fsb-tcfd.org/ and https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/ifrs-s2-climate-related-disclosures/
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TCFDDisclosure(BaseModel):
    """A specific TCFD recommended disclosure."""
    code: str
    name: str
    guidance: str = ""
    iris_cross_refs: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)


class TCFDPillar(BaseModel):
    """One of the 4 TCFD pillars."""
    name: str
    description: str = ""
    disclosures: list[TCFDDisclosure] = Field(default_factory=list)


class TCFDFramework(BaseModel):
    """The full TCFD / IFRS S2 framework."""
    pillars: list[TCFDPillar] = Field(default_factory=list)


TCFD = TCFDFramework(pillars=[
    TCFDPillar(
        name="Governance",
        description="The organization's governance around climate-related risks and opportunities",
        disclosures=[
            TCFDDisclosure(
                code="GOV-A",
                name="Board oversight of climate-related risks and opportunities",
                guidance="Describe the board's oversight of climate-related risks and opportunities",
                data_requirements=["Board/committee responsible for climate oversight", "Frequency of climate discussions", "How board is informed about climate issues"],
            ),
            TCFDDisclosure(
                code="GOV-B",
                name="Management's role in assessing and managing climate-related risks",
                guidance="Describe management's role in assessing and managing climate-related risks and opportunities",
                data_requirements=["Management positions responsible", "Processes for informing management", "How management monitors climate issues"],
            ),
        ],
    ),
    TCFDPillar(
        name="Strategy",
        description="Actual and potential impacts of climate-related risks and opportunities on business, strategy, and financial planning",
        disclosures=[
            TCFDDisclosure(
                code="STR-A",
                name="Climate-related risks and opportunities identified",
                guidance="Describe the climate-related risks and opportunities the organization has identified over short, medium, and long term",
                data_requirements=["Physical risks identified", "Transition risks identified", "Opportunities identified", "Time horizons defined"],
            ),
            TCFDDisclosure(
                code="STR-B",
                name="Impact on business, strategy, and financial planning",
                guidance="Describe the impact of climate-related risks and opportunities on business, strategy, and financial planning",
                data_requirements=["Impact on products/services", "Impact on supply chain", "Impact on adaptation/mitigation", "Impact on R&D", "Impact on operations/facilities"],
            ),
            TCFDDisclosure(
                code="STR-C",
                name="Resilience of strategy under different climate scenarios",
                guidance="Describe the resilience of the organization's strategy, taking into consideration different climate-related scenarios including a 2°C or lower scenario",
                data_requirements=["Scenario analysis conducted", "Scenarios used (e.g., 1.5°C, 2°C, 4°C)", "Key assumptions", "Time horizons", "Results and implications"],
            ),
        ],
    ),
    TCFDPillar(
        name="Risk Management",
        description="How the organization identifies, assesses, and manages climate-related risks",
        disclosures=[
            TCFDDisclosure(
                code="RISK-A",
                name="Process for identifying and assessing climate-related risks",
                guidance="Describe the organization's processes for identifying and assessing climate-related risks",
                data_requirements=["Risk identification process", "Scope of risks considered", "How materiality is determined", "Physical vs transition risks"],
            ),
            TCFDDisclosure(
                code="RISK-B",
                name="Process for managing climate-related risks",
                guidance="Describe the organization's processes for managing climate-related risks",
                data_requirements=["Risk mitigation strategies", "Risk transfer mechanisms", "Prioritization process"],
            ),
            TCFDDisclosure(
                code="RISK-C",
                name="Integration into overall risk management",
                guidance="Describe how processes for identifying, assessing, and managing climate-related risks are integrated into the organization's overall risk management",
                data_requirements=["Integration with enterprise risk management", "Escalation processes", "Risk appetite/tolerance"],
            ),
        ],
    ),
    TCFDPillar(
        name="Metrics & Targets",
        description="Metrics and targets used to assess and manage relevant climate-related risks and opportunities",
        disclosures=[
            TCFDDisclosure(
                code="MET-A",
                name="Metrics used to assess climate-related risks and opportunities",
                guidance="Disclose the metrics used by the organization to assess climate-related risks and opportunities in line with its strategy and risk management process",
                data_requirements=["Climate-related metrics tracked", "Water usage", "Energy usage", "Land use", "Waste management"],
                iris_cross_refs=["OI1479", "OI4112"],
            ),
            TCFDDisclosure(
                code="MET-B",
                name="Scope 1, 2, and 3 GHG emissions",
                guidance="Disclose Scope 1, Scope 2, and if appropriate, Scope 3 greenhouse gas emissions and the related risks",
                data_requirements=["Scope 1 emissions (tCO2e)", "Scope 2 emissions (tCO2e)", "Scope 3 emissions (tCO2e)", "Methodology used", "Base year"],
                iris_cross_refs=["OI4112", "OI1479"],
            ),
            TCFDDisclosure(
                code="MET-C",
                name="Targets and performance against targets",
                guidance="Describe the targets used by the organization to manage climate-related risks and opportunities and performance against targets",
                data_requirements=["Emission reduction targets", "Target year", "Base year", "Interim targets", "Progress to date", "Science-based target status"],
                iris_cross_refs=["OD4091"],
            ),
        ],
    ),
])


def get_tcfd_framework() -> TCFDFramework:
    return TCFD


def assess_tcfd_alignment(
    company_description: str = "",
    reported_data: dict[str, str] | None = None,
    document_text: str = "",
) -> dict:
    """Assess a company's alignment with TCFD/IFRS S2 framework.

    Returns per-pillar coverage and gap analysis.
    """
    text = f"{company_description} {document_text}".lower()
    reported = reported_data or {}

    result = {
        "framework": "TCFD / IFRS S2",
        "pillars": [],
        "overall_coverage": 0.0,
        "total_disclosures": 0,
        "addressed_disclosures": 0,
    }

    pillar_keywords = {
        "Governance": ["board", "governance", "oversight", "committee", "management role", "climate governance"],
        "Strategy": ["climate risk", "opportunity", "scenario", "resilience", "transition", "physical risk", "2 degree", "1.5 degree", "net zero"],
        "Risk Management": ["risk identification", "risk assessment", "risk management", "mitigation", "risk process", "enterprise risk"],
        "Metrics & Targets": ["emission", "scope 1", "scope 2", "scope 3", "GHG", "carbon", "target", "reduction target", "net zero target", "science-based"],
    }

    total = 0
    addressed = 0

    for pillar in TCFD.pillars:
        pillar_result = {
            "name": pillar.name,
            "total_disclosures": len(pillar.disclosures),
            "addressed": [],
            "gaps": [],
        }
        total += len(pillar.disclosures)

        kws = pillar_keywords.get(pillar.name, [])

        for disc in pillar.disclosures:
            disc_addressed = False

            kw_hits = sum(1 for kw in kws if kw in text)
            if kw_hits >= 2:
                disc_addressed = True

            if disc.iris_cross_refs:
                for ref in disc.iris_cross_refs:
                    if ref in reported:
                        disc_addressed = True
                        break

            if disc_addressed:
                addressed += 1
                pillar_result["addressed"].append({
                    "code": disc.code,
                    "name": disc.name,
                })
            else:
                pillar_result["gaps"].append({
                    "code": disc.code,
                    "name": disc.name,
                    "data_requirements": disc.data_requirements,
                })

        pillar_result["coverage_pct"] = round(
            len(pillar_result["addressed"]) / len(pillar.disclosures) * 100, 1
        ) if pillar.disclosures else 0

        result["pillars"].append(pillar_result)

    result["total_disclosures"] = total
    result["addressed_disclosures"] = addressed
    result["overall_coverage"] = round(addressed / total * 100, 1) if total > 0 else 0

    return result
