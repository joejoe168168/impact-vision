"""IFVI / VBA-style monetary impact valuation (impact accounting).

Monetises social and environmental outcomes so they can sit on one ledger
alongside financial return — the methodology family pioneered by the
Impact-Weighted Accounts Initiative (Harvard Business School) and now
stewarded by the International Foundation for Valuing Impacts (IFVI) together
with the Value Balancing Alliance (VBA). IFVI maintains a Global Value Factor
Database (~100,000 value factors) and topic methodologies (GHG, air pollution,
land use & conversion, waste, water pollution).

This module ships a small, clearly-labelled set of **illustrative default
value factors** and the arithmetic to turn physical impact quantities into
monetary value (positive benefits and negative costs), a net monetary impact,
a benefit/cost ratio, and an impact intensity relative to a financial figure
(invested capital, revenue, or EBITDA).

IMPORTANT: the bundled factors are order-of-magnitude defaults for
demonstration. For decision-grade valuation, override them with the IFVI
Global Value Factor Database values for the relevant geography and year.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field


Direction = Literal["benefit", "cost"]


class ValueFactor(BaseModel):
    """A monetary value factor for one impact pathway."""

    pathway: str
    label: str
    unit: str
    value_usd_per_unit: float = Field(ge=0)
    direction: Direction
    source: str = "Illustrative default — replace with IFVI Global Value Factor Database"
    year: int = 2025


# ---------------------------------------------------------------------------
# Seeded value-factor catalogue (illustrative USD defaults).
# ---------------------------------------------------------------------------

DEFAULT_VALUE_FACTORS: dict[str, ValueFactor] = {
    # --- Environmental costs (negative) ---
    "ghg_emissions": ValueFactor(
        pathway="ghg_emissions", label="GHG emissions (social cost of carbon)",
        unit="tCO2e", value_usd_per_unit=236.0, direction="cost",
        source="IFVI GHG Topic Methodology / social cost of carbon (illustrative)",
    ),
    "air_pollution": ValueFactor(
        pathway="air_pollution", label="Air pollution (criteria pollutants)",
        unit="tonne", value_usd_per_unit=35000.0, direction="cost",
        source="IFVI Air Pollution Interim Methodology (illustrative aggregate)",
    ),
    "water_pollution": ValueFactor(
        pathway="water_pollution", label="Water pollution",
        unit="m3", value_usd_per_unit=2.0, direction="cost",
        source="IFVI Water Pollution Interim Methodology (illustrative)",
    ),
    "water_consumption": ValueFactor(
        pathway="water_consumption", label="Water consumption (stressed basin)",
        unit="m3", value_usd_per_unit=1.5, direction="cost",
    ),
    "land_use": ValueFactor(
        pathway="land_use", label="Land use & conversion",
        unit="hectare-year", value_usd_per_unit=1200.0, direction="cost",
        source="IFVI Land Use & Conversion Interim Methodology (illustrative)",
    ),
    "waste_nonhazardous": ValueFactor(
        pathway="waste_nonhazardous", label="Non-hazardous waste",
        unit="tonne", value_usd_per_unit=120.0, direction="cost",
        source="IFVI Waste Interim Methodology (illustrative)",
    ),
    "waste_hazardous": ValueFactor(
        pathway="waste_hazardous", label="Hazardous waste",
        unit="tonne", value_usd_per_unit=1500.0, direction="cost",
        source="IFVI Waste Interim Methodology (illustrative)",
    ),
    # --- Social / environmental benefits (positive) ---
    "ghg_avoided": ValueFactor(
        pathway="ghg_avoided", label="Avoided GHG emissions",
        unit="tCO2e", value_usd_per_unit=236.0, direction="benefit",
        source="Avoided emissions valued at social cost of carbon (illustrative)",
    ),
    "living_wage_uplift": ValueFactor(
        pathway="living_wage_uplift", label="Wages paid above living-wage threshold",
        unit="USD", value_usd_per_unit=1.0, direction="benefit",
        source="Impact-Weighted Accounts employment methodology (wage quality)",
    ),
    "jobs_created": ValueFactor(
        pathway="jobs_created", label="Quality jobs created",
        unit="job-year", value_usd_per_unit=15000.0, direction="benefit",
        source="Illustrative social value of quality employment",
    ),
    "beneficiaries_essential_services": ValueFactor(
        pathway="beneficiaries_essential_services",
        label="Access to essential services (health/finance/energy/education)",
        unit="person-year", value_usd_per_unit=500.0, direction="benefit",
        source="Illustrative value of access to underserved essential services",
    ),
    "qaly_gained": ValueFactor(
        pathway="qaly_gained", label="Quality-Adjusted Life Years gained",
        unit="QALY", value_usd_per_unit=50000.0, direction="benefit",
        source="Health-economics QALY value threshold (illustrative)",
    ),
}


def get_value_factors() -> list[ValueFactor]:
    """Return the seeded value-factor catalogue."""
    return list(DEFAULT_VALUE_FACTORS.values())


def get_value_factor(pathway: str) -> ValueFactor:
    """Look up a single value factor by pathway key."""
    key = pathway.strip().lower()
    if key not in DEFAULT_VALUE_FACTORS:
        raise KeyError(
            f"Unknown pathway {pathway!r}. Known: {sorted(DEFAULT_VALUE_FACTORS)}"
        )
    return DEFAULT_VALUE_FACTORS[key]


class ImpactQuantity(BaseModel):
    """A physical impact quantity to be monetised."""

    pathway: str
    amount: float = Field(ge=0)
    unit: str = ""
    note: str = ""


class MonetizedImpact(BaseModel):
    """One monetised impact line."""

    pathway: str
    label: str
    amount: float
    unit: str
    value_usd_per_unit: float
    direction: Direction
    monetary_value_usd: float
    note: str = ""


class ImpactValuationResult(BaseModel):
    """Result of a monetary impact valuation."""

    currency: str = "USD"
    lines: list[MonetizedImpact] = Field(default_factory=list)
    total_benefit_usd: float = 0.0
    total_cost_usd: float = 0.0
    unpriced_pathways: list[str] = Field(default_factory=list)
    financial_value_usd: float | None = None
    financial_basis: str = ""
    notes: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def net_monetary_impact_usd(self) -> float:
        return round(self.total_benefit_usd - self.total_cost_usd, 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def benefit_cost_ratio(self) -> float | None:
        if self.total_cost_usd <= 0:
            return None
        return round(self.total_benefit_usd / self.total_cost_usd, 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def impact_intensity(self) -> float | None:
        """Net monetary impact per unit of financial value (e.g. per $ invested)."""
        if not self.financial_value_usd:
            return None
        return round(self.net_monetary_impact_usd / self.financial_value_usd, 4)


def monetize_impacts(
    quantities: list[ImpactQuantity],
    *,
    financial_value_usd: float | None = None,
    financial_basis: str = "",
    custom_factors: dict[str, ValueFactor] | None = None,
) -> ImpactValuationResult:
    """Monetise a list of physical impact quantities into a value ledger.

    ``custom_factors`` overrides or extends the default catalogue (use IFVI
    Global Value Factor Database values here for decision-grade output).
    ``financial_value_usd`` (invested capital, revenue, or EBITDA) enables the
    impact-intensity ratio.
    """
    factors = dict(DEFAULT_VALUE_FACTORS)
    if custom_factors:
        factors.update({k.strip().lower(): v for k, v in custom_factors.items()})

    lines: list[MonetizedImpact] = []
    unpriced: list[str] = []
    total_benefit = 0.0
    total_cost = 0.0

    for q in quantities:
        key = q.pathway.strip().lower()
        factor = factors.get(key)
        if factor is None:
            unpriced.append(q.pathway)
            continue
        monetary = round(q.amount * factor.value_usd_per_unit, 2)
        if factor.direction == "benefit":
            total_benefit += monetary
        else:
            total_cost += monetary
        lines.append(MonetizedImpact(
            pathway=factor.pathway, label=factor.label, amount=q.amount,
            unit=q.unit or factor.unit, value_usd_per_unit=factor.value_usd_per_unit,
            direction=factor.direction, monetary_value_usd=monetary, note=q.note,
        ))

    notes = [
        "Value factors are illustrative defaults; override with IFVI Global Value "
        "Factor Database values for decision-grade valuation.",
        "Monetisation does not net out double-counting across overlapping pathways.",
    ]
    if unpriced:
        notes.append(f"Unpriced pathways (no factor): {', '.join(sorted(set(unpriced)))}.")

    return ImpactValuationResult(
        lines=lines,
        total_benefit_usd=round(total_benefit, 2),
        total_cost_usd=round(total_cost, 2),
        unpriced_pathways=sorted(set(unpriced)),
        financial_value_usd=financial_value_usd,
        financial_basis=financial_basis,
        notes=notes,
    )


class ImpactWeightedReturn(BaseModel):
    """Impact-weighted return: a financial return adjusted by monetised impact."""

    financial_return_usd: float
    net_monetary_impact_usd: float
    invested_capital_usd: float | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def impact_weighted_return_usd(self) -> float:
        return round(self.financial_return_usd + self.net_monetary_impact_usd, 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def impact_multiple_of_money(self) -> float | None:
        """Net monetary impact per dollar of invested capital (IMM)."""
        if not self.invested_capital_usd:
            return None
        return round(self.net_monetary_impact_usd / self.invested_capital_usd, 3)


def impact_weighted_return(
    *,
    financial_return_usd: float,
    valuation: ImpactValuationResult,
    invested_capital_usd: float | None = None,
) -> ImpactWeightedReturn:
    """Combine a financial return with a monetised impact valuation."""
    return ImpactWeightedReturn(
        financial_return_usd=financial_return_usd,
        net_monetary_impact_usd=valuation.net_monetary_impact_usd,
        invested_capital_usd=invested_capital_usd,
    )


__all__ = [
    "Direction",
    "ValueFactor",
    "DEFAULT_VALUE_FACTORS",
    "get_value_factors",
    "get_value_factor",
    "ImpactQuantity",
    "MonetizedImpact",
    "ImpactValuationResult",
    "monetize_impacts",
    "ImpactWeightedReturn",
    "impact_weighted_return",
]
