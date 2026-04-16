"""Tests for the Impact Vision engine."""

import json
from pathlib import Path

import pytest

from openharness.impact.catalog import (
    get_default_json_path,
    load_catalog_json,
)
from openharness.impact.database import MetricStore, get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.models import Company, Metric, SDGGoal, SDGTarget
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.impact.sdg_taxonomy import get_all_targets, get_sdg_goal, get_sdg_goals


@pytest.fixture
def store() -> MetricStore:
    return get_metric_store()


@pytest.fixture
def sample_company() -> Company:
    return Company(
        name="TestCo",
        sector="Financial Services",
        impact_themes=["Financial Inclusion"],
        reported_metrics={
            "PI4060": "45000",
            "OI8869": "180",
            "OI6213": "85",
            "OI1571": "12",
            "OI1479": "120",
            "OI4112": "80",
        },
        sdg_claims=[1, 5, 8],
    )


@pytest.mark.skipif(
    get_metric_store().count == 0,
    reason="IRIS+ catalog data not available (requires Excel file in data/raw/)",
)
class TestMetricStore:
    def test_load_catalog(self, store: MetricStore) -> None:
        assert store.count > 700

    def test_search(self, store: MetricStore) -> None:
        results = store.search("climate")
        assert len(results) > 0
        assert any("climate" in m.name.lower() for m in results)

    def test_filter_by_sdg(self, store: MetricStore) -> None:
        results = store.filter_by_sdg(7)
        assert len(results) > 0
        for m in results:
            assert 7 in m.sdg_goals

    def test_filter_by_theme(self, store: MetricStore) -> None:
        results = store.filter_by_theme("Financial Inclusion")
        assert len(results) > 0

    def test_filter_by_dimension(self, store: MetricStore) -> None:
        results = store.filter_by_dimension("what")
        assert len(results) > 0
        for m in results:
            assert m.dimensions.what

    def test_get_metric(self, store: MetricStore) -> None:
        result = store.get("PI4060")
        assert result is not None
        assert result.id == "PI4060"

    def test_stats(self, store: MetricStore) -> None:
        stats = store.stats()
        assert stats["total_metrics"] > 700
        assert "sdg_coverage" in stats
        assert "dimension_counts" in stats


class TestSDGTaxonomy:
    def test_get_all_goals(self) -> None:
        goals = get_sdg_goals()
        assert len(goals) == 17
        assert goals[0].number == 1
        assert goals[0].name == "No Poverty"

    def test_get_sdg_goal(self) -> None:
        goal = get_sdg_goal(7)
        assert goal is not None
        assert goal.name == "Affordable and Clean Energy"
        assert len(goal.targets) >= 3

    def test_get_all_targets(self) -> None:
        targets = get_all_targets()
        assert len(targets) > 100


class TestFiveDimensions:
    def test_assess(self, sample_company: Company, store: MetricStore) -> None:
        result = assess_five_dimensions(sample_company, store)
        assert result.overall_score >= 0
        assert result.overall_score <= 5.0
        assert result.overall_grade in ("A", "B+", "B", "B-", "C+", "C", "D", "F")
        assert result.what.score >= 0
        assert result.who.score >= 0


class TestSDGMapper:
    def test_map_alignment(self, sample_company: Company, store: MetricStore) -> None:
        results = map_sdg_alignment(sample_company, store)
        assert len(results) > 0
        for a in results:
            assert 0 <= a.score <= 100
            assert a.confidence in ("high", "medium", "low")


class TestGapAnalysis:
    def test_analyze(self, sample_company: Company, store: MetricStore) -> None:
        result = analyze_gaps(sample_company, store)
        assert "coverage_percentage" in result
        assert 0 <= result["coverage_percentage"] <= 100
        assert "missing" in result
        assert "reported" in result


