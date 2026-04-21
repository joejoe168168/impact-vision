"""Regression tests for Phase 15 → Phase 20 additions.

One test module so we can run the whole Phase-15-through-20 coverage
pack in a single ``pytest`` invocation. Individual modules also have
detailed test coverage via the older Phase-10-14 files; this file
exercises the *new* surfaces introduced in v0.14.0.
"""
from __future__ import annotations

from datetime import date

import pytest


# ---------------------------------------------------------------------------
# Phase 15.6 — LLM extractor / verifier (offline-safe fallback path)
# ---------------------------------------------------------------------------

class TestLLMExtractorOfflineFallback:
    def test_falls_back_to_regex_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from openharness.impact.extractors.llm_extractor import LLMClaimExtractor

        ex = LLMClaimExtractor(api_key=None)
        claims = ex.extract(
            "We enrolled 3,500 students in 2024 and aim for net-zero by 2030."
        )
        assert claims, "regex fallback should have produced at least one claim"
        assert all(c.raw_extractor_id.startswith("llm-fallback") for c in claims)

    def test_strip_think_blocks(self):
        from openharness.impact.extractors.llm_extractor import _strip_think_blocks
        raw = "<think>debating…</think>\n```json\n{\"claims\":[]}\n```"
        out = _strip_think_blocks(raw)
        assert "<think>" not in out
        assert "```" not in out
        assert '"claims"' in out

    def test_safe_parse_json_recovers_from_noise(self):
        from openharness.impact.extractors.llm_extractor import _safe_parse_json
        noisy = 'irrelevant preamble {"claims":[{"text":"x"}]} trailing text'
        parsed = _safe_parse_json(noisy)
        assert parsed and parsed["claims"][0]["text"] == "x"


class TestLLMVerifierOfflineFallback:
    def test_no_api_key_uses_fallback(self, monkeypatch):
        from openharness.impact.extractors.base import ExtractedClaim
        from openharness.impact.extractors.llm_verifier import LLMSourceVerifier

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        v = LLMSourceVerifier(api_key=None, known_sources=[])
        result = v.verify(ExtractedClaim(text="net-zero by 2030", category="commitment"))
        assert result.verifier_id.startswith("llm-fallback")


# ---------------------------------------------------------------------------
# Phase 15 leftover — registry connectors
# ---------------------------------------------------------------------------

class TestCreditRegistries:
    def test_demo_registry_has_four_records(self):
        from openharness.impact.registries import DEMO_REGISTRY
        assert len(DEMO_REGISTRY.records) == 4
        ids = {r.registry for r in DEMO_REGISTRY.records}
        assert {"Verra", "Gold Standard", "Puro.earth", "BioCredits"} <= ids

    def test_aliases_resolve(self):
        from openharness.impact.registries import get_registry
        assert get_registry("vcs").id == "verra"
        assert get_registry("gs").id == "gold-standard"
        assert get_registry("puro").id == "puro.earth"

    def test_rollup_aggregates(self):
        from openharness.impact.registries import DEMO_REGISTRY, rollup_credits
        r = rollup_credits(DEMO_REGISTRY.records)
        assert r.total_outstanding > 0
        assert r.total_retired >= 0
        assert r.est_market_value_usd > 0
        assert set(r.by_registry.keys()) == {"Verra", "Gold Standard", "Puro.earth", "BioCredits"}


# ---------------------------------------------------------------------------
# Phase 15/16 — MOI + impact-adjusted IRR
# ---------------------------------------------------------------------------

class TestReturns:
    def test_moi_and_moic_basic(self):
        from openharness.impact.returns import ImpactCashflow, compute_moi
        cfs = [
            ImpactCashflow(period=date(2024, 1, 1), capital_flow_usd=-1_000_000, impact_units=0),
            ImpactCashflow(period=date(2025, 1, 1), capital_flow_usd=0, impact_units=5000),
            ImpactCashflow(period=date(2026, 1, 1), capital_flow_usd=1_500_000, impact_units=2000),
        ]
        moi = compute_moi(cfs, unit="beneficiaries")
        assert moi.moic_financial == pytest.approx(1.5, rel=1e-3)
        assert moi.moi_impact == pytest.approx(7000 / 1_000_000, rel=1e-3)

    def test_irr_converges_and_lift_is_signed(self):
        from openharness.impact.returns import ImpactCashflow, compute_irr
        cfs = [
            ImpactCashflow(period=date(2024, 1, 1), capital_flow_usd=-1_000_000),
            ImpactCashflow(period=date(2026, 1, 1), capital_flow_usd=1_210_000, impact_units=1000),
        ]
        r = compute_irr(cfs, impact_price_usd_per_unit=50.0)
        assert r.converged
        assert r.irr_financial and 0.05 < r.irr_financial < 0.15
        assert r.irr_impact_adjusted and r.irr_impact_adjusted > r.irr_financial


