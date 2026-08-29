"""Shift-aligned, sector-agnostic Just Transition assessment.

Encodes the 19 sector-agnostic metrics published by Shift, the Council for
Inclusive Capitalism, WBA, WBCSD and the LSE Just Transition Finance Lab
across three stakeholder groups (own workforce, communities, value-chain
workers) and four pillars (governance / strategy / risk & impact /
metrics & targets). Coverage is keyword- and evidence-based — callers do
not need to invent ``JT-01`` metric IDs.
"""

from __future__ import annotations

from typing import Any

from openharness.impact.models import Company, MetricRecord
from openharness.tools.impact.common import keyword_match_with_context

_GROUPS = ("own_workforce", "communities", "value_chain")
_PILLARS = ("governance", "strategy", "risk_impact", "metrics_targets")

# 19 sector-agnostic Just Transition metrics. Keywords are matched against
# company description, metric notes, reported values and the transition plan.
JT_METRICS: list[dict[str, Any]] = [
    {
        "id": "JT-01",
        "stakeholder_group": "own_workforce",
        "pillar": "governance",
        "metric": "Board / executive accountability for just transition",
        "outcome_focus": False,
        "gri_ref": "GRI 2-12",
        "tisfd_ref": "TISFD-GOVERNANCE",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "just transition governance",
            "board accountability",
            "transition committee",
            "executive remuneration climate",
            "just transition oversight",
        ),
        "iris_hints": (),
    },
    {
        "id": "JT-02",
        "stakeholder_group": "own_workforce",
        "pillar": "governance",
        "metric": "Social dialogue and worker representation in transition decisions",
        "outcome_focus": False,
        "gri_ref": "GRI 402",
        "tisfd_ref": "TISFD-GOVERNANCE",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "collective bargaining",
            "worker representation",
            "social dialogue",
            "trade union",
            "works council",
            "freedom of association",
        ),
        "iris_hints": ("OI1401", "OI1823"),
    },
    {
        "id": "JT-03",
        "stakeholder_group": "own_workforce",
        "pillar": "strategy",
        "metric": "Workforce transition, reskilling and redeployment plan",
        "outcome_focus": False,
        "gri_ref": "GRI 404",
        "tisfd_ref": "TISFD-STRATEGY",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "reskilling",
            "upskilling",
            "redeployment",
            "workforce transition",
            "retraining",
            "just transition plan",
        ),
        "iris_hints": ("PI2998", "PI8380"),
    },
    {
        "id": "JT-04",
        "stakeholder_group": "own_workforce",
        "pillar": "strategy",
        "metric": "Living-wage commitment for own employees",
        "outcome_focus": True,
        "gri_ref": "GRI 202-1",
        "tisfd_ref": "TISFD-STRATEGY",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "living wage",
            "living-wage",
            "wage floor",
            "fair wage",
            "anker methodology",
        ),
        "iris_hints": ("OI4202", "OI1671"),
    },
    {
        "id": "JT-05",
        "stakeholder_group": "own_workforce",
        "pillar": "risk_impact",
        "metric": "Job displacement and employment-security risk assessment",
        "outcome_focus": False,
        "gri_ref": "GRI 401",
        "tisfd_ref": "TISFD-RISK_IMPACT",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "job displacement",
            "employment security",
            "redundancy",
            "layoff risk",
            "job loss",
            "phase-out jobs",
        ),
        "iris_hints": ("PI4874",),
    },
    {
        "id": "JT-06",
        "stakeholder_group": "own_workforce",
        "pillar": "metrics_targets",
        "metric": "Share of own workforce paid at or above a living wage",
        "outcome_focus": True,
        "gri_ref": "GRI 202-1",
        "tisfd_ref": "TISFD-METRICS_TARGETS",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "living wage coverage",
            "workers above living wage",
            "wage gap closed",
            "paid a living wage",
        ),
        "iris_hints": ("OI4202",),
    },
    {
        "id": "JT-07",
        "stakeholder_group": "own_workforce",
        "pillar": "metrics_targets",
        "metric": "Workers reskilled, redeployed or supported through the transition",
        "outcome_focus": True,
        "gri_ref": "GRI 404-1",
        "tisfd_ref": "TISFD-METRICS_TARGETS",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "workers retrained",
            "employees reskilled",
            "training hours",
            "redeployed workers",
            "transition support",
        ),
        "iris_hints": ("PI2998", "PI8380"),
    },
    {
        "id": "JT-08",
        "stakeholder_group": "communities",
        "pillar": "governance",
        "metric": "Affected-community engagement, including FPIC where relevant",
        "outcome_focus": False,
        "gri_ref": "GRI 413",
        "tisfd_ref": "TISFD-GOVERNANCE",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "fpic",
            "free prior and informed consent",
            "community consultation",
            "affected community",
            "indigenous",
            "community engagement",
        ),
        "iris_hints": ("OI5690",),
    },
    {
        "id": "JT-09",
        "stakeholder_group": "communities",
        "pillar": "strategy",
        "metric": "Community economic diversification and livelihood support",
        "outcome_focus": True,
        "gri_ref": "GRI 413-1",
        "tisfd_ref": "TISFD-STRATEGY",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "economic diversification",
            "community livelihood",
            "local economic development",
            "alternative livelihoods",
            "community investment",
        ),
        "iris_hints": ("PI2251", "PI4060"),
    },
    {
        "id": "JT-10",
        "stakeholder_group": "communities",
        "pillar": "risk_impact",
        "metric": "Community impact assessment of the climate / nature transition",
        "outcome_focus": False,
        "gri_ref": "GRI 413-2",
        "tisfd_ref": "TISFD-RISK_IMPACT",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "community impact assessment",
            "social impact assessment",
            "community risk",
            "transition impact on communities",
        ),
        "iris_hints": ("OI5690",),
    },
    {
        "id": "JT-11",
        "stakeholder_group": "communities",
        "pillar": "metrics_targets",
        "metric": "Local employment and procurement from affected communities",
        "outcome_focus": True,
        "gri_ref": "GRI 204-1",
        "tisfd_ref": "TISFD-METRICS_TARGETS",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "local employment",
            "local procurement",
            "local hiring",
            "community jobs",
            "local suppliers",
        ),
        "iris_hints": ("PI4908", "OI1821"),
    },
    {
        "id": "JT-12",
        "stakeholder_group": "communities",
        "pillar": "metrics_targets",
        "metric": "Transition-related community investment",
        "outcome_focus": True,
        "gri_ref": "GRI 201-1",
        "tisfd_ref": "TISFD-METRICS_TARGETS",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "community investment",
            "community development fund",
            "just transition fund",
            "social investment",
        ),
        "iris_hints": ("PI2251",),
    },
    {
        "id": "JT-13",
        "stakeholder_group": "communities",
        "pillar": "risk_impact",
        "metric": "Accessible community grievance and remedy mechanism",
        "outcome_focus": False,
        "gri_ref": "GRI 2-25",
        "tisfd_ref": "TISFD-RISK_IMPACT",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "community grievance",
            "grievance mechanism",
            "remedy",
            "complaints mechanism",
            "ungp 31",
        ),
        "iris_hints": ("OI1042", "OI5049"),
    },
    {
        "id": "JT-14",
        "stakeholder_group": "value_chain",
        "pillar": "governance",
        "metric": "Supplier just-transition / labour requirements",
        "outcome_focus": False,
        "gri_ref": "GRI 414",
        "tisfd_ref": "TISFD-GOVERNANCE",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "supplier code",
            "supplier labour",
            "value chain standards",
            "responsible procurement",
            "supplier human rights",
        ),
        "iris_hints": ("OI1126",),
    },
    {
        "id": "JT-15",
        "stakeholder_group": "value_chain",
        "pillar": "strategy",
        "metric": "Supply-chain worker reskilling and transition support",
        "outcome_focus": False,
        "gri_ref": "GRI 414-1",
        "tisfd_ref": "TISFD-STRATEGY",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "supplier training",
            "value chain reskilling",
            "supply chain workers",
            "supplier transition support",
        ),
        "iris_hints": (),
    },
    {
        "id": "JT-16",
        "stakeholder_group": "value_chain",
        "pillar": "risk_impact",
        "metric": "Value-chain displacement, informality and wage-poverty risk",
        "outcome_focus": False,
        "gri_ref": "GRI 414-2",
        "tisfd_ref": "TISFD-RISK_IMPACT",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "informal worker",
            "supply chain displacement",
            "value chain risk",
            "supplier wage",
            "forced labour",
            "child labour",
        ),
        "iris_hints": ("OI8866",),
    },
    {
        "id": "JT-17",
        "stakeholder_group": "value_chain",
        "pillar": "metrics_targets",
        "metric": "Living-wage coverage in the supply chain",
        "outcome_focus": True,
        "gri_ref": "GRI 202-1",
        "tisfd_ref": "TISFD-METRICS_TARGETS",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "supplier living wage",
            "supply chain living wage",
            "value chain living wage",
            "fair trade wage",
        ),
        "iris_hints": ("OI4202",),
    },
    {
        "id": "JT-18",
        "stakeholder_group": "value_chain",
        "pillar": "metrics_targets",
        "metric": "Supplier worker voice and freedom of association",
        "outcome_focus": True,
        "gri_ref": "GRI 407",
        "tisfd_ref": "TISFD-METRICS_TARGETS",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "supplier union",
            "supplier worker voice",
            "value chain freedom of association",
            "supplier collective bargaining",
        ),
        "iris_hints": ("OI1401",),
    },
    {
        "id": "JT-19",
        "stakeholder_group": "value_chain",
        "pillar": "strategy",
        "metric": "Responsible phase-out and just procurement commitments",
        "outcome_focus": False,
        "gri_ref": "GRI 3-3",
        "tisfd_ref": "TISFD-STRATEGY",
        "source": "Shift / WBA / WBCSD / LSE Just Transition metrics",
        "keywords": (
            "responsible phase-out",
            "just procurement",
            "managed decline",
            "no stranded workers",
            "supplier offboarding",
        ),
        "iris_hints": (),
    },
]


