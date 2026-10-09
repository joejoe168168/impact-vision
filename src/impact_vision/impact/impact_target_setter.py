"""Context-driven impact target setter (GIIN Impact Target Setter lineage).

Sets indicative impact-target *ranges* from three context inputs —
**theme × geography × capital deployed** — over a chosen time horizon, aligned
to the SDGs and IRIS+ metric IDs. The intuition mirrors GIIN's Impact Target
Setter: rather than asking a fund to invent a number, derive a plausible
conservative / base / stretch range from comparable deployment intensity, then
let the fund refine it.

IMPORTANT: the per-theme deployment intensities are **illustrative defaults**
for triage and goal-framing, not benchmarked commitments. Calibrate against
the fund's pipeline economics and GIIN Impact Performance Benchmarks before
publishing a target.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Ambition = Literal["conservative", "base", "stretch"]

_AMBITION_MULTIPLIER: dict[Ambition, float] = {
    "conservative": 0.7,
    "base": 1.0,
    "stretch": 1.4,
}

# Geographic reach efficiency — reaching underserved populations typically
# delivers more *units of reach* per dollar (lower unit cost of access).
_GEOGRAPHY_REACH_MULTIPLIER: dict[str, float] = {
    "low_income": 1.6,
    "lower_middle_income": 1.3,
    "upper_middle_income": 1.0,
    "high_income": 0.6,
    "ldc": 1.7,
    "fragile_state": 1.4,
    "rural_underserved": 1.5,
    "global": 1.0,
    "unknown": 1.0,
}


class KpiTargetTemplate(BaseModel):
    metric_id: str
    label: str
    unit: str
    units_per_million_usd: float = Field(ge=0)
    sdg: list[int] = Field(default_factory=list)
    direction: Literal["higher_better", "lower_better"] = "higher_better"


# Theme → candidate KPI templates (units delivered per $1M deployed, base case).
THEME_TARGET_TEMPLATES: dict[str, list[KpiTargetTemplate]] = {
    "financial_inclusion": [
        KpiTargetTemplate(metric_id="PI4060", label="Clients reached", unit="clients", units_per_million_usd=8000, sdg=[1, 8, 10]),
        KpiTargetTemplate(metric_id="PI8330", label="Women clients reached", unit="clients", units_per_million_usd=3500, sdg=[5, 8]),
    ],
    "clean_energy": [
        KpiTargetTemplate(metric_id="PI8316", label="People with new/improved energy access", unit="people", units_per_million_usd=12000, sdg=[7]),
        KpiTargetTemplate(metric_id="OI6280", label="GHG emissions avoided", unit="tCO2e", units_per_million_usd=4000, sdg=[13]),
    ],
    "energy_access": [
        KpiTargetTemplate(metric_id="PI8316", label="People with new/improved energy access", unit="people", units_per_million_usd=12000, sdg=[7]),
    ],
    "healthcare": [
        KpiTargetTemplate(metric_id="PI5685", label="Patients served", unit="patients", units_per_million_usd=9000, sdg=[3]),
    ],
    "health": [
        KpiTargetTemplate(metric_id="PI5685", label="Patients served", unit="patients", units_per_million_usd=9000, sdg=[3]),
    ],
    "education": [
        KpiTargetTemplate(metric_id="PI2389", label="Students enrolled / reached", unit="students", units_per_million_usd=6000, sdg=[4]),
    ],
    "agriculture": [
        KpiTargetTemplate(metric_id="PI1764", label="Smallholder farmers reached", unit="farmers", units_per_million_usd=5000, sdg=[1, 2]),
        KpiTargetTemplate(metric_id="OI7472", label="Hectares under sustainable cultivation", unit="hectares", units_per_million_usd=2500, sdg=[2, 15]),
    ],
    "water_sanitation": [
        KpiTargetTemplate(metric_id="PI3848", label="People with improved water/sanitation access", unit="people", units_per_million_usd=15000, sdg=[6]),
    ],
    "affordable_housing": [
        KpiTargetTemplate(metric_id="PI6280", label="Affordable housing units", unit="units", units_per_million_usd=10, sdg=[11]),
    ],
    "employment": [
        KpiTargetTemplate(metric_id="OI3160", label="Jobs created/sustained", unit="jobs", units_per_million_usd=40, sdg=[8]),
    ],
    "general": [
        KpiTargetTemplate(metric_id="PI4060", label="Beneficiaries reached", unit="people", units_per_million_usd=7000, sdg=[1, 8, 10]),
    ],
}


class KpiTargetRange(BaseModel):
    metric_id: str
    label: str
    unit: str
    sdg: list[int] = Field(default_factory=list)
    conservative: float
    base: float
    stretch: float
    annual_trajectory: list[float] = Field(default_factory=list)
    rationale: str = ""


class TargetSetterInput(BaseModel):
    theme: str = Field(default="general")
    geography: str = Field(default="unknown")
    capital_usd: float = Field(ge=0, description="Capital to deploy against this theme")
    time_horizon_years: int = Field(default=5, ge=1, le=30)
    ambition: Ambition = "base"


class TargetSetterResult(BaseModel):
    theme: str
    geography: str
    capital_usd: float
    time_horizon_years: int
    ambition: str
    targets: list[KpiTargetRange] = Field(default_factory=list)
    sdg_focus: list[int] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def set_impact_targets(input: TargetSetterInput) -> TargetSetterResult:  # noqa: A002
    """Derive conservative/base/stretch impact-target ranges from context."""
    theme_key = input.theme.strip().lower().replace(" ", "_").replace("-", "_")
    templates = THEME_TARGET_TEMPLATES.get(theme_key, THEME_TARGET_TEMPLATES["general"])
    geo_key = input.geography.strip().lower().replace(" ", "_").replace("-", "_")
    geo_mult = _GEOGRAPHY_REACH_MULTIPLIER.get(geo_key, 1.0)
    millions = input.capital_usd / 1_000_000.0

    targets: list[KpiTargetRange] = []
    sdgs: set[int] = set()
    for tpl in templates:
        sdgs.update(tpl.sdg)
        base_units = tpl.units_per_million_usd * millions * geo_mult
        cons = round(base_units * _AMBITION_MULTIPLIER["conservative"], 1)
        base = round(base_units * _AMBITION_MULTIPLIER["base"], 1)
        stretch = round(base_units * _AMBITION_MULTIPLIER["stretch"], 1)
        chosen = {"conservative": cons, "base": base, "stretch": stretch}[input.ambition]
        # Smooth annual ramp to the chosen ambition level (cumulative).
        years = input.time_horizon_years
        trajectory = [round(chosen * (y + 1) / years, 1) for y in range(years)]
        targets.append(KpiTargetRange(
            metric_id=tpl.metric_id,
            label=tpl.label,
            unit=tpl.unit,
            sdg=tpl.sdg,
            conservative=cons,
            base=base,
            stretch=stretch,
            annual_trajectory=trajectory,
            rationale=(
                f"{tpl.units_per_million_usd:g} {tpl.unit}/$1M base intensity × "
                f"${millions:g}M × {geo_mult:g} geography factor over {years}y."
            ),
        ))

    notes = [
        "Deployment intensities are illustrative defaults — calibrate against fund "
        "pipeline economics and GIIN Impact Performance Benchmarks before publishing.",
        f"Ambition '{input.ambition}' selected; ranges show conservative/base/stretch for context.",
    ]
    if theme_key not in THEME_TARGET_TEMPLATES:
        notes.append(f"Unknown theme {input.theme!r} — used 'general' beneficiary-reach template.")

    return TargetSetterResult(
        theme=input.theme,
        geography=input.geography,
        capital_usd=input.capital_usd,
        time_horizon_years=input.time_horizon_years,
        ambition=input.ambition,
        targets=targets,
        sdg_focus=sorted(sdgs),
        notes=notes,
    )


__all__ = [
    "Ambition",
    "KpiTargetTemplate",
    "THEME_TARGET_TEMPLATES",
    "KpiTargetRange",
    "TargetSetterInput",
    "TargetSetterResult",
    "set_impact_targets",
]
