"""Blended-finance instrument designer (Phase 16).

Templates + a deal-design helper for the three instruments most common
in impact / catalytic capital structures:

1. **Impact-Linked Loan (IL-Loan)** — interest rate steps down when an
   impact KPI is hit, or up if it's missed.
2. **Social Outcomes Contract (SOC) / Development Impact Bond (DIB)** —
   an outcome payer reimburses investors only when independently
   verified outcomes are achieved.
3. **Impact Carry** — GP carried interest is gated on a portfolio-level
   impact hurdle (e.g. 80% of capital deployed in verified-impact
   companies by exit).

The module returns deterministic, board-ready term sheets you can
serialise to JSON, YAML or the IC memo template.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


InstrumentType = Literal["il-loan", "soc", "impact-carry"]


class RateStep(BaseModel):
    """One node of an impact-linked step schedule."""

    kpi_threshold: float
    rate_bps: int
    direction: Literal["down", "up"] = "down"
    note: str = ""


class ILLoanTerms(BaseModel):
    """Impact-linked loan term sheet."""

    borrower: str
    principal_usd: float = Field(gt=0)
    base_rate_bps: int
    tenor_months: int = Field(gt=0)
    kpi_id: str
    kpi_description: str
    baseline: float
    target: float
    step_schedule: list[RateStep]
    cap_bps: int | None = None  # maximum step-down
    floor_bps: int | None = None  # maximum step-up
    reporting_cadence: Literal["quarterly", "annual"] = "annual"
    verification_party: str = "Independent assurer (ISAE 3000)"


class SOCTerms(BaseModel):
    """Social Outcomes Contract / Development Impact Bond term sheet."""

    project_name: str
    outcome_payer: str
    intermediary: str
    service_provider: str
    beneficiary_count_target: int
    outcome_metric: str
    unit_price_usd: float
    max_payment_usd: float
    tenor_months: int
    validation_methodology: str = "Third-party RCT or matched-control study"
    trigger_gates: list[str] = Field(default_factory=list)


class ImpactCarryTerms(BaseModel):
    """Impact-gated GP carry term sheet."""

    fund_name: str
    gp_carry_rate_pct: float = 20.0
    impact_hurdle_pct: float = 80.0
    hurdle_metric: str = "Capital deployed into verified-impact companies"
    verification_party: str = "Independent assurer (ISAE 3000)"
    clawback_window_years: int = 5


class BlendedFinanceDeal(BaseModel):
    """Aggregate container for a full deal package."""

    deal_name: str
    created_at: date = Field(default_factory=date.today)
    il_loan: ILLoanTerms | None = None
    soc: SOCTerms | None = None
    impact_carry: ImpactCarryTerms | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Helpers that design a "sensible default" deal from a minimal input set
# ---------------------------------------------------------------------------


def design_il_loan(
    *,
    borrower: str,
    principal_usd: float,
    base_rate_bps: int,
    tenor_months: int,
    kpi_id: str,
    kpi_description: str,
    baseline: float,
    target: float,
    step_bps: int = 50,
) -> ILLoanTerms:
    """Return an IL-Loan term sheet with a 3-step schedule around the target."""
    midpoint = (baseline + target) / 2.0
    steps = [
        RateStep(
            kpi_threshold=baseline, rate_bps=0, direction="down", note="Baseline — no rate change."
        ),
        RateStep(
            kpi_threshold=midpoint,
            rate_bps=step_bps,
            direction="down",
            note="Midway between baseline and target.",
        ),
        RateStep(
            kpi_threshold=target,
            rate_bps=step_bps * 2,
            direction="down",
            note="Full step-down on target achievement.",
        ),
    ]
    return ILLoanTerms(
        borrower=borrower,
        principal_usd=principal_usd,
        base_rate_bps=base_rate_bps,
        tenor_months=tenor_months,
        kpi_id=kpi_id,
        kpi_description=kpi_description,
        baseline=baseline,
        target=target,
        step_schedule=steps,
        cap_bps=step_bps * 2,
        floor_bps=step_bps,
    )


def design_soc(
    *,
    project_name: str,
    outcome_payer: str,
    intermediary: str,
    service_provider: str,
    beneficiary_count_target: int,
    outcome_metric: str,
    unit_price_usd: float,
    tenor_months: int = 36,
) -> SOCTerms:
    return SOCTerms(
        project_name=project_name,
        outcome_payer=outcome_payer,
        intermediary=intermediary,
        service_provider=service_provider,
        beneficiary_count_target=beneficiary_count_target,
        outcome_metric=outcome_metric,
        unit_price_usd=unit_price_usd,
        max_payment_usd=unit_price_usd * beneficiary_count_target * 1.2,  # 20% buffer
        tenor_months=tenor_months,
        trigger_gates=[
            "20% of target achieved at month 12",
            "55% of target achieved at month 24",
            "100% of target achieved at maturity",
        ],
    )


def design_impact_carry(
    *,
    fund_name: str,
    gp_carry_rate_pct: float = 20.0,
    impact_hurdle_pct: float = 80.0,
) -> ImpactCarryTerms:
    return ImpactCarryTerms(
        fund_name=fund_name,
        gp_carry_rate_pct=gp_carry_rate_pct,
        impact_hurdle_pct=impact_hurdle_pct,
    )


class KPICredibility(BaseModel):
    kpi_id: str
    core_impact_relevance: int = Field(ge=1, le=5)
    ambition: int = Field(ge=1, le=5)
    penalty_materiality: float
    penalty_material: bool
    verification: Literal["third_party", "internal", "none"]
    score: int = Field(ge=0, le=100)
    flags: list[str] = Field(default_factory=list)


def score_kpi_credibility(
    kpi: dict, toc_outcomes: list[str], benchmark: dict | None = None
) -> KPICredibility:
    description = str(kpi.get("description", "")).lower()
    relevance = (
        5
        if any(str(outcome).lower() in description for outcome in toc_outcomes)
        else int(kpi.get("core_impact_relevance", 2))
    )
    ambition = int(kpi.get("ambition", 3 if benchmark else 2))
    penalty = float(kpi.get("step_up_bps", kpi.get("forfeited_carry_pct", 0)))
    is_carry = "forfeited_carry_pct" in kpi
    material = penalty >= (10 if is_carry else 25)
    verification = kpi.get("verification", "none")
    verification_points = {"third_party": 25, "internal": 12, "none": 0}[verification]
    score = min(
        100,
        round(
            relevance / 5 * 35 + ambition / 5 * 25 + (15 if material else 0) + verification_points
        ),
    )
    flags = []
    if not material:
        flags.append("penalty is economically immaterial")
    if verification != "third_party":
        flags.append("not third-party verified")
    if relevance < 3:
        flags.append("weak link to core Theory of Change outcome")
    return KPICredibility(
        kpi_id=str(kpi.get("kpi_id", "kpi")),
        core_impact_relevance=relevance,
        ambition=ambition,
        penalty_materiality=penalty,
        penalty_material=material,
        verification=verification,
        score=score,
        flags=flags,
    )


class PbRMilestone(BaseModel):
    milestone_id: str
    metric_id: str
    threshold: float
    due: str
    payment: float
    status: Literal["pending", "achieved", "missed", "disputed", "verified"] = "pending"
    evidence_refs: list[str] = Field(default_factory=list)


def track_payment_by_results(
    deal_terms, milestones: list[PbRMilestone], records, trail=None
) -> dict:
    by_metric = {record.metric_id: record for record in records}
    rows, payments = [], 0.0
    for milestone in milestones:
        record = by_metric.get(milestone.metric_id.upper())
        status = milestone.status
        if status != "disputed":
            if record is None or not isinstance(record.value, (int, float)):
                status = "pending"
            elif float(record.value) < milestone.threshold:
                status = "missed"
            elif record.is_verified:
                status = "verified"
                payments += milestone.payment
            else:
                status = "achieved"
        row = {**milestone.model_dump(mode="json"), "status": status}
        rows.append(row)
        if trail is not None:
            trail.record_event(
                event_type="pbr.milestone_evaluated",
                payload=row,
                actor="system",
                period=milestone.due[:7],
            )
    return {"deal_terms": deal_terms, "milestones": rows, "payments_due": round(payments, 2)}


class CarryStructure(BaseModel):
    model: Literal["reward", "forfeiture_escrow"]
    base_carry_pct: float
    at_risk_pct: float
    triggers: list[dict] = Field(default_factory=list)
    charity_fallback: str | None = None


def simulate_carry(structure: CarryStructure, scenarios: list[dict]) -> dict:
    rows = []
    for scenario in scenarios:
        achievements = scenario.get("achievement", scenario.get("targets", {}))
        achieved_weight = sum(
            float(t.get("weight", 0)) * float(bool(achievements.get(t.get("target_id"))))
            for t in structure.triggers
        )
        total_weight = sum(float(t.get("weight", 0)) for t in structure.triggers) or 1
        earned = achieved_weight / total_weight
        at_risk_carry = structure.base_carry_pct * structure.at_risk_pct
        carry_paid = structure.base_carry_pct - at_risk_carry + at_risk_carry * earned
        if structure.model == "reward":
            carry_paid = (
                structure.base_carry_pct * (1 - structure.at_risk_pct) + at_risk_carry * earned
            )
        rows.append(
            {
                "scenario": scenario.get("name", "scenario"),
                "achievement_pct": round(100 * earned, 2),
                "carry_paid_pct": round(carry_paid, 4),
                "forfeited_pct": round(structure.base_carry_pct - carry_paid, 4),
                "lp_economics_delta_pct": round(structure.base_carry_pct - carry_paid, 4),
            }
        )
    flags = []
    if structure.at_risk_pct < 0.1:
        flags.append("at_risk_pct below 10%; likely immaterial to LPs")
    if any(t.get("verifier") != "third_party" for t in structure.triggers):
        flags.append("one or more triggers are not third-party verified")
    return {"scenarios": rows, "flags": flags}


class SAFITerms(BaseModel):
    principal: float
    max_discount_pct: float
    outcome_schedule: list[PbRMilestone] = Field(default_factory=list)


def simulate_safi(terms: SAFITerms, records) -> dict:
    tracked = track_payment_by_results({}, terms.outcome_schedule, records)
    verified = sum(1 for row in tracked["milestones"] if row["status"] == "verified")
    ratio = verified / len(terms.outcome_schedule) if terms.outcome_schedule else 0
    discount = terms.max_discount_pct * ratio
    return {
        "verified_milestones": verified,
        "discount_pct": round(discount, 4),
        "conversion_value": round(terms.principal * (1 + discount), 2),
        "milestones": tracked["milestones"],
    }


__all__ = [
    "InstrumentType",
    "RateStep",
    "ILLoanTerms",
    "SOCTerms",
    "ImpactCarryTerms",
    "BlendedFinanceDeal",
    "design_il_loan",
    "design_soc",
    "design_impact_carry",
    "KPICredibility",
    "PbRMilestone",
    "CarryStructure",
    "SAFITerms",
    "score_kpi_credibility",
    "track_payment_by_results",
    "simulate_carry",
    "simulate_safi",
]
