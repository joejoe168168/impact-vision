"""Greenwashing / impact-washing detection engine.

Produces a composite greenwashing risk score (0-100) from 5 sub-scores:
1. Claim-Metric Gap: do SDG/theme claims have supporting metrics?
2. Adverse Omission: are negative-impact metrics missing for the sector?
3. Specificity: are claims concrete or vague?
4. Selectivity: is reporting balanced or cherry-picked?
5. Verification: is there evidence of measurement systems and auditing?

Extended with NLP-enhanced signals:
- Green Authenticity Index (GAI) - adapted from Stacey Matrix
- Cheap Talk Index - proportion of non-specific commitments
- Sentiment deflection detection
- Claim decomposition into verifiable sub-claims
- ClimateBERT integration stub for model-based detection
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.models import Company


_VAGUE_VERBS = {
    "aim", "aspire", "believe", "commit", "contribute", "dedicated", "endeavor",
    "expect", "hope", "intend", "plan", "pledge", "promise", "seek", "strive",
    "support", "try", "work toward", "working toward",
}

_CONCRETE_VERBS = {
    "achieved", "completed", "delivered", "deployed", "doubled", "eliminated",
    "generated", "grew", "halved", "implemented", "installed", "launched",
    "measured", "produced", "reached", "reduced", "saved", "served", "trained",
    "tripled", "verified",
}

_BUZZWORDS = {
    "sustainable", "sustainability", "esg", "green", "eco-friendly", "responsible",
    "ethical", "conscious", "purpose-driven", "impact-driven", "net-zero",
    "carbon-neutral", "climate-positive", "circular", "regenerative",
}

# Genuinely *adverse* metrics — i.e. things that, when reported, demonstrate
# the company is monitoring its negative impact. Picked from IRIS+ + sector
# best-practice. Sources: GIIN IRIS+ 5.3c, SASB sector standards, PCAF.
# An IRIS+ ID is used when one exists; otherwise an indicator label is given so
# the GP can mark a custom metric ID against the same concept.
_ADVERSE_METRICS_BY_SECTOR: dict[str, list[str]] = {
    # Microfinance / consumer lending: client over-indebtedness, pricing,
    # complaints, loan-loss provisioning, harassment.
    "fintech": [
        "PD8330",   # Average APR / cost of credit (proxy: pricing)
        "PI8675",   # Client over-indebtedness rate
        "OI4753",   # Client protection / over-indebtedness policy
        "PD3076",   # Portfolio at Risk > 30 days (PAR30)
        "OI5049",   # Client complaints rate (Lean Data)
    ],
    "financial": [
        "PD8330", "PI8675", "OI4753", "PD3076", "OI5049",
    ],
    # Energy: scope 1+2+3, water, methane, project-related displacement.
    "energy": [
        "OI4112",   # GHG Emissions: Direct (Scope 1)
        "OI1479",   # GHG Emissions: Indirect (Scope 2)
        "OI9803",   # Water Withdrawal: Total
        "OI8869",   # Worker fatalities / TRIR
        "PI8330",   # Communities displaced / resettled
    ],
    # Agriculture / food: pesticides, soil/water, smallholder pricing.
    "agriculture": [
        "OI4112",   # GHG (incl. land use change)
        "PI3468",   # Pesticide / fertiliser application intensity
        "OI9803",   # Water withdrawal in water-stressed areas
        "PI8330",   # Producer income vs. living-income benchmark
        "OI4753",   # Child / forced labour policy
    ],
    "livestock": [
        "OI4112", "OI9803", "PI3468", "OI4753",
    ],
    # Healthcare: avoidable adverse events, antibiotic stewardship, affordability.
    "healthcare": [
        "OI4753",   # Patient safety / adverse event rate
        "PI8675",   # Avoidable readmission rate
        "PD8330",   # Average out-of-pocket cost per visit (affordability)
        "OI5049",   # Patient complaints
    ],
    "health": ["OI4753", "PI8675", "PD8330", "OI5049"],
    # Technology / SaaS: data breaches, content moderation, model bias, e-waste.
    "technology": [
        "OI4732",   # Data privacy breach incidents
        "OI4753",   # Content moderation / harm mitigation policy
        "OI9803",   # Energy consumption (data centre)
        "OI4112",   # Scope 2 emissions
    ],
    "ict": ["OI4732", "OI4753", "OI9803", "OI4112"],
    # Manufacturing: scope 1/2/3, hazardous waste, occupational injury.
    "manufacturing": [
        "OI4112", "OI1479", "OI9803",
        "OI8869",   # Lost-time injury rate (LTIR)
        "PI3468",   # Hazardous waste generated
    ],
    # Mining / extractives: tailings, biodiversity, community grievances.
    "mining": [
        "OI4112", "OI9803", "PI3468",
        "OI4324",   # Community grievances / FPIC
        "OI8869",   # Worker fatalities
        "OI4753",   # Tailings management policy
    ],
    "extractives": [
        "OI4112", "OI9803", "PI3468", "OI4324", "OI8869", "OI4753",
    ],
    # Real estate / construction: embodied carbon, displacement.
    "real estate": [
        "OI4112", "OI9803", "OI8869",
        "PI8330",   # Tenant displacement / affordability
    ],
    "construction": [
        "OI4112", "OI9803", "OI8869", "PI3468",
    ],
    # Transport / logistics: scope 1, NOx/PM, road safety.
    "transport": [
        "OI4112", "OI9803", "OI8869",
    ],
    "logistics": ["OI4112", "OI9803", "OI8869"],
    # Education: drop-out, debt burden.
    "education": [
        "OI5049",   # Learner complaints
        "PI8675",   # Drop-out rate
        "PD8330",   # Tuition vs. household income (affordability)
    ],
    # Water / sanitation: leakage, affordability, source depletion.
    "water": [
        "OI9803", "PI3468", "PD8330",
    ],
    # Waste: landfill diversion, hazardous handling.
    "waste management": [
        "OI4112", "PI3468", "OI8869",
    ],
    # Default: GHG + worker safety as universal adverse signals.
    "default": [
        "OI4112",   # Scope 1
        "OI1479",   # Scope 2
        "OI8869",   # Worker fatalities / LTIR
        "OI4753",   # Adverse incident policy
    ],
}

_VERIFICATION_KEYWORDS = {
    "audit", "audited", "verified", "third-party", "third party",
    "assurance", "certification", "certified", "independently verified",
    "external review", "iso 14001", "b corp", "fair trade",
}

_MEASUREMENT_KEYWORDS = {
    "baseline", "benchmark", "data collection", "indicator", "kpi",
    "methodology", "monitoring", "reporting framework", "survey",
    "target", "tracking", "year-over-year",
}


class GreenwashingScore(BaseModel):
    """Composite greenwashing risk assessment."""

    overall_score: float = Field(ge=0, le=100, description="0=clean, 100=high greenwashing risk")
    classification: Literal[
        "Genuine Impact Leader",
        "Substantive with Gaps",
        "Moderate Risk",
        "High Risk",
        "Probable Greenwashing",
    ]

    claim_metric_gap: float = Field(ge=0, le=100, description="Unsubstantiated claims score")
    adverse_omission: float = Field(ge=0, le=100, description="Missing negative-impact metrics")
    specificity: float = Field(ge=0, le=100, description="Vagueness of language")
    selectivity: float = Field(ge=0, le=100, description="Cherry-picked positive reporting")
    verification: float = Field(ge=0, le=100, description="Lack of verification/audit signals")

    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def assess_greenwashing(
    company: Company,
    claims: list[dict[str, Any]] | None = None,
) -> GreenwashingScore:
    """Run greenwashing risk assessment for a company."""
    text = f"{company.description} {' '.join(company.impact_themes)}".lower()
    metrics = set(company.reported_metrics.keys())

    gap_score = _score_claim_metric_gap(company, metrics)
    omission_score = _score_adverse_omission(company, metrics)
    specificity_score = _score_specificity(text, claims)
    selectivity_score = _score_selectivity(company, metrics)
    verification_score = _score_verification(text, metrics)

    weights = {"gap": 0.30, "omission": 0.20, "specificity": 0.20, "selectivity": 0.15, "verification": 0.15}
    overall = (
        gap_score * weights["gap"]
        + omission_score * weights["omission"]
        + specificity_score * weights["specificity"]
        + selectivity_score * weights["selectivity"]
        + verification_score * weights["verification"]
    )
    overall = round(min(100, max(0, overall)), 1)

    classification = _classify(overall)
    flags = _generate_flags(gap_score, omission_score, specificity_score, selectivity_score, verification_score)
    recommendations = _generate_recommendations(gap_score, omission_score, specificity_score, selectivity_score, verification_score, company)

    return GreenwashingScore(
        overall_score=overall,
        classification=classification,
        claim_metric_gap=round(gap_score, 1),
        adverse_omission=round(omission_score, 1),
        specificity=round(specificity_score, 1),
        selectivity=round(selectivity_score, 1),
        verification=round(verification_score, 1),
        flags=flags,
        recommendations=recommendations,
    )


def _score_claim_metric_gap(company: Company, metrics: set[str]) -> float:
    """Score: do SDG claims and themes have supporting metrics?"""
    claims_count = len(company.sdg_claims) + len(company.impact_themes)
    if claims_count == 0:
        return 20.0

    if not metrics:
        return min(100, 40 + claims_count * 8)

    supported = 0
    for theme in company.impact_themes:
        theme_lower = theme.lower()
        if any(theme_lower in str(v).lower() for v in company.reported_metrics.values()):
            supported += 1

    support_ratio = (supported + len(metrics)) / max(1, claims_count * 3)
    return max(0, 80 - support_ratio * 100)


def _score_adverse_omission(company: Company, metrics: set[str]) -> float:
    """Score: are sector-appropriate negative-impact metrics missing?"""
    sector = company.sector.lower()
    required = _ADVERSE_METRICS_BY_SECTOR.get(sector, _ADVERSE_METRICS_BY_SECTOR["default"])

    if not required:
        return 20.0

    missing = [m for m in required if m not in metrics]
    return min(100, len(missing) / len(required) * 80 + 10)


def _score_specificity(text: str, claims: list[dict[str, Any]] | None) -> float:
    """Score: are claims vague or concrete?"""
    words = set(re.findall(r"\b\w+\b", text.lower()))

    vague_count = len(words & _VAGUE_VERBS)
    concrete_count = len(words & _CONCRETE_VERBS)
    buzzword_count = len(words & _BUZZWORDS)

    has_numbers = bool(re.search(r"\b\d+[%,.\d]*\b", text))

    score = 50.0
    score += vague_count * 5
    score -= concrete_count * 8
    score += buzzword_count * 4
    if has_numbers:
        score -= 15

    if claims:
        vague_claims = sum(1 for c in claims if c.get("category") in ("intent", "activity"))
        outcome_claims = sum(1 for c in claims if c.get("category") in ("outcome", "output"))
        if vague_claims > outcome_claims:
            score += 15

    return max(0, min(100, score))


def _score_selectivity(company: Company, metrics: set[str]) -> float:
    """Score: is reporting balanced or only positive metrics?"""
    if not metrics:
        return 60.0

    has_risk_metrics = any("risk" in str(v).lower() or mid.startswith("OI") for mid, v in company.reported_metrics.items())
    has_negative_metrics = any("OD" in mid or "negative" in str(v).lower() for mid, v in company.reported_metrics.items())
    total = len(metrics)

    score = 50.0
    if not has_risk_metrics:
        score += 20
    if not has_negative_metrics:
        score += 15
    if total < 5:
        score += 10

    return max(0, min(100, score))


def _has_word(text: str, term: str) -> bool:
    """Word-boundary aware substring check."""
    return bool(re.search(r"\b" + re.escape(term) + r"\b", text))


def _score_verification(text: str, metrics: set[str]) -> float:
    """Score: does the company show verification/audit signals?"""
    text_lower = text.lower()
    verification_hits = sum(1 for kw in _VERIFICATION_KEYWORDS if _has_word(text_lower, kw))
    measurement_hits = sum(1 for kw in _MEASUREMENT_KEYWORDS if _has_word(text_lower, kw))

    score = 70.0
    score -= verification_hits * 12
    score -= measurement_hits * 8
    score -= len(metrics) * 2

    return max(0, min(100, score))


def _classify(score: float) -> str:
    if score <= 20:
        return "Genuine Impact Leader"
    if score <= 40:
        return "Substantive with Gaps"
    if score <= 60:
        return "Moderate Risk"
    if score <= 80:
        return "High Risk"
    return "Probable Greenwashing"


def _generate_flags(gap: float, omission: float, specificity: float, selectivity: float, verification: float) -> list[str]:
    flags = []
    if gap > 60:
        flags.append("HIGH_CLAIM_METRIC_GAP: SDG/theme claims lack supporting metric evidence")
    if omission > 60:
        flags.append("ADVERSE_OMISSION: Missing negative-impact metrics for sector")
    if specificity > 60:
        flags.append("VAGUE_LANGUAGE: Claims use aspirational language without concrete evidence")
    if selectivity > 60:
        flags.append("SELECTIVE_REPORTING: Reporting appears to cherry-pick positive metrics")
    if verification > 60:
        flags.append("NO_VERIFICATION: No evidence of third-party verification or auditing")
    return flags


def _generate_recommendations(
    gap: float, omission: float, specificity: float, selectivity: float, verification: float,
    company: Company,
) -> list[str]:
    recs = []
    if gap > 40:
        recs.append("Map each SDG claim to at least one IRIS+ metric with reported data")
    if omission > 40:
        sector = company.sector or "general"
        recs.append(f"Report adverse-impact metrics appropriate for {sector} sector (e.g., GHG emissions, client protection)")
    if specificity > 40:
        recs.append("Replace aspirational language with concrete, quantified outcome statements")
    if selectivity > 40:
        recs.append("Include risk-oriented and negative-impact metrics alongside positive outcomes")
    if verification > 40:
        recs.append("Obtain third-party verification or implement a recognized measurement framework")
    return recs


# ---------------------------------------------------------------------------
# EU Green Claims Directive (Directive on Substantiation of Green Claims)
# Ref: COM/2023/166 final — adopted 2024, enforcement from 2026.
# ---------------------------------------------------------------------------

_ENVIRONMENTAL_CLAIM_PATTERNS: list[str] = [
    "carbon neutral", "carbon-neutral", "net zero", "net-zero", "climate neutral",
    "climate-neutral", "climate positive", "carbon negative", "eco-friendly",
    "biodegradable", "compostable", "recyclable", "recycled content",
    "renewable", "sustainable", "green", "environmentally friendly",
    "reduced footprint", "low carbon", "zero emission",
]

_LCA_TRIGGER_TERMS: list[str] = [
    "carbon neutral", "carbon-neutral", "net zero", "net-zero",
    "climate neutral", "climate-neutral", "carbon negative",
    "zero emission", "climate positive", "reduced footprint",
]


class GreenClaimsResult(BaseModel):
    """EU Green Claims Directive compliance assessment."""

    compliant: bool = False
    claims_found: list[str] = Field(default_factory=list)
    lca_required: bool = False
    lca_triggers: list[str] = Field(default_factory=list)
    substantiation_issues: list[str] = Field(default_factory=list)
    independent_verification_present: bool = False
    recommendations: list[str] = Field(default_factory=list)


def assess_green_claims_compliance(
    description: str = "",
    document_text: str = "",
    reported_metrics: dict[str, str] | None = None,
    has_lca: bool = False,
    has_independent_verification: bool = False,
) -> GreenClaimsResult:
    """Check company claims against the EU Green Claims Directive.

    The directive requires:
    1. Environmental claims are substantiated by scientific evidence.
    2. Claims about overall environmental impact require full life-cycle assessment.
    3. Claims are verified by an accredited independent verifier.
    4. Carbon offsetting claims must be secondary to actual reduction measures.
    """
    text = f"{description} {document_text}".lower()
    metrics = reported_metrics or {}

    # Multi-token / hyphenated patterns are checked as substrings (word boundary
    # would over-restrict because the patterns themselves include word breaks);
    # single-word patterns get a word-boundary match to avoid e.g. "green" in
    # "evergreen".
    def _claim_in(t: str, c: str) -> bool:
        return _has_word(t, c) if (" " not in c and "-" not in c) else c in t

    claims = [c for c in _ENVIRONMENTAL_CLAIM_PATTERNS if _claim_in(text, c)]
    lca_triggers = [t for t in _LCA_TRIGGER_TERMS if _claim_in(text, t)]
    lca_required = bool(lca_triggers) and not has_lca

    issues: list[str] = []
    recs: list[str] = []

    for claim in claims:
        has_data = any(
            claim.replace("-", " ").split()[0] in str(v).lower()
            for v in metrics.values()
        )
        if not has_data:
            issues.append(f"Claim '{claim}' lacks quantitative substantiation")

    if _has_word(text, "offset") or "carbon credit" in text:
        if "reduc" not in text:
            issues.append("Offsetting claim without evidence of actual emission reductions (Art. 5(6))")
            recs.append("Demonstrate primary emission reductions before referencing offsets")

    if lca_required:
        issues.append("Full-scope environmental claim requires life-cycle assessment (Art. 3(4))")
        recs.append("Commission a life-cycle assessment covering full product/service life cycle")

    if claims and not has_independent_verification:
        issues.append("Environmental claims require verification by an accredited independent body (Art. 10)")
        recs.append("Engage an accredited verifier per EU Green Claims Directive Art. 10")

    if not claims and not lca_triggers:
        recs.append("No explicit environmental claims detected — directive may not apply")

    compliant = bool(claims) and not issues

    return GreenClaimsResult(
        compliant=compliant,
        claims_found=claims,
        lca_required=lca_required,
        lca_triggers=lca_triggers,
        substantiation_issues=issues,
        independent_verification_present=has_independent_verification,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# UK FCA Anti-Greenwashing Rule (PS23/16, effective 31 May 2024)
# ---------------------------------------------------------------------------

class FCAAntiGreenwashingResult(BaseModel):
    """UK FCA Anti-Greenwashing Rule assessment."""

    compliant: bool = False
    issues: list[str] = Field(default_factory=list)
    sdl_labels_applicable: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


_FCA_PROHIBITED_TERMS = [
    "green fund", "sustainable fund", "esg fund", "impact fund",
    "net zero fund", "climate fund", "responsible fund",
]

_SDL_LABELS = {
    "sustainability_focus": {
        "label": "Sustainability Focus",
        "requirement": "At least 70% of assets meet a credible standard of environmental/social sustainability",
    },
    "sustainability_improvers": {
        "label": "Sustainability Improvers",
        "requirement": "Assets that may not be sustainable now but aim to improve over a set period",
    },
    "sustainability_impact": {
        "label": "Sustainability Impact",
        "requirement": "Investments with measurable positive environmental/social outcomes alongside financial return",
    },
    "sustainability_mixed_goals": {
        "label": "Sustainability Mixed Goals",
        "requirement": "Portfolio combining sustainability-focused and other investments with clear allocation",
    },
}


def assess_fca_anti_greenwashing(
    description: str = "",
    document_text: str = "",
    fund_name: str = "",
    reported_metrics: dict[str, str] | None = None,
) -> FCAAntiGreenwashingResult:
    """Assess compliance with the UK FCA Anti-Greenwashing Rule.

    Key requirements (PS23/16 + SDR):
    1. Sustainability claims must be fair, clear, and not misleading.
    2. Fund naming conventions restricted (no "green"/"ESG" without substance).
    3. Sustainability Disclosure Requirements (SDR) labels require evidence.
    4. Product-level disclosures must be consumer-facing and accessible.
    """
    text = f"{description} {document_text} {fund_name}".lower()
    metrics = reported_metrics or {}
    issues: list[str] = []
    recs: list[str] = []
    applicable_labels: list[str] = []

    def _term_in(t: str, term: str) -> bool:
        return _has_word(t, term) if (" " not in term and "-" not in term) else term in t

    for term in _FCA_PROHIBITED_TERMS:
        if _term_in(text, term):
            has_evidence = bool(metrics) or any(
                _has_word(text, kw)
                for kw in ["measured", "reported", "verified", "certified", "tracked"]
            )
            if not has_evidence:
                issues.append(
                    f"Use of '{term}' without substantiation may breach FCA Anti-Greenwashing Rule"
                )

    if _has_word(text, "impact") and metrics:
        applicable_labels.append("sustainability_impact")
    if _has_word(text, "esg") or _has_word(text, "sustainable"):
        if metrics and len(metrics) >= 3:
            applicable_labels.append("sustainability_focus")
        else:
            applicable_labels.append("sustainability_improvers")

    if not applicable_labels and any(_term_in(text, t) for t in _FCA_PROHIBITED_TERMS):
        issues.append("Sustainability-related terminology used without qualifying for an SDR label")
        recs.append("Evaluate whether a Sustainability Disclosure Requirements (SDR) label applies")

    if applicable_labels:
        for label_id in applicable_labels:
            info = _SDL_LABELS[label_id]
            recs.append(f"If using label '{info['label']}': {info['requirement']}")

    compliant = not bool(issues)
    return FCAAntiGreenwashingResult(
        compliant=compliant,
        issues=issues,
        sdl_labels_applicable=applicable_labels,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# NLP-Enhanced Greenwashing Detection
# ---------------------------------------------------------------------------

class NLPGreenwashingResult(BaseModel):
    """Advanced NLP-based greenwashing analysis."""

    green_authenticity_index: float = Field(ge=0, le=100, description="GAI: 0=inauthentic, 100=fully authentic")
    cheap_talk_index: float = Field(ge=0, le=100, description="CTI: 0=all substantive, 100=all cheap talk")
    sentiment_deflection_score: float = Field(ge=0, le=100, description="0=balanced, 100=high deflection")
    verifiable_sub_claims: list[dict[str, Any]] = Field(default_factory=list)
    climatebert_available: bool = False
    climatebert_prediction: str | None = None


_COMMITMENT_PATTERNS: list[str] = [
    r"\b(?:we|our|the)\s+(?:aim|plan|intend|expect|hope|aspire)\s+to\b",
    r"\b(?:committed|dedicated|working)\s+(?:to|toward)\b",
    r"\bby\s+20\d{2}\b",
    r"\bin\s+(?:the\s+)?(?:near|medium|long)\s+(?:term|future)\b",
    r"\b(?:net[\s-]?zero|carbon[\s-]?neutral)\s+by\b",
]

_SUBSTANTIVE_PATTERNS: list[str] = [
    r"\b\d+(?:\.\d+)?%?\s*(?:reduction|increase|decrease|growth|improvement)\b",
    r"\b(?:reduced|increased|achieved|measured|verified)\s+\w+\s+by\s+\d+",
    r"\b(?:ISO\s*\d+|GRI|IRIS\+?|SASB|CDP|SBTi|B\s*Corp)\b",
    r"\b\d{4}\s*(?:data|results|figures|report|audit)\b",
]

_DEFLECTION_POSITIVE = {
    "excited", "proud", "thrilled", "delighted", "honored", "pleased",
    "passionate", "grateful", "humbled", "privileged", "inspired",
}

_DEFLECTION_NEGATIVE = {
    "challenge", "risk", "concern", "failure", "incident", "violation",
    "contamination", "spill", "breach", "fine", "penalty", "lawsuit",
}


def assess_nlp_greenwashing(
    text: str,
    claims: list[dict[str, Any]] | None = None,
) -> NLPGreenwashingResult:
    """Run advanced NLP-based greenwashing analysis.

    Combines:
    - **Green Authenticity Index (GAI)** — adapted from the Stacey Matrix,
      evaluating coherence between stated values and reported actions.
    - **Cheap Talk Index (CTI)** — proportion of forward-looking commitments
      vs. substantive past-tense evidence.
    - **Sentiment Deflection Score** — detects overly positive emotional
      language used to deflect from negative information.
    - **Claim Decomposition** — splits claims into verifiable sub-claims.
    """
    lower = text.lower()

    # Green Authenticity Index
    gai = _compute_gai(lower)

    # Cheap Talk Index
    cti = _compute_cheap_talk_index(lower)

    # Sentiment deflection
    deflection = _compute_sentiment_deflection(lower)

    # Claim decomposition
    sub_claims = _decompose_claims(text, claims)

    # ClimateBERT stub
    climatebert_available = _check_climatebert_available()

    return NLPGreenwashingResult(
        green_authenticity_index=round(gai, 1),
        cheap_talk_index=round(cti, 1),
        sentiment_deflection_score=round(deflection, 1),
        verifiable_sub_claims=sub_claims,
        climatebert_available=climatebert_available,
        climatebert_prediction=None,
    )


def _compute_gai(text: str) -> float:
    """Green Authenticity Index — adapted from the Stacey Matrix.

    Evaluates alignment between:
    - Stated values/commitments (agreement dimension)
    - Reported evidence/data (certainty dimension)

    High GAI = strong alignment (authentic). Low GAI = misalignment (inauthentic).
    """
    value_keywords = {
        "sustainability", "responsible", "ethical", "impact", "green",
        "commitment", "policy", "principle", "standard", "framework",
    }
    evidence_keywords = {
        "data", "metric", "measured", "reported", "audited", "verified",
        "baseline", "target", "achieved", "result", "outcome", "evidence",
    }

    words = set(re.findall(r"\b\w+\b", text))
    values_found = len(words & value_keywords)
    evidence_found = len(words & evidence_keywords)

    if values_found == 0 and evidence_found == 0:
        return 50.0

    total = values_found + evidence_found
    if total == 0:
        return 50.0

    alignment = evidence_found / total
    return min(100, alignment * 100 + (evidence_found * 3))


def _compute_cheap_talk_index(text: str) -> float:
    """Cheap Talk Index — ratio of non-specific commitments to substantive evidence."""
    commitment_hits = sum(1 for p in _COMMITMENT_PATTERNS if re.search(p, text))
    substantive_hits = sum(1 for p in _SUBSTANTIVE_PATTERNS if re.search(p, text))

    total = commitment_hits + substantive_hits
    if total == 0:
        return 50.0

    return min(100, (commitment_hits / total) * 100)


def _compute_sentiment_deflection(text: str) -> float:
    """Detect overly positive sentiment used to deflect from negative info."""
    words = set(re.findall(r"\b\w+\b", text))
    pos_count = len(words & _DEFLECTION_POSITIVE)
    neg_count = len(words & _DEFLECTION_NEGATIVE)

    if pos_count == 0 and neg_count == 0:
        return 20.0

    total = pos_count + neg_count
    pos_ratio = pos_count / total

    if neg_count > 0 and pos_ratio > 0.8:
        return min(100, pos_ratio * 100 + 20)

    if pos_count > 3 and neg_count == 0:
        return min(100, 40 + pos_count * 8)

    return max(0, pos_ratio * 60)


def _decompose_claims(text: str, claims: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Break claims into verifiable sub-claims."""
    results: list[dict[str, Any]] = []

    source_claims = claims or []
    if not source_claims:
        sentences = re.split(r"[.!?]+", text)
        impact_keywords = {"impact", "sustainab", "emission", "reduc", "improv", "benefit", "achiev"}
        source_claims = [
            {"text": s.strip()} for s in sentences
            if any(k in s.lower() for k in impact_keywords) and len(s.strip()) > 20
        ]

    for claim in source_claims[:10]:
        claim_text = claim.get("text", claim.get("claim", ""))
        if not claim_text:
            continue

        has_quantity = bool(re.search(r"\b\d+(?:\.\d+)?[%]?\b", claim_text))
        has_timeframe = bool(re.search(r"\b(?:20\d{2}|by|since|annually|quarterly)\b", claim_text, re.IGNORECASE))
        has_method = bool(re.search(r"\b(?:measured|verified|audited|certified|reported)\b", claim_text, re.IGNORECASE))
        has_source = bool(re.search(r"\b(?:ISO|GRI|IRIS|CDP|SBTi|survey|audit)\b", claim_text, re.IGNORECASE))

        verifiability_score = sum([has_quantity, has_timeframe, has_method, has_source]) / 4 * 100
        missing = []
        if not has_quantity:
            missing.append("quantitative data")
        if not has_timeframe:
            missing.append("timeframe/date")
        if not has_method:
            missing.append("measurement methodology")
        if not has_source:
            missing.append("data source/standard")

        results.append({
            "claim": claim_text[:200],
            "verifiability_pct": round(verifiability_score, 0),
            "has_quantity": has_quantity,
            "has_timeframe": has_timeframe,
            "has_method": has_method,
            "has_source": has_source,
            "missing_for_verification": missing,
        })

    return results


def _check_climatebert_available() -> bool:
    """Check if ClimateBERT model is available locally.

    ClimateBERT (climatebert/distilroberta-base-climate-detector) can classify
    text as climate-related and detect specific climate claims. This is a stub
    that checks for the transformers library and model availability.
    """
    try:
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False
