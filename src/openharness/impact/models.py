"""Pydantic models for IRIS+ metrics, SDGs, assessments, and impact claims."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("metric_id")
    @classmethod
    def validate_metric_id(cls, v: str) -> str:
        import re
        v = v.strip().upper()
        if v and not re.match(r"^(PI|OI|OD|FP|PD)\d{4}$", v):
            raise ValueError(f"Invalid IRIS+ metric ID format: {v}")
        return v


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


class MetricRecord(BaseModel):
    """Canonical reviewed metric record for reporting, assurance, and exports.

    ``MetricValue`` remains the lightweight time-series shape used by older
    trend-analysis flows. ``MetricRecord`` is the stricter data contract used
    when a reported value is ready to move through review, LP reporting, or
    assurance workflows.
    """

    metric_id: str = Field(description="IRIS+ metric ID, normalized uppercase")
    value: Any = Field(description="Reported value; must not be empty")
    unit: str = Field(min_length=1, description="Unit or explicit value type, e.g. tCO2e, USD, count, qualitative")
    period: str = Field(min_length=1, description="Reporting period, e.g. FY2025, Q1 2026, current")
    source: str = Field(min_length=1, description="Source reference, filename, URL, system name, or evidence ID")
    owner: str = Field(min_length=1, description="Responsible person, role, investee contact, or system")
    quality_score: int = Field(ge=0, le=100, description="0-100 data-quality score")
    verification_status: Literal[
        "unverified",
        "self_reported",
        "management_verified",
        "third_party_verified",
        "audited",
        "proxy_estimate",
    ] = Field(default="unverified", description="Review or assurance state for this record")
    source_type: Literal[
        "manual_entry",
        "investee_submission",
        "document_extraction",
        "system_import",
        "proxy_estimate",
        "audited_statement",
    ] = Field(default="manual_entry", description="How the record entered the system")
    evidence_refs: list[str] = Field(default_factory=list, description="Evidence IDs, file paths, or URLs")
    notes: str = ""

    @field_validator("metric_id")
    @classmethod
    def validate_metric_id(cls, v: str) -> str:
        import re

        metric_id = (v or "").strip().upper()
        if not re.match(r"^(PI|OI|OD|FP|PD)\d{4}$", metric_id):
            raise ValueError(f"Invalid IRIS+ metric ID format: {v}")
        return metric_id

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Metric value is required")
        if isinstance(v, str) and not v.strip():
            raise ValueError("Metric value must not be empty")
        return v

    @field_validator("unit", "period", "source", "owner")
    @classmethod
    def strip_required_text(cls, v: str) -> str:
        cleaned = " ".join(str(v).split()).strip()
        if not cleaned:
            raise ValueError("Field must not be empty")
        return cleaned

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, refs: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            cleaned = str(ref).strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            out.append(cleaned)
        return out

    @property
    def quality_band(self) -> Literal["low", "moderate", "high"]:
        if self.quality_score >= 80:
            return "high"
        if self.quality_score >= 50:
            return "moderate"
        return "low"

    @property
    def is_verified(self) -> bool:
        return self.verification_status in {
            "management_verified",
            "third_party_verified",
            "audited",
        }


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

    @field_validator("satisfaction_score")
    @classmethod
    def validate_satisfaction(cls, v: float | None) -> float | None:
        if v is not None and (v < 1 or v > 5):
            raise ValueError(f"satisfaction_score must be 1-5, got {v}")
        return v

    @field_validator("nps")
    @classmethod
    def validate_nps(cls, v: float | None) -> float | None:
        if v is not None and (v < -100 or v > 100):
            raise ValueError(f"NPS must be -100 to 100, got {v}")
        return v


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


PIPELINE_STAGES = (
    "sourcing",
    "screening",
    "dd_in_progress",
    "ic_review",
    "invested",
    "monitoring",
    "exited",
    "passed",
)


class StageTransition(BaseModel):
    """Record of a company moving between pipeline stages."""

    from_stage: str = ""
    to_stage: str
    timestamp: str = Field(default="", description="ISO datetime of transition")
    actor: str = Field(default="", description="Who made the decision")
    rationale: str = Field(default="", description="Why the transition was made")
    notes: str = ""


class PipelineEntry(BaseModel):
    """A company's position in the investment pipeline."""

    company_name: str
    pipeline_stage: str = Field(default="sourcing", description="Current pipeline stage")
    assigned_to: str = Field(default="", description="Analyst/partner responsible")
    priority: Literal["high", "medium", "low"] = "medium"
    tags: list[str] = Field(default_factory=list)
    sector: str = ""
    geography: str = ""
    sdg_focus: list[int] = Field(default_factory=list, description="Primary SDG goals")
    investment_size: float | None = Field(default=None, description="Investment amount (USD)")
    created_at: str = ""
    updated_at: str = ""
    transitions: list[StageTransition] = Field(default_factory=list)
    notes: str = ""


