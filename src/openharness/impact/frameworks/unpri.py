"""UN Principles for Responsible Investment (UNPRI) self-assessment.

The 6 Principles for Responsible Investment provide a framework for incorporating
ESG issues into investment practice. The UNPRI Reporting & Assessment framework
evaluates signatory adherence.

Reference: https://www.unpri.org/
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UNPRIAction(BaseModel):
    """A specific action item under a UNPRI principle."""
    id: str
    description: str
    assessment_question: str = ""
    evidence_examples: list[str] = Field(default_factory=list)


class UNPRIPrinciple(BaseModel):
    """One of the 6 UN PRI principles."""
    number: int
    name: str
    full_text: str = ""
    actions: list[UNPRIAction] = Field(default_factory=list)


UNPRI_PRINCIPLES: list[UNPRIPrinciple] = [
    UNPRIPrinciple(
        number=1,
        name="Incorporate ESG into investment analysis and decision-making",
        full_text="We will incorporate environmental, social and corporate governance (ESG) issues into investment analysis and decision-making processes.",
        actions=[
            UNPRIAction(
                id="1.1", description="Address ESG issues in investment policy statements",
                assessment_question="Does the fund's investment policy explicitly address ESG integration?",
                evidence_examples=["ESG policy document", "Investment policy with ESG section", "Responsible investment policy"],
            ),
            UNPRIAction(
                id="1.2", description="Support development of ESG-related tools, metrics and analyses",
                assessment_question="Does the fund use or develop ESG tools and metrics (e.g., IRIS+, SASB)?",
                evidence_examples=["ESG scoring methodology", "IRIS+ metrics tracked", "SASB materiality assessment"],
            ),
            UNPRIAction(
                id="1.3", description="Assess the capabilities of internal/external investment managers to incorporate ESG",
                assessment_question="Does the fund evaluate its team's ESG capabilities and provide training?",
                evidence_examples=["ESG training programs", "Team ESG competency assessment", "External manager ESG evaluation"],
            ),
            UNPRIAction(
                id="1.4", description="Ask investment service providers to integrate ESG into research and analysis",
                assessment_question="Are ESG criteria included in RFPs and service provider evaluations?",
                evidence_examples=["RFP ESG requirements", "Service provider ESG questionnaire"],
            ),
            UNPRIAction(
                id="1.5", description="Encourage academic and other research on ESG integration",
                assessment_question="Does the fund support or engage with ESG research?",
                evidence_examples=["Research partnerships", "Published ESG insights", "Conference participation"],
            ),
            UNPRIAction(
                id="1.6", description="Advocate ESG training for investment professionals",
                assessment_question="Does the fund provide or support ESG training?",
                evidence_examples=["Training records", "CFA ESG certificate", "PRI Academy courses"],
            ),
        ],
    ),
    UNPRIPrinciple(
        number=2,
        name="Be active owners and incorporate ESG into ownership policies and practices",
        full_text="We will be active owners and incorporate ESG issues into our ownership policies and practices.",
        actions=[
            UNPRIAction(
                id="2.1", description="Develop and disclose an active ownership policy consistent with the Principles",
                assessment_question="Does the fund have an active ownership / engagement policy?",
                evidence_examples=["Engagement policy", "Stewardship code signatory", "Voting policy"],
            ),
            UNPRIAction(
                id="2.2", description="Exercise voting rights or monitor compliance with voting policy",
                assessment_question="Does the fund exercise proxy voting rights with ESG considerations?",
                evidence_examples=["Proxy voting records", "Voting guidelines", "Annual voting report"],
            ),
            UNPRIAction(
                id="2.3", description="Develop an engagement capability (either directly or through outsourcing)",
                assessment_question="Does the fund engage with portfolio companies on ESG issues?",
                evidence_examples=["Engagement logs", "Board seat ESG discussions", "Portfolio company ESG improvement plans"],
            ),
            UNPRIAction(
                id="2.4", description="Participate in the development of policy, regulation and standard setting",
                assessment_question="Does the fund participate in ESG policy development?",
                evidence_examples=["Regulatory consultation responses", "Industry working group membership"],
            ),
            UNPRIAction(
                id="2.5", description="File shareholder resolutions consistent with long-term ESG considerations",
                assessment_question="Has the fund filed or co-filed ESG-related shareholder resolutions?",
                evidence_examples=["Shareholder resolution records", "Collaborative engagement initiatives"],
            ),
        ],
    ),
    UNPRIPrinciple(
        number=3,
        name="Seek appropriate disclosure on ESG issues by investees",
        full_text="We will seek appropriate disclosure on ESG issues by the entities in which we invest.",
        actions=[
            UNPRIAction(
                id="3.1", description="Ask for standardised reporting on ESG issues (GRI, IRIS+, etc.)",
                assessment_question="Does the fund require portfolio companies to report using standardized ESG frameworks?",
                evidence_examples=["Reporting requirements in term sheets", "IRIS+ reporting mandate", "GRI reporting requirement"],
            ),
            UNPRIAction(
                id="3.2", description="Ask for ESG issues to be integrated within annual financial reports",
                assessment_question="Does the fund request ESG integration in financial reporting?",
                evidence_examples=["Annual report ESG section", "Integrated reporting"],
            ),
            UNPRIAction(
                id="3.3", description="Ask for information from companies regarding adoption of relevant norms and standards",
                assessment_question="Does the fund track portfolio companies' adherence to ESG standards and norms?",
                evidence_examples=["ESG compliance tracking", "Standards adoption log"],
            ),
            UNPRIAction(
                id="3.4", description="Support shareholder initiatives and resolutions promoting ESG disclosure",
                assessment_question="Does the fund support ESG disclosure initiatives?",
                evidence_examples=["CDP signatory", "TCFD supporter", "Climate Action 100+"],
            ),
        ],
    ),
    UNPRIPrinciple(
        number=4,
        name="Promote acceptance and implementation of the Principles within the investment industry",
        full_text="We will promote acceptance and implementation of the Principles within the investment industry.",
        actions=[
            UNPRIAction(
                id="4.1", description="Include PRI-related requirements in RFPs",
                assessment_question="Does the fund include PRI alignment in manager selection?",
                evidence_examples=["RFP PRI requirements", "Manager selection ESG criteria"],
            ),
            UNPRIAction(
                id="4.2", description="Align investment mandates, monitoring procedures and performance indicators with ESG",
                assessment_question="Are investment mandates aligned with ESG and impact goals?",
                evidence_examples=["ESG-linked mandates", "Impact KPIs in agreements"],
            ),
            UNPRIAction(
                id="4.3", description="Revisit relationships with service providers that fail to meet ESG expectations",
                assessment_question="Does the fund review service providers for ESG compliance?",
                evidence_examples=["Service provider ESG reviews", "Termination for ESG non-compliance"],
            ),
            UNPRIAction(
                id="4.4", description="Support the development of tools for benchmarking ESG integration",
                assessment_question="Does the fund contribute to ESG benchmarking tools?",
                evidence_examples=["GRESB participation", "EDCI participation", "ESG benchmark development"],
            ),
        ],
    ),
    UNPRIPrinciple(
        number=5,
        name="Work together to enhance effectiveness in implementing the Principles",
        full_text="We will work together to enhance our effectiveness in implementing the Principles.",
        actions=[
            UNPRIAction(
                id="5.1", description="Support/participate in networks and information platforms to share tools and learnings",
                assessment_question="Does the fund participate in ESG/impact networks?",
                evidence_examples=["PRI signatory", "GIIN member", "EDCI participant", "Industry forum membership"],
            ),
            UNPRIAction(
                id="5.2", description="Collectively address relevant emerging ESG issues",
                assessment_question="Does the fund engage in collaborative ESG initiatives?",
                evidence_examples=["Climate Action 100+", "Investor coalitions", "Joint engagements"],
            ),
            UNPRIAction(
                id="5.3", description="Develop or support appropriate collaborative initiatives",
                assessment_question="Has the fund co-developed ESG tools or standards?",
                evidence_examples=["Standards co-authorship", "Tool development", "Research collaboration"],
            ),
        ],
    ),
    UNPRIPrinciple(
        number=6,
        name="Report on activities and progress towards implementing the Principles",
        full_text="We will each report on our activities and progress towards implementing the Principles.",
        actions=[
            UNPRIAction(
                id="6.1", description="Disclose how ESG issues are integrated within investment practices",
                assessment_question="Does the fund publicly disclose its ESG integration approach?",
                evidence_examples=["PRI Transparency Report", "ESG policy on website", "Annual ESG report"],
            ),
            UNPRIAction(
                id="6.2", description="Disclose active ownership activities (voting, engagement, etc.)",
                assessment_question="Does the fund report on stewardship and engagement activities?",
                evidence_examples=["Stewardship report", "Voting disclosure", "Engagement case studies"],
            ),
            UNPRIAction(
                id="6.3", description="Disclose what is required from service providers in relation to the Principles",
                assessment_question="Does the fund disclose ESG expectations for service providers?",
                evidence_examples=["Supplier code of conduct", "ESG requirements documentation"],
            ),
            UNPRIAction(
                id="6.4", description="Communicate with beneficiaries about ESG issues and the Principles",
                assessment_question="Does the fund report ESG performance to LPs/beneficiaries?",
                evidence_examples=["LP ESG reports", "Annual impact report", "Quarterly ESG updates"],
            ),
            UNPRIAction(
                id="6.5", description="Report on progress and/or achievements relating to the Principles using a comply-or-explain approach",
                assessment_question="Does the fund use a comply-or-explain approach for PRI reporting?",
                evidence_examples=["PRI Assessment report", "Comply-or-explain disclosures"],
            ),
        ],
    ),
]


def get_unpri_principles() -> list[UNPRIPrinciple]:
    return UNPRI_PRINCIPLES


def assess_unpri_alignment(
    fund_description: str = "",
    fund_policies: list[str] | None = None,
    document_text: str = "",
) -> dict:
    """Assess a fund's alignment with the 6 UNPRI Principles.

    Returns per-principle scoring and recommendations.
    """
    text = f"{fund_description} {document_text} {' '.join(fund_policies or [])}".lower()

    result = {
        "framework": "UN Principles for Responsible Investment",
        "principles": [],
        "total_actions": 0,
        "addressed_actions": 0,
    }

    principle_keywords = {
        1: ["esg integration", "esg analysis", "investment policy", "esg tool", "iris+", "sasb", "esg training", "esg research"],
        2: ["active ownership", "engagement", "voting", "proxy", "stewardship", "board seat", "shareholder resolution"],
        3: ["esg disclosure", "esg reporting", "standardized reporting", "GRI", "TCFD", "integrated reporting", "transparency"],
        4: ["promote", "RFP", "investment mandate", "service provider", "benchmark", "ESG standard"],
        5: ["network", "collaborative", "GIIN", "PRI signatory", "coalition", "industry forum", "collective"],
        6: ["report", "disclose", "transparency report", "annual report", "LP report", "progress report"],
    }

    for principle in UNPRI_PRINCIPLES:
        p_result = {
            "number": principle.number,
            "name": principle.name,
            "total_actions": len(principle.actions),
            "addressed_actions": [],
            "gap_actions": [],
        }
        result["total_actions"] += len(principle.actions)

        kws = principle_keywords.get(principle.number, [])

        for action in principle.actions:
            addressed = False
            action_text = f"{action.description} {action.assessment_question}".lower()

            general_hits = sum(1 for kw in kws if kw in text)
            if general_hits >= 2:
                addressed = True

            for evidence in action.evidence_examples:
                if evidence.lower() in text:
                    addressed = True
                    break

            action_kws = action.description.lower().split()
            specific_hits = sum(1 for w in action_kws if len(w) > 4 and w in text)
            if specific_hits >= 3:
                addressed = True

            if addressed:
                p_result["addressed_actions"].append(action.id)
                result["addressed_actions"] += 1
            else:
                p_result["gap_actions"].append({
                    "id": action.id,
                    "description": action.description,
                    "question": action.assessment_question,
                })

        p_result["coverage_pct"] = round(
            len(p_result["addressed_actions"]) / len(principle.actions) * 100, 1
        ) if principle.actions else 0

        result["principles"].append(p_result)

    result["overall_coverage"] = round(
        result["addressed_actions"] / result["total_actions"] * 100, 1
    ) if result["total_actions"] > 0 else 0

    return result
