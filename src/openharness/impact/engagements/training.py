"""Training & capacity-building engine (roadmap-v4 Track 6).

Converts engagement gaps (failed validations, missing evidence,
low-coverage KPIs) into actionable training plans, workshop packs, and
investee coaching cards. Reuses the v3
:mod:`openharness.tools.impact.improvement_advisor_tool` pattern but adds
explicit "training" language + a learning-loop follow-up structure.

Design is deliberately data-only (no network, no LLM). Track 8 will layer
a copilot over this so the workshop facilitator has AI help; until then
consultants get a deterministic, auditable scaffold.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field


MaturityStage = Literal[
    "initial",
    "developing",
    "defined",
    "managed",
    "optimising",
]

BadgeKind = Literal[
    "data_ready",
    "report_ready",
    "assurance_ready",
    "lp_ready",
]


WORKSHOP_PACKS: dict[str, dict[str, list[str]]] = {
    "theory_of_change": {
        "agenda": [
            "Welcome & ground rules",
            "Review intake docs + AI-drafted ToC",
            "Challenge assumptions",
            "Rewrite outcomes in beneficiary language",
            "Agree assumptions + evidence plan",
        ],
        "prompts": [
            "Whose voice is missing?",
            "What would falsify this outcome?",
            "What counterfactual would we use?",
        ],
        "deliverables": ["Rewritten ToC", "Assumption register"],
    },
    "kpi_design": {
        "agenda": [
            "Review outcomes & attach metrics",
            "Stress-test metric quality (IRIS+ / EDCI / ESRS)",
            "Agree baselines and target direction",
            "Lock KPI framework v1",
        ],
        "prompts": [
            "Does every outcome have at least one lagging + leading indicator?",
            "Is the metric comparable across portfolio entities?",
        ],
        "deliverables": ["Locked KPI framework", "Baseline table"],
    },
    "esg_baseline": {
        "agenda": [
            "Double-materiality walk-through",
            "Framework mapping (CSRD / ISSB / SASB / GRI)",
            "Gap-closure roadmap",
        ],
        "prompts": [
            "Which topics are financially material but not yet reported?",
            "Which topics are impact-material but not yet governed?",
        ],
        "deliverables": ["Materiality matrix", "Gap-closure roadmap"],
    },
    "data_quality": {
        "agenda": [
            "Review exception queue",
            "Root-cause analysis",
            "Agree remediation plan",
        ],
        "prompts": [
            "Which exceptions are systemic vs one-off?",
            "What automation would prevent recurrence?",
        ],
        "deliverables": ["Data-quality remediation plan"],
    },
    "stakeholder_voice": {
        "agenda": [
            "Review stakeholder map",
            "Design Lean Data instrument",
            "Consent & ethics briefing",
            "Pilot + iterate",
        ],
        "prompts": [
            "Who benefits? Who is excluded?",
            "What consent language is appropriate for this jurisdiction?",
        ],
        "deliverables": ["Stakeholder voice instrument", "Consent template"],
    },
    "reporting": {
        "agenda": [
            "Identify audiences",
            "Map sections → evidence",
            "Run claim review panel",
            "Agree approval workflow",
        ],
        "prompts": [
            "What is the single sentence each audience should remember?",
            "Which claims have evidence gaps that require caveats?",
        ],
        "deliverables": ["Report outline", "Claim review log"],
    },
}


class TrainingAction(BaseModel):
    """One training plan action."""

    action_id: str = Field(default_factory=lambda: f"tp_{secrets.token_hex(4)}")
    topic: str
    workshop_pack: str = ""
    audience: str = "client team"
    objective: str = ""
    effort_days: float = 1.0
    success_metric: str = ""


class TrainingPlan(BaseModel):
    """Track 6.1 training plan."""

    plan_id: str = Field(default_factory=lambda: f"train_{secrets.token_hex(4)}")
    engagement_id: str = ""
    maturity_stage: MaturityStage = "developing"
    actions: list[TrainingAction] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: _now())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_effort_days(self) -> float:
        return round(sum(a.effort_days for a in self.actions), 1)


def build_training_plan(
    *,
    engagement_id: str,
    maturity_stage: MaturityStage = "developing",
    missing_topics: Iterable[str] | None = None,
    failed_validations: Iterable[str] | None = None,
    objectives: Iterable[str] | None = None,
) -> TrainingPlan:
    """Generate a training plan from engagement gap signals.

    ``missing_topics`` should be workshop-pack IDs (``theory_of_change`` etc).
    ``failed_validations`` are free-text strings from the ToC validator
    or evidence review.
    """
    actions: list[TrainingAction] = []
    stage_effort = {
        "initial": 2.0,
        "developing": 1.5,
        "defined": 1.0,
        "managed": 0.75,
        "optimising": 0.5,
    }[maturity_stage]

    for topic in missing_topics or []:
        pack_id = topic if topic in WORKSHOP_PACKS else ""
        actions.append(
            TrainingAction(
                topic=topic,
                workshop_pack=pack_id,
                objective=f"Build client capability on {topic.replace('_', ' ')}.",
                effort_days=stage_effort,
                success_metric=f"{topic.replace('_', ' ').title()} workshop completed and deliverable signed off.",
            )
        )
    for validation in failed_validations or []:
        actions.append(
            TrainingAction(
                topic="data_quality" if "evidence" in validation.lower() else "kpi_design",
                workshop_pack="data_quality" if "evidence" in validation.lower() else "kpi_design",
                objective=f"Address validation gap: {validation}.",
                effort_days=stage_effort,
                success_metric=f"Validation '{validation}' resolved in next review.",
            )
        )
    for objective in objectives or []:
        actions.append(
            TrainingAction(
                topic="custom",
                objective=objective,
                effort_days=stage_effort,
            )
        )
    return TrainingPlan(
        engagement_id=engagement_id,
        maturity_stage=maturity_stage,
        actions=actions,
    )


class WorkshopPack(BaseModel):
    """Track 6.2 workshop pack."""

    pack_id: str
    title: str
    agenda: list[str] = Field(default_factory=list)
    facilitation_prompts: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)


def get_workshop_pack(pack_id: str) -> WorkshopPack:
    try:
        payload = WORKSHOP_PACKS[pack_id]
    except KeyError as exc:
        known = ", ".join(sorted(WORKSHOP_PACKS))
        raise KeyError(
            f"Unknown workshop pack {pack_id!r}. Known: {known}"
        ) from exc
    return WorkshopPack(
        pack_id=pack_id,
        title=pack_id.replace("_", " ").title(),
        agenda=list(payload["agenda"]),
        facilitation_prompts=list(payload["prompts"]),
        deliverables=list(payload["deliverables"]),
    )


def list_workshop_packs() -> list[WorkshopPack]:
    return [get_workshop_pack(pid) for pid in sorted(WORKSHOP_PACKS)]


class InvesteeCoachingCard(BaseModel):
    """Track 6.3 investee coaching card tied to failed validations."""

    card_id: str = Field(default_factory=lambda: f"coach_{secrets.token_hex(4)}")
    entity_name: str
    failed_validation: str
    prescription: str
    example: str = ""
    severity: Literal["low", "medium", "high"] = "medium"


def build_coaching_card(
    *,
    entity_name: str,
    failed_validation: str,
    prescription: str = "",
    example: str = "",
    severity: Literal["low", "medium", "high"] = "medium",
) -> InvesteeCoachingCard:
    return InvesteeCoachingCard(
        entity_name=entity_name,
        failed_validation=failed_validation,
        prescription=prescription or (
            f"Address '{failed_validation}' before the next review cycle."
        ),
        example=example,
        severity=severity,
    )


class LearningLoopEntry(BaseModel):
    """Track 6.4 training → action → data → score loop."""

    loop_id: str = Field(default_factory=lambda: f"loop_{secrets.token_hex(4)}")
    training_assigned: str
    action_completed: str = ""
    data_improvement: str = ""
    score_change: float = 0.0
    reviewed_at: str = ""


def record_learning_loop(
    *,
    training_assigned: str,
    action_completed: str = "",
    data_improvement: str = "",
    score_change: float = 0.0,
) -> LearningLoopEntry:
    return LearningLoopEntry(
        training_assigned=training_assigned,
        action_completed=action_completed,
        data_improvement=data_improvement,
        score_change=score_change,
        reviewed_at=_now(),
    )


class ReadinessBadge(BaseModel):
    """Track 6.6 certification / readiness badge."""

    badge_id: str = Field(default_factory=lambda: f"badge_{secrets.token_hex(4)}")
    kind: BadgeKind
    issued_to: str
    criteria: str
    score: float = 0.0
    issued_at: str = Field(default_factory=lambda: _now())


def issue_readiness_badge(
    *,
    kind: BadgeKind,
    issued_to: str,
    score: float,
    criteria: str = "",
) -> ReadinessBadge:
    """Issue a readiness badge when a criterion threshold is met."""
    threshold = {
        "data_ready": 0.8,
        "report_ready": 0.8,
        "assurance_ready": 0.9,
        "lp_ready": 0.85,
    }[kind]
    if score < threshold:
        raise ValueError(
            f"Cannot issue {kind} badge — score {score} below threshold {threshold}."
        )
    return ReadinessBadge(
        kind=kind,
        issued_to=issued_to,
        criteria=criteria
        or f"{kind.replace('_', ' ').title()} criterion: score >= {threshold}",
        score=round(score, 3),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "BadgeKind",
    "InvesteeCoachingCard",
    "LearningLoopEntry",
    "MaturityStage",
    "ReadinessBadge",
    "TrainingAction",
    "TrainingPlan",
    "WORKSHOP_PACKS",
    "WorkshopPack",
    "build_coaching_card",
    "build_training_plan",
    "get_workshop_pack",
    "issue_readiness_badge",
    "list_workshop_packs",
    "record_learning_loop",
]
