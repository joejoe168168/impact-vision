"""Both SFDR 2.0 classifiers read one set of facts (data/regulatory/sfdr2.yaml)."""

from __future__ import annotations


def test_classifiers_share_threshold_status_and_categories() -> None:
    from impact_vision.impact.frameworks import sfdr_pai, sfdr_recast

    facts = sfdr_recast.sfdr2_facts()
    assert sfdr_pai._SFDR2_THRESHOLD_PCT == facts["threshold"] * 100
    assert sfdr_pai.SFDR2_POSITIONS == facts["positions"]
    assert facts["status_note"] in sfdr_pai.SFDR2_STATUS_NOTE
    assert set(sfdr_pai.SFDR2_CATEGORY_DESCRIPTIONS) - {"unclassified"} == set(facts["categories"])
    assert sfdr_recast.SFDR_V2_CATEGORY_LABELS["esg_basics"] == "ESG Basics"


def test_every_category_excludes_weapons_tobacco_and_ungc() -> None:
    from impact_vision.impact.frameworks.sfdr_recast import (
        MANDATORY_EXCLUSIONS,
        PortfolioHolding,
        SFDRv2Category,
        classify_sfdr_v2,
    )

    for category in (SFDRv2Category.SUSTAINABLE, SFDRv2Category.TRANSITION, SFDRv2Category.ESG_BASICS):
        assert {"controversial_weapons", "tobacco", "ungc_violations"} <= MANDATORY_EXCLUSIONS[category]
        result = classify_sfdr_v2(
            [PortfolioHolding(name="A", weight=1.0, follows_esg_strategy=True, sector_flags=["tobacco"])],
            category,
        )
        assert not result.eligible and result.exclusion_breaches[0].exclusion_id == "tobacco"


def test_fossil_exclusions_follow_the_benchmark_basis() -> None:
    from impact_vision.impact.frameworks.sfdr_pai import SFDR2Input, classify_sfdr2_category
    from impact_vision.impact.frameworks.sfdr_recast import PortfolioHolding, SFDRv2Category, classify_sfdr_v2

    fossil = [PortfolioHolding(name="A", weight=1.0, follows_esg_strategy=True, sector_flags=["fossil_fuel"])]
    assert not classify_sfdr_v2(fossil, SFDRv2Category.SUSTAINABLE).eligible       # PAB
    assert not classify_sfdr_v2(fossil, SFDRv2Category.TRANSITION).eligible        # expansion
    assert classify_sfdr_v2(fossil, SFDRv2Category.ESG_BASICS).eligible            # CTB only
    sustainable = classify_sfdr2_category(SFDR2Input(current_article=9, pct_strategy_aligned=90,
                                                     coal_revenue_pct_max=2))
    assert any("Paris-aligned" in f for f in sustainable.exclusion_flags)
