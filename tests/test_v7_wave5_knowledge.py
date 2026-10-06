"""Roadmap v7 W5.1 — knowledge as data."""

from __future__ import annotations

from datetime import date


def test_bundled_knowledge_is_sourced_and_fresh_today() -> None:
    from openharness.impact.knowledge import freshness_report

    report = freshness_report(today=date(2026, 10, 6))
    assert report.ok, report.summary()
    assert report.rows_checked > 300 and report.illustrative > 0


def test_freshness_gate_flags_stale_and_unsourced_rows() -> None:
    from openharness.impact.knowledge import freshness_report

    later = freshness_report(today=date(2027, 9, 1), names=["watchlist"])
    assert later.stale and not later.ok
    assert all("days old" in issue.problem for issue in later.stale)
    # illustrative benchmark rows never fail the gate
    bench = freshness_report(today=date(2030, 1, 1), names=["benchmarks"])
    assert bench.illustrative and all(i.row for i in bench.stale)
    assert len(bench.stale) < bench.rows_checked


def test_row_inherits_file_provenance() -> None:
    from openharness.impact.knowledge import effective_provenance

    prov = effective_provenance({"source": "FCA"}, {"as_of": "2026-10-06", "source_url": "https://x"})
    assert prov["as_of"] == "2026-10-06" and prov["source"] == "FCA" and prov["source_url"] == "https://x"
    assert prov["data_status"] == "published"


def test_modules_read_their_data_from_yaml() -> None:
    from openharness.impact.benchmarks import SECTOR_BENCHMARKS
    from openharness.impact.engagements.regulatory import JURISDICTION_PROFILES
    from openharness.impact.frameworks.cross_reference import CROSS_REFERENCE_MAP, lookup_by_iris
    from openharness.impact.knowledge import load_knowledge
    from openharness.impact.regulatory_packs import get_pack
    from openharness.impact.standards_registry import default_standards_registry

    assert len(JURISDICTION_PROFILES) == len(load_knowledge("regulatory/jurisdictions.yaml")["jurisdictions"])
    assert JURISDICTION_PROFILES["HK"].source.startswith("HKEX")
    assert len(CROSS_REFERENCE_MAP) == len(load_knowledge("concordance.yaml")["crosswalk"])
    assert lookup_by_iris("OI4112")
    assert len(SECTOR_BENCHMARKS) == 18
    assert get_pack("US-CA-CLIMATE").filings[1].cadence == "biennial"
    assert default_standards_registry().get("ISSA 5000").last_verified == "2026-10-06"


def test_one_benchmark_provider_answers_every_question() -> None:
    from openharness.impact.benchmark_provider import get_impact_benchmark_provider
    from openharness.impact.engagements.value_creation import BenchmarkQuery
    from openharness.impact.external_benchmarks import get_benchmark_provider

    provider = get_impact_benchmark_provider()
    assert get_benchmark_provider("impact_vision") is provider
    assert provider.percentiles("energy", "what").p50 > 0
    assert provider.sector_profile("Healthcare") is not None
    assert provider.kpi("energy", "ghg_avoided_tco2e") is not None
    assert provider.survey()["survey_year"] == 2023
    giin = provider.fetch(BenchmarkQuery(metric_id="ghg_avoided_tco2e", sector="energy"))
    sample = provider.fetch(BenchmarkQuery(metric_id="PI4060", sector="energy"))
    assert giin.sample_size and sample.sample_size and giin.provider == sample.provider == "impact_vision"
    assert provider.provenance("kpi")["data_status"] == "illustrative"
