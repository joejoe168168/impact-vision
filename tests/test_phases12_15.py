"""Regression tests for Phases 12-15 (fund workflow, frameworks, AI, platform)."""
from __future__ import annotations

import pytest

from openharness.impact.counterfactual import (
    CounterfactualInput,
    estimate_counterfactual,
)
from openharness.impact.extractors import (
    HeuristicVerifier,
    NoopExtractor,
    NoopVerifier,
    RegexExtractor,
    get_extractor,
    get_verifier,
)
from openharness.impact.frameworks import (
    EconomicActivity,
    FinancedEmissionsInput,
    SBTiClaim,
    TNFDInput,
    assess_taxonomy_alignment,
    assess_tnfd,
    check_sbti_alignment,
    parse_cdp_responses,
    rollup_pcaf,
)
from openharness.impact.ic_memo import render_ic_memo_markdown
from openharness.impact.models import Company
from openharness.impact.plugins import discover_plugins
from openharness.impact.signed_feed import HMACSigner, ReportFeed
from openharness.impact.sdk import ImpactVision
from openharness.impact.tenancy import (
    BUILTIN_ROLES,
    InMemoryRBACStore,
    PERM_DEAL_WRITE,
    PERM_REPORT_PUBLISH_LP,
    RBACPolicy,
    bootstrap_tenant,
)
from openharness.impact.toc_graph import build_simple_chain, render_mermaid


# ---------------------------------------------------------------------------
# Phase 12 — Fund workflow
# ---------------------------------------------------------------------------

class TestSDKFundWorkflow:
    def test_sdk_assess_evaluate_render(self):
        iv = ImpactVision()
        c = Company(
            name="Demo Co", sector="energy", country="KE",
            description="Off-grid solar provider",
            impact_themes=["climate"],
        )
        a = iv.assess_company(c)
        assert a.five_dimensions is not None
        assert len(a.sdg_alignments) >= 1

        thesis = iv.load_thesis()
        sc = iv.evaluate_deal_against_thesis(a, thesis=thesis)
        assert sc.overall_status in {"pass", "warn", "fail"}

        memo = iv.render_ic_memo(a, thesis=thesis, scorecard=sc)
        assert memo.startswith("# Investment Committee Memo")
        # IC gate detail must appear
        assert "IC Gate Detail" in memo

    def test_lp_calendar_is_populated(self):
        iv = ImpactVision()
        cal = iv.build_lp_calendar(thesis=iv.load_thesis(), horizon_months=12)
        assert len(cal.items) > 0


# ---------------------------------------------------------------------------
# Phase 13 — Frameworks
# ---------------------------------------------------------------------------

class TestPCAF:
    def test_basic_rollup(self):
        entries = [
            FinancedEmissionsInput(
                company_name="A", asset_class="listed_equity",
                outstanding_investment_eur=10_000_000,
                enterprise_value_eur=100_000_000,
                reported_emissions_tco2e=5_000,
                sector="manufacturing",
            ),
            FinancedEmissionsInput(
                company_name="B", asset_class="business_loans",
                outstanding_investment_eur=5_000_000,
                enterprise_value_eur=20_000_000,
                company_revenue_eur=30_000_000,
                sector="energy",
            ),
        ]
        r = rollup_pcaf(entries)
        assert r.company_count == 2
        assert r.total_financed_emissions_tco2e > 0
        assert r.coverage_pct == 50.0
        # B should have its DQS bumped to 4 (estimated emissions)
        b_result = next(e for e in r.entries if e.company_name == "B")
        assert b_result.data_quality_score >= 4


class TestSBTi:
    def test_aligned_target(self):
        claim = SBTiClaim(
            company_name="GreenCo",
            base_year=2020, target_year_near_term=2030,
            near_term_pct_reduction=50.0,
            target_year_net_zero=2045, net_zero_pct_reduction=95.0,
            scope3_covered=True, scope3_pct_of_inventory=60.0,
        )
        result = check_sbti_alignment(claim)
        assert result.overall_alignment == "aligned"
        assert result.near_term_pass and result.net_zero_pass

    def test_below_15c_pathway(self):
        claim = SBTiClaim(
            company_name="LaggardCo",
            base_year=2020, target_year_near_term=2030,
            near_term_pct_reduction=20.0,
        )
        result = check_sbti_alignment(claim)
        assert result.near_term_pass is False
        assert result.overall_alignment != "aligned"


class TestEUTaxonomy:
    def test_alignment_with_dnsh(self):
        activities = [
            EconomicActivity(
                name="Solar PV", nace_code="D35.11",
                revenue_share_pct=80, capex_share_pct=70,
                primary_objective="climate_mitigation",
                eligible=True, substantial_contribution=True,
                dnsh_pass=True, minimum_safeguards=True,
            ),
            EconomicActivity(
                name="Office services",
                revenue_share_pct=20, capex_share_pct=30,
                eligible=False,
            ),
        ]
        r = assess_taxonomy_alignment("Demo Co", activities)
        assert r.revenue_aligned_pct == 80.0
        assert r.revenue_eligible_pct == 80.0


