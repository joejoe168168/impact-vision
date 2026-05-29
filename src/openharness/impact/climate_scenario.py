"""Climate scenario risk — NGFS-style physical & transition exposure.

A lightweight, offline portfolio climate-risk screen structured around the
**NGFS scenario families** (Network for Greening the Financial System):

* **Orderly** — Net Zero 2050, Below 2°C (early, smooth policy; high transition
  effort, low physical risk).
* **Disorderly** — Delayed Transition, Divergent Net Zero (late/abrupt policy;
  high transition risk).
* **Hot house world** — Nationally Determined Contributions, Current Policies
  (weak policy; low transition but severe physical risk).
* **Too little too late** — late and insufficient action (high transition AND
  high physical risk).

It combines each scenario's transition/physical severity with **sector
sensitivities** to produce a portfolio-weighted transition-risk exposure,
physical-risk exposure, a combined score, and an illustrative value-at-risk
haircut so a fund can see which holdings drive climate risk under each pathway.

IMPORTANT: severities, sector sensitivities and the value-at-risk mapping are
illustrative coefficients for screening and engagement — not a calibrated
financial model. Use NGFS Phase V data + asset-level models for decision-grade
climate VaR.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ScenarioCategory = Literal["orderly", "disorderly", "hot_house", "too_little_too_late"]


class NGFSScenario(BaseModel):
    key: str
    name: str
    category: ScenarioCategory
    description: str
    transition_severity: float = Field(ge=0, le=1)
    physical_severity: float = Field(ge=0, le=1)
    carbon_price_2030_usd: float = 0.0
    temp_outcome_c: float = 0.0


NGFS_SCENARIOS: dict[str, NGFSScenario] = {
    "net_zero_2050": NGFSScenario(
        key="net_zero_2050", name="Net Zero 2050", category="orderly",
        description="Ambitious, early, smooth transition limiting warming to ~1.5°C.",
        transition_severity=0.8, physical_severity=0.2,
        carbon_price_2030_usd=160, temp_outcome_c=1.4),
    "below_2c": NGFSScenario(
        key="below_2c", name="Below 2°C", category="orderly",
        description="Gradual policy tightening; ~1.7°C outcome.",
        transition_severity=0.6, physical_severity=0.3,
        carbon_price_2030_usd=100, temp_outcome_c=1.7),
    "delayed_transition": NGFSScenario(
        key="delayed_transition", name="Delayed Transition", category="disorderly",
        description="Weak action to 2030 then abrupt, divergent policy; high transition shock.",
        transition_severity=0.9, physical_severity=0.4,
        carbon_price_2030_usd=50, temp_outcome_c=1.7),
    "divergent_net_zero": NGFSScenario(
        key="divergent_net_zero", name="Divergent Net Zero", category="disorderly",
        description="Net zero ~2050 but with sectoral divergence and higher costs.",
        transition_severity=0.85, physical_severity=0.3,
        carbon_price_2030_usd=140, temp_outcome_c=1.5),
    "ndcs": NGFSScenario(
        key="ndcs", name="Nationally Determined Contributions", category="hot_house",
        description="Only pledged NDCs implemented; ~2.4°C, rising physical risk.",
        transition_severity=0.3, physical_severity=0.7,
        carbon_price_2030_usd=30, temp_outcome_c=2.4),
    "current_policies": NGFSScenario(
        key="current_policies", name="Current Policies", category="hot_house",
        description="Only current policies; ~3°C, severe chronic & acute physical risk.",
        transition_severity=0.2, physical_severity=0.9,
        carbon_price_2030_usd=10, temp_outcome_c=3.0),
    "too_little_too_late": NGFSScenario(
        key="too_little_too_late", name="Too Little Too Late", category="too_little_too_late",
        description="Late, insufficient action: high transition shock AND high physical risk.",
        transition_severity=0.8, physical_severity=0.8,
        carbon_price_2030_usd=70, temp_outcome_c=2.5),
}


# Sector sensitivity to transition risk (carbon-intensive / policy-exposed) and
# physical risk (location / supply-chain exposure). 0-1.
SECTOR_TRANSITION_SENSITIVITY: dict[str, float] = {
    "fossil_fuels": 1.0, "oil_gas": 1.0, "coal": 1.0, "energy": 0.7,
    "utilities": 0.8, "power": 0.8, "cement": 0.9, "steel": 0.9,
    "manufacturing": 0.6, "transport": 0.7, "aviation": 0.9, "shipping": 0.8,
    "automotive": 0.7, "chemicals": 0.7, "mining": 0.8, "real_estate": 0.5,
    "construction": 0.6, "agriculture": 0.6, "financial_services": 0.4,
    "fintech": 0.3, "technology": 0.3, "healthcare": 0.3, "education": 0.2,
    "retail": 0.4, "clean_energy": 0.2, "water": 0.3, "default": 0.4,
}

SECTOR_PHYSICAL_SENSITIVITY: dict[str, float] = {
    "agriculture": 0.9, "food_security": 0.9, "water": 0.8, "fishing": 0.9,
    "forestry": 0.8, "real_estate": 0.7, "construction": 0.6, "tourism": 0.7,
    "energy": 0.5, "utilities": 0.6, "transport": 0.5, "insurance": 0.8,
    "mining": 0.6, "manufacturing": 0.5, "healthcare": 0.4, "financial_services": 0.3,
    "fintech": 0.2, "technology": 0.3, "education": 0.3, "retail": 0.4,
    "clean_energy": 0.4, "default": 0.4,
}


class PortfolioHolding(BaseModel):
    name: str
    sector: str = "default"
    value_usd: float = Field(default=0.0, ge=0)


class ScenarioExposure(BaseModel):
    scenario_key: str
    scenario_name: str
    category: str
    transition_exposure: float = 0.0
    physical_exposure: float = 0.0
    combined_risk_score: float = 0.0
    estimated_var_pct: float = 0.0
    estimated_var_usd: float = 0.0


class ClimateScenarioInput(BaseModel):
    holdings: list[PortfolioHolding] = Field(default_factory=list)
    scenario_keys: list[str] = Field(
        default_factory=list,
        description="Subset of NGFS scenario keys; empty = all scenarios",
    )
    max_var_pct: float = Field(
        default=35.0, ge=0, le=100,
        description="Illustrative max portfolio value-at-risk at full combined severity",
    )


class HoldingScenarioRisk(BaseModel):
    name: str
    sector: str
    value_usd: float
    transition_sensitivity: float
    physical_sensitivity: float
    worst_scenario: str = ""
    worst_combined_score: float = 0.0


class ClimateScenarioResult(BaseModel):
    total_value_usd: float = 0.0
    scenario_exposures: list[ScenarioExposure] = Field(default_factory=list)
    top_exposed_holdings: list[HoldingScenarioRisk] = Field(default_factory=list)
    headline_scenario: str = ""
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def _sector_key(sector: str) -> str:
    return sector.strip().lower().replace(" ", "_").replace("-", "_").replace("&", "and")


def _transition_sensitivity(sector: str) -> float:
    return SECTOR_TRANSITION_SENSITIVITY.get(_sector_key(sector), SECTOR_TRANSITION_SENSITIVITY["default"])


def _physical_sensitivity(sector: str) -> float:
    return SECTOR_PHYSICAL_SENSITIVITY.get(_sector_key(sector), SECTOR_PHYSICAL_SENSITIVITY["default"])


def assess_climate_scenarios(input: ClimateScenarioInput) -> ClimateScenarioResult:  # noqa: A002
    """Score portfolio physical & transition exposure across NGFS scenarios."""
    holdings = input.holdings
    total_value = sum(h.value_usd for h in holdings)
    keys = input.scenario_keys or list(NGFS_SCENARIOS.keys())
    scenarios = [NGFS_SCENARIOS[k] for k in keys if k in NGFS_SCENARIOS]

    # Value weights (equal-weight if no values supplied).
    if total_value > 0:
        weights = {h.name: h.value_usd / total_value for h in holdings}
    else:
        n = len(holdings) or 1
        weights = {h.name: 1.0 / n for h in holdings}

    exposures: list[ScenarioExposure] = []
    for sc in scenarios:
        trans = sum(
            weights[h.name] * _transition_sensitivity(h.sector) * sc.transition_severity
            for h in holdings
        )
        phys = sum(
            weights[h.name] * _physical_sensitivity(h.sector) * sc.physical_severity
            for h in holdings
        )
        combined = round((trans + phys) / 2, 4)
        var_pct = round(combined * input.max_var_pct, 2)
        exposures.append(ScenarioExposure(
            scenario_key=sc.key,
            scenario_name=sc.name,
            category=sc.category,
            transition_exposure=round(trans, 4),
            physical_exposure=round(phys, 4),
            combined_risk_score=combined,
            estimated_var_pct=var_pct,
            estimated_var_usd=round(total_value * var_pct / 100, 2),
        ))

    # Per-holding worst-case across scenarios.
    holding_risks: list[HoldingScenarioRisk] = []
    for h in holdings:
        ts = _transition_sensitivity(h.sector)
        ps = _physical_sensitivity(h.sector)
        worst_name, worst_score = "", 0.0
        for sc in scenarios:
            combined = (ts * sc.transition_severity + ps * sc.physical_severity) / 2
            if combined > worst_score:
                worst_score, worst_name = combined, sc.name
        holding_risks.append(HoldingScenarioRisk(
            name=h.name, sector=h.sector, value_usd=h.value_usd,
            transition_sensitivity=ts, physical_sensitivity=ps,
            worst_scenario=worst_name, worst_combined_score=round(worst_score, 4),
        ))
    holding_risks.sort(key=lambda x: (x.worst_combined_score, x.value_usd), reverse=True)

    headline = max(exposures, key=lambda e: e.combined_risk_score).scenario_name if exposures else ""

    findings: list[str] = []
    recs: list[str] = []
    if exposures:
        worst = max(exposures, key=lambda e: e.combined_risk_score)
        findings.append(
            f"Highest combined climate risk under '{worst.scenario_name}' "
            f"(combined {worst.combined_risk_score}, ~{worst.estimated_var_pct}% illustrative VaR)."
        )
        disorderly = [e for e in exposures if e.category in ("disorderly", "too_little_too_late")]
        if disorderly and max(e.transition_exposure for e in disorderly) > 0.4:
            recs.append("High transition exposure under disorderly pathways — request transition plans / SBTi targets from carbon-intensive holdings.")
        hot = [e for e in exposures if e.category == "hot_house"]
        if hot and max(e.physical_exposure for e in hot) > 0.4:
            recs.append("Material physical risk under hot-house pathways — commission asset-level physical-risk screening for exposed holdings.")
    if holding_risks:
        top = holding_risks[0]
        recs.append(f"Prioritise climate engagement with '{top.name}' ({top.sector}) — highest worst-case exposure.")
    if not recs:
        recs.append("Climate exposure is modest across NGFS scenarios — monitor and refresh with NGFS Phase V data annually.")

    return ClimateScenarioResult(
        total_value_usd=round(total_value, 2),
        scenario_exposures=exposures,
        top_exposed_holdings=holding_risks[:10],
        headline_scenario=headline,
        findings=findings,
        recommendations=recs,
        limitations=[
            "Scenario severities, sector sensitivities and the VaR mapping are illustrative "
            "screening coefficients, not a calibrated financial model.",
            "Use NGFS Phase V pathways and asset-level physical-risk models for decision-grade climate VaR.",
        ],
    )


__all__ = [
    "ScenarioCategory",
    "NGFSScenario",
    "NGFS_SCENARIOS",
    "SECTOR_TRANSITION_SENSITIVITY",
    "SECTOR_PHYSICAL_SENSITIVITY",
    "PortfolioHolding",
    "ScenarioExposure",
    "ClimateScenarioInput",
    "HoldingScenarioRisk",
    "ClimateScenarioResult",
    "assess_climate_scenarios",
]