# ---------------------------------------------------------------------------
# Phase 16 — external benchmarks + blended finance + LP portal + marketplace
# ---------------------------------------------------------------------------

class TestExternalBenchmarks:
    def test_quartile_assignment(self):
        from openharness.impact.external_benchmarks import contextualise
        ctx = contextualise("energy", "what", 4.0)
        assert ctx is not None
        assert ctx.quartile in {1, 2, 3, 4}
        assert ctx.narrative

    def test_generic_fallback_when_sector_missing(self):
        from openharness.impact.external_benchmarks import contextualise
        ctx = contextualise("made-up-sector", "how_much", 2.5)
        assert ctx is not None
        assert ctx.percentiles.sector.lower() == "generic"


class TestBlendedFinance:
    def test_il_loan_step_schedule_monotonic(self):
        from openharness.impact.blended_finance import design_il_loan
        t = design_il_loan(
            borrower="Acme", principal_usd=5_000_000, base_rate_bps=600,
            tenor_months=60, kpi_id="IRIS+PI1234",
            kpi_description="tCO2e avoided", baseline=1000, target=5000,
        )
        bps = [s.rate_bps for s in t.step_schedule]
        assert bps == sorted(bps)

    def test_soc_max_payment_has_buffer(self):
        from openharness.impact.blended_finance import design_soc
        t = design_soc(
            project_name="X", outcome_payer="Gov", intermediary="Int",
            service_provider="SP", beneficiary_count_target=1000,
            outcome_metric="students graduated", unit_price_usd=500.0,
        )
        assert t.max_payment_usd == pytest.approx(1000 * 500 * 1.2)


class TestLPPortal:
    def test_capital_account_rollup(self):
        from openharness.impact.lp_portal import LPPortal
        p = LPPortal(fund_name="Demo Fund")
        s = p.capital_account_statement(
            lp_identifier="LP-001",
            committed_capital_usd=10_000_000, contributed_capital_usd=7_500_000,
            distributions_usd=3_000_000, net_asset_value_usd=6_000_000,
        )
        assert s.committed_capital_usd == 10_000_000
        assert len(s.lines) == 4

    def test_audit_trail_verifies(self):
        from openharness.impact.lp_portal import LPPortal
        p = LPPortal(fund_name="Demo Fund")
        a = p.audit_trail()
        assert a.chain_valid


class TestMarketplace:
    def test_publish_search_and_compare(self):
        from openharness.impact.fund_thesis import FundThesis
        from openharness.impact.marketplace import ThesisMarketplace

        m = ThesisMarketplace()
        a = m.publish("GP A", FundThesis(name="A", strategy="climate",
                                         geography_focus=["EU"],
                                         sdg_weights={7: 0.5, 13: 0.5}))
        b = m.publish("GP B", FundThesis(name="B", strategy="climate",
                                         geography_focus=["EU", "UK"],
                                         sdg_weights={7: 0.4, 11: 0.6}))
        match = m.compare(a.listing_id, b.listing_id)
        assert match is not None and match.score > 0
        assert 7 in match.overlap_sdgs
        assert "EU" in match.overlap_geographies


# ---------------------------------------------------------------------------
# Phase 17 — assurance / CSRD / ISSB / audit trail / SOC2
# ---------------------------------------------------------------------------

class TestAssurance:
    def test_pack_round_trip(self):
        from openharness.impact.assurance import build_assurance_pack
        pack = build_assurance_pack(
            fund_name="Demo", reporting_period="FY2025",
            assertion_text="We believe the following disclosures are fairly stated.",
            prepared_by="CFO",
            subject_description="Portfolio-level impact KPIs",
            metrics=["PI5380", "OI6541"],
        )
        assert pack.standard == "ISAE3000"
        assert pack.assertion.prepared_by == "CFO"
        assert pack.criteria  # default criteria populated