def _evidence_corpus(
    company: Company,
    records: list[MetricRecord],
    transition_plan: dict | None,
) -> str:
    parts: list[str] = [
        company.description or "",
        " ".join(company.impact_themes),
        company.sector or "",
    ]
    for key, value in (company.reported_metrics or {}).items():
        parts.append(str(key))
        parts.append(str(value))
    for record in records:
        parts.extend(
            [
                record.metric_id,
                record.notes or "",
                record.methodology or "",
                str(record.value),
            ]
        )
    if transition_plan:
        parts.append(str(transition_plan))
    if company.beneficiary_feedback is not None:
        fb = company.beneficiary_feedback
        parts.extend(fb.themes)
        parts.extend(fb.challenges)
        parts.append(fb.methodology or "")
    return " ".join(parts)


def _metric_covered(metric: dict[str, Any], corpus: str, reported_ids: set[str]) -> bool:
    haystack = corpus.lower()
    if metric["id"].lower() in haystack or metric["metric"].lower() in haystack:
        return True
    if any(hint.upper() in reported_ids for hint in metric.get("iris_hints") or ()):
        return True
    return any(
        keyword_match_with_context(corpus, keyword) for keyword in metric.get("keywords") or ()
    )


def assess_just_transition(
    company: Company,
    records: list[MetricRecord],
    transition_plan: dict | None,
    *,
    wages: list[dict] | None = None,
    wage_geography: str | None = None,
) -> dict:
    corpus = _evidence_corpus(company, records, transition_plan)
    reported_ids = {str(key).upper() for key in (company.reported_metrics or {})}
    reported_ids.update(record.metric_id.upper() for record in records)

    covered = [metric for metric in JT_METRICS if _metric_covered(metric, corpus, reported_ids)]
    covered_ids = {metric["id"] for metric in covered}

    def _pct(items: list[dict[str, Any]]) -> float:
        if not items:
            return 0.0
        return round(100 * sum(item["id"] in covered_ids for item in items) / len(items), 1)

    by_group = {
        group: _pct([m for m in JT_METRICS if m["stakeholder_group"] == group])
        for group in _GROUPS
    }
    by_pillar = {
        pillar: _pct([m for m in JT_METRICS if m["pillar"] == pillar]) for pillar in _PILLARS
    }

    plan_text = str(transition_plan or {}).lower()
    linkage = any(
        term in plan_text
        for term in (
            "worker",
            "community",
            "livelihood",
            "just transition",
            "reskill",
            "living wage",
            "social dialogue",
        )
    )
    feedback = company.beneficiary_feedback
    worker_voice_signal = bool(
        (feedback is not None and (feedback.sample_size or 0) > 0)
        or any(
            keyword_match_with_context(corpus, term)
            for term in (
                "worker voice",
                "employee survey",
                "collective bargaining",
                "worker representation",
            )
        )
    )

    living_wage = None
    if wages is not None:
        from openharness.impact.living_wage import living_wage_gap

        living_wage = living_wage_gap(wage_geography or company.geography, wages)

    coverage_pct = round(100 * len(covered) / len(JT_METRICS), 1)
    if coverage_pct >= 75 and linkage:
        band = "aligned"
    elif coverage_pct >= 40:
        band = "developing"
    else:
        band = "early"

    return {
        "company": company.name,
        "coverage_pct": coverage_pct,
        "readiness_band": band,
        "per_stakeholder_group": by_group,
        "per_pillar": by_pillar,
        "transition_plan_people_linked": linkage,
        "worker_voice_signal": worker_voice_signal,
        "living_wage": living_wage,
        "covered": [m["id"] for m in covered],
        "gaps": [m["id"] for m in JT_METRICS if m["id"] not in covered_ids],
        "gap_details": [
            {"id": m["id"], "metric": m["metric"], "group": m["stakeholder_group"]}
            for m in JT_METRICS
            if m["id"] not in covered_ids
        ],
        "status": "indicative",
        "as_of": "2026-07",
        "citations": [
            "Shift / Council for Inclusive Capitalism / WBA / WBCSD / LSE Just Transition Finance Lab, 19 sector-agnostic metrics",
            "GRI 202 / 402 / 404 / 407 / 413 / 414",
            "TISFD beta (social & inequality disclosures)",
        ],
    }


__all__ = ["JT_METRICS", "assess_just_transition"]
