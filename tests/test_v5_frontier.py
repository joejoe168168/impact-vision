"""Tests for v5 frontier modules: QALY quantifier, HRDD, TISFD, target setter,
climate scenarios, AI governance, investee portal, and report D-track UX."""

from __future__ import annotations

import asyncio

from openharness.tools.base import ToolExecutionContext


def _ctx() -> ToolExecutionContext:
    from pathlib import Path
    return ToolExecutionContext(cwd=Path.cwd())


# --------------------------------------------------------------------------- B2
def test_impact_quantifier_welfare_and_rollup() -> None:
    from openharness.impact.impact_quantifier import (
        ImpactQuantifierInput, quantify_welfare, rollup_welfare,
    )

    r = quantify_welfare(ImpactQuantifierInput(
        label="Solar", theme="clean_energy", geography="low_income",
        breadth=10000, depth=0.6, duration_years=3, counterfactual=0.2, invested_usd=2_000_000,
    ))
    assert r.qalys > 0
    assert r.lives_improved == round(10000 * 0.6 * 0.8, 1)
    assert r.cost_per_qaly_usd is not None
    assert r.monetised_welfare_usd > 0

    roll = rollup_welfare([
        ImpactQuantifierInput(theme="health", geography="ldc", breadth=5000, depth=0.5),
        ImpactQuantifierInput(theme="financial_inclusion", geography="low_income", breadth=20000, depth=0.4),
    ])
    assert roll.total_qalys > 0
    assert len(roll.holdings) == 2
    assert roll.by_theme_qalys


def test_impact_quantifier_tool() -> None:
    from openharness.tools.impact.impact_quantifier_tool import ImpactQuantifierTool

    tool = ImpactQuantifierTool()
    res = asyncio.run(tool.execute(
        {"action": "quantify", "intervention": {"theme": "health", "geography": "ldc", "breadth": 1000, "depth": 0.5}},
        _ctx(),
    ))
    assert not res.is_error
    assert res.metadata["qalys"] > 0


# --------------------------------------------------------------------------- A3
def test_hrdd_gross_risk_ranks_first_and_csddd_band() -> None:
    from openharness.impact.hrdd import (
        GrievanceMechanism, HRDDInput, SalientIssue, assess_hrdd, seed_salient_issues_from_text,
    )

    seeded = seed_salient_issues_from_text("forced labour in tier-2 suppliers and excessive overtime")
    assert any(i.category == "forced_labour" for i in seeded)

    res = assess_hrdd(HRDDInput(
        company_name="Textile Co",
        salient_issues=[
            SalientIssue(name="Forced labour", category="forced_labour",
                         value_chain_tier="tier_2plus_suppliers", severity="critical", likelihood="medium"),
            SalientIssue(name="Living wage", category="living_wage",
                         value_chain_tier="tier_1_suppliers", severity="high", likelihood="high"),
        ],
        grievance=GrievanceMechanism(exists=True, anonymous_channel=True, tracks_to_remediation=True),
        has_rbc_policy=True, has_impact_identification=True, has_mitigation_plan=True,
    ))
    assert res.salient_issues_ranked[0].category == "forced_labour"
    assert res.oecd_coverage_pct > 0
    assert res.csddd_readiness
    assert res.overall_maturity in ("Initial", "Developing", "Established")


def test_hrdd_tool() -> None:
    from openharness.tools.impact.hrdd_tool import HRDDTool

    tool = HRDDTool()
    res = asyncio.run(tool.execute(
        {"action": "seed_from_text", "document_text": "child labour risk reported in cocoa supply chain"},
        _ctx(),
    ))
    assert not res.is_error
    assert res.metadata["count"] >= 1


# --------------------------------------------------------------------------- B4
def test_tisfd_readiness_four_pillars() -> None:
    from openharness.impact.frameworks.tisfd import assess_tisfd_readiness, get_tisfd_disclosures

    assert len(get_tisfd_disclosures()) == 13
    t = assess_tisfd_readiness(
        description="We track living wage and gender pay gap, run a grievance mechanism, "
                    "and engage affected communities and unions.",
        reported_metrics={"living_wage_coverage": "92%"},
    )
    assert t.overall_readiness_pct > 0
    assert t.status.startswith("beta")
    assert len(t.pillar_scores) == 4
    assert t.beta_notice


