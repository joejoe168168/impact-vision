"""Benchmarking / risk / value-creation intelligence (roadmap-v4 Track 4).

Wraps the existing v3 :mod:`openharness.impact.benchmarks`,
:mod:`openharness.impact.external_benchmarks`, and
:mod:`openharness.impact.risk_opportunity` into an engagement-scoped
intelligence layer that answers the Track 4 framing question: "Given this
data, what should management do next and why does it matter commercially?"

Design:

* `BenchmarkProvider` is the pluggable provider interface (Track 4.1). A
  default in-memory provider is shipped so tests and offline use keep
  working; the interface is meant to be swapped for a paid/open dataset.
* `PeerDashboard` materialises Track 4.2 from a provider output.
* `ImpactRiskRating` reuses the 14-risk framework from
  :mod:`openharness.impact.risk_opportunity` to produce Track 4.3.
* `ValueCreationPlan` ties KPI gaps + risks + benchmarks to recommended
  actions (Track 4.4).
* `BusinessCase` ships the Track 4.5 revenue / cost / valuation upside
  estimate (deliberately simple — the consultant supplies the numbers).
* `run_scenario` is the Track 4.6 scenario / sensitivity engine.
* `SupplyChainHotspot` stubs Track 4.7 Scope 3 supplier workflow.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from statistics import mean, median, pstdev
from typing import Iterable, Literal, Protocol

from pydantic import BaseModel, Field, computed_field


# --------------------------------------------------------------- benchmarks


class BenchmarkQuery(BaseModel):
    """Input to a benchmark provider call."""

    metric_id: str
    sector: str = ""
    geography: str = ""
    company_size_band: str = ""
    fund_strategy: str = ""
    period: str = ""


class BenchmarkObservation(BaseModel):
    """One peer observation returned by a provider."""

    entity_alias: str
    value: float
    unit: str = ""
    period: str = ""


class BenchmarkResult(BaseModel):
    """Aggregated benchmark with anonymised peer observations."""

    query: BenchmarkQuery
    sample_size: int
    mean_value: float | None = None
    median_value: float | None = None
    stdev_value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    observations: list[BenchmarkObservation] = Field(default_factory=list)
    provider: str = "in_memory"


class BenchmarkProvider(Protocol):
    """Pluggable benchmark-provider interface (Track 4.1)."""

    name: str

    def fetch(self, query: BenchmarkQuery) -> BenchmarkResult:  # pragma: no cover - protocol
        ...


class InMemoryBenchmarkProvider:
    """Default provider: serves a consultant-curated offline dataset.

    The dataset is keyed by ``(metric_id, sector)`` so the roadmap-v4 §2.1
    'benchmark provider interface' can ship without a paid data license on
    day one (the roadmap explicitly calls that out as acceptable).
    """

    name = "in_memory"

    def __init__(
        self,
        observations: dict[tuple[str, str], list[BenchmarkObservation]] | None = None,
    ) -> None:
        self._observations: dict[tuple[str, str], list[BenchmarkObservation]] = dict(
            observations or {}
        )

    def add_observation(
        self,
        *,
        metric_id: str,
        sector: str,
        observation: BenchmarkObservation,
    ) -> None:
        key = (metric_id.upper(), sector.lower())
        self._observations.setdefault(key, []).append(observation)

    def fetch(self, query: BenchmarkQuery) -> BenchmarkResult:
        observations = list(
            self._observations.get((query.metric_id.upper(), query.sector.lower()), [])
        )
        values = [o.value for o in observations]
        return BenchmarkResult(
            query=query,
            sample_size=len(values),
            mean_value=round(mean(values), 4) if values else None,
            median_value=round(median(values), 4) if values else None,
            stdev_value=round(pstdev(values), 4) if len(values) > 1 else None,
            min_value=min(values) if values else None,
            max_value=max(values) if values else None,
            observations=observations,
            provider=self.name,
        )


_DEFAULT_PROVIDER: BenchmarkProvider | None = None


def get_default_benchmark_provider() -> BenchmarkProvider:
    """Return the global default benchmark provider (seeded with sample data)."""
    global _DEFAULT_PROVIDER
    if _DEFAULT_PROVIDER is None:
        provider = InMemoryBenchmarkProvider()
        _seed_sample_data(provider)
        _DEFAULT_PROVIDER = provider
    return _DEFAULT_PROVIDER


def set_default_benchmark_provider(provider: BenchmarkProvider) -> None:
    """Override the global default provider (used by tests / deployments)."""
    global _DEFAULT_PROVIDER
    _DEFAULT_PROVIDER = provider


def _seed_sample_data(provider: InMemoryBenchmarkProvider) -> None:
    seed = [
        ("OI4112", "financial services", [1200, 2100, 3400, 900, 1800]),
        ("OI4112", "energy", [8500, 12000, 5500, 3400]),
        ("PD5833", "financial services", [450, 600, 720, 910]),
        ("PD5833", "energy", [12000, 18000, 24000, 32000]),
        ("OI6213", "financial services", [25, 45, 60, 30]),
    ]
    for metric_id, sector, values in seed:
        for idx, value in enumerate(values):
            provider.add_observation(
                metric_id=metric_id,
                sector=sector,
                observation=BenchmarkObservation(
                    entity_alias=f"peer-{idx+1}", value=float(value),
                ),
            )


class PeerDashboard(BaseModel):
    """Track 4.2 dashboard view."""

    dashboard_id: str = Field(default_factory=lambda: f"pd_{secrets.token_hex(4)}")
    engagement_id: str = ""
    observations: list[BenchmarkResult] = Field(default_factory=list)
    note: str = ""


def build_peer_dashboard(
    provider: BenchmarkProvider,
    queries: Iterable[BenchmarkQuery],
    *,
    engagement_id: str = "",
) -> PeerDashboard:
    """Hit the provider for each query and bundle the results into a dashboard."""
    results = [provider.fetch(q) for q in queries]
    return PeerDashboard(engagement_id=engagement_id, observations=results)


# ---------------------------------------------------------------- risk rating


RiskCategory = Literal[
    "strategic",
    "operational",
    "external",
    "governance",
    "stakeholder",
    "environmental",
    "social",
    "financial",
    "reputational",
    "regulatory",
    "technology",
    "supply_chain",
    "market",
    "model",
]


class ImpactRiskEntry(BaseModel):
    """One risk row."""

    risk_id: str = Field(default_factory=lambda: f"risk_{secrets.token_hex(4)}")
    title: str
    category: RiskCategory
    likelihood: Literal["low", "medium", "high"] = "medium"
    severity: Literal["low", "medium", "high"] = "medium"
    mitigation: str = ""
    owner: str = ""


class ImpactRiskRating(BaseModel):
    """Track 4.3: impact risk rating + material-risk register."""

    rating_id: str = Field(default_factory=lambda: f"rate_{secrets.token_hex(4)}")
    engagement_id: str = ""
    entries: list[ImpactRiskEntry] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overall_score(self) -> float:
        """0-100 score: higher = more material risk."""
        if not self.entries:
            return 0.0
        weight = {"low": 1, "medium": 2, "high": 3}
        values = [
            weight[e.likelihood] * weight[e.severity] for e in self.entries
        ]
        # Max per entry is 9, normalise over entry count.
        return round(100.0 * sum(values) / (9 * len(self.entries)), 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def material_risks(self) -> list[str]:
        return [e.title for e in self.entries if _is_material(e)]


def _is_material(entry: ImpactRiskEntry) -> bool:
    weight = {"low": 1, "medium": 2, "high": 3}
    return weight[entry.likelihood] * weight[entry.severity] >= 6


def build_risk_rating(
    *,
    engagement_id: str,
    entries: Iterable[ImpactRiskEntry],
) -> ImpactRiskRating:
    """Build a risk rating from a consultant-supplied risk register."""
    return ImpactRiskRating(engagement_id=engagement_id, entries=list(entries))


# ---------------------------------------------------------- value creation plan


class ValueCreationAction(BaseModel):
    """One recommended operational action."""

    action_id: str = Field(default_factory=lambda: f"vc_{secrets.token_hex(4)}")
    title: str
    description: str = ""
    rationale: str = ""
    tied_to_kpi: str = ""
    tied_to_risk: str = ""
    expected_outcome: str = ""
    effort: Literal["low", "medium", "high"] = "medium"
    timing: Literal["0-3m", "3-6m", "6-12m", "12-24m"] = "3-6m"


class ValueCreationPlan(BaseModel):
    """Track 4.4: value-creation recommendations tied to KPI gaps + risks."""

    plan_id: str = Field(default_factory=lambda: f"vcp_{secrets.token_hex(6)}")
    engagement_id: str = ""
    actions: list[ValueCreationAction] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: _now())
    summary: str = ""


def build_value_creation_plan(
    *,
    engagement_id: str,
    kpi_gaps: Iterable[str] | None = None,
    material_risks: Iterable[str] | None = None,
    peer_gaps: Iterable[str] | None = None,
    extra_actions: Iterable[ValueCreationAction] | None = None,
) -> ValueCreationPlan:
    """Deterministic value-creation recommendations.

    The logic is explicitly rules-based: every unmet KPI becomes a "close
    the data gap" action, every material risk becomes a "mitigate X"
    action, every peer gap becomes a "catch up on X" action. Track 8 will
    later layer LLM re-ranking; the deterministic backbone is what the
    audit trail can explain.
    """
    actions: list[ValueCreationAction] = []
    for kpi in kpi_gaps or []:
        actions.append(
            ValueCreationAction(
                title=f"Close KPI gap: {kpi}",
                rationale=f"{kpi} is not currently reported.",
                tied_to_kpi=kpi,
                expected_outcome=f"Reliable {kpi} data available for next reporting cycle.",
                effort="medium",
                timing="3-6m",
            )
        )
    for risk in material_risks or []:
        actions.append(
            ValueCreationAction(
                title=f"Mitigate material risk: {risk}",
                rationale=f"Material risk identified: {risk}.",
                tied_to_risk=risk,
                expected_outcome=f"Residual {risk} risk reduced to below-material threshold.",
                effort="medium",
                timing="3-6m",
            )
        )
    for peer_gap in peer_gaps or []:
        actions.append(
            ValueCreationAction(
                title=f"Catch peer: {peer_gap}",
                rationale=f"Company trails peers on {peer_gap}.",
                expected_outcome=f"Performance on {peer_gap} aligned with sector median.",
                effort="high",
                timing="6-12m",
            )
        )
    actions.extend(list(extra_actions or []))
    summary = (
        f"{len(actions)} value-creation actions generated "
        f"({sum(1 for a in actions if a.timing == '0-3m')} near-term)."
    )
    return ValueCreationPlan(engagement_id=engagement_id, actions=actions, summary=summary)


# ---------------------------------------------------------------- business case


class BusinessCase(BaseModel):
    """Track 4.5 business-case model (revenue / cost / valuation upside).

    Deliberately simple and explicit. Numbers are consultant inputs — the
    module just compiles them into a consistent structure.
    """

    case_id: str = Field(default_factory=lambda: f"bc_{secrets.token_hex(4)}")
    engagement_id: str = ""
    revenue_upside_usd: float = 0.0
    cost_reduction_usd: float = 0.0
    risk_avoidance_usd: float = 0.0
    valuation_multiple: float = 0.0
    funding_probability_pct: float = 0.0
    impact_upside_description: str = ""
    narrative: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_financial_upside_usd(self) -> float:
        return round(
            self.revenue_upside_usd + self.cost_reduction_usd + self.risk_avoidance_usd,
            2,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valuation_uplift_usd(self) -> float:
        if self.valuation_multiple <= 0:
            return 0.0
        return round(self.total_financial_upside_usd * self.valuation_multiple, 2)


def build_business_case(**kwargs) -> BusinessCase:
    return BusinessCase(**kwargs)


# ---------------------------------------------------------------- scenario engine


class ScenarioInput(BaseModel):
    """One sensitivity slider (e.g. 'customer growth', 'emission factor')."""

    name: str
    base_value: float
    low_multiplier: float = 0.8
    high_multiplier: float = 1.2


class ScenarioOutcome(BaseModel):
    """Outcome of a single scenario run."""

    scenario: Literal["downside", "base", "upside"]
    value: float


class ScenarioResult(BaseModel):
    """Track 4.6 scenario / sensitivity output."""

    engagement_id: str = ""
    metric: str
    outcomes: list[ScenarioOutcome]
    note: str = ""


def run_scenario(
    *,
    metric: str,
    base_value: float,
    inputs: Iterable[ScenarioInput],
    engagement_id: str = "",
) -> ScenarioResult:
    """Compound-multiplier scenario engine.

    Downside scenario multiplies the base value by each input's
    ``low_multiplier``; the upside does the opposite. This is intentionally
    simple (consultant-auditable) — plug in a proper model in Track 4.6
    later if you need compound economic effects.
    """
    inputs = list(inputs)
    if not inputs:
        return ScenarioResult(
            metric=metric,
            outcomes=[ScenarioOutcome(scenario="base", value=base_value)],
            engagement_id=engagement_id,
        )
    downside = base_value
    upside = base_value
    for i in inputs:
        downside *= i.low_multiplier
        upside *= i.high_multiplier
    return ScenarioResult(
        engagement_id=engagement_id,
        metric=metric,
        outcomes=[
            ScenarioOutcome(scenario="downside", value=round(downside, 4)),
            ScenarioOutcome(scenario="base", value=round(base_value, 4)),
            ScenarioOutcome(scenario="upside", value=round(upside, 4)),
        ],
    )


# ---------------------------------------------------------- supply-chain hotspot


class SupplyChainHotspot(BaseModel):
    """Track 4.7 Scope 3 supply-chain hotspot."""

    supplier_name: str
    tier: int = 1
    spend_usd: float = 0.0
    sector: str = ""
    country: str = ""
    emissions_intensity_tco2e_per_musd: float = 0.0
    estimated_tco2e: float = 0.0
    hotspot_score: float = 0.0


def score_supply_chain_hotspots(
    *,
    entries: Iterable[dict],
) -> list[SupplyChainHotspot]:
    """Rank supplier spend by estimated emissions."""
    result: list[SupplyChainHotspot] = []
    for raw in entries:
        item = SupplyChainHotspot(**raw)
        if item.estimated_tco2e == 0.0:
            item.estimated_tco2e = round(
                item.spend_usd / 1_000_000 * item.emissions_intensity_tco2e_per_musd,
                4,
            )
        result.append(item)
    if not result:
        return result
    max_emissions = max((item.estimated_tco2e for item in result), default=0.0)
    for item in result:
        if max_emissions > 0:
            item.hotspot_score = round(100.0 * item.estimated_tco2e / max_emissions, 2)
    return sorted(result, key=lambda h: h.hotspot_score, reverse=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "BenchmarkObservation",
    "BenchmarkProvider",
    "BenchmarkQuery",
    "BenchmarkResult",
    "BusinessCase",
    "ImpactRiskEntry",
    "ImpactRiskRating",
    "InMemoryBenchmarkProvider",
    "PeerDashboard",
    "RiskCategory",
    "ScenarioInput",
    "ScenarioOutcome",
    "ScenarioResult",
    "SupplyChainHotspot",
    "ValueCreationAction",
    "ValueCreationPlan",
    "build_business_case",
    "build_peer_dashboard",
    "build_risk_rating",
    "build_value_creation_plan",
    "get_default_benchmark_provider",
    "run_scenario",
    "score_supply_chain_hotspots",
    "set_default_benchmark_provider",
]
