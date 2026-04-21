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
    "EU-SFDR", "EU-CSRD", "UK-FCA-SDR",
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
        in_scope_summary=(
            "Large EU and third-country undertakings with EU turnover > €150M; "
            "staggered from FY2024 onwards."
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
