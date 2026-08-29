"""Regression coverage for thin v6 social/nature modules and scoring bugs."""

from __future__ import annotations

import asyncio
from pathlib import Path

from openharness.impact.carbon_credit_integrity import (
    CCP_APPROVED_METHODOLOGIES,
    CarbonCredit,
    normalize_program,
    screen_credits,
)
from openharness.impact.ecosystem_services import (
    BIODIVERSITY_CREDIT_PRINCIPLES,
    screen_biodiversity_credit,
)
from openharness.impact.frameworks.sbtn import nature_target_ranges, sbtn_readiness
from openharness.impact.fx import convert
from openharness.impact.greenwashing import assess_greenwashing
from openharness.impact.just_transition import JT_METRICS, assess_just_transition
from openharness.impact.living_wage import (
    list_geographies,
    living_wage_gap,
    resolve_geography,
)
from openharness.impact.models import Company, MetricRecord
from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.pitch_deck_analyze_tool import (
    PitchDeckAnalyzeInput,
    PitchDeckAnalyzeTool,
    _extract_reported_metrics,
)


def _record(**updates) -> MetricRecord:
    payload = {
        "metric_id": "OI5049",
        "value": "yes",
        "unit": "qualitative",
        "period": "FY2025",
        "source": "policy",
        "owner": "CHRO",
        "quality_score": 70,
        "notes": "",
    }
    payload.update(updates)
    return MetricRecord.model_validate(payload)


def test_just_transition_metrics_are_named_and_grouped() -> None:
    assert len(JT_METRICS) == 19
    assert all(not m["metric"].startswith("Just Transition practice metric") for m in JT_METRICS)
    groups = {m["stakeholder_group"] for m in JT_METRICS}
    pillars = {m["pillar"] for m in JT_METRICS}
    assert groups == {"own_workforce", "communities", "value_chain"}
    assert pillars == {"governance", "strategy", "risk_impact", "metrics_targets"}
    assert all(m["keywords"] for m in JT_METRICS)


def test_just_transition_matches_keywords_not_fake_ids() -> None:
    company = Company(
        name="Transition Co",
        description=(
            "Board accountability for just transition; collective bargaining covers "
            "the workforce; living wage commitment; community grievance mechanism; "
            "supplier code of conduct."
        ),
        sector="energy",
        geography="Kenya",
    )
    result = assess_just_transition(
        company,
        [_record(notes="Accessible community grievance mechanism")],
        {"summary": "The climate transition plan funds worker reskilling and livelihoods."},
    )
    assert result["coverage_pct"] > 0
    assert "JT-01" in result["covered"]
    assert "JT-02" in result["covered"]
    assert "JT-04" in result["covered"]
    assert "JT-13" in result["covered"]
    assert result["transition_plan_people_linked"] is True
    assert result["readiness_band"] in {"early", "developing", "aligned"}


def test_living_wage_aliases_and_fx() -> None:
    name, value = resolve_geography("nairobi, kenya")
    assert name == "Kenya"
    assert value == 4800
    assert "Hong Kong" in list_geographies()

    result = living_wage_gap(
        "Kenya",
        [
            {"role": "field officer", "headcount": 10, "annual_wage": 400_000, "currency": "KES"},
            {"role": "manager", "headcount": 2, "annual_wage": 900_000, "currency": "KES"},
        ],
    )
    assert result["status"] == "ok"
    assert result["resolved_geography"] == "Kenya"
    assert result["headcount_below"] == 10
    assert result["remediation_cost"] > 0
    assert not result["warnings"]

    missing = living_wage_gap("Atlantis", [{"role": "x", "headcount": 1, "annual_wage": 1}])
    assert missing["status"] == "no_benchmark"
    assert missing["remediation_cost"] is None
    us_name, us_value = resolve_geography("US")
    assert us_name == "United States"
    assert us_value == 42000


