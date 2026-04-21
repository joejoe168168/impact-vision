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


# ---------------------------------------------------------------------------
# v0.12 — HTML report renderers (IC memo + DD coverage)
# ---------------------------------------------------------------------------

class TestHtmlRenderers:
    def test_ic_memo_html_contains_key_sections(self):
        from openharness.impact.ic_memo import render_ic_memo, render_ic_memo_html

        iv = ImpactVision()
        a = iv.assess_company(Company(
            name="Acme Solar", sector="energy", geography="Kenya",
            impact_themes=["climate", "jobs"], sdg_claims=[7, 13],
        ))
        thesis = iv.load_thesis()
        sc = iv.evaluate_deal_against_thesis(
            a, thesis=thesis,
            dd_coverage_pct=62.0, greenwashing_score=28.0,
        )
        html = render_ic_memo_html(
            a, sc, thesis,
            dd_coverage_pct=62.0,
            greenwashing_score=28.0,
            greenwashing_classification="low",
            deal_size_eur_m=5.0,
        )

        assert html.startswith("<!DOCTYPE html>")
        assert "<title>IC Memo — Acme Solar</title>" in html
        assert "<h1>Acme Solar</h1>" in html
        # shared v2 chrome
        assert "kpi-strip" in html
        assert "class=\"toc\"" in html
        # KPI content
        assert "IC Gate" in html
        assert "DD Coverage" in html
        assert "Greenwashing risk" in html
        # Sections
        for anchor in ("thesis-fit", "five-d", "sdg", "dd-gw", "gate", "rec"):
            assert f'id="{anchor}"' in html
        # Deterministic: same call through render_ic_memo("html") matches
        html2 = render_ic_memo(
            a, sc, thesis, output_format="html",
            dd_coverage_pct=62.0,
            greenwashing_score=28.0,
            greenwashing_classification="low",
            deal_size_eur_m=5.0,
        )
        assert html2 == html

    def test_ic_memo_html_path_writes_file(self, tmp_path):
        from openharness.impact.ic_memo import render_ic_memo

        iv = ImpactVision()
        a = iv.assess_company(Company(name="FileCo", sector=""))
        sc = iv.evaluate_deal_against_thesis(a)
        out = tmp_path / "memo.html"
        result = render_ic_memo(a, sc, None, output_format="html", path=str(out))
        assert result == out
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "FileCo" in content

    def test_dd_report_html_contains_key_sections(self):
        iv = ImpactVision()
        pitch = (
            "We train 1000 rural women in Kenya to install solar panels. "
            "An independent RCT measured a 45% income increase vs. control. "
            "We audit supplier labor conditions annually via BSR."
        )
        html = iv.render_dd_report_html(
            pitch,
            company_name="Acme Solar",
            document_label="Pitch deck v3",
        )
        assert html.startswith("<!DOCTYPE html>")
        # New "DD Questionnaire Helper" branding (renamed from DD Coverage).
        assert "<title>DD Questionnaire Helper — Acme Solar</title>" in html
        # shared v2 chrome
        assert "kpi-strip" in html
        assert "class=\"toc\"" in html
        # KPI labels
        assert "Checklist coverage" in html
        assert "Avg evidence level" in html
        assert "High-priority gaps" in html
        # Sections — the questionnaire helper reorganised the page around
        # risks first, then the actionable information request, then the
        # coverage appendix. See dd_report_html.render_dd_questionnaire_html.
        for anchor in (
            "risks", "questionnaire", "evidence-gaps",
            "overview", "categories", "addressed", "legend",
        ):
            assert f'id="{anchor}"' in html

    def test_dd_report_html_empty_text_is_graceful(self):
        iv = ImpactVision()
        html = iv.render_dd_report_html("", company_name="No-Doc Co")
        assert "<!DOCTYPE html>" in html
        # Nothing addressed, so the addressed section shows the empty-state
        # message and every question lands in the unanswered section.
        assert "No checklist questions appear to be addressed" in html
        assert "No-Doc Co" in html

    def test_dd_report_html_writes_file(self, tmp_path):
        iv = ImpactVision()
        out = tmp_path / "dd.html"
        path = iv.render_dd_report_html(
            "We measure outcomes via a baseline survey.",
            company_name="FileCo",
            path=str(out),
        )
        assert path == out
        assert out.exists()
        assert "<!DOCTYPE html>" in out.read_text(encoding="utf-8")

    def test_main_impact_report_html_has_toc_and_anchors(self):
        """The main impact report keeps its TOC sidebar, KPI strip and
        section anchors so the executive summary can navigate to sub-sections.
        """
        from openharness.tools.impact import impact_report_tool as ir

        iv = ImpactVision()
        comp = Company(
            name="Acme Solar", sector="energy", geography="Kenya",
            impact_themes=["climate"], sdg_claims=[7, 13],
        )
        assess = iv.assess_company(comp)
        data = assess.model_dump(mode="json")
        data["generated_at"] = "2026-04-21T00:00:00Z"
        data["catalog_version"] = "IRIS+ 5.3c"
        data["company"] = comp.model_dump(mode="json")
        # Drop sections that require runtime enrichment
        for k in ("gap_analysis", "greenwashing"):
            data.pop(k, None)

        html = ir._to_html(data)
        assert "report-toc" in html
        assert "kpi-strip" in html
        assert 'id="executive-summary"' in html
        assert 'id="sec-5d"' in html

    def test_report_v2_helpers(self):
        from openharness.impact.report_templates import (
            render_footer,
            render_hero,
            render_kpi_strip,
            render_toc,
            sdg_swatch,
            wrap_document,
        )

        hero = render_hero(
            eyebrow="Test", title="Hello",
            subtitle="world", meta=[("Date", "2026-04-21")], tags=["A", "B"],
        )
        assert "report-hero" in hero and "Hello" in hero
        assert "tag" in hero and 'SDG' not in hero

        kpi = render_kpi_strip([
            {"label": "x", "value": "1", "kind": "pass", "badge": "OK", "badge_kind": "pass"},
            {"label": "y", "value": "2", "sub": "detail"},
        ])
        assert "kpi-tile pass" in kpi and "kpi-badge pass" in kpi
        assert "detail" in kpi

        toc = render_toc([("a", "A"), ("b", "B")])
        assert "#a" in toc and "#b" in toc

        foot = render_footer("note here")
        assert "note here" in foot

        swatch = sdg_swatch(7, 88.0)
        assert "SDG 7" in swatch and "88" in swatch

        doc = wrap_document(title="Hello", body_html="<p>ok</p>")
        assert doc.startswith("<!DOCTYPE html>")
        assert "<title>Hello</title>" in doc and "<p>ok</p>" in doc


