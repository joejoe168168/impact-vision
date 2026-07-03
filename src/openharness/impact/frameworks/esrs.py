"""EU CSRD / ESRS (European Sustainability Reporting Standards) framework.

The Corporate Sustainability Reporting Directive (CSRD) requires reporting under
ESRS, which implements a **double materiality** assessment — organisations must
report on both:
  1. **Impact materiality** — how the company affects people and the environment.
  2. **Financial materiality** — how sustainability issues affect the company's
     financial position and performance.

Reference: EFRAG Final ESRS Set 1 (July 2023), EU Delegated Regulation (EU) 2023/2772.

Status note (verified 2026-07): Omnibus I (Directive (EU) 2026/470, in force
2026-03-18) narrowed CSRD scope to >1,000 employees AND >€450M turnover, and a
revised, simplified ESRS set ("ESRS 2.0", ~60% fewer mandatory datapoints, same
2 cross-cutting + 10 topical architecture) is being adopted as a delegated act
in late 2026 with mandatory application for FY2027 (early adoption allowed for
FY2026). The topical structure below therefore stays valid; individual
datapoint lists will slim down when the revised delegated act lands. The VSME
voluntary standard doubles as the value-chain cap for <1,000-employee
suppliers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ESRSDisclosure(BaseModel):
    """A single ESRS disclosure requirement."""

    code: str
    name: str
    description: str = ""
    data_points: list[str] = Field(default_factory=list)
    iris_cross_refs: list[str] = Field(default_factory=list)
    gri_cross_refs: list[str] = Field(default_factory=list)


class ESRSTopic(BaseModel):
    """An ESRS standard or topical area (e.g. ESRS 1, E1 Climate Change)."""

    code: str
    name: str
    pillar: str  # "cross-cutting", "environment", "social", "governance"
    description: str = ""
    disclosures: list[ESRSDisclosure] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ESRS standards — general, cross-cutting, environment, social, governance
# ---------------------------------------------------------------------------

ESRS_STANDARDS: list[ESRSTopic] = [
    # Cross-cutting
    ESRSTopic(
        code="ESRS 1",
        name="General Requirements",
        pillar="cross-cutting",
        description="Overall reporting principles, double materiality, value chain, time horizons, and sustainability-statement structure",
        disclosures=[
            ESRSDisclosure(code="ESRS1-1", name="Basis for preparation and presentation"),
            ESRSDisclosure(code="ESRS1-2", name="Qualitative characteristics of information"),
            ESRSDisclosure(code="ESRS1-3", name="Double materiality as the basis for sustainability disclosures"),
            ESRSDisclosure(code="ESRS1-4", name="Due diligence and value chain boundaries"),
            ESRSDisclosure(code="ESRS1-5", name="Time horizons and reporting boundaries"),
        ],
        keywords=["double materiality", "value chain", "due diligence", "reporting boundary", "sustainability statement"],
    ),
    ESRSTopic(
        code="ESRS 2",
        name="General Disclosures",
        pillar="cross-cutting",
        description="Governance, strategy, IRO management, metrics & targets (applies to all undertakings)",
        disclosures=[
            ESRSDisclosure(code="GOV-1", name="Role of administrative bodies", gri_cross_refs=["2-9", "2-12"]),
            ESRSDisclosure(code="GOV-2", name="Information provided to and sustainability matters addressed by administrative bodies"),
            ESRSDisclosure(code="GOV-3", name="Integration of sustainability into incentive schemes"),
            ESRSDisclosure(code="GOV-4", name="Statement on sustainability due diligence"),
            ESRSDisclosure(code="GOV-5", name="Risk management and internal controls over sustainability reporting"),
            ESRSDisclosure(code="SBM-1", name="Strategy, business model and value chain"),
            ESRSDisclosure(code="SBM-2", name="Interests and views of stakeholders"),
            ESRSDisclosure(code="SBM-3", name="Material impacts, risks and opportunities and their interaction with strategy and business model"),
            ESRSDisclosure(code="IRO-1", name="Description of the processes to identify and assess material IROs"),
            ESRSDisclosure(code="IRO-2", name="Disclosure requirements in ESRS covered by the sustainability statement"),
            ESRSDisclosure(code="MDR-P", name="Policies adopted to manage material sustainability matters", gri_cross_refs=["3-3"]),
            ESRSDisclosure(code="MDR-A", name="Actions and resources in relation to material sustainability matters"),
            ESRSDisclosure(code="MDR-M", name="Metrics in relation to material sustainability matters"),
            ESRSDisclosure(code="MDR-T", name="Tracking effectiveness of policies and actions through targets"),
        ],
        keywords=["governance", "strategy", "due diligence", "stakeholder", "materiality", "risk management"],
    ),
    # Environment
    ESRSTopic(
        code="E1",
        name="Climate Change",
        pillar="environment",
        description="Climate change mitigation, adaptation, energy. Aligns with TCFD/ISSB S2.",
        disclosures=[
            ESRSDisclosure(code="E1-1", name="Transition plan for climate change mitigation", data_points=["GHG reduction targets", "Decarbonisation levers"]),
            ESRSDisclosure(code="E1-2", name="Policies related to climate change mitigation and adaptation"),
            ESRSDisclosure(code="E1-3", name="Actions and resources related to climate change"),
            ESRSDisclosure(code="E1-4", name="Targets related to climate change mitigation and adaptation"),
            ESRSDisclosure(code="E1-5", name="Energy consumption and mix", iris_cross_refs=["OI4112"], gri_cross_refs=["302-1"]),
            ESRSDisclosure(code="E1-6", name="Gross Scopes 1, 2, 3 and Total GHG emissions", iris_cross_refs=["OI1479", "OI4112"], gri_cross_refs=["305-1", "305-2", "305-3"]),
            ESRSDisclosure(code="E1-7", name="GHG removals and GHG mitigation projects"),
            ESRSDisclosure(code="E1-8", name="Internal carbon pricing"),
            ESRSDisclosure(code="E1-9", name="Anticipated financial effects from material physical and transition risks"),
        ],
        keywords=["climate", "emission", "carbon", "ghg", "energy", "transition", "net zero", "decarbonisation"],
    ),
    ESRSTopic(
        code="E2",
        name="Pollution",
        pillar="environment",
        description="Pollution of air, water and soil; substances of concern; substances of very high concern.",
        disclosures=[
            ESRSDisclosure(code="E2-1", name="Policies related to pollution"),
            ESRSDisclosure(code="E2-2", name="Actions and resources related to pollution"),
            ESRSDisclosure(code="E2-3", name="Targets related to pollution"),
            ESRSDisclosure(code="E2-4", name="Pollution of air, water and soil", gri_cross_refs=["305-7", "303-4"]),
            ESRSDisclosure(code="E2-5", name="Substances of concern and substances of very high concern"),
            ESRSDisclosure(code="E2-6", name="Anticipated financial effects from pollution-related impacts"),
        ],
        keywords=["pollution", "air quality", "water pollution", "soil contamination", "chemical", "toxic"],
    ),
    ESRSTopic(
        code="E3",
        name="Water and Marine Resources",
        pillar="environment",
        description="Water consumption, water stress, marine resource management.",
        disclosures=[
            ESRSDisclosure(code="E3-1", name="Policies related to water and marine resources"),
            ESRSDisclosure(code="E3-2", name="Actions and resources related to water and marine resources"),
            ESRSDisclosure(code="E3-3", name="Targets related to water and marine resources"),
            ESRSDisclosure(code="E3-4", name="Water consumption", gri_cross_refs=["303-5"]),
            ESRSDisclosure(code="E3-5", name="Anticipated financial effects from water and marine resource impacts"),
        ],
        keywords=["water", "marine", "ocean", "aquatic", "water stress", "water consumption"],
    ),
    ESRSTopic(
        code="E4",
        name="Biodiversity and Ecosystems",
        pillar="environment",
        description="Biodiversity and ecosystems, including land use and deforestation.",
        disclosures=[
            ESRSDisclosure(code="E4-1", name="Transition plan on biodiversity and ecosystems"),
            ESRSDisclosure(code="E4-2", name="Policies related to biodiversity and ecosystems"),
            ESRSDisclosure(code="E4-3", name="Actions and resources related to biodiversity and ecosystems"),
            ESRSDisclosure(code="E4-4", name="Targets related to biodiversity and ecosystems"),
            ESRSDisclosure(code="E4-5", name="Impact metrics related to biodiversity and ecosystems", gri_cross_refs=["304-1", "304-2"]),
            ESRSDisclosure(code="E4-6", name="Anticipated financial effects from biodiversity and ecosystem impacts"),
        ],
        keywords=["biodiversity", "ecosystem", "deforestation", "land use", "habitat", "species"],
    ),
    ESRSTopic(
        code="E5",
        name="Resource Use and Circular Economy",
        pillar="environment",
        description="Resource inflows and outflows, waste management, circular economy.",
        disclosures=[
            ESRSDisclosure(code="E5-1", name="Policies related to resource use and circular economy"),
            ESRSDisclosure(code="E5-2", name="Actions and resources related to resource use and circular economy"),
            ESRSDisclosure(code="E5-3", name="Targets related to resource use and circular economy"),
            ESRSDisclosure(code="E5-4", name="Resource inflows", gri_cross_refs=["301-1"]),
            ESRSDisclosure(code="E5-5", name="Resource outflows", gri_cross_refs=["306-3", "306-5"]),
            ESRSDisclosure(code="E5-6", name="Anticipated financial effects from resource use and circular economy impacts"),
        ],
        keywords=["circular economy", "waste", "recycling", "resource", "material", "packaging"],
    ),
    # Social
    ESRSTopic(
        code="S1",
        name="Own Workforce",
        pillar="social",
        description="Working conditions, equal treatment and opportunities, other work-related rights.",
        disclosures=[
            ESRSDisclosure(code="S1-1", name="Policies related to own workforce"),
            ESRSDisclosure(code="S1-2", name="Processes for engaging with own workers and workers' representatives"),
            ESRSDisclosure(code="S1-3", name="Processes to remediate negative impacts and channels for own workers to raise concerns"),
            ESRSDisclosure(code="S1-4", name="Taking action on material impacts on own workforce and effectiveness"),
            ESRSDisclosure(code="S1-5", name="Targets related to managing material negative impacts, advancing positive impacts, and managing material risks and opportunities"),
            ESRSDisclosure(code="S1-6", name="Characteristics of the undertaking's employees", iris_cross_refs=["OI8869"], gri_cross_refs=["2-7"]),
            ESRSDisclosure(code="S1-7", name="Characteristics of non-employee workers in the undertaking's own workforce"),
            ESRSDisclosure(code="S1-8", name="Collective bargaining coverage and social dialogue", gri_cross_refs=["2-30"]),
            ESRSDisclosure(code="S1-9", name="Diversity metrics", iris_cross_refs=["OI6213", "OI1075"], gri_cross_refs=["405-1"]),
            ESRSDisclosure(code="S1-10", name="Adequate wages", gri_cross_refs=["202-1"]),
            ESRSDisclosure(code="S1-11", name="Social protection"),
            ESRSDisclosure(code="S1-12", name="Persons with disabilities"),
            ESRSDisclosure(code="S1-13", name="Training and skills development metrics", gri_cross_refs=["404-1"]),
            ESRSDisclosure(code="S1-14", name="Health and safety metrics", gri_cross_refs=["403-9"]),
            ESRSDisclosure(code="S1-15", name="Work-life balance metrics"),
            ESRSDisclosure(code="S1-16", name="Remuneration metrics (pay gap indicators)", iris_cross_refs=["OI1582"], gri_cross_refs=["405-2"]),
            ESRSDisclosure(code="S1-17", name="Incidents, complaints and severe human rights impacts"),
        ],
        keywords=["employee", "workforce", "labor", "worker", "health", "safety", "diversity", "pay gap", "training"],
    ),
    ESRSTopic(
        code="S2",
        name="Workers in the Value Chain",
        pillar="social",
        description="Impacts on workers upstream and downstream in the value chain.",
        disclosures=[
            ESRSDisclosure(code="S2-1", name="Policies related to value chain workers"),
            ESRSDisclosure(code="S2-2", name="Processes for engaging with value chain workers"),
            ESRSDisclosure(code="S2-3", name="Processes to remediate negative impacts on value chain workers"),
            ESRSDisclosure(code="S2-4", name="Taking action on material impacts on value chain workers"),
            ESRSDisclosure(code="S2-5", name="Targets related to managing impacts on value chain workers"),
        ],
        keywords=["supply chain", "value chain", "supplier", "sourcing", "forced labor", "child labor"],
    ),
    ESRSTopic(
        code="S3",
        name="Affected Communities",
        pillar="social",
        description="Impacts on local and indigenous communities.",
        disclosures=[
            ESRSDisclosure(code="S3-1", name="Policies related to affected communities"),
            ESRSDisclosure(code="S3-2", name="Processes for engaging with affected communities"),
            ESRSDisclosure(code="S3-3", name="Processes to remediate negative impacts on affected communities"),
            ESRSDisclosure(code="S3-4", name="Taking action on material impacts on affected communities"),
            ESRSDisclosure(code="S3-5", name="Targets related to managing impacts on affected communities"),
        ],
        keywords=["community", "indigenous", "displacement", "land rights", "local impact"],
    ),
    ESRSTopic(
        code="S4",
        name="Consumers and End-Users",
        pillar="social",
        description="Impacts related to consumers and end-users of products/services.",
        disclosures=[
            ESRSDisclosure(code="S4-1", name="Policies related to consumers and end-users"),
            ESRSDisclosure(code="S4-2", name="Processes for engaging with consumers and end-users about impacts"),
            ESRSDisclosure(code="S4-3", name="Processes to remediate negative impacts and channels to raise concerns"),
            ESRSDisclosure(code="S4-4", name="Taking action on material impacts on consumers and end-users"),
            ESRSDisclosure(code="S4-5", name="Targets related to managing impacts on consumers and end-users"),
        ],
        keywords=["consumer", "customer", "end-user", "product safety", "data privacy", "health"],
    ),
    # Governance
    ESRSTopic(
        code="G1",
        name="Business Conduct",
        pillar="governance",
        description="Business ethics, corporate culture, anti-corruption, political engagement, supplier relationships, payment practices.",
        disclosures=[
            ESRSDisclosure(code="G1-1", name="Business conduct policies and corporate culture", gri_cross_refs=["2-23"]),
            ESRSDisclosure(code="G1-2", name="Management of relationships with suppliers"),
            ESRSDisclosure(code="G1-3", name="Prevention and detection of corruption and bribery", gri_cross_refs=["205-2"]),
            ESRSDisclosure(code="G1-4", name="Incidents of corruption or bribery", gri_cross_refs=["205-3"]),
            ESRSDisclosure(code="G1-5", name="Political influence and lobbying activities", gri_cross_refs=["415-1"]),
            ESRSDisclosure(code="G1-6", name="Payment practices"),
        ],
        keywords=["corruption", "bribery", "ethics", "lobbying", "payment", "supplier relationship"],
    ),
]


def get_esrs_standards(pillar: str | None = None) -> list[ESRSTopic]:
    """Return all ESRS topical standards, optionally filtered by pillar."""
    if pillar:
        p = pillar.lower()
        return [s for s in ESRS_STANDARDS if s.pillar == p]
    return list(ESRS_STANDARDS)


def get_total_data_points() -> int:
    """Count total disclosure requirements across all ESRS standards."""
    return sum(len(s.disclosures) for s in ESRS_STANDARDS)


# ---------------------------------------------------------------------------
# Double-materiality assessment
# ---------------------------------------------------------------------------


class MaterialityResult(BaseModel):
    """Result of a single topic's materiality assessment."""

    topic_code: str
    topic_name: str
    pillar: str
    impact_material: bool = False
    financial_material: bool = False
    double_material: bool = False
    materiality_status: str = "not_indicated"
    confidence: str = "low"
    impact_evidence: list[str] = Field(default_factory=list)
    financial_evidence: list[str] = Field(default_factory=list)
    disclosures_addressed: int = 0
    disclosures_total: int = 0
    coverage_pct: float = 0.0
    gaps: list[str] = Field(default_factory=list)


