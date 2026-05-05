"""Cross-reference mapping between sustainability frameworks.

Maps equivalent metrics/disclosures across IRIS+, GRI, EDCI, SFDR PAI, and SASB.
Enables lookup in any direction: given a metric in one standard, find equivalents in others.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CrossReference(BaseModel):
    """A mapping between equivalent metrics across standards.

    For SASB, both `sasb_dimension` (the broad pillar) and `sasb_codes` (the
    actual SASB metric codes, e.g. `FN-CB-230a.1`) are stored so reverse-lookup
    by SASB metric code works.
    """
    concept: str
    iris_plus: list[str] = Field(default_factory=list)
    gri: list[str] = Field(default_factory=list)
    edci: list[str] = Field(default_factory=list)
    sfdr_pai: list[int] = Field(default_factory=list)
    sasb_dimension: str = ""
    sasb_codes: list[str] = Field(default_factory=list)
    tnfd: list[str] = Field(default_factory=list)
    pcaf: list[str] = Field(default_factory=list)
    eu_taxonomy: list[str] = Field(default_factory=list)
    cdp: list[str] = Field(default_factory=list)
    sbti: list[str] = Field(default_factory=list)
    tcfd: list[str] = Field(default_factory=list)
    issb: list[str] = Field(default_factory=list)
    esrs: list[str] = Field(default_factory=list)
    sdg_goals: list[int] = Field(default_factory=list)
    mapping_confidence: Literal["direct", "partial", "proxy", "conceptual"] = "direct"
    mapping_basis: Literal["metric", "disclosure", "conceptual", "proxy"] = "conceptual"
    confidence: Literal["high", "medium", "low"] = "medium"
    source_url: str = ""
    notes: str = ""


CROSS_REFERENCE_MAP: list[CrossReference] = [
    # Environment - GHG Emissions
    CrossReference(
        concept="GHG Emissions - Scope 1 (Direct)",
        iris_plus=["OI4112"],
        gri=["305-1"],
        edci=["EDCI-E1"],
        sfdr_pai=[1],
        sasb_dimension="Environment",
        sasb_codes=["EM-EP-110a.1", "FN-CB-410a.2", "RT-CH-110a.1", "EM-MM-110a.1"],
        tcfd=["MET-B"],
        tnfd=["TNFD-MET-CR-1"],
        pcaf=["PCAF-Asset-Class-Listed-Equity-Scope1"],
        cdp=["CDP-Climate-C6.1"],
        sbti=["SBTi-Scope1-Target"],
        issb=["S2-MT-1"],
        esrs=["E1-6"],
        sdg_goals=[13],
    ),
    CrossReference(
        concept="GHG Emissions - Scope 2 (Indirect)",
        gri=["305-2"],
        edci=["EDCI-E2"],
        sfdr_pai=[1],
        sasb_codes=["EM-EP-110a.1", "RT-CH-110a.1"],
        tcfd=["MET-B"],
        pcaf=["PCAF-Asset-Class-Listed-Equity-Scope2"],
        cdp=["CDP-Climate-C6.3"],
        sbti=["SBTi-Scope2-Target"],
        issb=["S2-MT-1"],
        sdg_goals=[13],
    ),
    CrossReference(
        concept="GHG Emissions - Scope 3 (Value Chain)",
        gri=["305-3"],
        edci=["EDCI-E3"],
        sfdr_pai=[1],
        sasb_codes=["EM-EP-110a.1"],
        tcfd=["MET-B"],
        pcaf=["PCAF-Cat15-Financed-Emissions"],
        cdp=["CDP-Climate-C6.5"],
        sbti=["SBTi-Scope3-Target"],
        issb=["S2-MT-1"],
        sdg_goals=[13],
    ),
    CrossReference(
        concept="Total GHG Emissions",
        iris_plus=["OI1479"],
        gri=["305-5"],
        sfdr_pai=[1, 2, 3],
        sasb_dimension="Environment",
        sasb_codes=["EM-EP-110a.1"],
        tcfd=["MET-B"],
        pcaf=["PCAF-Total-Financed-Emissions"],
        cdp=["CDP-Climate-C6"],
        sbti=["SBTi-Net-Zero"],
        issb=["S2-MT-1"],
        esrs=["E1-6"],
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
        sfdr_pai=[6],
        sasb_dimension="Environment",
        sasb_codes=["EM-EP-130a.1", "RT-CH-130a.1", "RT-EE-130a.1"],
        eu_taxonomy=["Annex-I-7.1-Energy-Use"],
        cdp=["CDP-Climate-C8"],
        esrs=["E1-5"],
        sdg_goals=[7],
    ),
    CrossReference(
        concept="Renewable Energy Share",
        edci=["EDCI-E7"],
        sfdr_pai=[5],
        gri=["302-1"],
        sasb_codes=["IF-EU-000.D"],
        eu_taxonomy=["Annex-I-4.1-Renewable-Generation"],
        cdp=["CDP-Climate-C8.2"],
        sdg_goals=[7],
    ),
    CrossReference(
        concept="Net Zero Commitment",
        edci=["EDCI-E5", "EDCI-E6"],
        tcfd=["MET-C"],
        sbti=["SBTi-Net-Zero", "SBTi-1.5C-Aligned"],
        cdp=["CDP-Climate-C4.1"],
        sdg_goals=[13],
    ),
    # Water & Waste
    CrossReference(
        concept="Water Consumption",
        gri=["303-5"],
        tcfd=["MET-A"],
        sasb_codes=["EM-EP-140a.1", "FB-AG-140a.1", "RT-CH-140a.1"],
        cdp=["CDP-Water-W1.2"],
        tnfd=["TNFD-MET-WT-1"],
        sdg_goals=[6],
    ),
    CrossReference(
        concept="Emissions to Water",
        gri=["303-4"],
        sfdr_pai=[8],
        sasb_codes=["EM-EP-140a.2", "RT-CH-150a.1"],
        cdp=["CDP-Water-W1.4"],
        tnfd=["TNFD-MET-WT-2"],
        sdg_goals=[6, 14],
    ),
    CrossReference(
        concept="Hazardous Waste",
        gri=["306-3", "306-5"],
        sfdr_pai=[9],
        sasb_codes=["EM-EP-150a.1", "RT-CH-150a.1"],
        sdg_goals=[12],
    ),
    # Biodiversity
    CrossReference(
        concept="Biodiversity Impact",
        gri=["304-1", "304-2"],
        sfdr_pai=[7],
        sasb_codes=["EM-MM-160a.1", "FB-AG-440a.1"],
        tnfd=["TNFD-MET-BIO-1", "TNFD-LEAP-Locate"],
        esrs=["E4-5"],
        sdg_goals=[14, 15],
    ),
    # Deforestation
    CrossReference(
        concept="Deforestation / Land Conversion",
        gri=["304-3"],
        sfdr_pai=[19],
        tnfd=["TNFD-LEAP-Evaluate"],
        cdp=["CDP-Forests-F4"],
        sdg_goals=[13, 15],
    ),
    # EU Taxonomy alignment
    CrossReference(
        concept="EU Taxonomy Alignment Percentage",
        eu_taxonomy=["Annex-V-Disclosure-CapEx", "Annex-V-Disclosure-OpEx", "Annex-V-Disclosure-Turnover"],
        esrs=["E1-1"],
        sdg_goals=[13],
    ),
    # Social - Workforce
    CrossReference(
        concept="Total Employees",
        iris_plus=["OI8869"],
        gri=["2-7", "401-1"],
        sasb_dimension="Human Capital",
        sasb_codes=["FN-CB-000.B", "RT-CH-000.B"],
        esrs=["S1-6"],
        sdg_goals=[8],
        mapping_confidence="proxy",
        notes="EDCI 2026 tracks net new hires and turnover, not total employee headcount.",
    ),
    CrossReference(
        concept="Female Employees (%)",
        iris_plus=["OI6213"],
        gri=["405-1"],
        sfdr_pai=[13],
        sasb_codes=["FN-CB-330a.1"],
        esrs=["S1-9"],
        sdg_goals=[5, 10],
        mapping_confidence="proxy",
        notes="EDCI 2026 diversity fields cover women on board, women in C-suite, and under-represented groups.",
    ),
    CrossReference(
        concept="Female in Management/C-Suite",
        iris_plus=["OI1571"],
        gri=["405-1"],
        edci=["EDCI-S6"],
        sdg_goals=[5],
    ),
    CrossReference(
        concept="Female on Board",
        iris_plus=["OI1075"],
        gri=["405-1"],
        edci=["EDCI-S4"],
        sfdr_pai=[13],
        sdg_goals=[5],
    ),
    CrossReference(
        concept="Gender Pay Gap / Wage Equity",
        iris_plus=["OI1582"],
        gri=["405-2"],
        sfdr_pai=[12, 23],
        sasb_codes=["FN-CB-330a.1"],
        esrs=["S1-16"],
        sdg_goals=[5, 8, 10],
        mapping_confidence="proxy",
        notes="EDCI 2026 diversity fields do not include gender pay gap.",
    ),
    CrossReference(
        concept="Work-Related Injuries",
        gri=["403-9"],
        edci=["EDCI-S1", "EDCI-S2", "EDCI-S3"],
        sasb_dimension="Human Capital",
        sasb_codes=["EM-EP-320a.1", "RT-CH-320a.1", "EM-MM-320a.1"],
        esrs=["S1-14"],
        sdg_goals=[3, 8],
    ),
    CrossReference(
        concept="Employee Engagement / NPS",
        edci=["EDCI-S9", "EDCI-S10", "EDCI-S11"],
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
        edci=["EDCI-S4"],
        mapping_confidence="proxy",
        notes="EDCI diversity captures women on board, not board independence.",
    ),
    CrossReference(
        concept="Data Privacy & Security",
        gri=["418-1"],
        edci=["EDCI-G1"],
        sasb_dimension="Social Capital",
        mapping_confidence="proxy",
        notes="EDCI 2026 maps this concept narrowly to cybersecurity testing.",
    ),
    CrossReference(
        concept="ESG/Sustainability Oversight",
        gri=["2-12"],
        tcfd=["GOV-A", "GOV-B"],
        mapping_confidence="proxy",
        notes="EDCI 2026 public KPI categories do not include board ESG oversight.",
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
        sdg_goals=[1, 8],
        mapping_confidence="proxy",
        notes="Living wage is an adjacent ESG datapoint, not an EDCI 2026 KPI category.",
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
        iris_plus=["PI4060", "PI3193", "PI4237"],
        sasb_dimension="Social Capital",
        sdg_goals=[1, 8, 10],
        mapping_confidence="proxy",
        notes=(
            "Uses current IRIS+ client total and underserved-client disaggregations; "
            "the older poverty-client reference is not present in the bundled 5.3c catalog."
        ),
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
        edci=["EDCI-S8"],
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
_sasb_index: dict[str, list[CrossReference]] = {}
_tnfd_index: dict[str, list[CrossReference]] = {}
_pcaf_index: dict[str, list[CrossReference]] = {}
_eutax_index: dict[str, list[CrossReference]] = {}
_cdp_index: dict[str, list[CrossReference]] = {}
_sbti_index: dict[str, list[CrossReference]] = {}
_issb_index: dict[str, list[CrossReference]] = {}
_esrs_index: dict[str, list[CrossReference]] = {}
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
    for _id in _xref.sasb_codes:
        _sasb_index.setdefault(_id.upper(), []).append(_xref)
    for _id in _xref.tnfd:
        _tnfd_index.setdefault(_id, []).append(_xref)
    for _id in _xref.pcaf:
        _pcaf_index.setdefault(_id, []).append(_xref)
    for _id in _xref.eu_taxonomy:
        _eutax_index.setdefault(_id, []).append(_xref)
    for _id in _xref.cdp:
        _cdp_index.setdefault(_id, []).append(_xref)
    for _id in _xref.sbti:
        _sbti_index.setdefault(_id, []).append(_xref)
    for _id in _xref.issb:
        _issb_index.setdefault(_id, []).append(_xref)
    for _id in _xref.esrs:
        _esrs_index.setdefault(_id, []).append(_xref)


def lookup_by_iris(metric_id: str) -> list[CrossReference]:
    return _iris_index.get(metric_id, [])


def lookup_by_gri(disclosure_code: str) -> list[CrossReference]:
    return _gri_index.get(disclosure_code, [])


def lookup_by_edci(metric_id: str) -> list[CrossReference]:
    return _edci_index.get(metric_id, [])


def lookup_by_sfdr(indicator_number: int) -> list[CrossReference]:
    return _sfdr_index.get(indicator_number, [])


def lookup_by_sasb(code: str) -> list[CrossReference]:
    """Lookup by a specific SASB metric code (e.g. 'FN-CB-230a.1')."""
    return _sasb_index.get(code.upper(), [])


def lookup_by_tnfd(code: str) -> list[CrossReference]:
    return _tnfd_index.get(code, [])


def lookup_by_pcaf(code: str) -> list[CrossReference]:
    return _pcaf_index.get(code, [])


def lookup_by_eu_taxonomy(code: str) -> list[CrossReference]:
    return _eutax_index.get(code, [])


def lookup_by_cdp(code: str) -> list[CrossReference]:
    return _cdp_index.get(code, [])


def lookup_by_sbti(code: str) -> list[CrossReference]:
    return _sbti_index.get(code, [])


def lookup_by_issb(code: str) -> list[CrossReference]:
    return _issb_index.get(code, [])


def lookup_by_esrs(code: str) -> list[CrossReference]:
    return _esrs_index.get(code, [])


def search_cross_references(query: str) -> list[CrossReference]:
    """Search cross-references by concept name."""
    q = query.lower()
    return [xref for xref in CROSS_REFERENCE_MAP if q in xref.concept.lower()]


def get_all_cross_references() -> list[CrossReference]:
    return CROSS_REFERENCE_MAP


def format_cross_reference(xref: CrossReference) -> str:
    """Format a cross-reference for display."""
    parts = [f"[{xref.concept}]"]
    if xref.mapping_confidence != "direct":
        parts.append(f"  Mapping confidence: {xref.mapping_confidence}")
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
    if xref.sasb_dimension or xref.sasb_codes:
        sasb_parts = []
        if xref.sasb_dimension:
            sasb_parts.append(xref.sasb_dimension)
        if xref.sasb_codes:
            sasb_parts.append(", ".join(xref.sasb_codes))
        parts.append(f"  SASB: {' / '.join(sasb_parts)}")
    if xref.tnfd:
        parts.append(f"  TNFD: {', '.join(xref.tnfd)}")
    if xref.pcaf:
        parts.append(f"  PCAF: {', '.join(xref.pcaf)}")
    if xref.eu_taxonomy:
        parts.append(f"  EU Taxonomy: {', '.join(xref.eu_taxonomy)}")
    if xref.cdp:
        parts.append(f"  CDP: {', '.join(xref.cdp)}")
    if xref.sbti:
        parts.append(f"  SBTi: {', '.join(xref.sbti)}")
    if xref.sdg_goals:
        parts.append(f"  SDGs: {', '.join(f'{g}' for g in xref.sdg_goals)}")
    if xref.notes:
        parts.append(f"  Notes: {xref.notes}")
    return "\n".join(parts)
