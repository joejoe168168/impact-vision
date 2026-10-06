"""W0.7: report options must actually change the HTML report."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import yaml

from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool


def _render(tmp_path: Path, **overrides) -> str:
    data = yaml.safe_load(open("examples/sample_company.yaml", encoding="utf-8"))["company"]
    out = tmp_path / "r.html"
    args = ImpactReportInput(
        company_name=data["name"],
        company_description=data["description"],
        sector=data["sector"],
        reported_metrics={k: str(v) for k, v in data["reported_metrics"].items()},
        sdg_claims=data["sdg_claims"],
        output_format="html",
        output_path=str(out),
        **overrides,
    )
    result = asyncio.run(ImpactReportTool().execute(args, ToolExecutionContext(cwd=tmp_path)))
    assert not result.is_error, result.output
    return out.read_text(encoding="utf-8")


def _section_ids(html: str) -> list[str]:
    return re.findall(r'<h2 id="([^"]+)"', html)


def test_target_progress_html_renders_with_targets(tmp_path):
    html = _render(
        tmp_path,
        report_type="target_progress",
        impact_targets=[{"metric_id": "PI4060", "target_value": 60000, "target_year": 2027}],
    )
    assert "Target Summary:" in html


def test_lp_ready_differs_from_full(tmp_path):
    full = _render(tmp_path)
    lp = _render(tmp_path, report_type="lp_ready")
    assert full != lp
    assert "sec-gap" in _section_ids(full)
    assert "sec-gap" not in _section_ids(lp)
    assert "sec-greenwashing" not in _section_ids(lp)


def test_public_audience_drops_internal_content(tmp_path):
    html = _render(tmp_path, audience="public")
    assert "Not for public distribution" not in html
    assert "Greenwashing risk" not in html
    assert {"sec-gap", "sec-greenwashing", "sec-esg-toolbox"}.isdisjoint(_section_ids(html))
    assert 'class="audience-bar"' not in html


def test_toc_has_no_dead_links(tmp_path):
    for overrides in ({}, {"audience": "public"}):
        html = _render(tmp_path, **overrides)
        toc = re.search(r'<nav class="report-toc".*?</nav>', html, re.S).group(0)
        ids = set(re.findall(r'id="([^"]+)"', html))
        assert all(link in ids for link in re.findall(r'href="#([^"]+)"', toc))
