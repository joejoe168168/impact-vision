"""Fund-level analytics: SDG contribution, impact-weighted returns, additionality."""

from __future__ import annotations


def compute_weighted_sdg_contribution(
    company_results: list[dict],
) -> dict[int, float]:
    """Compute fund-level SDG contribution weighted by portfolio company materiality.

    Each company's SDG scores are weighted by (1) number of metrics reported
    and (2) 5D score to approximate materiality.
    """
    sdg_weighted: dict[int, float] = {}
    total_weight = 0.0

    for r in company_results:
        weight = (r.get("metrics_reported", 0) + 1) * max(r.get("five_dim_score", 1), 0.5)
        total_weight += weight
        for sdg in r.get("top_sdgs", []):
            goal = sdg["goal"]
            sdg_weighted[goal] = sdg_weighted.get(goal, 0) + sdg["score"] * weight

    if total_weight > 0:
        sdg_weighted = {g: round(v / total_weight, 1) for g, v in sdg_weighted.items()}

    return dict(sorted(sdg_weighted.items(), key=lambda x: x[1], reverse=True))


def impact_weighted_returns_stub(
    company_results: list[dict],
    financial_returns: dict[str, float] | None = None,
) -> dict:
    """Stub for impact-weighted returns calculation.

    When financial return data is available, this will compute impact-weighted
    returns using the methodology from the Impact-Weighted Accounts Initiative
    (Harvard Business School / Global Steering Group for Impact Investment).

    Currently returns a placeholder structure.
    """
    financial_returns = financial_returns or {}
    n = len(company_results)

    avg_impact = sum(r.get("five_dim_score", 0) for r in company_results) / n if n > 0 else 0

    return {
        "method": "impact-weighted_returns",
        "status": "stub",
        "note": "Provide financial_returns dict ({company_name: IRR%}) to compute impact-weighted returns",
        "portfolio_impact_score": round(avg_impact, 2),
        "companies_with_financial_data": len(financial_returns),
        "companies_without_financial_data": n - len(financial_returns),
    }


def assess_portfolio_additionality(
    company_results: list[dict],
) -> dict:
    """Heuristic additionality assessment for the portfolio.

    Evaluates whether the fund is contributing to outcomes that would not
    happen without its investment, based on available signals.
    """
    n = len(company_results)
    if n == 0:
        return {"additionality_score": 0, "signals": [], "classification": "insufficient_data"}

    signals: list[str] = []
    score = 0.0

    high_impact_count = sum(1 for r in company_results if r.get("five_dim_score", 0) >= 3.5)
    if high_impact_count > n * 0.5:
        signals.append(f"{high_impact_count}/{n} companies have strong impact scores (>=3.5/5)")
        score += 20

    avg_contribution = sum(r.get("contribution", 0) for r in company_results) / n
    if avg_contribution >= 3.0:
        signals.append(f"Average contribution score: {avg_contribution:.1f}/5 (strong additionality signal)")
        score += 25
    elif avg_contribution >= 2.0:
        signals.append(f"Average contribution score: {avg_contribution:.1f}/5 (moderate)")
        score += 10

    low_gap = sum(1 for r in company_results if r.get("gap_coverage", 0) >= 50)
    if low_gap > n * 0.5:
        signals.append(f"{low_gap}/{n} companies report >50% of core metrics (good measurement)")
        score += 15

    sdg_goals = set()
    for r in company_results:
        sdg_goals.update(s["goal"] for s in r.get("top_sdgs", []))
    if len(sdg_goals) >= 5:
        signals.append(f"Fund covers {len(sdg_goals)} SDGs (broad impact diversification)")
        score += 10

    sectors = set(r.get("sector", "") for r in company_results if r.get("sector"))
    if len(sectors) >= 3:
        signals.append(f"Fund spans {len(sectors)} sectors")
        score += 5

    total_metrics = sum(r.get("metrics_reported", 0) for r in company_results)
    if total_metrics >= n * 3:
        signals.append(f"{total_metrics} total metrics reported (strong measurement infrastructure)")
        score += 15
    elif total_metrics >= n:
        signals.append(f"{total_metrics} total metrics (moderate measurement)")
        score += 5

    score = min(100, score)
    if score >= 60:
        classification = "strong_additionality"
    elif score >= 35:
        classification = "moderate_additionality"
    else:
        classification = "weak_additionality"

    return {
        "additionality_score": round(score, 1),
        "classification": classification,
        "signals": signals,
        "recommendation": (
            "Strengthen contribution evidence with counterfactual analysis or market comparison"
            if score < 60 else "Fund demonstrates strong additionality signals"
        ),
    }
