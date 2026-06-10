"""Engagement-type bundles (roadmap-v4 §4a).

Productised service catalog: 12 named engagements that map to existing v3
agent tools so a consultant can launch a project without hand-picking 30
tools. Every bundle references:

* The Impact Management Compass step (Tideline taxonomy).
* The v3 agent tools that compose the bundle (so an agent can autowire them
  via the existing registry).
* The default deliverables / checklist phases the bundle expects.

Bundles are **data**, not code — no behaviour lives here so the catalog can
be audited in a single glance. The wiring into the workspace happens in
:class:`openharness.impact.engagements.workspace.EngagementWorkspace`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EngagementBundleType = Literal[
    "strategy_imm",
    "dd_light",
    "dd_mid",
    "dd_full_iwa",
    "esg_baseline",
    "annual_impact_report",
    "lp_ddq",
    "verification_3pillar",
    "exit_vdd",
    "regulatory",
    "stakeholder_voice",
    "capacity_training",
]

CompassStep = Literal[
    "strategy",
    "system_design",
    "due_diligence",
    "monitoring_reporting",
    "verification",
    "exit",
    "regulatory",
    "cross_cutting",
]


class EngagementBundle(BaseModel):
    """Productised engagement template (roadmap-v4 §4a row)."""

    bundle_id: EngagementBundleType
    name: str
    compass_step: CompassStep
    description: str
    bundled_tools: list[str] = Field(default_factory=list)
    default_deliverables: list[str] = Field(default_factory=list)
    default_checklist_phases: list[str] = Field(default_factory=list)
    default_sla_days: int = 30
    target_audiences: list[str] = Field(default_factory=list)
    """Intended consumers (founder / IC / LP / board / public / regulator / verifier)."""


def _bundle(**kwargs) -> EngagementBundle:  # small helper to keep the catalog tidy
    return EngagementBundle(**kwargs)


_DISCOVERY_PHASES = [
    "discovery",
    "data_request",
    "stakeholder_map",
    "toc_workshop",
    "kpi_design",
    "reporting",
    "training",
]


ENGAGEMENT_BUNDLES: dict[EngagementBundleType, EngagementBundle] = {
    "strategy_imm": _bundle(
        bundle_id="strategy_imm",
        name="Impact Strategy / IMM Baseline",
        compass_step="strategy",
        description=(
            "Establish fund/impact thesis, theory of change, governance, and "
            "headline KPIs so downstream engagements all plug into a shared "
            "strategic frame."
        ),
        bundled_tools=[
            "pitch_deck_analyze",
            "sdg_mapper",
            "five_dimension_assess",
            "metric_recommender",
            "narrative_tool",
        ],
        default_deliverables=[
            "Strategy memo",
            "Theory of Change v1",
            "KPI framework",
            "Workshop pack",
        ],
        default_checklist_phases=_DISCOVERY_PHASES,
        default_sla_days=45,
        target_audiences=["founder", "ic", "board"],
    ),
    "dd_light": _bundle(
        bundle_id="dd_light",
        name="Impact DD — Light",
        compass_step="due_diligence",
        description=(
            "Three-day impact due diligence pass: exclusion screen, pitch-deck "
            "ingest, DD checklist, greenwashing scan. Closest to Impact "
            "Institute 'DD-Light'."
        ),
        bundled_tools=[
            "pitch_deck_analyze",
            "dd_checklist",
            "exclusion_screening",
            "greenwashing",
        ],
        default_deliverables=["DD-Light memo", "Red-flag summary"],
        default_checklist_phases=["discovery", "data_request", "reporting"],
        default_sla_days=3,
        target_audiences=["ic"],
    ),
    "dd_mid": _bundle(
        bundle_id="dd_mid",
        name="Impact DD — Mid",
        compass_step="due_diligence",
        description=(
            "DD-Light plus Five-Dimension scoring, SDG alignment, framework "
            "scan, risk/opportunity, and sector benchmarks. Produces a KPI "
            "term-sheet annex."
        ),
        bundled_tools=[
            "pitch_deck_analyze",
            "dd_checklist",
            "five_dimension_assess",
            "sdg_mapper",
            "framework_tool",
            "impact_risk_opportunity",
            "metric_recommender",
            "greenwashing_detect",
        ],
        default_deliverables=[
            "DD-Mid memo",
            "KPI term-sheet annex",
            "Risk/opportunity register",
        ],
        default_checklist_phases=_DISCOVERY_PHASES,
        default_sla_days=14,
        target_audiences=["ic", "board"],
    ),
    "dd_full_iwa": _bundle(
        bundle_id="dd_full_iwa",
        name="Impact DD — Full (IWA / IMM)",
        compass_step="due_diligence",
        description=(
            "Quantified Impact-Weighted Accounts style DD with SROI, causal / "
            "counterfactual analysis, scenario modelling and climate accounting. "
            "Headline output is an Impact Multiple of Money (IMM)."
        ),
        bundled_tools=[
            "pitch_deck_analyze",
            "dd_checklist",
            "five_dimension_assess",
            "sdg_mapper",
            "framework_tool",
            "impact_risk_opportunity",
            "metric_recommender",
            "greenwashing_detect",
            "beneficiary_feedback",
        ],
        default_deliverables=[
            "IMM report",
            "SROI calculations",
            "Scenario model",
            "Climate accounting pack",
        ],
        default_checklist_phases=_DISCOVERY_PHASES,
        default_sla_days=45,
        target_audiences=["ic", "lp", "board"],
    ),
    "esg_baseline": _bundle(
        bundle_id="esg_baseline",
        name="ESG Baseline",
        compass_step="system_design",
        description=(
            "Materiality scan plus CSRD/ESRS, ISSB, SASB, GRI, TCFD coverage, "
            "data-quality assessment, exclusion screening and regulatory gap "
            "check. Produces a materiality matrix."
        ),
        bundled_tools=[
            "framework_tool",
            "data_quality",
            "exclusion_screening",
            "cross_reference",
            "metric_recommender",
        ],
        default_deliverables=["Materiality matrix", "ESG baseline report"],
        default_checklist_phases=["discovery", "data_request", "reporting"],
        default_sla_days=30,
        target_audiences=["board", "regulator"],
    ),
    "annual_impact_report": _bundle(
        bundle_id="annual_impact_report",
        name="Annual Impact Report",
        compass_step="monitoring_reporting",
        description=(
            "Multi-audience annual report built on LP narrative, trend "
            "analysis, monitoring tool and impact report tool."
        ),
        bundled_tools=[
            "impact_report",
            "lp_narrative",
            "narrative_tool",
            "trend_analysis",
            "monitoring",
            "portfolio_tool",
        ],
        default_deliverables=[
            "LP narrative",
            "Public annual report",
            "Portfolio rollup",
        ],
        default_checklist_phases=["data_request", "reporting"],
        default_sla_days=30,
        target_audiences=["lp", "public"],
    ),
    "lp_ddq": _bundle(
        bundle_id="lp_ddq",
        name="LP DDQ Response Pack",
        compass_step="monitoring_reporting",
        description=(
            "ILPA / GIIN / EDCI / SFDR LP-DDQ response constrained to verified "
            "data, with a Q&A workspace the consultant can defend line-by-line."
        ),
        bundled_tools=[
            "lp_ddq_export",
            "lp_narrative",
            "portfolio_query",
            "evidence_review",
        ],
        default_deliverables=["LP DDQ response pack", "Q&A transcript"],
        default_checklist_phases=["data_request", "reporting"],
        default_sla_days=14,
        target_audiences=["lp"],
    ),
    "verification_3pillar": _bundle(
        bundle_id="verification_3pillar",
        name="Impact Verification (BlueMark 3-Pillar)",
        compass_step="verification",
        description=(
            "Mandate + Practice + Reporting verification bundled into a single "
            "assurance pack ready for BlueMark / DNV / KPMG handoff. Implements "
            "roadmap-v4 Track 10 as a read-only engagement wrapper."
        ),
        bundled_tools=[
            "verification_workspace",
            "evidence_review",
            "greenwashing_detect",
            "lp_narrative",
        ],
        default_deliverables=[
            "Mandate verification pack",
            "Practice verification pack",
            "Reporting verification pack",
            "Signed assurance manifest",
        ],
        default_checklist_phases=["data_request", "reporting"],
        default_sla_days=30,
        target_audiences=["verifier", "lp"],
    ),
    "exit_vdd": _bundle(
        bundle_id="exit_vdd",
        name="Impact VDD / Exit Report",
        compass_step="exit",
        description=(
            "OPIM Principle 8 exit-impact assessment with durability risks, "
            "post-exit follow-ups and a residual-impact narrative suitable for "
            "IC approval."
        ),
        bundled_tools=["exit_impact", "lp_narrative", "evidence_review"],
        default_deliverables=["Exit impact report", "Post-exit follow-up plan"],
        default_checklist_phases=["data_request", "reporting"],
        default_sla_days=21,
        target_audiences=["ic", "lp"],
    ),
    "regulatory": _bundle(
        bundle_id="regulatory",
        name="Regulatory Compliance",
        compass_step="regulatory",
        description=(
            "Jurisdiction-aware SFDR / SDR / SEC climate / CSRD-ESRS / ISSB "
            "wizard (roadmap-v4 Track 9). Wave 1 surfaces it as a bundle "
            "pointing at existing framework modules; a full wizard UI lands "
            "in Wave 5."
        ),
        bundled_tools=[
            "framework_tool",
            "cross_reference",
            "data_quality",
            "lp_ddq_export",
        ],
        default_deliverables=[
            "Regulatory gap report",
            "SFDR PAI / Article 8/9 pack",
            "Climate disclosure pack",
        ],
        default_checklist_phases=["discovery", "data_request", "reporting"],
        default_sla_days=30,
        target_audiences=["regulator", "lp"],
    ),
    "stakeholder_voice": _bundle(
        bundle_id="stakeholder_voice",
        name="Stakeholder Voice Study",
        compass_step="cross_cutting",
        description=(
            "Lean Data survey, beneficiary feedback, worker voice, with "
            "persistent stakeholder IDs across rounds (roadmap-v4 Sopact "
            "counter-measure)."
        ),
        bundled_tools=[
            "stakeholder_voice",
            "beneficiary_feedback",
        ],
        default_deliverables=[
            "Stakeholder voice report",
            "Consent log",
            "Feedback quality scorecard",
        ],
        default_checklist_phases=[
            "discovery",
            "stakeholder_map",
            "data_request",
            "reporting",
        ],
        default_sla_days=45,
        target_audiences=["ic", "lp", "public"],
    ),
    "capacity_training": _bundle(
        bundle_id="capacity_training",
        name="Capacity Building / Training",
        compass_step="cross_cutting",
        description=(
            "Workshop pack generator: ToC, KPI design, ESG baseline, data "
            "quality, stakeholder voice, reporting. Closes the investee "
            "coaching loop introduced in v3."
        ),
        bundled_tools=[
            "improvement_advisor",
            "narrative_tool",
            "dd_checklist",
            "evidence_review",
        ],
        default_deliverables=[
            "Training plan",
            "Workshop facilitation pack",
            "Investee coaching cards",
        ],
        default_checklist_phases=["discovery", "training"],
        default_sla_days=30,
        target_audiences=["founder", "board"],
    ),
}


def list_bundles() -> list[EngagementBundle]:
    """Return all catalog entries sorted by compass step then bundle_id."""
    order = {
        "strategy": 0,
        "system_design": 1,
        "due_diligence": 2,
        "monitoring_reporting": 3,
        "verification": 4,
        "exit": 5,
        "regulatory": 6,
        "cross_cutting": 7,
    }
    return sorted(
        ENGAGEMENT_BUNDLES.values(),
        key=lambda b: (order.get(b.compass_step, 99), b.bundle_id),
    )


def get_bundle(bundle_id: str) -> EngagementBundle:
    """Look up one bundle by its ID, raising ``KeyError`` if unknown."""
    try:
        return ENGAGEMENT_BUNDLES[bundle_id]  # type: ignore[index]
    except KeyError as exc:
        known = ", ".join(sorted(ENGAGEMENT_BUNDLES))
        raise KeyError(
            f"Unknown engagement bundle {bundle_id!r}. Known bundles: {known}"
        ) from exc


__all__ = [
    "CompassStep",
    "ENGAGEMENT_BUNDLES",
    "EngagementBundle",
    "EngagementBundleType",
    "get_bundle",
    "list_bundles",
]