_FINANCIAL_KEYWORDS: dict[str, list[str]] = {
    "E1": ["carbon tax", "stranded asset", "transition risk", "physical risk", "climate risk", "carbon price", "energy cost"],
    "E2": ["fine", "penalty", "remediation cost", "cleanup", "regulation", "compliance"],
    "E3": ["water scarcity", "drought", "water price", "water risk"],
    "E4": ["deforestation risk", "biodiversity regulation", "nature-related risk"],
    "E5": ["raw material cost", "supply disruption", "waste disposal cost"],
    "S1": ["turnover", "talent retention", "strike", "lawsuit", "litigation"],
    "S2": ["supply chain disruption", "reputational risk", "labor dispute"],
    "S3": ["social license", "protest", "community opposition", "permit"],
    "S4": ["product recall", "consumer lawsuit", "data breach", "privacy fine", "GDPR"],
    "G1": ["corruption fine", "bribery scandal", "sanction", "regulatory action"],
}


def assess_double_materiality(
    description: str = "",
    document_text: str = "",
    sector: str = "",
    reported_metrics: dict[str, str] | None = None,
) -> dict:
    """Run a double-materiality screening across all ESRS standards.

    Returns per-topic potential impact materiality, potential financial
    materiality, and a combined potential double-materiality flag with coverage
    analysis. This screening does not replace a CSRD-compliant double
    materiality process with stakeholder validation.
    """
    text = f"{description} {document_text} {sector}".lower()
    metrics = reported_metrics or {}

    results: list[MaterialityResult] = []

    for topic in ESRS_STANDARDS:
        impact_evidence: list[str] = []
        financial_evidence: list[str] = []

        for kw in topic.keywords:
            if kw in text:
                impact_evidence.append(kw)

        fin_kws = _FINANCIAL_KEYWORDS.get(topic.code, [])
        for fkw in fin_kws:
            if fkw in text:
                financial_evidence.append(fkw)

        addressed = 0
        gaps: list[str] = []
        for disc in topic.disclosures:
            found = False
            disc_lower = disc.name.lower()
            if any(kw in text for kw in disc_lower.split()[:4] if len(kw) > 3):
                found = True
            for ref in disc.iris_cross_refs:
                if ref in metrics:
                    found = True
                    impact_evidence.append(f"IRIS+ {ref}")
            if found:
                addressed += 1
            else:
                gaps.append(f"{disc.code}: {disc.name}")

        is_impact = len(impact_evidence) >= 2
        is_financial = len(financial_evidence) >= 1
        materiality_status = (
            "potential_double_material"
            if is_impact and is_financial
            else "potential_impact_material"
            if is_impact
            else "potential_financial_material"
            if is_financial
            else "not_indicated"
        )
        confidence = "medium" if is_impact and is_financial else "low" if (is_impact or is_financial) else "low"
        total = len(topic.disclosures)
        cov = round(addressed / total * 100, 1) if total else 0.0

        results.append(MaterialityResult(
            topic_code=topic.code,
            topic_name=topic.name,
            pillar=topic.pillar,
            impact_material=is_impact,
            financial_material=is_financial,
            double_material=is_impact and is_financial,
            materiality_status=materiality_status,
            confidence=confidence,
            impact_evidence=list(set(impact_evidence)),
            financial_evidence=list(set(financial_evidence)),
            disclosures_addressed=addressed,
            disclosures_total=total,
            coverage_pct=cov,
            gaps=gaps[:5],
        ))

    material_topics = [r for r in results if r.impact_material or r.financial_material]
    double_topics = [r for r in results if r.double_material]
    total_disc = sum(r.disclosures_total for r in results)
    addressed_disc = sum(r.disclosures_addressed for r in results)

    return {
        "framework": "EU CSRD / ESRS (European Sustainability Reporting Standards)",
        "assessment_basis": "keyword_and_metric_screening_not_csrd_double_materiality_opinion",
        "requires_stakeholder_validation": True,
        "total_topics": len(ESRS_STANDARDS),
        "material_topics": len(material_topics),
        "double_material_topics": len(double_topics),
        "total_disclosures": total_disc,
        "disclosures_addressed": addressed_disc,
        "overall_coverage_pct": round(addressed_disc / total_disc * 100, 1) if total_disc else 0.0,
        "topics": [r.model_dump() for r in results],
        "summary": (
            f"{len(material_topics)}/{len(ESRS_STANDARDS)} standards with materiality signals "
            f"({len(double_topics)} potentially double-material). "
            f"Disclosure coverage: {addressed_disc}/{total_disc}."
        ),
        "limitations": [
            "Materiality flags are screening signals, not final ESRS materiality conclusions.",
            "A CSRD-ready process requires stakeholder input, IRO validation, thresholds, and governance sign-off.",
        ],
    }
