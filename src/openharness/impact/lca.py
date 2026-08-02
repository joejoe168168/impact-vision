"""Lifecycle assessment (LCA), lifecycle sustainability, and LCM helpers.

This module implements a deliberately transparent calculation layer inspired by
the ISO 14040/14044 workflow (ISO 14044 describes goal/scope, LCI, LCIA,
interpretation, reporting, limitations, and critical review):

* goal and scope definition (including functional unit and system boundary),
* lifecycle inventory (LCI) flow capture with data-quality/provenance fields,
* lifecycle impact assessment (LCIA) using caller-supplied characterization
  factors,
* interpretation, hotspot and burden-shift flags,
* deterministic scenario sensitivity,
* a practical life-cycle-management (LCM) action plan, and
* a light LCSA composition of environmental, economic, and social dimensions.

The engine does **not** bundle ecoinvent, ReCiPe, EF, TRACI, or another
licensed database. A flow carries its own characterization factors, which keeps
the result reproducible and makes factor provenance explicit. The method
catalogue below is metadata for method selection, not a replacement for a
licensed LCIA implementation.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

LifecycleStage = Literal[
    "raw_materials",
    "manufacturing",
    "distribution",
    "use",
    "end_of_life",
    "beyond_system",
]
Boundary = Literal[
    "cradle_to_gate",
    "cradle_to_grave",
    "cradle_to_cradle",
    "gate_to_gate",
    "custom",
]
AssessmentMode = Literal["attributional", "consequential"]
ReadinessStatus = Literal["pass", "partial", "gap"]


STAGE_ORDER: tuple[str, ...] = (
    "raw_materials",
    "manufacturing",
    "distribution",
    "use",
    "end_of_life",
    "beyond_system",
)

BOUNDARY_STAGES: dict[str, tuple[str, ...]] = {
    "cradle_to_gate": ("raw_materials", "manufacturing"),
    "cradle_to_grave": (
        "raw_materials",
        "manufacturing",
        "distribution",
        "use",
        "end_of_life",
    ),
    "cradle_to_cradle": (
        "raw_materials",
        "manufacturing",
        "distribution",
        "use",
        "end_of_life",
        "beyond_system",
    ),
    "gate_to_gate": ("manufacturing",),
}

STAGE_ALIASES = {
    "raw_material": "raw_materials",
    "raw_materials": "raw_materials",
    "materials": "raw_materials",
    "production": "manufacturing",
    "factory": "manufacturing",
    "transport": "distribution",
    "logistics": "distribution",
    "customer_use": "use",
    "use_phase": "use",
    "eol": "end_of_life",
    "end_of_life": "end_of_life",
    "recycling": "end_of_life",
    "credits": "beyond_system",
}

IMPACT_CATEGORY_UNITS: dict[str, str] = {
    "climate_change": "kg CO2e",
    "gwp100": "kg CO2e",
    "energy_use": "MJ",
    "water_use": "m3 world eq",
    "eutrophication": "kg PO4e",
    "acidification": "mol H+ eq",
    "resource_use": "kg Sb eq",
    "land_use": "m2a crop eq",
    "particulate_matter": "disease incidence",
    "human_toxicity": "CTUh",
    "ecotoxicity": "CTUe",
}

CLIMATE_CATEGORY_ALIASES = {
    "climate_change",
    "gwp100",
    "gwp",
    "carbon_footprint",
    "ghg",
}

LCIA_METHODS: dict[str, dict[str, Any]] = {
    "recipe_2016_midpoint": {
        "name": "ReCiPe 2016 midpoint",
        "family": "midpoint",
        "region": "global",
        "best_for": "Broad product comparison and hotspot screening.",
        "categories": [
            "climate_change",
            "particulate_matter",
            "terrestrial_acidification",
            "freshwater_eutrophication",
            "water_use",
            "resource_use",
        ],
    },
    "ef_3_1": {
        "name": "Environmental Footprint 3.1",
        "family": "midpoint",
        "region": "European Union",
        "best_for": "EU PEF/OEF and product-category-rule aligned work.",
        "categories": [
            "climate_change",
            "water_use",
            "eutrophication",
            "acidification",
            "resource_use",
        ],
        "source_url": "https://knowledge4policy.ec.europa.eu/european-platform-life-cycle-assessment-eplca/environmental-footprint-transition-phase_en",
    },
    "traci_2_1": {
        "name": "TRACI 2.1",
        "family": "midpoint",
        "region": "United States",
        "best_for": "US-context environmental comparison.",
        "categories": [
            "climate_change",
            "energy_use",
            "water_use",
            "eutrophication",
            "acidification",
        ],
    },
    "cml_ia": {
        "name": "CML-IA baseline",
        "family": "midpoint",
        "region": "global",
        "best_for": "Academic and method-comparison studies.",
        "categories": ["climate_change", "acidification", "eutrophication", "resource_use"],
    },
}

LCA_FRAMEWORK_SOURCES = {
    "iso_14044": "https://www.iso.org/standard/38498.html",
    "eu_environmental_footprint": "https://knowledge4policy.ec.europa.eu/european-platform-life-cycle-assessment-eplca/environmental-footprint-transition-phase_en",
}


def _normalize_key(value: object) -> str:
    return "_".join(str(value).strip().lower().replace("-", " ").split())


def _normalize_stage(value: object) -> str:
    cleaned = _normalize_key(value)
    return STAGE_ALIASES.get(cleaned, cleaned)


def _normalise_string(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


class LCAStudy(BaseModel):
    """Goal and scope definition for one LCA/LCSA study."""

    study_id: str = "lca-study"
    product_system: str
    goal: str = ""
    intended_application: str = ""
    audience: list[str] = Field(default_factory=list)
    functional_unit: str
    reference_flow: str = ""
    reference_quantity: float = Field(default=1.0, gt=0)
    boundary: Boundary = "cradle_to_grave"
    included_stages: list[str] = Field(default_factory=list)
    excluded_processes: list[str] = Field(default_factory=list)
    geography: str = "global"
    reference_year: int | None = Field(default=None, ge=1900, le=2200)
    assessment_mode: AssessmentMode = "attributional"
    lcia_method: str = "recipe_2016_midpoint"
    assessment_dimensions: list[Literal["environmental", "economic", "social"]] = Field(
        default_factory=lambda: ["environmental"]
    )
    allocation_method: str = "documented_case_by_case"
    assumptions: list[str] = Field(default_factory=list)
    review_type: Literal["none", "internal", "critical_review"] = "none"

    @field_validator(
        "study_id",
        "product_system",
        "goal",
        "intended_application",
        "functional_unit",
        "reference_flow",
        "geography",
        "allocation_method",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> str:
        return _normalise_string(value)

    @field_validator("included_stages", mode="before")
    @classmethod
    def normalize_stages(cls, values: object) -> list[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        return [_normalize_stage(value) for value in values]  # type: ignore[union-attr]

    def model_post_init(self, __context: Any, /) -> None:
        if not self.included_stages:
            if self.boundary == "custom":
                raise ValueError("included_stages is required for a custom boundary")
            self.included_stages = list(BOUNDARY_STAGES[self.boundary])
        unknown = sorted(set(self.included_stages) - set(STAGE_ORDER))
        if unknown:
            raise ValueError(f"Unknown lifecycle stage(s): {unknown}")
        self.included_stages = list(dict.fromkeys(self.included_stages))
        self.assessment_dimensions = list(dict.fromkeys(self.assessment_dimensions))


class LCIFlow(BaseModel):
    """One foreground or background lifecycle inventory flow.

    ``impact_factors`` maps an impact category to a characterization factor per
    ``unit``. Factors may be negative for an explicitly modelled avoided burden;
    that assumption should be documented in ``notes`` and ``evidence_refs``.
    """

    flow_id: str
    name: str
    stage: str
    direction: Literal["input", "output"] = "input"
    quantity: float = Field(gt=0)
    unit: str
    source: str = ""
    region: str = "global"
    data_quality_score: int = Field(default=3, ge=1, le=5)
    verified: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    impact_factors: dict[str, float] = Field(default_factory=dict)
    uncertainty_low: dict[str, float] = Field(default_factory=dict)
    uncertainty_high: dict[str, float] = Field(default_factory=dict)
    allocation_method: str = ""
    notes: str = ""

    @field_validator("flow_id", "name", "unit", "source", "region", "allocation_method", "notes")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        return _normalise_string(value)

    @field_validator("stage", mode="before")
    @classmethod
    def normalize_stage(cls, value: object) -> str:
        return _normalize_stage(value)

    @field_validator("impact_factors", "uncertainty_low", "uncertainty_high", mode="before")
    @classmethod
    def normalize_factor_keys(cls, values: object) -> dict[str, float]:
        if values is None:
            return {}
        return {_normalize_key(key): float(value) for key, value in dict(values).items()}

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def normalize_evidence_refs(cls, values: object) -> list[str]:
        if values is None:
            return []
        return [str(value).strip() for value in values if str(value).strip()]  # type: ignore[union-attr]


class LCAContribution(BaseModel):
    flow_id: str
    flow_name: str
    lifecycle_stage: str
    category: str
    value: float
    unit: str
    share_pct: float


class Hotspot(BaseModel):
    rank: int
    lifecycle_stage: str
    category: str
    value: float
    unit: str
    share_pct: float
    flow_ids: list[str] = Field(default_factory=list)


class DataQualitySummary(BaseModel):
    total_flows: int
    characterized_flows: int
    sourced_flows: int
    verified_flows: int
    average_score: float
    evidence_coverage_pct: float
    characterization_coverage_pct: float
    low_quality_flow_ids: list[str] = Field(default_factory=list)


class LCAInterpretation(BaseModel):
    dominant_categories: list[str] = Field(default_factory=list)
    dominant_stages: list[str] = Field(default_factory=list)
    tradeoff_flags: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)


class LCAResult(BaseModel):
    study_id: str
    product_system: str
    functional_unit: str
    lcia_method: str
    impacts: dict[str, float] = Field(default_factory=dict)
    impact_units: dict[str, str] = Field(default_factory=dict)
    stage_impacts: dict[str, dict[str, float]] = Field(default_factory=dict)
    contributions: list[LCAContribution] = Field(default_factory=list)
    hotspots: list[Hotspot] = Field(default_factory=list)
    data_quality: DataQualitySummary
    interpretation: LCAInterpretation
    model_basis: str = (
        "LCI quantity × caller-supplied characterization factor; not a bundled database calculation."
    )

    @property
    def climate_change_value(self) -> float:
        for category, value in self.impacts.items():
            if category in CLIMATE_CATEGORY_ALIASES:
                return value
        return 0.0


class LCAScenario(BaseModel):
    """A transparent what-if scenario for LCA sensitivity analysis."""

    scenario_id: str
    label: str
    flow_multipliers: dict[str, float] = Field(default_factory=dict)
    category_multipliers: dict[str, float] = Field(default_factory=dict)
    description: str = ""

    @field_validator("flow_multipliers", mode="before")
    @classmethod
    def validate_flow_multipliers(cls, values: object) -> dict[str, float]:
        normalized = {str(key).strip(): float(value) for key, value in dict(values or {}).items()}
        if any(value < 0 for value in normalized.values()):
            raise ValueError("Scenario multipliers must be non-negative")
        return normalized

    @field_validator("category_multipliers", mode="before")
    @classmethod
    def validate_category_multipliers(cls, values: object) -> dict[str, float]:
        normalized = {_normalize_key(key): float(value) for key, value in dict(values or {}).items()}
        if any(value < 0 for value in normalized.values()):
            raise ValueError("Scenario multipliers must be non-negative")
        return normalized


class SensitivityScenarioResult(BaseModel):
    scenario_id: str
    label: str
    impacts: dict[str, float]
    delta_pct_by_category: dict[str, float | None]
    dominant_category: str = ""
    dominant_stage: str = ""


class LCASensitivityResult(BaseModel):
    study_id: str
    baseline_impacts: dict[str, float]
    scenarios: list[SensitivityScenarioResult]
    robust_conclusion: Literal["robust", "sensitive", "inconclusive"]
    method_note: str = (
        "Scenario results are deterministic what-if calculations; they do not replace probabilistic uncertainty analysis."
    )


class ReadinessCheck(BaseModel):
    check_id: str
    label: str
    status: ReadinessStatus
    weight: float
    detail: str


class LCAReadiness(BaseModel):
    study_id: str
    score: float = Field(ge=0, le=100)
    band: Literal["not_ready", "foundational", "decision_ready", "assurance_prepared"]
    checks: list[ReadinessCheck]
    gaps: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    assessment_basis: str = "Deterministic implementation-readiness screen; not an ISO conformity opinion."


class LCMAction(BaseModel):
    action_id: str
    lifecycle_stage: str
    priority: Literal["high", "medium", "low"]
    hotspot_category: str
    problem_statement: str
    recommended_action: str
    target_metric: str
    owner: str = "Unassigned"
    due_period: str = "Next review cycle"
    status: Literal["proposed", "accepted", "in_progress", "complete", "blocked"] = "proposed"
    evidence_needed: list[str] = Field(default_factory=list)


class LCMPlan(BaseModel):
    study_id: str
    objective: str
    current_state: str
    actions: list[LCMAction] = Field(default_factory=list)
    monitoring_indicators: list[str] = Field(default_factory=list)
    governance_cadence: str = "Quarterly, with an annual goal-and-scope refresh."
    decision_gates: list[str] = Field(default_factory=list)
    caveat: str = (
        "Actions are management recommendations. No reduction claim is made until a scenario or follow-up LCA supports it."
    )


class LifecycleCostLine(BaseModel):
    line_id: str
    name: str
    stage: str
    amount: float
    currency: str = "USD"
    period_year: int = Field(default=0, ge=0)
    cost_type: Literal[
        "capex",
        "operating",
        "maintenance",
        "replacement",
        "end_of_life",
        "externality",
        "other",
    ] = "other"
    source: str = ""
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("stage", mode="before")
    @classmethod
    def normalize_stage(cls, value: object) -> str:
        return _normalize_stage(value)


class LCCResult(BaseModel):
    total_nominal: float
    total_present_value: float
    currency: str
    discount_rate: float
    costs_by_stage: dict[str, float]
    line_count: int
    evidence_coverage_pct: float
    note: str = "LCC is reported separately from environmental impact units; do not add the figures together."


class SocialIndicator(BaseModel):
    indicator_id: str
    name: str
    stakeholder_group: Literal[
        "workers",
        "communities",
        "consumers",
        "value_chain",
        "society",
        "other",
    ]
    stage: str
    value: float = Field(ge=0)
    unit: str
    direction: Literal["positive", "negative", "neutral"] = "neutral"
    quality_score: int = Field(default=3, ge=1, le=5)
    source: str = ""
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("stage", mode="before")
    @classmethod
    def normalize_stage(cls, value: object) -> str:
        return _normalize_stage(value)


class SocialLCAResult(BaseModel):
    indicator_values: dict[str, float]
    negative_hotspots: list[str]
    stakeholder_coverage: dict[str, int]
    stage_coverage: dict[str, int]
    average_quality_score: float
    evidence_coverage_pct: float
    note: str = (
        "Social indicators remain disaggregated by unit and stakeholder; this is a coverage and hotspot view, not a monetized social score."
    )


class LCSAResult(BaseModel):
    study_id: str
    environmental: LCAResult
    economic: LCCResult | None = None
    social: SocialLCAResult | None = None
    dimensions_present: list[str]
    gaps: list[str] = Field(default_factory=list)
    decision_flags: list[str] = Field(default_factory=list)


def list_lcia_methods() -> list[dict[str, Any]]:
    """Return method-selection metadata without implying bundled factors."""
    return [
        {
            "method_id": method_id,
            **metadata,
            "framework_sources": LCA_FRAMEWORK_SOURCES,
        }
        for method_id, metadata in LCIA_METHODS.items()
    ]


def _impact_unit(category: str) -> str:
    return IMPACT_CATEGORY_UNITS.get(category, "factor-defined unit")


def _dominant(mapping: dict[str, float]) -> str:
    return max(mapping, key=lambda key: abs(mapping[key]), default="")


def _calculate_result(
    study: LCAStudy,
    flows: list[LCIFlow],
    *,
    flow_multipliers: dict[str, float] | None = None,
    category_multipliers: dict[str, float] | None = None,
) -> LCAResult:
    allowed_stages = set(study.included_stages)
    outside = sorted({flow.stage for flow in flows if flow.stage not in allowed_stages})
    if outside:
        raise ValueError(
            f"LCI flows fall outside the study boundary: {outside}; "
            "move them into the boundary or document them as excluded."
        )
    if not flows:
        raise ValueError("At least one LCI flow is required")

    flow_multipliers = flow_multipliers or {}
    category_multipliers = category_multipliers or {}
    impacts: dict[str, float] = defaultdict(float)
    stage_impacts: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    raw_contributions: list[tuple[str, str, str, str, float]] = []

    for flow in flows:
        multiplier = flow_multipliers.get(flow.flow_id, 1.0)
        if multiplier < 0:
            raise ValueError("Flow multipliers must be non-negative")
        normalized_quantity = flow.quantity / study.reference_quantity * multiplier
        for category, factor in flow.impact_factors.items():
            value = normalized_quantity * factor * category_multipliers.get(category, 1.0)
            impacts[category] += value
            stage_impacts[flow.stage][category] += value
            raw_contributions.append((flow.flow_id, flow.name, flow.stage, category, value))

    rounded_impacts = {key: round(value, 8) for key, value in sorted(impacts.items())}
    rounded_stage_impacts = {
        stage: {category: round(value, 8) for category, value in sorted(values.items())}
        for stage, values in sorted(stage_impacts.items(), key=lambda item: STAGE_ORDER.index(item[0]))
    }

    contributions: list[LCAContribution] = []
    for flow_id, flow_name, stage, category, value in raw_contributions:
        denominator = abs(impacts[category])
        share = 0.0 if denominator == 0 else abs(value) / denominator * 100
        contributions.append(
            LCAContribution(
                flow_id=flow_id,
                flow_name=flow_name,
                lifecycle_stage=stage,
                category=category,
                value=round(value, 8),
                unit=_impact_unit(category),
                share_pct=round(share, 2),
            )
        )

    aggregate: dict[tuple[str, str], dict[str, Any]] = {}
    for contribution in contributions:
        key = (contribution.lifecycle_stage, contribution.category)
        bucket = aggregate.setdefault(key, {"value": 0.0, "flow_ids": []})
        bucket["value"] += contribution.value
        bucket["flow_ids"].append(contribution.flow_id)
    candidates: list[tuple[float, str, str, dict[str, Any]]] = []
    for (stage, category), bucket in aggregate.items():
        denominator = abs(impacts[category])
        share = 0.0 if denominator == 0 else abs(bucket["value"]) / denominator * 100
        candidates.append((abs(bucket["value"]), stage, category, {**bucket, "share": share}))
    candidates.sort(reverse=True)
    hotspots = [
        Hotspot(
            rank=index,
            lifecycle_stage=stage,
            category=category,
            value=round(bucket["value"], 8),
            unit=_impact_unit(category),
            share_pct=round(bucket["share"], 2),
            flow_ids=sorted(set(bucket["flow_ids"])),
        )
        for index, (_absolute, stage, category, bucket) in enumerate(candidates[:10], start=1)
    ]

    total_flows = len(flows)
    characterized = sum(bool(flow.impact_factors) for flow in flows)
    sourced = sum(bool(flow.source or flow.evidence_refs) for flow in flows)
    verified = sum(flow.verified for flow in flows)
    average_score = round(sum(flow.data_quality_score for flow in flows) / total_flows, 2)
    quality = DataQualitySummary(
        total_flows=total_flows,
        characterized_flows=characterized,
        sourced_flows=sourced,
        verified_flows=verified,
        average_score=average_score,
        evidence_coverage_pct=round(sourced / total_flows * 100, 2),
        characterization_coverage_pct=round(characterized / total_flows * 100, 2),
        low_quality_flow_ids=[flow.flow_id for flow in flows if flow.data_quality_score <= 2],
    )

    category_order = sorted(rounded_impacts, key=lambda key: abs(rounded_impacts[key]), reverse=True)
    stage_totals = {
        stage: sum(abs(value) for value in values.values()) for stage, values in stage_impacts.items()
    }
    stage_order = sorted(stage_totals, key=stage_totals.get, reverse=True)
    top_stages = {
        category: _dominant(
            {stage: values.get(category, 0.0) for stage, values in stage_impacts.items()}
        )
        for category in rounded_impacts
    }
    tradeoff_flags: list[str] = []
    if len({stage for stage in top_stages.values() if stage}) > 1:
        tradeoff_flags.append(
            "Different impact categories are led by different lifecycle stages; review the full profile before optimizing one category."
        )
    if any(value < 0 for value in rounded_impacts.values()):
        tradeoff_flags.append(
            "Negative contributions are present; verify avoided-burden, substitution, or recycling assumptions and allocation choices."
        )
    limitations: list[str] = []
    if study.lcia_method not in LCIA_METHODS:
        limitations.append("The selected LCIA method is not in the local method metadata catalogue.")
    if quality.characterization_coverage_pct < 100:
        limitations.append("Some LCI flows have no characterization factors and are absent from impact totals.")
    if quality.evidence_coverage_pct < 80:
        limitations.append("Less than 80% of flows have a source or evidence reference.")
    if "end_of_life" not in study.included_stages and study.boundary == "cradle_to_grave":
        limitations.append("The declared grave boundary has no end-of-life stage in the included flow set.")
    interpretation = LCAInterpretation(
        dominant_categories=category_order[:5],
        dominant_stages=stage_order[:5],
        tradeoff_flags=tradeoff_flags,
        limitations=limitations,
        key_assumptions=list(study.assumptions),
    )
    return LCAResult(
        study_id=study.study_id,
        product_system=study.product_system,
        functional_unit=study.functional_unit,
        lcia_method=study.lcia_method,
        impacts=rounded_impacts,
        impact_units={category: _impact_unit(category) for category in rounded_impacts},
        stage_impacts=rounded_stage_impacts,
        contributions=contributions,
        hotspots=hotspots,
        data_quality=quality,
        interpretation=interpretation,
    )


def calculate_lca(
    study: LCAStudy | dict[str, Any],
    flows: Iterable[LCIFlow | dict[str, Any]],
) -> LCAResult:
    """Run a deterministic LCIA roll-up for an LCI payload."""
    study_model = study if isinstance(study, LCAStudy) else LCAStudy.model_validate(study)
    flow_models = [flow if isinstance(flow, LCIFlow) else LCIFlow.model_validate(flow) for flow in flows]
    return _calculate_result(study_model, flow_models)


def run_lca_sensitivity(
    study: LCAStudy | dict[str, Any],
    flows: Iterable[LCIFlow | dict[str, Any]],
    scenarios: Iterable[LCAScenario | dict[str, Any]],
) -> LCASensitivityResult:
    """Run explicit flow/category what-if scenarios and compare hotspots."""
    study_model = study if isinstance(study, LCAStudy) else LCAStudy.model_validate(study)
    flow_models = [flow if isinstance(flow, LCIFlow) else LCIFlow.model_validate(flow) for flow in flows]
    scenario_models = [
        scenario if isinstance(scenario, LCAScenario) else LCAScenario.model_validate(scenario)
        for scenario in scenarios
    ]
    if not scenario_models:
        raise ValueError("At least one sensitivity scenario is required")
    baseline = _calculate_result(study_model, flow_models)
    scenario_results: list[SensitivityScenarioResult] = []
    dominant_categories: list[str] = []
    dominant_stages: list[str] = []
    inconclusive = False
    for scenario in scenario_models:
        result = _calculate_result(
            study_model,
            flow_models,
            flow_multipliers=scenario.flow_multipliers,
            category_multipliers=scenario.category_multipliers,
        )
        deltas: dict[str, float | None] = {}
        all_categories = set(baseline.impacts) | set(result.impacts)
        for category in sorted(all_categories):
            base = baseline.impacts.get(category, 0.0)
            current = result.impacts.get(category, 0.0)
            deltas[category] = None if base == 0 else round((current - base) / abs(base) * 100, 2)
            inconclusive = inconclusive or base == 0
        dominant_category = _dominant(result.impacts)
        dominant_stage = result.interpretation.dominant_stages[0] if result.interpretation.dominant_stages else ""
        dominant_categories.append(dominant_category)
        dominant_stages.append(dominant_stage)
        scenario_results.append(
            SensitivityScenarioResult(
                scenario_id=scenario.scenario_id,
                label=scenario.label,
                impacts=result.impacts,
                delta_pct_by_category=deltas,
                dominant_category=dominant_category,
                dominant_stage=dominant_stage,
            )
        )
    max_delta = max(
        (
            abs(delta)
            for item in scenario_results
            for delta in item.delta_pct_by_category.values()
            if delta is not None
        ),
        default=0.0,
    )
    robust = "inconclusive" if inconclusive else "sensitive" if max_delta > 20 else "robust"
    if len(set(dominant_categories)) > 1 or len(set(dominant_stages)) > 1:
        robust = "sensitive"
    return LCASensitivityResult(
        study_id=study_model.study_id,
        baseline_impacts=baseline.impacts,
        scenarios=scenario_results,
        robust_conclusion=robust,
    )


def calculate_lcc(
    lines: Iterable[LifecycleCostLine | dict[str, Any]],
    *,
    reference_quantity: float = 1.0,
    discount_rate: float = 0.0,
) -> LCCResult:
    """Calculate nominal and discounted lifecycle costs without mixing units."""
    if reference_quantity <= 0:
        raise ValueError("reference_quantity must be positive")
    if discount_rate < 0:
        raise ValueError("discount_rate must be non-negative")
    line_models = [line if isinstance(line, LifecycleCostLine) else LifecycleCostLine.model_validate(line) for line in lines]
    currencies = {line.currency for line in line_models}
    if len(currencies) > 1:
        raise ValueError("All lifecycle cost lines must use the same currency")
    currency = next(iter(currencies), "USD")
    by_stage: dict[str, float] = defaultdict(float)
    nominal = 0.0
    present_value = 0.0
    for line in line_models:
        value = line.amount / reference_quantity
        nominal += value
        present_value += value / ((1 + discount_rate) ** line.period_year)
        by_stage[line.stage] += value
    evidence_coverage = (
        0.0
        if not line_models
        else round(sum(bool(line.source or line.evidence_refs) for line in line_models) / len(line_models) * 100, 2)
    )
    return LCCResult(
        total_nominal=round(nominal, 2),
        total_present_value=round(present_value, 2),
        currency=currency,
        discount_rate=discount_rate,
        costs_by_stage={stage: round(value, 2) for stage, value in sorted(by_stage.items())},
        line_count=len(line_models),
        evidence_coverage_pct=evidence_coverage,
    )


def assess_social_lca(
    indicators: Iterable[SocialIndicator | dict[str, Any]],
) -> SocialLCAResult:
    """Provide a transparent, disaggregated S-LCA coverage and hotspot view."""
    rows = [
        indicator
        if isinstance(indicator, SocialIndicator)
        else SocialIndicator.model_validate(indicator)
        for indicator in indicators
    ]
    values: dict[str, float] = defaultdict(float)
    stakeholder_coverage: dict[str, int] = defaultdict(int)
    stage_coverage: dict[str, int] = defaultdict(int)
    negative_hotspots: list[str] = []
    for row in rows:
        values[row.indicator_id] += row.value
        stakeholder_coverage[row.stakeholder_group] += 1
        stage_coverage[row.stage] += 1
        if row.direction == "negative":
            negative_hotspots.append(f"{row.stakeholder_group}:{row.name} ({row.stage})")
    return SocialLCAResult(
        indicator_values={key: round(value, 4) for key, value in sorted(values.items())},
        negative_hotspots=negative_hotspots,
        stakeholder_coverage=dict(sorted(stakeholder_coverage.items())),
        stage_coverage=dict(sorted(stage_coverage.items())),
        average_quality_score=round(sum(row.quality_score for row in rows) / len(rows), 2) if rows else 0.0,
        evidence_coverage_pct=(
            round(sum(bool(row.source or row.evidence_refs) for row in rows) / len(rows) * 100, 2)
            if rows
            else 0.0
        ),
    )


def calculate_lcsa(
    study: LCAStudy | dict[str, Any],
    flows: Iterable[LCIFlow | dict[str, Any]],
    *,
    cost_lines: Iterable[LifecycleCostLine | dict[str, Any]] = (),
    social_indicators: Iterable[SocialIndicator | dict[str, Any]] = (),
    discount_rate: float = 0.0,
) -> LCSAResult:
    """Compose environmental LCA, lifecycle cost, and social indicators."""
    study_model = study if isinstance(study, LCAStudy) else LCAStudy.model_validate(study)
    flow_models = [flow if isinstance(flow, LCIFlow) else LCIFlow.model_validate(flow) for flow in flows]
    environmental = _calculate_result(study_model, flow_models)
    cost_models = [
        line if isinstance(line, LifecycleCostLine) else LifecycleCostLine.model_validate(line)
        for line in cost_lines
    ]
    social_models = [
        indicator
        if isinstance(indicator, SocialIndicator)
        else SocialIndicator.model_validate(indicator)
        for indicator in social_indicators
    ]
    economic = (
        calculate_lcc(cost_models, reference_quantity=study_model.reference_quantity, discount_rate=discount_rate)
        if cost_models
        else None
    )
    social = assess_social_lca(social_models) if social_models else None
    dimensions_present = ["environmental"]
    gaps: list[str] = []
    if "economic" in study_model.assessment_dimensions:
        if economic is None:
            gaps.append("Economic dimension is declared but no lifecycle cost lines were supplied.")
        else:
            dimensions_present.append("economic")
    if "social" in study_model.assessment_dimensions:
        if social is None:
            gaps.append("Social dimension is declared but no social indicators were supplied.")
        else:
            dimensions_present.append("social")
    flags = list(environmental.interpretation.tradeoff_flags)
    flags.append("Environmental, economic, and social outputs use different units; apply a documented MCDA or decision rule.")
    if economic and economic.evidence_coverage_pct < 80:
        flags.append("Economic cost evidence coverage is below 80%.")
    if social and social.negative_hotspots:
        flags.append("Negative social indicators require stakeholder review and mitigation ownership.")
    return LCSAResult(
        study_id=study_model.study_id,
        environmental=environmental,
        economic=economic,
        social=social,
        dimensions_present=dimensions_present,
        gaps=gaps,
        decision_flags=flags,
    )


def assess_lca_readiness(
    study: LCAStudy | dict[str, Any],
    flows: Iterable[LCIFlow | dict[str, Any]],
    *,
    scenarios: Iterable[LCAScenario | dict[str, Any]] = (),
    cost_lines: Iterable[LifecycleCostLine | dict[str, Any]] = (),
    social_indicators: Iterable[SocialIndicator | dict[str, Any]] = (),
) -> LCAReadiness:
    """Score whether a study is ready for a decision or management cycle."""
    study_model = study if isinstance(study, LCAStudy) else LCAStudy.model_validate(study)
    flow_models = [flow if isinstance(flow, LCIFlow) else LCIFlow.model_validate(flow) for flow in flows]
    scenario_models = [
        scenario if isinstance(scenario, LCAScenario) else LCAScenario.model_validate(scenario)
        for scenario in scenarios
    ]
    cost_models = [
        line if isinstance(line, LifecycleCostLine) else LifecycleCostLine.model_validate(line)
        for line in cost_lines
    ]
    social_models = [
        indicator
        if isinstance(indicator, SocialIndicator)
        else SocialIndicator.model_validate(indicator)
        for indicator in social_indicators
    ]
    result = None
    if flow_models:
        result = _calculate_result(study_model, flow_models)
    checks: list[ReadinessCheck] = []

    def add(check_id: str, label: str, status: ReadinessStatus, weight: float, detail: str) -> None:
        checks.append(ReadinessCheck(check_id=check_id, label=label, status=status, weight=weight, detail=detail))

    goal_complete = bool(study_model.goal and study_model.intended_application and study_model.audience)
    add(
        "goal_scope",
        "Goal, application, and audience",
        "pass" if goal_complete else "partial" if study_model.goal else "gap",
        15,
        "Goal, intended application, and audience are recorded." if goal_complete else "Record why the study is being done, how it will be used, and who will read it.",
    )
    fu_complete = bool(study_model.functional_unit and study_model.reference_flow)
    add(
        "functional_unit",
        "Functional unit and reference flow",
        "pass" if fu_complete else "partial" if study_model.functional_unit else "gap",
        15,
        "Functional unit is defined with a reference flow." if fu_complete else "Add a performance-based reference flow so alternatives are comparable.",
    )
    boundary_complete = bool(study_model.included_stages)
    add(
        "system_boundary",
        "System boundary and exclusions",
        "pass" if boundary_complete and study_model.excluded_processes else "partial" if boundary_complete else "gap",
        10,
        "Boundary stages and at least one explicit exclusion are documented." if boundary_complete and study_model.excluded_processes else "List boundary stages and record exclusions/assumptions explicitly.",
    )
    lci_status: ReadinessStatus = "pass" if flow_models and result and result.data_quality.characterization_coverage_pct == 100 else "partial" if flow_models else "gap"
    add(
        "inventory",
        "LCI coverage",
        lci_status,
        20,
        "All supplied flows are characterized." if lci_status == "pass" else "Add flows or characterization factors for all material processes.",
    )
    data_status: ReadinessStatus = "gap"
    data_detail = "No LCI data were supplied."
    if result:
        data_status = "pass" if result.data_quality.average_score >= 4 else "partial" if result.data_quality.average_score >= 3 else "gap"
        data_detail = f"Average LCI data-quality score: {result.data_quality.average_score}/5."
    add("data_quality", "LCI data quality", data_status, 10, data_detail)
    evidence_status: ReadinessStatus = "gap"
    evidence_detail = "No source/evidence references were supplied."
    if result:
        evidence_status = "pass" if result.data_quality.evidence_coverage_pct >= 80 else "partial" if result.data_quality.evidence_coverage_pct > 0 else "gap"
        evidence_detail = f"Source/evidence coverage: {result.data_quality.evidence_coverage_pct}%."
    add("provenance", "Source and evidence provenance", evidence_status, 10, evidence_detail)
    add(
        "lcia_method",
        "LCIA method selection",
        "pass" if study_model.lcia_method in LCIA_METHODS else "partial",
        5,
        "Method is present in the local selection catalogue." if study_model.lcia_method in LCIA_METHODS else "Record the method rationale and pin its factor source/version.",
    )
    uncertainty_status = "pass" if scenario_models or any(flow.uncertainty_low or flow.uncertainty_high for flow in flow_models) else "partial"
    add(
        "uncertainty",
        "Uncertainty or sensitivity treatment",
        uncertainty_status,
        5,
        "Explicit uncertainty bounds or sensitivity scenarios are present." if uncertainty_status == "pass" else "Run at least one documented scenario or add factor uncertainty bounds.",
    )
    interpretation_status = "pass" if result and result.hotspots else "partial" if result else "gap"
    add(
        "interpretation",
        "Interpretation and hotspot review",
        interpretation_status,
        10,
        "Hotspots and limitations are available for review." if interpretation_status == "pass" else "Run the assessment and review hotspots/limitations before making a claim.",
    )
    if "economic" in study_model.assessment_dimensions:
        add(
            "lcc",
            "Lifecycle cost dimension",
            "pass" if cost_models else "gap",
            5,
            "Cost lines are available." if cost_models else "Supply lifecycle cost lines or remove the economic dimension from scope.",
        )
    if "social" in study_model.assessment_dimensions:
        add(
            "slca",
            "Social lifecycle dimension",
            "pass" if social_models else "gap",
            5,
            "Social indicators are available." if social_models else "Supply stakeholder/stage indicators or remove the social dimension from scope.",
        )
    earned = sum(check.weight * (1.0 if check.status == "pass" else 0.5 if check.status == "partial" else 0.0) for check in checks)
    total_weight = sum(check.weight for check in checks)
    score = round(earned / total_weight * 100, 2) if total_weight else 0.0
    band = "assurance_prepared" if score >= 85 else "decision_ready" if score >= 65 else "foundational" if score >= 40 else "not_ready"
    gaps = [check.detail for check in checks if check.status != "pass"]
    next_actions = [
        "Approve the goal, intended application, audience, functional unit, and system boundary.",
        "Close high-contribution LCI data gaps with primary data or documented proxy choices.",
        "Run a sensitivity scenario for the top hotspot and review possible burden shifting.",
    ]
    if "economic" in study_model.assessment_dimensions and not cost_models:
        next_actions.append("Add lifecycle cost data using the same functional unit and boundary.")
    if "social" in study_model.assessment_dimensions and not social_models:
        next_actions.append("Add stakeholder and lifecycle-stage social indicators, with consent/evidence provenance.")
    return LCAReadiness(
        study_id=study_model.study_id,
        score=score,
        band=band,
        checks=checks,
        gaps=gaps,
        next_actions=next_actions,
    )


_LCM_RECOMMENDATIONS = {
    "raw_materials": "Engage suppliers for primary data, reduce material intensity, and test recycled or lower-impact inputs.",
    "manufacturing": "Review yield, process energy, heat/electricity sources, and process-loss hotspots with operations owners.",
    "distribution": "Model route, load factor, distance, mode, and packaging choices; prioritize the highest-contribution lanes.",
    "use": "Validate lifetime, user energy/material consumption, maintenance, and performance assumptions against field evidence.",
    "end_of_life": "Improve design for reuse/recycling, take-back coverage, sorting assumptions, and end-of-life data quality.",
    "beyond_system": "Document substitution/avoided-burden assumptions and test them as a separate consequential scenario.",
}


def build_lcm_plan(
    result: LCAResult,
    *,
    owners_by_stage: dict[str, str] | None = None,
    due_period_by_stage: dict[str, str] | None = None,
) -> LCMPlan:
    """Turn LCA hotspots into a managed improvement backlog."""
    owners_by_stage = owners_by_stage or {}
    due_period_by_stage = due_period_by_stage or {}
    actions: list[LCMAction] = []
    indicators: list[str] = []
    for index, hotspot in enumerate(result.hotspots[:6], start=1):
        priority = "high" if hotspot.share_pct >= 25 else "medium" if hotspot.share_pct >= 10 else "low"
        metric = f"{hotspot.category} ({hotspot.unit}) per {result.functional_unit}"
        evidence_needed = [
            "Owner-confirmed primary data or a documented proxy for the hotspot flow.",
            "A follow-up scenario showing the proposed change and any cross-category trade-off.",
        ]
        actions.append(
            LCMAction(
                action_id=f"lcm-{index:02d}",
                lifecycle_stage=hotspot.lifecycle_stage,
                priority=priority,
                hotspot_category=hotspot.category,
                problem_statement=(
                    f"{hotspot.lifecycle_stage} contributes {hotspot.share_pct}% of the "
                    f"{hotspot.category} profile ({hotspot.value:.4g} {hotspot.unit})."
                ),
                recommended_action=_LCM_RECOMMENDATIONS[hotspot.lifecycle_stage],
                target_metric=metric,
                owner=owners_by_stage.get(hotspot.lifecycle_stage, "Unassigned"),
                due_period=due_period_by_stage.get(hotspot.lifecycle_stage, "Next review cycle"),
                evidence_needed=evidence_needed,
            )
        )
        indicators.append(metric)
    objective = f"Reduce lifecycle impacts for {result.product_system} per {result.functional_unit}."
    current_state = (
        f"Top hotspot is {result.hotspots[0].lifecycle_stage}/{result.hotspots[0].category} "
        f"at {result.hotspots[0].share_pct}% of its category profile."
        if result.hotspots
        else "No characterized hotspots are available; close LCI coverage gaps first."
    )
    return LCMPlan(
        study_id=result.study_id,
        objective=objective,
        current_state=current_state,
        actions=actions,
        monitoring_indicators=sorted(set(indicators)),
        decision_gates=[
            "Goal and scope approved",
            "Hotspot owner assigned",
            "Primary data/proxy evidence reviewed",
            "Scenario sensitivity reviewed",
            "Follow-up LCA and stakeholder impacts reviewed",
        ],
    )


__all__ = [
    "BOUNDARY_STAGES",
    "LCA_FRAMEWORK_SOURCES",
    "LCIA_METHODS",
    "Hotspot",
    "LCAContribution",
    "LCAInterpretation",
    "LCAReadiness",
    "LCAResult",
    "LCAScenario",
    "LCASensitivityResult",
    "LCAStudy",
    "LCCResult",
    "LCIFlow",
    "LCMAction",
    "LCMPlan",
    "LifecycleCostLine",
    "ReadinessCheck",
    "SensitivityScenarioResult",
    "SocialIndicator",
    "SocialLCAResult",
    "assess_lca_readiness",
    "assess_social_lca",
    "build_lcm_plan",
    "calculate_lca",
    "calculate_lcc",
    "calculate_lcsa",
    "list_lcia_methods",
    "run_lca_sensitivity",
]
