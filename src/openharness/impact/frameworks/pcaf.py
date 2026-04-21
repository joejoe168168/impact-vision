"""PCAF — Partnership for Carbon Accounting Financials.

Calculates Scope 3 Category 15 (financed emissions) for a financial
institution's portfolio, following the *PCAF Global GHG Accounting and
Reporting Standard* (Part A, listed equity / corporate bonds; Part B
business loans, project finance and mortgages).

Each portfolio-company entry produces an `attribution_factor` (= outstanding
investment / EVIC) and a `financed_emissions` figure (= attribution_factor
× reported / estimated company emissions).

The calculator produces a per-asset-class roll-up plus a portfolio data
quality score (DQS) on PCAF's 1-5 scale (1 = highest quality).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


AssetClass = Literal[
    "listed_equity",
    "corporate_bonds",
    "business_loans",
    "project_finance",
    "mortgages",
    "commercial_real_estate",
    "motor_vehicle_loans",
    "sovereign_bonds",
]


class FinancedEmissionsInput(BaseModel):
    """One portfolio entry."""
    company_name: str
    asset_class: AssetClass
    outstanding_investment_eur: float
    enterprise_value_eur: float = 0.0
    company_revenue_eur: float = 0.0
    reported_emissions_tco2e: float | None = None
    sector: str = ""
    data_quality_score: int = Field(default=4, ge=1, le=5)


class FinancedEmissionsResult(BaseModel):
    company_name: str
    asset_class: str
    attribution_factor: float
    financed_emissions_tco2e: float
    data_quality_score: int
    methodology: str
    notes: str = ""


class PCAFRollup(BaseModel):
    portfolio_size_eur: float
    company_count: int
    total_financed_emissions_tco2e: float
    by_asset_class: dict[str, float] = Field(default_factory=dict)
    by_sector: dict[str, float] = Field(default_factory=dict)
    weighted_data_quality_score: float
    coverage_pct: float
    entries: list[FinancedEmissionsResult] = Field(default_factory=list)


# Sector-default emission factors (tCO2e per EUR M revenue) — used when a
# company doesn't report. Source: EXIOBASE 3 + PCAF's industry default
# database, simplified to NACE-1 buckets. Indicative only; production users
# should plug in CDP / Trucost data.
SECTOR_DEFAULT_INTENSITY: dict[str, float] = {
    "energy": 4500,
    "utilities": 3500,
    "mining": 2500,
    "extractives": 2500,
    "manufacturing": 600,
    "construction": 400,
    "agriculture": 800,
    "transport": 900,
    "logistics": 900,
    "real estate": 250,
    "retail": 150,
    "financial": 80,
    "fintech": 80,
    "technology": 90,
    "ict": 90,
    "healthcare": 110,
    "education": 80,
    "professional services": 60,
    "default": 200,
}


def _sector_intensity(sector: str) -> float:
    s = (sector or "").lower()
    for key, v in SECTOR_DEFAULT_INTENSITY.items():
        if key in s:
            return v
    return SECTOR_DEFAULT_INTENSITY["default"]


def calculate_financed_emissions(entry: FinancedEmissionsInput) -> FinancedEmissionsResult:
    """Single-entry PCAF calculation.

    Methodology selection:
      - `listed_equity` / `corporate_bonds`: attribution = outstanding / EVIC
      - `business_loans` / `project_finance`: attribution = outstanding / EVIC
        (PCAF Standard Part A also accepts outstanding / total equity + debt)
      - For all asset classes, if `reported_emissions_tco2e` is provided we
        use it; else we estimate from revenue × sector intensity.
    """
    notes_parts: list[str] = []
    if entry.enterprise_value_eur > 0:
        attribution = entry.outstanding_investment_eur / entry.enterprise_value_eur
        denom_label = "EVIC"
    else:
        # If EVIC unknown, assume 100% attribution (common conservative assumption
        # for SME loans where EVIC isn't observable).
        attribution = 1.0
        denom_label = "outstanding (EVIC unknown — conservative attribution=1)"
        notes_parts.append("EVIC not provided; attribution_factor set to 1.0")

    if entry.reported_emissions_tco2e is not None:
        emissions = entry.reported_emissions_tco2e
        method = "reported"
    elif entry.company_revenue_eur > 0:
        intensity = _sector_intensity(entry.sector)
        emissions = (entry.company_revenue_eur / 1_000_000) * intensity
        method = f"estimated from revenue × sector intensity ({intensity} tCO2e/EUR M)"
        notes_parts.append("Emissions estimated; data quality score capped at 4")
    else:
        emissions = 0.0
        method = "unable to compute (no reported emissions and no revenue)"
        notes_parts.append("Insufficient inputs — financed emissions reported as 0; flag for follow-up")

    financed = attribution * emissions

    dqs = entry.data_quality_score
    if entry.reported_emissions_tco2e is None and dqs < 4:
        dqs = 4  # PCAF scoring rule

    return FinancedEmissionsResult(
        company_name=entry.company_name,
        asset_class=entry.asset_class,
        attribution_factor=round(attribution, 4),
        financed_emissions_tco2e=round(financed, 2),
        data_quality_score=dqs,
        methodology=f"attribution={denom_label}; emissions={method}",
        notes="; ".join(notes_parts),
    )


def rollup_pcaf(entries: list[FinancedEmissionsInput]) -> PCAFRollup:
    """Roll up financed emissions for a portfolio."""
    results = [calculate_financed_emissions(e) for e in entries]

    total = sum(r.financed_emissions_tco2e for r in results)
    by_class: dict[str, float] = {}
    by_sector: dict[str, float] = {}
    weighted_dqs_num = 0.0
    weighted_dqs_den = 0.0
    portfolio_size = sum(e.outstanding_investment_eur for e in entries)
    coverage_count = sum(1 for e in entries if e.reported_emissions_tco2e is not None)

    for entry, result in zip(entries, results):
        by_class[result.asset_class] = by_class.get(result.asset_class, 0.0) + result.financed_emissions_tco2e
        by_sector[entry.sector or "Uncategorised"] = by_sector.get(entry.sector or "Uncategorised", 0.0) + result.financed_emissions_tco2e
        weighted_dqs_num += result.data_quality_score * entry.outstanding_investment_eur
        weighted_dqs_den += entry.outstanding_investment_eur

    wdqs = (weighted_dqs_num / weighted_dqs_den) if weighted_dqs_den else 0.0
    coverage = (coverage_count / len(entries) * 100) if entries else 0.0

    return PCAFRollup(
        portfolio_size_eur=portfolio_size,
        company_count=len(entries),
        total_financed_emissions_tco2e=round(total, 2),
        by_asset_class={k: round(v, 2) for k, v in by_class.items()},
        by_sector={k: round(v, 2) for k, v in by_sector.items()},
        weighted_data_quality_score=round(wdqs, 2),
        coverage_pct=round(coverage, 1),
        entries=results,
    )
