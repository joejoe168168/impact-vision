"""Worker-voice aggregation channel (Phase 19).

Wires anonymised worker-voice survey data into the **Who** dimension of
the 5D assessment, giving the "Who" score a direct stakeholder input
instead of inferring it from company disclosures alone.

Inputs
------
Expects a :class:`SurveyDataset` returned by
:mod:`openharness.impact.surveys` or an equivalent adapter. The
aggregator looks for three signals:

1. **Net Promoter Score proxy** — ``nps_score`` column (0-10).
2. **Grievance rate** — ``grievance_reported`` boolean column.
3. **Anonymity attestation** — ``anonymous_submission`` boolean column.

Outputs
-------
A :class:`WorkerVoiceSummary` with the aggregates + a "Who lift" in
[-1, +1] that the orchestration layer can add to the 5D Who score
(before clamping back into [0, 5]).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.impact.surveys import SurveyDataset


class WorkerVoiceSummary(BaseModel):
    n_respondents: int
    nps_score: float | None = None
    grievance_rate_pct: float | None = None
    anonymity_guaranteed_pct: float | None = None
    who_lift: float = Field(ge=-1, le=1, default=0.0)
    rationale: str = ""


def summarise(dataset: SurveyDataset) -> WorkerVoiceSummary:
    n = dataset.n()
    if n == 0:
        return WorkerVoiceSummary(n_respondents=0,
                                  rationale="Empty survey dataset.")

    nps_values: list[float] = []
    grievances: list[bool] = []
    anonymous: list[bool] = []
    for r in dataset.responses:
        ans = r.answers
        if "nps_score" in ans:
            try:
                nps_values.append(float(ans["nps_score"]))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        if "grievance_reported" in ans:
            grievances.append(_to_bool(ans.get("grievance_reported")))
        if "anonymous_submission" in ans:
            anonymous.append(_to_bool(ans.get("anonymous_submission")))

    nps: float | None = None
    if nps_values:
        promoters = sum(1 for v in nps_values if v >= 9) / len(nps_values)
        detractors = sum(1 for v in nps_values if v <= 6) / len(nps_values)
        nps = round(100 * (promoters - detractors), 1)

    grievance_rate: float | None = None
    if grievances:
        grievance_rate = round(100 * sum(grievances) / len(grievances), 1)

    anonymity_pct: float | None = None
    if anonymous:
        anonymity_pct = round(100 * sum(anonymous) / len(anonymous), 1)

    # Map to a [-1, +1] Who lift with conservative weights.
    lift = 0.0
    reasons: list[str] = []
    if nps is not None:
        lift += (nps / 200.0)  # NPS ∈ [-100, 100] → [-0.5, 0.5]
        reasons.append(f"NPS {nps:+.1f} → {nps / 200.0:+.2f} lift")
    if grievance_rate is not None:
        lift -= grievance_rate / 200.0  # 20% grievances → -0.1
        reasons.append(f"grievance {grievance_rate:.1f}% → {-grievance_rate/200.0:+.2f}")
    if anonymity_pct is not None and anonymity_pct < 90:
        lift -= 0.1  # penalty for non-anonymous surveys
        reasons.append("anonymity <90% → -0.10 penalty")

    lift = max(-1.0, min(1.0, round(lift, 3)))

    return WorkerVoiceSummary(
        n_respondents=n,
        nps_score=nps,
        grievance_rate_pct=grievance_rate,
        anonymity_guaranteed_pct=anonymity_pct,
        who_lift=lift,
        rationale="; ".join(reasons) or "No Who-dimension signals found.",
    )


def _to_bool(v: object) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "t"}


__all__ = ["WorkerVoiceSummary", "summarise"]
