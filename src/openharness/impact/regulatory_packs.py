"""Per-jurisdiction regulatory packs (Phase 20).

Static library of the disclosure-regime requirements GPs hit in the
seven most active impact-investing jurisdictions. Each pack enumerates:

* **Mandatory filings** — what must be submitted, at what cadence.
* **Metric mapping** — which IRIS+ / ESRS / SFDR PAI metrics satisfy the
  regime.
* **Thresholds & timelines** — who is in scope and by when.

These are intended as *guidance defaults*. The legal advisor on a deal
should always double-check current wording — regulators update their
technical standards roughly annually.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Jurisdiction = Literal[
    "EU-SFDR", "EU-CSRD", "EU-CSDDD", "UK-FCA-SDR",
    "US-SEC-ESG", "HK-HKEX-ESG", "AU-AASB-S2",
    "GLOBAL-ISSB",
]


class RegulatoryFiling(BaseModel):
    name: str
    cadence: Literal["annual", "semi-annual", "quarterly", "event-driven"]
    format: str = ""
    deadline_days_after_period: int = 120
    mandatory_for: str = "all funds in scope"


class RegulatoryPack(BaseModel):
    jurisdiction: Jurisdiction
    issuer: str
    in_scope_summary: str
    filings: list[RegulatoryFiling]
    required_metrics: list[str] = Field(default_factory=list)
    notes: str = ""
    as_of: str = Field(default="", description="Date the pack was last verified, YYYY-MM-DD")
    legal_basis: str = Field(default="", description="Primary legal citation, e.g. Directive (EU) 2026/470")


_PACKS: dict[str, RegulatoryPack] = {
    "EU-SFDR": RegulatoryPack(
        jurisdiction="EU-SFDR",
        issuer="ESAs (EBA/EIOPA/ESMA)",
        in_scope_summary=(
            "All financial market participants and financial advisers "
            "distributing products in the EU."
        ),
        filings=[
            RegulatoryFiling(name="Principal Adverse Impacts (PAI) statement",
                             cadence="annual", format="RTS Annex I template",
                             deadline_days_after_period=180),
            RegulatoryFiling(name="Article 8/9 periodic report",
                             cadence="annual", format="RTS Annex IV/V template",
                             deadline_days_after_period=120),
        ],
        required_metrics=[
            "scope1_2_tco2e", "scope3_tco2e", "carbon_footprint",
            "gross_energy_consumption_per_meur", "violations_ungc_oecd",
            "board_gender_ratio", "unadjusted_gender_pay_gap",
        ],
    ),
    "EU-CSRD": RegulatoryPack(
        jurisdiction="EU-CSRD",
        issuer="European Commission / EFRAG",
        as_of="2026-03-18",
        legal_basis="Directive (EU) 2026/470 (Omnibus I), in force 2026-03-18",
        in_scope_summary=(
            "POST-OMNIBUS I: mandatory only for undertakings meeting BOTH "
            ">1,000 employees AND >€450M net turnover. Non-EU groups: >€450M EU "
            "turnover with an in-scope EU subsidiary or a >€200M EU branch. "
            "Listed SMEs and most former Wave 2/3 entities are now OUT of scope; "
            "former Wave 1 reporters below the thresholds may pause FY2025-FY2026."
        ),
        filings=[
            RegulatoryFiling(name="ESRS sustainability statement in mgmt report",
                             cadence="annual", format="XBRL digital tagging",
                             deadline_days_after_period=120),
        ],
        required_metrics=[
            "ESRS E1 climate", "ESRS E2 pollution", "ESRS E3 water",
            "ESRS S1 own-workforce", "ESRS G1 business-conduct",
        ],
        notes=(
            "Member States transpose Omnibus I by 2027-03-19; new scope applies "
            "from FY2027. Sector-specific ESRS removed. A SIMPLIFIED ESRS "
            "delegated act is targeted for 2026-09. Undertakings below 1,000 "
            "employees may refuse data requests exceeding the VSME voluntary "
            "standard — use the VSME module for those investees."
        ),
    ),
    "EU-CSDDD": RegulatoryPack(
        jurisdiction="EU-CSDDD",
        issuer="European Commission",
        as_of="2026-03-18",
        legal_basis="CSDDD as amended by Directive (EU) 2026/470 (Omnibus I)",
        in_scope_summary=(
            "POST-OMNIBUS I: applies to companies with >5,000 employees AND "
            ">€1.5B net worldwide turnover (non-EU: >€1.5B EU turnover). "
            "Application deferred to 2029-07-26; MS transposition by 2028-07-26."
        ),
        filings=[
            RegulatoryFiling(
                name="Human-rights & environmental due-diligence statement",
                cadence="annual", format="narrative + value-chain risk register",
                deadline_days_after_period=120),
        ],
        required_metrics=[
            "salient_human_rights_issues", "value_chain_risk_register",
            "grievance_mechanism", "remediation_actions",
        ],
        notes=(
            "Climate transition-plan ADOPTION obligation removed by Omnibus I; "
            "EU-harmonised civil-liability regime removed (national law applies); "
            "penalties capped at 3% of net global turnover. Even when out of legal "
            "scope, OECD Guidelines / UNGP-aligned HRDD remains an LP and customer "
            "expectation — use the hrdd module to evidence it."
        ),
    ),
    "UK-FCA-SDR": RegulatoryPack(
        jurisdiction="UK-FCA-SDR",
        issuer="UK FCA",
        in_scope_summary="UK-authorised asset managers with AUM > £5bn.",
        filings=[
            RegulatoryFiling(name="Sustainability Product Label disclosure",
                             cadence="annual"),
            RegulatoryFiling(name="Entity-level sustainability report",
                             cadence="annual"),
        ],
        required_metrics=[
            "outcome_metric_per_product", "naming_and_marketing_evidence",
        ],
    ),
    "US-SEC-ESG": RegulatoryPack(
        jurisdiction="US-SEC-ESG",
        issuer="US Securities and Exchange Commission",
        in_scope_summary=(
            "All SEC-registered investment companies; climate-disclosure "
            "rule currently in litigation, other ESG naming rules in force."
        ),
        filings=[
            RegulatoryFiling(name="Form N-CSR ESG sections",
                             cadence="semi-annual"),
            RegulatoryFiling(name="Climate-related disclosures in 10-K",
                             cadence="annual"),
        ],
        required_metrics=["ghg_scope1_2", "climate_related_financial_impacts"],
    ),
    "HK-HKEX-ESG": RegulatoryPack(
        jurisdiction="HK-HKEX-ESG",
        issuer="Hong Kong Exchanges and Clearing (HKEX)",
        in_scope_summary="All HKEX-listed issuers; full ISSB alignment from 2025.",
        filings=[
            RegulatoryFiling(name="Environmental, Social and Governance Report",
                             cadence="annual",
                             format="ISSB-aligned from FY2025"),
        ],
        required_metrics=[
            "scope1_ghg", "scope2_ghg", "scope3_ghg",
            "climate-transition-plan", "internal-carbon-price",
        ],
    ),
    "AU-AASB-S2": RegulatoryPack(
        jurisdiction="AU-AASB-S2",
        issuer="Australian Accounting Standards Board",
        in_scope_summary=(
            "Large Australian entities; phased-in from FY2025 via the AASB S2 "
            "climate-related standard (based on IFRS S2)."
        ),
        filings=[
            RegulatoryFiling(name="AASB S2 climate-related disclosures",
                             cadence="annual", format="AASB S2 structured data"),
        ],
        required_metrics=["scope1_ghg", "scope2_ghg", "scope3_ghg", "physical_risk"],
    ),
    "GLOBAL-ISSB": RegulatoryPack(
        jurisdiction="GLOBAL-ISSB",
        issuer="IFRS Foundation / ISSB",
        in_scope_summary="Baseline global sustainability reporting.",
        filings=[
            RegulatoryFiling(name="IFRS S1 general disclosures", cadence="annual"),
            RegulatoryFiling(name="IFRS S2 climate disclosures", cadence="annual"),
        ],
        required_metrics=["ghg_scope1", "ghg_scope2", "ghg_scope3", "transition_plan"],
    ),
}


def list_packs() -> list[RegulatoryPack]:
    return list(_PACKS.values())


def get_pack(jurisdiction: str) -> RegulatoryPack:
    key = jurisdiction.upper()
    if key not in _PACKS:
        raise KeyError(
            f"Unknown jurisdiction '{jurisdiction}'. Known: {sorted(_PACKS)}"
        )
    return _PACKS[key]


__all__ = ["Jurisdiction", "RegulatoryFiling", "RegulatoryPack", "list_packs", "get_pack"]
