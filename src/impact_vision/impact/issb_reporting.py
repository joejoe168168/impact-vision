"""ISSB IFRS S1 / S2 reporting pack (Phase 17).

Assembles the machine-readable disclosure pack required by:

* **IFRS S1** — General sustainability-related financial disclosures.
* **IFRS S2** — Climate-related disclosures (Scope 1/2/3, transition
  plan, physical + transition risks, targets).

The pack mirrors the four IFRS S1 pillars (Governance, Strategy, Risk
Management, Metrics & Targets) plus a dedicated climate section for
S2. Downstream tools can serialise it to JSON-LD, XBRL taxonomy tags or
the structured inline disclosure formats used by most filers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
import yaml
from impact_vision.impact._paths import data_path as bundled_data_path


S2RiskType = Literal["transition", "physical-acute", "physical-chronic"]


class Governance(BaseModel):
    oversight_body: str
    meeting_frequency: str = "quarterly"
    reporting_line: str = ""
    management_role: str = ""


class StrategyItem(BaseModel):
    topic: str
    time_horizon: Literal["short", "medium", "long"]
    description: str
    financial_effect: str = ""


class RiskItem(BaseModel):
    name: str
    s2_type: S2RiskType | None = None
    likelihood: float = Field(ge=0, le=1, default=0.5)
    magnitude_usd: float | None = None
    mitigation: str = ""


class MetricTarget(BaseModel):
    metric: str
    unit: str
    baseline_value: float
    baseline_year: int
    target_value: float
    target_year: int
    scope: Literal["scope1", "scope2", "scope3", "other"] = "other"
    methodology: str = ""


class IFRSS1Pack(BaseModel):
    entity: str
    reporting_period: str
    governance: Governance
    strategy: list[StrategyItem] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    metrics_targets: list[MetricTarget] = Field(default_factory=list)


class IFRSS2Pack(BaseModel):
    entity: str
    reporting_period: str
    scope1_tco2e: float = 0.0
    scope2_tco2e: float = 0.0
    scope3_tco2e: float = 0.0
    transition_plan_summary: str = ""
    physical_risks: list[RiskItem] = Field(default_factory=list)
    transition_risks: list[RiskItem] = Field(default_factory=list)
    science_based_target: MetricTarget | None = None


class IFRSS2Amendment(BaseModel):
    """One issued IFRS S2 targeted amendment and its implementation status."""

    amendment_id: str
    title: str
    summary: str
    status: Literal["proposed", "issued", "effective"] = "issued"
    effective_date: str
    early_application: bool = False
    source_url: str


class ISSBPack(BaseModel):
    """Combined S1 + S2 pack."""
    s1: IFRSS1Pack
    s2: IFRSS2Pack


def build_issb_pack(
    *,
    s1: IFRSS1Pack,
    s2: IFRSS2Pack,
) -> ISSBPack:
    return ISSBPack(s1=s1, s2=s2)


def load_s2_amendments(path: str | Path | None = None) -> list[IFRSS2Amendment]:
    """Load the maintained IFRS S2 targeted-amendment register.

    The register is deliberately separate from the S2 disclosure model: a
    filing pack can remain S2-2023 while a jurisdiction transitions to the
    amendments effective from 2027.
    """
    data_path = (
        Path(path)
        if path
        else bundled_data_path("issb_s2_amendments.yaml")
    )
    payload = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    rows = payload.get("amendments", [])
    return [IFRSS2Amendment.model_validate(row) for row in rows]


def s2_amendment_summary(path: str | Path | None = None) -> dict:
    """Return amendments plus the register-level effective-date metadata."""
    data_path = (
        Path(path)
        if path
        else bundled_data_path("issb_s2_amendments.yaml")
    )
    payload = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    return {
        "framework": payload.get("framework", "IFRS S2"),
        "as_of": payload.get("as_of", ""),
        "effective_date": payload.get("effective_date", "2027-01-01"),
        "early_application": bool(payload.get("early_application", False)),
        "source_url": payload.get("source_url", ""),
        "source_note": payload.get("source_note", ""),
        "amendments": [row.model_dump(mode="json") for row in load_s2_amendments(data_path)],
    }


__all__ = [
    "Governance",
    "StrategyItem",
    "RiskItem",
    "MetricTarget",
    "IFRSS1Pack",
    "IFRSS2Pack",
    "IFRSS2Amendment",
    "ISSBPack",
    "build_issb_pack",
    "load_s2_amendments",
    "s2_amendment_summary",
]
