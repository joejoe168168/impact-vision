"""Heuristic assessment of impact risks and opportunities."""

from __future__ import annotations

from openharness.impact.models import Company

_RISK_RULES: dict[str, dict[str, str]] = {
    "over-indebted": {"category": "social_harm", "risk": "Potential over-indebtedness of vulnerable clients", "severity": "high", "mitigation": "Set affordability limits and monitor repayment stress signals."},
    "privacy": {"category": "data_governance", "risk": "Data privacy and consent risk", "severity": "high", "mitigation": "Adopt privacy-by-design and third-party security audits."},
    "climate": {"category": "environmental", "risk": "Climate transition and physical risk exposure", "severity": "medium", "mitigation": "Define adaptation plans and emissions reduction targets."},
    "waste": {"category": "environmental", "risk": "Waste and pollution externalities", "severity": "medium", "mitigation": "Track waste streams and implement circular mitigation plans."},
    "labor": {"category": "social", "risk": "Labor standards and worker welfare risk", "severity": "medium", "mitigation": "Implement supplier and workforce labor compliance controls."},
    "grant": {"category": "business_model", "risk": "Grant dependence threatens long-term impact sustainability", "severity": "medium", "mitigation": "Diversify revenue and test unit economics of impact model."},
}

_OPPORTUNITY_RULES: dict[str, dict[str, str]] = {
    "financial inclusion": {"category": "inclusion", "opportunity": "Expand access to formal financial services for underserved groups", "time_horizon": "near_term"},
    "women": {"category": "equity", "opportunity": "Increase women-centered outcomes and gender equity positioning", "time_horizon": "near_term"},
    "smallholder": {"category": "livelihoods", "opportunity": "Raise smallholder productivity and rural income resilience", "time_horizon": "mid_term"},
    "renewable": {"category": "climate", "opportunity": "Scale decarbonization impact through renewable adoption", "time_horizon": "mid_term"},
    "education": {"category": "human_capital", "opportunity": "Improve education access and long-term employability outcomes", "time_horizon": "long_term"},
    "health": {"category": "wellbeing", "opportunity": "Improve affordability and reach of essential health services", "time_horizon": "mid_term"},
}

_SEVERITY_WEIGHT = {"low": 1.0, "medium": 2.0, "high": 3.0}


def assess_impact_risk_opportunity(company: Company) -> dict:
    """Return structured risk/opportunity assessment for a company."""
    text = f"{company.sector} {company.description} {' '.join(company.impact_themes)}".lower()

    risks: list[dict] = []
    opportunities: list[dict] = []

    for token, rule in _RISK_RULES.items():
        if token in text:
            risks.append({"trigger": token, **rule})

    for token, rule in _OPPORTUNITY_RULES.items():
        if token in text:
            opportunities.append({"trigger": token, **rule})

    metric_ids = set(company.reported_metrics.keys())
    missing_management_metrics = {"OD4091", "OI4732"} - metric_ids
    if missing_management_metrics:
        risks.append(
            {
                "trigger": "missing_management_metrics",
                "category": "impact_management",
                "risk": "Weak impact management control signals (targets/reporting not fully evidenced)",
                "severity": "medium",
                "mitigation": "Add OD4091 and OI4732 style metrics for targets and periodic performance reporting.",
            }
        )

    if not opportunities and company.sdg_claims:
        opportunities.append(
            {
                "trigger": "sdg_claims",
                "category": "sdg_execution",
                "opportunity": "Translate SDG claims into measurable outcomes and differentiated LP reporting",
                "time_horizon": "near_term",
            }
        )

    risk_score = _score_risks(risks)
    opportunity_score = _score_opportunities(opportunities)

    return {
        "risk_score": risk_score,
        "opportunity_score": opportunity_score,
        "risks": risks,
        "opportunities": opportunities,
        "priority_risks": [r for r in risks if r.get("severity") == "high"][:3] or risks[:3],
        "priority_opportunities": opportunities[:3],
    }


def _score_risks(risks: list[dict]) -> float:
    if not risks:
        return 15.0
    weighted = sum(_SEVERITY_WEIGHT.get(r.get("severity", "medium"), 2.0) for r in risks)
    return round(min(100.0, 20.0 + weighted * 12.0), 1)


def _score_opportunities(opportunities: list[dict]) -> float:
    if not opportunities:
        return 25.0
    return round(min(100.0, 30.0 + len(opportunities) * 14.0), 1)
