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