def test_tisfd_framework_tool_mode() -> None:
    from openharness.tools.impact.framework_tool import FrameworkTool

    tool = FrameworkTool()
    res = asyncio.run(tool.execute({"framework": "tisfd", "action": "list"}, _ctx()))
    assert not res.is_error
    assert "TISFD" in res.output


# --------------------------------------------------------------------------- B5
def test_target_setter_ranges_and_trajectory() -> None:
    from openharness.impact.impact_target_setter import TargetSetterInput, set_impact_targets

    ts = set_impact_targets(TargetSetterInput(
        theme="financial_inclusion", geography="low_income", capital_usd=10_000_000,
        time_horizon_years=5, ambition="base",
    ))
    assert ts.targets
    first = ts.targets[0]
    assert first.conservative < first.base < first.stretch
    assert len(first.annual_trajectory) == 5
    assert first.annual_trajectory[-1] >= first.annual_trajectory[0]
    assert ts.sdg_focus


def test_decision_workflow_set_targets_action() -> None:
    from openharness.tools.impact.decision_workflow_tool import DecisionWorkflowTool

    tool = DecisionWorkflowTool()
    res = asyncio.run(tool.execute(
        {"action": "set_targets", "target_theme": "clean_energy", "geography": "ldc",
         "target_capital_usd": 5_000_000, "target_horizon_years": 4},
        _ctx(),
    ))
    assert not res.is_error
    assert res.metadata["targets"]


# --------------------------------------------------------------------------- E1
def test_climate_scenarios_exposure() -> None:
    from openharness.impact.climate_scenario import (
        ClimateScenarioInput, PortfolioHolding, assess_climate_scenarios,
    )

    res = assess_climate_scenarios(ClimateScenarioInput(holdings=[
        PortfolioHolding(name="OilCo", sector="oil_gas", value_usd=5_000_000),
        PortfolioHolding(name="SolarCo", sector="clean_energy", value_usd=3_000_000),
        PortfolioHolding(name="FarmCo", sector="agriculture", value_usd=2_000_000),
    ]))
    assert res.total_value_usd == 10_000_000
    assert len(res.scenario_exposures) == 7
    assert res.headline_scenario
    assert res.top_exposed_holdings
    # OilCo has the highest transition sensitivity of the three.
    assert any(h.name == "OilCo" for h in res.top_exposed_holdings[:2])


def test_climate_scenario_tool() -> None:
    from openharness.tools.impact.climate_scenario_tool import ClimateScenarioTool

    tool = ClimateScenarioTool()
    res = asyncio.run(tool.execute(
        {"action": "assess", "holdings": [{"name": "A", "sector": "coal", "value_usd": 1_000_000}]},
        _ctx(),
    ))
    assert not res.is_error
    assert res.metadata["scenario_exposures"]


# --------------------------------------------------------------------------- E2
def test_ai_governance_classification_and_artifact() -> None:
    from openharness.impact.ai_governance import (
        build_ai_governance_artifact, classify_ai_act_risk,
    )
    from openharness.impact.engagements.copilot import CopilotOutput

    assert classify_ai_act_risk(
        "extract impact claims and map to IRIS+",
        human_in_the_loop=True, discloses_ai_use=True, keeps_records=True,
    ).risk_tier == "limited"
    assert classify_ai_act_risk(
        "creditworthiness scoring for loan approval",
        human_in_the_loop=True, discloses_ai_use=True, keeps_records=True,
    ).risk_tier == "high"

    outputs = [
        CopilotOutput(kind="claim_draft", prompt="p", response="r", model="m1", model_version="v1",
                      prompt_version="pv1", source_refs=["doc:1"], confidence=0.8,
                      reviewer="Analyst", decision="approved"),
        CopilotOutput(kind="claim_draft", prompt="p2", response="r2", model="m1", model_version="v1",
                      prompt_version="pv1", source_refs=[], confidence=0.3, decision="pending"),
    ]
    artifact = build_ai_governance_artifact(subject="DealCo", outputs=outputs)
    assert artifact.total_artifacts == 2
    assert artifact.reviewed_artifacts == 1
    assert 0 < artifact.oversight_coverage_pct <= 100
    assert artifact.ai_act.risk_tier == "limited"