class TestDDChecklist:
    def test_load_checklist(self) -> None:
        from openharness.impact.dd_checklist import load_checklist
        questions = load_checklist()
        assert len(questions) >= 40
        assert all(q.id for q in questions)
        assert all(q.question for q in questions)

    def test_categories(self) -> None:
        from openharness.impact.dd_checklist import load_checklist
        questions = load_checklist()
        cats = {q.category for q in questions}
        assert "impact_thesis" in cats
        assert "risk" in cats
        assert "who_stakeholders" in cats

    def test_analyze_coverage(self) -> None:
        from openharness.impact.dd_checklist import analyze_document_coverage
        text = (
            "Our theory of change links financial inclusion to poverty reduction. "
            "We serve 45,000 underserved clients, primarily women in rural areas. "
            "SDG 1 and SDG 5 are our primary goals. We measure outcomes quarterly."
        )
        result = analyze_document_coverage(text)
        assert result.total_questions > 0
        assert len(result.addressed) > 0
        assert result.coverage_pct > 0

    def test_select_questions(self) -> None:
        from openharness.impact.dd_checklist import select_questions_for_document
        text = "A fintech startup providing mobile banking to rural communities."
        suggested = select_questions_for_document(text, max_questions=10)
        assert len(suggested) > 0
        assert len(suggested) <= 10


class TestFrameworks:
    def test_sasb_match(self) -> None:
        from openharness.impact.frameworks.sasb import match_sasb_industry
        matches = match_sasb_industry(sector="Financial Services", description="Digital microfinance platform")
        assert len(matches) > 0
        assert matches[0][1] > 0

    def test_gri_match(self) -> None:
        from openharness.impact.frameworks.gri import match_gri_topics
        matches = match_gri_topics(description="Manufacturing company with high energy consumption and emissions")
        assert len(matches) > 0

    def test_tcfd_assess(self) -> None:
        from openharness.impact.frameworks.tcfd import assess_tcfd_alignment
        result = assess_tcfd_alignment(
            company_description="We track Scope 1 and Scope 2 emissions and have set science-based targets",
            reported_data={"OI4112": "80", "OI1479": "120"},
        )
        assert result["total_disclosures"] == 11
        assert result["addressed_disclosures"] > 0

    def test_sfdr_assess(self) -> None:
        from openharness.impact.frameworks.sfdr_pai import assess_sfdr_compliance
        result = assess_sfdr_compliance(
            reported_data={"OI4112": "80", "OI1479": "120", "OI1582": "0.95"},
            company_description="We report GHG emissions and gender pay gap data",
        )
        assert result["total"] == 14
        assert result["addressed"] > 0

    def test_edci_assess(self) -> None:
        from openharness.impact.frameworks.edci import assess_edci_coverage
        result = assess_edci_coverage(
            reported_data={"OI4112": "80", "OI6213": "85"},
            company_description="We track employee turnover, female leadership, and energy use",
        )
        assert result["total"] == 17
        assert result["addressed"] > 0

    def test_unpri_assess(self) -> None:
        from openharness.impact.frameworks.unpri import assess_unpri_alignment
        result = assess_unpri_alignment(
            fund_description="We integrate ESG analysis into investment decisions and report to LPs",
        )
        assert result["total_actions"] == 27
        assert len(result["principles"]) == 6

    def test_toc_rs_group(self) -> None:
        from openharness.impact.frameworks.theory_of_change import assess_toc_alignment, get_rs_group_principles
        principles = get_rs_group_principles()
        assert len(principles) == 8
        result = assess_toc_alignment(
            description="We take a total portfolio approach with blended value, managing all capital for systemic change",
        )
        assert result["addressed"] > 0
        assert result["total_principles"] == 8

    def test_toc_giin_checklist(self) -> None:
        from openharness.impact.frameworks.theory_of_change import assess_toc_completeness
        result = assess_toc_completeness(
            document_text="The problem we address is financial exclusion. Our stakeholders are "
                         "smallholder farmers. We provide microloans as our intervention. "
                         "Our activities lead to outputs and outcomes. The key risk is regulatory change. "
                         "We measure with IRIS metrics quarterly and learn from the data.",
        )
        assert result["total_steps"] == 8
        assert result["addressed"] > 0