class TestCSRDWizard:
    def test_above_threshold_is_material(self):
        from openharness.impact.csrd_wizard import (
            MaterialityScore, assess_double_materiality,
        )
        scores = [
            MaterialityScore(topic="E1-climate", impact_materiality=4.5,
                             financial_materiality=4.0),
            MaterialityScore(topic="S1-own-workforce", impact_materiality=2.0,
                             financial_materiality=2.0),
        ]
        m = assess_double_materiality(entity="Co", reporting_period="2025",
                                      scores=scores)
        assert "E1-climate" in m.material_topics
        assert "S1-own-workforce" not in m.material_topics


class TestISSBPack:
    def test_structured_output(self):
        from openharness.impact.issb_reporting import (
            Governance, IFRSS1Pack, IFRSS2Pack, build_issb_pack,
        )
        s1 = IFRSS1Pack(entity="Co", reporting_period="2025",
                        governance=Governance(oversight_body="Audit Committee"))
        s2 = IFRSS2Pack(entity="Co", reporting_period="2025",
                        scope1_tco2e=100, scope2_tco2e=50, scope3_tco2e=400)
        pack = build_issb_pack(s1=s1, s2=s2)
        assert pack.s2.scope3_tco2e == 400


class TestAuditTrail:
    def test_chain_valid_after_events(self):
        from openharness.impact.audit_trail import AuditTrail
        t = AuditTrail(tenant_id="T", fund_id="F")
        t.record_event(event_type="score.recompute",
                       payload={"company": "Acme", "score": 3.4})
        t.record_event(event_type="dd.flag",
                       payload={"question": "gov-01", "priority": "high"})
        ok, problems = t.verify()
        assert ok, problems
        assert t.length == 2


class TestSOC2Checklist:
    def test_default_checklist_non_empty(self):
        from openharness.impact.soc2_checklist import (
            build_readiness_report, default_checklist,
        )
        items = default_checklist()
        assert len(items) > 20
        r = build_readiness_report("Impact Vision GP", items=items)
        assert 0 <= r.completion_pct <= 100
        assert r.total_controls == len(items)


# ---------------------------------------------------------------------------
# Phase 18 — causal / bayes / meta / spillover / sroi
# ---------------------------------------------------------------------------

class TestCausal:
    def test_rct_shifts_prior(self):
        from openharness.impact.causal import StudyResult, update_counterfactual_prior
        r = StudyResult(
            study_id="JPAL-001", design="RCT", outcome_metric="income_usd",
            treatment_effect=100.0, std_error=25.0,
            n_treatment=500, n_control=500,
        )
        new = update_counterfactual_prior(0.5, r)
        assert new > 0.5  # positive effect should push prior up


class TestBayes:
    def test_posterior_updates_and_ci(self):
        from openharness.impact.bayes import default_prior, update
        prior = default_prior(optimism=0.5, strength=4.0)
        post = update(prior, corroborating=3, contradicting=1)
        assert post.mean == pytest.approx(5 / 8)
        lo, hi = post.credible_interval(0.95)
        assert 0 <= lo < post.mean < hi <= 1


class TestMetaAnalysis:
    def test_deviation_flag_fires_above_two_sigma(self):
        from openharness.impact.meta_analysis import MetaStudy, deviation_flag, pool_effects
        studies = [
            MetaStudy(study_id="s1", outcome_metric="y",
                      effect_size=0.20, std_error=0.05),
            MetaStudy(study_id="s2", outcome_metric="y",
                      effect_size=0.22, std_error=0.05),
            MetaStudy(study_id="s3", outcome_metric="y",
                      effect_size=0.18, std_error=0.05),
        ]
        pooled = pool_effects(studies)
        flag, z = deviation_flag(2.0, pooled, sigma_threshold=2.0)
        assert flag and z > 2.0


