"""SFDR 2.0 category classifier (Commission proposal of 20 November 2025).

This module is decision support, not legal advice.  The proposal is not in
force; every result therefore carries an explicit proposal label and date.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SFDRv2Category(str, Enum):
    SUSTAINABLE = "sustainable"
    TRANSITION = "transition"
    ESG_BASICS = "esg_basics"
    UNCATEGORISED = "uncategorised"


class ExclusionBreach(BaseModel):
    exclusion_id: str
    category: SFDRv2Category
    holding_name: str
    detail: str


class PortfolioHolding(BaseModel):
    name: str
    weight: float = Field(ge=0, le=1)
    follows_esg_strategy: bool = False
    sector_flags: list[str] = Field(default_factory=list)


class SFDRv2Result(BaseModel):
    category: SFDRv2Category
    eligible: bool
    strategy_share: float
    threshold: float = 0.70
    exclusion_breaches: list[ExclusionBreach] = Field(default_factory=list)
    migration_note: str = ""
    gaps: list[str] = Field(default_factory=list)
    legal_status: str = "proposal"
    as_of: str = "2025-11-20"
    citations: list[str] = Field(
        default_factory=lambda: [
            "European Commission SFDR review proposal, COM proposal 2025-11-20",
        ]
    )


MANDATORY_EXCLUSIONS: dict[SFDRv2Category, set[str]] = {
    SFDRv2Category.SUSTAINABLE: {
        "controversial_weapons",
        "tobacco",
        "ungc_violations",
        "fossil_fuel",
    },
    SFDRv2Category.TRANSITION: {
        "controversial_weapons",
        "tobacco",
        "ungc_violations",
    },
    SFDRv2Category.ESG_BASICS: {"controversial_weapons", "ungc_violations"},
    SFDRv2Category.UNCATEGORISED: set(),
}


def classify_sfdr_v2(
    holdings: list[PortfolioHolding],
    target_category: SFDRv2Category,
    threshold: float = 0.70,
) -> SFDRv2Result:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    total_weight = sum(item.weight for item in holdings)
    aligned_weight = sum(item.weight for item in holdings if item.follows_esg_strategy)
    strategy_share = aligned_weight / total_weight if total_weight else 0.0
    breaches = [
        ExclusionBreach(
            exclusion_id=flag,
            category=target_category,
            holding_name=holding.name,
            detail=f"{flag} is excluded for the proposed {target_category.value} category",
        )
        for holding in holdings
        for flag in holding.sector_flags
        if flag in MANDATORY_EXCLUSIONS[target_category]
    ]
    gaps: list[str] = []
    if strategy_share < threshold:
        gaps.append(f"Binding-strategy share {strategy_share:.1%} is below {threshold:.0%}")
    if breaches:
        gaps.append(f"Resolve {len(breaches)} mandatory-exclusion breach(es)")
    eligible = not gaps and target_category is not SFDRv2Category.UNCATEGORISED
    return SFDRv2Result(
        category=target_category if eligible else SFDRv2Category.UNCATEGORISED,
        eligible=eligible,
        strategy_share=round(strategy_share, 6),
        threshold=threshold,
        exclusion_breaches=breaches,
        gaps=gaps,
    )


def migrate_from_v1(article: str, holdings: list[PortfolioHolding]) -> dict:
    article = str(article).strip().lower().removeprefix("article ").removeprefix("art ")
    suggested = {
        "9": SFDRv2Category.SUSTAINABLE,
        "8": SFDRv2Category.ESG_BASICS,
        "6": SFDRv2Category.UNCATEGORISED,
    }.get(article)
    if suggested is None:
        raise ValueError("article must be 6, 8, or 9")
    result = classify_sfdr_v2(holdings, suggested)
    result.migration_note = (
        f"Current Article {article} has no automatic equivalence; candidate "
        f"category is {suggested.value}. Re-paper binding strategy and exclusions."
    )
    return {
        "suggested_category": suggested.value,
        "rationale": result.migration_note,
        "gaps": result.gaps,
        "result": result,
        "legal_status": "proposal",
        "as_of": "2025-11-20",
    }


__all__ = [
    "ExclusionBreach",
    "MANDATORY_EXCLUSIONS",
    "PortfolioHolding",
    "SFDRv2Category",
    "SFDRv2Result",
    "classify_sfdr_v2",
    "migrate_from_v1",
]
