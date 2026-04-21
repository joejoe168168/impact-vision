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

from typing import Literal

from pydantic import BaseModel, Field


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


__all__ = [
    "Governance",
    "StrategyItem",
    "RiskItem",
    "MetricTarget",
    "IFRSS1Pack",
    "IFRSS2Pack",
    "ISSBPack",
    "build_issb_pack",
]
