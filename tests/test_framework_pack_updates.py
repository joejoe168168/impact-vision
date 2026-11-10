"""R6 / R7: GRI 101-103, SBTi Net-Zero V2 and the EU Taxonomy simplification, from sourced YAML."""

from datetime import date

from impact_vision.impact.frameworks import pack_updates as pu


def test_every_row_has_a_source():
    data = pu.load_updates()
    rows = (data["gri"]["topic_standards"] + data["sbti"]["standards"] + data["eu_taxonomy"]["delegated_acts"])
    assert rows and all(r["source_url"].startswith("https://") and r["verified"] for r in rows)


def test_gri_101_replaces_304_from_2026():
    assert pu.gri_successor("GRI 304", date(2025, 12, 31)) is None
    assert pu.gri_successor("GRI 304", date(2026, 1, 1))["id"] == "GRI 101"


def test_gri_102_and_103_apply_from_2027_not_before():
    assert pu.gri_successor("305-1", date(2026, 11, 10)) is None
    assert pu.gri_upcoming("305-1", date(2026, 11, 10))["id"] == "GRI 102"
    assert pu.gri_successor("305-1", date(2027, 1, 1))["id"] == "GRI 102"
    assert pu.gri_successor("201-2", date(2027, 6, 1))["id"] == "GRI 102"
    assert pu.gri_successor("GRI 302", date(2027, 1, 1))["id"] == "GRI 103"
    assert pu.gri_successor("305-7", date(2027, 6, 1)) is None  # air emissions stay in GRI 305


def test_gri_sector_standards():
    assert [r["id"] for r in pu.gri_sector_standards()] == ["GRI 11", "GRI 12", "GRI 13", "GRI 14"]


def test_sbti_version_window():
    ids = lambda d: [r["id"] for r in pu.sbti_standard_in_force(d)]  # noqa: E731
    assert ids(date(2026, 11, 10)) == ["CNZS_V1"]
    assert ids(date(2027, 3, 1)) == ["CNZS_V2", "CNZS_V1"]
    assert ids(date(2028, 2, 1)) == ["CNZS_V2"]


def test_taxonomy_materiality_threshold():
    assert pu.taxonomy_non_material({"turnover": 4.0, "capex": 9.9, "opex": 2.0})
    assert not pu.taxonomy_non_material({"turnover": 4.0, "capex": 10.0})
    assert not pu.taxonomy_non_material({})
    assert any("2026/73" in ref for ref in pu.taxonomy_references())


def test_taxonomy_assessment_cites_the_simplification_act_and_flags_non_material():
    from impact_vision.impact.frameworks.eu_taxonomy import EconomicActivity, assess_taxonomy_alignment

    fields = EconomicActivity.model_fields
    kwargs = {"eligible": True, "revenue_share_pct": 4.0, "capex_share_pct": 3.0, "opex_share_pct": 1.0}
    for name, info in fields.items():
        if info.is_required() and name not in kwargs:
            kwargs[name] = "Solar PV generation"
    result = assess_taxonomy_alignment("Acme", [EconomicActivity(**kwargs)])
    assert any("2026/73" in r for r in result.references)
    assert any("non-material" in f for f in result.findings)


# --------------------------------------------------------------------------- wiring (R6 / R7, second pass)


def _codes(on):
    from impact_vision.impact.frameworks.gri import get_gri_standards

    return {s.code: s for s in get_gri_standards(on=on)}


def test_gri_standards_in_force_follow_the_successor_dates():
    from impact_vision.impact.frameworks.gri import GRI_STANDARDS

    before, after_101, after_102 = _codes(date(2025, 12, 31)), _codes(date(2026, 1, 1)), _codes(date(2027, 1, 1))
    assert "GRI 304" in before and "GRI 101" not in before
    assert "GRI 304" not in after_101 and after_101["GRI 101"].effective_date == "2026-01-01"
    assert after_101["GRI 101"].source_url.startswith("https://www.globalreporting.org")
    assert any("GRI 102" in u for u in after_101["GRI 305"].upcoming)          # published, not yet in force
    assert "305-1" in {d.code for d in after_101["GRI 305"].disclosures}
    # 2027: GRI 102 takes 305-1..5 and 201-2; GRI 103 replaces GRI 302; 305-7 stays.
    g305 = after_102["GRI 305"]
    assert {d.code for d in g305.disclosures} == {"305-6", "305-7"}
    assert g305.superseded_disclosures["305-1"].startswith("GRI 102")
    assert "GRI 302" not in after_102 and {"GRI 102", "GRI 103"} <= set(after_102)
    assert "GRI 304" in {s.code for s in GRI_STANDARDS}  # the as-issued catalogue is untouched