class TestCrossReference:
    def test_lookup_by_iris(self) -> None:
        from openharness.impact.frameworks.cross_reference import lookup_by_iris
        results = lookup_by_iris("OI4112")
        assert len(results) > 0
        assert results[0].concept == "GHG Emissions - Scope 1 (Direct)"

    def test_lookup_by_gri(self) -> None:
        from openharness.impact.frameworks.cross_reference import lookup_by_gri
        results = lookup_by_gri("305-1")
        assert len(results) > 0

    def test_lookup_by_edci(self) -> None:
        from openharness.impact.frameworks.cross_reference import lookup_by_edci
        results = lookup_by_edci("EDCI-E1")
        assert len(results) > 0

    def test_lookup_by_sfdr(self) -> None:
        from openharness.impact.frameworks.cross_reference import lookup_by_sfdr
        results = lookup_by_sfdr(1)
        assert len(results) > 0

    def test_search_cross_references(self) -> None:
        from openharness.impact.frameworks.cross_reference import search_cross_references
        results = search_cross_references("gender")
        assert len(results) > 0

    def test_total_mappings(self) -> None:
        from openharness.impact.frameworks.cross_reference import get_all_cross_references
        refs = get_all_cross_references()
        assert len(refs) >= 35


class TestEvidenceLevels:
    def test_evidence_level_narrative(self) -> None:
        from openharness.impact.dd_checklist import analyze_document_coverage
        text = "Our mission is to improve lives. We aim to create social good."
        result = analyze_document_coverage(text)
        for match in result.addressed:
            assert 1 <= match.evidence_level <= 5
            assert match.evidence_label != ""

    def test_evidence_level_outcome_data(self) -> None:
        from openharness.impact.dd_checklist import analyze_document_coverage
        text = (
            "We served 45,000 clients. Our pre-post survey data shows a 30% income increase. "
            "We tracked KPIs quarterly and measured outcomes against baseline. "
            "Our theory of change links financial inclusion to poverty reduction. "
            "SDG 1 and SDG 5. We monitor data with IRIS metrics."
        )
        result = analyze_document_coverage(text)
        assert result.avg_evidence_level >= 2.0

    def test_evidence_level_definitions(self) -> None:
        from openharness.impact.dd_checklist import EVIDENCE_LEVELS
        assert len(EVIDENCE_LEVELS) == 5
        assert 1 in EVIDENCE_LEVELS
        assert 5 in EVIDENCE_LEVELS


class TestSectorDDQuestions:
    def test_sector_questions_loaded(self) -> None:
        from openharness.impact.dd_checklist import load_checklist
        questions = load_checklist()
        sector_cats = {q.category for q in questions if q.category.startswith("sector_")}
        assert "sector_fintech" in sector_cats
        assert "sector_health" in sector_cats
        assert "sector_agriculture" in sector_cats
        assert "sector_energy" in sector_cats
        assert "sector_education" in sector_cats

    def test_sector_questions_count(self) -> None:
        from openharness.impact.dd_checklist import load_checklist
        questions = load_checklist()
        sector_qs = [q for q in questions if q.category.startswith("sector_")]
        assert len(sector_qs) == 25  # 5 sectors * 5 questions each

    def test_sector_relevance_detection(self) -> None:
        from openharness.impact.dd_checklist import select_questions_for_document
        text = "A fintech platform offering microfinance loans and mobile banking to rural communities."
        suggested = select_questions_for_document(text, max_questions=20)
        categories = {q.category for q in suggested}
        assert "sector_fintech" in categories


class TestBenchmarks:
    def test_get_benchmark(self) -> None:
        from openharness.impact.benchmarks import get_benchmark
        bm = get_benchmark("Financial Services")
        assert bm is not None
        assert bm.five_d_overall > 0
        assert len(bm.sdg_primary) > 0

    def test_get_benchmark_fuzzy(self) -> None:
        from openharness.impact.benchmarks import get_benchmark
        bm = get_benchmark("healthcare")
        assert bm is not None
        assert bm.sector == "Healthcare"

    def test_compare_to_benchmark(self) -> None:
        from openharness.impact.benchmarks import compare_to_benchmark
        result = compare_to_benchmark(
            "Financial Services",
            {"what": 3.5, "who": 3.0, "how_much": 2.5, "contribution": 2.0, "risk": 3.0},
            2.8, 40.0,
        )
        assert result["benchmark_available"] is True
        assert "dimensions" in result
        assert "overall" in result

    def test_no_benchmark(self) -> None:
        from openharness.impact.benchmarks import compare_to_benchmark
        result = compare_to_benchmark("Unknown Sector", {}, 0, 0)
        assert result["benchmark_available"] is False
