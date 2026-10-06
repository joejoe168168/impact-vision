"""W2.8: data exports — JSON schema/slim, numeric CSV, formatted XLSX."""

from __future__ import annotations

import csv
import io
import json

import pytest

from openharness.impact import exports
from openharness.impact.pipeline import assess_file, sample_deck_path, write_deliverables


@pytest.fixture(scope="module")
def bundle():
    return assess_file(sample_deck_path("pig-farm"))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1,200 tCO2e", (1200.0, "tCO2e")), ("62%", (62.0, "%")), (3, (3.0, "")),
     ("n/a", (None, "")), ("", (None, "")), (True, (None, ""))],
)
def test_parse_number(raw, expected):
    assert exports.parse_number(raw) == expected


def test_json_has_schema_version_and_slim_is_much_smaller(bundle):
    full = json.loads(exports.to_json(bundle.report_data))
    slim = json.loads(exports.to_json(bundle.report_data, slim=True))
    assert full["schema_version"] == slim["schema_version"] == exports.SCHEMA_VERSION
    assert (full["export_mode"], slim["export_mode"]) == ("full", "slim")
    assert "sdg_alignment" not in slim
    assert all("evidence_chain" not in a for a in slim["sdg_alignments"])
    assert "required" not in slim["gap_analysis"]
    assert slim["gap_analysis"]["coverage_percentage"] == full["gap_analysis"]["coverage_percentage"]
    assert len(json.dumps(slim)) * 4 < len(json.dumps(full))
    # slim must not mutate the source payload
    assert "evidence_chain" in bundle.report_data["sdg_alignments"][0]


def test_csv_has_numeric_columns(bundle):
    rows = list(csv.DictReader(io.StringIO(exports.to_csv(bundle.report_data))))
    assert list(rows[0]) == exports.CSV_HEADER
    overall = next(r for r in rows if r["Metric"] == "Overall Grade")
    assert float(overall["Numeric"]) == bundle.report_data["five_dimensions"]["overall_score"]
    assert overall["Max"] == "5" and overall["Details"].endswith("/5.0")
    sdg = next(r for r in rows if r["Section"] == "SDG")
    assert 0 < float(sdg["Numeric"]) <= 100 and sdg["Max"] == "100"
    assert any(r["Section"] == "Greenwashing" and r["Numeric"] for r in rows)


def test_xlsx_is_formatted_and_numeric(bundle, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    path = exports.write_xlsx(bundle.report_data, tmp_path / "r.xlsx")
    wb = openpyxl.load_workbook(path)
    assert {"Summary", "5 Dimensions", "SDG Alignment", "Gap Analysis", "Claims",
            "All figures", "Methodology"} <= set(wb.sheetnames)
    sdg = wb["SDG Alignment"]
    assert sdg.freeze_panes == "A2" and sdg.auto_filter.ref.startswith("A1:")
    assert isinstance(sdg["C2"].value, (int, float))
    assert sdg.column_dimensions["B"].width >= 10
    five = wb["5 Dimensions"]
    assert isinstance(five["B2"].value, (int, float)) and five["B2"].number_format == "0.0"
    gap = wb["Gap Analysis"]
    reported = [row for row in gap.iter_rows(min_row=2, values_only=True) if row[0] == "Reported"]
    assert any(isinstance(row[3], (int, float)) for row in reported)
    assert wb["Methodology"].max_row >= 6


def test_deliverables_include_data_files(bundle, tmp_path):
    names = {p.name for p in write_deliverables(bundle, tmp_path, include_docx=False)}
    assert "kampung_makmur_sdn_bhd_data.csv" in names
    assert "kampung_makmur_sdn_bhd_data.xlsx" in names


def test_tool_json_slim_flag(tmp_path):
    import asyncio

    from openharness.tools.base import ToolExecutionContext
    from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool

    ctx = ToolExecutionContext(cwd=tmp_path)
    args = ImpactReportInput(company_name="Acme Solar", sector="energy",
                             reported_metrics={"OI4112": "1,200 tCO2e"}, output_format="json", slim=True)
    result = asyncio.run(ImpactReportTool().execute(args, ctx))
    payload = json.loads(result.output)
    assert payload["schema_version"] == exports.SCHEMA_VERSION and payload["export_mode"] == "slim"
