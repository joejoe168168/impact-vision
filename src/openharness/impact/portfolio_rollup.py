"""Capital-weighted portfolio roll-up.

Replaces the legacy arithmetic-mean roll-up of 5D scores (which is
mathematically meaningless across heterogeneous companies — see Phase-11
finding #11) with a $-deployed-weighted version.

Inputs:
  - A list of `(Assessment, capital_eur_m, ownership_pct)` tuples
  - A `FundThesis` (used for SDG / 5D weights — optional)

Outputs:
  - PortfolioRollup with weighted 5D, weighted SDG scores per goal,
    sector exposure tables, and an unweighted-vs-weighted comparison so the
    reader can see how concentration changes the headline number.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from pydantic import BaseModel, Field

from openharness.impact.fund_thesis import FundThesis, weighted_5d_overall
from openharness.impact.models import Assessment


class PortfolioCompanyEntry(BaseModel):
    company_name: str
    sector: str = ""
    capital_eur_m: float = 0.0
    ownership_pct: float = 0.0
    five_d_overall: float = 0.0
    weighted_five_d_overall: float = 0.0
    sdg_alignments: dict[int, float] = Field(default_factory=dict)


class PortfolioRollup(BaseModel):
    fund_name: str
    company_count: int
    total_deployed_eur_m: float
    weighted_5d_overall: float
    unweighted_5d_overall: float
    weighted_sdg_scores: dict[int, float] = Field(default_factory=dict)
    sector_exposure_eur_m: dict[str, float] = Field(default_factory=dict)
    companies: list[PortfolioCompanyEntry] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _five_d_overall(a: Assessment) -> float:
    if a.five_dimensions is None:
        return 0.0
    return float(a.five_dimensions.overall_score)


def rollup_portfolio(
    entries: Iterable[tuple[Assessment, float, float]],
    thesis: FundThesis | None = None,
) -> PortfolioRollup:
    """Roll up a portfolio.

    `entries` is an iterable of `(assessment, capital_eur_m, ownership_pct)`.

    `ownership_pct` is on a 0-100 scale; if 0 it is ignored and the rollup
    uses pure $-deployed weighting.
    """
    items = list(entries)
    if not items:
        return PortfolioRollup(
            fund_name=thesis.name if thesis else "Portfolio",
            company_count=0,
            total_deployed_eur_m=0.0,
            weighted_5d_overall=0.0,
            unweighted_5d_overall=0.0,
        )

    thesis = thesis or FundThesis()  # default equal-weight
    total_capital = sum(max(0.0, c) for _, c, _ in items) or 1.0

    weighted_sum = 0.0
    unweighted_sum = 0.0
    company_rows: list[PortfolioCompanyEntry] = []
    sector_exposure: dict[str, float] = defaultdict(float)
    sdg_weighted_acc: dict[int, float] = defaultdict(float)

    for assessment, capital, ownership in items:
        weight = (max(0.0, capital) / total_capital)
        co_5d = _five_d_overall(assessment)
        w5d = weighted_5d_overall(assessment.five_dimensions, thesis) if assessment.five_dimensions else 0.0

        sector = assessment.company.sector or "Uncategorised"
        sector_exposure[sector] += capital

        unweighted_sum += co_5d
        weighted_sum += co_5d * weight

        per_company_sdg: dict[int, float] = {}
        for a in assessment.sdg_alignments:
            per_company_sdg[a.goal] = a.score
            sdg_weighted_acc[a.goal] += a.score * weight

        company_rows.append(PortfolioCompanyEntry(
            company_name=assessment.company.name or "Unnamed",
            sector=sector,
            capital_eur_m=capital,
            ownership_pct=ownership,
            five_d_overall=round(co_5d, 2),
            weighted_five_d_overall=round(w5d, 2),
            sdg_alignments=per_company_sdg,
        ))

    notes: list[str] = []
    if total_capital == 1.0 and not any(c > 0 for _, c, _ in items):
        notes.append("All capital_eur_m values are 0 — using equal-weight roll-up.")
    if thesis.is_default:
        notes.append("Using default equal-weight fund thesis. Provide one for fund-specific weighting.")

    return PortfolioRollup(
        fund_name=thesis.name,
        company_count=len(items),
        total_deployed_eur_m=round(sum(c for _, c, _ in items), 2),
        weighted_5d_overall=round(weighted_sum, 2),
        unweighted_5d_overall=round(unweighted_sum / len(items), 2),
        weighted_sdg_scores={g: round(s, 1) for g, s in sorted(sdg_weighted_acc.items())},
        sector_exposure_eur_m={s: round(v, 2) for s, v in sorted(sector_exposure.items())},
        companies=company_rows,
        notes=notes,
    )
