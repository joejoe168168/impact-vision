"""GRI (Global Reporting Initiative) Universal and Topic Standards.

GRI provides the world's most widely used sustainability reporting standards.
- Universal Standards (GRI 1, 2, 3): Apply to all organizations
- Topic Standards: Economic (200), Environmental (300), Social (400)

Reference: https://www.globalreporting.org/standards/
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GRIDisclosure(BaseModel):
    """A specific GRI disclosure requirement."""
    code: str  # e.g., "302-1"
    name: str
    description: str = ""
    iris_cross_refs: list[str] = Field(default_factory=list)


class GRIStandard(BaseModel):
    """A GRI Topic Standard."""
    code: str  # e.g., "GRI 302"
    name: str
    series: str  # "universal", "economic", "environmental", "social"
    description: str = ""
    disclosures: list[GRIDisclosure] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


GRI_STANDARDS: list[GRIStandard] = [
    # === Universal Standards ===
    GRIStandard(
        code="GRI 1", name="Foundation 2021", series="universal",
        description="Sets out the purpose and system of GRI Standards, requirements and principles for reporting",
        disclosures=[
            GRIDisclosure(code="1-1", name="Application of GRI 1"),
        ],
    ),
    GRIStandard(
        code="GRI 2", name="General Disclosures 2021", series="universal",
        description="Disclosures about the organization, governance, strategy, and stakeholder engagement",
        disclosures=[
            GRIDisclosure(code="2-1", name="Organizational details"),
            GRIDisclosure(code="2-2", name="Entities included in sustainability reporting"),
            GRIDisclosure(code="2-3", name="Reporting period, frequency and contact point"),
            GRIDisclosure(code="2-6", name="Activities, value chain and other business relationships"),
            GRIDisclosure(code="2-7", name="Employees", iris_cross_refs=["OI8869", "OI6213"]),
            GRIDisclosure(code="2-8", name="Workers who are not employees"),
            GRIDisclosure(code="2-9", name="Governance structure and composition", iris_cross_refs=["OI1075"]),
            GRIDisclosure(code="2-12", name="Role of the highest governance body in overseeing sustainability"),
            GRIDisclosure(code="2-19", name="Remuneration policies"),
            GRIDisclosure(code="2-22", name="Statement on sustainable development strategy"),
            GRIDisclosure(code="2-23", name="Policy commitments"),
            GRIDisclosure(code="2-25", name="Processes to remediate negative impacts"),
            GRIDisclosure(code="2-26", name="Mechanisms for seeking advice and raising concerns"),
            GRIDisclosure(code="2-27", name="Compliance with laws and regulations"),
            GRIDisclosure(code="2-29", name="Approach to stakeholder engagement"),
            GRIDisclosure(code="2-30", name="Collective bargaining agreements"),
        ],
        keywords=["governance", "organization", "stakeholder"],
    ),
    GRIStandard(
        code="GRI 3", name="Material Topics 2021", series="universal",
        description="Process for determining material topics and how to report them",
        disclosures=[
            GRIDisclosure(code="3-1", name="Process to determine material topics"),
            GRIDisclosure(code="3-2", name="List of material topics"),
            GRIDisclosure(code="3-3", name="Management of material topics"),
        ],
        keywords=["materiality", "material topics"],
    ),
    # === Economic Standards (200 series) ===
    GRIStandard(
        code="GRI 201", name="Economic Performance 2016", series="economic",
        description="Direct economic value generated and distributed",
        disclosures=[
            GRIDisclosure(code="201-1", name="Direct economic value generated and distributed",
                         iris_cross_refs=["FP4761"]),
            GRIDisclosure(code="201-2", name="Financial implications of climate change"),
            GRIDisclosure(code="201-3", name="Defined benefit plan obligations"),
            GRIDisclosure(code="201-4", name="Financial assistance received from government"),
        ],
        keywords=["economic", "revenue", "financial", "value"],
    ),
    GRIStandard(
        code="GRI 202", name="Market Presence 2016", series="economic",
        disclosures=[
            GRIDisclosure(code="202-1", name="Ratios of standard entry level wage to local minimum wage",
                         iris_cross_refs=["OI1582"]),
            GRIDisclosure(code="202-2", name="Proportion of senior management hired from the local community"),
        ],
        keywords=["wage", "local", "community", "market"],
    ),
    GRIStandard(
        code="GRI 203", name="Indirect Economic Impacts 2016", series="economic",
        disclosures=[
            GRIDisclosure(code="203-1", name="Infrastructure investments and services supported"),
            GRIDisclosure(code="203-2", name="Significant indirect economic impacts"),
        ],
        keywords=["indirect", "infrastructure", "community development"],
    ),
    GRIStandard(
        code="GRI 204", name="Procurement Practices 2016", series="economic",
        disclosures=[
            GRIDisclosure(code="204-1", name="Proportion of spending on local suppliers"),
        ],
        keywords=["procurement", "supplier", "local sourcing"],
    ),
    GRIStandard(
        code="GRI 205", name="Anti-corruption 2016", series="economic",
        disclosures=[
            GRIDisclosure(code="205-1", name="Operations assessed for risks related to corruption"),
            GRIDisclosure(code="205-2", name="Communication and training about anti-corruption"),
            GRIDisclosure(code="205-3", name="Confirmed incidents of corruption"),
        ],
        keywords=["corruption", "bribery", "ethics"],
    ),
    GRIStandard(
        code="GRI 206", name="Anti-competitive Behavior 2016", series="economic",
        disclosures=[
            GRIDisclosure(code="206-1", name="Legal actions for anti-competitive behavior"),
        ],
        keywords=["anti-competitive", "antitrust"],
    ),
    GRIStandard(
        code="GRI 207", name="Tax 2019", series="economic",
        disclosures=[
            GRIDisclosure(code="207-1", name="Approach to tax"),
            GRIDisclosure(code="207-2", name="Tax governance, control, and risk management"),
            GRIDisclosure(code="207-3", name="Stakeholder engagement and management of concerns related to tax"),
            GRIDisclosure(code="207-4", name="Country-by-country reporting"),
        ],
        keywords=["tax"],
    ),
    # === Environmental Standards (300 series) ===
    GRIStandard(
        code="GRI 301", name="Materials 2016", series="environmental",
        disclosures=[
            GRIDisclosure(code="301-1", name="Materials used by weight or volume"),
            GRIDisclosure(code="301-2", name="Recycled input materials used"),
            GRIDisclosure(code="301-3", name="Reclaimed products and their packaging materials"),
        ],
        keywords=["materials", "recycled", "circular"],
    ),
    GRIStandard(
        code="GRI 302", name="Energy 2016", series="environmental",
        disclosures=[
            GRIDisclosure(code="302-1", name="Energy consumption within the organization"),
            GRIDisclosure(code="302-2", name="Energy consumption outside of the organization"),
            GRIDisclosure(code="302-3", name="Energy intensity"),
            GRIDisclosure(code="302-4", name="Reduction of energy consumption"),
            GRIDisclosure(code="302-5", name="Reductions in energy requirements of products and services"),
        ],
        keywords=["energy", "renewable", "consumption"],
    ),
    GRIStandard(
        code="GRI 303", name="Water and Effluents 2018", series="environmental",
        disclosures=[
            GRIDisclosure(code="303-1", name="Interactions with water as a shared resource"),
            GRIDisclosure(code="303-2", name="Management of water discharge-related impacts"),
            GRIDisclosure(code="303-3", name="Water withdrawal"),
            GRIDisclosure(code="303-4", name="Water discharge"),
            GRIDisclosure(code="303-5", name="Water consumption"),
        ],
        keywords=["water", "effluent", "discharge"],
    ),
    GRIStandard(
        code="GRI 304", name="Biodiversity 2016", series="environmental",
        disclosures=[
            GRIDisclosure(code="304-1", name="Operational sites in or adjacent to protected areas"),
            GRIDisclosure(code="304-2", name="Significant impacts of activities on biodiversity"),
            GRIDisclosure(code="304-3", name="Habitats protected or restored"),
            GRIDisclosure(code="304-4", name="IUCN Red List species affected"),
        ],
        keywords=["biodiversity", "habitat", "species", "ecosystem"],
    ),
    GRIStandard(
        code="GRI 305", name="Emissions 2016", series="environmental",
        disclosures=[
            GRIDisclosure(code="305-1", name="Direct (Scope 1) GHG emissions",
                         iris_cross_refs=["OI4112"]),
            GRIDisclosure(code="305-2", name="Energy indirect (Scope 2) GHG emissions"),
            GRIDisclosure(code="305-3", name="Other indirect (Scope 3) GHG emissions"),
            GRIDisclosure(code="305-4", name="GHG emissions intensity"),
            GRIDisclosure(code="305-5", name="Reduction of GHG emissions",
                         iris_cross_refs=["OI1479"]),
            GRIDisclosure(code="305-6", name="Emissions of ozone-depleting substances (ODS)"),
            GRIDisclosure(code="305-7", name="NOx, SOx, and other significant air emissions"),
        ],
        keywords=["emission", "GHG", "carbon", "greenhouse", "scope 1", "scope 2", "scope 3"],
    ),
    GRIStandard(
        code="GRI 306", name="Waste 2020", series="environmental",
        disclosures=[
            GRIDisclosure(code="306-1", name="Waste generation and significant waste-related impacts"),
            GRIDisclosure(code="306-2", name="Management of significant waste-related impacts"),
            GRIDisclosure(code="306-3", name="Waste generated"),
            GRIDisclosure(code="306-4", name="Waste diverted from disposal"),
            GRIDisclosure(code="306-5", name="Waste directed to disposal"),
        ],
        keywords=["waste", "disposal", "recycling", "circular economy"],
    ),
    GRIStandard(
        code="GRI 308", name="Supplier Environmental Assessment 2016", series="environmental",
        disclosures=[
            GRIDisclosure(code="308-1", name="New suppliers that were screened using environmental criteria"),
            GRIDisclosure(code="308-2", name="Negative environmental impacts in the supply chain"),
        ],
        keywords=["supplier", "supply chain", "environmental assessment"],
    ),
    # === Social Standards (400 series) ===
    GRIStandard(
        code="GRI 401", name="Employment 2016", series="social",
        disclosures=[
            GRIDisclosure(code="401-1", name="New employee hires and employee turnover",
                         iris_cross_refs=["OI8869"]),
            GRIDisclosure(code="401-2", name="Benefits provided to full-time employees"),
            GRIDisclosure(code="401-3", name="Parental leave"),
        ],
        keywords=["employment", "turnover", "benefits", "parental"],
    ),
    GRIStandard(
        code="GRI 402", name="Labor/Management Relations 2016", series="social",
        disclosures=[
            GRIDisclosure(code="402-1", name="Minimum notice periods regarding operational changes"),
        ],
        keywords=["labor", "management relations"],
    ),
    GRIStandard(
        code="GRI 403", name="Occupational Health and Safety 2018", series="social",
        disclosures=[
            GRIDisclosure(code="403-1", name="Occupational H&S management system"),
            GRIDisclosure(code="403-2", name="Hazard identification, risk assessment, incident investigation"),
            GRIDisclosure(code="403-5", name="Worker training on occupational H&S"),
            GRIDisclosure(code="403-8", name="Workers covered by an OHS management system"),
            GRIDisclosure(code="403-9", name="Work-related injuries"),
            GRIDisclosure(code="403-10", name="Work-related ill health"),
        ],
        keywords=["occupational", "health and safety", "injury", "H&S", "workplace safety"],
    ),
    GRIStandard(
        code="GRI 404", name="Training and Education 2016", series="social",
        disclosures=[
            GRIDisclosure(code="404-1", name="Average hours of training per year per employee"),
            GRIDisclosure(code="404-2", name="Programs for upgrading employee skills"),
            GRIDisclosure(code="404-3", name="Percentage of employees receiving performance reviews"),
        ],
        keywords=["training", "education", "skills", "performance review"],
    ),
    GRIStandard(
        code="GRI 405", name="Diversity and Equal Opportunity 2016", series="social",
        disclosures=[
            GRIDisclosure(code="405-1", name="Diversity of governance bodies and employees",
                         iris_cross_refs=["OI6213", "OI1571", "OI1075"]),
            GRIDisclosure(code="405-2", name="Ratio of basic salary and remuneration of women to men",
                         iris_cross_refs=["OI1582"]),
        ],
        keywords=["diversity", "gender", "equality", "equal opportunity"],
    ),
    GRIStandard(
        code="GRI 406", name="Non-discrimination 2016", series="social",
        disclosures=[
            GRIDisclosure(code="406-1", name="Incidents of discrimination and corrective actions taken"),
        ],
        keywords=["discrimination"],
    ),
    GRIStandard(
        code="GRI 407", name="Freedom of Association and Collective Bargaining 2016", series="social",
        disclosures=[
            GRIDisclosure(code="407-1", name="Operations where freedom of association may be at risk"),
        ],
        keywords=["freedom of association", "collective bargaining", "union"],
    ),
    GRIStandard(
        code="GRI 408", name="Child Labor 2016", series="social",
        disclosures=[
            GRIDisclosure(code="408-1", name="Operations and suppliers at significant risk for child labor"),
        ],
        keywords=["child labor"],
    ),
    GRIStandard(
        code="GRI 409", name="Forced or Compulsory Labor 2016", series="social",
        disclosures=[
            GRIDisclosure(code="409-1", name="Operations and suppliers at significant risk for forced labor"),
        ],
        keywords=["forced labor", "compulsory labor", "modern slavery"],
    ),
    GRIStandard(
        code="GRI 410", name="Security Practices 2016", series="social",
        disclosures=[
            GRIDisclosure(code="410-1", name="Security personnel trained in human rights"),
        ],
        keywords=["security", "human rights training"],
    ),
    GRIStandard(
        code="GRI 411", name="Rights of Indigenous Peoples 2016", series="social",
        disclosures=[
            GRIDisclosure(code="411-1", name="Incidents of violations involving rights of indigenous peoples"),
        ],
        keywords=["indigenous", "native", "First Nations"],
    ),
    GRIStandard(
        code="GRI 413", name="Local Communities 2016", series="social",
        disclosures=[
            GRIDisclosure(code="413-1", name="Operations with community engagement and impact assessments",
                         iris_cross_refs=["OI4324"]),
            GRIDisclosure(code="413-2", name="Operations with significant negative impacts on local communities"),
        ],
        keywords=["community", "local", "engagement", "impact assessment"],
    ),
    GRIStandard(
        code="GRI 414", name="Supplier Social Assessment 2016", series="social",
        disclosures=[
            GRIDisclosure(code="414-1", name="New suppliers screened using social criteria"),
            GRIDisclosure(code="414-2", name="Negative social impacts in the supply chain"),
        ],
        keywords=["supplier", "social assessment", "supply chain"],
    ),
    GRIStandard(
        code="GRI 415", name="Public Policy 2016", series="social",
        disclosures=[
            GRIDisclosure(code="415-1", name="Political contributions"),
        ],
        keywords=["political", "lobbying", "public policy"],
    ),
    GRIStandard(
        code="GRI 416", name="Customer Health and Safety 2016", series="social",
        disclosures=[
            GRIDisclosure(code="416-1", name="Assessment of health and safety impacts of products"),
            GRIDisclosure(code="416-2", name="Incidents of non-compliance re: health and safety impacts"),
        ],
        keywords=["product safety", "customer health", "safety"],
    ),
    GRIStandard(
        code="GRI 417", name="Marketing and Labeling 2016", series="social",
        disclosures=[
            GRIDisclosure(code="417-1", name="Requirements for product and service information and labeling"),
            GRIDisclosure(code="417-2", name="Incidents of non-compliance re: product information"),
            GRIDisclosure(code="417-3", name="Incidents of non-compliance re: marketing communications"),
        ],
        keywords=["marketing", "labeling", "advertising"],
    ),
    GRIStandard(
        code="GRI 418", name="Customer Privacy 2016", series="social",
        disclosures=[
            GRIDisclosure(code="418-1", name="Substantiated complaints re: customer privacy and data breaches"),
        ],
        keywords=["privacy", "data breach", "customer data"],
    ),
]


def get_gri_standards(series: str | None = None) -> list[GRIStandard]:
    if series:
        return [s for s in GRI_STANDARDS if s.series == series]
    return GRI_STANDARDS


def match_gri_topics(
    sector: str = "",
    description: str = "",
    themes: list[str] | None = None,
) -> list[tuple[GRIStandard, float]]:
    """Match a company to the most relevant GRI topic standards.

    Returns list of (standard, score) sorted by relevance descending.
    """
    text = f"{sector} {description} {' '.join(themes or [])}".lower()
    scored: list[tuple[GRIStandard, float]] = []

    for std in GRI_STANDARDS:
        if std.series == "universal":
            continue  # universals always apply

        score = 0.0
        for kw in std.keywords:
            if kw.lower() in text:
                score += 2.0

        std_name_words = std.name.lower().split()
        for w in std_name_words:
            if len(w) > 3 and w in text:
                score += 1.0

        if score > 0:
            scored.append((std, round(score, 2)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:10]
