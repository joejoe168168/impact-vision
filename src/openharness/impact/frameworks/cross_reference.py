"""Cross-reference mapping between sustainability frameworks.

Maps equivalent metrics/disclosures across IRIS+, GRI, EDCI, SFDR PAI, and SASB.
Enables lookup in any direction: given a metric in one standard, find equivalents in others.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CrossReference(BaseModel):
    """A mapping between equivalent metrics across standards."""
    concept: str
    iris_plus: list[str] = Field(default_factory=list)
    gri: list[str] = Field(default_factory=list)
    edci: list[str] = Field(default_factory=list)
    sfdr_pai: list[int] = Field(default_factory=list)
    sasb_dimension: str = ""
    tcfd: list[str] = Field(default_factory=list)
    issb: list[str] = Field(default_factory=list)
    esrs: list[str] = Field(default_factory=list)
    sdg_goals: list[int] = Field(default_factory=list)


CROSS_REFERENCE_MAP: list[CrossReference] = [
    # Environment - GHG Emissions
    CrossReference(
        concept="GHG Emissions - Scope 1 (Direct)",
        iris_plus=["OI4112"],
        gri=["305-1"],
        edci=["EDCI-E1"],
        sfdr_pai=[1],
        sasb_dimension="Environment",
        tcfd=["MET-B"],
        issb=["S2-MT-1"],
        esrs=["E1-6"],
        sdg_goals=[13],
    ),
    CrossReference(
        concept="GHG Emissions - Scope 2 (Indirect)",
        gri=["305-2"],
        edci=["EDCI-E2"],
        sfdr_pai=[1],
        tcfd=["MET-B"],
        issb=["S2-MT-1"],
        sdg_goals=[13],
    ),
    CrossReference(
        concept="GHG Emissions - Scope 3 (Value Chain)",
        gri=["305-3"],
        edci=["EDCI-E3"],
        sfdr_pai=[1],
        tcfd=["MET-B"],
        issb=["S2-MT-1"],
        sdg_goals=[13],
    ),
    CrossReference(
        concept="Total GHG Emissions",
        iris_plus=["OI1479"],
        gri=["305-5"],
        sfdr_pai=[1, 2, 3],
        sasb_dimension="Environment",
        tcfd=["MET-B"],
        issb=["S2-MT-1"],
        sdg_goals=[13],
    ),
    CrossReference(
        concept="Carbon Footprint (Portfolio-Level)",
        sfdr_pai=[2],
        tcfd=["MET-B"],
        issb=["S2-MT-1"],
        sdg_goals=[13],
    ),
    CrossReference(
        concept="GHG Intensity",
        sfdr_pai=[3],
        gri=["305-4"],
        tcfd=["MET-B"],
        issb=["S2-MT-1"],
        sdg_goals=[13],
    ),
    # Energy
    CrossReference(
        concept="Energy Consumption",
        gri=["302-1"],
        edci=["EDCI-E5"],
        sfdr_pai=[6],
        sasb_dimension="Environment",
        esrs=["E1-5"],
        sdg_goals=[7],
    ),
    CrossReference(
        concept="Renewable Energy Share",
        edci=["EDCI-E4"],
        sfdr_pai=[5],
        gri=["302-1"],
        sdg_goals=[7],
    ),
    CrossReference(
        concept="Net Zero Commitment",
        edci=["EDCI-E6"],
        tcfd=["MET-C"],
        sdg_goals=[13],
    ),
    # Water & Waste
    CrossReference(
        concept="Water Consumption",
        gri=["303-5"],
        tcfd=["MET-A"],
        sdg_goals=[6],
    ),
    CrossReference(
        concept="Emissions to Water",
        gri=["303-4"],
        sfdr_pai=[8],
        sdg_goals=[6, 14],
    ),
    CrossReference(
        concept="Hazardous Waste",
        gri=["306-3", "306-5"],
        sfdr_pai=[9],
        sdg_goals=[12],
    ),
    # Biodiversity
    CrossReference(
        concept="Biodiversity Impact",
        gri=["304-1", "304-2"],
        sfdr_pai=[7],
        esrs=["E4-5"],
        sdg_goals=[14, 15],
    ),
    # Social - Workforce
    CrossReference(
        concept="Total Employees",
        iris_plus=["OI8869"],
        gri=["2-7", "401-1"],
        edci=["EDCI-S7"],
        sasb_dimension="Human Capital",
        esrs=["S1-6"],
        sdg_goals=[8],
    ),
    CrossReference(
        concept="Female Employees (%)",
        iris_plus=["OI6213"],
        gri=["405-1"],
        edci=["EDCI-S4"],
        sfdr_pai=[13],
        esrs=["S1-9"],
        sdg_goals=[5, 10],
    ),
    CrossReference(
        concept="Female in Management/C-Suite",
        iris_plus=["OI1571"],
        gri=["405-1"],
        edci=["EDCI-S5"],
        sdg_goals=[5],
    ),
    CrossReference(
        concept="Female on Board",
        iris_plus=["OI1075"],
        gri=["405-1"],
        edci=["EDCI-S6"],
        sfdr_pai=[13],
        sdg_goals=[5],
    ),
    CrossReference(
        concept="Gender Pay Gap / Wage Equity",
        iris_plus=["OI1582"],
        gri=["405-2"],
        edci=["EDCI-S8"],
        sfdr_pai=[12],
        esrs=["S1-16"],
        sdg_goals=[5, 8, 10],
    ),
    CrossReference(
        concept="Work-Related Injuries",
        gri=["403-9"],
        edci=["EDCI-S1", "EDCI-S2"],
        sasb_dimension="Human Capital",
        sdg_goals=[3, 8],
    ),
    CrossReference(
        concept="Employee Engagement / NPS",
        edci=["EDCI-S3"],
        sdg_goals=[8],
    ),
    # Social - Clients/Beneficiaries
    CrossReference(
        concept="Total Clients/Beneficiaries",
        iris_plus=["PI4060"],
        sasb_dimension="Social Capital",
        sdg_goals=[1, 8, 10],
    ),
    CrossReference(
        concept="Client Protection Policy",
        iris_plus=["OI4753"],
        sasb_dimension="Social Capital",
    ),
    CrossReference(
        concept="Client Feedback System",
        iris_plus=["OI5049"],
        gri=["2-25", "2-26"],
    ),
    # Governance
    CrossReference(
        concept="Board Composition/Independence",
        iris_plus=["OI1075"],
        gri=["2-9"],
        edci=["EDCI-G1"],
    ),
    CrossReference(
        concept="Data Privacy & Security",
        gri=["418-1"],
        edci=["EDCI-G2"],
        sasb_dimension="Social Capital",
    ),
    CrossReference(
        concept="ESG/Sustainability Oversight",
        gri=["2-12"],
        edci=["EDCI-G3"],
        tcfd=["GOV-A", "GOV-B"],
    ),
    CrossReference(
        concept="Anti-Corruption",
        gri=["205-1", "205-2", "205-3"],
        sasb_dimension="Leadership & Governance",
        esrs=["G1-3", "G1-4"],
    ),
    # Compliance & Norms
    CrossReference(
        concept="UNGC/OECD Compliance",
        sfdr_pai=[10, 11],
        gri=["2-23", "2-27"],
    ),
    CrossReference(
        concept="Controversial Weapons Exposure",
        sfdr_pai=[14],
    ),
    CrossReference(
        concept="Fossil Fuel Exposure",
        sfdr_pai=[4],
        sdg_goals=[7, 13],
    ),
    # Financial
    CrossReference(
        concept="Revenue / Economic Performance",
        iris_plus=["FP4761"],
        gri=["201-1"],
        sdg_goals=[8],
    ),
    CrossReference(
        concept="Revenue from Grants/Donations",
        iris_plus=["FP3021"],
    ),
    CrossReference(
        concept="Community Engagement",
        iris_plus=["OI4324"],
        gri=["413-1"],
    ),
    CrossReference(
        concept="Social & Environmental Targets",
        iris_plus=["OD4091"],
        gri=["3-3"],
        tcfd=["MET-C"],
    ),
    CrossReference(
        concept="Social & Environmental Reporting",
        iris_plus=["OI4732"],
        gri=["3-3"],
    ),
    # Supply Chain
    CrossReference(
        concept="Supplier Environmental Assessment",
        gri=["308-1", "308-2"],
        sasb_dimension="Business Model & Innovation",
    ),
    CrossReference(
        concept="Supplier Social Assessment",
        gri=["414-1", "414-2"],
        sasb_dimension="Social Capital",
    ),
    CrossReference(
        concept="Child Labor Risk",
        gri=["408-1"],
        sasb_dimension="Social Capital",
    ),
    CrossReference(
        concept="Forced Labor Risk",
        gri=["409-1"],
        sasb_dimension="Social Capital",
    ),
    CrossReference(
        concept="Local Community Impact",
        gri=["413-1", "413-2"],
        iris_plus=["OI4324"],
        sasb_dimension="Social Capital",
        sdg_goals=[11],
    ),
    CrossReference(
        concept="Living Wage / Market Presence",
        iris_plus=["OI1582"],
        gri=["202-1"],
        edci=["EDCI-S8"],
        sdg_goals=[1, 8],
    ),
    # Land Use
    CrossReference(
        concept="Land Use & Land-Use Change",
        gri=["304-1"],
        sasb_dimension="Environment",
        esrs=["E4-5"],
        sdg_goals=[15],
    ),
    # Community Development
    CrossReference(
        concept="Community Development & Investment",
        iris_plus=["OI4324"],
        gri=["203-1", "413-1"],
        sasb_dimension="Social Capital",
        esrs=["S3-4"],
        sdg_goals=[11],
    ),
    # Training & Education Outcomes
    CrossReference(
        concept="Training & Education Outcomes",
        iris_plus=["PI2998"],
        gri=["404-1", "404-2"],
        sasb_dimension="Human Capital",
        esrs=["S1-13"],
        sdg_goals=[4, 8],
    ),
    # Financial Inclusion Depth
    CrossReference(
        concept="Financial Inclusion Depth",
        iris_plus=["PI4060", "PI2740"],
        sasb_dimension="Social Capital",
        sdg_goals=[1, 8, 10],
    ),
    # Access Metrics
    CrossReference(
        concept="Access to Essential Services",
        iris_plus=["PI4060"],
        gri=["203-2"],
        sdg_goals=[1, 3, 4, 6, 7, 10],
    ),
    # Product Safety
    CrossReference(
        concept="Product Safety & Quality",
        gri=["416-1", "416-2"],
        sasb_dimension="Social Capital",
        sdg_goals=[3, 12],
    ),
    # Customer Satisfaction
    CrossReference(
        concept="Customer Satisfaction & NPS",
        iris_plus=["OI5049"],
        sasb_dimension="Social Capital",
        sdg_goals=[8],
    ),
    # SASB metric-level: Human Capital - Labor Practices
    CrossReference(
        concept="Employee Turnover Rate",
        gri=["401-1"],
        sasb_dimension="Human Capital",
        esrs=["S1-6"],
        sdg_goals=[8],
    ),
    CrossReference(
        concept="Employee Benefits & Parental Leave",
        gri=["401-2", "401-3"],
        sasb_dimension="Human Capital",
        esrs=["S1-11"],
        sdg_goals=[5, 8],
    ),
    # SASB: Business Model & Innovation
    CrossReference(
        concept="Product Design for Sustainability",
        gri=["301-1", "301-2"],
        sasb_dimension="Business Model & Innovation",
        esrs=["E5-4"],
        sdg_goals=[12],
    ),
    CrossReference(
        concept="Product Lifecycle Management",
        gri=["301-3"],
        sasb_dimension="Business Model & Innovation",
        esrs=["E5-5"],
        sdg_goals=[12],
    ),
    # GRI expansion: tax & economic impact
    CrossReference(
        concept="Tax Transparency",
        gri=["207-1", "207-4"],
        sasb_dimension="Leadership & Governance",
        esrs=["G1-4"],
        sdg_goals=[16, 17],
    ),
    CrossReference(
        concept="Indirect Economic Impact",
        gri=["203-2"],
        iris_plus=["OI4324"],
        sdg_goals=[1, 8, 10],
    ),
    CrossReference(
        concept="Non-Discrimination",
        gri=["406-1"],
        sasb_dimension="Human Capital",
        esrs=["S1-9"],
        sdg_goals=[5, 10],
    ),
    CrossReference(
        concept="Freedom of Association",
        gri=["407-1"],
        sasb_dimension="Human Capital",
        sfdr_pai=[11],
        sdg_goals=[8],
    ),
    CrossReference(
        concept="Indigenous Peoples' Rights",
        gri=["411-1"],
        sasb_dimension="Social Capital",
        sdg_goals=[10, 16],
    ),
    CrossReference(
        concept="Human Rights Assessment",
        gri=["412-1", "412-2"],
        sfdr_pai=[10, 11],
        esrs=["S1-1"],
        sdg_goals=[16],
    ),
    CrossReference(
        concept="Marketing & Labeling",
        gri=["417-1", "417-2"],
        sasb_dimension="Social Capital",
        sdg_goals=[12],
    ),
]

# Build reverse-lookup indexes
_iris_index: dict[str, list[CrossReference]] = {}
_gri_index: dict[str, list[CrossReference]] = {}
_edci_index: dict[str, list[CrossReference]] = {}
_sfdr_index: dict[int, list[CrossReference]] = {}
_concept_index: dict[str, CrossReference] = {}

for _xref in CROSS_REFERENCE_MAP:
    _concept_index[_xref.concept.lower()] = _xref
    for _id in _xref.iris_plus:
        _iris_index.setdefault(_id, []).append(_xref)
    for _id in _xref.gri:
        _gri_index.setdefault(_id, []).append(_xref)
    for _id in _xref.edci:
        _edci_index.setdefault(_id, []).append(_xref)
    for _num in _xref.sfdr_pai:
        _sfdr_index.setdefault(_num, []).append(_xref)


def lookup_by_iris(metric_id: str) -> list[CrossReference]:
    return _iris_index.get(metric_id, [])


def lookup_by_gri(disclosure_code: str) -> list[CrossReference]:
    return _gri_index.get(disclosure_code, [])


def lookup_by_edci(metric_id: str) -> list[CrossReference]:
    return _edci_index.get(metric_id, [])


def lookup_by_sfdr(indicator_number: int) -> list[CrossReference]:
    return _sfdr_index.get(indicator_number, [])


def search_cross_references(query: str) -> list[CrossReference]:
    """Search cross-references by concept name."""
    q = query.lower()
    return [xref for xref in CROSS_REFERENCE_MAP if q in xref.concept.lower()]


def get_all_cross_references() -> list[CrossReference]:
    return CROSS_REFERENCE_MAP


def format_cross_reference(xref: CrossReference) -> str:
    """Format a cross-reference for display."""
    parts = [f"[{xref.concept}]"]
    if xref.iris_plus:
        parts.append(f"  IRIS+: {', '.join(xref.iris_plus)}")
    if xref.gri:
        parts.append(f"  GRI: {', '.join(xref.gri)}")
    if xref.edci:
        parts.append(f"  EDCI: {', '.join(xref.edci)}")
    if xref.sfdr_pai:
        parts.append(f"  SFDR PAI: {', '.join(f'#{n}' for n in xref.sfdr_pai)}")
    if xref.tcfd:
        parts.append(f"  TCFD: {', '.join(xref.tcfd)}")
    if xref.issb:
        parts.append(f"  ISSB: {', '.join(xref.issb)}")
    if xref.esrs:
        parts.append(f"  ESRS: {', '.join(xref.esrs)}")
    if xref.sasb_dimension:
        parts.append(f"  SASB: {xref.sasb_dimension}")
    if xref.sdg_goals:
        parts.append(f"  SDGs: {', '.join(f'{g}' for g in xref.sdg_goals)}")
    return "\n".join(parts)