class TestSpillover:
    def test_leakage_and_spillover_order(self):
        from openharness.impact.spillover import SpilloverAssumption, adjust_node
        a = SpilloverAssumption(
            toc_node_id="n1", outcome_metric="ha restored",
            raw_value=100.0, leakage_rate=0.2, spillover_rate=0.5,
        )
        out = adjust_node(a)
        # 100 * (1-0.2) * (1+0.5) = 120
        assert out.adjusted_value == pytest.approx(120.0)


class TestSROI:
    def test_sroi_positive_ratio(self):
        from openharness.impact.sroi import SROIOutcome, compute_sroi
        r = compute_sroi(
            project_name="X",
            total_investment_usd=100_000,
            outcomes=[
                SROIOutcome(
                    name="jobs created", unit_value_usd=5000,
                    quantity_per_year=20, duration_years=3,
                    deadweight_pct=20, attribution_pct=10,
                    displacement_pct=5, drop_off_pct_per_year=10,
                ),
            ],
        )
        assert r.sroi_ratio > 0
        assert "sroi_deadweight_plus20pct" in r.sensitivity


# ---------------------------------------------------------------------------
# Phase 19 — satellite / surveys / worker-voice / ecosystem
# ---------------------------------------------------------------------------

class TestSatellite:
    def test_deterministic_observation(self):
        from openharness.impact.geospatial import AssetLocation, get_satellite_provider
        p = get_satellite_provider()
        asset = AssetLocation(asset_id="FARM-01", latitude=3.15, longitude=101.7)
        a = p.observe(asset, "gfw-tree-cover-loss", date(2025, 1, 1))
        b = p.observe(asset, "gfw-tree-cover-loss", date(2025, 1, 1))
        assert a and b and a.value == b.value
        assert a.unit == "ha"


class TestSurveys:
    def test_csv_loader_skips_blank_ids(self):
        from openharness.impact.surveys import GenericCSVProvider, aggregate_numeric
        blob = (
            "respondent_id,nps_score,grievance_reported\n"
            "R1,9,false\n"
            "R2,7,true\n"
            ",4,true\n"        # skipped
            "R3,10,false\n"
        )
        d = GenericCSVProvider().load_csv(blob, form_id="test")
        assert d.n() == 3
        agg = aggregate_numeric(d, column="nps_score")
        assert agg["n"] == 3


class TestWorkerVoice:
    def test_who_lift_in_range(self):
        from openharness.impact.surveys import GenericCSVProvider
        from openharness.impact.worker_voice import summarise
        blob = (
            "respondent_id,nps_score,grievance_reported,anonymous_submission\n"
            "A,10,false,true\nB,9,false,true\nC,8,false,true\nD,6,true,true\n"
        )
        d = GenericCSVProvider().load_csv(blob, form_id="w")
        s = summarise(d)
        assert -1 <= s.who_lift <= 1
        assert s.n_respondents == 4


class TestEcosystem:
    def test_unit_value_lookup_returns_sensible_usd(self):
        from openharness.impact.ecosystem_services import (
            EcosystemAsset, get_ecosystem_provider,
        )
        v = get_ecosystem_provider().value(
            EcosystemAsset(asset_id="LOT-01", hectares=50.0, land_cover="wetland"),
            "water-purification",
        )
        assert v is not None
        assert v.annual_value_usd == pytest.approx(420.0 * 50.0)


# ---------------------------------------------------------------------------
# Phase 20 — i18n, thesis packs, regulatory packs, FX
# ---------------------------------------------------------------------------

class TestI18NDashboard:
    def test_six_language_keys_present(self):
        from openharness.impact.i18n import get_dashboard_strings, supported_locales
        for locale in supported_locales():
            s = get_dashboard_strings(locale)
            assert s, f"no strings for locale {locale}"
            assert "dashboard_title" in s

    def test_fallback_to_en(self):
        from openharness.impact.i18n import get_dashboard_strings
        s = get_dashboard_strings("made-up")
        assert s.get("run_tool")


