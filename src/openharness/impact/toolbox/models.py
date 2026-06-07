"""Data contracts for the ESG toolbox integration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


ToolboxCategory = Literal["disclosure", "rating", "export", "supplier", "carbon"]
SourceType = Literal["official", "secondary", "methodology", "legislation", "guidance"]


class SourceRecord(BaseModel):
    """A source used to describe or assess a toolbox module."""

    title: str
    url: str
    source_type: SourceType = "secondary"
    publisher: str = ""
    as_of: str = ""
    notes: str = ""


class RequirementItem(BaseModel):
    """One normalized requirement, topic, criterion, or evidence need."""

    id: str
    title: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    evidence_examples: list[str] = Field(default_factory=list)
    framework_refs: list[str] = Field(default_factory=list)

    @field_validator("keywords", "evidence_examples", "framework_refs")
    @classmethod
    def clean_text_list(cls, values: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value).strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                out.append(cleaned)
        return out


class AssessmentQuestion(BaseModel):
    """A user-facing checklist question derived from a requirement."""

    id: str
    question: str
    evidence_examples: list[str] = Field(default_factory=list)
    requirement_id: str = ""


class CalculatorMethod(BaseModel):
    """Minimal representation of a calculator-style method."""

    id: str
    name: str
    formula: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    source_url: str = ""


class ToolboxSourceIndexRecord(BaseModel):
    """One normalized record extracted from an ohESG page dataset."""

    record_id: str
    title: str
    summary: str = ""
    url: str = ""
    record_type: str = ""
    category: str = ""
    keywords: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, values: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value).strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                out.append(cleaned)
        return out


class ToolboxSourceProfile(BaseModel):
    """Scraped ohESG source profile for one toolbox module."""

    tool_id: str
    url: str
    source_title: str = ""
    source_description: str = ""
    source_tags: list[str] = Field(default_factory=list)
    page_title: str = ""
    meta_description: str = ""
    headings: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    embedded_data_keys: list[str] = Field(default_factory=list)
    embedded_data_summary: dict[str, object] = Field(default_factory=dict)
    as_of: str = ""

    @field_validator("source_tags", "headings", "links", "keywords", "embedded_data_keys")
    @classmethod
    def clean_source_list(cls, values: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value).strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                out.append(cleaned)
        return out


class ToolboxToolSpec(BaseModel):
    """Normalized spec for one ohESG toolbox item."""

    tool_id: str
    title: str
    description: str
    url: str
    source_title: str = ""
    source_description: str = ""
    source_tags: list[str] = Field(default_factory=list)
    categories: list[ToolboxCategory]
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    supported_actions: list[str] = Field(default_factory=lambda: ["get", "checklist", "assess"])
    requirements: list[RequirementItem] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    methods: list[CalculatorMethod] = Field(default_factory=list)
    source_index: list[ToolboxSourceIndexRecord] = Field(default_factory=list)
    source_profile: ToolboxSourceProfile | None = None
    as_of: str = "2026-06-06"

    @field_validator("tool_id")
    @classmethod
    def normalize_tool_id(cls, value: str) -> str:
        cleaned = value.strip().lower().replace("_", "-")
        if not cleaned:
            raise ValueError("tool_id is required")
        return cleaned

    @field_validator("source_tags", "tags", "aliases", "sectors", "jurisdictions", "supported_actions")
    @classmethod
    def dedupe_text_list(cls, values: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value).strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                out.append(cleaned)
        return out


class ToolboxAssessmentResult(BaseModel):
    """Deterministic readiness result for a toolbox assessment."""

    tool_id: str
    title: str
    score_pct: int
    matched_requirement_ids: list[str] = Field(default_factory=list)
    gap_requirement_ids: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    as_of: str = "2026-06-06"
