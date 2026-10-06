"""User-facing strings for the decision report (v7 W2.1 / W2.5).

Every visible label goes through :func:`translator` so a language is just a
dictionary. Missing keys fall back to English, so a partial translation never
breaks a report.
"""

from __future__ import annotations

from collections.abc import Callable

EN: dict[str, str] = {
    "doc_title": "Impact assessment",
    "eyebrow": "Impact assessment",
    "generated": "Generated {date}",
    "standard": "IRIS+ {version}",
    "source": "Source: {source}",
    "skip": "Skip to report",
    "contents": "Contents",
    "notice_full": "Confidential — prepared for internal investment and LP use.",
    "notice_ic": "Confidential — prepared for the investment committee.",
    "notice_lp": "Confidential — prepared for the fund's limited partners.",
    "notice_regulator": "Prepared for regulatory review.",
    "notice_public": "Prepared for public disclosure.",
    # verdict
    "sec_verdict": "Recommendation",
    "verdict_pass": "Proceed to investment committee",
    "verdict_warn": "Conditional — resolve before IC",
    "verdict_insufficient": "Not IC-ready — insufficient evidence",
    "verdict_fail": "Do not proceed",
    "verdict_unknown": "No IC gate run",
    "why": "Why",
    "missing_data": "missing data",
    "confidence_evidence-based": "Confidence: scores rest on reported metrics.",
    "confidence_partial": "Confidence: partly evidenced — some scores rest on a few reported metrics.",
    "confidence_estimated": "Confidence: estimated from document text only — treat as a hypothesis.",
    # kpis
    "kpi_5d": "5 Dimensions score",
    "kpi_5d_sub": "Grade {grade} · {evidence}",
    "kpi_sdg": "Top SDG",
    "kpi_sdg_none": "None material",
    "kpi_gw": "Greenwashing risk",
    "kpi_evidence": "Evidence",
    "kpi_evidence_value": "{claims} claims",
    "kpi_evidence_sub": "{metrics} IRIS+ metrics · DD {dd}% covered",
    "kpi_evidence_sub_nodd": "{metrics} IRIS+ metrics",
    "evidence-based": "evidence-based",
    "partial": "partial evidence",
    "estimated": "estimated",
    # change our mind
    "sec_mind": "What would change our mind",
    "lede_mind": "The three pieces of evidence that would move this assessment most.",
    "mind_metric": "Report {name} ({id})",
    "mind_metric_why": "{dimension} is the weakest dimension ({score}/5, {evidence}); this is a core metric for the sector.",
    "mind_verify": "Independent verification of the headline claims",
    "mind_verify_why": "No third-party verification or audit was found for the main outcomes.",
    "mind_outcome": "Outcome evidence with a baseline or comparison group",
    "mind_outcome_why": "Most claims show change but not attribution (NESTA level 2); a comparison moves them to level 3.",
    "mind_adverse": "Negative-impact metrics for the sector",
    "mind_adverse_why": "Only positive metrics are reported; omissions raise greenwashing risk.",
    "mind_dd": "Answer: {question}",
    "mind_dd_why": "High-priority due-diligence question not answered by the documents.",
    # 5D
    "sec_5d": "Five Dimensions of Impact",
    "lede_5d": "Scored 1–5. The tick shows the sector benchmark where one exists.",
    "dim_what": "What",
    "dim_who": "Who",
    "dim_how_much": "How much",
    "dim_contribution": "Contribution",
    "dim_risk": "Risk",
    "legend_score": "Company score",
    "legend_bench": "Sector benchmark",
    "table_view": "Show as table",
    "col_dimension": "Dimension",
    "col_score": "Score",
    "col_benchmark": "Benchmark",
    "col_evidence": "Evidence",
    "col_notes": "Notes",
    # SDG
    "sec_sdg": "SDG alignment",
    "lede_sdg": "Material goals only (claimed, inferred from the business, or evidenced by a goal-specific metric), scored 0–100.",
    "sdg_other": "Other goals (context only): {goals}",
    "sdg_none": "No goal is material yet — report goal-specific IRIS+ metrics.",
    "col_goal": "Goal",
    "col_confidence": "Confidence",
    "col_metrics": "Matched metrics",
    # evidence
    "sec_evidence": "Evidence ledger",
    "lede_evidence": "Every claim found in the documents and every metric used in scoring.",
    "col_claim": "Claim",
    "col_type": "Type",
    "col_level": "NESTA level",
    "col_signals": "Evidence",
    "col_metric": "Metric",
    "col_value": "Value",
    "col_origin": "Origin",
    "origin_reported": "reported",
    "origin_extracted": "extracted from text",
    "origin_derived": "derived",
    "claims_caption": "Claims ({n})",
    "metrics_caption": "Metrics ({n})",
    "no_claims": "No claims were extracted.",
    "signal_third_party_verified": "Third-party verified",
    "signal_audited": "Audited",
    "signal_certified": "Certified",
    "signal_controlled_evaluation": "Controlled evaluation",
    "signal_baseline_comparison": "Baseline comparison",
    # greenwashing
    "sec_gw": "Greenwashing review",
    "lede_gw": "Components of the 0–100 risk score. At 60 or above risk is a finding; below it mostly reflects missing data.",
    "gw_claim_metric_gap": "Claims without metrics",
    "gw_adverse_omission": "Missing negative impacts",
    "gw_specificity": "Vague language",
    "gw_selectivity": "Selective reporting",
    "gw_verification": "No verification",
    "legend_component": "Risk component (0–100)",
    "legend_threshold": "Finding threshold (60)",
    "flags": "Flags",
    # risks & actions
    "sec_risks": "Risks and opportunities",
    "risks_disclosed": "Disclosed in the documents",
    "risks_sector": "Typical for the sector — check in diligence",
    "opportunities": "Opportunities",
    "sec_actions": "Action plan",
    "lede_actions": "De-duplicated next steps, most important first.",
    "area_metrics": "Metrics",
    "area_evidence": "Evidence",
    "area_sdg": "SDGs",
    "area_risk": "Risk",
    "area_evidence_quality": "Evidence quality",
    "area_5d": "Impact",
    # targets / feedback
    "sec_targets": "Impact targets",
    "col_target": "Target",
    "col_current": "Current",
    "col_status": "Status",
    "sec_feedback": "Beneficiary feedback",
    # appendix
    "sec_appendix": "Methodology and definitions",
    "method_title": "How this report was produced",
    "method_1": "Claims are extracted from the documents and graded on the NESTA standards of evidence; quantities are mapped to IRIS+ metric IDs only when unit and context are unambiguous.",
    "method_2": "Five Dimensions scores (1–5) come from reported metrics where available and from document text otherwise; the evidence label says which.",
    "method_3": "SDG scores (0–100) combine goal-specific metric coverage, inference from the business and impact themes; cross-cutting metrics count at reduced weight.",
    "method_4": "Greenwashing risk weights claim–metric gaps (30%), missing negative impacts (20%), vague language (20%), selective reporting (15%) and lack of verification (15%).",
    "method_5": "The IC gate applies the fund thesis thresholds; failures caused by missing data are reported as insufficient evidence, not as a negative finding.",
    "glossary_title": "Terms used in this report",
    "generated_by": "Generated by Impact Vision — open-source impact measurement.",
}

STRINGS: dict[str, dict[str, str]] = {"en": EN}


def translator(lang: str = "en") -> Callable[..., str]:
    """Return ``t(key, **fmt)`` for *lang*, falling back to English."""
    table = STRINGS.get(lang) or STRINGS.get(lang.split("-")[0]) or EN

    def t(key: str, **fmt: object) -> str:
        text = table.get(key) or EN.get(key) or key
        return text.format(**fmt) if fmt else text

    return t


__all__ = ["EN", "STRINGS", "translator"]