class TestRegionalThesisPacks:
    def test_four_regional_yamls_exist(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent
        data = repo_root / "data"
        for name in [
            "fund_thesis.climate_eu.yaml",
            "fund_thesis.inclusive_finance_africa.yaml",
            "fund_thesis.gender_lens_south_asia.yaml",
            "fund_thesis.indigenous_led_na.yaml",
        ]:
            assert (data / name).is_file(), f"missing pack: {name}"


class TestRegulatoryPacks:
    def test_seven_jurisdictions_registered(self):
        from openharness.impact.regulatory_packs import list_packs
        packs = list_packs()
        assert len(packs) >= 7
        ids = {p.jurisdiction for p in packs}
        assert {"EU-SFDR", "EU-CSRD", "UK-FCA-SDR", "HK-HKEX-ESG"} <= ids

    def test_unknown_raises(self):
        import pytest as _pt
        from openharness.impact.regulatory_packs import get_pack
        with _pt.raises(KeyError):
            get_pack("MARS")


class TestFX:
    def test_round_trip_is_idempotent(self):
        from openharness.impact.fx import convert
        v = convert(100.0, from_ccy="USD", to_ccy="USD")
        assert v == 100.0

    def test_myr_to_usd(self):
        from openharness.impact.fx import convert
        v = convert(4650.0, from_ccy="MYR", to_ccy="USD")
        assert v is not None
        # 4650 MYR / 4.65 USD-per-MYR ≈ 1000 USD
        assert 900 < v < 1100


# ---------------------------------------------------------------------------
# Phase 15.6 — branding + DD v2 + SSE
# ---------------------------------------------------------------------------

class TestBranding:
    def test_default_colors_when_no_yaml(self):
        from openharness.impact.branding import branding_css, load_branding
        b = load_branding(thesis_path="/does/not/exist.yaml")
        css = branding_css(b)
        assert "--primary:" in css and "#0d47a1" in css

    def test_bad_color_ignored(self):
        from openharness.impact.branding import load_branding
        b = load_branding(raw={"primary_color": "javascript:alert(1)"})
        assert b.primary_color == "#0d47a1"  # fell back


class TestQuestionnaireV2:
    def test_missing_answer_triggers_followup(self):
        from openharness.impact.dd_checklist import DDQuestion
        from openharness.impact.questionnaire_v2 import (
            BranchRule, active_follow_up_ids, expand_active,
        )
        catalogue = [
            DDQuestion(id="who-7", question="Who are the beneficiaries?",
                       category="who"),
            DDQuestion(id="who-7a", question="How do you count them?",
                       category="who"),
        ]
        rules = [
            BranchRule(parent_id="who-7", kind="missing",
                       follow_up_ids=["who-7a"]),
        ]
        assert active_follow_up_ids({"who-7": ""}, rules) == ["who-7a"]
        expanded = expand_active(answered={"who-7": ""}, rules=rules,
                                 catalogue=catalogue)
        assert [q.id for q in expanded] == ["who-7a"]


class TestSSEStreaming:
    def test_sse_format(self):
        from openharness.web.streaming import sse_format
        out = sse_format("progress", {"pct": 50})
        assert out.startswith("event: progress\n")
        assert "data: " in out
        assert out.endswith("\n\n") or out.endswith("\n")

    def test_build_router_exposes_echo(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from openharness.web.streaming import build_sse_router
        app = FastAPI()
        app.include_router(build_sse_router())
        with TestClient(app) as c:
            r = c.get("/api/v1/stream/echo?msg=hi&n=2")
            assert r.status_code == 200
            body = r.text
            assert "event: progress" in body
            assert "event: result" in body
            assert "event: done" in body


# ---------------------------------------------------------------------------
# SDK façade smoke — every new static method should be callable
# ---------------------------------------------------------------------------

class TestSDKFacade:
    def test_new_methods_are_exposed(self):
        from openharness.impact.sdk import ImpactVision
        expected = [
            "compute_moi", "compute_irr", "rollup_credits",
            "benchmark_peer_context", "design_il_loan", "design_soc",
            "lp_portal", "thesis_marketplace", "build_assurance_pack",
            "double_materiality", "audit_trail", "soc2_readiness",
            "update_counterfactual_with_study", "bayesian_prior",
            "meta_pool", "adjust_spillover", "compute_sroi",
            "satellite_observation", "load_survey_csv", "worker_voice",
            "ecosystem_value", "regulatory_pack", "convert_currency",
            "load_branding",
        ]
        for name in expected:
            assert hasattr(ImpactVision, name), f"missing SDK method: {name}"
