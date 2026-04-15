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


class Company(BaseModel):
    """A company or startup being assessed for impact."""

    name: str
    description: str = ""
    sector: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping of IRIS+ metric ID to reported value",
    )
    sdg_claims: list[int] = Field(
        default_factory=list,
        description="SDG goals the company claims alignment with",
    )


class DimensionScore(BaseModel):
    """Score for a single dimension of impact."""

    dimension: str
    score: float = Field(ge=0, le=5, description="0-5 score")
    metrics_reported: int = 0
    metrics_available: int = 0
    gaps: list[str] = Field(default_factory=list)
    notes: str = ""


class FiveDimensionScore(BaseModel):
    """Complete 5-Dimension assessment result."""

    what: DimensionScore
    who: DimensionScore
    how_much: DimensionScore
    contribution: DimensionScore
    risk: DimensionScore
    overall_score: float = Field(ge=0, le=5)
    overall_grade: str = Field(description="A-F letter grade")
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
