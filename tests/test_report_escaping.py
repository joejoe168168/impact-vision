"""W0.6: user-supplied text must never reach report HTML unescaped."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from impact_vision.impact.ic_memo import render_ic_memo
from impact_vision.impact.investee_portal import build_investee_portal
from impact_vision.impact.models import Company
from impact_vision.impact.sdk import ImpactVision
from impact_vision.tools.base import ToolExecutionContext
from impact_vision.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool

ATTR = '"><svg onload=alert(1)>'
TAG = "<img src=x onerror=alert(1)>"


def _assert_clean(html: str) -> None:
    assert ATTR not in html
    assert TAG not in html


def _report(tmp_path: Path, **overrides) -> str:
    out = tmp_path / "report.html"
    args = dict(
        company_name=f"Acme {ATTR}",
        company_description=f"We help farmers {TAG} grow. Risks: run-off {ATTR}.",
        sector="agriculture",
        geography=f"Kenya {ATTR}",
        impact_themes=[f"theme {TAG}"],
        reported_metrics={"PI4060": f"45,000 {ATTR}", "OI4112": "120"},
        sdg_claims=[1, 2],
        impact_targets=[{
            "metric_id": "PI4060", "target_value": 50000, "target_year": 2027,
            "baseline_value": 1000, "description": f"target {TAG}",
        }],
        metric_history=[
            {"metric_id": "PI4060", "value": 40000, "period": f"2024 {TAG}"},
            {"metric_id": "PI4060", "value": 45000, "period": "2025"},
        ],
        impact_claims=[{"text": f"We reached 5,000 farmers {TAG}", "category": "outcome"}],
        beneficiary_feedback={
            "satisfaction_score": 4.2, "nps": 40, "sample_size": 200,
            "methodology": f"Lean Data {TAG}", "survey_date": f"2026 {ATTR}",
        },
        branding={"fund_name": f"Fund {TAG}", "footer_text": f"foot {ATTR}"},
        output_format="html",
        output_path=str(out),
    )
    args.update(overrides)
    result = asyncio.run(
        ImpactReportTool().execute(ImpactReportInput(**args), ToolExecutionContext(cwd=tmp_path))
    )
    assert not result.is_error, result.output
    return out.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "overrides",
    [{}, {"report_type": "lp_ready"}, {"report_type": "target_progress"}, {"audience": "public"}],
)
def test_impact_report_escapes_user_text(tmp_path, overrides):
    _assert_clean(_report(tmp_path, **overrides))


def test_ic_memo_and_dd_report_escape_user_text():
    iv = ImpactVision()
    company = Company(
        name=f"Acme {ATTR}", sector="agriculture", description=f"Farm {TAG}",
        geography=f"MY {ATTR}", impact_themes=[f"t {TAG}"], reported_metrics={"PI4060": f"1 {ATTR}"},
    )
    assessment = iv.assess_company(company)
    scorecard = iv.evaluate_deal_against_thesis(assessment, thesis=iv.load_thesis())
    _assert_clean(str(render_ic_memo(assessment, scorecard, output_format="html")))
    _assert_clean(str(iv.render_dd_report_html(
        f"Our beneficiaries {TAG} are farmers {ATTR}.",
        company_name=f"Acme {ATTR}",
        document_label=f"doc {TAG}",
    )))


def test_investee_portal_escapes_user_text():
    _assert_clean(build_investee_portal(
        fund_name=f"Fund {TAG}", company_name=f"Co {ATTR}", routing={f"x{TAG}": "a"},
    ))
