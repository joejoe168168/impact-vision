"""W1.3: assess_deal in one call; downstream tools take its assessment_id."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import openharness.impact.storage as storage
from openharness.impact.pipeline import sample_deck_path
from openharness.impact.tool_advisor import route_query
from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.assess_deal_tool import AssessDealInput, AssessDealTool
from openharness.tools.impact.five_dimension_assess_tool import (
    FiveDimensionAssessTool,
    FiveDimensionInput,
)
from openharness.tools.impact.greenwashing_tool import GreenwashingDetectorTool, GreenwashingInput
from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool
from openharness.tools.impact.sdg_mapper_tool import SdgMapperInput, SdgMapperTool


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_global_store", storage.AssessmentStore(tmp_path / "iv.db"))
    yield
    storage._global_store = None


def _run(tool, args, cwd: Path):
    return asyncio.run(tool.execute(args, ToolExecutionContext(cwd=cwd)))


def _assess(tmp_path, **kw):
    result = _run(
        AssessDealTool(),
        AssessDealInput(file_path=str(sample_deck_path("solar")), **kw),
        tmp_path,
    )
    assert not result.is_error, result.output
    payload = json.loads(result.output.split("JSON: ", 1)[1])
    return result.output, payload


def test_assess_deal_returns_summary_and_id(tmp_path):
    output, payload = _assess(tmp_path, output_dir="reports")
    assert payload["company"] == "SunPath Energy Ltd"
    assert payload["assessment_id"]
    assert "IC gate:" in output
    assert (tmp_path / "reports" / "sunpath_energy_ltd_impact_report.html").is_file()


def test_downstream_tools_hydrate_from_assessment_id(tmp_path):
    _, payload = _assess(tmp_path)
    aid = payload["assessment_id"]

    sdg = _run(SdgMapperTool(), SdgMapperInput(assessment_id=aid), tmp_path)
    assert not sdg.is_error and "SunPath Energy Ltd" in sdg.output

    fd = _run(FiveDimensionAssessTool(), FiveDimensionInput(assessment_id=aid), tmp_path)
    assert not fd.is_error and "SunPath" in fd.output

    gw = _run(GreenwashingDetectorTool(), GreenwashingInput(assessment_id=aid), tmp_path)
    assert not gw.is_error

    out = tmp_path / "lp.html"
    report = _run(
        ImpactReportTool(),
        ImpactReportInput(assessment_id=aid, output_format="html", output_path=str(out), audience="lp"),
        tmp_path,
    )
    assert not report.is_error, report.output
    html = out.read_text(encoding="utf-8")
    assert "SunPath Energy Ltd" in html
    assert 'id="sec-claims"' in html  # extracted claims carried over


def test_explicit_fields_win_over_assessment(tmp_path):
    _, payload = _assess(tmp_path)
    sdg = _run(
        SdgMapperTool(),
        SdgMapperInput(assessment_id=payload["assessment_id"], company_name="Renamed Co"),
        tmp_path,
    )
    assert "Renamed Co" in sdg.output


def test_missing_name_and_unknown_id_are_clear_errors(tmp_path):
    no_name = _run(SdgMapperTool(), SdgMapperInput(), tmp_path)
    assert no_name.is_error and "assessment_id" in no_name.output
    unknown = _run(SdgMapperTool(), SdgMapperInput(assessment_id="999999"), tmp_path)
    assert unknown.is_error and "assess_deal" in unknown.output


def test_assess_deal_needs_input(tmp_path):
    result = _run(AssessDealTool(), AssessDealInput(), tmp_path)
    assert result.is_error


def test_advisor_routes_pitch_decks_to_assess_deal():
    routed = route_query("we received a new pitch deck, please screen this deal")
    names = [r["tool"] for r in routed["recommendations"]]
    assert "assess_deal" in names[:3]
    assert routed["playbook"]["steps"][0]["tool"] == "assess_deal"
