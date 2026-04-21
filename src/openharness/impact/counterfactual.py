"""Counterfactual estimator templates.

Produces a structured "what would have happened anyway?" estimate for an
impact claim. Real counterfactual evaluation requires RCTs or
quasi-experiments (DID, RDD, propensity-score matching) that no template
can substitute for. What this module *does* provide is a defensible
working estimate using GIIN's *additionality* heuristics, so that GPs can
benchmark a deal's net additionality before commissioning a full eval.

Three template families are supported, mirroring the GIIN COMPASS guide:
  1. **Investor additionality** (financial)
  2. **Enterprise additionality** (would the activity have happened anyway?)
  3. **Beneficiary additionality** (would the user have used something else?)

Each template returns a `CounterfactualEstimate` with a point estimate, a
low/high range, and the reasoning trail.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CounterfactualType = Literal["investor", "enterprise", "beneficiary"]


class CounterfactualInput(BaseModel):
    type: CounterfactualType
    sector: str = ""
    geography: str = ""
    capital_eur_m: float = 0.0
    market_maturity: Literal["frontier", "emerging", "mature"] = "emerging"
    alternative_capital_available: bool = True
    alternative_provider_share_pct: float = 0.0   # share of beneficiaries who could use a substitute
    intervention_displaces_existing: bool = False
    target_outcome_value: float | None = None
    target_outcome_unit: str | None = None


class CounterfactualEstimate(BaseModel):
    type: CounterfactualType
    point_estimate_pct_attributable: float
    low_estimate_pct: float
    high_estimate_pct: float
    net_outcome_value: float | None = None
    net_outcome_unit: str | None = None
    rationale: str
    references: list[str] = Field(default_factory=list)


def estimate_investor_additionality(input_data: CounterfactualInput) -> CounterfactualEstimate:
    """Probability that the investment caused activity that wouldn't have happened.

    Heuristic anchors (rough, defensible, not RCT):
      - Frontier market & no alt capital: 80% point (60-95)
      - Emerging market with alt capital: 30% point (10-50)
      - Mature market with alt capital: 10% point (0-25)
    """
    if input_data.market_maturity == "frontier" and not input_data.alternative_capital_available:
        point, low, high = 80.0, 60.0, 95.0
        rationale = "Frontier market with no observable alternative capital — high additionality."
    elif input_data.market_maturity == "frontier":
        point, low, high = 55.0, 35.0, 75.0
        rationale = "Frontier market but some alt capital exists — moderate-high additionality."
    elif input_data.market_maturity == "emerging" and not input_data.alternative_capital_available:
        point, low, high = 60.0, 40.0, 80.0
        rationale = "Emerging market, capital-constrained sector — moderate-high additionality."
    elif input_data.market_maturity == "emerging":
        point, low, high = 30.0, 10.0, 50.0
        rationale = "Emerging market with available alt capital — moderate additionality."
    else:
        point, low, high = 10.0, 0.0, 25.0
        rationale = "Mature market — low investor additionality (capital is fungible)."

    net = None
    if input_data.target_outcome_value is not None:
        net = input_data.target_outcome_value * (point / 100.0)

    return CounterfactualEstimate(
        type="investor",
        point_estimate_pct_attributable=point,
        low_estimate_pct=low,
        high_estimate_pct=high,
        net_outcome_value=net,
        net_outcome_unit=input_data.target_outcome_unit,
        rationale=rationale,
        references=[
            "GIIN COMPASS — The Methodology for Comparing and Assessing Impact (2020)",
            "Brest & Born, 'Unpacking the Impact in Impact Investing' (SSIR, 2013)",
        ],
    )


def estimate_enterprise_additionality(input_data: CounterfactualInput) -> CounterfactualEstimate:
    """Probability that the enterprise's activity is *itself* additional."""
    if input_data.intervention_displaces_existing:
        point, low, high = 25.0, 10.0, 45.0
        rationale = "Intervention displaces an existing service — net enterprise additionality is modest."
    elif input_data.market_maturity == "frontier":
        point, low, high = 80.0, 60.0, 95.0
        rationale = "Greenfield activity in a frontier market — high enterprise additionality."
    else:
        point, low, high = 50.0, 30.0, 70.0
        rationale = "Activity is not displacing an existing service; moderate enterprise additionality."

    net = None
    if input_data.target_outcome_value is not None:
        net = input_data.target_outcome_value * (point / 100.0)

    return CounterfactualEstimate(
        type="enterprise",
        point_estimate_pct_attributable=point,
        low_estimate_pct=low,
        high_estimate_pct=high,
        net_outcome_value=net,
        net_outcome_unit=input_data.target_outcome_unit,
        rationale=rationale,
        references=["GIIN COMPASS Methodology (2020)"],
    )


def estimate_beneficiary_additionality(input_data: CounterfactualInput) -> CounterfactualEstimate:
    """% of beneficiaries who genuinely got a better outcome than they would have otherwise."""
    sub_share = max(0.0, min(100.0, input_data.alternative_provider_share_pct))
    point = max(0.0, 100.0 - sub_share)
    # Range: ±15pp around the substitution-share-implied estimate
    low = max(0.0, point - 15)
    high = min(100.0, point + 15)
    rationale = (
        f"Assumes ~{sub_share:.0f}% of beneficiaries would have accessed an alternative provider; "
        f"the remaining ~{point:.0f}% are net-additional."
    )
    net = None
    if input_data.target_outcome_value is not None:
        net = input_data.target_outcome_value * (point / 100.0)

    return CounterfactualEstimate(
        type="beneficiary",
        point_estimate_pct_attributable=point,
        low_estimate_pct=low,
        high_estimate_pct=high,
        net_outcome_value=net,
        net_outcome_unit=input_data.target_outcome_unit,
        rationale=rationale,
        references=[
            "GIIN COMPASS Methodology (2020)",
            "Karlan & Goldberg — 'Microfinance Evaluation Strategies' (J-PAL, 2011)",
        ],
    )


def estimate_counterfactual(input_data: CounterfactualInput) -> CounterfactualEstimate:
    """Dispatch to the right template based on `input_data.type`."""
    if input_data.type == "investor":
        return estimate_investor_additionality(input_data)
    if input_data.type == "enterprise":
        return estimate_enterprise_additionality(input_data)
    return estimate_beneficiary_additionality(input_data)
