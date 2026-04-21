"""Deal scorecard / IC gate engine.

Configurable pass/fail evaluator for a deal against a fund's thesis. Used at
two points in the workflow:

  1. **Pre-IC screen**: block IC submission if the deal fails any gate.
  2. **Monitoring**: re-evaluate quarterly and flag drift.

Gates are read from `FundThesis.ic_gate` so each fund manager can tune
thresholds without touching code.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.fund_thesis import FundThesis
from openharness.impact.models import Assessment


class GateCheck(BaseModel):
    name: str
    status: Literal["pass", "fail", "warn", "n/a"]
    actual: float | str | None = None
    threshold: float | str | None = None
    message: str = ""


class DealScorecard(BaseModel):
    company: str
    fund: str
    overall_status: Literal["pass", "fail", "warn"]
    checks: list[GateCheck] = Field(default_factory=list)
    blocking_failures: list[str] = Field(default_factory=list)
    warnings_list: list[str] = Field(default_factory=list)
    recommendation: str = ""


def _grade_status(value: float, threshold: float, *, higher_is_better: bool) -> Literal["pass", "fail", "warn"]:
    if higher_is_better:
        if value >= threshold:
            return "pass"
        if value >= threshold * 0.85:
            return "warn"
        return "fail"
    if value <= threshold:
        return "pass"
    if value <= threshold * 1.15:
        return "warn"
    return "fail"


def evaluate_deal(
    assessment: Assessment,
    thesis: FundThesis,
    *,
    dd_coverage_pct: float | None = None,
    greenwashing_score: float | None = None,
    exclusion_pass: bool | None = None,
) -> DealScorecard:
    """Score a deal against the fund thesis IC gate.

    Returns a `DealScorecard` with `overall_status` of:
      - `pass`: all blocking checks passed and no warns
      - `warn`: warnings only (no fails)
      - `fail`: at least one blocking failure
    """
    gate = thesis.ic_gate
    checks: list[GateCheck] = []

    # 5D overall
    if assessment.five_dimensions is not None:
        actual = float(assessment.five_dimensions.overall_score)
        st = _grade_status(actual, gate.min_5d_overall, higher_is_better=True)
        checks.append(GateCheck(
            name="5D overall score",
            status=st,
            actual=actual,
            threshold=gate.min_5d_overall,
            message=f"5D overall {actual} vs. min {gate.min_5d_overall}",
        ))

    # Top SDG score
    if assessment.sdg_alignments:
        top = max(assessment.sdg_alignments, key=lambda a: a.score)
        st = _grade_status(top.score, gate.min_top_sdg_score, higher_is_better=True)
        checks.append(GateCheck(
            name="Top SDG score",
            status=st,
            actual=top.score,
            threshold=gate.min_top_sdg_score,
            message=f"SDG {top.goal} ({top.goal_name}): {top.score} vs. min {gate.min_top_sdg_score}",
        ))

    # DD coverage
    if dd_coverage_pct is not None:
        st = _grade_status(dd_coverage_pct, gate.min_dd_coverage_pct, higher_is_better=True)
        checks.append(GateCheck(
            name="DD checklist coverage",
            status=st,
            actual=dd_coverage_pct,
            threshold=gate.min_dd_coverage_pct,
            message=f"{dd_coverage_pct:.1f}% covered vs. min {gate.min_dd_coverage_pct}%",
        ))

    # Greenwashing
    if greenwashing_score is not None:
        st = _grade_status(greenwashing_score, gate.max_greenwashing_score, higher_is_better=False)
        checks.append(GateCheck(
            name="Greenwashing risk",
            status=st,
            actual=greenwashing_score,
            threshold=gate.max_greenwashing_score,
            message=f"Risk {greenwashing_score:.1f} vs. max {gate.max_greenwashing_score}",
        ))

    # Exclusion screen
    if exclusion_pass is not None and gate.exclusion_must_pass:
        checks.append(GateCheck(
            name="Exclusion screening",
            status="pass" if exclusion_pass else "fail",
            actual="pass" if exclusion_pass else "fail",
            threshold="must pass",
            message=("All exclusions cleared" if exclusion_pass
                     else "One or more exclusion criteria triggered"),
        ))

    # Sector forbidden / required
    sector = (assessment.company.sector or "").lower()
    if gate.forbidden_sectors:
        is_forbidden = any(f.lower() in sector for f in gate.forbidden_sectors)
        checks.append(GateCheck(
            name="Forbidden sector check",
            status="fail" if is_forbidden else "pass",
            actual=sector,
            threshold=", ".join(gate.forbidden_sectors),
            message=("Sector matches the fund's forbidden list" if is_forbidden
                     else "Sector not on the forbidden list"),
        ))
    if gate.required_sectors:
        is_required = any(r.lower() in sector for r in gate.required_sectors)
        checks.append(GateCheck(
            name="Required sector check",
            status="pass" if is_required else "fail",
            actual=sector,
            threshold=", ".join(gate.required_sectors),
            message=("Sector matches a required focus area" if is_required
                     else "Sector outside fund's required focus areas"),
        ))

    fails = [c.message for c in checks if c.status == "fail"]
    warns = [c.message for c in checks if c.status == "warn"]
    if fails:
        overall = "fail"
        rec = "BLOCK IC submission. Resolve blocking failures and re-screen."
    elif warns:
        overall = "warn"
        rec = "Conditional IC: address the warnings before final approval."
    else:
        overall = "pass"
        rec = "All gates passed — eligible for IC submission."

    return DealScorecard(
        company=assessment.company.name or "Unnamed company",
        fund=thesis.name,
        overall_status=overall,
        checks=checks,
        blocking_failures=fails,
        warnings_list=warns,
        recommendation=rec,
    )


def render_scorecard_text(scorecard: DealScorecard) -> str:
    """Plain-text scorecard for CLI / IC memo embedding."""
    lines = [
        f"DEAL SCORECARD — {scorecard.company}",
        f"Fund: {scorecard.fund}",
        f"Overall: {scorecard.overall_status.upper()}",
        "",
        f"{'Check':<32} {'Status':<6} {'Actual':<12} {'Threshold':<12}",
        "-" * 72,
    ]
    for c in scorecard.checks:
        lines.append(
            f"{c.name:<32} {c.status:<6} "
            f"{str(c.actual):<12} {str(c.threshold):<12}"
        )
    lines.append("")
    lines.append("Recommendation: " + scorecard.recommendation)
    return "\n".join(lines)