def test_ai_governance_tool() -> None:
    from openharness.tools.impact.ai_governance_tool import AIGovernanceTool

    tool = AIGovernanceTool()
    res = asyncio.run(tool.execute({"action": "model_card"}, _ctx()))
    assert not res.is_error
    assert res.metadata["purpose"]


# --------------------------------------------------------------------------- C2
def test_investee_portal_html() -> None:
    from openharness.impact.investee_portal import (
        build_investee_portal, default_portal_sections, portal_schema,
    )

    secs = default_portal_sections(include_pai=True)
    assert portal_schema(secs)["question_count"] > 5
    doc = build_investee_portal(fund_name="Example Capital", company_name="DealCo", sections=secs)
    assert "<!DOCTYPE html>" in doc
    assert 'id="investee-form"' in doc
    assert "skip-link" in doc          # WCAG skip link
    assert "Why we ask:" in doc        # why-we-need-this feedback loop
    assert "SFDR" in doc               # PAI plain language
    assert "investee_submission.json" in doc


def test_investee_portal_tool_schema() -> None:
    from openharness.tools.impact.investee_portal_tool import InvesteePortalTool

    tool = InvesteePortalTool()
    res = asyncio.run(tool.execute({"action": "schema"}, _ctx()))
    assert not res.is_error
    assert res.metadata["question_count"] > 5


# --------------------------------------------------------------- Track D report
def test_report_audience_tearsheet_uncertainty_dark() -> None:
    from openharness.impact.models import Company
    from openharness.tools.impact.impact_report_tool import _to_html

    company = Company(name="Acme Solar", description="Solar in Kenya", sector="Energy",
                      impact_themes=["Clean Energy"], sdg_claims=[7, 13])
    data = {
        "company": company.model_dump(),
        "generated_at": "2026-05-29T00:00:00+00:00",
        "catalog_version": "IRIS+ 5.3c",
        "five_dimensions": {
            "what": {"dimension": "What", "score": 4.0, "metrics_reported": 3, "metrics_available": 5, "gaps": [], "notes": "", "provenance": "evidence-based"},
            "who": {"dimension": "Who", "score": 2.5, "metrics_reported": 1, "metrics_available": 8, "gaps": ["x"], "notes": "", "provenance": "partial"},
            "how_much": {"dimension": "How Much", "score": 2.0, "metrics_reported": 0, "metrics_available": 6, "gaps": ["y"], "notes": "", "provenance": "estimated"},
            "contribution": {"dimension": "Contribution", "score": 2.5, "metrics_reported": 0, "metrics_available": 5, "gaps": [], "notes": "", "provenance": "estimated"},
            "risk": {"dimension": "Risk", "score": 2.0, "metrics_reported": 0, "metrics_available": 4, "gaps": [], "notes": "", "provenance": "estimated"},
            "overall_score": 2.6, "overall_grade": "C+", "overall_provenance": "partial",
            "impact_theme": "Clean Energy", "recommendations": ["Track more"],
        },
        "sdg_alignments": [
            {"goal": 7, "goal_name": "Energy", "score": 80, "confidence": "High", "matched_metrics": ["OI4112"], "matched_targets": ["7.1"], "provenance": "evidence-based"},
        ],
        "greenwashing": {"overall_score": 22, "sub_scores": {}},
    }

    light = _to_html(data)
    assert 'class="audience-bar"' in light          # D4
    assert 'data-aud="regulator"' in light          # D4
    assert "var MAP =" in light                      # D4 script
    assert 'id="tear-sheet"' in light                # D6
    assert "At a glance" in light                    # D6
    assert 'class="uncertainty"' in light            # D5
    assert "indicative range" in light               # D5
    assert "<body>" in light                         # default light theme

    dark = _to_html({**data, "theme": "dark", "audience": "lp"})
    assert '<body class="theme-dark">' in dark       # D7 dark mode
    assert 'data-aud="lp" aria-pressed="true"' in dark


def test_report_branding_injection() -> None:
    from openharness.impact.branding import inject_branding_css, load_branding

    html = "<html><head><style>x</style></head><body>hi</body></html>"
    branded = inject_branding_css(html, load_branding(raw={"fund_name": "Example", "primary_color": "#0d47a1"}))
    assert "impact-vision-branding" in branded
