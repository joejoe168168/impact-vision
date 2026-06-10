"""Static registry for the ohESG-inspired ESG toolbox modules."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from openharness.impact.toolbox.models import (
    CalculatorMethod,
    RequirementItem,
    SourceRecord,
    ToolboxCategory,
    ToolboxSourceIndexRecord,
    ToolboxSourceProfile,
    ToolboxToolSpec,
)


TOOLBOX_CATEGORIES: dict[str, str] = {
    "disclosure": "Sustainability disclosure standards and reporting preparation",
    "rating": "ESG rating, questionnaire, and audit readiness",
    "export": "Export-market sustainability compliance",
    "supplier": "Supply-chain ESG and due-diligence preparation",
    "carbon": "Carbon accounting, target-setting, and product carbon compliance",
}

OHESG_BASE = "https://tool.ohesg.com"
_SNAPSHOT_PATH = Path(__file__).resolve().parents[4] / "data" / "raw" / "ohesg_toolbox_snapshot.json"
_SOURCE_PROFILE_DIR = Path(__file__).resolve().parents[4] / "data" / "raw" / "ohesg_toolbox"


def _load_ohesg_landing_tools() -> dict[str, dict[str, object]]:
    try:
        snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    tools = snapshot.get("tools", [])
    if not isinstance(tools, list):
        return {}
    return {
        str(tool.get("tool_id", "")): tool
        for tool in tools
        if isinstance(tool, dict) and tool.get("tool_id")
    }


_OHESG_LANDING_TOOLS = _load_ohesg_landing_tools()


def _load_ohesg_pages() -> dict[str, dict[str, object]]:
    try:
        snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    pages = snapshot.get("pages", {})
    if not isinstance(pages, dict):
        return {}
    return {str(tool_id): page for tool_id, page in pages.items() if isinstance(page, dict)}


_OHESG_PAGES = _load_ohesg_pages()


def _load_ohesg_source_profiles() -> dict[str, ToolboxSourceProfile]:
    profiles: dict[str, ToolboxSourceProfile] = {}
    if not _SOURCE_PROFILE_DIR.exists():
        return profiles
    for path in sorted(_SOURCE_PROFILE_DIR.glob("*.json")):
        try:
            profile = ToolboxSourceProfile.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        profiles[profile.tool_id] = profile
    return profiles


_OHESG_SOURCE_PROFILES = _load_ohesg_source_profiles()


def _ohesg(path: str) -> SourceRecord:
    return SourceRecord(
        title="ohESG ESG Practice Toolbox",
        url=f"{OHESG_BASE}{path}",
        source_type="secondary",
        publisher="ohESG",
        as_of="2026-06-06",
        notes="Curated secondary quick-reference used for discovery and structure.",
    )


def _official(title: str, url: str, publisher: str, *, source_type: str = "official") -> SourceRecord:
    return SourceRecord(title=title, url=url, source_type=source_type, publisher=publisher, as_of="2026-06-06")


COMMON_DISCLOSURE_REQS = [
    RequirementItem(
        id="governance",
        title="Governance ownership",
        description="Board or management ownership of the sustainability topic is identified.",
        keywords=["board", "governance", "committee", "oversight", "management"],
        evidence_examples=["Board charter", "ESG committee minutes", "management responsibility matrix"],
    ),
    RequirementItem(
        id="strategy",
        title="Strategy and business model connection",
        description="The topic is linked to strategy, risks, opportunities, and business model effects.",
        keywords=["strategy", "business model", "risk", "opportunity", "transition plan"],
        evidence_examples=["Strategy memo", "risk register", "transition plan"],
    ),
    RequirementItem(
        id="metrics-targets",
        title="Metrics and targets",
        description="Quantitative metrics, boundaries, baselines, and targets are available.",
        keywords=["metric", "target", "baseline", "kpi", "scope", "intensity"],
        evidence_examples=["KPI table", "target register", "assured data extract"],
    ),
]

COMMON_RATING_REQS = [
    RequirementItem(
        id="policies",
        title="Policy documents",
        description="Current policies cover the rating or audit themes.",
        keywords=["policy", "code of conduct", "procedure", "standard operating"],
        evidence_examples=["Environmental policy", "labor policy", "supplier code of conduct"],
    ),
    RequirementItem(
        id="actions",
        title="Implementation evidence",
        description="Procedures, training, controls, and operational records evidence implementation.",
        keywords=["training", "procedure", "audit", "corrective action", "control"],
        evidence_examples=["Training logs", "audit reports", "CAPA tracker"],
    ),
    RequirementItem(
        id="results",
        title="Performance results",
        description="Recent KPIs and incidents are tracked and explainable.",
        keywords=["kpi", "incident", "performance", "score", "result"],
        evidence_examples=["KPI dashboard", "incident register", "management review"],
    ),
]

COMMON_EXPORT_REQS = [
    RequirementItem(
        id="applicability",
        title="Applicability screen",
        description="Products, country, thresholds, and value-chain role are checked against the regulation.",
        keywords=["product", "country", "threshold", "import", "export", "cn code", "hs code"],
        evidence_examples=["Product code list", "export destination list", "customer role map"],
    ),
    RequirementItem(
        id="technical-data",
        title="Technical data pack",
        description="Product, emissions, origin, traceability, or due-diligence data is available as required.",
        keywords=["emissions", "origin", "traceability", "bill of materials", "supplier"],
        evidence_examples=["Product carbon footprint", "bill of materials", "supplier declaration"],
    ),
    RequirementItem(
        id="filing-deadline",
        title="Filing and deadline owner",
        description="Reporting calendar, accountable owner, and customer/regulator workflow are defined.",
        keywords=["deadline", "declaration", "filing", "owner", "calendar"],
        evidence_examples=["Compliance calendar", "filing responsibility matrix", "customer data request workflow"],
    ),
]

COMMON_CARBON_REQS = [
    RequirementItem(
        id="boundary",
        title="Inventory boundary",
        description="Organizational and operational boundaries are documented.",
        keywords=["boundary", "operational control", "equity share", "scope 1", "scope 2", "scope 3"],
        evidence_examples=["GHG inventory boundary memo", "entity list", "scope matrix"],
        framework_refs=["GHG Protocol", "ISO 14064-1"],
    ),
    RequirementItem(
        id="activity-data",
        title="Activity data and emission factors",
        description="Activity data and emission factors are traceable to source and version.",
        keywords=["activity data", "emission factor", "fuel", "electricity", "supplier-specific"],
        evidence_examples=["Fuel invoices", "electricity bills", "emission-factor catalog"],
        framework_refs=["GHG Protocol", "ISO 14064-1"],
    ),
    RequirementItem(
        id="assurance",
        title="Calculation review or assurance",
        description="Calculations are reviewed, reconciled, and ready for assurance where needed.",
        keywords=["assurance", "verification", "reconciliation", "review", "calculation"],
        evidence_examples=["Calculation workbook", "assurance statement", "QA log"],
    ),
]


def _reqs(*groups: Iterable[RequirementItem]) -> list[RequirementItem]:
    out: list[RequirementItem] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item.id not in seen:
                seen.add(item.id)
                out.append(item)
    return out


def _method(
    method_id: str,
    name: str,
    formula: str,
    inputs: list[str],
    outputs: list[str],
    source_url: str,
) -> CalculatorMethod:
    return CalculatorMethod(
        id=method_id,
        name=name,
        formula=formula,
        inputs=inputs,
        outputs=outputs,
        source_url=source_url,
    )


TOOLBOX_TOOLS: tuple[ToolboxToolSpec, ...] = (
    ToolboxToolSpec(
        tool_id="carbon-calculator",
        title="Carbon Calculator",
        description=(
            "General manufacturing carbon calculator for Scope 1 direct emissions, "
            "Scope 2 purchased energy, and selected manufacturing Scope 3 categories, "
            "based on the ohESG calculator structure, ISO 14064-1, and GHG Protocol concepts."
        ),
        url=f"{OHESG_BASE}/carbon-calculator/",
        categories=["carbon"],
        tags=[
            "carbon accounting",
            "GHG",
            "ISO 14064-1",
            "Scope 1",
            "Scope 2",
            "Scope 3",
            "manufacturing",
        ],
        aliases=["carbon calculator", "emissions calculator", "碳计算器", "manufacturing carbon calculator"],
        sectors=["manufacturing"],
        supported_actions=["get", "checklist", "assess", "methodology", "crosswalk"],
        requirements=_reqs(COMMON_CARBON_REQS, [
            RequirementItem(
                id="scope1-categories",
                title="Scope 1 source categories",
                description=(
                    "Stationary combustion, mobile combustion, process emissions, and fugitive "
                    "emissions are separately captured with activity data and factor basis."
                ),
                keywords=[
                    "stationary combustion",
                    "mobile combustion",
                    "process emissions",
                    "fugitive emissions",
                    "refrigerant",
                    "fuel",
                    "boiler",
                    "vehicle",
                ],
                evidence_examples=[
                    "Fuel purchase records",
                    "Vehicle fuel logs",
                    "Process emissions factor memo",
                    "Refrigerant top-up and leakage records",
                ],
                framework_refs=["GHG Protocol Corporate Standard", "ISO 14064-1"],
            ),
            RequirementItem(
                id="scope2-dual-reporting",
                title="Scope 2 location and market data",
                description=(
                    "Purchased electricity, heat, steam, and cooling are captured; renewable certificates "
                    "are assessed against Scope 2 quality criteria before market-based claims."
                ),
                keywords=[
                    "purchased electricity",
                    "location-based",
                    "market-based",
                    "green certificate",
                    "renewable energy certificate",
                    "steam",
                    "heat",
                    "cooling",
                ],
                evidence_examples=[
                    "Electricity bills in MWh or kWh",
                    "Supplier-specific emission factor",
                    "Renewable certificate register",
                    "District heating invoices",
                ],
                framework_refs=["GHG Protocol Scope 2 Guidance"],
            ),
            RequirementItem(
                id="scope3-manufacturing",
                title="Manufacturing Scope 3 categories",
                description=(
                    "Purchased goods and services, fuel and energy related activities, upstream and "
                    "downstream transport, and waste generated in operations are screened for materiality."
                ),
                keywords=[
                    "purchased goods",
                    "spend",
                    "naics",
                    "transport",
                    "distribution",
                    "waste",
                    "t&d loss",
                    "scope 3",
                ],
                evidence_examples=[
                    "Procurement spend by category",
                    "Freight tonne-km data",
                    "Waste disposal records",
                    "Transmission and distribution loss assumption",
                ],
                framework_refs=["GHG Protocol Scope 3 Standard"],
            ),
            RequirementItem(
                id="results-intensity-trend",
                title="Results, intensity, and trend outputs",
                description=(
                    "Scope totals, Scope 2 location/market alternatives, carbon intensity, and at least "
                    "three years of trend data are available for reporting review."
                ),
                keywords=["scope total", "carbon footprint", "intensity", "trend", "three years", "tco2e"],
                evidence_examples=[
                    "Scope 1/2/3 summary table",
                    "Revenue intensity calculation",
                    "Three-year emissions trend",
                ],
                framework_refs=["GHG Protocol Corporate Standard", "ISO 14064-1"],
            ),
        ]),
        methods=[
            CalculatorMethod(
                id="activity-factor",
                name="Activity data multiplied by emission factor",
                formula="emissions_tco2e = activity_data * emission_factor",
                inputs=["activity_data", "emission_factor", "unit"],
                outputs=["emissions_tco2e"],
                source_url="https://ghgprotocol.org/calculation-tools-faq",
            ),
            CalculatorMethod(
                id="stationary-combustion-energy",
                name="Stationary combustion energy conversion",
                formula="emissions_tco2e = fuel_quantity * net_calorific_value_gj_per_unit * emission_factor_tco2e_per_gj",
                inputs=["fuel_quantity", "net_calorific_value", "emission_factor"],
                outputs=["stationary_combustion_tco2e"],
                source_url="https://ghgprotocol.org/calculation-tools",
            ),
            CalculatorMethod(
                id="fugitive-gwp",
                name="Fugitive emissions GWP conversion",
                formula="emissions_tco2e = leaked_gas_mass_tonnes * gwp_factor",
                inputs=["leaked_gas_mass", "gwp_factor"],
                outputs=["fugitive_emissions_tco2e"],
                source_url="https://www.iso.org/standard/66453.html",
            ),
            CalculatorMethod(
                id="scope2-location-market",
                name="Scope 2 location-based and market-based reporting",
                formula="scope2_tco2e = purchased_energy_mwh * applicable_emission_factor_tco2e_per_mwh",
                inputs=["purchased_energy_mwh", "grid_average_factor", "supplier_or_certificate_factor"],
                outputs=["scope2_location_tco2e", "scope2_market_tco2e"],
                source_url="https://ghgprotocol.org/scope-2-guidance",
            ),
        ],
        sources=[
            _ohesg("/carbon-calculator/"),
            _official("GHG Protocol Corporate Standard", "https://ghgprotocol.org/corporate-standard", "GHG Protocol", source_type="guidance"),
            _official("GHG Protocol Calculation Tools and Guidance", "https://ghgprotocol.org/calculation-tools", "GHG Protocol", source_type="guidance"),
            _official("GHG Protocol Standards and Guidance", "https://ghgprotocol.org/standards-guidance", "GHG Protocol", source_type="guidance"),
            _official("ISO 14064-1 overview", "https://www.iso.org/standard/66453.html", "ISO", source_type="methodology"),
        ],
    ),
    ToolboxToolSpec(
        tool_id="material",
        title="Double Materiality Assessment",
        description="Impact and financial materiality assessment workflow for sustainability reporting.",
        url=f"{OHESG_BASE}/material/",
        categories=["disclosure"],
        tags=["GRI", "double materiality", "CSRD"],
        aliases=["materiality", "double materiality"],
        requirements=_reqs(COMMON_DISCLOSURE_REQS, [
            RequirementItem(id="stakeholders", title="Stakeholder inputs", description="Affected stakeholders and users of sustainability information are identified and consulted through surveys, interviews, or workshops, and their input is traceable to topic scoring.", keywords=["stakeholder", "survey", "interview", "consultation"], evidence_examples=["Stakeholder map", "survey results"], framework_refs=["ESRS 1", "GRI 3"]),
            RequirementItem(id="matrix", title="Materiality matrix", description="Impact and financial materiality scores are combined into a prioritized topic matrix with documented thresholds for what counts as material.", keywords=["matrix", "financial materiality", "impact materiality"], evidence_examples=["Materiality scoring workbook"], framework_refs=["ESRS 1", "IFRS S1"]),
        ]),
        sources=[_ohesg("/material/"), _official("EFRAG ESRS Set 1", "https://www.efrag.org/en/sustainability-reporting/esrs-workstreams/sector-agnostic-standards-set-1-esrs", "EFRAG")],
    ),
    ToolboxToolSpec(
        tool_id="msci",
        title="MSCI ESG Rating Assistant",
        description="Industry key-issue readiness for MSCI ESG rating response preparation.",
        url=f"{OHESG_BASE}/msci/",
        categories=["rating"],
        tags=["MSCI", "ESG rating"],
        aliases=["msci esg"],
        requirements=COMMON_RATING_REQS,
        sources=[_ohesg("/msci/"), _official("MSCI ESG Ratings methodology", "https://www.msci.com/our-solutions/esg-investing/esg-ratings", "MSCI", source_type="methodology")],
    ),
    ToolboxToolSpec(
        tool_id="ecovadis",
        title="EcoVadis Rating Assistant",
        description="EcoVadis readiness across environment, labor and human rights, ethics, and sustainable procurement themes.",
        url=f"{OHESG_BASE}/ecovadis/",
        categories=["rating", "supplier"],
        tags=["EcoVadis", "supplier ESG", "ESG rating"],
        aliases=["ecovadis"],
        requirements=_reqs(COMMON_RATING_REQS, [
            RequirementItem(id="environment", title="Environment theme", description="Energy, GHG, water, pollution, biodiversity, waste, and product-lifecycle evidence covers the EcoVadis Environment theme for the assessed scope.", keywords=["energy", "ghg", "water", "biodiversity", "waste"], evidence_examples=["Environmental KPIs", "ISO 14001 certificate"], framework_refs=["EcoVadis methodology"]),
            RequirementItem(id="labor-human-rights", title="Labor and human rights theme", description="Health and safety, working conditions, social dialogue, career management, child/forced labor, and diversity evidence covers the Labor & Human Rights theme.", keywords=["health and safety", "working conditions", "social dialogue", "human rights"], evidence_examples=["OHS records", "employee handbook"], framework_refs=["EcoVadis methodology", "ILO conventions"]),
            RequirementItem(id="ethics", title="Ethics theme", description="Anti-corruption, anti-competitive practices, responsible information management, and data privacy controls cover the Ethics theme.", keywords=["anti-corruption", "competition", "information security", "privacy"], evidence_examples=["Anti-corruption policy", "privacy controls"], framework_refs=["EcoVadis methodology"]),
            RequirementItem(id="sustainable-procurement", title="Sustainable procurement theme", description="Supplier environmental and social practices are managed through a supplier code, risk-based selection, contractual clauses, and supplier audits or assessments.", keywords=["supplier", "procurement", "sourcing", "supplier audit"], evidence_examples=["Supplier code", "supplier audit results"], framework_refs=["EcoVadis methodology"]),
        ]),
        sources=[_ohesg("/ecovadis/"), _official("EcoVadis methodology", "https://support.ecovadis.com/hc/en-us/articles/115002531507-What-is-the-EcoVadis-methodology", "EcoVadis", source_type="methodology")],
    ),
    ToolboxToolSpec(tool_id="cdp", title="CDP Rating Assistant", description="CDP questionnaire module and scoring readiness.", url=f"{OHESG_BASE}/cdp/", categories=["rating"], tags=["CDP", "climate disclosure"], aliases=["cdp"], requirements=_reqs(COMMON_RATING_REQS, COMMON_CARBON_REQS), sources=[_ohesg("/cdp/"), _official("CDP guidance", "https://www.cdp.net/en/guidance", "CDP", source_type="guidance")]),
    ToolboxToolSpec(tool_id="csa", title="S&P Global CSA Assistant", description="S&P Global Corporate Sustainability Assessment topic and disclosure readiness.", url=f"{OHESG_BASE}/csa/", categories=["rating"], tags=["CSA", "S&P Global"], aliases=["sp csa", "corporate sustainability assessment"], requirements=COMMON_RATING_REQS, sources=[_ohesg("/csa/"), _official("S&P Global CSA", "https://www.spglobal.com/esg/csa/", "S&P Global", source_type="methodology")]),
    ToolboxToolSpec(tool_id="gri", title="GRI Standards Quick Reference", description="GRI Universal, Topic, and Sector Standards quick reference with disclosures and topics.", url=f"{OHESG_BASE}/gri/", categories=["disclosure"], tags=["GRI", "disclosure standards"], aliases=["global reporting initiative"], requirements=_reqs(COMMON_DISCLOSURE_REQS, [RequirementItem(id="content-index", title="GRI content index", description="A GRI content index lists every reported disclosure with its location, statement of use, applicable GRI 1 basis, and reasons for any omissions.", keywords=["content index", "omission", "gri 1", "gri 2", "gri 3"], evidence_examples=["GRI content index"], framework_refs=["GRI 1"])]), sources=[_ohesg("/gri/"), _official("GRI Standards", "https://www.globalreporting.org/standards/", "GRI")]),
    ToolboxToolSpec(tool_id="esrs", title="ESRS Standards Quick Reference", description="EU ESRS disclosure requirements for CSRD preparation.", url=f"{OHESG_BASE}/esrs/", categories=["disclosure", "export"], tags=["ESRS", "CSRD", "EU"], aliases=["csrd", "efrag esrs"], jurisdictions=["EU"], requirements=_reqs(COMMON_DISCLOSURE_REQS, [
        # CSRD applicability is company-size-based, not customs-code-based, so the
        # generic export template (CN/HS-code screen) is intentionally not used here.
        RequirementItem(
            id="csrd-scope-thresholds",
            title="CSRD scope and threshold screen",
            description="Post-Omnibus CSRD scope is checked: EU undertakings (or consolidating parents) with more than 1,000 employees and over EUR 450 million net turnover report under ESRS, with first mandatory reporting for financial years beginning on or after 1 January 2027 (Directive (EU) 2026/470).",
            keywords=["1000 employees", "450 million", "net turnover", "threshold", "omnibus", "scope", "wave"],
            evidence_examples=["Headcount and turnover memo", "Group consolidation scope", "CSRD wave timeline note"],
            framework_refs=["CSRD", "Omnibus I Directive (EU) 2026/470"],
        ),
        RequirementItem(
            id="reporting-calendar-owner",
            title="Reporting calendar and statement owner",
            description="The sustainability-statement timetable, accountable owner, assurance provider, and ESEF/XBRL tagging plan are defined for the first applicable financial year.",
            keywords=["deadline", "sustainability statement", "owner", "calendar", "assurance", "tagging"],
            evidence_examples=["Reporting calendar", "responsibility matrix", "assurance engagement letter"],
            framework_refs=["CSRD"],
        ),
    ]), sources=[_ohesg("/esrs/"), _official("EFRAG ESRS Set 1", "https://www.efrag.org/en/sustainability-reporting/esrs-workstreams/sector-agnostic-standards-set-1-esrs", "EFRAG")]),
    ToolboxToolSpec(tool_id="iss", title="ISS ESG Rating Assistant", description="ISS STOXX corporate rating response preparation.", url=f"{OHESG_BASE}/iss/", categories=["rating"], tags=["ISS", "ESG rating"], aliases=["iss stoxx"], requirements=COMMON_RATING_REQS, sources=[_ohesg("/iss/"), _official("ISS ESG", "https://www.issgovernance.com/esg/", "ISS STOXX", source_type="methodology")]),
    ToolboxToolSpec(tool_id="cbam-export", title="CBAM Goods Export Query", description="CBAM covered-goods lookup and product-code applicability preparation.", url=f"{OHESG_BASE}/cbam-export/", categories=["export", "carbon"], tags=["CBAM", "CN code", "carbon"], aliases=["cbam product query", "cn code"], jurisdictions=["EU"], sectors=["steel", "aluminum", "cement", "fertilizer", "electricity", "hydrogen"], requirements=_reqs(COMMON_EXPORT_REQS, COMMON_CARBON_REQS), sources=[_ohesg("/cbam-export/"), _official("European Commission CBAM guidance", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en", "European Commission", source_type="guidance")]),
    ToolboxToolSpec(tool_id="cbam-steel", title="CBAM Steel and Aluminum Carbon Accounting", description="CBAM embedded-emissions preparation for steel and aluminum product scenarios.", url=f"{OHESG_BASE}/cbam-steel/", categories=["export", "carbon"], tags=["CBAM", "steel", "aluminum"], aliases=["cbam aluminum", "cbam steel"], jurisdictions=["EU"], sectors=["steel", "aluminum"], requirements=_reqs(COMMON_EXPORT_REQS, COMMON_CARBON_REQS), sources=[_ohesg("/cbam-steel/"), _official("European Commission CBAM guidance", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en", "European Commission", source_type="guidance")]),
    ToolboxToolSpec(tool_id="cbam", title="CBAM Compliance Assistant", description="EU Carbon Border Adjustment Mechanism compliance, deadlines, decision tree, and cost-estimation preparation.", url=f"{OHESG_BASE}/cbam/", categories=["export", "carbon"], tags=["CBAM", "EU", "carbon border"], aliases=["carbon border adjustment mechanism"], jurisdictions=["EU"], sectors=["steel", "aluminum", "cement", "fertilizer", "electricity", "hydrogen"], requirements=_reqs(COMMON_EXPORT_REQS, COMMON_CARBON_REQS), sources=[_ohesg("/cbam/"), _official("Regulation (EU) 2023/956", "https://eur-lex.europa.eu/eli/reg/2023/956/oj", "EUR-Lex", source_type="legislation"), _official("European Commission CBAM guidance", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en", "European Commission", source_type="guidance")]),
    ToolboxToolSpec(tool_id="glossary", title="ESG Glossary and Topic Lookup", description="ESG topic, indicator, and GICS-oriented quick lookup.", url=f"{OHESG_BASE}/glossary/", categories=["disclosure"], tags=["GRI", "ESRS", "GICS"], aliases=["esg glossary"], requirements=COMMON_DISCLOSURE_REQS, sources=[_ohesg("/glossary/")]),
    ToolboxToolSpec(
        tool_id="sbti",
        title="SBTi Assistant",
        description=(
            "Science Based Targets initiative readiness assistant for corporate near-term targets, "
            "net-zero targets, Scope 3 supplier engagement, sector routes, target validation, and "
            "five-year review planning."
        ),
        url=f"{OHESG_BASE}/sbti/",
        categories=["carbon"],
        tags=["SBTi", "targets", "near-term", "net-zero", "Scope 3", "supplier engagement"],
        aliases=["science based targets", "science based targets initiative", "SBTi 助手"],
        supported_actions=["get", "search", "checklist", "assess", "methodology", "crosswalk"],
        requirements=_reqs(COMMON_CARBON_REQS, [
            RequirementItem(
                id="sbti-target-boundary",
                title="SBTi target boundary and base year",
                description=(
                    "The company has a complete GHG inventory, base year, target year, organizational boundary, "
                    "and Scope 1/2/3 target boundary aligned to SBTi corporate criteria."
                ),
                keywords=[
                    "SBTi",
                    "base year",
                    "target year",
                    "target boundary",
                    "scope 1",
                    "scope 2",
                    "scope 3",
                    "ghg inventory",
                    "near-term",
                ],
                evidence_examples=[
                    "Base-year GHG inventory",
                    "Scope 1/2/3 boundary memo",
                    "Target wording and target-year calculation",
                ],
                framework_refs=["SBTi Corporate Near-Term Criteria", "GHG Protocol"],
            ),
            RequirementItem(
                id="sbti-near-term-ambition",
                title="Near-term target ambition",
                description=(
                    "Near-term targets use the appropriate SBTi method, ambition level, timeframe, and coverage "
                    "for the company's sector and emissions profile."
                ),
                keywords=[
                    "near-term criteria",
                    "5-10 years",
                    "ambition",
                    "1.5",
                    "absolute contraction",
                    "SDA",
                    "target-setting tool",
                    "coverage",
                ],
                evidence_examples=[
                    "SBTi target-setting tool output",
                    "Near-term criteria checklist",
                    "Method selection memo",
                ],
                framework_refs=["SBTi Corporate Near-Term Criteria"],
            ),
            RequirementItem(
                id="sbti-net-zero-ambition",
                title="Net-zero and long-term target ambition",
                description=(
                    "Net-zero targets include long-term value-chain reductions, residual emissions treatment, "
                    "and transparent neutralization planning without using offsets to replace abatement."
                ),
                keywords=[
                    "net-zero standard",
                    "long-term target",
                    "residual emissions",
                    "neutralization",
                    "abatement",
                    "value chain",
                    "2050",
                ],
                evidence_examples=[
                    "Net-zero target criteria checklist",
                    "Long-term pathway calculation",
                    "Residual emissions and neutralization memo",
                ],
                framework_refs=["SBTi Corporate Net-Zero Standard"],
            ),
            RequirementItem(
                id="sbti-scope3-supplier",
                title="Scope 3 and supplier engagement readiness",
                description=(
                    "Scope 3 materiality, supplier target coverage, supplier engagement plan, data strategy, "
                    "and tracking approach are defined where value-chain emissions are material."
                ),
                keywords=[
                    "scope 3",
                    "supplier engagement",
                    "supplier",
                    "value chain",
                    "procurement",
                    "emissions screening",
                    "data strategy",
                ],
                evidence_examples=[
                    "Scope 3 screening",
                    "Supplier engagement plan",
                    "Supplier target tracking file",
                    "Procurement category emissions analysis",
                ],
                framework_refs=["SBTi Supplier Engagement Guidance", "GHG Protocol Scope 3 Standard"],
            ),
            RequirementItem(
                id="sbti-sector-route",
                title="Sector route and special rules",
                description=(
                    "Sector-specific guidance and tool availability are checked for buildings, chemicals, cement, "
                    "FLAG, financial institutions, power, transport, steel, and other applicable sectors."
                ),
                keywords=[
                    "sector",
                    "buildings",
                    "chemicals",
                    "cement",
                    "FLAG",
                    "financial institutions",
                    "power",
                    "transport",
                    "steel",
                    "sectoral decarbonization approach",
                ],
                evidence_examples=[
                    "Sector applicability decision log",
                    "SBTi sector guidance references",
                    "FLAG or financial institution screening",
                ],
                framework_refs=["SBTi sector guidance"],
            ),
            RequirementItem(
                id="sbti-validation-review",
                title="Validation, status, and five-year review",
                description=(
                    "Submission, validation, company status, target update triggers, and mandatory five-year "
                    "review evidence are owned and calendared. The standard-version transition is tracked: new "
                    "targets may use Near-Term Criteria V5.3 and Corporate Net-Zero Standard V1.3 until "
                    "31 December 2027; from 1 January 2028 all new targets must use the Corporate Net-Zero "
                    "Standard V2 (published 2026), while existing validated targets remain valid to the end of "
                    "their timeframe."
                ),
                keywords=[
                    "validation",
                    "submission",
                    "commitment",
                    "company status",
                    "five-year review",
                    "target update",
                    "approved target",
                    "services",
                ],
                evidence_examples=[
                    "SBTi submission pack",
                    "Validation correspondence",
                    "Company status record",
                    "Five-year review calendar",
                ],
                framework_refs=["SBTi Company Status Manual", "SBTi Mandatory Five-Year Review Guidance"],
            ),
        ]),
        methods=[
            CalculatorMethod(
                id="sbti-six-decision-roadmap",
                name="SBTi six-decision roadmap",
                formula="readiness = ambition + timeframe + scope12_method + scope3_method + data_strategy + asset_plan",
                inputs=["ambition", "timeframe", "scope_1_2_method", "scope_3_method", "data_strategy", "asset_plan"],
                outputs=["sbti_readiness_route"],
                source_url=f"{OHESG_BASE}/sbti/roadmap",
            ),
            CalculatorMethod(
                id="sbti-threshold-screen",
                name="SBTi threshold quick screen",
                formula="triggered_rules = emissions_profile + sector + scope3_share + flag_share",
                inputs=["scope1_emissions", "scope2_emissions", "scope3_emissions", "sector", "flag_share"],
                outputs=["triggered_sbti_rules", "required_actions"],
                source_url=f"{OHESG_BASE}/sbti/tools/thresholds",
            ),
            CalculatorMethod(
                id="sbti-sector-matrix",
                name="SBTi sector resource matrix",
                formula="sector_route = sector + resource_status + available_methods + special_scope3_rules",
                inputs=["sector", "resource_status", "available_methods"],
                outputs=["sector_guidance_route"],
                source_url=f"{OHESG_BASE}/sbti/sectors/matrix",
            ),
            CalculatorMethod(
                id="sbti-five-year-review",
                name="SBTi mandatory five-year review planner",
                formula="review_window = approval_date + five_year_review_requirement",
                inputs=["target_approval_date", "current_target_status", "standard_version"],
                outputs=["review_window", "update_evidence_checklist"],
                source_url=f"{OHESG_BASE}/sbti/tools/five-year-review",
            ),
        ],
        sources=[
            _ohesg("/sbti/"),
            _official("SBTi resources", "https://sciencebasedtargets.org/resources", "SBTi", source_type="guidance"),
            _official("SBTi Corporate Net-Zero Standard", "https://sciencebasedtargets.org/net-zero", "SBTi", source_type="methodology"),
            _official("SBTi validation services", "https://sciencebasedtargets.org/validation-services", "SBTi", source_type="guidance"),
            _official("GHG Protocol Standards and Guidance", "https://ghgprotocol.org/standards-guidance", "GHG Protocol", source_type="guidance"),
        ],
    ),
    ToolboxToolSpec(tool_id="smeta", title="SMETA Audit Preparation", description="Sedex SMETA workplace and management-system audit readiness.", url=f"{OHESG_BASE}/smeta/", categories=["rating", "supplier"], tags=["SMETA", "Sedex", "supplier ESG"], aliases=["sedex smeta"], requirements=COMMON_RATING_REQS, sources=[_ohesg("/smeta/"), _official("Sedex SMETA", "https://www.sedex.com/solutions/smeta-audit/", "Sedex", source_type="methodology")]),
    ToolboxToolSpec(tool_id="sa8000", title="SA8000 Assistant", description="SA8000 decent-work standard and certification readiness.", url=f"{OHESG_BASE}/sa8000/", categories=["rating", "supplier"], tags=["SA8000", "labor"], aliases=["social accountability 8000"], requirements=COMMON_RATING_REQS, sources=[_ohesg("/sa8000/"), _official("SA8000 Standard", "https://sa-intl.org/programs/sa8000/", "Social Accountability International", source_type="methodology")]),
    ToolboxToolSpec(tool_id="aa1000", title="AA1000 Standards Learning", description="AccountAbility sustainability principles and assurance-standard preparation.", url=f"{OHESG_BASE}/aa1000/", categories=["disclosure"], tags=["AA1000", "assurance"], aliases=["accountability aa1000"], requirements=_reqs(COMMON_DISCLOSURE_REQS, [RequirementItem(id="assurance-scope", title="Assurance scope and criteria", description="The assurance engagement scope, subject matter, and reporting criteria are defined against the four AA1000 AccountAbility principles (inclusivity, materiality, responsiveness, impact).", keywords=["assurance", "inclusivity", "materiality", "responsiveness", "impact"], evidence_examples=["Assurance plan", "stakeholder engagement record"], framework_refs=["AA1000AP", "AA1000AS v3"])]), sources=[_ohesg("/aa1000/"), _official("AccountAbility Standards", "https://www.accountability.org/standards/", "AccountAbility", source_type="methodology")]),
    ToolboxToolSpec(tool_id="eu-green-deal", title="EU Green Deal Regulation Lookup", description="European Green Deal regulation overview, timelines, and export-compliance lookup.", url=f"{OHESG_BASE}/eu-green-deal/", categories=["export"], tags=["EU", "law", "export"], aliases=["european green deal"], jurisdictions=["EU"], requirements=COMMON_EXPORT_REQS, sources=[_ohesg("/eu-green-deal/"), _official("European Green Deal", "https://commission.europa.eu/strategy-and-policy/priorities-2019-2024/european-green-deal_en", "European Commission")]),
    ToolboxToolSpec(tool_id="battery", title="EU Battery Regulation Compliance Toolkit", description="EU Battery Regulation product classification, DPP fields, carbon footprint, checklist, and timeline.", url=f"{OHESG_BASE}/battery/", categories=["export", "carbon"], tags=["EU battery regulation", "DPP", "carbon footprint"], aliases=["battery regulation"], jurisdictions=["EU"], sectors=["batteries"], requirements=_reqs(COMMON_EXPORT_REQS, COMMON_CARBON_REQS), sources=[_ohesg("/battery/"), _official("Regulation (EU) 2023/1542", "https://eur-lex.europa.eu/eli/reg/2023/1542/oj", "EUR-Lex", source_type="legislation")]),
    ToolboxToolSpec(tool_id="eudr", title="EUDR Deforestation Compliance Toolkit", description="EU Deforestation Regulation product, risk, due-diligence, and geolocation preparation.", url=f"{OHESG_BASE}/eudr/", categories=["export"], tags=["EUDR", "deforestation"], aliases=["deforestation regulation"], jurisdictions=["EU"], sectors=["wood", "rubber", "soy", "coffee", "cocoa", "palm oil", "cattle"], requirements=COMMON_EXPORT_REQS, sources=[_ohesg("/eudr/"), _official("EU Deforestation Regulation", "https://environment.ec.europa.eu/topics/forests/deforestation/regulation-deforestation-free-products_en", "European Commission", source_type="guidance")]),
    ToolboxToolSpec(tool_id="csddd", title="CSDDD Supply Chain Due Diligence Toolkit", description="Human-rights and environmental due-diligence risk identification and supplier self-check preparation.", url=f"{OHESG_BASE}/csddd/", categories=["export", "supplier"], tags=["CSDDD", "HRDD", "supplier ESG"], aliases=["cs3d", "corporate sustainability due diligence"], jurisdictions=["EU"], requirements=_reqs(COMMON_RATING_REQS, [
        # CSDDD applicability is employee/turnover-threshold-based, not customs-code-based,
        # so the generic export template (CN/HS-code screen) is intentionally not used here.
        RequirementItem(
            id="csddd-scope-thresholds",
            title="CSDDD scope and threshold screen",
            description="Post-Omnibus CSDDD scope is checked: EU companies with more than 5,000 employees and over EUR 1.5 billion net worldwide turnover (or non-EU companies with over EUR 1.5 billion EU turnover), with member-state transposition by 26 July 2028 and application from 26 July 2029.",
            keywords=["5000 employees", "1.5 billion", "net turnover", "threshold", "omnibus", "transposition", "scope"],
            evidence_examples=["Headcount and turnover memo", "Group structure map", "CSDDD applicability note"],
            framework_refs=["CSDDD", "Omnibus I Directive (EU) 2026/470"],
        ),
        RequirementItem(id="grievance-remedy", title="Grievance and remediation", description="A notification and complaints mechanism is accessible to affected stakeholders, and identified harms have remediation plans with tracked outcomes.", keywords=["grievance", "remediation", "complaint", "stakeholder"], evidence_examples=["Grievance procedure", "remediation tracker"], framework_refs=["CSDDD", "UNGPs"]),
    ]), sources=[_ohesg("/csddd/"), _official("Corporate sustainability due diligence", "https://commission.europa.eu/business-economy-euro/doing-business-eu/sustainability-due-diligence-responsible-business/corporate-sustainability-due-diligence_en", "European Commission", source_type="guidance")]),
    ToolboxToolSpec(tool_id="espr", title="ESPR Ecodesign and Sustainable Product Toolkit", description="EU ESPR product-category, DPP, and ecodesign requirement preparation.", url=f"{OHESG_BASE}/espr/", categories=["export"], tags=["ESPR", "DPP", "ecodesign"], aliases=["ecodesign sustainable products"], jurisdictions=["EU"], requirements=COMMON_EXPORT_REQS, sources=[_ohesg("/espr/"), _official("Ecodesign for Sustainable Products Regulation", "https://commission.europa.eu/energy-climate-change-environment/standards-tools-and-labels/products-labelling-rules-and-requirements/ecodesign-sustainable-products-regulation_en", "European Commission", source_type="guidance")]),
    ToolboxToolSpec(tool_id="amfori-bsci", title="amfori BSCI Rating Assistant", description="amfori BSCI performance-area and audit-readiness assistant.", url=f"{OHESG_BASE}/amfori-bsci/", categories=["rating", "supplier"], tags=["amfori BSCI", "supplier audit"], aliases=["bsci"], requirements=COMMON_RATING_REQS, sources=[_ohesg("/amfori-bsci/"), _official("amfori BSCI", "https://www.amfori.org/en/solutions/social/about-bsci", "amfori", source_type="methodology")]),
    ToolboxToolSpec(tool_id="rba", title="RBA Rating Assistant", description="Responsible Business Alliance Code, VAP score, forced-labor, and minerals due-diligence readiness.", url=f"{OHESG_BASE}/rba/", categories=["rating", "supplier"], tags=["RBA", "VAP", "responsible business"], aliases=["responsible business alliance"], requirements=COMMON_RATING_REQS, sources=[_ohesg("/rba/"), _official("RBA Code of Conduct", "https://www.responsiblebusiness.org/code-of-conduct/", "Responsible Business Alliance", source_type="methodology")]),
    ToolboxToolSpec(tool_id="icma", title="Sustainable Bond Navigator", description="ICMA GBP/SBP/SBG/SLBP and transition-finance preparation.", url=f"{OHESG_BASE}/icma/", categories=["disclosure"], tags=["ICMA", "sustainable finance", "bond"], aliases=["green bond principles", "sustainability-linked bond principles"], requirements=_reqs(COMMON_DISCLOSURE_REQS, [RequirementItem(id="use-of-proceeds-kpi", title="Use-of-proceeds or KPI framework", description="A bond framework defines either eligible use-of-proceeds categories with allocation tracking (GBP/SBP) or KPIs and sustainability performance targets (SLBP), supported by external review.", keywords=["use of proceeds", "kpi", "spo", "bond", "allocation"], evidence_examples=["Green bond framework", "SPO report", "allocation report"], framework_refs=["ICMA GBP", "ICMA SLBP"])]), sources=[_ohesg("/icma/"), _official("ICMA Sustainable Finance", "https://www.icmagroup.org/sustainable-finance/", "ICMA", source_type="methodology")]),
    ToolboxToolSpec(tool_id="issb", title="Sustainability Disclosure Assistant", description="ISSB IFRS S1 and S2 four-pillar disclosure readiness with interoperability references.", url=f"{OHESG_BASE}/issb/", categories=["disclosure"], tags=["ISSB", "IFRS S1", "IFRS S2"], aliases=["ifrs sustainability"], requirements=COMMON_DISCLOSURE_REQS, sources=[_ohesg("/issb/"), _official("ISSB and IFRS Sustainability Disclosure Standards", "https://www.ifrs.org/sustainability/knowledge-hub/introduction-to-issb-and-ifrs-sustainability-disclosure-standards/", "IFRS Foundation")]),
    ToolboxToolSpec(tool_id="climate-bonds", title="Climate Bonds Navigator", description="Climate Bonds Standard and taxonomy certification preparation.", url=f"{OHESG_BASE}/climate-bonds/", categories=["disclosure"], tags=["Climate Bonds", "taxonomy", "green bond"], aliases=["cbi", "climate bonds standard"], requirements=_reqs(COMMON_DISCLOSURE_REQS, [RequirementItem(id="taxonomy-eligibility", title="Taxonomy and certification eligibility", description="Financed assets and activities are screened against the Climate Bonds Taxonomy and applicable sector criteria before an approved verifier is engaged for certification.", keywords=["taxonomy", "certification", "verifier", "sector criteria"], evidence_examples=["Eligible asset list", "verifier scope"], framework_refs=["Climate Bonds Standard", "Climate Bonds Taxonomy"])]), sources=[_ohesg("/climate-bonds/"), _official("Climate Bonds Standard", "https://www.climatebonds.net/standard", "Climate Bonds Initiative", source_type="methodology")]),
    ToolboxToolSpec(tool_id="nav", title="ESG Ecosystem Navigator", description="ESG institution, standard-setter, rating, and tool ecosystem lookup.", url=f"{OHESG_BASE}/nav/", categories=["disclosure"], tags=["ESG ecosystem", "institutions"], aliases=["esg navigation"], supported_actions=["get", "search", "methodology"], requirements=COMMON_DISCLOSURE_REQS, sources=[_ohesg("/nav/")]),
    ToolboxToolSpec(
        tool_id="carbon-iso",
        title="Carbon-related ISO Standards Learning Guide",
        description=(
            "ISO carbon and climate standards selector covering the mitigation track "
            "(ISO 14064-1/2/3, ISO 14067, ISO 14068) and adaptation track "
            "(ISO 14090/14091/14092), with readiness checklists for choosing the right standard."
        ),
        url=f"{OHESG_BASE}/carbon-iso/",
        categories=["carbon"],
        tags=[
            "ISO",
            "carbon accounting",
            "adaptation",
            "ISO 14064",
            "ISO 14067",
            "ISO 14068",
            "ISO 14090",
            "ISO 14091",
        ],
        aliases=["iso carbon", "carbon iso", "碳相关 ISO 标准学习指南", "iso ghg selector"],
        supported_actions=["get", "search", "checklist", "assess", "methodology", "crosswalk"],
        requirements=_reqs(COMMON_CARBON_REQS, [
            RequirementItem(
                id="standard-selection",
                title="ISO standard selection",
                description=(
                    "The use case is classified before selecting an ISO route: organization inventory, "
                    "project reductions/removals, validation/verification, product carbon footprint, "
                    "carbon-neutrality claim, or climate-adaptation planning."
                ),
                keywords=[
                    "standard selector",
                    "organization inventory",
                    "project",
                    "verification",
                    "product carbon footprint",
                    "carbon neutrality",
                    "adaptation",
                    "14064",
                    "14067",
                    "14068",
                    "14090",
                    "14091",
                ],
                evidence_examples=[
                    "Use-case memo",
                    "Customer request or tender requirement",
                    "Standard applicability decision log",
                ],
                framework_refs=["ISO 14064", "ISO 14067", "ISO 14068", "ISO 14090"],
            ),
            RequirementItem(
                id="iso-14064-1-inventory",
                title="ISO 14064-1 organization inventory readiness",
                description=(
                    "Organization boundary, reporting boundary, six emission categories, quantification "
                    "method, base year, quality management, and reporting/verification evidence are prepared."
                ),
                keywords=[
                    "14064-1",
                    "organization boundary",
                    "reporting boundary",
                    "six categories",
                    "base year",
                    "quality management",
                    "verification",
                ],
                evidence_examples=[
                    "Boundary memo",
                    "Six-category emissions map",
                    "Base-year recalculation policy",
                    "GHG report skeleton",
                ],
                framework_refs=["ISO 14064-1"],
            ),
            RequirementItem(
                id="iso-14067-product-cfp",
                title="ISO 14067 product carbon footprint readiness",
                description=(
                    "Product carbon footprint work defines goal and scope, functional or declared unit, "
                    "system boundary, cut-off rules, data quality, allocation, biogenic carbon, dLUC, "
                    "and critical review needs."
                ),
                keywords=[
                    "14067",
                    "product carbon footprint",
                    "cfp",
                    "lca",
                    "functional unit",
                    "declared unit",
                    "system boundary",
                    "allocation",
                    "critical review",
                    "pcr",
                ],
                evidence_examples=[
                    "Product system flow diagram",
                    "Functional unit definition",
                    "Primary and secondary data inventory",
                    "Allocation decision log",
                    "Critical review plan",
                ],
                framework_refs=["ISO 14067", "ISO 14040", "ISO 14044"],
            ),
            RequirementItem(
                id="iso-14068-neutrality",
                title="ISO 14068 carbon-neutrality claim readiness",
                description=(
                    "Carbon-neutrality work prioritizes reduction, removals or enhancements, credible offsets, "
                    "transition planning, verification, and public reporting before making claims."
                ),
                keywords=[
                    "14068",
                    "carbon neutrality",
                    "neutrality claim",
                    "offset",
                    "carbon credit",
                    "transition plan",
                    "reduction first",
                    "verification",
                ],
                evidence_examples=[
                    "Carbon-neutrality management plan",
                    "Reduction hierarchy evidence",
                    "Carbon-credit due-diligence file",
                    "Public claim review",
                ],
                framework_refs=["ISO 14068"],
            ),
            RequirementItem(
                id="iso-14090-adaptation",
                title="ISO 14090/14091 adaptation and climate-risk readiness",
                description=(
                    "Climate-adaptation work has an adaptation cycle, vulnerability/risk assessment, exposure, "
                    "sensitivity, adaptive capacity, adaptation plan, monitoring, and reporting."
                ),
                keywords=[
                    "14090",
                    "14091",
                    "14092",
                    "adaptation",
                    "vulnerability",
                    "exposure",
                    "sensitivity",
                    "adaptive capacity",
                    "climate risk",
                    "monitoring",
                ],
                evidence_examples=[
                    "Climate risk register",
                    "Exposure and sensitivity assessment",
                    "Adaptation action plan",
                    "Monitoring and reporting cadence",
                ],
                framework_refs=["ISO 14090", "ISO 14091", "ISO/TS 14092"],
            ),
        ]),
        methods=[
            CalculatorMethod(
                id="iso-standard-selector",
                name="Three-question ISO standard selector",
                formula="route = use_case + subject + assurance_need",
                inputs=["use_case", "subject", "assurance_need"],
                outputs=["recommended_iso_standard", "next_checklist"],
                source_url=f"{OHESG_BASE}/carbon-iso/standard-picker",
            ),
            CalculatorMethod(
                id="iso-14064-1-six-step-inventory",
                name="ISO 14064-1 organization inventory workflow",
                formula="boundary -> source/category map -> quantification -> base year -> quality management -> report/verification",
                inputs=["boundary_documents", "activity_data", "emission_factors", "base_year_policy"],
                outputs=["organization_ghg_inventory_readiness"],
                source_url=f"{OHESG_BASE}/carbon-iso/14064-1",
            ),
            CalculatorMethod(
                id="iso-14067-seven-step-cfp",
                name="ISO 14067 product carbon footprint workflow",
                formula="goal_scope -> product_system -> data_collection -> allocation -> lci_lcia -> sensitivity -> critical_review",
                inputs=["functional_unit", "system_boundary", "lifecycle_inventory", "allocation_rules"],
                outputs=["product_cfp_readiness"],
                source_url=f"{OHESG_BASE}/carbon-iso/14067",
            ),
            CalculatorMethod(
                id="iso-14091-risk-logic",
                name="ISO 14091 vulnerability and climate-risk logic",
                formula="vulnerability = exposure + sensitivity - adaptive_capacity",
                inputs=["exposure", "sensitivity", "adaptive_capacity"],
                outputs=["climate_vulnerability_assessment"],
                source_url="https://www.iso.org/standard/68508.html",
            ),
        ],
        sources=[
            _ohesg("/carbon-iso/"),
            _official("ISO climate change standards", "https://www.iso.org/sectors/environment/climate-change", "ISO", source_type="methodology"),
            _official("ISO 14064-1:2018", "https://www.iso.org/standard/66453.html", "ISO", source_type="methodology"),
            _official("ISO 14064-2:2019", "https://www.iso.org/standard/66454.html", "ISO", source_type="methodology"),
            _official("ISO 14067:2018", "https://www.iso.org/standard/71206.html", "ISO", source_type="methodology"),
            _official("ISO 14091:2021", "https://www.iso.org/standard/68508.html", "ISO", source_type="methodology"),
        ],
    ),
    ToolboxToolSpec(tool_id="aws", title="Water Stewardship Standard Assistant", description="Alliance for Water Stewardship standard quick reference and certification readiness.", url=f"{OHESG_BASE}/aws/", categories=["disclosure"], tags=["AWS", "water stewardship"], aliases=["alliance for water stewardship"], requirements=_reqs(COMMON_DISCLOSURE_REQS, [RequirementItem(id="water-stewardship-plan", title="Water stewardship plan", description="A site water-stewardship plan covers water balance, withdrawal and discharge quality, catchment-shared challenges, and commitments with measurable targets.", keywords=["water", "catchment", "withdrawal", "discharge", "stewardship"], evidence_examples=["Water balance", "catchment risk assessment"], framework_refs=["AWS Standard V3.0"])]), sources=[_ohesg("/aws/"), _official("AWS Standard V3.0 (launched 18 March 2026; one-year transition from V2.0 until 18 March 2027)", "https://a4ws.org/aws-standard/", "Alliance for Water Stewardship", source_type="methodology")]),
    ToolboxToolSpec(tool_id="irma", title="IRMA Responsible Mining Assistant", description="IRMA responsible mining standard and chain-of-custody readiness.", url=f"{OHESG_BASE}/irma/", categories=["supplier"], tags=["IRMA", "responsible mining"], aliases=["initiative for responsible mining assurance"], sectors=["mining"], requirements=COMMON_RATING_REQS, sources=[_ohesg("/irma/"), _official("IRMA Standard", "https://responsiblemining.net/what-we-do/standard/", "IRMA", source_type="methodology")]),
    ToolboxToolSpec(tool_id="conflict-minerals", title="Conflict Minerals Compliance Assistant", description="OECD five-step due diligence, RMI tools, 3TG, cobalt, mica, and conflict-minerals regulations.", url=f"{OHESG_BASE}/conflict-minerals/", categories=["supplier"], tags=["conflict minerals", "OECD", "RMI", "3TG"], aliases=["cmrt", "emrt", "responsible minerals"], sectors=["mining", "electronics", "automotive"], requirements=_reqs(COMMON_RATING_REQS, [RequirementItem(id="minerals-traceability", title="Minerals traceability and smelter review", description="3TG, cobalt, and mica supply chains are traced to smelters and refiners via CMRT/EMRT templates, and smelter RMAP conformance status is reviewed with follow-up for non-conformant facilities.", keywords=["3tg", "cobalt", "mica", "smelter", "cmrt", "emrt", "rmap"], evidence_examples=["CMRT", "EMRT", "smelter list"], framework_refs=["OECD Due Diligence Guidance", "RMI RMAP"])]), sources=[_ohesg("/conflict-minerals/"), _official("OECD Due Diligence Guidance for Responsible Mineral Supply Chains", "https://www.oecd.org/corporate/mne/mining.htm", "OECD", source_type="guidance"), _official("Responsible Minerals Initiative tools", "https://www.responsiblemineralsinitiative.org/", "RMI", source_type="guidance")]),
    ToolboxToolSpec(tool_id="ghg", title="GHG Protocol Navigator", description="GHG Protocol standards family, Scope 1/2/3 boundaries, calculation tools, and inventory path.", url=f"{OHESG_BASE}/ghg/", categories=["carbon"], tags=["GHG Protocol", "Scope 1", "Scope 2", "Scope 3"], aliases=["greenhouse gas protocol"], requirements=COMMON_CARBON_REQS, sources=[_ohesg("/ghg/"), _official("GHG Protocol Standards and Guidance", "https://ghgprotocol.org/standards-guidance", "GHG Protocol", source_type="guidance")]),
)


_COMPLETION_REQUIREMENTS: dict[str, list[RequirementItem]] = {
    "material": [
        RequirementItem(
            id="impacts-risks-opportunities",
            title="Impacts, risks, and opportunities inventory",
            description="Actual and potential impacts plus financial risks and opportunities are inventoried before scoring.",
            keywords=["iro", "impact", "risk", "opportunity", "value chain", "actual impact", "potential impact"],
            evidence_examples=["IRO register", "value-chain map", "risk and opportunity log"],
            framework_refs=["ESRS 1", "GRI 3"],
        ),
        RequirementItem(
            id="impact-materiality",
            title="Impact materiality scoring",
            description="Scale, scope, irremediable character, likelihood, and severity are documented for impact materiality.",
            keywords=["scale", "scope", "severity", "likelihood", "irremediable", "impact materiality"],
            evidence_examples=["Impact scoring rubric", "stakeholder evidence pack", "severity calibration notes"],
            framework_refs=["ESRS 1", "GRI 3"],
        ),
        RequirementItem(
            id="financial-materiality",
            title="Financial materiality scoring",
            description="Revenue, cost, asset, financing, and enterprise-value channels are assessed for financial materiality.",
            keywords=["financial materiality", "enterprise value", "revenue", "cost", "asset", "financing"],
            evidence_examples=["Financial impact model", "risk register linkage", "management workshop record"],
            framework_refs=["ESRS 1", "ISSB IFRS S1"],
        ),
    ],
    "msci": [
        RequirementItem(
            id="industry-key-issues",
            title="Industry key issue mapping",
            description="The company maps operations to an industry and identifies material ESG key issues before evidence collection.",
            keywords=["industry", "key issue", "material issue", "peer", "exposure"],
            evidence_examples=["Industry classification memo", "key-issue map", "peer benchmark"],
            framework_refs=["MSCI ESG Ratings"],
        ),
        RequirementItem(
            id="risk-exposure-management",
            title="Risk exposure and management evidence",
            description="Exposure to key risks and the company's management systems, controls, and performance are documented.",
            keywords=["exposure", "risk management", "controversy", "governance", "performance"],
            evidence_examples=["Risk exposure memo", "control evidence", "controversy response log"],
            framework_refs=["MSCI ESG Ratings"],
        ),
        RequirementItem(
            id="data-source-reconciliation",
            title="Public data reconciliation",
            description="Public disclosures and rating-provider data points are reconciled to internal evidence before response.",
            keywords=["public disclosure", "rating data", "reconciliation", "correction", "issuer communication"],
            evidence_examples=["Public-data reconciliation", "issuer correction pack", "evidence index"],
            framework_refs=["MSCI ESG Ratings"],
        ),
        RequirementItem(
            id="industry-universe-routing",
            title="160-industry routing",
            description="The company's activities, revenue mix, and peer set are routed to the relevant MSCI ESG industry before key issues are interpreted.",
            keywords=["160", "industry", "sub-industry", "revenue mix", "peer set", "classification"],
            evidence_examples=["Revenue-by-activity table", "Industry routing note", "Peer set benchmark"],
            framework_refs=["MSCI ESG Ratings"],
        ),
        RequirementItem(
            id="rating-scale-model",
            title="Rating scale and scoring model",
            description="The MSCI scoring model is understood before responding: key issues across environment, social, and governance pillars are weighted by industry contribution to externalities; exposure and management scores combine into an industry-adjusted weighted-average key-issue score mapped to the AAA-CCC letter scale, with controversies able to drag management scores down.",
            keywords=["AAA", "CCC", "letter rating", "key issue score", "weighted average", "exposure", "management score", "controversy deduction"],
            evidence_examples=["Key-issue weight table", "Exposure vs management score memo", "Controversy impact log"],
            framework_refs=["MSCI ESG Ratings methodology"],
        ),
    ],
    "ecovadis": [
        RequirementItem(
            id="management-system-cycle",
            title="Policies, actions, and results cycle",
            description="Evidence shows the EcoVadis management-system chain from policy commitments to actions and measurable results.",
            keywords=["policy", "action", "result", "indicator", "management system", "coverage"],
            evidence_examples=["Policy register", "action plan", "KPI results"],
            framework_refs=["EcoVadis methodology"],
        ),
        RequirementItem(
            id="document-validity",
            title="Document validity and scope",
            description="Documents are current, attributable to the assessed legal entity, and cover the requested assessment scope.",
            keywords=["valid", "date", "entity", "scope", "site", "certificate"],
            evidence_examples=["Document validity log", "entity scope map", "certificate register"],
            framework_refs=["EcoVadis methodology"],
        ),
        RequirementItem(
            id="scoring-and-medals",
            title="Scoring model and medal thresholds",
            description="The EcoVadis scoring model is understood: 21 criteria across four themes are weighted by industry, size, and location into a 0-100 score; medals are percentile-based among rated companies (Platinum top 1%, Gold top 5%, Silver top 15%, Bronze top 35%) and require a minimum overall score, so reassessment planning tracks both score and percentile drift.",
            keywords=["score", "0-100", "medal", "platinum", "gold", "silver", "bronze", "percentile", "weighting"],
            evidence_examples=["Scorecard review", "Theme weight note", "Medal threshold tracker"],
            framework_refs=["EcoVadis methodology"],
        ),
    ],
    "cdp": [
        RequirementItem(
            id="questionnaire-scope",
            title="Questionnaire scope and module routing",
            description="The 13-module integrated corporate questionnaire is scoped before drafting: climate change, forests, and water security are scored themes; plastics, biodiversity, and ocean (new for 2026) remain unscored; forests scoring covers seven commodities (cattle, palm oil, soy, timber, cocoa, coffee, rubber); module routing depends on sector, size, and opted-in topics.",
            keywords=["questionnaire", "module", "climate", "water", "forest", "supply chain", "sector", "plastics", "biodiversity", "ocean"],
            evidence_examples=["CDP module map", "question owner matrix", "response calendar"],
            framework_refs=["CDP 2026 corporate questionnaire"],
        ),
        RequirementItem(
            id="environmental-targets",
            title="Environmental targets and transition plan",
            description="Targets, transition plans, and progress metrics are supported by boundary and base-year evidence.",
            keywords=["target", "transition plan", "base year", "progress", "scope", "abatement"],
            evidence_examples=["Target register", "transition plan", "progress dashboard"],
            framework_refs=["CDP climate questionnaire"],
        ),
        RequirementItem(
            id="verification-and-risk",
            title="Verification and environmental risk evidence",
            description="External verification status, risk assessment, opportunities, and financial impacts are documented.",
            keywords=["verification", "assurance", "risk assessment", "opportunity", "financial impact"],
            evidence_examples=["Verification statement", "risk assessment", "financial impact worksheet"],
            framework_refs=["CDP scoring guidance"],
        ),
    ],
    "csa": [
        RequirementItem(
            id="industry-questionnaire",
            title="CSA industry questionnaire routing",
            description="The company identifies its CSA industry and maps questions to responsible evidence owners.",
            keywords=["industry", "questionnaire", "CSA", "topic", "owner"],
            evidence_examples=["CSA industry mapping", "question owner list", "topic index"],
            framework_refs=["S&P Global CSA"],
        ),
        RequirementItem(
            id="public-disclosure-alignment",
            title="Public disclosure alignment",
            description="CSA responses are reconciled against public reports and web disclosures used in assessment review.",
            keywords=["public disclosure", "annual report", "sustainability report", "website", "alignment"],
            evidence_examples=["Disclosure reconciliation", "public evidence links", "CSA response evidence pack"],
            framework_refs=["S&P Global CSA"],
        ),
        RequirementItem(
            id="topic-performance-evidence",
            title="Topic performance evidence",
            description="Governance, economic, environmental, and social topic evidence includes policies, programs, KPIs, and trend data.",
            keywords=["governance", "economic", "environmental", "social", "kpi", "trend"],
            evidence_examples=["Topic KPI table", "program evidence", "trend workbook"],
            framework_refs=["S&P Global CSA"],
        ),
        RequirementItem(
            id="industry-weighting-map",
            title="62-industry weighting map",
            description="CSA industry weights, core topics, and disclosure focus areas are documented before questionnaire preparation.",
            keywords=["62", "industry", "weight", "dimension weight", "core issue", "disclosure focus"],
            evidence_examples=["CSA industry weighting note", "Dimension weight table", "Core-topic evidence map"],
            framework_refs=["S&P Global CSA"],
        ),
    ],
    "gri": [
        RequirementItem(
            id="gri-1-claim",
            title="GRI reporting claim and basis",
            description="The report basis, use of GRI Standards, statement of use, and omission handling are defined.",
            keywords=["statement of use", "in accordance", "with reference", "omission", "gri 1"],
            evidence_examples=["GRI statement of use", "omissions register", "reporting basis memo"],
            framework_refs=["GRI 1"],
        ),
        RequirementItem(
            id="gri-2-general-disclosures",
            title="GRI 2 general disclosures",
            description="Organization, governance, strategy, policy, stakeholder, and reporting-practice disclosures are evidenced.",
            keywords=["gri 2", "general disclosure", "governance", "stakeholder", "reporting practice"],
            evidence_examples=["GRI 2 evidence index", "governance disclosures", "stakeholder engagement record"],
            framework_refs=["GRI 2"],
        ),
        RequirementItem(
            id="gri-3-material-topics",
            title="GRI 3 material topics and topic standards",
            description="Material topics, impacts, management approach, and applicable topic disclosures are connected in the index.",
            keywords=["gri 3", "material topic", "management approach", "topic standard", "impact"],
            evidence_examples=["Material topic list", "topic-standard map", "management approach disclosure"],
            framework_refs=["GRI 3"],
        ),
        RequirementItem(
            id="gri-305-emissions",
            title="GRI 305 emissions disclosures",
            description="Direct, energy indirect, other indirect, intensity, reduction, and ozone-depleting substance emissions disclosures are mapped where material.",
            keywords=["GRI 305", "emissions", "scope 1", "scope 2", "scope 3", "ghg", "ozone-depleting", "reduction", "排放"],
            evidence_examples=["GRI 305 disclosure index", "GHG inventory table", "Emissions reduction evidence"],
            framework_refs=["GRI 305"],
        ),
    ],
    "esrs": [
        RequirementItem(
            id="esrs-2-cross-cutting",
            title="ESRS 2 cross-cutting disclosures",
            description="Governance, strategy, IRO management, and metrics/targets disclosures are mapped before topical ESRS work.",
            keywords=["esrs 2", "governance", "strategy", "iro", "metrics and targets"],
            evidence_examples=["ESRS 2 disclosure map", "IRO procedure", "governance evidence"],
            framework_refs=["ESRS 2"],
        ),
        RequirementItem(
            id="topical-standard-scope",
            title="Topical standard scope",
            description="E1-E5, S1-S4, and G1 disclosure requirements are selected through materiality conclusions.",
            keywords=["E1", "E2", "E3", "E4", "E5", "S1", "S2", "S3", "S4", "G1", "material"],
            evidence_examples=["Topical ESRS applicability matrix", "materiality conclusion", "DR owner map"],
            framework_refs=["ESRS Set 1"],
        ),
        RequirementItem(
            id="value-chain-and-datapoints",
            title="Value-chain and datapoint readiness",
            description="Upstream/downstream datapoints, estimates, phase-ins, and entity boundaries are documented. The datapoint inventory tracks the revised simplified ESRS (delegated act expected in 2026, cutting mandatory datapoints by roughly 60% and dropping sector-specific standards) so collection effort is prioritized on datapoints that survive the revision.",
            keywords=["value chain", "datapoint", "estimate", "phase-in", "boundary", "upstream", "downstream", "simplified esrs"],
            evidence_examples=["ESRS datapoint inventory", "value-chain evidence log", "estimate methodology"],
            framework_refs=["ESRS 1", "Omnibus I Directive (EU) 2026/470"],
        ),
    ],
    "iss": [
        RequirementItem(
            id="rating-topic-map",
            title="ISS rating topic map",
            description="The company identifies relevant ISS governance, environmental, social, and controversy topics.",
            keywords=["governance", "environmental", "social", "controversy", "topic", "rating"],
            evidence_examples=["ISS topic map", "controversy review", "governance evidence pack"],
            framework_refs=["ISS ESG"],
        ),
        RequirementItem(
            id="controversy-response",
            title="Controversy and incident response",
            description="Public controversies, incidents, remediation, and response evidence are tracked and reconciled.",
            keywords=["controversy", "incident", "remediation", "response", "media", "stakeholder"],
            evidence_examples=["Incident log", "remediation file", "public response pack"],
            framework_refs=["ISS ESG"],
        ),
        RequirementItem(
            id="issuer-data-review",
            title="Issuer data review",
            description="Rating data, public documents, and issuer feedback are reviewed before submission or correction.",
            keywords=["issuer", "data review", "feedback", "correction", "public document"],
            evidence_examples=["Issuer feedback log", "rating-data reconciliation", "public evidence links"],
            framework_refs=["ISS ESG"],
        ),
        RequirementItem(
            id="corporate-assessment-methodology",
            title="Corporate assessment methodology lookup",
            description="Relevant ISS STOXX assessment topics, norms, governance indicators, and issuer update routes are identified.",
            keywords=["ISS STOXX", "corporate assessment", "methodology", "norms", "governance indicators", "update route"],
            evidence_examples=["ISS methodology topic map", "Norms screen", "Issuer update record"],
            framework_refs=["ISS ESG"],
        ),
    ],
    "cbam-export": [
        RequirementItem(
            id="cn-code-screen",
            title="CN code covered-goods screen",
            description="CN or HS codes are mapped to the current CBAM covered-goods list and product role.",
            keywords=["cn code", "hs code", "covered goods", "annex i", "importer", "operator"],
            evidence_examples=["CN code list", "customs classification memo", "customer role map"],
            framework_refs=["Regulation (EU) 2023/956"],
        ),
        RequirementItem(
            id="installation-data-route",
            title="Installation and operator data route",
            description="Installation, operator, production route, and embedded emissions evidence owners are identified.",
            keywords=["installation", "operator", "production route", "embedded emissions", "specific emissions"],
            evidence_examples=["Installation profile", "operator declaration", "production-route map"],
            framework_refs=["CBAM implementing regulation"],
        ),
    ],
    "cbam-steel": [
        RequirementItem(
            id="steel-aluminum-route",
            title="Steel and aluminum production route",
            description="Product route, precursor materials, process emissions, and electricity consumption are identified.",
            keywords=["steel", "aluminum", "precursor", "production route", "electricity", "process emissions"],
            evidence_examples=["Bill of materials", "production route worksheet", "electricity consumption records"],
            framework_refs=["CBAM guidance"],
        ),
        RequirementItem(
            id="embedded-emissions-calculation",
            title="Embedded emissions calculation pack",
            description="Direct and indirect embedded emissions, default values, and actual data basis are documented.",
            keywords=["embedded emissions", "direct emissions", "indirect emissions", "default values", "actual data"],
            evidence_examples=["Embedded emissions workbook", "default value justification", "actual data evidence"],
            framework_refs=["CBAM implementing regulation"],
        ),
    ],
    "cbam": [
        RequirementItem(
            id="definitive-period-obligations",
            title="CBAM definitive-period obligations",
            description="Definitive-regime obligations applying from 1 January 2026 are calendared: authorised-declarant status, the 50-tonne annual mass de minimis screen (not applicable to hydrogen and electricity), and the first annual CBAM declaration due 30 September 2027 for 2026 imports.",
            keywords=["definitive period", "authorised declarant", "50 tonnes", "de minimis", "annual declaration", "declarant", "reporting obligation"],
            evidence_examples=["CBAM declaration calendar", "declarant authorisation record", "Annual import-mass tracker"],
            framework_refs=["Regulation (EU) 2023/956", "Regulation (EU) 2025/2083"],
        ),
        RequirementItem(
            id="certificate-cost-prep",
            title="Certificate and carbon-price preparation",
            description="Certificate exposure is modelled: sales start 1 February 2027 (covering 2026 imports at EU ETS quarterly-average prices), holdings must cover at least 50% of cumulative embedded emissions, and harmonised penalties apply (EUR 100/tCO2e for declarants, EUR 300-500/tCO2e for unauthorised importers).",
            keywords=["certificate", "carbon price", "paid carbon price", "cost", "ETS", "financial exposure", "coverage ratio", "penalty"],
            evidence_examples=["CBAM cost model", "paid carbon price evidence", "certificate exposure worksheet"],
            framework_refs=["Regulation (EU) 2023/956", "Regulation (EU) 2025/2083"],
        ),
    ],
    "glossary": [
        RequirementItem(
            id="term-normalization",
            title="Term and acronym normalization",
            description="ESG acronyms, definitions, and equivalent terms are normalized before routing to standards or tools.",
            keywords=["definition", "acronym", "term", "indicator", "topic", "taxonomy"],
            evidence_examples=["Term lookup result", "definition source", "synonym map"],
        ),
        RequirementItem(
            id="framework-routing",
            title="Framework routing suggestion",
            description="User terms are routed to relevant disclosure, rating, carbon, export, or supplier modules.",
            keywords=["route", "framework", "standard", "tool", "module", "lookup"],
            evidence_examples=["Framework route log", "matched standards", "recommended module list"],
        ),
        RequirementItem(
            id="industry-topic-context",
            title="Industry and topic context",
            description="Industry context such as GICS or sector is captured before topic interpretation.",
            keywords=["gics", "sector", "industry", "materiality", "topic"],
            evidence_examples=["Sector classification", "topic context note", "industry keyword match"],
        ),
        RequirementItem(
            id="multi-source-filter",
            title="Multi-source topic filter",
            description="GRI, ESRS, GICS, and other source filters are preserved so terms can be compared across framework vocabularies.",
            keywords=["GRI", "ESRS", "GICS", "filter", "multi-source", "indicator"],
            evidence_examples=["Selected source filters", "Framework term comparison", "Indicator source map"],
        ),
    ],
    "smeta": [
        RequirementItem(
            id="labor-standards",
            title="Labor standards and working conditions",
            description="Working hours, wages, employment status, child labor, forced labor, and discrimination controls are evidenced.",
            keywords=["working hours", "wages", "child labor", "forced labor", "discrimination", "employment"],
            evidence_examples=["Payroll sample", "time records", "labor policy", "worker interview plan"],
            framework_refs=["SMETA"],
        ),
        RequirementItem(
            id="health-safety-site",
            title="Health and safety site readiness",
            description="Site risk assessments, emergency preparedness, incident records, and worker training are ready for audit.",
            keywords=["health and safety", "risk assessment", "emergency", "incident", "training", "ppe"],
            evidence_examples=["H&S risk assessment", "emergency drill log", "incident register"],
            framework_refs=["SMETA"],
        ),
        RequirementItem(
            id="audit-capa",
            title="Audit CAPA workflow",
            description="Non-conformities, corrective actions, owners, due dates, and verification evidence are tracked.",
            keywords=["capa", "non-conformity", "corrective action", "audit", "verification"],
            evidence_examples=["CAPA tracker", "audit report", "closure evidence"],
            framework_refs=["SMETA"],
        ),
        RequirementItem(
            id="smeta-7-framework",
            title="SMETA 7 framework routing",
            description="SMETA 7.0 (released June 2024) expectations are routed for site self-check: explicit Workplace Requirements against the ETI Base Code, the Management Systems Assessment that replaced observations, and the Collaborative Action Required finding for living wages, responsible recruitment, child labor, and discrimination; 2-pillar audits cover labor standards plus health and safety, 4-pillar adds environment and business ethics.",
            keywords=["SMETA 7", "sedex", "workplace requirements", "management system", "self-check", "business ethics", "collaborative action required", "eti base code"],
            evidence_examples=["SMETA 7 self-check", "Workplace requirement matrix", "Management Systems Assessment evidence"],
            framework_refs=["SMETA 7.0", "ETI Base Code"],
        ),
    ],
    "sa8000": [
        RequirementItem(
            id="social-performance-team",
            title="Social performance team and management system",
            description="A cross-functional team, worker representative mechanism, risk assessment, and internal monitoring are established.",
            keywords=["social performance team", "worker representative", "risk assessment", "internal monitoring"],
            evidence_examples=["SPT charter", "worker representative record", "internal monitoring plan"],
            framework_refs=["SA8000"],
        ),
        RequirementItem(
            id="labor-performance-criteria",
            title="Labor performance criteria",
            description="Child labor, forced labor, health and safety, freedom of association, discrimination, discipline, hours, and remuneration are controlled.",
            keywords=["child labor", "forced labor", "freedom of association", "working hours", "remuneration"],
            evidence_examples=["Labor procedure pack", "payroll review", "worker grievance records"],
            framework_refs=["SA8000"],
        ),
        RequirementItem(
            id="certification-audit-readiness",
            title="Certification audit readiness",
            description="Internal audits, management reviews, corrective actions, and certification scope are ready.",
            keywords=["certification", "internal audit", "management review", "corrective action", "scope"],
            evidence_examples=["Internal audit report", "management review minutes", "certification scope memo"],
            framework_refs=["SA8000"],
        ),
        RequirementItem(
            id="sa8000-2026-transition",
            title="SA8000:2026 standard transition",
            description="The organization maps decent-work performance criteria, management-system updates, and indicator-library evidence to the 2026 standard.",
            keywords=["SA8000:2026", "decent work", "indicator library", "performance criteria", "management system"],
            evidence_examples=["2026 transition checklist", "Indicator-library map", "Management-system update log"],
            framework_refs=["SA8000"],
        ),
    ],
    "aa1000": [
        RequirementItem(
            id="accountability-principles",
            title="AccountAbility principles evidence",
            description="Inclusivity, materiality, responsiveness, and impact principles are translated into evidence and controls.",
            keywords=["inclusivity", "materiality", "responsiveness", "impact", "principle"],
            evidence_examples=["Principles mapping", "stakeholder engagement evidence", "response tracker"],
            framework_refs=["AA1000AP"],
        ),
        RequirementItem(
            id="assurance-engagement-type",
            title="Assurance engagement type",
            description="Assurance type, level, scope, subject matter, criteria, and limitations are defined before engagement.",
            keywords=["assurance", "type 1", "type 2", "level", "scope", "criteria", "limitations"],
            evidence_examples=["Assurance scope memo", "criteria matrix", "assurance provider brief"],
            framework_refs=["AA1000AS"],
        ),
        RequirementItem(
            id="four-principles-process",
            title="Four-principles and assurance process",
            description="Inclusivity, materiality, responsiveness, and impact are connected to engagement planning, evidence testing, findings, and management response.",
            keywords=["four principles", "inclusivity", "materiality", "responsiveness", "impact", "assurance process"],
            evidence_examples=["Principles-to-evidence matrix", "Assurance process timeline", "Management response tracker"],
            framework_refs=["AA1000AP", "AA1000AS"],
        ),
    ],
    "eu-green-deal": [
        RequirementItem(
            id="regulation-router",
            title="EU sustainability regulation router",
            description="Product, sector, company size, and market role are routed to relevant EU Green Deal laws.",
            keywords=["green deal", "regulation", "sector", "product", "company size", "market role"],
            evidence_examples=["EU regulation applicability map", "customer request log", "market role memo"],
            framework_refs=["European Green Deal"],
        ),
        RequirementItem(
            id="timeline-and-clause-map",
            title="Timeline and clause map",
            description="Compliance milestones, delegated acts, customer data requests, and accountable owners are mapped.",
            keywords=["timeline", "delegated act", "deadline", "clause", "owner", "compliance"],
            evidence_examples=["Compliance timeline", "clause map", "owner matrix"],
            framework_refs=["European Green Deal"],
        ),
        RequirementItem(
            id="china-exporter-customer-requests",
            title="China exporter customer request workflow",
            description="EU customer data requests are translated into product, carbon, supply-chain, DPP, and due-diligence evidence tasks for exporters.",
            keywords=["China exporter", "EU customer", "data request", "product data", "supply chain", "DPP"],
            evidence_examples=["Customer request register", "Exporter evidence task list", "EU buyer response pack"],
            framework_refs=["European Green Deal"],
        ),
        RequirementItem(
            id="green-deal-law-portfolio",
            title="Green Deal law portfolio",
            description="CBAM, Batteries, ESPR, EUDR, CSRD/ESRS, CSDDD, and other Green Deal-linked laws are mapped to business exposure.",
            keywords=["CBAM", "battery", "ESPR", "EUDR", "CSRD", "CSDDD", "law portfolio"],
            evidence_examples=["EU law exposure map", "Regulation-to-product matrix", "Compliance owner portfolio"],
            framework_refs=["European Green Deal"],
        ),
    ],
    "battery": [
        RequirementItem(
            id="battery-classification",
            title="Battery classification and role",
            description="Battery category, economic operator role, and EU market pathway are classified.",
            keywords=["battery category", "economic operator", "portable", "industrial", "ev battery", "market"],
            evidence_examples=["Battery classification memo", "operator role map", "product SKU list"],
            framework_refs=["Regulation (EU) 2023/1542"],
        ),
        RequirementItem(
            id="battery-dpp-fields",
            title="Battery passport data fields",
            description="Digital product passport fields, carbon footprint, recycled content, due diligence, and performance data are prepared.",
            keywords=["digital product passport", "dpp", "carbon footprint", "recycled content", "due diligence", "performance"],
            evidence_examples=["Battery passport data map", "carbon footprint declaration", "recycled-content evidence"],
            framework_refs=["Regulation (EU) 2023/1542"],
        ),
        RequirementItem(
            id="battery-regulatory-timeline",
            title="Battery Regulation milestone timeline",
            description="Key milestones are calendared per category: carbon-footprint declarations for EV batteries (18 February 2025, subject to delegated/implementing acts), rechargeable industrial batteries above 2 kWh (18 February 2026), and LMT batteries (18 August 2028); the digital battery passport becomes mandatory 18 February 2027; minimum recycled-content shares (16% cobalt, 85% lead, 6% lithium, 6% nickel) apply from 18 August 2031.",
            keywords=["timeline", "carbon footprint declaration", "battery passport", "2027", "recycled content", "delegated act", "milestone"],
            evidence_examples=["Battery compliance calendar", "Delegated-act watchlist", "Category milestone matrix"],
            framework_refs=["Regulation (EU) 2023/1542"],
        ),
    ],
    "eudr": [
        RequirementItem(
            id="commodity-product-screen",
            title="Commodity and product screen",
            description="Relevant commodities, derived products, HS codes, and EU placing/export role are checked.",
            keywords=["commodity", "hs code", "wood", "rubber", "soy", "coffee", "cocoa", "palm oil", "cattle"],
            evidence_examples=["EUDR product screen", "commodity sourcing list", "customer role memo"],
            framework_refs=["Regulation (EU) 2023/1115"],
        ),
        RequirementItem(
            id="geolocation-traceability",
            title="Geolocation and traceability",
            description="Plot geolocation, supplier chain, production date, and traceability evidence are collected.",
            keywords=["geolocation", "plot", "traceability", "supplier chain", "production date"],
            evidence_examples=["Geolocation dataset", "supplier traceability file", "farm plot evidence"],
            framework_refs=["Regulation (EU) 2023/1115"],
        ),
        RequirementItem(
            id="dds-risk-mitigation",
            title="Due diligence statement and risk mitigation",
            description="Risk assessment, country risk, mitigation steps, and due-diligence statement workflow are ready.",
            keywords=["due diligence statement", "risk assessment", "country risk", "mitigation", "DDS"],
            evidence_examples=["EUDR risk assessment", "mitigation log", "DDS draft"],
            framework_refs=["Regulation (EU) 2023/1115"],
        ),
        RequirementItem(
            id="country-risk-classification",
            title="Country risk classification",
            description="Country risk level, supplier geography, and product origin are checked before simplified or full due diligence is selected.",
            keywords=["country risk", "risk classification", "origin", "supplier geography", "simplified due diligence"],
            evidence_examples=["Country risk note", "Origin-country list", "Supplier geography map"],
            framework_refs=["Regulation (EU) 2023/1115"],
        ),
        RequirementItem(
            id="application-timeline",
            title="EUDR application timeline and operator category",
            description="The amended application dates are mapped to the operator's size category: 30 December 2026 for large and medium-sized companies (and timber-sector micro/small enterprises), 30 June 2027 for other micro and small enterprises; micro and small primary operators may use the one-time simplified declaration introduced by Regulation (EU) 2025/2650.",
            keywords=["30 december 2026", "30 june 2027", "application date", "micro", "small", "simplified declaration", "primary operator"],
            evidence_examples=["Operator size classification memo", "EUDR readiness timeline", "Simplified-declaration eligibility note"],
            framework_refs=["Regulation (EU) 2023/1115", "Regulation (EU) 2025/2650"],
        ),
    ],
    "csddd": [
        RequirementItem(
            id="risk-based-hrdd",
            title="Risk-based human rights and environmental due diligence",
            description="Supply-chain impacts are identified, prioritized, prevented, mitigated, and tracked.",
            keywords=["human rights", "environmental due diligence", "risk-based", "prevent", "mitigate", "track"],
            evidence_examples=["HRDD risk register", "supplier risk heatmap", "mitigation action plan"],
            framework_refs=["CSDDD", "OECD Due Diligence Guidance"],
        ),
        RequirementItem(
            id="supplier-self-check",
            title="Supplier self-check and contractual controls",
            description="Supplier questionnaires, contractual assurances, monitoring, and escalation are documented.",
            keywords=["supplier self-check", "contractual assurance", "monitoring", "escalation", "questionnaire"],
            evidence_examples=["Supplier self-assessment", "contract clause map", "monitoring plan"],
            framework_refs=["CSDDD"],
        ),
    ],
    "espr": [
        RequirementItem(
            id="product-category-router",
            title="Product category and ecodesign router",
            description="Product categories are screened for delegated acts and ecodesign parameters.",
            keywords=["product category", "delegated act", "ecodesign", "durability", "repairability", "recyclability"],
            evidence_examples=["Product category screen", "ecodesign parameter map", "delegated-act watchlist"],
            framework_refs=["ESPR"],
        ),
        RequirementItem(
            id="dpp-data-model",
            title="Digital product passport data model",
            description="Product identifier, materials, substances, lifecycle, circularity, and access-control fields are mapped.",
            keywords=["digital product passport", "dpp", "identifier", "materials", "substances", "circularity"],
            evidence_examples=["DPP data model", "substances register", "lifecycle data pack"],
            framework_refs=["ESPR"],
        ),
        RequirementItem(
            id="priority-product-coverage",
            title="Priority product coverage",
            description="Steel, textiles, furniture, tyres, and other priority product groups are screened for ecodesign and DPP preparation.",
            keywords=["steel", "textile", "furniture", "tyre", "tire", "priority product", "ecodesign"],
            evidence_examples=["Priority product screen", "SKU-to-product-group map", "Delegated-act watchlist"],
            framework_refs=["ESPR"],
        ),
        RequirementItem(
            id="ecodesign-parameter-pack",
            title="Ecodesign parameter pack",
            description="Durability, repairability, recyclability, recycled content, substances of concern, and resource-efficiency parameters are gathered.",
            keywords=["durability", "repairability", "recyclability", "recycled content", "substances of concern", "resource efficiency"],
            evidence_examples=["Ecodesign parameter table", "Repairability evidence", "Recycled-content support"],
            framework_refs=["ESPR"],
        ),
    ],
    "amfori-bsci": [
        RequirementItem(
            id="performance-area-map",
            title="BSCI performance-area map",
            description="Thirteen social performance areas are mapped to policies, records, worker evidence, and site controls.",
            keywords=["performance area", "social management", "worker", "working hours", "remuneration", "occupational health"],
            evidence_examples=["Performance-area checklist", "worker records", "site control evidence"],
            framework_refs=["amfori BSCI"],
        ),
        RequirementItem(
            id="audit-rating-capa",
            title="Audit rating and CAPA preparation",
            description="Audit grades, non-compliances, corrective actions, and improvement plan evidence are tracked.",
            keywords=["audit rating", "A", "B", "C", "D", "E", "corrective action", "improvement"],
            evidence_examples=["Audit grade history", "CAPA tracker", "improvement plan"],
            framework_refs=["amfori BSCI"],
        ),
        RequirementItem(
            id="audit-question-bank",
            title="81-question audit self-check",
            description="The 13 performance areas are translated into the 81 audit-question evidence set and owner workflow.",
            keywords=["81", "audit question", "self-check", "13 performance areas", "owner", "evidence"],
            evidence_examples=["81-question self-check", "Question owner matrix", "Audit evidence pack"],
            framework_refs=["amfori BSCI"],
        ),
        RequirementItem(
            id="continuous-improvement-cycle",
            title="Continuous improvement cycle",
            description="Online self-assessment, audit findings, A-E rating outcomes, root causes, and improvement plan updates are tracked over time.",
            keywords=["continuous improvement", "online self-assessment", "A-E rating", "root cause", "improvement plan"],
            evidence_examples=["Self-assessment record", "Root-cause analysis", "Improvement plan history"],
            framework_refs=["amfori BSCI"],
        ),
    ],
    "rba": [
        RequirementItem(
            id="code-section-readiness",
            title="RBA Code section readiness",
            description="Labor, health and safety, environmental, ethics, and management-system sections are evidenced.",
            keywords=["labor", "health and safety", "environmental", "ethics", "management system", "code"],
            evidence_examples=["RBA code gap assessment", "policy pack", "site evidence index"],
            framework_refs=["RBA Code of Conduct"],
        ),
        RequirementItem(
            id="vap-score-prep",
            title="VAP score and audit preparation",
            description="Validated Assessment Program score drivers, priority findings, and closure evidence are prepared.",
            keywords=["VAP", "score", "priority finding", "audit", "closure", "corrective action"],
            evidence_examples=["VAP preparation workbook", "finding closure evidence", "site audit plan"],
            framework_refs=["RBA VAP"],
        ),
        RequirementItem(
            id="minerals-forced-labor",
            title="Minerals and forced-labor controls",
            description="Conflict-minerals, forced-labor, recruitment-fee, and supply-chain controls are documented.",
            keywords=["conflict minerals", "forced labor", "recruitment fee", "smelter", "supply chain"],
            evidence_examples=["CMRT/EMRT", "forced-labor controls", "supplier due diligence file"],
            framework_refs=["RBA Code of Conduct"],
        ),
        RequirementItem(
            id="recognition-level-route",
            title="Platinum-Gold-Silver recognition route",
            description="VAP score evidence and closure status are mapped to the Platinum, Gold, Silver, or corrective-action preparation route.",
            keywords=["Platinum", "Gold", "Silver", "recognition", "VAP 200", "closure", "priority finding"],
            evidence_examples=["VAP score model", "Recognition route note", "Priority finding closure pack"],
            framework_refs=["RBA VAP"],
        ),
    ],
    "icma": [
        RequirementItem(
            id="bond-type-decision",
            title="Bond type decision",
            description="Use-of-proceeds, sustainability-linked, social, sustainability, or transition bond route is selected.",
            keywords=["green bond", "social bond", "sustainability bond", "sustainability-linked", "transition bond"],
            evidence_examples=["Bond route decision tree", "issuer mandate", "eligible project memo"],
            framework_refs=["ICMA Principles"],
        ),
        RequirementItem(
            id="eligible-projects-kpis",
            title="Eligible projects or KPIs",
            description="Eligible project categories, allocation rules, KPIs, SPTs, and ambition rationale are prepared.",
            keywords=["eligible project", "allocation", "KPI", "SPT", "ambition", "calibration"],
            evidence_examples=["Eligible project list", "KPI methodology", "SPT calibration memo"],
            framework_refs=["ICMA GBP", "ICMA SLBP"],
        ),
        RequirementItem(
            id="external-review-reporting",
            title="External review and reporting",
            description="Second-party opinion, verification, allocation reporting, and impact reporting are planned.",
            keywords=["second party opinion", "SPO", "verification", "allocation report", "impact report"],
            evidence_examples=["SPO scope", "allocation report template", "impact metrics table"],
            framework_refs=["ICMA Guidelines"],
        ),
    ],
    "issb": [
        RequirementItem(
            id="ifrs-s1-core-content",
            title="IFRS S1 core content",
            description="Governance, strategy, risk management, and metrics/targets are mapped for sustainability-related financial disclosures.",
            keywords=["IFRS S1", "governance", "strategy", "risk management", "metrics and targets"],
            evidence_examples=["IFRS S1 disclosure map", "risk management process", "metrics register"],
            framework_refs=["IFRS S1"],
        ),
        RequirementItem(
            id="ifrs-s2-climate",
            title="IFRS S2 climate disclosure",
            description="Climate risks, transition plan, scenario analysis, Scope 1/2/3 emissions, and financed emissions where relevant are evidenced.",
            keywords=["IFRS S2", "climate", "scenario analysis", "transition plan", "Scope 1", "Scope 2", "Scope 3"],
            evidence_examples=["Climate scenario analysis", "transition plan", "GHG inventory"],
            framework_refs=["IFRS S2"],
        ),
        RequirementItem(
            id="sasb-industry-crosswalk",
            title="SASB industry crosswalk",
            description="Industry-based SASB metrics and interoperability references are mapped to the disclosure inventory.",
            keywords=["SASB", "industry-based", "interoperability", "crosswalk", "metric"],
            evidence_examples=["SASB metric map", "industry classification", "interoperability matrix"],
            framework_refs=["SASB Standards"],
        ),
        RequirementItem(
            id="global-adoption-roadmap",
            title="Global adoption roadmap",
            description="Jurisdictional ISSB adoption, transition reliefs, interoperability with ESRS/GRI/TCFD, and filing readiness are tracked.",
            keywords=["global adoption", "jurisdiction", "transition relief", "ESRS", "GRI", "TCFD", "interoperability"],
            evidence_examples=["ISSB adoption tracker", "Interoperability matrix", "Filing-readiness calendar"],
            framework_refs=["ISSB", "IFRS S1", "IFRS S2"],
        ),
    ],
    "climate-bonds": [
        RequirementItem(
            id="taxonomy-screen",
            title="Climate Bonds taxonomy screen",
            description="Assets, activities, and use of proceeds are screened against Climate Bonds taxonomy and sector criteria.",
            keywords=["taxonomy", "sector criteria", "eligible asset", "use of proceeds", "screen"],
            evidence_examples=["Taxonomy eligibility screen", "asset list", "sector criteria memo"],
            framework_refs=["Climate Bonds Taxonomy"],
        ),
        RequirementItem(
            id="certification-verifier",
            title="Certification and verifier readiness",
            description="Pre-issuance/post-issuance certification, verifier scope, and evidence pack are planned.",
            keywords=["certification", "verifier", "pre-issuance", "post-issuance", "evidence"],
            evidence_examples=["Verifier scope", "certification checklist", "evidence pack"],
            framework_refs=["Climate Bonds Standard"],
        ),
        RequirementItem(
            id="allocation-impact-reporting",
            title="Allocation and impact reporting",
            description="Allocation, asset performance, and climate impact reporting metrics are defined.",
            keywords=["allocation", "impact reporting", "asset performance", "climate impact", "proceeds"],
            evidence_examples=["Allocation report", "impact KPI table", "asset performance data"],
            framework_refs=["Climate Bonds Standard"],
        ),
    ],
    "nav": [
        RequirementItem(
            id="institution-role-router",
            title="Institution role router",
            description="ESG institutions are categorized by role such as standard-setter, regulator, rating provider, assurance body, or data platform.",
            keywords=["institution", "standard-setter", "regulator", "rating", "assurance", "data platform"],
            evidence_examples=["Institution role map", "source selection log", "tool route recommendation"],
        ),
        RequirementItem(
            id="jurisdiction-sector-filter",
            title="Jurisdiction and sector filter",
            description="Jurisdiction, sector, framework family, and use case are used to route users to relevant sources.",
            keywords=["jurisdiction", "sector", "filter", "framework", "use case"],
            evidence_examples=["Filter output", "jurisdiction map", "sector source list"],
        ),
        RequirementItem(
            id="source-authority-check",
            title="Source authority check",
            description="Official, methodology, secondary, and community sources are distinguished before advice is generated.",
            keywords=["official", "methodology", "secondary", "source", "authority"],
            evidence_examples=["Source authority label", "source register", "methodology citation"],
        ),
        RequirementItem(
            id="ecosystem-timeline-linkage",
            title="Ecosystem timeline and channel linkage",
            description="Institution pages, 1997-2026 timeline events, 28 filters, and links to related ohESG channels are preserved for navigation.",
            keywords=["103", "1997", "2026", "28 filters", "institution page", "channel link", "timeline"],
            evidence_examples=["Institution detail record", "Timeline entry", "Related-channel link map"],
        ),
    ],
    "aws": [
        RequirementItem(
            id="catchment-context",
            title="Catchment context and shared water challenges",
            description="Site catchment, water balance, stakeholders, and shared water challenges are identified.",
            keywords=["catchment", "water balance", "shared water challenge", "stakeholder", "site"],
            evidence_examples=["Catchment map", "water balance", "stakeholder engagement record"],
            framework_refs=["AWS Standard"],
        ),
        RequirementItem(
            id="aws-five-steps",
            title="AWS five-step stewardship workflow",
            description="Gather, commit, plan, implement, evaluate, and communicate evidence is organized for certification.",
            keywords=["gather", "commit", "plan", "implement", "evaluate", "communicate", "certification"],
            evidence_examples=["AWS plan", "implementation evidence", "annual communication"],
            framework_refs=["AWS Standard"],
        ),
        RequirementItem(
            id="certification-level-route",
            title="Core-Gold-Platinum certification route",
            description="Core, Gold, and Platinum level criteria are mapped to site evidence, scoring, and certification planning. The standard-version choice is documented: AWS Standard V3.0 launched 18 March 2026 with a one-year transition, after which all initial and recertification audits use V3.0 (V2.0 surveillance audits continue for existing certificates).",
            keywords=["Core", "Gold", "Platinum", "50", "15", "certification level", "criteria", "V3.0", "transition"],
            evidence_examples=["AWS level route", "Core criteria checklist", "Gold/Platinum evidence plan", "Standard-version decision note"],
            framework_refs=["AWS Standard V3.0"],
        ),
    ],
    "irma": [
        RequirementItem(
            id="irma-principles-chapters",
            title="IRMA principles and chapters map",
            description="Business integrity, social responsibility, environmental responsibility, and planning/legacy chapters are mapped.",
            keywords=["business integrity", "social responsibility", "environmental responsibility", "planning", "legacy", "chapter"],
            evidence_examples=["IRMA chapter map", "mine-site evidence index", "management plan register"],
            framework_refs=["IRMA Standard"],
        ),
        RequirementItem(
            id="mine-site-evidence",
            title="Mine-site and stakeholder evidence",
            description="Community, worker, environmental, emergency, and reclamation evidence is ready for mine-site assessment.",
            keywords=["mine site", "community", "worker", "environment", "emergency", "reclamation"],
            evidence_examples=["Community engagement file", "worker records", "reclamation plan"],
            framework_refs=["IRMA Standard"],
        ),
        RequirementItem(
            id="chain-of-custody",
            title="Chain-of-custody readiness",
            description="Material identity, supplier chain, and responsible sourcing claims are documented.",
            keywords=["chain of custody", "traceability", "supplier", "responsible sourcing", "claim"],
            evidence_examples=["Chain-of-custody map", "supplier declarations", "material traceability file"],
            framework_refs=["IRMA"],
        ),
        RequirementItem(
            id="achievement-level-readiness",
            title="Transparency/50/75/100 achievement level readiness",
            description="Mine-site evidence is mapped to IRMA achievement levels and gaps are tracked by principle and chapter.",
            keywords=["Transparency", "IRMA 50", "IRMA 75", "IRMA 100", "achievement level", "chapter"],
            evidence_examples=["Achievement level scorecard", "Chapter gap tracker", "Evidence-by-principle map"],
            framework_refs=["IRMA Standard"],
        ),
    ],
    "conflict-minerals": [
        RequirementItem(
            id="oecd-five-step",
            title="OECD five-step due diligence",
            description="Management systems, risk identification, risk response, third-party audit, and annual reporting are documented.",
            keywords=["five-step", "management system", "risk identification", "risk response", "audit", "annual report"],
            evidence_examples=["OECD step checklist", "risk response plan", "annual minerals report"],
            framework_refs=["OECD Guidance"],
        ),
        RequirementItem(
            id="rmi-template-control",
            title="RMI template and smelter control",
            description="CMRT/EMRT responses, smelter/refiner lists, RMAP status, and supplier follow-up are tracked.",
            keywords=["CMRT", "EMRT", "smelter", "refiner", "RMAP", "supplier follow-up"],
            evidence_examples=["CMRT", "EMRT", "smelter list", "RMAP status file"],
            framework_refs=["RMI"],
        ),
        RequirementItem(
            id="regulation-scope",
            title="Regulatory scope and minerals coverage",
            description="3TG, cobalt, mica, Dodd-Frank, EU 2017/821, and customer-specific scope are screened.",
            keywords=["3TG", "cobalt", "mica", "Dodd-Frank", "EU 2017/821", "customer scope"],
            evidence_examples=["Minerals applicability screen", "customer requirement log", "supplier scope list"],
            framework_refs=["Dodd-Frank", "EU 2017/821"],
        ),
    ],
    "ghg": [
        RequirementItem(
            id="scope3-screening",
            title="Scope 3 category screening",
            description="All relevant Scope 3 categories are screened and material categories have data-quality plans.",
            keywords=["scope 3", "category", "purchased goods", "transport", "use of sold products", "data quality"],
            evidence_examples=["Scope 3 screening", "category data-quality plan", "supplier data request"],
            framework_refs=["GHG Protocol Scope 3 Standard"],
        ),
        RequirementItem(
            id="calculation-tools",
            title="Calculation tools and factor governance",
            description="Calculation workbooks, factor sources, units, and version controls are traceable.",
            keywords=["calculation tool", "emission factor", "unit", "version", "workbook", "QA"],
            evidence_examples=["Calculation workbook", "factor register", "version-control log"],
            framework_refs=["GHG Protocol Calculation Tools"],
        ),
        RequirementItem(
            id="china-grid-factor-route",
            title="China grid-factor route",
            description="China electricity grid emission factors, purchased electricity units, and Scope 2 reporting choices are documented where relevant.",
            keywords=["China", "grid factor", "electricity", "Scope 2", "purchased electricity", "emission factor"],
            evidence_examples=["China grid-factor source note", "Purchased electricity records", "Scope 2 factor decision log"],
            framework_refs=["GHG Protocol Scope 2 Guidance"],
        ),
        RequirementItem(
            id="eight-step-inventory-path",
            title="Eight-step corporate inventory path",
            description="The inventory follows a structured path from purpose and boundary through data collection, calculation, QA, reporting, and improvement.",
            keywords=["eight-step", "8 step", "inventory path", "boundary", "data collection", "QA", "reporting"],
            evidence_examples=["Eight-step inventory plan", "Inventory owner matrix", "Improvement action log"],
            framework_refs=["GHG Protocol Corporate Standard"],
        ),
    ],
}


_DISCLOSURE_ROUTING_REQUIREMENTS = _COMPLETION_REQUIREMENTS["glossary"]


_COMPLETION_METHODS: dict[str, list[CalculatorMethod]] = {
    "material": [
        _method("double-materiality-matrix", "Double-materiality matrix", "priority = impact_materiality + financial_materiality", ["impact_scores", "financial_scores", "stakeholder_inputs"], ["material_topic_matrix"], f"{OHESG_BASE}/material/"),
    ],
    "msci": [
        _method("msci-evidence-gap", "MSCI-style evidence gap scan", "gap = industry_key_issues - evidenced_controls", ["industry", "key_issues", "evidence_index"], ["evidence_gap_list"], f"{OHESG_BASE}/msci/"),
    ],
    "ecovadis": [
        _method("ecovadis-par-cycle", "Policy-action-result readiness cycle", "readiness = policy_coverage + action_evidence + result_kpis", ["theme", "documents", "kpis"], ["theme_readiness"], "https://support.ecovadis.com/hc/en-us/articles/115002531507-What-is-the-EcoVadis-methodology"),
    ],
    "cdp": [
        _method("cdp-module-routing", "CDP questionnaire module routing", "modules = environmental_topics + sector + supply_chain_request", ["topics", "sector", "customer_request"], ["required_modules"], "https://www.cdp.net/en/guidance"),
    ],
    "csa": [
        _method("csa-topic-map", "CSA topic evidence map", "topic_readiness = questionnaire_topics x evidence_owners", ["industry", "topics", "owners"], ["topic_evidence_map"], "https://www.spglobal.com/esg/csa/"),
    ],
    "gri": [
        _method("gri-content-index", "GRI content-index builder", "content_index = general_disclosures + material_topic_disclosures + omissions", ["gri_2", "material_topics", "topic_standards"], ["gri_content_index"], "https://www.globalreporting.org/standards/"),
    ],
    "esrs": [
        _method("esrs-datapoint-readiness", "ESRS datapoint readiness map", "dr_readiness = materiality_scope + datapoint_inventory + evidence_owner", ["material_topics", "datapoints", "owners"], ["esrs_gap_map"], "https://www.efrag.org/en/sustainability-reporting/esrs-workstreams/sector-agnostic-standards-set-1-esrs"),
    ],
    "iss": [
        _method("iss-controversy-review", "ISS controversy and issuer-data review", "review_priority = controversy_severity + public_data_gap", ["controversies", "public_sources", "issuer_evidence"], ["issuer_review_actions"], f"{OHESG_BASE}/iss/"),
    ],
    "cbam-export": [
        _method("cbam-cn-screen", "CBAM CN-code applicability screen", "applicability = cn_code in covered_goods + eu_import_role", ["cn_code", "product_description", "market_role"], ["cbam_applicability"], "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en"),
    ],
    "cbam-steel": [
        _method("cbam-embedded-emissions", "CBAM embedded-emissions prep", "embedded_emissions = direct_emissions + indirect_emissions + precursor_adjustments", ["production_route", "activity_data", "precursors"], ["embedded_emissions_pack"], "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en"),
    ],
    "cbam": [
        _method("cbam-decision-tree", "CBAM compliance decision tree", "obligations = covered_goods + import_role + transition_or_definitive_period", ["cn_code", "country", "role", "date"], ["cbam_obligation_route"], "https://eur-lex.europa.eu/eli/reg/2023/956/oj"),
    ],
    "glossary": [
        _method("term-to-tool-router", "ESG term to toolbox router", "routes = matched_terms + category + jurisdiction", ["query", "sector", "jurisdiction"], ["recommended_tool_ids"], f"{OHESG_BASE}/glossary/"),
    ],
    "smeta": [
        _method("smeta-audit-gap", "SMETA audit gap screen", "audit_gap = required_workplace_controls - evidenced_controls", ["site_profile", "worker_records", "policies"], ["audit_gap_list"], "https://www.sedex.com/solutions/smeta-audit/"),
    ],
    "sa8000": [
        _method("sa8000-management-system", "SA8000 management-system readiness", "readiness = performance_criteria + management_system + worker_evidence", ["performance_evidence", "management_system", "worker_records"], ["certification_readiness"], "https://sa-intl.org/programs/sa8000/"),
    ],
    "aa1000": [
        _method("aa1000-assurance-scope", "AA1000 assurance scope builder", "scope = principles + subject_matter + assurance_type + assurance_level", ["principles", "subject_matter", "criteria"], ["assurance_scope"], "https://www.accountability.org/standards/"),
    ],
    "eu-green-deal": [
        _method("eu-regulation-router", "EU Green Deal regulation router", "route = product + sector + market_role + company_size", ["product", "sector", "market_role", "company_size"], ["applicable_regulations"], "https://commission.europa.eu/strategy-and-policy/priorities-2019-2024/european-green-deal_en"),
    ],
    "battery": [
        _method("battery-dpp-readiness", "EU battery passport readiness", "dpp_readiness = battery_category + carbon_footprint + due_diligence + recycled_content", ["battery_category", "operator_role", "product_data"], ["battery_dpp_gap_map"], "https://eur-lex.europa.eu/eli/reg/2023/1542/oj"),
    ],
    "eudr": [
        _method("eudr-dds-readiness", "EUDR due-diligence statement readiness", "dds = product_scope + geolocation + risk_assessment + mitigation", ["commodity", "geolocation", "country_risk", "supplier_chain"], ["dds_readiness"], "https://environment.ec.europa.eu/topics/forests/deforestation/regulation-deforestation-free-products_en"),
    ],
    "csddd": [
        _method("csddd-risk-prioritization", "CSDDD value-chain risk prioritization", "priority = severity + likelihood + leverage + value_chain_position", ["impacts", "suppliers", "countries", "leverage"], ["prioritized_hrdd_actions"], "https://commission.europa.eu/business-economy-euro/doing-business-eu/sustainability-due-diligence-responsible-business/corporate-sustainability-due-diligence_en"),
    ],
    "espr": [
        _method("espr-dpp-router", "ESPR product and DPP router", "requirements = product_category + delegated_act + dpp_fields", ["product_category", "product_data", "market_role"], ["ecodesign_dpp_requirements"], "https://commission.europa.eu/energy-climate-change-environment/standards-tools-and-labels/products-labelling-rules-and-requirements/ecodesign-sustainable-products-regulation_en"),
    ],
    "amfori-bsci": [
        _method("bsci-performance-gap", "amfori BSCI performance-area gap screen", "gap = performance_areas - site_evidence", ["site_profile", "worker_records", "audit_history"], ["performance_area_gaps"], "https://www.amfori.org/en/solutions/social/about-bsci"),
    ],
    "rba": [
        _method("rba-vap-prep", "RBA VAP preparation map", "vap_readiness = code_sections + site_controls + closure_evidence", ["code_evidence", "site_controls", "audit_findings"], ["vap_preparation_gaps"], "https://www.responsiblebusiness.org/code-of-conduct/"),
    ],
    "icma": [
        _method("bond-route-decision", "Sustainable bond route decision", "route = use_of_proceeds_or_kpi + issuer_strategy + review_need", ["financing_objective", "eligible_projects", "kpis"], ["bond_framework_route"], "https://www.icmagroup.org/sustainable-finance/"),
    ],
    "issb": [
        _method("issb-four-pillar-map", "ISSB four-pillar disclosure map", "readiness = governance + strategy + risk_management + metrics_targets", ["disclosures", "climate_data", "industry_metrics"], ["ifrs_s1_s2_gap_map"], "https://www.ifrs.org/sustainability/knowledge-hub/introduction-to-issb-and-ifrs-sustainability-disclosure-standards/"),
    ],
    "climate-bonds": [
        _method("cbi-certification-path", "Climate Bonds certification path", "path = taxonomy_eligibility + verifier_scope + reporting_plan", ["assets", "use_of_proceeds", "verifier"], ["certification_readiness"], "https://www.climatebonds.net/standard"),
    ],
    "nav": [
        _method("institution-router", "ESG institution router", "route = role + jurisdiction + use_case + sector", ["role", "jurisdiction", "use_case", "sector"], ["recommended_sources"], f"{OHESG_BASE}/nav/"),
    ],
    "aws": [
        _method("aws-five-step-check", "AWS five-step certification check", "readiness = gather + commit + plan + implement + evaluate_communicate", ["site", "catchment", "water_data", "plan"], ["aws_certification_gaps"], "https://a4ws.org/aws-standard/"),
    ],
    "irma": [
        _method("irma-achievement-level", "IRMA achievement-level preparation", "level_readiness = chapter_evidence + stakeholder_evidence + site_controls", ["mine_site", "chapter_evidence", "stakeholder_records"], ["irma_gap_map"], "https://responsiblemining.net/what-we-do/standard/"),
    ],
    "conflict-minerals": [
        _method("minerals-traceability-gap", "Responsible minerals traceability gap screen", "gap = supplier_scope + smelter_status + risk_response", ["suppliers", "minerals", "smelters", "countries"], ["minerals_due_diligence_gaps"], "https://www.oecd.org/corporate/mne/mining.htm"),
    ],
    "ghg": [
        _method("ghg-inventory-path", "GHG inventory eight-step path", "inventory = boundary + data + factors + calculation + QA + report", ["boundary", "activity_data", "emission_factors", "calculation_tools"], ["inventory_readiness"], "https://ghgprotocol.org/calculation-tools"),
    ],
}


_COMPLETION_SOURCES: dict[str, list[SourceRecord]] = {
    "material": [
        _official("GRI 3: Material Topics", "https://www.globalreporting.org/standards/standards-development/universal-standards/", "GRI", source_type="methodology"),
        _official("IFRS S1 General Requirements", "https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/ifrs-s1-general-requirements/", "IFRS Foundation", source_type="methodology"),
    ],
    "msci": [_official("MSCI ESG Ratings", "https://www.msci.com/our-solutions/esg-investing/esg-ratings", "MSCI", source_type="methodology")],
    "ecovadis": [_official("EcoVadis scorecards and methodology", "https://support.ecovadis.com/hc/en-us/sections/360002170531-EcoVadis-Scorecards", "EcoVadis", source_type="methodology")],
    "cdp": [_official("CDP disclosure guidance", "https://www.cdp.net/en/guidance", "CDP", source_type="guidance")],
    "csa": [_official("S&P Global CSA methodology", "https://www.spglobal.com/esg/csa/methodology/", "S&P Global", source_type="methodology")],
    "gri": [_official("GRI Universal Standards", "https://www.globalreporting.org/standards/standards-development/universal-standards/", "GRI", source_type="methodology")],
    "esrs": [
        _official("European Commission CSRD", "https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en", "European Commission", source_type="guidance"),
        _official("Omnibus I Directive (EU) 2026/470 (CSRD/CSDDD simplification)", "https://eur-lex.europa.eu/eli/dir/2026/470/oj", "EUR-Lex", source_type="legislation"),
    ],
    "iss": [_official("ISS ESG solutions", "https://www.issgovernance.com/esg/", "ISS STOXX", source_type="methodology")],
    "cbam-export": [_official("Regulation (EU) 2023/956", "https://eur-lex.europa.eu/eli/reg/2023/956/oj", "EUR-Lex", source_type="legislation")],
    "cbam-steel": [_official("CBAM implementing regulation", "https://eur-lex.europa.eu/eli/reg_impl/2023/1773/oj", "EUR-Lex", source_type="legislation")],
    "cbam": [
        _official("CBAM transitional registry guidance", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en", "European Commission", source_type="guidance"),
        _official("Regulation (EU) 2025/2083 (CBAM Omnibus simplification)", "https://eur-lex.europa.eu/eli/reg/2025/2083/oj", "EUR-Lex", source_type="legislation"),
    ],
    "glossary": [
        _official("GRI Standards", "https://www.globalreporting.org/standards/", "GRI", source_type="methodology"),
        _official("SASB Standards", "https://sasb.ifrs.org/standards/", "IFRS Foundation", source_type="methodology"),
    ],
    "smeta": [_official("Sedex SMETA audit", "https://www.sedex.com/solutions/smeta-audit/", "Sedex", source_type="methodology")],
    "sa8000": [_official("SA8000 resources", "https://sa-intl.org/resources/", "Social Accountability International", source_type="guidance")],
    "aa1000": [_official("AA1000 Assurance Standard", "https://www.accountability.org/standards/aa1000-assurance-standard/", "AccountAbility", source_type="methodology")],
    "eu-green-deal": [_official("European Commission policy and regulations", "https://commission.europa.eu/strategy-and-policy_en", "European Commission", source_type="guidance")],
    "battery": [_official("European Commission batteries policy", "https://environment.ec.europa.eu/topics/waste-and-recycling/batteries_en", "European Commission", source_type="guidance")],
    "eudr": [
        _official("Regulation (EU) 2023/1115", "https://eur-lex.europa.eu/eli/reg/2023/1115/oj", "EUR-Lex", source_type="legislation"),
        _official("Regulation (EU) 2025/2650 (EUDR postponement and simplification)", "https://eur-lex.europa.eu/eli/reg/2025/2650/oj", "EUR-Lex", source_type="legislation"),
    ],
    "csddd": [
        _official("OECD Due Diligence Guidance", "https://www.oecd.org/investment/due-diligence-guidance-for-responsible-business-conduct.htm", "OECD", source_type="guidance"),
        _official("Omnibus I Directive (EU) 2026/470 (CSRD/CSDDD simplification)", "https://eur-lex.europa.eu/eli/dir/2026/470/oj", "EUR-Lex", source_type="legislation"),
    ],
    "espr": [_official("Regulation (EU) 2024/1781", "https://eur-lex.europa.eu/eli/reg/2024/1781/oj", "EUR-Lex", source_type="legislation")],
    "amfori-bsci": [_official("amfori BSCI platform", "https://www.amfori.org/en/solutions/social/about-bsci", "amfori", source_type="methodology")],
    "rba": [_official("RBA Validated Assessment Program", "https://www.responsiblebusiness.org/tools/vap/", "Responsible Business Alliance", source_type="methodology")],
    "icma": [_official("ICMA Principles, Handbooks and Guidelines", "https://www.icmagroup.org/sustainable-finance/the-principles-guidelines-and-handbooks/", "ICMA", source_type="methodology")],
    "issb": [_official("IFRS Sustainability Standards Navigator", "https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/", "IFRS Foundation", source_type="methodology")],
    "climate-bonds": [_official("Climate Bonds Taxonomy", "https://www.climatebonds.net/standard/taxonomy", "Climate Bonds Initiative", source_type="methodology")],
    "nav": [
        _official("IFRS Sustainability", "https://www.ifrs.org/sustainability/", "IFRS Foundation", source_type="methodology"),
        _official("GRI Standards", "https://www.globalreporting.org/standards/", "GRI", source_type="methodology"),
    ],
    "aws": [_official("AWS Standard System", "https://a4ws.org/the-aws-standard-system/", "Alliance for Water Stewardship", source_type="methodology")],
    "irma": [_official("IRMA Assessment Manual", "https://responsiblemining.net/what-we-do/assessment/", "IRMA", source_type="guidance")],
    "conflict-minerals": [
        _official("EU conflict minerals regulation", "https://policy.trade.ec.europa.eu/development-and-sustainability/conflict-minerals-regulation_en", "European Commission", source_type="guidance"),
        _official("Responsible Minerals Initiative tools", "https://www.responsiblemineralsinitiative.org/reporting-templates/", "RMI", source_type="guidance"),
    ],
    "ghg": [
        _official("GHG Protocol Corporate Standard", "https://ghgprotocol.org/corporate-standard", "GHG Protocol", source_type="guidance"),
        _official("GHG Protocol Calculation Tools", "https://ghgprotocol.org/calculation-tools", "GHG Protocol", source_type="guidance"),
    ],
}


def _merge_requirements(base: list[RequirementItem], *extras: list[RequirementItem]) -> list[RequirementItem]:
    merged: dict[str, RequirementItem] = {item.id: item for item in base}
    for extra in extras:
        for item in extra:
            merged[item.id] = item
    return list(merged.values())


def _merge_sources(base: list[SourceRecord], extra: list[SourceRecord]) -> list[SourceRecord]:
    merged: dict[str, SourceRecord] = {item.url.lower(): item for item in base}
    for item in extra:
        merged[item.url.lower()] = item
    return list(merged.values())


def _merge_methods(base: list[CalculatorMethod], extra: list[CalculatorMethod]) -> list[CalculatorMethod]:
    merged: dict[str, CalculatorMethod] = {item.id: item for item in base}
    for item in extra:
        merged[item.id] = item
    return list(merged.values())


def _merge_source_index(base: list[ToolboxSourceIndexRecord], extra: list[ToolboxSourceIndexRecord]) -> list[ToolboxSourceIndexRecord]:
    merged: dict[str, ToolboxSourceIndexRecord] = {item.record_id: item for item in base}
    for item in extra:
        merged[item.record_id] = item
    return list(merged.values())


def _source_index_from_snapshot(tool_id: str) -> list[ToolboxSourceIndexRecord]:
    """Build compact runtime search records from archived ohESG embedded data."""
    page = _OHESG_PAGES.get(tool_id, {})
    embedded = page.get("embedded_data", {})
    if not isinstance(embedded, dict):
        return []

    records: list[ToolboxSourceIndexRecord] = []
    for dataset_name, dataset in embedded.items():
        records.extend(_extract_source_records(tool_id, str(dataset_name), dataset))
    return records


def _extract_source_records(tool_id: str, dataset_name: str, value: object, prefix: str = "") -> list[ToolboxSourceIndexRecord]:
    records: list[ToolboxSourceIndexRecord] = []
    if isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, dict):
                record = _record_from_mapping(tool_id, dataset_name, item, f"{prefix}{index}")
                if record:
                    records.append(record)
            elif isinstance(item, list):
                records.extend(_extract_source_records(tool_id, dataset_name, item, f"{prefix}{index}-"))
        return records

    if not isinstance(value, dict):
        return records

    record = _record_from_mapping(tool_id, dataset_name, value, prefix.rstrip("-") or "root")
    if record:
        records.append(record)

    for key, nested in value.items():
        if isinstance(nested, list):
            for index, item in enumerate(nested):
                if isinstance(item, dict):
                    child = _record_from_mapping(tool_id, dataset_name, item, f"{prefix}{key}-{index}")
                    if child:
                        records.append(child)
                    records.extend(_extract_nested_children(tool_id, dataset_name, item, f"{prefix}{key}-{index}-"))
                elif isinstance(item, list):
                    records.extend(_extract_source_records(tool_id, dataset_name, item, f"{prefix}{key}-{index}-"))
        elif isinstance(nested, dict):
            records.extend(_extract_source_records(tool_id, dataset_name, nested, f"{prefix}{key}-"))
    return _dedupe_source_records(records)


def _extract_nested_children(tool_id: str, dataset_name: str, item: dict[str, object], prefix: str) -> list[ToolboxSourceIndexRecord]:
    records: list[ToolboxSourceIndexRecord] = []
    for key, nested in item.items():
        if isinstance(nested, (list, dict)):
            records.extend(_extract_source_records(tool_id, dataset_name, nested, f"{prefix}{key}-"))
    return records


def _record_from_mapping(
    tool_id: str,
    dataset_name: str,
    item: dict[str, object],
    fallback_id: str,
) -> ToolboxSourceIndexRecord | None:
    title = _first_text(
        item,
        "title",
        "titleEn",
        "titleCn",
        "name_en",
        "name_zh",
        "term",
        "term_en",
        "criteriaTitleCn",
        "stepTitleCn",
        "summaryCn",
        "key_issue_name_en",
        "key_issue_name_zh",
    )
    summary = _first_text(
        item,
        "summary",
        "summary_zh",
        "meaning",
        "note",
        "problem",
        "whenToUse",
        "industry_description",
        "rating_focus_summary",
        "why_it_matters",
        "short_definition",
        "definition",
        "intentCn",
        "summaryCn",
        "industry_specific_interpretation",
    )
    if not title and not summary:
        return None

    raw_id = _first_text(
        item,
        "id",
        "slug",
        "code",
        "number",
        "reqNumber",
        "criteriaNumber",
        "stepNumber",
        "term",
        "term_en",
    ) or fallback_id
    record_id = f"{tool_id}:{dataset_name}:{_slugify(raw_id)}"
    url = _first_text(item, "url", "officialUrl", "officialPage", "officialPdf", "detailHref")
    if url.startswith("/"):
        url = f"{OHESG_BASE}{url}"
    record_type = _first_text(item, "type", "tier", "stage", "status", "mvp_priority")
    category = _first_text(item, "category", "sector", "sector_en", "pillar", "issue_category", "category_group")
    keywords = _collect_keywords(item, title, summary)
    metadata = _compact_metadata(item)
    return ToolboxSourceIndexRecord(
        record_id=record_id,
        title=title or raw_id,
        summary=summary,
        url=url,
        record_type=record_type,
        category=category,
        keywords=keywords,
        metadata=metadata,
    )


def _first_text(item: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return ""


def _collect_keywords(item: dict[str, object], *texts: str) -> list[str]:
    values: list[str] = []
    for key in (
        "keywords",
        "search_keywords",
        "key_topics",
        "related",
        "tags",
        "scope",
        "common_assessment_aspects",
        "common_disclosure_points",
        "related_frameworks",
        "related_topic_ids",
        "related_methodology_module_ids",
        "outcomes",
        "actionWords",
    ):
        value = item.get(key)
        if isinstance(value, list):
            values.extend(str(part) for part in value if str(part).strip())
        elif isinstance(value, str):
            values.extend(part.strip() for part in value.replace("/", ",").split(",") if part.strip())
    for text in texts:
        values.extend(_keyword_candidates(text))
    return _dedupe_text(values)[:40]


def _keyword_candidates(text: str) -> list[str]:
    if not text:
        return []
    normalized = text.replace("（", " ").replace("）", " ").replace("(", " ").replace(")", " ")
    chunks = [chunk.strip(" .;:，、。；：[]") for chunk in normalized.replace("/", " ").split()]
    return [chunk for chunk in chunks if len(chunk) >= 2][:20]


def _compact_metadata(item: dict[str, object]) -> dict[str, object]:
    allowed = {
        "code",
        "sector",
        "sector_zh",
        "e_weight",
        "s_weight",
        "g_weight",
        "pillar_weights",
        "prime_threshold",
        "weight",
        "priority_label",
        "version",
        "released",
        "audience",
        "edition",
        "mustRead",
        "tone",
        "tier",
        "outcomes",
        "actionWords",
        "criteriaCount",
        "coreCount",
        "goldCount",
        "platinumCount",
    }
    return {key: value for key, value in item.items() if key in allowed and value not in ("", [], {})}


def _dedupe_source_records(records: list[ToolboxSourceIndexRecord]) -> list[ToolboxSourceIndexRecord]:
    merged: dict[str, ToolboxSourceIndexRecord] = {}
    for record in records:
        merged.setdefault(record.record_id, record)
    return list(merged.values())


def _dedupe_text(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
    return out


def _slugify(value: str) -> str:
    cleaned = value.strip().lower().replace("_", "-").replace(" ", "-").replace("/", "-")
    return "".join(char for char in cleaned if char.isalnum() or char in {"-", "."}) or "record"


def _complete_tool_spec(tool: ToolboxToolSpec) -> ToolboxToolSpec:
    landing = _OHESG_LANDING_TOOLS.get(tool.tool_id, {})
    profile = _OHESG_SOURCE_PROFILES.get(tool.tool_id)
    source_index = _source_index_from_snapshot(tool.tool_id)
    source_title = str(landing.get("title", ""))
    source_description = str(landing.get("description", ""))
    source_tags = [str(tag) for tag in landing.get("tags", [])]
    profile_aliases = []
    if profile:
        profile_aliases = [
            profile.page_title,
            profile.meta_description,
            *profile.headings[:20],
            *profile.keywords[:80],
            *profile.embedded_data_keys,
        ]
    source_aliases = [
        value
        for value in [source_title, source_description, *source_tags, *profile_aliases]
        if value
    ]
    return tool.model_copy(
        update={
            "aliases": [*tool.aliases, *source_aliases],
            "source_title": source_title,
            "source_description": source_description,
            "source_tags": source_tags,
            "source_profile": profile,
            "supported_actions": [
                "get",
                "search",
                "checklist",
                "assess",
                "methodology",
                "crosswalk",
                "source_profile",
                "workflow",
                "input_plan",
                "recommend",
            ],
            "requirements": _merge_requirements(
                tool.requirements,
                _COMPLETION_REQUIREMENTS.get(tool.tool_id, []),
                _DISCLOSURE_ROUTING_REQUIREMENTS if tool.tool_id in {"gri", "esrs"} else [],
            ),
            "sources": _merge_sources(tool.sources, _COMPLETION_SOURCES.get(tool.tool_id, [])),
            "methods": _merge_methods(tool.methods, _COMPLETION_METHODS.get(tool.tool_id, [])),
            "source_index": _merge_source_index(tool.source_index, source_index),
        },
        deep=True,
    )


_EXPLICIT_ALIASES_BY_TOOL_ID = {
    tool.tool_id: [tool.title, *tool.aliases, *tool.tags]
    for tool in TOOLBOX_TOOLS
}

TOOLBOX_TOOLS = tuple(_complete_tool_spec(tool) for tool in TOOLBOX_TOOLS)


_TOOLS_BY_ID = {tool.tool_id: tool for tool in TOOLBOX_TOOLS}
_ALIASES: dict[str, str] = {tool.tool_id: tool.tool_id for tool in TOOLBOX_TOOLS}
for _tool in TOOLBOX_TOOLS:
    for _alias in [_tool.title, *_tool.aliases, *_tool.tags]:
        _ALIASES.setdefault(_alias.lower().replace("_", "-"), _tool.tool_id)
for _tool_id, _aliases in _EXPLICIT_ALIASES_BY_TOOL_ID.items():
    for _alias in _aliases:
        _ALIASES[_alias.lower().replace("_", "-")] = _tool_id


def list_toolbox_tools(category: ToolboxCategory | str | None = None) -> list[ToolboxToolSpec]:
    """Return toolbox tools, optionally filtered by category."""
    if not category or category == "all":
        return list(TOOLBOX_TOOLS)
    return [tool for tool in TOOLBOX_TOOLS if category in tool.categories]


def get_toolbox_tool(tool_id: str) -> ToolboxToolSpec:
    """Get one toolbox tool by ID, tag, title, or alias."""
    key = tool_id.strip().lower().replace("_", "-")
    if key in _TOOLS_BY_ID:
        return _TOOLS_BY_ID[key]
    resolved = _ALIASES.get(key, key)
    try:
        return _TOOLS_BY_ID[resolved]
    except KeyError as exc:
        raise KeyError(f"Unknown ESG toolbox tool: {tool_id}") from exc


def search_toolbox_tools(query: str, category: ToolboxCategory | str | None = None) -> list[ToolboxToolSpec]:
    """Simple deterministic search over title, description, tags, aliases, and requirements."""
    terms = [term for term in query.lower().replace("/", " ").split() if term]
    candidates = list_toolbox_tools(category)
    if not terms:
        return candidates

    matches: list[tuple[int, ToolboxToolSpec]] = []
    for tool in candidates:
        profile = tool.source_profile
        profile_terms: list[str] = []
        if profile:
            profile_terms = [
                profile.page_title,
                profile.meta_description,
                " ".join(profile.headings),
                " ".join(profile.keywords),
                " ".join(profile.embedded_data_keys),
                json.dumps(profile.embedded_data_summary, ensure_ascii=False, sort_keys=True, default=str),
            ]
        core_haystack = " ".join([
            tool.tool_id,
            tool.title,
            tool.description,
            tool.source_title,
            tool.source_description,
            " ".join(tool.tags),
            " ".join(tool.source_tags),
            " ".join(tool.aliases),
            " ".join(tool.sectors),
            " ".join(tool.jurisdictions),
        ]).lower()
        requirement_haystack = " ".join(
            req.title + " " + req.description + " " + " ".join(req.keywords) for req in tool.requirements
        ).lower()
        source_haystack = " ".join([
            " ".join(req.title + " " + req.description + " " + " ".join(req.keywords) for req in tool.requirements),
            " ".join(
                record.title + " " + record.summary + " " + record.category + " " + " ".join(record.keywords)
                for record in tool.source_index
            ),
            " ".join(profile_terms),
        ]).lower()
        haystack = " ".join([core_haystack, requirement_haystack, source_haystack])
        if all(term in haystack for term in terms):
            score = sum(
                core_haystack.count(term) * 8
                + requirement_haystack.count(term) * 4
                + source_haystack.count(term)
                for term in terms
            )
            matches.append((score, tool))
    return [tool for _, tool in sorted(matches, key=lambda item: (-item[0], item[1].tool_id))]
