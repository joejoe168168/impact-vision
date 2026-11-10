"""HKEX ESG Reporting Code (Listing Rules Appendix C2) gap check."""
from __future__ import annotations

import asyncio
import re

import pytest
import yaml
from typer.testing import CliRunner

from impact_vision.impact._paths import data_path
from impact_vision.impact.frameworks.hkex_esg import hkex_esg_gap, hkex_esg_provisions, to_text

REPORT_EN = """# Harbour Logistics — ESG Report 2025
The Board has overall responsibility for ESG matters and oversees them through the Sustainability Committee.
The Board reviews progress against our ESG targets twice a year.
This report covers our Hong Kong and Shenzhen operations; the reporting boundary is unchanged from last year.
We carried out a materiality assessment with stakeholder engagement in 2025.
Emission factors follow the GHG Protocol and the HKEX calculation guidance.
Scope 1 emissions were 12,400 tCO2e and Scope 2 emissions were 8,100 tCO2e.
Energy consumption was 41,000 MWh. Water consumption was 96,000 cubic metres.
KPI A2.5 Packaging material is not applicable to our logistics business.
There were no work-related fatalities in 2023, 2024 or 2025. Lost days due to work injury were 46.
Our whistle-blowing policy is overseen by the Audit Committee, and anti-corruption training was given to all directors.
We ran scenario analysis on physical risks and transition risks.
"""

REPORT_ZH = """董事會全面負責本集團的ESG事宜，並透過可持續發展委員會監察。
本報告涵蓋香港及深圳業務，匯報範圍與去年相同。
範圍1排放為12,400公噸二氧化碳當量，範圍2排放為8,100公噸。能源總耗量為41,000千瓦時。
包裝材料對本集團業務並不適用。年內並無因工亡故個案。舉報政策由審核委員會監督。
"""


def _status(result: dict) -> dict[str, str]:
    return {r["id"]: r["status"] for r in result["requirements"]}


def test_checklist_covers_every_part_b_and_part_c_provision() -> None:
    cfg = yaml.safe_load(data_path("regulatory/hkex_esg_code.yaml").read_text(encoding="utf-8"))
    refs = {r["ref"] for r in cfg["requirements"]}
    # Part B paras 13(i)-(iii), the three reporting principles and the boundary.
    assert len([r for r in cfg["requirements"] if r["part"] == "B"]) == 7
    # Part C as in force from 2025: KPI A1.2 and Aspect A4 moved to Part D.
    kpis = {"A1": (1, 3, 4, 5, 6), "A2": (1, 2, 3, 4, 5), "A3": (1,), "B1": (1, 2), "B2": (1, 2, 3), "B3": (1, 2),
            "B4": (1, 2), "B5": (1, 2, 3, 4), "B6": (1, 2, 3, 4, 5), "B7": (1, 2, 3), "B8": (1, 2)}
    for aspect, numbers in kpis.items():
        assert f"Aspect {aspect} — General Disclosure" in refs
        for n in numbers:
            assert f"KPI {aspect}.{n}" in refs
    assert "KPI A1.2" not in refs and not any("A4" in ref for ref in refs)
    for req in cfg["requirements"]:
        assert req["title"] and req["zh"] and req["cues"], req["id"]
        for cue in req["cues"]:
            re.compile(cue)
    assert cfg["source_url"].startswith("https://www.hkex.com.hk/") and cfg["as_of"]


def test_reads_an_english_report() -> None:
    out = hkex_esg_gap(REPORT_EN)
    status = _status(out)
    assert status["b13_oversight"] == "addressed" and status["b15_boundary"] == "addressed"
    assert status["a2_1"] == "addressed" and status["b2_1"] == "addressed"
    assert status["d_scope12"] == "addressed" and status["d_resilience"] != "gap"
    assert status["b14_consistency"] == "gap" and status["b5_1"] == "gap"
    assert out["parts"]["B"]["coverage_pct"] > out["parts"]["C_soc"]["coverage_pct"]
    assert any("para 14 — Consistency" in g for g in out["mandatory_gaps"])
    text = to_text(out)
    assert "Appendix C2" in text and "not a compliance opinion" in text


def test_not_applicable_is_an_explanation_only_under_comply_or_explain() -> None:
    out = hkex_esg_gap(REPORT_EN)
    row = next(r for r in out["requirements"] if r["id"] == "a2_5")
    assert row["status"] == "explained" and "not applicable" in row["evidence"][0]
    assert "KPI A2.5" not in " ".join(out["gaps"])
    # A mandatory Part B item cannot be explained away.
    dodge = hkex_esg_gap("The reporting boundary is not applicable to the Group.")
    assert _status(dodge)["b15_boundary"] != "explained"


