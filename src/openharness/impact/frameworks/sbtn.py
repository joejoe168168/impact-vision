"""Science Based Targets Network five-step nature-readiness workflow."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from openharness.impact.models import Company


class SBTNStep(BaseModel):
    step: Literal["assess", "prioritise", "measure", "act", "track"]
    questions: list[dict] = Field(default_factory=list)
    complete: bool = False


_QUESTIONS = {
    "assess": [("A1", "Map value-chain nature pressures", "pressure inventory")],
    "prioritise": [
        ("P1", "Prioritise locations and pressures", "materiality and geospatial evidence")
    ],
    "measure": [("M1", "Measure baseline state and pressures", "baseline metrics")],
    "act": [("AC1", "Set and implement avoid-reduce-restore targets", "approved action plan")],
    "track": [("T1", "Track target progress and disclose", "verified monitoring records")],
}


def sbtn_readiness(company: Company, answers: dict) -> dict:
    steps = []
    for name, questions in _QUESTIONS.items():
        rows = [{"id": qid, "text": text, "evidence_ask": ask} for qid, text, ask in questions]
        complete = all(bool(answers.get(qid)) for qid, _, _ in questions)
        steps.append(SBTNStep(step=name, questions=rows, complete=complete))
    pct = round(100 * sum(step.complete for step in steps) / len(steps), 1)
    return {
        "company": company.name,
        "steps": [s.model_dump() for s in steps],
        "completion_pct": pct,
        "readiness_band": "ready" if pct == 100 else "developing" if pct >= 40 else "early",
        "next_actions": [q["text"] for s in steps if not s.complete for q in s.questions],
        "gbf_target_15": "Supports business assessment and disclosure under GBF Target 15",
        "status": "beta",
        "as_of": "2026-07",
        "citations": ["SBTN corporate manual", "Kunming-Montreal GBF Target 15"],
    }


def nature_target_ranges(
    pressure: Literal["land", "freshwater", "ocean", "biodiversity", "climate"], sector: str
) -> dict:
    defaults = {
        "land": [0, 5],
        "freshwater": [10, 25],
        "ocean": [10, 30],
        "biodiversity": [10, 30],
        "climate": [42, 50],
    }
    return {
        "pressure": pressure,
        "sector": sector or "unknown",
        "indicative_reduction_pct": defaults[pressure],
        "status": "indicative",
        "as_of": "2026-07",
        "citations": ["SBTN methods v1/v2 beta"],
    }


__all__ = ["SBTNStep", "nature_target_ranges", "sbtn_readiness"]