def test_fx_covers_impact_fund_currencies() -> None:
    kes = convert(130, from_ccy="KES", to_ccy="USD")
    assert kes == 1.0
    assert convert(100, from_ccy="PHP", to_ccy="USD") is not None
    assert convert(100, from_ccy="VND", to_ccy="USD") is not None


def test_sbtn_has_full_five_step_questionnaire() -> None:
    company = Company(
        name="Agri Co",
        description="TNFD LEAP assessment complete with no-conversion policy from a 2020 cut-off.",
        sector="agriculture",
    )
    result = sbtn_readiness(company, {})
    question_ids = [q["id"] for step in result["steps"] for q in step["questions"]]
    assert len(question_ids) >= 16
    assert {"A1", "P1", "M1", "AC1", "T1"}.issubset(question_ids)
    assert "AC1" in result["auto_detected"]
    assert result["material_pressures_for_sector"]
    land = nature_target_ranges("land", "agriculture")
    assert land["indicative_reduction_pct"] == [0, 0]
    assert "no conversion" in land["note"].lower()


def test_carbon_credit_aliases_and_no_fake_methods() -> None:
    assert "icvcm-method-01" not in CCP_APPROVED_METHODOLOGIES
    assert normalize_program("Verra VCS") == "verra_vcs"
    labelled = screen_credits(
        [
            CarbonCredit(
                program="verra",
                methodology_id="VM-0042",
                vintage=2023,
                volume_tco2e=1000,
                ccp_labelled=True,
                project_type="soil",
            )
        ]
    )
    assert labelled.ccp_status == "ccp_labelled"
    assert labelled.vcmi_claim_tier == "compliant"

    pathway = screen_credits(
        [
            CarbonCredit(
                program="Gold Standard",
                methodology_id="gs-reforestation",
                vintage=2022,
                volume_tco2e=500,
                project_type="arr",
            )
        ]
    )
    assert pathway.ccp_status == "ccp_eligible_program"
    assert any("not CCP-labelled" in flag for flag in pathway.flags)

    unknown = screen_credits(
        [
            CarbonCredit(
                program="mystery-registry",
                methodology_id="xyz-1",
                vintage=2010,
                volume_tco2e=10,
                project_type="mystery",
            )
        ]
    )
    assert unknown.ccp_status == "unknown"
    assert any("pre-2016" in flag for flag in unknown.flags)


def test_biodiversity_principles_are_named() -> None:
    assert len(BIODIVERSITY_CREDIT_PRINCIPLES) == 21
    assert all(
        not item["principle"].startswith("High-integrity biodiversity credit principle")
        for item in BIODIVERSITY_CREDIT_PRINCIPLES
    )
    result = screen_biodiversity_credit({"BCP-01": 2, "BCP-09": 1})
    assert result["per_pillar"]["outcomes"] > 0
    assert any(gap["id"] == "BCP-02" for gap in result["gaps"])
    assert "BCP-01" not in result["unanswered"]


def test_greenwashing_unrelated_metrics_do_not_close_sdg_gap() -> None:
    claims = [1, 2, 3, 4, 5]
    empty = Company(
        name="Claim Co",
        description="We aspire to support every SDG.",
        sector="technology",
        sdg_claims=claims,
    )
    bloated = Company(
        name="Claim Co",
        description="We aspire to support every SDG.",
        sector="technology",
        sdg_claims=claims,
        reported_metrics={
            "CUSTOM:offices": "4",
            "CUSTOM:patents": "12",
            "CUSTOM:nps": "40",
            "CUSTOM:arr": "2m",
        },
    )
    empty_score = assess_greenwashing(empty)
    bloated_score = assess_greenwashing(bloated)
    assert bloated_score.claim_metric_gap >= 75
    assert bloated_score.claim_metric_gap >= empty_score.claim_metric_gap - 5


def test_company_uppercases_iris_metric_ids() -> None:
    company = Company(name="X", reported_metrics={"oi4112": "10", "custom:x": "y"})
    assert "OI4112" in company.reported_metrics
    assert "CUSTOM:x" in company.reported_metrics


