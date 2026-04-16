"""Tests for report generation (HTML, CSV, text, JSON)."""

from __future__ import annotations

import json

import pytest

from openharness.impact.models import Company


def _make_report_data(company_name: str = "TestCo") -> dict:
    """Create minimal report data for testing."""
    company = Company(
        name=company_name,
        description="Solar energy startup providing clean energy to rural Kenya",
        sector="Energy",
        impact_themes=["Clean Energy", "Climate Mitigation"],
        sdg_claims=[7, 13],
        reported_metrics={"OI4112": "500 tCO2e"},
    )
    return {
        "company": company.model_dump(),
        "generated_at": "2026-04-16T00:00:00+00:00",
        "catalog_version": "IRIS+ 5.3c",
    }


class TestTextReport:
    def test_to_text_includes_company_name(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_text
        data = _make_report_data()
        text = _to_text(data)
        assert "TestCo" in text

    def test_to_text_includes_company_info(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_text
        data = _make_report_data()
        text = _to_text(data)
        assert "IMPACT ASSESSMENT REPORT" in text
        assert "TestCo" in text


class TestCSVReport:
    def test_to_csv_returns_string(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_csv
        data = _make_report_data()
        csv_output = _to_csv(data)
        assert isinstance(csv_output, str)
        assert len(csv_output) > 0

    def test_to_csv_has_headers(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_csv
        data = _make_report_data()
        csv_output = _to_csv(data)
        first_line = csv_output.strip().split("\n")[0]
        assert "," in first_line


class TestHTMLReport:
    def test_to_html_returns_valid_html(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_html
        data = _make_report_data()
        html = _to_html(data)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_to_html_includes_company_name(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_html
        data = _make_report_data()
        html = _to_html(data)
        assert "TestCo" in html

    def test_to_html_includes_plotly(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_html
        data = _make_report_data()
        html = _to_html(data)
        assert "plotly" in html.lower()

    def test_to_html_with_five_dimensions(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_html
        data = _make_report_data()
        data["five_dimensions"] = {
            "what": {"dimension": "What", "score": 3.0, "metrics_reported": 1, "metrics_available": 10, "gaps": [], "notes": "test", "provenance": "partial"},
            "who": {"dimension": "Who", "score": 2.5, "metrics_reported": 0, "metrics_available": 8, "gaps": [], "notes": "test", "provenance": "estimated"},
            "how_much": {"dimension": "How Much", "score": 2.0, "metrics_reported": 0, "metrics_available": 6, "gaps": [], "notes": "test", "provenance": "estimated"},
            "contribution": {"dimension": "Contribution", "score": 2.5, "metrics_reported": 0, "metrics_available": 5, "gaps": [], "notes": "test", "provenance": "estimated"},
            "risk": {"dimension": "Risk", "score": 2.0, "metrics_reported": 0, "metrics_available": 4, "gaps": [], "notes": "test", "provenance": "estimated"},
            "overall_score": 2.4,
            "overall_grade": "C+",
            "overall_provenance": "partial",
            "impact_theme": "Clean Energy",
            "recommendations": ["Track more metrics"],
        }
        html = _to_html(data)
        assert "5 Dimensions" in html
        assert "C+" in html


class TestJSONReport:
    def test_json_output_is_valid(self) -> None:
        data = _make_report_data()
        json_str = json.dumps(data, indent=2, default=str)
        parsed = json.loads(json_str)
        assert parsed["company"]["name"] == "TestCo"


class TestTemplateEngine:
    def test_render_header(self) -> None:
        from openharness.impact.report_templates.html_template import render_header
        data = _make_report_data()
        header = render_header(data)
        assert "TestCo" in header
        assert "Energy" in header
        assert "<!DOCTYPE html>" in header

    def test_render_footer(self) -> None:
        from openharness.impact.report_templates.html_template import render_footer
        footer = render_footer()
        assert "Impact Vision" in footer
        assert "</html>" in footer

    def test_get_css(self) -> None:
        from openharness.impact.report_templates.html_template import get_css
        css = get_css()
        assert "--primary" in css
        assert "score-card" in css

    def test_sdg_colors(self) -> None:
        from openharness.impact.report_templates.html_template import get_sdg_colors
        colors = get_sdg_colors()
        assert len(colors) == 17
        assert 1 in colors
        assert colors[1].startswith("#")


class TestStorageLayer:
    def test_save_and_retrieve_assessment(self, tmp_path) -> None:
        from openharness.impact.storage import AssessmentStore
        store = AssessmentStore(tmp_path / "test.db")
        rid = store.save_assessment(
            "TestCo",
            {"name": "TestCo", "sector": "Energy"},
            five_dimensions={"overall_score": 3.0},
        )
        assert rid > 0
        result = store.get_assessment("TestCo")
        assert result is not None
        assert result["company"]["name"] == "TestCo"
        assert result["five_dimensions"]["overall_score"] == 3.0
        store.close()

    def test_list_assessments(self, tmp_path) -> None:
        from openharness.impact.storage import AssessmentStore
        store = AssessmentStore(tmp_path / "test.db")
        store.save_assessment("CompA", {"name": "CompA"})
        store.save_assessment("CompB", {"name": "CompB"})
        listings = store.list_assessments()
        assert len(listings) == 2
        store.close()

    def test_delete_assessment(self, tmp_path) -> None:
        from openharness.impact.storage import AssessmentStore
        store = AssessmentStore(tmp_path / "test.db")
        store.save_assessment("CompDel", {"name": "CompDel"})
        assert store.delete_assessment("CompDel")
        assert store.get_assessment("CompDel") is None
        store.close()

    def test_session_history(self, tmp_path) -> None:
        from openharness.impact.storage import AssessmentStore
        store = AssessmentStore(tmp_path / "test.db")
        store.log_tool_invocation(
            session_id="sess-001",
            company_name="TestCo",
            tool_name="five_dimension_assess",
            output_summary="Grade: B",
        )
        history = store.get_session_history(company_name="TestCo")
        assert len(history) == 1
        assert history[0]["tool_name"] == "five_dimension_assess"
        store.close()

    def test_update_existing_assessment(self, tmp_path) -> None:
        from openharness.impact.storage import AssessmentStore
        store = AssessmentStore(tmp_path / "test.db")
        store.save_assessment("TestCo", {"name": "TestCo"}, five_dimensions={"score": 2.0})
        store.save_assessment("TestCo", {"name": "TestCo"}, five_dimensions={"score": 3.5})
        result = store.get_assessment("TestCo")
        assert result["five_dimensions"]["score"] == 3.5
        listings = store.list_assessments()
        assert len(listings) == 1
        store.close()
