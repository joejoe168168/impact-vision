"""Heuristic assessment of impact risks and opportunities."""

from __future__ import annotations

from openharness.impact.models import Company

_DEFAULTS_RISK_RULES: dict[str, dict[str, str]] = {
    "over-indebted": {"category": "social_harm", "risk": "Potential over-indebtedness of vulnerable clients", "severity": "high", "likelihood": "medium", "mitigation": "Set affordability limits and monitor repayment stress signals."},
    "privacy": {"category": "data_governance", "risk": "Data privacy and consent risk", "severity": "high", "likelihood": "medium", "mitigation": "Adopt privacy-by-design and third-party security audits."},
    "climate": {"category": "environmental", "risk": "Climate transition and physical risk exposure", "severity": "medium", "likelihood": "high", "mitigation": "Define adaptation plans and emissions reduction targets."},
    "waste": {"category": "environmental", "risk": "Waste and pollution externalities", "severity": "medium", "likelihood": "medium", "mitigation": "Track waste streams and implement circular mitigation plans."},
    "labor": {"category": "social", "risk": "Labor standards and worker welfare risk", "severity": "medium", "likelihood": "medium", "mitigation": "Implement supplier and workforce labor compliance controls."},
    "grant": {"category": "business_model", "risk": "Grant dependence threatens long-term impact sustainability", "severity": "medium", "likelihood": "medium", "mitigation": "Diversify revenue and test unit economics of impact model."},
    "concentration": {"category": "concentration", "risk": "Revenue or beneficiary concentration in single geography or client", "severity": "medium", "likelihood": "medium", "mitigation": "Diversify across geographies and client segments."},
    "regulatory": {"category": "regulatory_policy", "risk": "Regulatory or policy change may undermine the business model", "severity": "high", "likelihood": "low", "mitigation": "Monitor regulatory landscape and build adaptability into the business model."},
    "compliance": {"category": "regulatory_policy", "risk": "Non-compliance with applicable regulations", "severity": "high", "likelihood": "low", "mitigation": "Establish compliance monitoring and legal review processes."},
    "reputation": {"category": "reputational", "risk": "Reputational risk from impact-washing or unintended harm", "severity": "high", "likelihood": "low", "mitigation": "Implement transparent reporting and independent verification."},
    "greenwash": {"category": "reputational", "risk": "Greenwashing or impact-washing risk from unsubstantiated claims", "severity": "high", "likelihood": "medium", "mitigation": "Ensure all impact claims are backed by measurable evidence."},
    "exit": {"category": "exit", "risk": "Exit strategy may erode impact outcomes for beneficiaries", "severity": "medium", "likelihood": "medium", "mitigation": "Include impact preservation clauses in shareholder agreements."},
    "data integrity": {"category": "data_integrity", "risk": "Self-reported data with no third-party verification", "severity": "medium", "likelihood": "high", "mitigation": "Establish data validation processes and plan for third-party audit."},
    "single source": {"category": "data_integrity", "risk": "Metrics rely on single data source without triangulation", "severity": "low", "likelihood": "high", "mitigation": "Cross-reference data from multiple sources (e.g., surveys + admin data)."},
}

_DEFAULTS_OPPORTUNITY_RULES: dict[str, dict[str, str]] = {
    "financial inclusion": {"category": "inclusion", "opportunity": "Expand access to formal financial services for underserved groups", "time_horizon": "near_term"},
    "women": {"category": "equity", "opportunity": "Increase women-centered outcomes and gender equity positioning", "time_horizon": "near_term"},
    "smallholder": {"category": "livelihoods", "opportunity": "Raise smallholder productivity and rural income resilience", "time_horizon": "mid_term"},
    "renewable": {"category": "climate", "opportunity": "Scale decarbonization impact through renewable adoption", "time_horizon": "mid_term"},
    "education": {"category": "human_capital", "opportunity": "Improve education access and long-term employability outcomes", "time_horizon": "long_term"},
    "health": {"category": "wellbeing", "opportunity": "Improve affordability and reach of essential health services", "time_horizon": "mid_term"},
    "circular economy": {"category": "environment", "opportunity": "Capture value from waste streams and reduce resource dependence", "time_horizon": "mid_term"},
    "digital": {"category": "technology", "opportunity": "Scale impact through digital delivery channels and data-driven insights", "time_horizon": "near_term"},
    "affordable housing": {"category": "livelihoods", "opportunity": "Address housing gap with scalable affordable solutions", "time_horizon": "mid_term"},
    "clean water": {"category": "environment", "opportunity": "Improve access to safe water and sanitation infrastructure", "time_horizon": "mid_term"},
    "nutrition": {"category": "wellbeing", "opportunity": "Improve nutrition outcomes for vulnerable populations", "time_horizon": "mid_term"},
    "climate adaptation": {"category": "climate", "opportunity": "Build climate resilience for vulnerable communities and ecosystems", "time_horizon": "long_term"},
    "youth": {"category": "human_capital", "opportunity": "Create pathways for youth employment and skills development", "time_horizon": "mid_term"},
    "biodiversity": {"category": "environment", "opportunity": "Protect and restore biodiversity through nature-based solutions", "time_horizon": "long_term"},
    "electrification": {"category": "climate", "opportunity": "Extend electrification to underserved areas", "time_horizon": "mid_term"},
    "telemedicine": {"category": "wellbeing", "opportunity": "Extend healthcare access through remote delivery models", "time_horizon": "near_term"},
}


