"""Tests for report generation (HTML, CSV, text, JSON)."""

from __future__ import annotations

import json
import asyncio
from pathlib import Path

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

    def test_to_text_snapshot_includes_claim_evidence(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_text
        data = _make_report_data()
        data["impact_claims"] = [
            {
                "text": "TestCo avoided 500 tCO2e for rural customers.",
                "category": "outcome",
                "confidence": 0.82,
                "evidence_strength": 3,
                "mapped_metrics": ["OI4112"],
            },
        ]
        text = _to_text(data)
        expected = "\n".join([
            "IMPACT CLAIMS",
            "----------------------------------------",
            "  - [OUTCOME] TestCo avoided 500 tCO2e for rural customers.",
            "    Confidence: 82% | Evidence: NESTA 3",
            "    Mapped metrics: OI4112",
        ])
        assert expected in text


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

    def test_to_csv_includes_claim_rows(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_csv
        data = _make_report_data()
        data["impact_claims"] = [
            {"text": "Avoided emissions", "category": "outcome", "mapped_metrics": ["OI4112"]},
        ]
        csv_output = _to_csv(data)
        assert "Claim,outcome,Avoided emissions,metrics: OI4112" in csv_output


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

    def test_to_html_snapshot_includes_escaped_claims_and_targets(self) -> None:
        from openharness.tools.impact.impact_report_tool import _to_html
        data = _make_report_data()
        data["impact_claims"] = [
            {
                "text": "Avoids <script>alert(1)</script> emissions",
                "category": "outcome",
                "confidence": 0.75,
                "evidence_strength": 2,
                "mapped_metrics": ["OI4112"],
                "mapped_sdg_targets": ["13.2"],
            },
        ]
        data["target_tracking"] = {
            "targets": [
                {
                    "metric_id": "OI4112",
                    "target": "500 tCO2e by 2027",
                    "current_value": 250,
                    "progress_pct": 50.0,
                    "status": "behind",
                },
            ],
            "summary": {"on_track": 0, "behind": 1, "exceeded": 0, "at_risk": 0},
        }
        html = _to_html(data)
        assert '<h2 id="sec-claims">Impact Claims' in html
        assert "Avoids &lt;script&gt;alert(1)&lt;/script&gt; emissions" in html
        assert "<script>alert(1)</script>" not in html
        assert "<td>500 tCO2e by 2027</td>" in html

    def test_report_tool_target_progress_uses_input_targets(self) -> None:
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool
        args = ImpactReportInput(
            company_name="TargetCo",
            company_description="Solar energy access",
            sector="energy",
            reported_metrics={"OI4112": "150 tCO2e"},
            impact_targets={"OI4112": "200 tCO2e by 2027"},
            metric_history=[{"metric_id": "OI4112", "value": "100", "period": "FY2024"}],
            report_type="target_progress",
            output_format="text",
        )
        result = asyncio.run(ImpactReportTool().execute(args, ToolExecutionContext(cwd=Path.cwd())))
        assert "TARGET PROGRESS REPORT: TargetCo" in result.output
        assert "OI4112: ON TRACK" in result.output
        assert "Target: 200 tCO2e by 2027" in result.output

    def test_api_report_forwards_target_and_claim_inputs(self) -> None:
        from openharness.api_gateway.router import ReportRequest, generate_report
        req = ReportRequest(
            company_name="API TargetCo",
            company_description="Solar energy access",
            sector="energy",
            reported_metrics={"OI4112": "150 tCO2e"},
            impact_targets={"OI4112": "200 tCO2e by 2027"},
            metric_history=[{"metric_id": "OI4112", "value": "100", "period": "FY2024"}],
            impact_claims=[
                {
                    "text": "API TargetCo avoids emissions.",
                    "mapped_metrics": ["OI4112"],
                    "category": "outcome",
                },
            ],
            report_type="target_progress",
            output_format="text",
        )
        payload = asyncio.run(generate_report(req))
        assert "TARGET PROGRESS REPORT: API TargetCo" in payload["result"]
        assert "Target: 200 tCO2e by 2027" in payload["result"]


class TestJSONReport:
    def test_json_output_is_valid(self) -> None:
        data = _make_report_data()
        json_str = json.dumps(data, indent=2, default=str)
        parsed = json.loads(json_str)
        assert parsed["company"]["name"] == "TestCo"

    def test_report_json_enriches_tracked_metrics_and_gap_suggestions(self) -> None:
        from openharness.tools.base import ToolExecutionContext
        from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool

        args = ImpactReportInput(
            company_name="EvidenceCo",
            company_description="Solar energy access for rural households.",
            sector="energy",
            reported_metrics={"PI4060": "5000"},
            output_format="json",
        )
        result = asyncio.run(ImpactReportTool().execute(args, ToolExecutionContext(cwd=Path.cwd())))

        payload = json.loads(result.output)
        assert "PI4060" in payload["five_dimensions"]["who"]["metrics_tracked"]
        assert payload["gap_analysis"]["suggested_metrics"]
        assert payload["gap_analysis"]["suggested_metrics"][0]["iris_id"]


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
