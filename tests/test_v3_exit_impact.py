"""Tests for v3 OPIM Principle 7 exit impact assessment."""

from __future__ import annotations

from openharness.impact.exit_impact import (
    ExitDurabilityRisk,
    PostExitFollowUp,
    build_exit_plan,
    score_exit_impact,
)
from openharness.impact.models import Company, ImpactClaim


def _company() -> Company:
    return Company(name="ExitCo", sector="energy")


def test_durability_risk_score_uses_likelihood_severity() -> None:
    risk = ExitDurabilityRisk(
        risk_id="r1",
        category="commercial",
        description="customer churn",
        likelihood="likely",
        severity="major",
        mitigation="customer success plan",
    )
    assert risk.score == 9


def test_score_exit_impact_strong_when_well_documented() -> None:
    plan = build_exit_plan(
        company=_company(),
        exit_date="2027-01-01",
        risks=[
            ExitDurabilityRisk(
                risk_id="r1",
                category="commercial",
                description="churn",
                likelihood="unlikely",
                severity="minor",
                mitigation="contract retention",
            ),
            ExitDurabilityRisk(
                risk_id="r2",
                category="governance",
                description="board vacuum",
                likelihood="possible",
                severity="moderate",
                mitigation="board commitments",
            ),
        ],
        follow_ups=[
            PostExitFollowUp(
                follow_up_id="f1", description="12m review", period="12m",
                owner="analyst", status="completed", metric_ids=["OI4112"],
            ),
            PostExitFollowUp(
                follow_up_id="f2", description="24m review", period="24m",
                owner="analyst", status="planned", metric_ids=["OI4112"],
            ),
        ],
        claims=[
            ImpactClaim(text="Avoided 1500 tCO2e", evidence_strength=4),
            ImpactClaim(text="2,000 households served", evidence_strength=5),
        ],
    )
    assert plan.opim_principle == "OPIM Principle 7"
    assert plan.learning_principle == "OPIM Principle 8"
    score = score_exit_impact(plan)
    assert score.band in {"moderate", "strong"}
    assert score.residual_score >= 60
    assert "no_residual_evidence" not in score.flags
    assert "no_follow_ups_planned" not in score.flags


def test_score_exit_impact_weak_when_undocumented() -> None:
    plan = build_exit_plan(company=_company(), exit_date="2027-01-01")
    score = score_exit_impact(plan)
    assert score.band == "weak"
    assert "no_risks_documented" in score.flags
    assert "no_follow_ups_planned" in score.flags
    assert "no_residual_evidence" in score.flags


def test_unmitigated_risks_flag_exposed() -> None:
    plan = build_exit_plan(
        company=_company(),
        exit_date="2027-01-01",
        risks=[ExitDurabilityRisk(
            risk_id="r1",
            category="regulatory",
            description="policy change",
            likelihood="likely",
            severity="major",
        )],
        follow_ups=[PostExitFollowUp(
            follow_up_id="f1",
            description="6m",
            period="6m",
        )],
    )
    score = score_exit_impact(plan)
    assert "unmitigated_risks" in score.flags
    assert "follow_up_owner_missing" in score.flags