class MonitoringSchedule(BaseModel):
    """Monitoring configuration for an invested company."""

    company_name: str
    frequency: Literal["monthly", "quarterly", "semi_annual", "annual"] = "quarterly"
    next_review_date: str = Field(default="", description="ISO date of next review")
    last_review_date: str = Field(default="", description="ISO date of last review")
    alert_thresholds: dict[str, float] = Field(
        default_factory=dict,
        description="Metric ID -> threshold value; alert when deviation exceeds this",
    )
    watch_metrics: list[str] = Field(
        default_factory=list,
        description="Metric IDs to track for this company",
    )
    status: Literal["active", "paused", "completed"] = "active"


class MonitoringAlert(BaseModel):
    """An alert triggered by monitoring threshold breach or schedule event."""

    company_name: str
    alert_type: Literal[
        "metric_deviation", "target_at_risk", "evidence_expired",
        "review_due", "score_change", "risk_increase",
    ]
    severity: Literal["info", "warning", "critical"] = "warning"
    message: str = ""
    metric_id: str = Field(default="", description="Related metric ID if applicable")
    current_value: float | None = None
    threshold_value: float | None = None
    created_at: str = ""
    acknowledged: bool = False


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
    evidence_chain: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Chain: [{claim_text, metric_id, evidence_type, sdg_target, confidence}]",
    )
    scoring_basis: Literal["core_set", "broad_catalog", "estimated"] = "estimated"


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

    def model_post_init(self, __context: Any) -> None:
        """Auto-populate confidence from calibrated formula after model initialization.

        Only overrides confidence when it is still at the default value (0.5),
        preserving any explicitly set confidence.
        """
        if self.confidence != 0.5:
            return  # Respect explicitly set confidence
        has_metric = len(self.mapped_metrics) > 0
        has_quant = any(c.isdigit() for c in self.text)
        # Only calibrate if we have any signal beyond a bare claim
        if has_metric or has_quant or self.evidence_strength > 1:
            self.confidence = self.calibrated_confidence(
                keyword_hits=len(self.mapped_metrics) + len(self.mapped_sdg_targets),
                has_metric=has_metric,
                has_quantitative_data=has_quant,
                evidence_level=self.evidence_strength,
            )

    def recalibrate_confidence(self) -> None:
        """Update confidence using the calibrated formula based on current fields.

        Automatically derives confidence from mapped_metrics, evidence_strength,
        and whether the claim text contains quantitative data.
        """
        import re
        has_metric = len(self.mapped_metrics) > 0
        has_quant = bool(re.search(r"\d+[%,.\d]*\s*(?:people|beneficiar|tCO2|MWh|USD|EUR|households|farmers|clients)?", self.text))
        self.confidence = self.calibrated_confidence(
            keyword_hits=len(self.mapped_metrics) + len(self.mapped_sdg_targets),
            has_metric=has_metric,
            has_quantitative_data=has_quant,
            evidence_level=self.evidence_strength,
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
