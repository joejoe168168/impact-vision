"""TISFD (beta) — Taskforce on Inequality & Social-related Financial Disclosures.

The TISFD launched in late 2024 (CalPERS, PRI, Manulife, AXA, ING, Generation
IM, unions, NGOs) and released a **beta draft framework** for consultation
(open to 31 July 2026, final framework due 2027). It is structured like
TCFD/TNFD — **Governance / Strategy / Risk & Impact Management / Metrics &
Targets** — and covers the **financial materiality and impact materiality** of
people-related issues: pay, labour conditions, freedom of association,
community impacts, human rights, and inequality. It is designed to be
ISSB / GRI / ESRS compatible.

This module provides a **forward-looking readiness self-assessment** behind an
explicit *beta* label so funds can pilot early without overclaiming. The
disclosure set will be updated when the final framework is published.

Reference: TISFD beta framework (2025 consultation draft).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TISFDPillar = Literal["governance", "strategy", "risk_impact_management", "metrics_targets"]

FRAMEWORK_STATUS = "beta (2025 consultation draft; final due 2027)"


class TISFDDisclosure(BaseModel):
    code: str
    pillar: TISFDPillar
    title: str
    description: str
    detection_keywords: list[str] = Field(default_factory=list)
    gri_cross_refs: list[str] = Field(default_factory=list)
    esrs_cross_refs: list[str] = Field(default_factory=list)


# Beta recommended-disclosure set (14), modelled on the TCFD/TNFD four-pillar
# architecture and TISFD's inequality + social-materiality scope.
TISFD_DISCLOSURES: list[TISFDDisclosure] = [
    # Governance
    TISFDDisclosure(code="G.A", pillar="governance",
        title="Board oversight of social & inequality issues",
        description="Board oversight of people-related and inequality impacts, dependencies, risks and opportunities.",
        detection_keywords=["board oversight", "board committee", "social governance", "human rights committee"],
        gri_cross_refs=["GRI 2-9", "GRI 2-12"], esrs_cross_refs=["ESRS 2 GOV-1"]),
    TISFDDisclosure(code="G.B", pillar="governance",
        title="Management role & stakeholder engagement",
        description="Management's role and engagement with affected stakeholders and rights-holders (incl. workers, communities).",
        detection_keywords=["stakeholder engagement", "affected stakeholders", "rights-holders", "worker voice", "community consultation"],
        gri_cross_refs=["GRI 2-29"], esrs_cross_refs=["ESRS 2 SBM-2"]),
    # Strategy
    TISFDDisclosure(code="S.A", pillar="strategy",
        title="Material social & inequality issues",
        description="Material people-related impacts and dependencies identified over short, medium and long term.",
        detection_keywords=["material social", "inequality", "social impact", "human rights impact", "double materiality"],
        gri_cross_refs=["GRI 3-1", "GRI 3-2"], esrs_cross_refs=["ESRS 2 IRO-1"]),
    TISFDDisclosure(code="S.B", pillar="strategy",
        title="Effects on business model & value chain",
        description="Effects of material social issues on business model, value chain, strategy and financial planning.",
        detection_keywords=["value chain", "business model", "supply chain workers", "financial planning"],
        gri_cross_refs=["GRI 2-6"], esrs_cross_refs=["ESRS 2 SBM-3"]),
    TISFDDisclosure(code="S.C", pillar="strategy",
        title="Inequality resilience & just transition",
        description="Resilience of the strategy to social/inequality scenarios, including a just transition.",
        detection_keywords=["just transition", "social resilience", "scenario", "distributional"],
        esrs_cross_refs=["ESRS S1-4"]),
    # Risk & Impact Management
    TISFDDisclosure(code="R.A", pillar="risk_impact_management",
        title="Identify & assess social impacts",
        description="Processes to identify and assess actual and potential adverse social impacts on people (incl. value chain).",
        detection_keywords=["human rights due diligence", "impact assessment", "salient issues", "saliency", "risk assessment"],
        gri_cross_refs=["GRI 2-25"], esrs_cross_refs=["ESRS S1", "ESRS S2"]),
    TISFDDisclosure(code="R.B", pillar="risk_impact_management",
        title="Manage, prevent, mitigate & remediate",
        description="Processes to prevent, mitigate and remediate adverse social impacts; access to remedy.",
        detection_keywords=["grievance", "remediation", "remedy", "mitigation", "corrective action"],
        gri_cross_refs=["GRI 2-26"], esrs_cross_refs=["ESRS S1-3"]),
    TISFDDisclosure(code="R.C", pillar="risk_impact_management",
        title="Integration into enterprise risk",
        description="How social/inequality processes are integrated into overall enterprise risk management.",
        detection_keywords=["enterprise risk", "integrated risk", "erm"],
        esrs_cross_refs=["ESRS 2 IRO-1"]),
    # Metrics & Targets
    TISFDDisclosure(code="M.A", pillar="metrics_targets",
        title="Pay & wage metrics",
        description="Metrics on pay equity, living wage, and wage gaps across the workforce and value chain.",
        detection_keywords=["living wage", "pay gap", "gender pay", "pay equity", "wage"],
        gri_cross_refs=["GRI 405-2"], esrs_cross_refs=["ESRS S1-10", "ESRS S1-16"]),
    TISFDDisclosure(code="M.B", pillar="metrics_targets",
        title="Labour conditions & freedom of association",
        description="Metrics on working conditions, health & safety, working hours, and freedom of association / collective bargaining.",
        detection_keywords=["collective bargaining", "freedom of association", "health and safety", "working hours", "union"],
        gri_cross_refs=["GRI 403", "GRI 407"], esrs_cross_refs=["ESRS S1-8", "ESRS S1-14"]),
    TISFDDisclosure(code="M.C", pillar="metrics_targets",
        title="Diversity, discrimination & inclusion",
        description="Metrics on diversity, non-discrimination, and inclusion across the workforce.",
        detection_keywords=["diversity", "discrimination", "inclusion", "deib", "representation"],
        gri_cross_refs=["GRI 405", "GRI 406"], esrs_cross_refs=["ESRS S1-9", "ESRS S1-17"]),
    TISFDDisclosure(code="M.D", pillar="metrics_targets",
        title="Community & affected-stakeholder impact metrics",
        description="Metrics on impacts to affected communities and consumers/end-users (incl. inequality outcomes).",
        detection_keywords=["community impact", "affected communities", "consumers", "end-users", "beneficiaries"],
        gri_cross_refs=["GRI 413"], esrs_cross_refs=["ESRS S3", "ESRS S4"]),
    TISFDDisclosure(code="M.E", pillar="metrics_targets",
        title="Targets & performance",
        description="Targets used to manage material social/inequality issues and performance against them.",
        detection_keywords=["target", "goal", "commitment", "baseline", "kpi"],
        esrs_cross_refs=["ESRS S1-5"]),
]


class TISFDPillarScore(BaseModel):
    pillar: str
    addressed: int
    total: int
    coverage_pct: float


class TISFDAssessmentResult(BaseModel):
    framework: str = "TISFD"
    status: str = FRAMEWORK_STATUS
    company_name: str = ""
    overall_readiness_pct: float = 0.0
    readiness_level: str = ""
    addressed_codes: list[str] = Field(default_factory=list)
    missing_codes: list[str] = Field(default_factory=list)
    pillar_scores: list[TISFDPillarScore] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    beta_notice: str = (
        "TISFD is a beta consultation framework (final due 2027). Use this readiness "
        "screen to prepare and pilot — do not represent it as compliance with a final standard."
    )


def get_tisfd_disclosures(pillar: str | None = None) -> list[TISFDDisclosure]:
    if pillar:
        return [d for d in TISFD_DISCLOSURES if d.pillar == pillar]
    return list(TISFD_DISCLOSURES)


def assess_tisfd_readiness(
    description: str = "",
    document_text: str = "",
    reported_metrics: dict[str, str] | None = None,
    company_name: str = "",
) -> TISFDAssessmentResult:
    """Keyword-driven TISFD readiness screen across the 4 pillars."""
    text = f"{description} {document_text}".lower()
    metric_text = " ".join(
        f"{k} {v}" for k, v in (reported_metrics or {}).items()
    ).lower()
    haystack = f"{text} {metric_text}"

    addressed: list[str] = []
    missing: list[str] = []
    pillar_counts: dict[str, dict[str, int]] = {}

    for d in TISFD_DISCLOSURES:
        bucket = pillar_counts.setdefault(d.pillar, {"addressed": 0, "total": 0})
        bucket["total"] += 1
        hit = any(kw in haystack for kw in d.detection_keywords)
        if hit:
            bucket["addressed"] += 1
            addressed.append(d.code)
        else:
            missing.append(d.code)

    total = len(TISFD_DISCLOSURES)
    overall = round(len(addressed) / total * 100, 1) if total else 0.0

    pillar_scores = [
        TISFDPillarScore(
            pillar=p,
            addressed=c["addressed"],
            total=c["total"],
            coverage_pct=round(c["addressed"] / c["total"] * 100, 1) if c["total"] else 0.0,
        )
        for p, c in pillar_counts.items()
    ]

    if overall >= 70:
        level = "Advanced (pilot-ready)"
    elif overall >= 40:
        level = "Developing"
    else:
        level = "Early"

    recs: list[str] = []
    for ps in pillar_scores:
        if ps.coverage_pct < 50:
            recs.append(
                f"Strengthen TISFD {ps.pillar.replace('_', ' ').title()} pillar "
                f"({ps.coverage_pct}%) — it is the weakest readiness area."
            )
    if "M.A" in missing:
        recs.append("Add pay-equity / living-wage metrics (TISFD M.A; maps to ESRS S1-16, GRI 405-2).")
    if "R.A" in missing:
        recs.append("Document a human-rights/social due-diligence process (TISFD R.A) — see the hrdd_assess tool.")
    if not recs:
        recs.append("Strong TISFD readiness — formalise targets (M.E) and pilot disclosure ahead of the 2027 final framework.")

    return TISFDAssessmentResult(
        company_name=company_name,
        overall_readiness_pct=overall,
        readiness_level=level,
        addressed_codes=addressed,
        missing_codes=missing,
        pillar_scores=pillar_scores,
        recommendations=recs,
    )


__all__ = [
    "TISFDPillar",
    "FRAMEWORK_STATUS",
    "TISFDDisclosure",
    "TISFD_DISCLOSURES",
    "TISFDPillarScore",
    "TISFDAssessmentResult",
    "get_tisfd_disclosures",
    "assess_tisfd_readiness",
]
