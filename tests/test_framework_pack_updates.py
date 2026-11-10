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