def test_part_d_basis_follows_the_issuer() -> None:
    by_issuer = {i: {r["id"]: r["basis"] for r in hkex_esg_gap(REPORT_EN, issuer=i)["requirements"]}
                 for i in ("largecap", "main_board", "gem")}
    assert by_issuer["largecap"]["d_scope3"] == "mandatory"
    assert by_issuer["main_board"]["d_scope3"] == "comply_or_explain"
    assert by_issuer["gem"]["d_scope3"] == "voluntary"
    # Scope 1 and 2 are mandatory for every issuer; Part B always is.
    assert {b["d_scope12"] for b in by_issuer.values()} == {"mandatory"}
    assert {b["b13_oversight"] for b in by_issuer.values()} == {"mandatory"}
    silent = "We make furniture."
    assert len(hkex_esg_gap(silent, issuer="largecap")["mandatory_gaps"]) > len(
        hkex_esg_gap(silent, issuer="gem")["mandatory_gaps"])
    with pytest.raises(ValueError):
        hkex_esg_gap(silent, issuer="nasdaq")


def test_reads_traditional_chinese() -> None:
    out = hkex_esg_gap(REPORT_ZH, lang="zh-HK")
    status = _status(out)
    assert status["b13_oversight"] != "gap" and status["b15_boundary"] != "gap"
    assert status["d_scope12"] == "addressed" and status["a2_5"] == "explained" and status["b2_1"] != "gap"
    assert out["parts"]["B"]["label"].startswith("B 部分") and out["issuer_label"] == "主板發行人"
    assert any(r["title"].startswith("董事會聲明") for r in out["requirements"])
    assert out["warnings"] and "強制披露" in out["warnings"][0]


def test_issb_statement_is_reported_but_not_taken_as_compliance() -> None:
    out = hkex_esg_gap("This report is prepared in accordance with IFRS S1 and IFRS S2.", issuer="largecap")
    assert out["issb_statement"] is True
    assert any("para 8" in w for w in out["warnings"])          # stated, yet Part D items are missing
    assert all(r["id"] != "issb_statement" for r in out["requirements"] if not r["informational"])


def test_provision_list_needs_no_report() -> None:
    rows = hkex_esg_provisions()
    assert len(rows) == 65 and rows[0]["ref"] == "para 13(i)"
    assert {r["basis"] for r in rows} == {"mandatory", "comply or explain"}


def test_cli_and_agent_tool(tmp_path) -> None:
    from impact_vision.cli import app
    from impact_vision.tools.base import ToolExecutionContext
    from impact_vision.tools.impact.framework_tool import FRAMEWORK_CATALOG, FrameworkInput, FrameworkTool

    report = tmp_path / "esg.md"
    report.write_text(REPORT_EN, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["framework", "hkex-esg", str(report), "--issuer", "largecap"])
    assert result.exit_code == 0 and "KPI B2.1" in result.output and "LargeCap" in result.output
    assert runner.invoke(app, ["framework", "hkex-esg", str(report), "--issuer", "x"]).exit_code == 2
    listing = runner.invoke(app, ["framework", "list"]).output
    for key, _name, _detail in FRAMEWORK_CATALOG:
        assert key in listing
    assert "hkex_esg" in listing and "hkfrs_s1" in listing

    tool = FrameworkTool()
    ctx = ToolExecutionContext(cwd=tmp_path)
    assessed = asyncio.run(tool.execute(
        FrameworkInput(framework="hkex_esg", action="assess", document_text=REPORT_EN,
                       structured_inputs={"issuer": "largecap"}), ctx))
    assert not assessed.is_error and assessed.metadata["issuer"] == "largecap"
    listed = asyncio.run(tool.execute(FrameworkInput(framework="hkex_esg", action="list"), ctx))
    assert "KPI B8.2" in listed.output
    s1 = asyncio.run(tool.execute(
        FrameworkInput(framework="hkfrs_s1", action="assess", document_text=REPORT_EN), ctx))
    assert not s1.is_error and "HKFRS S1" in s1.output
    every = asyncio.run(tool.execute(FrameworkInput(framework="all", action="list"), ctx))
    assert "hkex_esg" in every.output


def test_registry_and_freshness_gate_know_the_hk_checklists() -> None:
    from impact_vision.impact.knowledge import KNOWLEDGE_FILES, freshness_report
    from impact_vision.impact.standards_registry import default_standards_registry

    assert {"hkex_esg_code", "hkfrs_s1"} <= set(KNOWLEDGE_FILES)
    report = freshness_report(names=["hkex_esg_code", "hkfrs_s1"])
    assert report.ok and report.rows_checked > 70, report.summary()
    reg = default_standards_registry()
    assert reg.get("HKEX_ESG_CODE").effective_date == "2025-01-01"
    assert reg.get("HKFRS_S1") and reg.get("PCAF").version == "2025-12"
    assert "2027-02-19" in reg.get("ISSB_NATURE").notes