class TestDDQuestionnaireHelper:
    """Regression coverage for the re-branded DD Questionnaire Helper.

    The helper:
      1. Puts the *information request* (unanswered questions) front-and-centre,
         sorted by priority and DD sequence.
      2. Surfaces a consolidated evidence / document gap list.
      3. Keeps the old coverage table as an appendix.
    """

    PITCH = (
        "We train 2,000 small-holder farmers in Malaysia on regenerative "
        "pig-farming practices. Revenue was US$ 4.5m last year. We track a "
        "few KPIs internally but have no independent verification yet."
    )

    def test_questionnaire_alias_matches_report_html(self):
        iv = ImpactVision()
        a = iv.render_dd_report_html(self.PITCH, company_name="HogCo")
        b = iv.render_dd_questionnaire_html(self.PITCH, company_name="HogCo")
        assert a == b

    def test_questionnaire_sections_are_risk_first(self):
        iv = ImpactVision()
        html = iv.render_dd_questionnaire_html(self.PITCH, company_name="HogCo")
        # Key risk areas MUST appear before the information request,
        # and both must appear before the coverage appendix.
        idx_risks = html.find('id="risks"')
        idx_quest = html.find('id="questionnaire"')
        idx_cover = html.find('id="overview"')
        idx_legnd = html.find('id="legend"')
        assert 0 <= idx_risks < idx_quest < idx_cover < idx_legnd
        # Priority callouts exist in the information request
        assert "Priority 1 — Ask first" in html
        # Evidence-gap consolidated list is present
        assert "Evidence &amp; document gaps" in html
        # Each question card shows a response placeholder ready for editing
        assert "Founder response" in html
        # "Attach / ask for" appears at least once for the sample pitch
        assert "Attach / ask for" in html

    def test_questionnaire_docx_export_roundtrips(self, tmp_path):
        pytest.importorskip("docx")
        iv = ImpactVision()
        out = tmp_path / "dd_questionnaire.docx"
        path = iv.render_dd_questionnaire_docx(
            self.PITCH, out, company_name="HogCo",
            document_label="Founder narrative", reviewer="QA bot",
        )
        assert path == out
        assert out.exists()
        # Word XML content contains our heading + company name
        import zipfile
        with zipfile.ZipFile(out) as zf:
            body = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        assert "DD — Questionnaire Helper" in body or "Questionnaire Helper" in body
        assert "HogCo" in body
        # Priority heading appears only if there are unanswered questions
        # (the sample pitch leaves many blanks, so "Priority 1" must exist)
        assert "Priority 1" in body or "Priority 2" in body
        # Founder response slot and evidence checklist markers present
        assert "Founder response" in body


