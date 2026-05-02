"""Reusable client-type template library (roadmap-v4 Track 1.6).

Hand-curated presets for each client type (fund, corporate CSR, foundation,
nonprofit, social enterprise) that a consultant can spin up in a single call
without picking a bundle by hand. Each preset includes:

* the default bundle to launch with,
* the deliverables the client type typically expects,
* the checklist phases that apply.

Consultants can override any of these fields when they instantiate an
engagement — this is a starting point, not a cage.
"""

from __future__ import annotations

from openharness.impact.engagements.models import TemplateLibraryEntry


CLIENT_TEMPLATE_LIBRARY: dict[str, TemplateLibraryEntry] = {
    "fund_impact_launch": TemplateLibraryEntry(
        template_id="fund_impact_launch",
        client_type="fund",
        title="Fund Impact Launch",
        description=(
            "New impact-labelled fund preparing for first close. Combines "
            "strategy baseline with an LP-facing narrative and SFDR / SDR "
            "positioning."
        ),
        default_bundle="strategy_imm",
        recommended_deliverables=[
            "Fund impact thesis",
            "LP narrative v1",
            "SFDR Article 8/9 positioning memo",
        ],
        default_checklist_phases=[
            "discovery",
            "stakeholder_map",
            "toc_workshop",
            "kpi_design",
            "reporting",
        ],
        guidance=(
            "Run the strategy bundle first, then layer the regulatory bundle "
            "once the fund vehicle is chosen."
        ),
    ),
    "fund_annual_cycle": TemplateLibraryEntry(
        template_id="fund_annual_cycle",
        client_type="fund",
        title="Fund Annual Impact Cycle",
        description=(
            "Full annual cycle for an established fund: portfolio data "
            "collection, LP DDQ responses, annual impact report, and a "
            "3-pillar verification handoff."
        ),
        default_bundle="annual_impact_report",
        recommended_deliverables=[
            "Annual impact report",
            "LP DDQ responses",
            "Portfolio rollup",
            "Assurance handoff pack",
        ],
        default_checklist_phases=["data_request", "reporting"],
        guidance=(
            "Pair this template with the verification_3pillar bundle if the "
            "fund has BlueMark / DNV on retainer."
        ),
    ),
    "corporate_esg_baseline": TemplateLibraryEntry(
        template_id="corporate_esg_baseline",
        client_type="corporate_csr",
        title="Corporate ESG Baseline",
        description=(
            "CSRD / ESRS / ISSB materiality scan with double-materiality "
            "workshop and an audit-ready evidence pack."
        ),
        default_bundle="esg_baseline",
        recommended_deliverables=[
            "Materiality matrix",
            "ESG baseline report",
            "Gap-closure roadmap",
        ],
        default_checklist_phases=["discovery", "data_request", "reporting"],
        guidance=(
            "Lead with double-materiality; reuse the outputs to seed an "
            "Annual Impact Report template next cycle."
        ),
    ),
    "foundation_grantee_portfolio": TemplateLibraryEntry(
        template_id="foundation_grantee_portfolio",
        client_type="foundation",
        title="Foundation Grantee Portfolio Review",
        description=(
            "Evaluate a portfolio of grantees against a shared theory of "
            "change with Lean Data beneficiary voice."
        ),
        default_bundle="stakeholder_voice",
        recommended_deliverables=[
            "Grantee scorecard",
            "Beneficiary voice report",
            "Learning loop write-up",
        ],
        default_checklist_phases=[
            "discovery",
            "stakeholder_map",
            "data_request",
            "reporting",
            "training",
        ],
        guidance=(
            "Foundations often care about grantee capacity building — keep "
            "the training phase enabled by default."
        ),
    ),
    "nonprofit_impact_report": TemplateLibraryEntry(
        template_id="nonprofit_impact_report",
        client_type="nonprofit",
        title="Nonprofit Annual Impact Report",
        description=(
            "Annual report for a nonprofit with a clear theory of change and "
            "mixed funder audiences."
        ),
        default_bundle="annual_impact_report",
        recommended_deliverables=[
            "Annual impact report",
            "Donor update pack",
            "Case study",
        ],
        default_checklist_phases=["data_request", "reporting"],
        guidance=(
            "Tone should lean public / donor-friendly — add a public report "
            "deliverable if not already present."
        ),
    ),
    "social_enterprise_dd": TemplateLibraryEntry(
        template_id="social_enterprise_dd",
        client_type="social_enterprise",
        title="Social Enterprise Investment Readiness",
        description=(
            "DD-Mid plus stakeholder voice: what an early-stage social "
            "enterprise needs to land a growth round."
        ),
        default_bundle="dd_mid",
        recommended_deliverables=[
            "DD-Mid memo",
            "KPI term-sheet annex",
            "Beneficiary voice summary",
        ],
        default_checklist_phases=[
            "discovery",
            "data_request",
            "stakeholder_map",
            "toc_workshop",
            "kpi_design",
            "reporting",
        ],
        guidance=(
            "Pair with capacity_training for founder-facing IMM coaching "
            "once the DD closes."
        ),
    ),
}


def get_client_template(template_id: str) -> TemplateLibraryEntry:
    """Look up a template by ID, raising ``KeyError`` if unknown."""
    try:
        return CLIENT_TEMPLATE_LIBRARY[template_id]
    except KeyError as exc:
        known = ", ".join(sorted(CLIENT_TEMPLATE_LIBRARY))
        raise KeyError(
            f"Unknown client template {template_id!r}. Known templates: {known}"
        ) from exc


__all__ = ["CLIENT_TEMPLATE_LIBRARY", "get_client_template"]
