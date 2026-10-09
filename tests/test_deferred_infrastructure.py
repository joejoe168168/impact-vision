"""Coverage for concordance, geospatial/dMRV, ESRS, iXBRL, MCP shim, namespace."""

from __future__ import annotations

from datetime import date

from impact_vision.impact.concordance import load_concordance
from impact_vision.impact.dmrv import get_dmrv_signer, observations_to_series
from impact_vision.impact.frameworks.esrs import load_simplified_datapoints
from impact_vision.impact.geospatial import AssetLocation, classify_biome, get_satellite_provider
from impact_vision.impact.greenwashing import classify_climate_claims
from impact_vision.impact.models import MetricRecord
from impact_vision.impact.xbrl_export import render_ixbrl, render_xbrl_json, tag_records
from impact_vision.mcp.highlevel import FastMCP, create_highlevel_server


def _record(metric_id: str = "OI4112") -> MetricRecord:
    return MetricRecord.model_validate(
        {
            "metric_id": metric_id,
            "value": 10,
            "unit": "tCO2e",
            "period": "2026-12-31",
            "source": "ledger",
            "owner": "CFO",
            "quality_score": 90,
            "verification_status": "third_party_verified",
            "boundary": "operational control",
            "methodology": "GHG Protocol",
        }
    )


def test_concordance_has_lp_comparable_core() -> None:
    concordance = load_concordance()
    ids = {entry.concept_id for entry in concordance.entries}
    assert len(concordance.entries) >= 100
    for concept in (
        "ghg_scope1_emissions",
        "ghg_scope2_emissions",
        "ghg_scope3_emissions",
        "energy_consumption",
        "water_consumed",
        "living_wage",
        "gender_pay_gap",
        "financed_emissions",
    ):
        assert concept in ids
    scope2 = concordance.lookup("iris", "OI9604")
    assert scope2 is not None
    assert any(ref.taxonomy_uri for ref in scope2.refs)


def test_geospatial_biome_caps_desert_loss() -> None:
    provider = get_satellite_provider()
    amazon = AssetLocation(asset_id="AMZ", latitude=-3.1, longitude=-60.0)
    dubai = AssetLocation(asset_id="DXB", latitude=25.2, longitude=55.3)
    assert classify_biome(*(-3.1, -60.0)) == "tropical_forest"
    assert classify_biome(25.2, 55.3) == "desert"
    amz = provider.observe(amazon, "gfw-tree-cover-loss", date(2025, 1, 1))
    dxb = provider.observe(dubai, "gfw-tree-cover-loss", date(2025, 1, 1))
    assert amz and dxb
    assert dxb.biome == "desert"
    assert amz.biome == "tropical_forest"
    assert dxb.value <= 1.0
    assert "GFC" in (dxb.dataset_version or "")
    same = provider.observe(dubai, "gfw-tree-cover-loss", date(2025, 1, 1))
    assert same and same.value == dxb.value


def test_dmrv_lifts_geospatial_and_requires_dev_flag(monkeypatch) -> None:
    provider = get_satellite_provider()
    asset = AssetLocation(asset_id="F1", latitude=1.3, longitude=103.8)
    obs = [
        provider.observe(asset, "viirs-nightlights", date(2025, 1, 1)),
        provider.observe(asset, "viirs-nightlights", date(2025, 2, 1)),
    ]
    series = observations_to_series(obs, "OI4112")
    assert series.source_kind == "remote_sensing"
    assert len(series.points) == 2
    monkeypatch.setenv("IMPACT_VISION_ALLOW_DEV_KEYS", "0")
    monkeypatch.delenv("IMPACT_VISION_DMRV_HMAC_KEY", raising=False)
    try:
        get_dmrv_signer()
        raised = False
    except ValueError:
        raised = True
    assert raised
    monkeypatch.setenv("IMPACT_VISION_ALLOW_DEV_KEYS", "1")
    assert get_dmrv_signer().id


def test_climate_claim_classifier_is_heuristic_without_model() -> None:
    result = classify_climate_claims(
        "We will be carbon neutral by 2030 using offsets and a net-zero pledge."
    )
    assert result["is_climate_related"] is True
    assert result["neutrality_language"] is True
    assert result["offset_language"] is True
    assert result["backend"] in {"heuristic", "climatebert"}


def test_simplified_esrs_named_disclosures_outrank_fillers() -> None:
    rows = load_simplified_datapoints()
    # W4.1: the revised ESRS are law, so generated filler rows are gone.
    assert not any(row.synthetic for row in rows)
    named = rows
    assert len(named) >= 50
    ids = {row.datapoint_id for row in named}
    assert "ESRS2-GOV-1" in ids or "GOV-1" in ids
    assert any(row.datapoint_id.startswith("E1-") for row in named)


def test_ixbrl_document_has_schema_and_units() -> None:
    concordance = load_concordance()
    tags, untaggable = tag_records([_record()], "esrs_set1", concordance)
    assert tags and not untaggable
    html = render_ixbrl("<html><body></body></html>", tags, "Acme", "2026-12-31")
    assert "schemaRef" in html
    assert "xbrli:unit" in html
    payload = render_xbrl_json(tags, "Acme", "2026-12-31")
    assert payload["documentInfo"]["status"] == "screening_prototype"
    assert payload["facts"]


def test_mcp_highlevel_server_constructs() -> None:
    server = create_highlevel_server("impact-vision-test")
    assert server is not None
    assert FastMCP is not None


def test_impact_vision_namespace_reexports() -> None:
    import impact_vision
    from impact_vision.impact.models import Company

    assert Company(name="NS Co").name == "NS Co"
    assert impact_vision.impact.models.Company is Company
