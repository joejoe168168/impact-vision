"""W2.8: data exports — JSON schema/slim, numeric CSV, formatted XLSX."""

from __future__ import annotations

import csv
import io
import json

import pytest

from impact_vision.impact import exports
from impact_vision.impact.pipeline import assess_file, sample_deck_path, write_deliverables


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

    from impact_vision.tools.base import ToolExecutionContext
    from impact_vision.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool

    ctx = ToolExecutionContext(cwd=tmp_path)
    args = ImpactReportInput(company_name="Acme Solar", sector="energy",
                             reported_metrics={"OI4112": "1,200 tCO2e"}, output_format="json", slim=True)
    result = asyncio.run(ImpactReportTool().execute(args, ctx))
    payload = json.loads(result.output)
    assert payload["schema_version"] == exports.SCHEMA_VERSION and payload["export_mode"] == "slim"


def test_exports_carry_the_expected_impact_headline(bundle, tmp_path):
    """The figure the IC reads first must be in the data files, not only in the HTML."""
    openpyxl = pytest.importorskip("openpyxl")
    data = bundle.report_data
    head = data["expected_impact"]["outcomes"][0]

    rows = list(csv.DictReader(io.StringIO(exports.to_csv(data))))
    p50 = next(r for r in rows if r["Section"] == "Expected impact" and r["Metric"].endswith("P50"))
    assert float(p50["Numeric"]) == pytest.approx(head["p50"], abs=0.1) and p50["Unit"] == head["unit"]
    assert {"P10", "P50", "P90"} <= {r["Metric"].rsplit(" ", 1)[-1] for r in rows if r["Section"] == "Expected impact"}
    assert any(r["Metric"] == "IC gate" and r["Value"] for r in rows)
    plan = [r for r in rows if r["Section"] == "Evidence plan"]
    assert plan and plan[0]["Value"] == data["expected_impact"]["gate"]["plan"][0]["action"]
    assert any(r["Section"] == "Negative impact" and r["Max"] == "9" for r in rows)
    assert {r["Metric"] for r in rows if r["Section"] == "Contribution"} == {"Enterprise", "Investor"}

    wb = openpyxl.load_workbook(exports.write_xlsx(data, tmp_path / "r.xlsx"))
    assert {"Expected impact", "Impact factors", "Evidence plan", "Negative impacts"} <= set(wb.sheetnames)
    impact = wb["Expected impact"]
    assert impact["D2"].value == pytest.approx(head["p50"]) and impact["D2"].number_format == "#,##0"
    assert impact["C2"].value < impact["D2"].value < impact["E2"].value
    summary = {r[0].value: r[1] for r in wb["Summary"].iter_rows(min_row=4)}
    assert summary["Expected impact (P50)"].value == pytest.approx(head["p50"], abs=0.1)
    assert summary["IC gate"].value == data["expected_impact"]["gate"]["label"]
    assert summary["Expected-impact methodology"].value == data["expected_impact"]["methodology"]["methodology_version"]
    factors = {(r[0], r[1]) for r in wb["Impact factors"].iter_rows(min_row=2, values_only=True)}
    assert any(name == "Reach" for _, name in factors)


def test_summary_counts_are_whole_numbers_and_each_sheet_has_one_table(bundle, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(exports.write_xlsx(bundle.report_data, tmp_path / "r.xlsx"))
    summary = {r[0].value: r[1] for r in wb["Summary"].iter_rows(min_row=4)}
    claims = summary["Claims extracted"]
    assert isinstance(claims.value, int) and "." not in claims.number_format      # was "12.0"
    assert summary["5D overall (1–5)"].number_format == "0.0"
    # The frozen header sits under row 1 on both AI sheets (a second table used to move it).
    assert wb["AI provenance"].freeze_panes == "A2" and wb["AI provenance"].auto_filter.ref.startswith("A1:")
    assert wb["AI figures"].freeze_panes == "A2" and wb["AI figures"]["A1"].value == "Figure"


def test_csv_file_opens_in_excel_with_chinese_text(tmp_path):
    from impact_vision.impact.pipeline import assess_document, write_deliverables

    deck = ("# 綠源農業\n\n綠源農業向雲南的小農戶提供有機肥料。\n\n## 成果\n- 2024 年服務 3,200 名農戶。\n"
            "- We served 3,200 farmers in 2024 and raised yields by 18%.\n")
    out = write_deliverables(assess_document(deck, name="綠源農業"), tmp_path)
    path = next(p for p in out if p.suffix == ".csv")
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")                       # byte-order mark: Excel reads it as UTF-8
    rows = list(csv.DictReader(io.StringIO(raw.decode(exports.CSV_ENCODING))))
    assert list(rows[0]) == exports.CSV_HEADER                   # the BOM is not glued to the first header
    assert rows[0]["Value"] == "綠源農業"