def test_fintech_hits_giin_financial_services_benchmark() -> None:
    from openharness.impact.benchmarks import get_benchmark
    from openharness.impact.models import Company

    bm = get_benchmark("fintech")
    assert bm is not None
    assert bm.sector == "Financial Services"
    company = Company(name="PayCo", sector="Financial Services")
    assert get_benchmark(company.sector) is not None
    assert get_benchmark("livestock") is not None


def test_greenwashing_verification_ignores_metric_count() -> None:
    few = Company(
        name="Count Co",
        description="We aspire to be sustainable.",
        sector="technology",
        reported_metrics={"CUSTOM:a": "1"},
    )
    many = Company(
        name="Count Co",
        description="We aspire to be sustainable.",
        sector="technology",
        reported_metrics={f"CUSTOM:m{i}": "1" for i in range(40)},
    )
    assert assess_greenwashing(many).verification == assess_greenwashing(few).verification


def test_normalize_metric_map_keeps_custom_and_edci() -> None:
    from openharness.tools.impact.common import normalize_metric_map

    normalized, warnings = normalize_metric_map(
        {"oi4112": "10", "EDCI-G1": "yes", "CUSTOM:data_breach_incidents": "2", "BADID": "x"}
    )
    assert normalized["OI4112"] == "10"
    assert normalized["EDCI-G1"] == "yes"
    assert normalized["CUSTOM:data_breach_incidents"] == "2"
    assert "BADID" not in normalized
    assert any("BADID" in w for w in warnings)


def test_ddq_bank_is_authored_not_generated() -> None:
    from openharness.impact.ddq_responder import load_ddq_bank

    bank = load_ddq_bank()
    assert len(bank) == 80
    assert all("(intent " not in q.text for q in bank)
    assert {q.framework for q in bank} == {"ilpa_ddq2", "pri_2026", "ilpa_climate_module"}
    assert len({q.qid for q in bank}) == 80
    assert any(q.answer_kind == "metric" and "ghg_scope1_emissions" in q.maps_to for q in bank)


def test_giin_benchmarks_cover_core_impact_sectors() -> None:
    from openharness.impact.giin_benchmarks import list_giin_benchmarks

    sectors = {row.sector for row in list_giin_benchmarks()}
    assert {
        "agriculture",
        "energy",
        "financial services",
        "healthcare",
        "education",
        "water",
        "housing",
        "manufacturing",
        "waste management",
        "transport",
    }.issubset(sectors)
    assert list_giin_benchmarks("fintech")
    assert list_giin_benchmarks("edtech")


def test_pitch_deck_mapped_metrics_require_iris_id_in_sentence() -> None:
    from openharness.impact.database import get_metric_store
    from openharness.tools.impact.pitch_deck_analyze_tool import _match_metrics

    store = get_metric_store()
    health_only = _match_metrics("We work in health and education.", store)
    assert health_only == []
    with_id = _match_metrics("Scope 1 emissions (OI4112) are measured annually.", store)
    assert any(m.id == "OI4112" for m in with_id)


def test_pitch_deck_extracts_only_valued_iris_ids() -> None:
    text = (
        "Solar Co provides clean energy. Scope 1 (OI4112): 1,200 tCO2e. "
        "We also recommend tracking PI4060."
    )
    extracted = _extract_reported_metrics(text)
    assert extracted["OI4112"] == "1,200 tCO2e"
    assert "PI4060" not in extracted


def test_pitch_deck_tool_still_keeps_suggestions_out_of_reported(tmp_path: Path) -> None:
    tool = PitchDeckAnalyzeTool()
    result = asyncio.run(
        tool.execute(
            PitchDeckAnalyzeInput(
                text=(
                    "Solar Co provides clean energy access to rural households and "
                    "supports SDG 7 with renewable energy services."
                ),
                save_company_yaml=str(tmp_path / "company.yaml"),
            ),
            ToolExecutionContext(cwd=Path(".")),
        )
    )
    assert not result.is_error
    assert result.metadata["extracted_company"]["reported_metrics"] == {}
    assert result.metadata["suggested_metrics"]
