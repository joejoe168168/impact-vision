"""Pydantic models for IRIS+ metrics, SDGs, assessments, and impact claims."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DimensionTags(BaseModel):
    """5 Dimensions of Impact tags from the IRIS+ catalog."""

    what: bool = False
    who: bool = False
    how_much_scale: bool = False
    how_much_depth: bool = False
    how_much_duration: bool = False
    contribution_depth: bool = False
    contribution_duration: bool = False
    risk: bool = False

    @property
    def active_dimensions(self) -> list[str]:
        return [k for k, v in self.model_dump().items() if v]


class JointImpactIndicators(BaseModel):
    """Joint Impact Indicators (JII) flags."""

    gender: bool = False
    jobs: bool = False
    climate: bool = False


class Metric(BaseModel):
    """A single IRIS+ metric from the 5.3c catalog."""

    id: str = Field(description="Unique metric ID (e.g. PI4060, OI4112)")
    name: str
    definition: str = ""
    footnote: str | None = None
    calculation: str | None = None
    usage_guidance: str | None = None
    primary_impact_category: str = ""
    is_cross_category: bool = False
    impact_themes: list[str] = Field(default_factory=list)
    focus: Literal["social", "environmental", "both"] = "both"
    section: str = ""
    subsection: str = ""
    citation: str = ""
    metric_type: Literal["metric", "submetric"] = "metric"
    related_metrics: list[str] = Field(default_factory=list)
    metric_level: str = ""
    quantity_type: str = ""
    reporting_format: str = ""
    sdg_goals: list[int] = Field(default_factory=list)
    sdg_targets: list[str] = Field(default_factory=list)
    dimensions: DimensionTags = Field(default_factory=DimensionTags)
    jii: JointImpactIndicators = Field(default_factory=JointImpactIndicators)
    stakeholders: list[str] = Field(default_factory=list)
    financials: list[str] = Field(default_factory=list)


class SDGTarget(BaseModel):
    """A single SDG target (e.g. 1.1, 5.a)."""

    id: str = Field(description="Target ID like '1.1' or '5.a'")
    goal: int = Field(description="Parent SDG goal number (1-17)")
    description: str = ""


class SDGGoal(BaseModel):
    """One of the 17 UN Sustainable Development Goals."""

    number: int = Field(ge=1, le=17)
    name: str
    description: str = ""
    targets: list[SDGTarget] = Field(default_factory=list)


class ImpactTarget(BaseModel):
    """A structured impact target for tracking progress."""

    metric_id: str = Field(description="IRIS+ metric ID (e.g. OI4112)")
    target_value: float | None = Field(default=None, description="Numeric target value (None for qualitative targets)")
    target_unit: str = Field(default="", description="Unit (e.g. 'tCO2e', 'count')")
    target_date: str = Field(default="", description="Target achievement date (e.g. '2027')")
    baseline_value: float | None = Field(default=None, description="Baseline value at start")
    baseline_date: str = Field(default="", description="Baseline date (e.g. '2024')")
    description: str = Field(default="", description="Free-text target description")


class MetricValue(BaseModel):
    """A single reported metric value with context for time-series tracking."""

    metric_id: str = Field(description="IRIS+ metric ID (e.g. OI4112)")
    value: Any = Field(description="Reported value (numeric, string, or structured)")
    unit: str = Field(default="", description="Unit of measurement (e.g. 'tCO2e', 'count', 'USD')")
    period: str = Field(default="", description="Reporting period (e.g. 'FY2025', 'Q1 2026', '2025-H1')")
    timestamp: str = Field(default="", description="ISO date when value was reported (e.g. '2026-04-16')")
    source: str = Field(default="", description="Source of data (e.g. 'pitch_deck', 'self_reported', 'audited')")
    verified: bool = Field(default=False, description="Whether value has been third-party verified")
    verification_status: Literal[
        "self_reported", "management_verified", "third_party_verified", "audited"
    ] = Field(default="self_reported", description="Verification level")
    reported_by: str = Field(default="", description="Name/role of person who reported this value")
    notes: str = ""


class AuditTrailEntry(BaseModel):
    """A single audit trail entry tracking who reported what and when."""

    metric_id: str = Field(description="IRIS+ metric ID")
    action: Literal["created", "updated", "verified", "deleted"] = Field(description="Action taken")
    timestamp: str = Field(description="ISO datetime of action")
    actor: str = Field(default="", description="Who performed the action (name, role, or system)")
    old_value: Any = Field(default=None, description="Previous value (for updates)")
    new_value: Any = Field(default=None, description="New value")
    evidence: str = Field(default="", description="Link/reference to supporting evidence")
    notes: str = ""


class BeneficiaryFeedback(BaseModel):
    """Structured beneficiary feedback data (e.g. 60 Decibels Lean Data)."""

    satisfaction_score: float | None = Field(default=None, description="Overall satisfaction (1-5 scale)")
    nps: float | None = Field(default=None, description="Net Promoter Score (-100 to 100)")
    sample_size: int = Field(default=0, description="Number of beneficiaries surveyed")
    survey_date: str = Field(default="", description="Date of survey (e.g. '2026-Q1')")
    methodology: str = Field(default="", description="Survey methodology (e.g. '60 Decibels Lean Data', 'in-person')")
    quality_of_life_improvement: float | None = Field(
        default=None, description="% reporting quality of life improvement",
    )
    would_recommend: float | None = Field(
        default=None, description="% who would recommend the product/service",
    )
    themes: list[str] = Field(default_factory=list, description="Qualitative themes from open-ended responses")
    challenges: list[str] = Field(default_factory=list, description="Reported challenges or negative feedback")
    quotes: list[str] = Field(default_factory=list, description="Representative beneficiary quotes")
    segments: dict[str, Any] = Field(
        default_factory=dict,
        description="Disaggregated data by segment (e.g. {'gender': {'female': 4.2, 'male': 3.8}})",
    )


class Company(BaseModel):
    """A company or startup being assessed for impact."""

    name: str
    description: str = ""
    sector: str = ""
    geography: str = Field(default="", description="Country or region (e.g. 'Kenya', 'Southeast Asia')")
    stage: Literal["", "pre-seed", "seed", "series-a", "series-b", "growth", "mature"] = Field(
        default="", description="Investment stage"
    )
    founded_year: int | None = Field(default=None, description="Year founded")
    employees: int | None = Field(default=None, description="Number of employees")
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping of IRIS+ metric ID to reported value",
    )
    sdg_claims: list[int] = Field(
        default_factory=list,
        description="SDG goals the company claims alignment with",
    )
    impact_targets: list[ImpactTarget] = Field(
        default_factory=list,
        description="Structured impact targets for metric tracking",
    )
    reporting_period: str = Field(default="", description="Reporting period (e.g. 'FY2025', 'Q1 2026')")
    exclusion_flags: list[str] = Field(
        default_factory=list,
        description="Norms-based exclusion flags (e.g. 'fossil_fuel', 'controversial_weapons')",
    )
    metric_history: list[MetricValue] = Field(
        default_factory=list,
        description="Time-series metric values for progress tracking across periods",
    )
    beneficiary_feedback: BeneficiaryFeedback | None = Field(
        default=None,
        description="Structured beneficiary feedback data (satisfaction, NPS, qualitative themes)",
    )
    audit_trail: list[AuditTrailEntry] = Field(
        default_factory=list,
        description="Chronological log of metric changes and verification events",
    )


class DimensionScore(BaseModel):
    """Score for a single dimension of impact."""

    dimension: str
    score: float = Field(ge=0, le=5, description="0-5 score")
    metrics_reported: int = 0
    metrics_available: int = 0
    gaps: list[str] = Field(default_factory=list)
    notes: str = ""
    provenance: Literal["evidence-based", "estimated", "partial"] = "estimated"


class FiveDimensionScore(BaseModel):
    """Complete 5-Dimension assessment result."""

    what: DimensionScore
    who: DimensionScore
    how_much: DimensionScore
    contribution: DimensionScore
    risk: DimensionScore
    overall_score: float = Field(ge=0, le=5)
    overall_grade: str = Field(description="A-F letter grade")
    overall_provenance: Literal["evidence-based", "estimated", "partial"] = "estimated"
    impact_theme: str = ""
    recommendations: list[str] = Field(default_factory=list)


class SDGAlignment(BaseModel):
    """SDG alignment result for a single goal."""

    goal: int
    goal_name: str = ""
    score: float = Field(ge=0, le=100, description="0-100 alignment score")
    matched_targets: list[str] = Field(default_factory=list)
    matched_metrics: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    provenance: Literal["evidence-based", "estimated", "partial"] = "estimated"


class Assessment(BaseModel):
    """Complete impact assessment for a company."""

    company: Company
    five_dimensions: FiveDimensionScore | None = None
    sdg_alignments: list[SDGAlignment] = Field(default_factory=list)
    gap_analysis: dict[str, Any] = Field(default_factory=dict)
    impact_claims: list[ImpactClaim] = Field(default_factory=list)
    timestamp: str = ""


class ImpactClaim(BaseModel):
    """An impact claim extracted from a document."""

    text: str = Field(description="The claim text as found in the document")
    source_page: int | None = None
    mapped_metrics: list[str] = Field(
        default_factory=list,
        description="IRIS+ metric IDs this claim maps to",
    )
    mapped_sdg_targets: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, default=0.5)
    category: Literal["outcome", "output", "activity", "intent", "risk"] = "intent"
    evidence_strength: int = Field(
        default=1,
        ge=1,
        le=5,
        description="NESTA-inspired evidence strength (1=narrative only, 2=correlation, 3=causation shown, 4=independent evaluation, 5=RCT/meta-analysis)",
    )
    negation_detected: bool = Field(
        default=False,
        description="True if the claim was found in a negation context",
    )
    entities: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Extracted entities: {'stakeholders': [...], 'geographies': [...], 'outcomes': [...]}",
    )

    @staticmethod
    def calibrated_confidence(
        keyword_hits: int,
        has_metric: bool = False,
        has_quantitative_data: bool = False,
        evidence_level: int = 1,
    ) -> float:
        """Compute a calibrated confidence score replacing the naive linear formula.

        Uses a logarithmic curve for keywords with bonuses for metrics and evidence.
        """
        import math
        base = 0.15 + 0.25 * math.log1p(keyword_hits)
        if has_metric:
            base += 0.15
        if has_quantitative_data:
            base += 0.10
        base += (evidence_level - 1) * 0.05
        return round(min(1.0, max(0.0, base)), 2)
