"""W3.1: REST, MCP and console surfaces generated from the tool registry."""

from __future__ import annotations

import asyncio

import pytest

from openharness.impact import surfaces

DECK = ("SunPath sells pay-as-you-go solar home systems in Kenya. In 2025 we connected "
        "12,000 households and avoided 9,000 tCO2e.")


def test_manifest_matches_public_tool_surface():
    import openharness.tools.impact as impact_tools

    names = {t.name for t in surfaces.surface_tools()}
    assert len(names) == len(impact_tools.__all__)
    assert {"assess_deal", "impact_advisor", "impact_report", "engagement_suite"} <= names
    assert all(e["area"] != "More" for e in surfaces.tool_manifest(include_schema=False))
    entry = surfaces.tool_entry(surfaces.get_surface_tool("assess_deal"))
    assert entry["title"] == "Assess Deal" and "properties" in entry["input_schema"]


def test_remote_callers_cannot_pass_server_paths(monkeypatch):
    monkeypatch.delenv(surfaces.ALLOW_PATHS_ENV, raising=False)
    with pytest.raises(surfaces.PathFieldRejected):
        surfaces.validate_payload("pitch_deck_analyze", {"file_path": "/etc/passwd"})
    with pytest.raises(surfaces.PathFieldRejected):
        surfaces.validate_payload("pitch_deck_analyze", {"url": "http://169.254.169.254/"})
    # empty values are fine, and the local (MCP stdio) surface may pass paths
    surfaces.validate_payload("assess_deal", {"text": DECK, "file_path": ""})
    surfaces.validate_payload("pitch_deck_analyze", {"file_path": "deck.pdf"}, allow_paths=True)
    with pytest.raises(surfaces.ToolNotFound):
        surfaces.validate_payload("bash", {})


def test_playbook_prompt():
    text = surfaces.playbook_prompt("deal_screening", "SunPath")
    assert "SunPath" in text and "`assess_deal`" in text and "assessment_id" in text
    with pytest.raises(KeyError):
        surfaces.playbook_prompt("nope")


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from openharness.api_gateway.router import app

    return TestClient(app)


def test_rest_tool_routes(client):
    listing = client.get("/api/v1/tools").json()
    assert len(listing["tools"]) == len(surfaces.surface_tools())
    assert "input_schema" not in listing["tools"][0]
    assert "input_schema" in client.get("/api/v1/tools?schemas=true").json()["tools"][0]
    assert client.get("/api/v1/tools/sdg_mapper").json()["name"] == "sdg_mapper"
    assert client.get("/api/v1/tools/bash").status_code == 404

    ok = client.post("/api/v1/tools/assess_deal", json={"text": DECK, "company_name": "SunPath"})
    assert ok.status_code == 200 and "IC gate" in ok.json()["output"]
    assert client.post("/api/v1/tools/pitch_deck_analyze",
                       json={"file_path": "/etc/passwd"}).status_code == 400
    assert client.post("/api/v1/tools/sdg_mapper", json={"sdg_claims": "x"}).status_code == 422
    assert client.get("/api/v1/playbooks").json()["playbooks"][0]["playbook_id"] == "deal_screening"


def test_mcp_exposes_every_tool_and_playbook_prompts():
    pytest.importorskip("mcp")
    from openharness.impact import mcp_server
    from openharness.impact.tool_advisor import PLAYBOOKS

    async def go():
        tools = {t.name: t for t in await mcp_server.mcp.list_tools()}
        prompts = {p.name for p in await mcp_server.mcp.list_prompts()}
        result = await mcp_server.mcp.call_tool("assess_deal", {"text": DECK, "company_name": "SunPath"})
        prompt = await mcp_server.mcp.get_prompt("lp_reporting", {"subject": "Fund I"})
        return tools, prompts, result, prompt

    tools, prompts, result, prompt = asyncio.run(go())
    assert {t.name for t in surfaces.surface_tools()} <= set(tools)
    audience = tools["assess_deal"].inputSchema["properties"]["audience"]
    assert audience["enum"] == ["full", "ic", "lp", "regulator", "public"]
    assert "IC gate" in str(result)
    assert prompts == {p.playbook_id for p in PLAYBOOKS}
    assert "Fund I" in prompt.messages[0].content.text


def test_console_discovers_registry_tools():
    from openharness.web.console import render_console_html

    html = render_console_html()
    assert "discoverFromRegistry" in html and "/api/v1/tools?schemas=true" in html