def test_gri_matching_uses_the_standards_in_force():
    from impact_vision.impact.frameworks.gri import match_gri_topics

    hits = [s.code for s, _ in match_gri_topics(description="Habitat restoration and biodiversity offsets",
                                                 on=date(2026, 6, 1))]
    assert "GRI 101" in hits and "GRI 304" not in hits


def test_sbti_cites_the_versions_and_says_which_thresholds_it_applied():
    from impact_vision.impact.frameworks.sbti import SBTiClaim, check_sbti_alignment

    claim = SBTiClaim(company_name="GreenCo", base_year=2020, target_year_near_term=2030,
                      near_term_pct_reduction=50.0, target_year_net_zero=2045, net_zero_pct_reduction=95.0)
    now = check_sbti_alignment(claim, today=date(2026, 11, 10))
    assert now.thresholds_version == "CNZS_V1" and now.standards_accepted == ["CNZS_V1"]
    assert any("V1.3.1" in r for r in now.references) and not any("v1.2" in r for r in now.references)
    assert not any("V2.0" in f for f in now.findings)
    both = check_sbti_alignment(claim, today=date(2027, 3, 1))
    assert any("V2.0 is also accepted" in f for f in both.findings)
    only_v2 = check_sbti_alignment(claim, today=date(2028, 2, 1))
    assert any("only version accepted" in f for f in only_v2.findings)
    assert only_v2.near_term_pass == now.near_term_pass  # V1 numbers still applied: no V2 figures invented
    assert pu.sbti_thresholds()["v2_thresholds_recorded"] is False


def test_registry_rows_for_the_new_pack_facts():
    from impact_vision.impact.standards_registry import default_standards_registry

    reg = default_standards_registry()
    assert reg.get("GRI 101").effective_date == "2026-01-01" and reg.get("GRI 101").status == "active"
    assert reg.get("GRI 102").status == "published" and reg.get("GRI_103").effective_date == "2027-01-01"
    assert reg.get("SBTI_CNZS").version == "V1.3.1"                     # in force today
    assert reg.get("SBTI_CNZS", "V2.0").effective_date == "2027-02-01"
    assert reg.get("EU Taxonomy").version == "(EU) 2026/73"
    published = {s.key for s in reg.active_rule_packs()}
    assert "GRI_102@2025" not in published


def _tool(framework, action, **kw):
    import asyncio
    from pathlib import Path

    from impact_vision.tools.base import ToolExecutionContext
    from impact_vision.tools.impact.framework_tool import FrameworkInput, FrameworkTool

    args = FrameworkInput(framework=framework, action=action, **kw)
    return asyncio.run(FrameworkTool().execute(args, ToolExecutionContext(cwd=Path("."))))


def test_framework_tool_exposes_eu_taxonomy_and_sbti():
    from impact_vision.tools.impact.framework_tool import FRAMEWORK_CATALOG

    assert {"eu_taxonomy", "sbti"} <= {key for key, _, _ in FRAMEWORK_CATALOG}
    listing = _tool("eu_taxonomy", "list")
    assert not listing.is_error and "2026/73" in listing.output and "10%" in listing.output
    activity = {"name": "Solar PV", "eligible": True, "substantial_contribution": True, "dnsh_pass": True,
                "minimum_safeguards": True, "revenue_share_pct": 60, "capex_share_pct": 70, "opex_share_pct": 50}
    res = _tool("eu_taxonomy", "assess", description="SunCo", structured_inputs={"activities": [activity]})
    assert not res.is_error and "aligned 60.0%" in res.output and res.metadata["revenue_aligned_pct"] == 60
    assert _tool("eu_taxonomy", "assess").is_error  # needs activities
    sb = _tool("sbti", "assess", description="GreenCo",
               structured_inputs={"base_year": 2020, "target_year_near_term": 2030, "near_term_pct_reduction": 50})
    assert not sb.is_error and "Thresholds: CNZS_V1" in sb.output
    assert "V2.0" in _tool("sbti", "list").output
    assert "GRI 101" in _tool("gri", "list").output