class TestTNFD:
    def test_coverage_calc(self):
        inp = TNFDInput(
            company_name="NatureCo",
            addressed_disclosure_codes=["G.A", "G.B", "S.A", "S.D", "M.A", "M.B", "M.C"],
            leap_locate_done=True,
        )
        r = assess_tnfd(inp)
        assert r.disclosure_count_addressed == 7
        assert "S.D" in r.addressed_codes


class TestCDP:
    def test_climate_intake(self):
        responses = [
            {"question_code": "C1.1", "response": "Yes — board oversight"},
            {"question_code": "C6.1", "response": 12345.6},
            {"question_code": "C6.3", "response": 6789.0},
            {"question_code": "C10.1a", "response": "Limited assurance"},
        ]
        r = parse_cdp_responses("DemoCo", "climate", responses, reporting_year=2024)
        assert r.responses_with_data == 4
        # Several critical codes are still missing
        assert "C2.1a" in r.missing_critical


# ---------------------------------------------------------------------------
# Phase 14 — AI / extractors
# ---------------------------------------------------------------------------

class TestExtractors:
    def test_registry_lookup(self):
        assert isinstance(get_extractor("regex"), RegexExtractor)
        assert isinstance(get_verifier("heuristic"), HeuristicVerifier)
        assert isinstance(get_extractor("noop"), NoopExtractor)
        assert isinstance(get_verifier("noop"), NoopVerifier)
        with pytest.raises(KeyError):
            get_extractor("does-not-exist")

    def test_regex_extractor_finds_outcome_and_certification(self):
        text = "In 2024 we enrolled 3,500 students. Our org is B-Corp certified."
        claims = RegexExtractor().extract(text)
        cats = {c.category for c in claims}
        assert "outcome" in cats
        assert "certification" in cats

    def test_heuristic_verifier_validates_outcome_with_assurance(self):
        from openharness.impact.extractors import ExtractedClaim
        c = ExtractedClaim(
            text="3,500 students enrolled, audited by Deloitte",
            category="outcome", metric_value=3500.0, metric_unit="students",
            metric_year=2024, raw_extractor_id="t",
        )
        r = HeuristicVerifier().verify(c)
        assert r.verified is True


class TestToCGraph:
    def test_mermaid_render(self):
        g = build_simple_chain("Off-grid solar", [
            ("input", "EUR 5M"),
            ("activity", "Deploy 50k kits"),
            ("output", "50k connected"),
            ("outcome", "kerosene reduction"),
            ("impact", "SDG 7 / SDG 13"),
        ])
        body = render_mermaid(g)
        assert body.startswith("flowchart")
        assert "N0 --> N1" in body
        assert "N3 --> N4" in body


class TestCounterfactual:
    def test_investor_additionality_frontier(self):
        inp = CounterfactualInput(
            type="investor", market_maturity="frontier",
            alternative_capital_available=False,
            target_outcome_value=100.0, target_outcome_unit="households",
        )
        r = estimate_counterfactual(inp)
        assert r.point_estimate_pct_attributable >= 70
        assert r.net_outcome_value is not None

    def test_beneficiary_additionality_with_substitution(self):
        inp = CounterfactualInput(
            type="beneficiary",
            alternative_provider_share_pct=70.0,
        )
        r = estimate_counterfactual(inp)
        assert 25 <= r.point_estimate_pct_attributable <= 35


# ---------------------------------------------------------------------------
# Phase 15 — Platform
# ---------------------------------------------------------------------------

class TestRBAC:
    def test_admin_can_publish_lp_report(self):
        store = InMemoryRBACStore()
        tenant, admin = bootstrap_tenant(store, "Acme Capital", "admin@acme.test")
        policy = RBACPolicy(store)
        d = policy.is_allowed(admin.id, PERM_REPORT_PUBLISH_LP, resource_tenant_id=tenant.id)
        assert d.allowed

    def test_cross_tenant_denied(self):
        store = InMemoryRBACStore()
        tenant_a, admin_a = bootstrap_tenant(store, "A Capital", "a@a.test")
        bootstrap_tenant(store, "B Capital", "b@b.test")
        policy = RBACPolicy(store)
        d = policy.is_allowed(admin_a.id, PERM_DEAL_WRITE, resource_tenant_id="not-the-right-tenant")
        assert not d.allowed
        assert "Cross-tenant" in d.reason

    def test_builtin_roles_have_known_perms(self):
        assert PERM_DEAL_WRITE in BUILTIN_ROLES["analyst"]
        assert PERM_REPORT_PUBLISH_LP in BUILTIN_ROLES["lp_relations"]


class TestPlugins:
    def test_discover_does_not_raise_with_no_plugins(self):
        report = discover_plugins()
        assert report.failed == []


