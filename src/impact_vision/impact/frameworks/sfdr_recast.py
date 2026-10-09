"""SFDR 2.0 holdings-based eligibility check (formerly ``sfdr_v2``).

Checks a portfolio against a *target* SFDR 2.0 category: the 70% binding-
strategy share and the category's mandatory exclusions. Its companion,
:func:`impact_vision.impact.frameworks.sfdr_pai.classify_sfdr2_category`,
previews which category a fund's signals point to. Both read the same facts
from ``data/regulatory/sfdr2.yaml``.

Decision support, not legal advice: the recast is proposed law, so every
result carries ``legal_status="proposal"`` and the as-of date.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def sfdr2_facts() -> dict[str, Any]:
    """Shared SFDR 2.0 facts (categories, exclusions, threshold, positions)."""
    from impact_vision.impact.knowledge import load_knowledge

    return load_knowledge("regulatory/sfdr2.yaml")


class SFDRv2Category(str, Enum):
    SUSTAINABLE = "sustainable"
    TRANSITION = "transition"
    ESG_BASICS = "esg_basics"
    UNCATEGORISED = "uncategorised"


SFDR_V2_CATEGORY_LABELS: dict[str, str] = {
    **{key: row["label"] for key, row in sfdr2_facts()["categories"].items()},
    "uncategorised": "Unclassified",
}


class ExclusionBreach(BaseModel):
    exclusion_id: str
    category: SFDRv2Category
    holding_name: str
    detail: str
    flag: str = ""  # the holding flag that triggered it (may be a legacy alias)


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
    as_of: str = Field(default_factory=lambda: str(sfdr2_facts()["as_of"]))
    position: str = "council"
    category_label: str = ""
    status_note: str = Field(default_factory=lambda: sfdr2_facts()["status_note"])
    citations: list[str] = Field(
        default_factory=lambda: [str(v) for v in sfdr2_facts()["positions"].values()]
    )


MANDATORY_EXCLUSIONS: dict[SFDRv2Category, set[str]] = {
    **{SFDRv2Category(key): set(row["exclusions"]) for key, row in sfdr2_facts()["categories"].items()},
    SFDRv2Category.UNCATEGORISED: set(),
}


def _expand_flag(flag: str) -> list[str]:
    """Holding flag → exclusion ids (legacy flags like ``fossil_fuel`` fan out)."""
    return list(sfdr2_facts().get("flag_aliases", {}).get(flag, [flag]))


def classify_sfdr_v2(
    holdings: list[PortfolioHolding],
    target_category: SFDRv2Category,
    threshold: float | None = None,
    *,
    position: Literal["commission", "council", "parliament"] = "council",
) -> SFDRv2Result:
    threshold = float(sfdr2_facts()["threshold"]) if threshold is None else threshold
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    total_weight = sum(item.weight for item in holdings)
    aligned_weight = sum(item.weight for item in holdings if item.follows_esg_strategy)
    strategy_share = aligned_weight / total_weight if total_weight else 0.0
    descriptions = sfdr2_facts()["exclusions"]
    breaches: list[ExclusionBreach] = []
    for holding in holdings:
        hit: set[str] = set()
        for flag in holding.sector_flags:
            for exclusion_id in _expand_flag(flag):
                if exclusion_id in MANDATORY_EXCLUSIONS[target_category] and exclusion_id not in hit:
                    hit.add(exclusion_id)
                    breaches.append(ExclusionBreach(
                        exclusion_id=exclusion_id,
                        category=target_category,
                        holding_name=holding.name,
                        flag=flag,
                        detail=f"{descriptions.get(exclusion_id, exclusion_id)}: excluded for the "
                               f"proposed {SFDR_V2_CATEGORY_LABELS[target_category.value]} category",
                    ))
    gaps: list[str] = []
    if strategy_share < threshold:
        gaps.append(f"Binding-strategy share {strategy_share:.1%} is below {threshold:.0%}")
    if breaches:
        gaps.append(f"Resolve {len(breaches)} mandatory-exclusion breach(es)")
    eligible = not gaps and target_category is not SFDRv2Category.UNCATEGORISED
    return SFDRv2Result(
        position=position,
        category=target_category if eligible else SFDRv2Category.UNCATEGORISED,
        eligible=eligible,
        strategy_share=round(strategy_share, 6),
        threshold=threshold,
        exclusion_breaches=breaches,
        gaps=gaps,
        category_label=SFDR_V2_CATEGORY_LABELS[
            (target_category if eligible else SFDRv2Category.UNCATEGORISED).value
        ],
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
        "as_of": result.as_of,
    }


__all__ = [
    "ExclusionBreach",
    "MANDATORY_EXCLUSIONS",
    "PortfolioHolding",
    "SFDRv2Category",
    "SFDRv2Result",
    "SFDR_V2_CATEGORY_LABELS",
    "classify_sfdr_v2",
    "migrate_from_v1",
    "sfdr2_facts",
]
