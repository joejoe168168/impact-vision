"""TNFD v1 — Taskforce on Nature-related Financial Disclosures.

Implements the *LEAP* approach (Locate, Evaluate, Assess, Prepare) and the
14 TNFD recommended disclosures across Governance, Strategy, Risk &
Impact Management, and Metrics & Targets.

Reference: https://tnfd.global/recommendations-of-the-tnfd/ (v1.0, Sep 2023)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TNFDPillar = Literal["governance", "strategy", "risk_management", "metrics_targets"]


class TNFDDisclosure(BaseModel):
    code: str
    pillar: TNFDPillar
    title: str
    description: str
    iris_cross_refs: list[str] = Field(default_factory=list)


# All 14 recommended disclosures (TNFD v1, mapped to closest IRIS+ proxies
# where they exist; many are governance-only and have no IRIS+ analog).
TNFD_DISCLOSURES: list[TNFDDisclosure] = [
    # Governance
    TNFDDisclosure(code="G.A", pillar="governance",
                   title="Board oversight of nature-related issues",
                   description="Describe board oversight of nature-related dependencies, impacts, risks and opportunities."),
    TNFDDisclosure(code="G.B", pillar="governance",
                   title="Management role in nature-related issues",
                   description="Describe management's role in assessing and managing nature-related dependencies, impacts, risks and opportunities."),
    TNFDDisclosure(code="G.C", pillar="governance",
                   title="Indigenous Peoples & local communities",
                   description="Describe organisation's human rights policies and engagement with affected stakeholders."),
    # Strategy
    TNFDDisclosure(code="S.A", pillar="strategy",
                   title="Material nature-related issues",
                   description="Describe nature-related dependencies, impacts, risks and opportunities identified over short, medium and long term."),
    TNFDDisclosure(code="S.B", pillar="strategy",
                   title="Effects on business model & strategy",
                   description="Describe effects of material nature issues on business model, value chain, strategy and financial planning."),
    TNFDDisclosure(code="S.C", pillar="strategy",
                   title="Resilience & scenario analysis",
                   description="Describe resilience of strategy considering different nature-related scenarios."),
    TNFDDisclosure(code="S.D", pillar="strategy",
                   title="Priority locations",
                   description="Disclose locations of assets / activities meeting TNFD priority-location criteria.",
                   iris_cross_refs=["OI4708"]),
    # Risk & Impact Management
    TNFDDisclosure(code="R.A1", pillar="risk_management",
                   title="Direct operations risk processes",
                   description="Describe processes for identifying, assessing and prioritising nature risks in direct operations."),
    TNFDDisclosure(code="R.A2", pillar="risk_management",
                   title="Upstream / downstream value chain processes",
                   description="Describe processes for identifying nature risks in upstream and downstream value chain."),
    TNFDDisclosure(code="R.B", pillar="risk_management",
                   title="Risk management",
                   description="Describe processes for managing nature-related dependencies, impacts, risks and opportunities."),
    TNFDDisclosure(code="R.C", pillar="risk_management",
                   title="Integration into overall risk",
                   description="Describe how nature processes are integrated into overall risk management."),
    # Metrics & Targets
    TNFDDisclosure(code="M.A", pillar="metrics_targets",
                   title="Metrics for material risks & opportunities",
                   description="Disclose metrics used to assess and manage material nature-related risks and opportunities.",
                   iris_cross_refs=["PI8407", "OI3525"]),
    TNFDDisclosure(code="M.B", pillar="metrics_targets",
                   title="Metrics for impacts & dependencies",
                   description="Disclose metrics used to assess impacts and dependencies on nature.",
                   iris_cross_refs=["PI4060", "OI3525", "OI4708"]),
    TNFDDisclosure(code="M.C", pillar="metrics_targets",
                   title="Targets & performance",
                   description="Describe targets and goals used to manage nature-related issues and performance against them."),
]


class TNFDAssessmentResult(BaseModel):
    company_name: str
    disclosure_count_total: int
    disclosure_count_addressed: int
    coverage_pct: float
    by_pillar: dict[str, dict[str, int]]
    addressed_codes: list[str]
    missing_codes: list[str]
    leap_progress: dict[str, str]
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class TNFDInput(BaseModel):
    """Inputs for a TNFD self-assessment."""
    company_name: str
    addressed_disclosure_codes: list[str] = Field(default_factory=list)
    leap_locate_done: bool = False
    leap_evaluate_done: bool = False
    leap_assess_done: bool = False
    leap_prepare_done: bool = False
    sector: str = ""


def assess_tnfd(input_data: TNFDInput) -> TNFDAssessmentResult:
    addressed = set(input_data.addressed_disclosure_codes)
    by_pillar: dict[str, dict[str, int]] = {}
    addressed_codes: list[str] = []
    missing_codes: list[str] = []

    for d in TNFD_DISCLOSURES:
        bucket = by_pillar.setdefault(d.pillar, {"total": 0, "addressed": 0})
        bucket["total"] += 1
        if d.code in addressed:
            bucket["addressed"] += 1
            addressed_codes.append(d.code)
        else:
            missing_codes.append(d.code)

    total = len(TNFD_DISCLOSURES)
    coverage = (len(addressed_codes) / total * 100) if total else 0.0

    leap = {
        "Locate": "complete" if input_data.leap_locate_done else "todo",
        "Evaluate": "complete" if input_data.leap_evaluate_done else "todo",
        "Assess": "complete" if input_data.leap_assess_done else "todo",
        "Prepare": "complete" if input_data.leap_prepare_done else "todo",
    }

    findings: list[str] = []
    recs: list[str] = []
    if coverage < 50:
        findings.append(f"TNFD coverage {coverage:.0f}% — below recommended baseline (50%) for first-year reporters.")
        recs.append("Address governance disclosures (G.A, G.B) first; they're the lowest-effort entry point.")
    if not input_data.leap_locate_done:
        recs.append("Complete LEAP-Locate using ENCORE / WWF Risk Filter before next reporting cycle.")
    if "S.D" not in addressed:
        recs.append("Disclose priority locations (S.D) — required for v1 'core' alignment.")

    return TNFDAssessmentResult(
        company_name=input_data.company_name,
        disclosure_count_total=total,
        disclosure_count_addressed=len(addressed_codes),
        coverage_pct=round(coverage, 1),
        by_pillar=by_pillar,
        addressed_codes=addressed_codes,
        missing_codes=missing_codes,
        leap_progress=leap,
        findings=findings,
        recommendations=recs,
    )
