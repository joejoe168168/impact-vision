"""Impact Due Diligence checklist engine.

Loads structured DD questions from YAML and determines which questions
are already addressed vs. which need to be asked, based on document text.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


EVIDENCE_LEVELS = {
    1: "Narrative / anecdotal only (self-reported, no data)",
    2: "Output data (quantified activities, e.g. # served, # trained)",
    3: "Outcome data measured (pre/post, surveys, tracked KPIs)",
    4: "Controlled comparison (quasi-experimental, benchmarks, cohort studies)",
    5: "Rigorous evaluation (RCT, independent audit, causal attribution)",
}


class DDQuestion(BaseModel):
    id: str
    question: str
    category: str
    phase: str = "deep_diligence"
    dimension: str | None = None
    priority: str = "medium"
    keywords: list[str] = Field(default_factory=list)
    follow_up: str | None = None


class DDChecklistResult(BaseModel):
    """Result of running the checklist against document text."""

    total_questions: int
    addressed: list[DDQuestionMatch] = Field(default_factory=list)
    unanswered: list[DDQuestion] = Field(default_factory=list)
    coverage_pct: float = 0.0
    high_priority_gaps: list[DDQuestion] = Field(default_factory=list)
    avg_evidence_level: float = Field(
        default=0.0,
        description="Average NESTA evidence level across addressed questions (1-5 scale)",
    )


class DDQuestionMatch(BaseModel):
    """A DD question that appears to be addressed in the document."""

    question: DDQuestion
    matched_keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    relevant_text_snippets: list[str] = Field(default_factory=list)
    evidence_level: int = Field(
        default=1, ge=1, le=5,
        description="NESTA Standards of Evidence level (1=narrative, 5=RCT/causal)",
    )
    evidence_label: str = ""


_checklist_cache: list[DDQuestion] | None = None
_checklist_cache_path: str | None = None


def _get_default_checklist_path() -> Path:
    candidates = [
        Path(__file__).parent.parent.parent.parent / "data" / "dd_checklist.yaml",
        Path.cwd() / "data" / "dd_checklist.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_checklist(path: str | Path | None = None) -> list[DDQuestion]:
    """Load DD questions from YAML file."""
    global _checklist_cache, _checklist_cache_path
    cache_key = str(path) if path else "__default__"
    if _checklist_cache is not None and _checklist_cache_path == cache_key:
        return _checklist_cache

    yaml_path = Path(path) if path else _get_default_checklist_path()
    if not yaml_path.exists():
        logger.warning("DD checklist not found: %s", yaml_path)
        return []

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    questions = []
    for q_data in data.get("questions", []):
        questions.append(DDQuestion(
            id=q_data["id"],
            question=q_data["question"],
            category=q_data["category"],
            phase=q_data.get("phase", "deep_diligence"),
            dimension=q_data.get("dimension"),
            priority=q_data.get("priority", "medium"),
            keywords=q_data.get("keywords", []),
            follow_up=q_data.get("follow_up"),
        ))

    _checklist_cache = questions
    _checklist_cache_path = cache_key

    logger.info("Loaded %d DD checklist questions", len(questions))
    return questions


def analyze_document_coverage(
    document_text: str,
    questions: list[DDQuestion] | None = None,
    categories: list[str] | None = None,
    min_confidence: float = 0.3,
) -> DDChecklistResult:
    """Analyze which DD questions are addressed in a document.

    Scans the document text for keyword matches against each question's
    keyword list. Questions with sufficient matches are considered 'addressed'.
    """
    if questions is None:
        questions = load_checklist()

    if categories:
        cat_set = set(categories)
        questions = [q for q in questions if q.category in cat_set]

    import re
    text_lower = document_text.lower()
    sentences = _rough_sentences(text_lower)

    addressed: list[DDQuestionMatch] = []
    unanswered: list[DDQuestion] = []

    for q in questions:
        matched_kw: list[str] = []
        snippets: list[str] = []

        for kw in q.keywords:
            kw_lower = kw.lower().strip()
            if not kw_lower:
                continue
            pattern = re.compile(r"\b" + re.escape(kw_lower) + r"\b")
            match = pattern.search(text_lower)
            if not match:
                continue
            matched_kw.append(kw)
            for sent in sentences:
                if pattern.search(sent) and len(sent) > 30:
                    snippet = sent.strip()[:200]
                    if snippet not in snippets:
                        snippets.append(snippet)
            # Fallback: if no full sentence matched (e.g. very short sentences),
            # take a +/-200 char window around the first hit so evidence-level
            # detection still has context to look at.
            if not snippets:
                start = max(0, match.start() - 200)
                end = min(len(text_lower), match.end() + 200)
                snippets.append(text_lower[start:end].strip()[:400])

        if not matched_kw:
            unanswered.append(q)
            continue

        confidence = min(1.0, len(matched_kw) / max(len(q.keywords), 1) * 1.5)
        if confidence >= min_confidence:
            ev_level = _assess_evidence_level(snippets)
            addressed.append(DDQuestionMatch(
                question=q,
                matched_keywords=matched_kw,
                confidence=round(confidence, 2),
                relevant_text_snippets=snippets[:3],
                evidence_level=ev_level,
                evidence_label=EVIDENCE_LEVELS.get(ev_level, ""),
            ))
        else:
            unanswered.append(q)

    total = len(questions)
    coverage = round(len(addressed) / total * 100, 1) if total > 0 else 0.0
    high_gaps = [q for q in unanswered if q.priority == "high"]
    avg_ev = round(sum(a.evidence_level for a in addressed) / len(addressed), 1) if addressed else 0.0

    return DDChecklistResult(
        total_questions=total,
        addressed=addressed,
        unanswered=unanswered,
        coverage_pct=coverage,
        high_priority_gaps=high_gaps,
        avg_evidence_level=avg_ev,
    )


def select_questions_for_document(
    document_text: str,
    max_questions: int = 15,
    focus_categories: list[str] | None = None,
) -> list[DDQuestion]:
    """Select the most relevant unanswered DD questions for a document.

    Prioritizes high-priority questions and questions from categories
    that appear relevant to the document content.
    """
    result = analyze_document_coverage(
        document_text, categories=focus_categories
    )

    relevance_categories = _detect_relevant_categories(document_text)

    scored: list[tuple[float, DDQuestion]] = []
    for q in result.unanswered:
        score = 0.0
        if q.priority == "high":
            score += 3.0
        elif q.priority == "medium":
            score += 1.0

        if q.category in relevance_categories:
            score += 2.0

        if q.dimension:
            score += 0.5

        if q.phase == "screening":
            score += 1.0

        scored.append((score, q))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [q for _, q in scored[:max_questions]]


def _detect_relevant_categories(text: str) -> set[str]:
    """Detect which DD categories are most relevant to the document."""
    text_lower = text.lower()
    cat_keywords = {
        "impact_thesis": ["impact", "mission", "social", "environmental", "problem", "solution"],
        "theory_of_change": ["theory of change", "logic model", "pathway", "mechanism"],
        "what_outcomes": ["outcome", "result", "output", "change", "improvement"],
        "who_stakeholders": ["beneficiar", "stakeholder", "customer", "community", "target population"],
        "how_much_scale": ["scale", "reach", "number of", "growth", "users"],
        "contribution": ["additionality", "unique", "counterfactual", "alternative"],
        "risk": ["risk", "challenge", "barrier", "mitigation"],
        "measurement_systems": ["measurement", "metric", "KPI", "data", "monitoring"],
        "governance_esg": ["governance", "board", "ESG", "diversity", "policy"],
        "sdg_alignment": ["SDG", "sustainable development", "UN"],
        "negative_impact": ["negative", "harm", "unintended"],
        "exit_sustainability": ["exit", "sustainability", "long-term"],
        "financial_sustainability": ["revenue", "profit", "unit economics", "business model", "financial"],
        "team_capability": ["founder", "team", "leadership", "experience", "CEO"],
        "market_context": ["market", "competitive", "regulatory", "demand", "TAM"],
        "product_design": ["product", "design", "user", "safety", "privacy", "pricing"],
        "supply_chain": ["supply chain", "supplier", "sourcing", "labor"],
        "stakeholder_voice": ["feedback", "voice", "survey", "engagement", "participat"],
        "investor_alignment": ["investor", "fund", "portfolio", "covenant", "mandate"],
        "sector_fintech": ["fintech", "microfinance", "lending", "loan", "banking", "payment", "credit"],
        "sector_health": ["health", "medical", "clinic", "patient", "pharmaceutical", "telemedicine"],
        "sector_agriculture": ["agriculture", "farming", "smallholder", "crop", "livestock", "agri"],
        "sector_energy": ["solar", "renewable", "energy access", "off-grid", "clean energy", "battery"],
        "sector_education": ["education", "edtech", "school", "learning", "student", "teacher", "curriculum"],
    }
    relevant = set()
    for cat, keywords in cat_keywords.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits >= 2:
            relevant.add(cat)
    return relevant


_LEVEL5_SIGNALS = (
    "rct", "randomized controlled", "randomised controlled", "causal attribution",
    "independent evaluation", "counterfactual analysis", "experimental design",
)
_LEVEL4_SIGNALS = (
    "quasi-experimental", "comparison group", "control group", "matched sample",
    "cohort study", "benchmark study", "diff-in-diff", "difference-in-differences",
)
_LEVEL3_SIGNALS = (
    "pre-post", "baseline", "survey data", "measured outcome",
    "tracked quarterly", "monitored quarterly", "year-over-year",
    "longitudinal", "panel data", "kpi", "tracked",
)
_LEVEL2_SIGNALS = (
    "served", "trained", "delivered", "produced", "distributed",
    "reached", "enrolled", "number of",
)


def _signal_in_text(text: str, signal: str) -> bool:
    """Word-boundary aware substring check.

    Avoids false positives like 'served' matching 'observed'.
    """
    import re
    return bool(re.search(r"\b" + re.escape(signal) + r"\b", text))


def _assess_evidence_level(snippets: list[str], full_text: str | None = None) -> int:
    """Assess NESTA Standards of Evidence level (1-5) based on snippet signals.

    IMPORTANT: this only inspects the matched snippets (not the full document) so
    that an unrelated mention of e.g. 'RCT' does not promote every addressed
    question to level 5. The `full_text` parameter is kept for API compatibility
    but is intentionally not consulted.
    """
    combined = " ".join(snippets).lower()
    if not combined.strip():
        return 1

    for signal in _LEVEL5_SIGNALS:
        if _signal_in_text(combined, signal):
            return 5
    for signal in _LEVEL4_SIGNALS:
        if _signal_in_text(combined, signal):
            return 4
    for signal in _LEVEL3_SIGNALS:
        if _signal_in_text(combined, signal):
            return 3
    for signal in _LEVEL2_SIGNALS:
        if _signal_in_text(combined, signal):
            return 2
    return 1


def _rough_sentences(text: str) -> list[str]:
    """Split text into rough sentence-like chunks."""
    import re
    parts = re.split(r'[.!?\n]+', text)
    return [p.strip() for p in parts if len(p.strip()) > 20]
