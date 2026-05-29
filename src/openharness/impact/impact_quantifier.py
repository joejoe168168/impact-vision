"""GIIN-Impact-Lab-style welfare quantifier (QALYs / lives improved).

Converts the GIIN Impact Quantifier's intuition —
**breadth × depth × theme × geography** — into a common welfare unit
(Quality-Adjusted Life Years, QALYs, and "lives meaningfully improved") so that
impact across very different sectors can be compared on a single human-welfare
scale and rolled up to portfolio level.

The arithmetic, in words:

    QALYs ≈ breadth                      (# people reached)
            × depth                       (0-1 share of the welfare gap closed)
            × duration_years              (how long the benefit persists)
            × theme_welfare_weight        (QALYs gained per person-year at full depth)
            × geography_need_multiplier   (underserved geographies → higher need)
            × (1 − counterfactual)        (additionality: net of what would have happened anyway)

    lives_improved ≈ breadth × depth × (1 − counterfactual)

IMPORTANT: the bundled theme weights and geography multipliers are
**illustrative defaults** for demonstration and cross-sector triage, NOT
clinically validated QALY coefficients. For decision-grade welfare estimates,
replace them with GIIN Impact Quantifier coefficients or a peer-reviewed
health-economics source for the relevant population.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# Seeded coefficients (illustrative defaults).
# ---------------------------------------------------------------------------

# QALYs gained per person-year of benefit at full depth (depth = 1.0).
# Health interventions sit near the top; access-to-services interventions
# contribute a smaller welfare increment per person-year.
THEME_WELFARE_WEIGHTS: dict[str, float] = {
    "health": 0.20,
    "healthcare": 0.20,
    "nutrition": 0.15,
    "water_sanitation": 0.12,
    "clean_energy": 0.06,
    "energy_access": 0.06,
    "financial_inclusion": 0.05,
    "education": 0.08,
    "employment": 0.07,
    "housing": 0.07,
    "agriculture": 0.06,
    "food_security": 0.10,
    "gender_equality": 0.06,
    "digital_inclusion": 0.04,
    "climate_adaptation": 0.05,
    "general": 0.05,
}

# Geography need multiplier — higher for underserved / low-income contexts
# where the marginal welfare value of an intervention is greater.
GEOGRAPHY_NEED_MULTIPLIERS: dict[str, float] = {
    "low_income": 1.5,
    "lower_middle_income": 1.25,
    "upper_middle_income": 1.0,
    "high_income": 0.7,
    "ldc": 1.6,
    "fragile_state": 1.7,
    "rural_underserved": 1.4,
    "global": 1.0,
    "unknown": 1.0,
}

# Value of one QALY for optional monetisation (health-economics threshold,
# illustrative). Aligns with the impact_valuation `qaly_gained` factor.
DEFAULT_QALY_VALUE_USD = 50000.0


Geography = Literal[
    "low_income", "lower_middle_income", "upper_middle_income", "high_income",
    "ldc", "fragile_state", "rural_underserved", "global", "unknown",
]


class ImpactQuantifierInput(BaseModel):
    """Inputs for a welfare (QALY) quantification of one intervention."""

    label: str = Field(default="", description="Intervention / company / product label")
    theme: str = Field(default="general", description="Impact theme (see THEME_WELFARE_WEIGHTS)")
    geography: Geography = Field(default="unknown")
    breadth: float = Field(ge=0, description="Number of people reached")
    depth: float = Field(
        default=0.5, ge=0, le=1,
        description="Share of the welfare gap closed per person (0-1); 1.0 = full benefit",
    )
    duration_years: float = Field(default=1.0, ge=0, description="Years the benefit persists")
    counterfactual: float = Field(
        default=0.0, ge=0, le=1,
        description="Share that would have occurred anyway (0-1); subtracted for additionality",
    )
    theme_weight_override: float | None = Field(
        default=None, ge=0,
        description="Override the theme welfare weight (QALYs/person-year at full depth)",
    )
    geography_multiplier_override: float | None = Field(
        default=None, ge=0, description="Override the geography need multiplier",
    )
    invested_usd: float | None = Field(
        default=None, ge=0, description="Capital deployed, for QALYs-per-$ cost-effectiveness",
    )


class ImpactQuantifierResult(BaseModel):
    """Welfare quantification output for one intervention."""

    label: str = ""
    theme: str = "general"
    geography: str = "unknown"
    breadth: float = 0.0
    depth: float = 0.0
    duration_years: float = 0.0
    counterfactual: float = 0.0
    theme_welfare_weight: float = 0.0
    geography_need_multiplier: float = 0.0
    qalys: float = 0.0
    lives_improved: float = 0.0
    invested_usd: float | None = None
    cost_per_qaly_usd: float | None = None
    qaly_value_usd: float = DEFAULT_QALY_VALUE_USD
    notes: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def monetised_welfare_usd(self) -> float:
        """QALYs valued at the QALY threshold (for impact-accounting bridges)."""
        return round(self.qalys * self.qaly_value_usd, 2)


def quantify_welfare(input: ImpactQuantifierInput) -> ImpactQuantifierResult:  # noqa: A002
    """Quantify welfare (QALYs + lives improved) for one intervention."""
    theme_key = input.theme.strip().lower().replace(" ", "_").replace("-", "_")
    theme_weight = (
        input.theme_weight_override
        if input.theme_weight_override is not None
        else THEME_WELFARE_WEIGHTS.get(theme_key, THEME_WELFARE_WEIGHTS["general"])
    )
    geo_mult = (
        input.geography_multiplier_override
        if input.geography_multiplier_override is not None
        else GEOGRAPHY_NEED_MULTIPLIERS.get(input.geography, 1.0)
    )

    additionality = max(0.0, 1.0 - input.counterfactual)
    qalys = (
        input.breadth
        * input.depth
        * input.duration_years
        * theme_weight
        * geo_mult
        * additionality
    )
    lives = input.breadth * input.depth * additionality

    cost_per_qaly = None
    if input.invested_usd and qalys > 0:
        cost_per_qaly = round(input.invested_usd / qalys, 2)

    notes = [
        "Theme weights and geography multipliers are illustrative defaults — "
        "replace with GIIN Impact Quantifier coefficients for decision-grade output.",
        "QALYs are net of the stated counterfactual (additionality).",
    ]
    if theme_key not in THEME_WELFARE_WEIGHTS and input.theme_weight_override is None:
        notes.append(f"Unknown theme {input.theme!r} — used 'general' welfare weight.")

    return ImpactQuantifierResult(
        label=input.label,
        theme=input.theme,
        geography=input.geography,
        breadth=input.breadth,
        depth=input.depth,
        duration_years=input.duration_years,
        counterfactual=input.counterfactual,
        theme_welfare_weight=theme_weight,
        geography_need_multiplier=geo_mult,
        qalys=round(qalys, 3),
        lives_improved=round(lives, 1),
        invested_usd=input.invested_usd,
        cost_per_qaly_usd=cost_per_qaly,
        notes=notes,
    )


class PortfolioWelfareRollup(BaseModel):
    """Portfolio-level welfare roll-up across interventions."""

    holdings: list[ImpactQuantifierResult] = Field(default_factory=list)
    total_qalys: float = 0.0
    total_lives_improved: float = 0.0
    total_invested_usd: float = 0.0
    portfolio_cost_per_qaly_usd: float | None = None
    total_monetised_welfare_usd: float = 0.0
    by_theme_qalys: dict[str, float] = Field(default_factory=dict)
    by_geography_qalys: dict[str, float] = Field(default_factory=dict)


def rollup_welfare(inputs: list[ImpactQuantifierInput]) -> PortfolioWelfareRollup:
    """Quantify and roll up welfare across a portfolio of interventions."""
    holdings = [quantify_welfare(i) for i in inputs]
    total_qalys = round(sum(h.qalys for h in holdings), 3)
    total_lives = round(sum(h.lives_improved for h in holdings), 1)
    total_invested = round(sum(h.invested_usd or 0.0 for h in holdings), 2)
    total_monetised = round(sum(h.monetised_welfare_usd for h in holdings), 2)

    by_theme: dict[str, float] = {}
    by_geo: dict[str, float] = {}
    for h in holdings:
        by_theme[h.theme] = round(by_theme.get(h.theme, 0.0) + h.qalys, 3)
        by_geo[h.geography] = round(by_geo.get(h.geography, 0.0) + h.qalys, 3)

    cost_per_qaly = (
        round(total_invested / total_qalys, 2)
        if total_invested > 0 and total_qalys > 0
        else None
    )

    return PortfolioWelfareRollup(
        holdings=holdings,
        total_qalys=total_qalys,
        total_lives_improved=total_lives,
        total_invested_usd=total_invested,
        portfolio_cost_per_qaly_usd=cost_per_qaly,
        total_monetised_welfare_usd=total_monetised,
        by_theme_qalys=by_theme,
        by_geography_qalys=by_geo,
    )


__all__ = [
    "THEME_WELFARE_WEIGHTS",
    "GEOGRAPHY_NEED_MULTIPLIERS",
    "DEFAULT_QALY_VALUE_USD",
    "Geography",
    "ImpactQuantifierInput",
    "ImpactQuantifierResult",
    "quantify_welfare",
    "PortfolioWelfareRollup",
    "rollup_welfare",
]