class TestWebConsole:
    """Smoke-tests for the new web console SPA and router."""

    def test_console_html_contains_tool_list(self):
        from openharness.web.console import render_console_html

        html = render_console_html()
        assert "<!DOCTYPE html>" in html
        assert "Impact Vision" in html
        assert "Web Console" in html
        # A handful of tools that MUST be wired up
        for needle in ("5-Dimension scoring", "SDG alignment map", "Greenwashing screen", "Impact report"):
            assert needle in html
        # Endpoints are inlined so the SPA can fetch without extra config
        for endpoint in ("/api/v1/score", "/api/v1/sdg-map", "/api/v1/report"):
            assert endpoint in html

    def test_console_router_serves_root(self):
        pytest.importorskip("fastapi")
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from openharness.web.console import console_router

        app = FastAPI()
        app.include_router(console_router())
        client = TestClient(app)

        for path in ("/", "/console"):
            r = client.get(path)
            assert r.status_code == 200
            assert "Impact Vision" in r.text
            assert "Web Console" in r.text


class TestWebConsolePhase156:
    """Phase 15.6 — OpenAPI-driven forms & browser-side run history."""

    def test_openapi_walker_is_wired_into_html(self):
        """The SPA must ship the OpenAPI discovery + history JS so analysts
        get auto-forms for every new endpoint and a replayable run history."""
        from openharness.web.console import render_console_html

        html = render_console_html()

        # OpenAPI discovery scaffolding
        assert "discoverFromOpenAPI" in html
        assert "/openapi.json" in html
        assert "extractRequestSchema" in html  # requestBody schema extraction
        assert "resolveRef" in html  # $ref resolution
        assert "schema-badge" in html  # UI marker showing openapi / fallback
        assert "fieldsFromSchema" in html

        # Run-history scaffolding (localStorage-backed)
        assert "HISTORY_KEY" in html
        assert "impact_vision_runs_v1" in html  # cache key
        assert "pushHistory" in html
        assert "renderHistoryList" in html
        assert "replayHistory" in html
        assert "clearHistory" in html
        assert "historyList" in html  # DOM anchor in the sidebar

        # Curated sample data helper still available
        assert "fillSampleData" in html
        assert "Acme Solar" in html

    def test_curated_catalogue_and_recipes_are_exported(self):
        """External plug-ins / tests may want to inspect or extend the
        curated catalogue and field recipes — keep them importable."""
        from openharness.web.console import _FIELD_RECIPES, _TOOL_CATALOGUE

        # 19 endpoints seeded at minimum; grows as the gateway adds routes.
        assert len(_TOOL_CATALOGUE) >= 19
        # Every catalogue entry references a concrete /api/v1 endpoint
        for entry in _TOOL_CATALOGUE:
            assert entry["endpoint"].startswith("/api/v1/")
            assert entry["id"] and entry["label"] and entry["desc"]

        # Field recipes exist for the primary assessment endpoints
        for tool_id in ("score", "sdg-map", "report", "pipeline"):
            assert tool_id in _FIELD_RECIPES
            assert len(_FIELD_RECIPES[tool_id]) >= 1

    def test_console_picks_up_new_fastapi_route_via_openapi(self):
        """Proof that the OpenAPI walker machinery is in place: mount a
        dummy ``/api/v1/demo-echo`` route and confirm it appears in the
        gateway's OpenAPI spec (the JS walker consumes exactly this)."""
        pytest.importorskip("fastapi")
        from fastapi import Body, FastAPI
        from fastapi.testclient import TestClient

        from openharness.web.console import console_router

        app = FastAPI(title="Demo")
        app.include_router(console_router())

        @app.post("/api/v1/demo-echo", summary="Demo Echo",
                  description="Auto-discovered by the web console.")
        async def _demo_echo(
            company_name: str = Body(..., embed=True),
            note: str | None = Body(None, embed=True),
        ) -> dict:
            return {"echoed": company_name, "note": note}

        client = TestClient(app)

        # The console root still serves 200
        assert client.get("/").status_code == 200

        # The OpenAPI schema exposes the new route so the walker can find it
        spec = client.get("/openapi.json").json()
        assert "/api/v1/demo-echo" in spec["paths"]
        post = spec["paths"]["/api/v1/demo-echo"]["post"]
        assert post["summary"] == "Demo Echo"
        # And a request body schema is present (what fieldsFromSchema walks)
        rb = post["requestBody"]["content"]["application/json"]["schema"]
        assert "$ref" in rb or "properties" in rb or "type" in rb