def _load_rules() -> tuple[dict, dict]:
    """Load risk/opportunity rules from scoring config, fall back to defaults."""
    try:
        from openharness.impact.five_dimensions import _load_scoring_config
        config = _load_scoring_config()
        risk_rules = config.get("risk_rules", _DEFAULTS_RISK_RULES)
        opp_rules = config.get("opportunity_rules", _DEFAULTS_OPPORTUNITY_RULES)
        return risk_rules, opp_rules
    except Exception:
        return _DEFAULTS_RISK_RULES, _DEFAULTS_OPPORTUNITY_RULES

_SEVERITY_WEIGHT = {"low": 1.0, "medium": 2.0, "high": 3.0}
_LIKELIHOOD_WEIGHT = {"low": 0.5, "medium": 1.0, "high": 1.5}

_RISK_MATRIX: dict[tuple[str, str], str] = {
    ("high", "high"): "critical",
    ("high", "medium"): "high",
    ("high", "low"): "medium",
    ("medium", "high"): "high",
    ("medium", "medium"): "medium",
    ("medium", "low"): "low",
    ("low", "high"): "medium",
    ("low", "medium"): "low",
    ("low", "low"): "low",
}


def assess_impact_risk_opportunity(company: Company) -> dict:
    """Return structured risk/opportunity assessment for a company."""
    risk_rules, opp_rules = _load_rules()
    text = f"{company.sector} {company.description} {' '.join(company.impact_themes)}".lower()

    risks: list[dict] = []
    opportunities: list[dict] = []

    for token, rule in risk_rules.items():
        if token in text:
            severity = rule.get("severity", "medium")
            likelihood = rule.get("likelihood", "medium")
            risk_level = _RISK_MATRIX.get((severity, likelihood), "medium")
            risks.append({"trigger": token, "risk_level": risk_level, **rule})

    for token, rule in opp_rules.items():
        if token in text:
            opportunities.append({"trigger": token, **rule})

    metric_ids = set(company.reported_metrics.keys())
    missing_management_metrics = {"OD4091", "OI4732"} - metric_ids
    if missing_management_metrics:
        risks.append({
            "trigger": "missing_management_metrics",
            "category": "impact_management",
            "risk": "Weak impact management control signals (targets/reporting not fully evidenced)",
            "severity": "medium",
            "mitigation": "Add OD4091 and OI4732 style metrics for targets and periodic performance reporting.",
        })

    if not opportunities and company.sdg_claims:
        opportunities.append({
            "trigger": "sdg_claims",
            "category": "sdg_execution",
            "opportunity": "Translate SDG claims into measurable outcomes and differentiated LP reporting",
            "time_horizon": "near_term",
        })

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


def check_controversy_signals(company_name: str, description: str) -> dict:
    """Placeholder for external controversy data source integration.

    In production, this would query APIs like RepRisk, Sustainalytics,
    or news sentiment feeds. Currently returns a stub.
    """
    return {
        "data_source": "stub (no external API configured)",
        "company": company_name,
        "controversies_found": 0,
        "severity": "none",
        "categories": [],
        "note": "Connect an external controversy screening provider for live results.",
    }


def _score_risks(risks: list[dict]) -> float:
    if not risks:
        return 15.0
    weighted = sum(
        _SEVERITY_WEIGHT.get(r.get("severity", "medium"), 2.0)
        * _LIKELIHOOD_WEIGHT.get(r.get("likelihood", "medium"), 1.0)
        for r in risks
    )
    return round(min(100.0, 20.0 + weighted * 8.0), 1)


def _score_opportunities(opportunities: list[dict]) -> float:
    if not opportunities:
        return 25.0
    return round(min(100.0, 30.0 + len(opportunities) * 14.0), 1)
