"""v8 W3.5: KPIs from Excel / CSV count as reported metrics."""
from __future__ import annotations

import pytest

from openharness.impact.metric_import import import_metrics
from openharness.impact.pipeline import assess_files

DECK = "# Sunlit Homes — Seed pitch\n\nSunlit Homes sells solar lanterns to off-grid households in Uganda.\n"


def test_csv_by_id_and_name_with_periods(tmp_path):
    sheet = tmp_path / "kpis.csv"
    sheet.write_text("Indicator,Value,Year\nPI4060,9000,2023\nPI4060,12000,2024\n"
                     "Client Individuals: Provided New Access,4100,2024\nHappiness index,7,2024\n", encoding="utf-8")
    result = import_metrics(sheet)
    assert result.metrics["PI4060"] == 12000
    assert result.metrics["PI2822"] == 4100
    assert result.series["PI4060"] == [("2023", 9000), ("2024", 12000)]
    assert result.unmatched == ["Happiness index"]


def test_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["IRIS ID", "Reported value", "Unit"])
    ws.append(["OI2764", 1800, "tCO2e"])
    path = tmp_path / "kpis.xlsx"
    wb.save(path)
    assert import_metrics(path).metrics == {"OI2764": 1800}


def test_spreadsheet_metrics_feed_the_assessment(tmp_path):
    deck = tmp_path / "deck.md"
    deck.write_text(DECK, encoding="utf-8")
    sheet = tmp_path / "kpis.csv"
    sheet.write_text("metric,value\nPI4060,12000\nOI2764,1800\n", encoding="utf-8")
    bundle = assess_files([deck, sheet])
    assert bundle.company.reported_metrics["PI4060"] == 12000
    assert bundle.report_data["metric_import"][0]["matched"] == ["OI2764", "PI4060"]
    with pytest.raises(ValueError):
        assess_files([sheet])