class TestSignedFeed:
    def test_chain_verifies_then_breaks_on_tamper(self):
        signer = HMACSigner(key=b"k")
        feed = ReportFeed(tenant_id="acme", fund_id="fund-i")
        feed.append(signer, "ilpa_esg", "2025-Q4", {"aum": 150})
        feed.append(signer, "sfdr_pai", "2025", {"pai": 1234})
        ok, problems = feed.verify(signer)
        assert ok and problems == []

        feed.reports[0].payload["aum"] = 999
        ok2, problems2 = feed.verify(signer)
        assert not ok2 and any("content_hash" in p for p in problems2)

    def test_wrong_signer_rejected(self):
        from openharness.impact.signed_feed import export_chain, import_chain
        real = HMACSigner(key=b"real")
        fake = HMACSigner(key=b"fake")
        feed = ReportFeed(tenant_id="t", fund_id="f")
        feed.append(real, "ilpa_esg", "2025", {"x": 1})
        # Round-trip export/import preserves the chain
        feed2 = import_chain(export_chain(feed))
        ok, _ = feed2.verify(real)
        assert ok
        # But the wrong signer cannot validate
        ok_wrong, probs = feed2.verify(fake)
        assert not ok_wrong
        assert any("signature invalid" in p for p in probs)


# ---------------------------------------------------------------------------
# Additional bug-hunt / edge cases surfaced during v0.11 review
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_pcaf_zero_input(self):
        from openharness.impact.frameworks.pcaf import rollup_pcaf
        r = rollup_pcaf([])
        assert r.company_count == 0
        assert r.total_financed_emissions_tco2e == 0.0

    def test_pcaf_no_emissions_and_no_revenue_is_flagged(self):
        from openharness.impact.frameworks.pcaf import (
            FinancedEmissionsInput, rollup_pcaf,
        )
        r = rollup_pcaf([FinancedEmissionsInput(
            company_name="X", asset_class="business_loans",
            outstanding_investment_eur=1_000_000,
            enterprise_value_eur=10_000_000,
        )])
        assert r.total_financed_emissions_tco2e == 0.0
        assert r.entries[0].notes  # should carry a follow-up flag

    def test_sbti_insufficient_data(self):
        from openharness.impact.frameworks.sbti import (
            SBTiClaim, check_sbti_alignment,
        )
        r = check_sbti_alignment(SBTiClaim(company_name="Empty"))
        assert r.overall_alignment == "insufficient_data"

    def test_eu_taxonomy_empty_activities_reports_zero_alignment(self):
        r = assess_taxonomy_alignment("Y", [])
        assert r.revenue_aligned_pct == 0.0
        assert any("No EU Taxonomy-eligible" in f for f in r.findings)

    def test_tnfd_empty_input_leap_all_todo(self):
        r = assess_tnfd(TNFDInput(company_name="N"))
        assert r.coverage_pct == 0.0
        assert all(v == "todo" for v in r.leap_progress.values())

    def test_cdp_skips_rows_without_question_code(self):
        r = parse_cdp_responses("Z", "climate", [
            {"response": "orphan — no code"},
            {"question_code": "C1.1", "response": "board oversight"},
        ])
        assert r.responses_total == 1

    def test_extractor_handles_empty_and_none_text(self):
        ex = get_extractor("regex")
        assert ex.extract("") == []
        assert ex.extract(None) == []  # guards against None for defensive callers

    def test_rbac_inactive_user_denied(self):
        from openharness.impact.tenancy import User
        store = InMemoryRBACStore()
        tenant, admin = bootstrap_tenant(store, "ACo", "a@a.test")
        store.upsert_user(User(
            id="u2", tenant_id=tenant.id, email="u2@a.test",
            role_names=["analyst"], is_active=False,
        ))
        p = RBACPolicy(store)
        d = p.is_allowed("u2", PERM_DEAL_WRITE, resource_tenant_id=tenant.id)
        assert not d.allowed
        assert "inactive" in d.reason.lower()

    def test_rbac_role_with_unknown_perm_rejected_at_construction(self):
        from openharness.impact.tenancy import Role
        with pytest.raises(ValueError):
            Role(name="bad", permissions=["not-a-real-permission"])

    def test_rbac_require_raises_permission_error(self):
        store = InMemoryRBACStore()
        policy = RBACPolicy(store)
        with pytest.raises(PermissionError):
            policy.require("nonexistent", PERM_DEAL_WRITE)

    def test_ic_memo_handles_missing_5d(self):
        from openharness.impact.deal_gate import evaluate_deal
        from openharness.impact.fund_thesis import FundThesis
        from openharness.impact.models import Assessment, Company

        a = Assessment(
            company=Company(name="Ghost", sector=""),
            assessed_at="2026-04-21",
            sdg_alignments=[],
            five_dimensions=None,
        )
        sc = evaluate_deal(a, FundThesis())
        md = render_ic_memo_markdown(a, sc, None)
        assert "Ghost" in md
        assert "No 5D assessment available" in md
