"""Wave 4 standards currency: PCAF 2025, China MoF profile (roadmap v8)."""
from __future__ import annotations

from impact_vision.impact.frameworks.pcaf import FinancedEmissionsInput, rollup_pcaf


def test_pcaf_2025_classes_undrawn_and_avoided_are_separate():
    entries = [
        FinancedEmissionsInput(company_name="A", asset_class="listed_equity", outstanding_investment_eur=10e6,
                               enterprise_value_eur=100e6, reported_emissions_tco2e=5000,
                               undrawn_commitment_eur=2e6, avoided_emissions_tco2e=800),
        FinancedEmissionsInput(company_name="B", asset_class="use_of_proceeds", outstanding_investment_eur=5e6,
                               enterprise_value_eur=20e6, reported_emissions_tco2e=1000),
    ]
    r = rollup_pcaf(entries)
    assert r.total_financed_emissions_tco2e == 750.0  # 500 + 250: avoided emissions are not netted
    assert r.avoided_emissions_tco2e == 800 and r.undrawn_commitments_eur == 2e6
    assert r.method_version == "pcaf-2025-12"
    assert "Dec 2025" in r.entries[1].notes


def test_cn_profile_has_the_mof_standards():
    from impact_vision.impact.engagements.regulatory import get_jurisdiction_profile

    ids = [o.obligation_id for o in get_jurisdiction_profile("CN").obligations]
    assert {"cn_mof_basic_standard", "cn_mof_climate_no1"} <= set(ids)


REPORT_EN = """# Harbour Logistics — Sustainability Report 2025
The Board oversees climate-related risks through its Sustainability Committee, which meets quarterly.
Management's role: the Chief Sustainability Officer reports to the committee.
We assessed physical and transition risks over short-term, medium-term and long-term time horizons.
Our value chain and business model are exposed to carbon pricing; our transition plan electrifies the fleet.
Scenario analysis at 1.5°C and 3°C shows the strategy is resilient.
Scope 1 emissions were 12,400 tCO2e; Scope 2 were 3,100 tCO2e. Our KPIs are listed in the appendix.
We target a 40% cut in Scope 1 and 2 by 2030 against a 2022 baseline.
This report complies with HKFRS S1.
"""

REPORT_ZH = """# 港灣物流 可持續發展報告
董事會透過可持續發展委員會監察氣候相關風險。
我們評估了短期、中期及長期的風險及機遇。
範圍一排放為 12,400 公噸二氧化碳當量。
"""


def test_hkfrs_s1_gap_reads_english_and_flags_gaps():
    from impact_vision.impact.frameworks.hkfrs_s1 import hkfrs_s1_gap, to_text

    out = hkfrs_s1_gap(REPORT_EN)
    status = {r["id"]: r["status"] for r in out["requirements"]}
    assert status["gov_body"] == "addressed" and status["strat_resilience"] == "addressed"
    assert status["targets"] in {"addressed", "partly"}
    assert status["judgements"] == "gap" and status["compliance_statement"] == "stated"
    assert out["warnings"] and "¶72" in out["warnings"][0]  # claims compliance with gaps left
    assert "HKFRS S1" in to_text(out)


def test_hkfrs_s1_gap_reads_traditional_chinese():
    from impact_vision.impact.frameworks.hkfrs_s1 import hkfrs_s1_gap

    out = hkfrs_s1_gap(REPORT_ZH, lang="zh-HK")
    status = {r["id"]: r["status"] for r in out["requirements"]}
    assert status["gov_body"] != "gap" and status["strat_risks_opps"] != "gap" and status["metrics_disclosed"] != "gap"
    assert out["pillars"]["governance"]["label"] == "管治"
    assert any(r["title"].startswith("監察") for r in out["requirements"])


def test_scope3_method_is_recorded_and_validated(monkeypatch):
    import pytest

    from impact_vision.impact.climate_accounting import resolve_scope3_method

    assert resolve_scope3_method() == "ghgp-2011"
    monkeypatch.setenv("IMPACT_VISION_GHG_SCOPE3_METHOD", "ghgp-revision")
    with pytest.raises(ValueError, match="ghgp-2011"):
        resolve_scope3_method()  # a pending method can't be used before it is final
