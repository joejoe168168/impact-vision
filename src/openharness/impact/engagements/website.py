"""Public website productisation backend (roadmap-v4 Track 7).

Ships the **data** layer of the product website — the diagnostic quiz,
report gallery, benchmark teaser, playbook catalogue, upload demo and
lead-capture structures — so a future front-end can render them without
re-designing the domain model.

This module does not touch any web framework; it is pure Pydantic and
deterministic scoring so the same outputs can power Streamlit, FastAPI,
Next.js, or MCP clients equally.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field


Maturity = Literal["initial", "developing", "defined", "managed", "optimising"]


# ---------------------------------------------------------- diagnostic quiz (7.1)


class DiagnosticQuestion(BaseModel):
    question_id: str
    prompt: str
    category: str
    options: list[dict[str, str]] = Field(default_factory=list)
    """List of ``{"id": "...", "label": "...", "score": "0-4"}``."""


class DiagnosticAnswer(BaseModel):
    question_id: str
    option_id: str


class DiagnosticResult(BaseModel):
    result_id: str = Field(default_factory=lambda: f"diag_{secrets.token_hex(4)}")
    total_score: int
    max_score: int
    stage: Maturity
    category_scores: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score_pct(self) -> float:
        if self.max_score == 0:
            return 0.0
        return round(self.total_score / self.max_score, 3)


DIAGNOSTIC_QUESTIONS: list[DiagnosticQuestion] = [
    DiagnosticQuestion(
        question_id="strategy",
        prompt="How is your impact thesis articulated?",
        category="strategy",
        options=[
            {"id": "none", "label": "We don't have one yet", "score": "0"},
            {"id": "informal", "label": "Informal narrative", "score": "1"},
            {"id": "written", "label": "Written thesis not yet tied to KPIs", "score": "2"},
            {"id": "tied_kpi", "label": "Thesis tied to a KPI framework", "score": "3"},
            {"id": "tied_toc", "label": "Thesis tied to a ToC + KPI + risk register", "score": "4"},
        ],
    ),
    DiagnosticQuestion(
        question_id="data",
        prompt="How do you collect portfolio impact data today?",
        category="data_collection",
        options=[
            {"id": "email", "label": "Email + spreadsheets", "score": "0"},
            {"id": "single_tool", "label": "Single data-collection tool", "score": "1"},
            {"id": "versioned", "label": "Versioned schema with validation", "score": "2"},
            {"id": "workflow", "label": "Workflow with exception queue", "score": "3"},
            {"id": "platform", "label": "End-to-end platform with audit trail", "score": "4"},
        ],
    ),
    DiagnosticQuestion(
        question_id="reporting",
        prompt="How often are claims reviewed before publication?",
        category="reporting",
        options=[
            {"id": "never", "label": "Not formally reviewed", "score": "0"},
            {"id": "adhoc", "label": "Ad hoc review by partner", "score": "1"},
            {"id": "checklist", "label": "Structured checklist", "score": "2"},
            {"id": "evidence", "label": "Each claim tied to evidence", "score": "3"},
            {"id": "audit", "label": "Claim review panel with audit log", "score": "4"},
        ],
    ),
    DiagnosticQuestion(
        question_id="verification",
        prompt="Do you undergo independent impact verification?",
        category="assurance",
        options=[
            {"id": "none", "label": "No", "score": "0"},
            {"id": "planning", "label": "Planning to", "score": "1"},
            {"id": "started", "label": "Mid-engagement", "score": "2"},
            {"id": "periodic", "label": "Periodic verification cycle", "score": "3"},
            {"id": "aligned", "label": "OPIM-aligned 3-pillar verification", "score": "4"},
        ],
    ),
    DiagnosticQuestion(
        question_id="regulatory",
        prompt="How do you track regulatory obligations (SFDR / SDR / CSRD / ISSB)?",
        category="regulatory",
        options=[
            {"id": "unknown", "label": "We don't know which apply", "score": "0"},
            {"id": "list", "label": "We have a list", "score": "1"},
            {"id": "mapped", "label": "Each obligation mapped to a metric", "score": "2"},
            {"id": "workflow", "label": "Workflow with deadlines + owners", "score": "3"},
            {"id": "auto", "label": "Fully automated regulator-facing narrative", "score": "4"},
        ],
    ),
    DiagnosticQuestion(
        question_id="stakeholder",
        prompt="Do you routinely capture beneficiary / stakeholder voice?",
        category="stakeholder_voice",
        options=[
            {"id": "no", "label": "No", "score": "0"},
            {"id": "ad_hoc", "label": "Ad hoc interviews", "score": "1"},
            {"id": "lean", "label": "Lean Data or surveys", "score": "2"},
            {"id": "linked", "label": "Linked to claims + consent", "score": "3"},
            {"id": "longitudinal", "label": "Longitudinal with persistent IDs", "score": "4"},
        ],
    ),
    DiagnosticQuestion(
        question_id="governance",
        prompt="How is AI used in your impact workflow?",
        category="governance",
        options=[
            {"id": "none", "label": "Not used", "score": "0"},
            {"id": "manual", "label": "Manual, case-by-case", "score": "1"},
            {"id": "assistive", "label": "Assistive drafting with manual review", "score": "2"},
            {"id": "queue", "label": "AI outputs go through a review queue", "score": "3"},
            {"id": "audit", "label": "All AI outputs logged with prompt/model version", "score": "4"},
        ],
    ),
]


_STAGE_CUTS: list[tuple[float, Maturity]] = [
    (0.2, "initial"),
    (0.4, "developing"),
    (0.6, "defined"),
    (0.8, "managed"),
    (1.0, "optimising"),
]


def list_diagnostic_questions() -> list[DiagnosticQuestion]:
    return list(DIAGNOSTIC_QUESTIONS)


def score_diagnostic(answers: Iterable[DiagnosticAnswer]) -> DiagnosticResult:
    """Score the diagnostic quiz and return stage + category breakdown.

    Duplicate answers for the same ``question_id`` collapse to the *last*
    answer so ``max_score`` equals 4 * len(DIAGNOSTIC_QUESTIONS) regardless
    of caller behaviour.
    """
    answers = list(answers)
    question_by_id = {q.question_id: q for q in DIAGNOSTIC_QUESTIONS}
    # Collapse duplicates (last one wins) to avoid double-counting max_score.
    answers_by_question: dict[str, DiagnosticAnswer] = {}
    for answer in answers:
        if answer.question_id in question_by_id:
            answers_by_question[answer.question_id] = answer
    per_category_counts: dict[str, list[float]] = {}
    total_score = 0
    max_score = 4 * len(DIAGNOSTIC_QUESTIONS)
    for answer in answers_by_question.values():
        question = question_by_id[answer.question_id]
        option = next(
            (o for o in question.options if o["id"] == answer.option_id),
            None,
        )
        if option is None:
            continue
        score = float(option.get("score", "0"))
        total_score += int(score)
        per_category_counts.setdefault(question.category, []).append(score / 4)

    category_scores = {
        cat: round(sum(values) / len(values), 3) if values else 0.0
        for cat, values in per_category_counts.items()
    }

    score_pct = total_score / max_score if max_score else 0.0
    stage: Maturity = "initial"
    for cut, label in _STAGE_CUTS:
        if score_pct <= cut:
            stage = label
            break

    recommendations = _recommendations_for(stage, category_scores)

    return DiagnosticResult(
        total_score=total_score,
        max_score=max_score,
        stage=stage,
        category_scores=category_scores,
        recommendations=recommendations,
    )


def _recommendations_for(stage: Maturity, categories: dict[str, float]) -> list[str]:
    tips: list[str] = []
    if stage in {"initial", "developing"}:
        tips.append("Run an Impact Strategy / IMM baseline engagement.")
    if categories.get("data_collection", 1.0) < 0.5:
        tips.append("Adopt a versioned data-collection schema with a review queue.")
    if categories.get("assurance", 1.0) < 0.5:
        tips.append("Plan a BlueMark-style 3-pillar verification engagement.")
    if categories.get("regulatory", 1.0) < 0.5:
        tips.append("Run the Regulatory Compliance Workbench for your jurisdiction.")
    if categories.get("stakeholder_voice", 1.0) < 0.5:
        tips.append("Launch a Stakeholder Voice study with persistent IDs.")
    if categories.get("governance", 1.0) < 0.5:
        tips.append("Enforce AI governance: log prompt, model version, reviewer.")
    if not tips:
        tips.append(
            "Maintain current cadence; consider publishing an annual assurance bundle."
        )
    return tips


# ---------------------------------------------------------- report gallery (7.2)


class GalleryItem(BaseModel):
    item_id: str
    title: str
    engagement_type: str
    audience: str
    summary: str
    teaser_bullets: list[str] = Field(default_factory=list)


REPORT_GALLERY: list[GalleryItem] = [
    GalleryItem(
        item_id="dd_light",
        title="Impact DD — Light",
        engagement_type="dd_light",
        audience="ic",
        summary=(
            "Three-day screen with DD checklist, exclusion test, and "
            "greenwashing scan."
        ),
        teaser_bullets=[
            "Red-flag summary with IRIS+ references",
            "Decision-ready recommendation",
        ],
    ),
    GalleryItem(
        item_id="annual_impact",
        title="Annual Impact Report",
        engagement_type="annual_impact_report",
        audience="lp",
        summary="Multi-audience annual cycle with LP narrative and trend analysis.",
        teaser_bullets=[
            "LP-grade claim review panel",
            "Portfolio rollup with peer context",
        ],
    ),
    GalleryItem(
        item_id="assurance",
        title="3-Pillar Verification Bundle",
        engagement_type="verification_3pillar",
        audience="verifier",
        summary="Mandate + Practice + Reporting packs ready for BlueMark-style verifiers.",
        teaser_bullets=[
            "OPIM-aligned evidence map",
            "Signed assurance manifest",
        ],
    ),
    GalleryItem(
        item_id="stakeholder_voice",
        title="Stakeholder Voice Study",
        engagement_type="stakeholder_voice",
        audience="ic",
        summary="Lean Data survey + beneficiary feedback with consent tracking.",
        teaser_bullets=[
            "Persistent stakeholder IDs",
            "Claim-level quality scoring",
        ],
    ),
    GalleryItem(
        item_id="exit_vdd",
        title="Impact VDD / Exit Report",
        engagement_type="exit_vdd",
        audience="ic",
        summary="OPIM Principle 8 residual-impact assessment at exit.",
        teaser_bullets=[
            "Durability risk register",
            "Post-exit follow-up plan",
        ],
    ),
]


def list_gallery_items() -> list[GalleryItem]:
    return list(REPORT_GALLERY)


# ---------------------------------------------------------- benchmark teaser (7.3)


class BenchmarkTeaserRow(BaseModel):
    metric_id: str
    sector: str
    median: float
    p25: float
    p75: float
    sample_size: int


class BenchmarkTeaser(BaseModel):
    title: str = "Sector Benchmark Teaser"
    rows: list[BenchmarkTeaserRow] = Field(default_factory=list)
    disclaimer: str = (
        "Sample values from an in-memory demo dataset. Paid providers pluggable "
        "via the `BenchmarkProvider` interface."
    )


def build_benchmark_teaser() -> BenchmarkTeaser:
    """Hard-coded teaser dataset used on the public site (Track 7.3)."""
    sample = [
        ("OI4112", "financial services", 1800.0, 1200.0, 3400.0, 5),
        ("PD5833", "financial services", 660.0, 450.0, 910.0, 4),
        ("PD5833", "energy", 21000.0, 12000.0, 32000.0, 4),
        ("OI6213", "financial services", 37.5, 25.0, 60.0, 4),
    ]
    return BenchmarkTeaser(
        rows=[
            BenchmarkTeaserRow(
                metric_id=m, sector=s, median=md, p25=p25, p75=p75, sample_size=n
            )
            for m, s, md, p25, p75, n in sample
        ]
    )


# ------------------------------------------------------------ playbook library (7.4)


class PlaybookPage(BaseModel):
    slug: str
    title: str
    audience: str
    summary: str
    body_markdown: str


PLAYBOOK_PAGES: dict[str, PlaybookPage] = {
    "toc_design": PlaybookPage(
        slug="toc_design",
        title="Theory of Change Design",
        audience="founder + consultant",
        summary="Consultant-curated, evidence-bound ToC design playbook.",
        body_markdown=(
            "## Why\n\nStart with strategy, not metrics.\n\n"
            "## How\n\n1. Gather intake docs.\n2. AI-draft a ToC.\n3. Run the "
            "ToC canvas + validator.\n4. Capture every override in the audit trail.\n"
        ),
    ),
    "kpi_framework": PlaybookPage(
        slug="kpi_framework",
        title="KPI Framework Playbook",
        audience="fund manager",
        summary="From ToC outcomes to IRIS+ + cross-framework KPIs.",
        body_markdown=(
            "## Why\n\nAvoid KPI drift.\n\n## How\n\nRun `generate_kpi_framework` "
            "against a validated canvas, cross-reference across frameworks, then "
            "lock the framework for the engagement.\n"
        ),
    ),
    "stakeholder_voice": PlaybookPage(
        slug="stakeholder_voice",
        title="Stakeholder Voice Playbook",
        audience="program manager",
        summary="Lean Data + consent + persistent stakeholder IDs.",
        body_markdown=(
            "## Why\n\nSopact's persistent-identity critique is correct.\n\n"
            "## How\n\nUse the v3 stakeholder_voice module, ensure consent is "
            "logged, and reuse stable IDs across rounds.\n"
        ),
    ),
    "impact_dd": PlaybookPage(
        slug="impact_dd",
        title="Impact Due Diligence Playbook",
        audience="investor",
        summary="Light / Mid / Full DD ladder.",
        body_markdown=(
            "## Why\n\nImpact Institute's modular DD ladder works.\n\n"
            "## How\n\nPick the appropriate `dd_light / dd_mid / dd_full_iwa` "
            "bundle; run the engagement workspace with its audit trail on.\n"
        ),
    ),
    "assurance_readiness": PlaybookPage(
        slug="assurance_readiness",
        title="Assurance Readiness Playbook",
        audience="CFO",
        summary="Prepare for BlueMark-style 3-pillar verification.",
        body_markdown=(
            "## Why\n\nLPs increasingly require third-party assurance.\n\n"
            "## How\n\nComplete the mandate, practice, and reporting packs and "
            "publish the signed assurance manifest.\n"
        ),
    ),
}


def list_playbook_pages() -> list[PlaybookPage]:
    return list(PLAYBOOK_PAGES.values())


def get_playbook_page(slug: str) -> PlaybookPage:
    try:
        return PLAYBOOK_PAGES[slug]
    except KeyError as exc:
        known = ", ".join(sorted(PLAYBOOK_PAGES))
        raise KeyError(
            f"Unknown playbook page {slug!r}. Known pages: {known}"
        ) from exc


# ---------------------------------------------------------- lead capture (7.5)


class LeadCapture(BaseModel):
    """Lead generated from diagnostic outputs."""

    lead_id: str = Field(default_factory=lambda: f"lead_{secrets.token_hex(4)}")
    email: str
    organization: str = ""
    role: str = ""
    stage: Maturity = "initial"
    recommendation: str = ""
    created_at: str = Field(default_factory=lambda: _now())
    consent: bool = False


def capture_lead(
    *,
    email: str,
    diagnostic: DiagnosticResult,
    organization: str = "",
    role: str = "",
    consent: bool = False,
) -> LeadCapture:
    if not email or "@" not in email:
        raise ValueError("A valid email is required to capture a lead.")
    if not consent:
        raise ValueError(
            "Explicit consent is required before creating a lead record (GDPR/PDPA)."
        )
    recommendation = (
        diagnostic.recommendations[0] if diagnostic.recommendations else ""
    )
    return LeadCapture(
        email=email,
        organization=organization,
        role=role,
        stage=diagnostic.stage,
        recommendation=recommendation,
        consent=consent,
    )


# ---------------------------------------------------------- upload demo (7.6)


class UploadDemoResult(BaseModel):
    """Redacted demo output from the 'upload a memo' flow (Track 7.6).

    Deliberately never echoes the source text. Returns a hash + sanitised
    summary only — the public demo should not leak client uploads.
    """

    demo_id: str = Field(default_factory=lambda: f"demo_{secrets.token_hex(4)}")
    content_hash: str
    word_count: int
    sample_outputs: dict[str, str] = Field(default_factory=dict)
    privacy_note: str = (
        "Source text is hashed and discarded. Only sanitised, non-identifying "
        "outputs are returned to the browser."
    )


def run_upload_demo(*, text: str) -> UploadDemoResult:
    cleaned = " ".join(text.split())
    content_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    word_count = len(cleaned.split())
    sample_outputs = {
        "impact_claim_detected": (
            "Detected 2 impact-style claims (redacted)" if "impact" in cleaned.lower() else
            "No explicit impact claims detected"
        ),
        "suggested_bundle": (
            "dd_mid" if word_count > 400 else "dd_light"
        ),
        "suggested_framework": "IRIS+ core metric set",
    }
    return UploadDemoResult(
        content_hash=content_hash,
        word_count=word_count,
        sample_outputs=sample_outputs,
    )


# ---------------------------------------------------------- partner page (7.7)


class PartnerMode(BaseModel):
    """White-label mode metadata for the partner page."""

    partner_id: str
    name: str
    white_label: bool = True
    template_library: list[str] = Field(default_factory=list)
    methodology_pinned_version: str = ""


def describe_partner_mode(partner_id: str, name: str) -> PartnerMode:
    return PartnerMode(
        partner_id=partner_id,
        name=name,
        template_library=[
            "fund_impact_launch",
            "corporate_esg_baseline",
            "foundation_grantee_portfolio",
        ],
        methodology_pinned_version="impact-vision-v4",
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "BenchmarkTeaser",
    "BenchmarkTeaserRow",
    "DIAGNOSTIC_QUESTIONS",
    "DiagnosticAnswer",
    "DiagnosticQuestion",
    "DiagnosticResult",
    "GalleryItem",
    "LeadCapture",
    "Maturity",
    "PLAYBOOK_PAGES",
    "PartnerMode",
    "PlaybookPage",
    "REPORT_GALLERY",
    "UploadDemoResult",
    "build_benchmark_teaser",
    "capture_lead",
    "describe_partner_mode",
    "get_playbook_page",
    "list_diagnostic_questions",
    "list_gallery_items",
    "list_playbook_pages",
    "run_upload_demo",
    "score_diagnostic",
]
