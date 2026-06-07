"""Tests for the ESG toolbox integration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.impact.toolbox import (
    build_esg_workflow,
    build_toolbox_input_plan,
    build_toolbox_output_blueprint,
    build_toolbox_workflow_plan,
    build_tool_checklist,
    crosswalk_reported_metrics,
    get_source_profile,
    get_toolbox_tool,
    list_source_profiles,
    list_toolbox_tools,
    search_toolbox_tools,
    source_keyword_coverage,
)
from openharness.impact.toolbox.ingest import extract_landing_tools
from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.esg_toolbox_tool import ESGToolboxInput, ESGToolboxTool


REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO_ROOT / "data" / "raw" / "ohesg_toolbox_snapshot.json"
SOURCE_PROFILE_DIR = REPO_ROOT / "data" / "raw" / "ohesg_toolbox"


def test_toolbox_registry_has_33_ohesg_modules() -> None:
    tools = list_toolbox_tools()

    assert len(tools) == 33
    assert get_toolbox_tool("ghg").title == "GHG Protocol Navigator"
    assert get_toolbox_tool("GHG Protocol").tool_id == "ghg"
    assert {"workflow", "input_plan", "recommend"} <= set(get_toolbox_tool("ghg").supported_actions)


def test_curated_tool_aliases_take_precedence_over_scraped_source_terms() -> None:
    assert get_toolbox_tool("CMRT").tool_id == "conflict-minerals"
    assert get_toolbox_tool("EMRT").tool_id == "conflict-minerals"


def test_ohesg_snapshot_was_scraped_for_all_33_tools() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert snapshot["source"] == "https://tool.ohesg.com/"
    assert snapshot["tool_count"] == 33
    assert len(snapshot["tools"]) == 33
    assert {tool["tool_id"] for tool in snapshot["tools"]} == {tool.tool_id for tool in list_toolbox_tools()}
    assert all(snapshot["pages"][tool["tool_id"]]["url"].startswith("https://tool.ohesg.com/") for tool in snapshot["tools"])


def test_ohesg_source_profiles_are_split_into_33_files() -> None:
    files = sorted(SOURCE_PROFILE_DIR.glob("*.json"))
    profiles = list_source_profiles()

    assert len(files) == 33
    assert len(profiles) == 33
    assert {path.stem for path in files} == {tool.tool_id for tool in list_toolbox_tools()}
    for profile in profiles:
        assert profile.url == f"https://tool.ohesg.com/{profile.tool_id}/"
        assert profile.source_title
        assert profile.source_description
        assert len(profile.keywords) >= 10


def test_registry_matches_scraped_ohesg_landing_cards() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    scraped_by_id = {tool["tool_id"]: tool for tool in snapshot["tools"]}

    for tool in list_toolbox_tools():
        scraped = scraped_by_id[tool.tool_id]
        assert tool.url == f"https://tool.ohesg.com{scraped['url']}"
        assert tool.categories == scraped["categories"]
        assert any(source.url == tool.url and source.publisher == "ohESG" for source in tool.sources)
        assert tool.source_title == scraped["title"]
        assert tool.source_description == scraped["description"]
        assert tool.source_tags == scraped["tags"]
        profile = get_source_profile(tool.tool_id)
        assert profile is not None
        assert profile.source_title == scraped["title"]
        assert profile.source_description == scraped["description"]
        assert profile.source_tags == scraped["tags"]


def test_landing_tools_parser_handles_nested_tag_objects() -> None:
    html = """
    <script>
      const TOOLS = [
        { id: 'x', title: '工具X', desc: '说明', url: '/x/', icon: 'book',
          categories: ['carbon'], tags: [{n:'碳核算',c:'tag-carbon'},{n:'温室气体',c:'tag-carbon'}] },
        { id: 'y', title: '工具Y', desc: '说明2', url: '/y/',
          categories: ['rating','supplier'], tags: [{n:'ESG评级',c:'tag-rating'}] },
      ];
    </script>
    """

    tools = extract_landing_tools(html)

    assert [tool.tool_id for tool in tools] == ["x", "y"]
    assert tools[0].tags == ["碳核算", "温室气体"]
    assert tools[1].categories == ["rating", "supplier"]


def test_all_toolbox_modules_meet_production_plan_contract() -> None:
    for tool in list_toolbox_tools():
        assert tool.url == f"https://tool.ohesg.com/{tool.tool_id}/"
        assert len(tool.requirements) >= 5
        assert len(build_tool_checklist(tool)) == len(tool.requirements)
        assert len(tool.sources) >= 2
        assert any(source.publisher == "ohESG" for source in tool.sources)
        assert any(source.publisher != "ohESG" for source in tool.sources)
        assert tool.methods, tool.tool_id
        assert {"get", "search", "checklist", "assess", "methodology", "crosswalk", "source_profile"} <= set(tool.supported_actions)
        for requirement in tool.requirements:
            assert requirement.title
            assert requirement.keywords
            assert requirement.evidence_examples


def test_all_toolbox_modules_have_non_empty_methodology_metadata() -> None:
    for tool in list_toolbox_tools():
        assert all(method.id and method.name and method.inputs and method.outputs for method in tool.methods)
        assert all(source.url.startswith("https://") for source in tool.sources)


def test_toolbox_category_counts_match_ohesg_landing_page() -> None:
    assert len(list_toolbox_tools("disclosure")) == 10
    assert len(list_toolbox_tools("rating")) == 9
    assert len(list_toolbox_tools("export")) == 9
    assert len(list_toolbox_tools("supplier")) == 8
    assert len(list_toolbox_tools("carbon")) == 8


def test_ghg_module_is_complete_for_first_slice() -> None:
    ghg = get_toolbox_tool("ghg")

    assert ghg.url == "https://tool.ohesg.com/ghg/"
    assert "carbon" in ghg.categories
    assert any("ghgprotocol.org" in source.url for source in ghg.sources)
    assert len(ghg.requirements) >= 3
    assert {q.requirement_id for q in build_tool_checklist(ghg)} >= {"boundary", "activity-data", "assurance"}


def test_carbon_calculator_module_is_complete_for_second_slice() -> None:
    calculator = get_toolbox_tool("carbon-calculator")

    assert calculator.url == "https://tool.ohesg.com/carbon-calculator/"
    assert calculator.sectors == ["manufacturing"]
    assert any("iso.org/standard/66453.html" in source.url for source in calculator.sources)
    assert any("ghgprotocol.org/corporate-standard" in source.url for source in calculator.sources)
    assert {method.id for method in calculator.methods} >= {
        "activity-factor",
        "stationary-combustion-energy",
        "fugitive-gwp",
        "scope2-location-market",
    }
    assert {q.requirement_id for q in build_tool_checklist(calculator)} >= {
        "scope1-categories",
        "scope2-dual-reporting",
        "scope3-manufacturing",
        "results-intensity-trend",
    }


def test_carbon_iso_module_is_complete_for_third_slice() -> None:
    carbon_iso = get_toolbox_tool("carbon-iso")

    assert carbon_iso.url == "https://tool.ohesg.com/carbon-iso/"
    assert "carbon" in carbon_iso.categories
    assert any("iso.org/standard/66453.html" in source.url for source in carbon_iso.sources)
    assert any("iso.org/standard/71206.html" in source.url for source in carbon_iso.sources)
    assert {method.id for method in carbon_iso.methods} >= {
        "iso-standard-selector",
        "iso-14064-1-six-step-inventory",
        "iso-14067-seven-step-cfp",
        "iso-14091-risk-logic",
    }
    assert {q.requirement_id for q in build_tool_checklist(carbon_iso)} >= {
        "standard-selection",
        "iso-14064-1-inventory",
        "iso-14067-product-cfp",
        "iso-14068-neutrality",
        "iso-14090-adaptation",
    }


def test_sbti_module_is_complete_for_fourth_slice() -> None:
    sbti = get_toolbox_tool("sbti")

    assert sbti.url == "https://tool.ohesg.com/sbti/"
    assert "carbon" in sbti.categories
    assert any("sciencebasedtargets.org/resources" in source.url for source in sbti.sources)
    assert any("sciencebasedtargets.org/net-zero" in source.url for source in sbti.sources)
    assert {method.id for method in sbti.methods} >= {
        "sbti-six-decision-roadmap",
        "sbti-threshold-screen",
        "sbti-sector-matrix",
        "sbti-five-year-review",
    }
    assert {q.requirement_id for q in build_tool_checklist(sbti)} >= {
        "sbti-target-boundary",
        "sbti-near-term-ambition",
        "sbti-net-zero-ambition",
        "sbti-scope3-supplier",
        "sbti-sector-route",
        "sbti-validation-review",
    }


def test_remaining_toolbox_modules_have_specific_completion_requirements() -> None:
    expected = {
        "material": {"impacts-risks-opportunities", "impact-materiality", "financial-materiality"},
        "msci": {"industry-key-issues", "risk-exposure-management", "data-source-reconciliation"},
        "ecovadis": {"environment", "labor-human-rights", "document-validity"},
        "cdp": {"questionnaire-scope", "environmental-targets", "verification-and-risk"},
        "csa": {"industry-questionnaire", "public-disclosure-alignment", "topic-performance-evidence"},
        "gri": {"term-normalization", "framework-routing", "industry-topic-context"},
        "esrs": {"term-normalization", "framework-routing", "industry-topic-context"},
        "iss": {"rating-topic-map", "controversy-response", "issuer-data-review"},
        "cbam-export": {"cn-code-screen", "installation-data-route", "applicability"},
        "cbam-steel": {"steel-aluminum-route", "embedded-emissions-calculation", "technical-data"},
        "cbam": {"transition-period-reporting", "certificate-cost-prep", "applicability"},
        "glossary": {"term-normalization", "framework-routing", "industry-topic-context"},
        "smeta": {"labor-standards", "health-safety-site", "audit-capa"},
        "sa8000": {"labor-performance-criteria", "social-performance-team", "certification-audit-readiness"},
        "aa1000": {"accountability-principles", "assurance-engagement-type", "assurance-scope"},
        "eu-green-deal": {"regulation-router", "timeline-and-clause-map", "applicability"},
        "battery": {"battery-classification", "battery-dpp-fields", "technical-data"},
        "eudr": {"commodity-product-screen", "geolocation-traceability", "dds-risk-mitigation"},
        "csddd": {"risk-based-hrdd", "grievance-remedy", "supplier-self-check"},
        "espr": {"product-category-router", "dpp-data-model", "technical-data"},
        "amfori-bsci": {"performance-area-map", "audit-rating-capa", "policies"},
        "rba": {"code-section-readiness", "vap-score-prep", "minerals-forced-labor"},
        "icma": {"bond-type-decision", "external-review-reporting", "eligible-projects-kpis"},
        "issb": {"ifrs-s1-core-content", "ifrs-s2-climate", "sasb-industry-crosswalk"},
        "climate-bonds": {"taxonomy-screen", "certification-verifier", "allocation-impact-reporting"},
        "nav": {"institution-role-router", "jurisdiction-sector-filter", "source-authority-check"},
        "aws": {"aws-five-steps", "catchment-context", "water-stewardship-plan"},
        "irma": {"irma-principles-chapters", "mine-site-evidence", "chain-of-custody"},
        "conflict-minerals": {"oecd-five-step", "rmi-template-control", "regulation-scope"},
        "ghg": {"boundary", "scope3-screening", "calculation-tools"},
    }

    for tool_id, requirement_ids in expected.items():
        actual = {req.id for req in get_toolbox_tool(tool_id).requirements}
        assert requirement_ids <= actual, tool_id


def test_embedded_ohesg_page_data_modules_have_page_specific_requirements() -> None:
    expected = {
        "csa": {"industry-weighting-map"},
        "gri": {"multi-source-filter"},
        "iss": {"corporate-assessment-methodology"},
        "aws": {"certification-level-route"},
        "ghg": {"china-grid-factor-route", "eight-step-inventory-path"},
    }

    for tool_id, requirement_ids in expected.items():
        actual = {req.id for req in get_toolbox_tool(tool_id).requirements}
        assert requirement_ids <= actual, tool_id


def test_runtime_terms_cover_core_source_profile_keywords() -> None:
    for tool in list_toolbox_tools():
        runtime_terms = [
            tool.title,
            tool.description,
            *tool.tags,
            *tool.aliases,
            *(req.title for req in tool.requirements),
            *(req.description for req in tool.requirements),
            *(keyword for req in tool.requirements for keyword in req.keywords),
        ]
        coverage = source_keyword_coverage(tool.tool_id, runtime_terms)
        profile = get_source_profile(tool.tool_id)
        assert profile is not None
        assert tool.source_title == profile.source_title
        assert set(tool.source_tags) <= set(profile.source_tags)
        # Source profiles contain noisy page chrome; require a minimum semantic
        # overlap with runtime product metadata.
        assert len(coverage["matched"]) >= 5, tool.tool_id


def test_toolbox_search_finds_cbam_and_ghg() -> None:
    scope_matches = [tool.tool_id for tool in search_toolbox_tools("Scope 1 Scope 2")]
    assert "ghg" in scope_matches
    assert "carbon-calculator" in scope_matches
    cbam_ids = {tool.tool_id for tool in search_toolbox_tools("CBAM")}
    assert {"cbam", "cbam-export", "cbam-steel"} <= cbam_ids


def test_toolbox_search_supports_english_user_queries() -> None:
    examples = {
        "battery passport": "battery",
        "deforestation due diligence": "eudr",
        "water stewardship": "aws",
        "responsible mining": "irma",
        "sustainable bond": "icma",
        "conflict minerals smelter": "conflict-minerals",
        "science based targets": "sbti",
    }

    for query, expected_tool_id in examples.items():
        result_ids = [tool.tool_id for tool in search_toolbox_tools(query)[:8]]
        assert expected_tool_id in result_ids, query
        if query in {"battery passport", "deforestation due diligence", "sustainable bond", "conflict minerals smelter", "science based targets"}:
            assert result_ids[0] == expected_tool_id, query


def test_toolbox_workflow_routes_carbon_module_to_existing_impact_tools() -> None:
    plan = build_toolbox_workflow_plan(
        "ghg",
        company_description="Manufacturer with Scope 1 and Scope 2 data for EU customers.",
        sector="manufacturing",
        jurisdiction="EU",
        reported_metrics={"OI4112": "1200 tCO2e", "OI6697": "2600 MWh"},
    )

    impact_tools = {rec.impact_tool for rec in plan.improves_impact_tools}
    assert {"gap_analysis", "evidence_review", "impact_report", "emission_factors", "climate_scenario_risk"} <= impact_tools
    assert plan.input_plan.completion_pct >= 80
    assert "Scope 1/2/3 coverage matrix" in plan.output_blueprint.widgets


def test_esg_workflow_can_filter_recommendations_by_category() -> None:
    workflow = build_esg_workflow(
        company_description="Battery exporter with supplier audits and EU customer requests.",
        jurisdiction="EU",
        product_code="850760",
        supplier_profile="Tier 1 supplier audit records and CAPA logs.",
        category="export",
        limit=10,
        include_low_score=True,
    )

    assert workflow.recommended_tools
    assert all("export" in item.categories for item in workflow.recommended_tools)


def test_toolbox_workflow_routes_supplier_export_modules_to_product_and_hrdd_tools() -> None:
    battery_plan = build_toolbox_workflow_plan(
        "battery",
        company_description="Battery manufacturer selling products into the EU.",
        jurisdiction="EU",
        product_code="850760",
    )
    csddd_plan = build_toolbox_workflow_plan(
        "csddd",
        company_description="Company has factories, suppliers, worker policies, grievance process, and audit records.",
        supplier_profile="Tier 1 factories with audit and CAPA records.",
    )

    assert "product_passport" in {rec.impact_tool for rec in battery_plan.improves_impact_tools}
    assert "regulatory_calendar" in {rec.impact_tool for rec in battery_plan.improves_impact_tools}
    assert "hrdd_assess" in {rec.impact_tool for rec in csddd_plan.improves_impact_tools}
    assert "investee_portal" in {rec.impact_tool for rec in csddd_plan.improves_impact_tools}


def test_toolbox_input_plan_minimizes_questions_from_document_context() -> None:
    plan = build_toolbox_input_plan(
        "cbam",
        document_text="Steel exporter to EU with CN code 7208 and embedded emissions data.",
        reported_metrics={"OI4112": "900 tCO2e"},
    )

    statuses = {field.field: field.status for field in plan.minimum_fields}
    assert statuses["company_description"] == "inferable"
    assert statuses["sector"] == "inferable"
    assert statuses["jurisdiction"] == "inferable"
    assert statuses["product_code"] == "inferable"
    assert plan.completion_pct >= 80
    assert len(plan.next_questions) <= 1


def test_toolbox_output_blueprint_is_category_specific() -> None:
    disclosure = build_toolbox_output_blueprint("issb")
    supplier = build_toolbox_output_blueprint("smeta")

    assert disclosure.primary_view == "Disclosure gap and crosswalk workspace"
    assert "framework crosswalk" in disclosure.widgets
    assert supplier.primary_view == "Supplier ESG audit workspace"
    assert "CAPA tracker" in supplier.widgets


@pytest.mark.asyncio
async def test_esg_toolbox_tool_assesses_ghg_readiness() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(
            action="assess",
            tool_id="ghg",
            company_description="Manufacturing company with Scope 1 and Scope 2 GHG inventory.",
            document_text="The company defines an operational control boundary and uses fuel invoices, electricity bills, emission factors, and calculation QA review.",
            reported_metrics={"OI4112": "1200 tCO2e"},
        ),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    assert not result.is_error
    assert result.metadata["tool_id"] == "ghg"
    assert result.metadata["score_pct"] >= 67
    assert "https://tool.ohesg.com/ghg/" in result.output


@pytest.mark.asyncio
async def test_esg_toolbox_tool_assesses_carbon_calculator_readiness() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(
            action="assess",
            tool_id="carbon-calculator",
            company_description="Manufacturing company preparing ISO 14064-1 GHG inventory.",
            document_text=(
                "The inventory boundary uses operational control. Scope 1 includes stationary combustion, "
                "mobile combustion, process emissions, and refrigerant fugitive emissions. Scope 2 includes "
                "purchased electricity with location-based and market-based calculations plus renewable "
                "energy certificates. Scope 3 screens purchased goods, transport, waste, and T&D losses. "
                "The report has scope totals, carbon footprint intensity, three years of trend data, and "
                "calculation review."
            ),
            reported_metrics={"OI4112": "1800 tCO2e", "OI6697": "2600 MWh"},
        ),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    assert not result.is_error
    assert result.metadata["tool_id"] == "carbon-calculator"
    assert result.metadata["score_pct"] >= 80
    assert "https://tool.ohesg.com/carbon-calculator/" in result.output


@pytest.mark.asyncio
async def test_esg_toolbox_tool_assesses_carbon_iso_readiness() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(
            action="assess",
            tool_id="carbon-iso",
            company_description="Exporter needs ISO 14067 product carbon footprint and ISO 14064-1 organization inventory support.",
            document_text=(
                "The team completed a standard selector decision log. The ISO 14064-1 inventory has an "
                "organization boundary, reporting boundary, six categories, base year, quality management, "
                "and verification file. The ISO 14067 CFP defines functional unit, declared unit, system "
                "boundary, allocation, primary data, secondary data, and critical review. A carbon neutrality "
                "claim under ISO 14068 will follow reduction first, transition plan, carbon credit due diligence, "
                "and public reporting. Climate adaptation work uses ISO 14090 and ISO 14091 with exposure, "
                "sensitivity, adaptive capacity, vulnerability, climate risk register, and monitoring."
            ),
            reported_metrics={"OI4112": "1800 tCO2e", "OI6697": "2600 MWh"},
        ),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    assert not result.is_error
    assert result.metadata["tool_id"] == "carbon-iso"
    assert result.metadata["score_pct"] >= 80
    assert "https://tool.ohesg.com/carbon-iso/" in result.output


@pytest.mark.asyncio
async def test_esg_toolbox_tool_assesses_sbti_readiness() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(
            action="assess",
            tool_id="sbti",
            sector="steel manufacturing",
            company_description="Company preparing SBTi near-term and net-zero targets.",
            document_text=(
                "The company has a base year GHG inventory with Scope 1, Scope 2, and Scope 3 target boundary. "
                "Near-term criteria are checked for 5-10 years, ambition, coverage, absolute contraction, and "
                "SDA. The net-zero standard analysis covers long-term target, residual emissions, neutralization, "
                "abatement, value chain and 2050. Scope 3 supplier engagement includes procurement category "
                "emissions screening, supplier targets, data strategy, and tracking. The steel sector route "
                "is documented with SBTi sector guidance. Validation submission, commitment status, approved "
                "target tracking, and five-year review calendar are owned."
            ),
            reported_metrics={"OI4112": "1800 tCO2e", "OI6697": "2600 MWh"},
        ),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    assert not result.is_error
    assert result.metadata["tool_id"] == "sbti"
    assert result.metadata["score_pct"] >= 80
    assert "https://tool.ohesg.com/sbti/" in result.output


@pytest.mark.asyncio
async def test_esg_toolbox_methodology_includes_carbon_calculator_methods() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(action="methodology", tool_id="carbon-calculator", output_format="json"),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    method_ids = {method["id"] for method in result.metadata["methods"]}
    assert {"activity-factor", "scope2-location-market"} <= method_ids


@pytest.mark.asyncio
async def test_esg_toolbox_methodology_includes_carbon_iso_methods() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(action="methodology", tool_id="carbon-iso", output_format="json"),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    method_ids = {method["id"] for method in result.metadata["methods"]}
    assert {"iso-standard-selector", "iso-14067-seven-step-cfp"} <= method_ids


@pytest.mark.asyncio
async def test_esg_toolbox_methodology_includes_sbti_methods() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(action="methodology", tool_id="sbti", output_format="json"),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    method_ids = {method["id"] for method in result.metadata["methods"]}
    assert {"sbti-six-decision-roadmap", "sbti-five-year-review"} <= method_ids


@pytest.mark.asyncio
async def test_esg_toolbox_source_profile_exposes_scraped_page_terms() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(action="source_profile", tool_id="ghg"),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    assert not result.is_error
    assert result.metadata["tool_id"] == "ghg"
    assert result.metadata["embedded_data_keys"] == ["__GHG_DATA"]
    assert "GHG Protocol" in result.output
    assert "Impact Vision title: GHG Protocol Navigator" in result.output
    assert "Impact Vision description:" in result.output
    assert "Top source keywords" in result.output


@pytest.mark.asyncio
async def test_esg_toolbox_tool_returns_workflow_plan() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(
            action="workflow",
            tool_id="battery",
            company_description="Battery manufacturer selling into the EU.",
            jurisdiction="EU",
            product_code="850760",
            output_format="json",
        ),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    assert not result.is_error
    assert result.metadata["tool_id"] == "battery"
    impact_tools = {rec["impact_tool"] for rec in result.metadata["improves_impact_tools"]}
    assert {"product_passport", "regulatory_calendar"} <= impact_tools
    assert result.metadata["output_blueprint"]["primary_view"] == "Export compliance applicability workspace"


@pytest.mark.asyncio
async def test_esg_toolbox_tool_returns_minimal_input_plan() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(
            action="input_plan",
            tool_id="ghg",
            company_description="Manufacturing company with GHG inventory.",
            sector="Manufacturing",
            jurisdiction="EU",
            reported_metrics={"OI4112": "1200 tCO2e"},
            output_format="json",
        ),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    assert not result.is_error
    assert result.metadata["completion_pct"] >= 75
    assert any(step.startswith("Parse GHG inventory") for step in result.metadata["ai_assist_steps"])


@pytest.mark.asyncio
async def test_esg_toolbox_recommend_uses_plain_english_query() -> None:
    tool = ESGToolboxTool()
    result = await tool.execute(
        ESGToolboxInput(
            action="recommend",
            query="battery passport export carbon footprint",
            output_format="json",
        ),
        ToolExecutionContext(cwd=__import__("pathlib").Path.cwd()),
    )

    assert not result.is_error
    tool_ids = [item["tool_id"] for item in result.metadata["recommended_tools"][:5]]
    assert "battery" in tool_ids
    assert result.metadata["ui"]["cards"]


@pytest.mark.asyncio
async def test_esg_toolbox_api_rejects_invalid_action_cleanly() -> None:
    from fastapi import HTTPException

    from openharness.api_gateway.router import ESGToolboxRequest, esg_toolbox_endpoint

    with pytest.raises(HTTPException) as exc_info:
        await esg_toolbox_endpoint(ESGToolboxRequest(action="bad-action"))

    assert exc_info.value.status_code == 400
    assert "action" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_esg_toolbox_mcp_rejects_invalid_action_cleanly() -> None:
    from openharness.impact.mcp_server import esg_toolbox

    output = await esg_toolbox(action="bad-action")

    assert "Invalid ESG toolbox input" in output
    assert "action" in output


def test_ghg_crosswalk_maps_impact_metric_to_framework_uses() -> None:
    mappings = crosswalk_reported_metrics({"OI4112": "1200 tCO2e"}, tool_id="ghg")

    assert "OI4112" in mappings
    assert any("GHG" in item for item in mappings["OI4112"])


def test_carbon_calculator_crosswalk_maps_energy_metric() -> None:
    mappings = crosswalk_reported_metrics({"OI6697": "2600 MWh"}, tool_id="carbon-calculator")

    assert "OI6697" in mappings
    assert any("Scope 2" in item for item in mappings["OI6697"])


def test_default_tool_registry_registers_esg_toolbox() -> None:
    registry = create_default_tool_registry()

    assert registry.get("esg_toolbox") is not None


@pytest.mark.asyncio
async def test_mcp_esg_toolbox_wrapper_recommends_modules() -> None:
    from openharness.impact.mcp_server import esg_toolbox

    output = await esg_toolbox(
        action="recommend",
        company_description="Battery manufacturer exporting to EU with Scope 1 and Scope 2 data.",
        sector="battery manufacturing",
        jurisdiction="EU",
        country="EU",
        product_code="850760",
        reported_metrics={"OI4112": "1200 tCO2e"},
    )

    assert "Recommended ESG toolbox modules" in output
    assert "battery" in output or "cbam" in output
