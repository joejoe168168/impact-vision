"""Shift-aligned, sector-agnostic Just Transition assessment."""

from __future__ import annotations
from openharness.impact.models import Company, MetricRecord

_GROUPS = ("own_workforce", "communities", "value_chain")
_PILLARS = ("governance", "strategy", "risk_impact", "metrics_targets")
JT_METRICS = [
    {
        "id": f"JT-{i:02d}",
        "stakeholder_group": _GROUPS[(i - 1) % 3],
        "pillar": _PILLARS[(i - 1) % 4],
        "metric": f"Just Transition practice metric {i}",
        "outcome_focus": i % 2 == 0,
        "gri_ref": "GRI 3-3",
        "tisfd_ref": f"TISFD-{_PILLARS[(i - 1) % 4].upper()}",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
    }
    for i in range(1, 20)
]


def assess_just_transition(
    company: Company,
    records: list[MetricRecord],
    transition_plan: dict | None,
    *,
    wages: list[dict] | None = None,
    wage_geography: str | None = None,
) -> dict:
    evidence = " ".join(
        [record.notes for record in records] + [record.metric_id for record in records]
    ).lower()
    covered = [
        metric
        for metric in JT_METRICS
        if metric["id"].lower() in evidence or metric["metric"].lower() in evidence
    ]
    by_group = {
        group: round(
            100
            * sum(m in covered for m in JT_METRICS if m["stakeholder_group"] == group)
            / sum(m["stakeholder_group"] == group for m in JT_METRICS),
            1,
        )
        for group in _GROUPS
    }
    by_pillar = {
        pillar: round(
            100
            * sum(m in covered for m in JT_METRICS if m["pillar"] == pillar)
            / sum(m["pillar"] == pillar for m in JT_METRICS),
            1,
        )
        for pillar in _PILLARS
    }
    plan_text = str(transition_plan or {}).lower()
    linkage = any(
        term in plan_text for term in ("worker", "community", "livelihood", "just transition")
    )
    living_wage = None
    if wages is not None:
        from openharness.impact.living_wage import living_wage_gap

        living_wage = living_wage_gap(wage_geography or company.geography, wages)
    return {
        "company": company.name,
        "coverage_pct": round(100 * len(covered) / 19, 1),
        "per_stakeholder_group": by_group,
        "per_pillar": by_pillar,
        "transition_plan_people_linked": linkage,
        "worker_voice_signal": bool(company.beneficiary_feedback),
        "living_wage": living_wage,
        "gaps": [m["id"] for m in JT_METRICS if m not in covered],
    }


__all__ = ["JT_METRICS", "assess_just_transition"]
