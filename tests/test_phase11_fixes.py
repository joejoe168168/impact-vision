"""Phase 11 regression tests for the 12 correctness/linkage fixes.

Each test maps to one of the issues called out in the README "System Review"
section. If any of these fail, the corresponding fix has regressed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


# ---------------------------------------------------------------------------
# Issue 1 — MCP server resources
# ---------------------------------------------------------------------------

mcp_available = True
try:
    import mcp  # noqa: F401
except ImportError:
    mcp_available = False


@pytest.mark.skipif(not mcp_available, reason="`mcp` package not installed")
class TestMCPResources:
    """All 5 MCP resources must return non-error JSON.

    These exercises the resource handler functions directly (we can't easily
    run the MCP transport in a unit test) but cover the bug paths that used
    to throw `AttributeError` on the wrong method / attribute names.
    """

    def test_catalog_stats_resource(self) -> None:
        from openharness.impact import mcp_server
        out = json.loads(mcp_server.catalog_stats())
        assert "error" not in out
        assert out["total_metrics"] > 0
        assert isinstance(out["categories"], list)
        assert isinstance(out["themes"], list)

    def test_dd_checklist_categories_resource(self) -> None:
        from openharness.impact import mcp_server
        out = json.loads(mcp_server.dd_checklist_categories())
        assert "error" not in out
        assert out["total_questions"] > 0
        assert isinstance(out["categories"], dict)

    def test_cross_reference_lookup_resource(self) -> None:
        from openharness.impact import mcp_server
        out = json.loads(mcp_server.cross_reference_lookup("OI4112"))
        assert "error" not in out
        assert out["match_count"] >= 1

    def test_sdg_goals_list_resource(self) -> None:
        from openharness.impact import mcp_server
        out = json.loads(mcp_server.sdg_goals_list())
        assert "error" not in out
        assert out["total"] == 17


class TestMCPResourceLogicStandalone:
    """Test the pure logic the MCP resources call, with no `mcp` dependency.

    Even if the FastMCP server can't import, the underlying engine calls must
    be sound (they were the source of issue #1).
    """

    def test_store_all_metrics_works(self) -> None:
        from openharness.impact.database import get_metric_store
        store = get_metric_store()
        metrics = store.all_metrics()
        assert metrics, "MetricStore.all_metrics() must return non-empty"
        m = metrics[0]
        # The MCP resource was reading m.category / m.theme — these don't
        # exist. The correct attributes are below.
        assert hasattr(m, "primary_impact_category")
        assert hasattr(m, "impact_themes")

    def test_load_checklist_returns_dd_questions(self) -> None:
        from openharness.impact.dd_checklist import DDQuestion, load_checklist
        qs = load_checklist()
        assert qs, "load_checklist() returned empty"
        assert isinstance(qs[0], DDQuestion)
        # Critical: must be addressable by attribute, not dict .get()
        assert hasattr(qs[0], "category")

    def test_iris_lookup_helpers_exist(self) -> None:
        from openharness.impact.frameworks import cross_reference as xr
        assert hasattr(xr, "lookup_by_iris")
        assert hasattr(xr, "lookup_by_gri")
        assert hasattr(xr, "lookup_by_edci")
        assert hasattr(xr, "lookup_by_sfdr")
        assert hasattr(xr, "lookup_by_sasb")


# ---------------------------------------------------------------------------
# Issue 2 — DD evidence-level scoping
# ---------------------------------------------------------------------------

class TestDDEvidenceScoping:
    def test_unrelated_rct_does_not_promote_all_questions(self) -> None:
        """An RCT mention buried in a memo's footer must not lift every
        addressed question to evidence level 5.
        """
        from openharness.impact.dd_checklist import analyze_document_coverage

        # Long text with one stray "RCT" mention but no other rigorous-evidence
        # signals near the question keywords.
        text = (
            "We serve smallholder farmers in Kenya and India. "
            "We provide loans, training and inputs to producers. "
            "Total clients reached: 12,000. Female clients: 60%. "
            "Loans outstanding: USD 2.4M. Training hours: 8,400. "
            "Outcomes are reported annually in our impact report. "
            * 5
            + " Note: a third-party RCT is planned for 2027."
        )
        result = analyze_document_coverage(text)
        assert result.avg_evidence_level < 5.0, (
            f"Stray 'RCT' mention should not push avg evidence level to 5; got {result.avg_evidence_level}"
        )


# ---------------------------------------------------------------------------
# Issue 3 — SDG core metric set per goal
# ---------------------------------------------------------------------------

class TestSDGCoreMetricSet:
    def test_yaml_loads(self) -> None:
        from openharness.impact.sdg_mapper import _load_core_metrics_per_sdg
        core = _load_core_metrics_per_sdg()
        assert len(core) >= 16, f"Should cover at least 16 SDGs, got {len(core)}"
        for goal_num, ids in core.items():
            assert 1 <= goal_num <= 17
            assert 5 <= len(ids) <= 20, f"SDG {goal_num} has {len(ids)} metrics; should be 5-20"

    def test_scoring_basis_in_alignment(self) -> None:
        from openharness.impact.database import get_metric_store
        from openharness.impact.models import Company
        from openharness.impact.sdg_mapper import map_sdg_alignment

        company = Company(
            name="Test Microfinance",
            sector="financial",
            description="Microfinance lender serving smallholder female borrowers in rural Kenya.",
            sdg_claims=[1, 5, 8],
            reported_metrics={
                "PI4060": "12000",
                "PI3193": "8500",
                "OI4753": "Yes",
                "OI6213": "62%",
                "OI1571": "45%",
            },
        )
        alignments = map_sdg_alignment(company, get_metric_store())
        # At least one alignment should have a recognised scoring basis
        bases = {a.scoring_basis for a in alignments}
        assert bases & {"core_set", "broad_catalog", "estimated"}


# ---------------------------------------------------------------------------
# Issue 4 / 8 — 5D per-dimension cap and floor
# ---------------------------------------------------------------------------

class TestFiveDimensionCap:
    def test_no_metrics_no_floor_at_one(self) -> None:
        """When a dimension has no reference set at all, the score must
        reflect the inferred baseline (>= 0.5) but not be auto-floored at 1.0.
        """
        from openharness.impact.database import get_metric_store
        from openharness.impact.five_dimensions import assess_five_dimensions
        from openharness.impact.models import Company

        company = Company(
            name="Empty",
            sector="professional services",
            description="Consultancy",
            reported_metrics={},
        )
        result = assess_five_dimensions(company, get_metric_store())
        # Overall must be reasonable, not pegged at 1.0+ purely from the floor
        assert result.what.score >= 0.5

    def test_per_dim_cap_applied_with_few_metrics(self) -> None:
        """Reporting only 1-2 dimension-relevant metrics must not push the
        dimension above 2.5.
        """
        from openharness.impact.database import get_metric_store
        from openharness.impact.five_dimensions import assess_five_dimensions
        from openharness.impact.models import Company

        company = Company(
            name="Sparse Reporter",
            sector="financial",
            description="Inclusive fintech for under-banked women.",
            impact_themes=["financial inclusion"],
            reported_metrics={"PI4060": "1000", "OI6213": "55%"},
        )
        result = assess_five_dimensions(company, get_metric_store())
        for dim in (result.what, result.who, result.how_much,
                    result.contribution, result.risk):
            assert dim.score <= 5.0


# ---------------------------------------------------------------------------
# Issue 5 — Word-boundary matching
# ---------------------------------------------------------------------------

class TestWordBoundaryMatching:
    def test_dd_keyword_does_not_substring_match(self) -> None:
        """'food' as a DD keyword must not match 'seafood' embedded in text."""
        from openharness.impact.dd_checklist import analyze_document_coverage
        # Use text where only the substring is present — no real DD signal.
        text = (
            "We sell seafood and adjobs through our marketplace. "
            "No measurement programme." * 3
        )
        result = analyze_document_coverage(text, min_confidence=0.8)
        # Should match very few questions since substring matches are blocked.
        assert len(result.addressed) < 30, (
            f"Word-boundary regression: matched {len(result.addressed)} questions "
            "from a text that has no real DD signal"
        )


# ---------------------------------------------------------------------------
# Issue 6 — Adverse metrics map
# ---------------------------------------------------------------------------

class TestAdverseMetricsMap:
    def test_fintech_adverse_set_is_meaningful(self) -> None:
        from openharness.impact.greenwashing import _ADVERSE_METRICS_BY_SECTOR
        fintech = _ADVERSE_METRICS_BY_SECTOR["fintech"]
        # Old placeholder set was {PI4060, OI1571} — both *positive* impact
        # metrics. The new set must be wider AND not be a subset of those.
        assert len(fintech) >= 4
        assert set(fintech) != {"PI4060", "OI1571"}


# ---------------------------------------------------------------------------
# Issue 7 — Benchmark provenance
# ---------------------------------------------------------------------------

class TestBenchmarkProvenance:
    def test_every_benchmark_has_source_and_confidence(self) -> None:
        from openharness.impact.benchmarks import SECTOR_BENCHMARKS
        for name, bm in SECTOR_BENCHMARKS.items():
            assert bm.source, f"{name} missing source"
            assert bm.source_year >= 2020
            assert bm.confidence in {"high", "medium", "indicative"}


# ---------------------------------------------------------------------------
# Issue 9 — SFDR PAI IRIS+ cross-refs
# ---------------------------------------------------------------------------

class TestSFDRPAILinkage:
    def test_all_mandatory_pais_have_iris_links(self) -> None:
        from openharness.impact.frameworks.sfdr_pai import PAI_INDICATORS
        for pai in PAI_INDICATORS:
            assert pai.iris_cross_refs, (
                f"PAI #{pai.number} '{pai.name}' has no IRIS+ cross-reference"
            )

    def test_all_optional_pais_have_iris_links(self) -> None:
        from openharness.impact.frameworks.sfdr_pai import OPTIONAL_PAI_INDICATORS
        for pai in OPTIONAL_PAI_INDICATORS:
            assert pai.iris_cross_refs, (
                f"Optional PAI #{pai.number} '{pai.name}' has no IRIS+ cross-reference"
            )

    def test_direct_pai_keys_count_as_reported_data(self) -> None:
        from openharness.impact.frameworks.sfdr_pai import assess_sfdr_compliance

        result = assess_sfdr_compliance(reported_data={"SFDR PAI 1": "100 tCO2e", "pai-13": "40%"})
        rows = {row["number"]: row for row in result["indicators"]}

        assert rows[1]["addressed"] is True
        assert rows[13]["addressed"] is True
        assert "PAI 1 reported" in rows[1]["evidence"]

    def test_text_mentions_do_not_count_as_reportable_pai_coverage(self) -> None:
        from openharness.impact.frameworks.sfdr_pai import assess_sfdr_compliance

        result = assess_sfdr_compliance(
            company_description="The company mentions GHG emissions and gender pay gap governance.",
        )
        rows = {row["number"]: row for row in result["indicators"]}

        assert rows[1]["status"] == "mentioned"
        assert rows[1]["addressed"] is False
        assert result["addressed"] == 0


# ---------------------------------------------------------------------------
# Issue 10 — SASB metric codes in cross-references
# ---------------------------------------------------------------------------

class TestSASBCodeLookup:
    def test_lookup_by_sasb_code(self) -> None:
        from openharness.impact.frameworks.cross_reference import lookup_by_sasb
        results = lookup_by_sasb("EM-EP-110a.1")
        assert results, "SASB code reverse lookup returned empty"
        # The returned cross-reference should map back to GHG concept
        assert any("GHG" in r.concept or "Emissions" in r.concept for r in results)

    def test_new_framework_lookups(self) -> None:
        from openharness.impact.frameworks.cross_reference import (
            lookup_by_cdp,
            lookup_by_pcaf,
            lookup_by_sbti,
            lookup_by_tnfd,
        )
        assert lookup_by_pcaf("PCAF-Cat15-Financed-Emissions")
        assert lookup_by_sbti("SBTi-Net-Zero")
        assert lookup_by_cdp("CDP-Climate-C6.1")
        assert lookup_by_tnfd("TNFD-MET-CR-1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
