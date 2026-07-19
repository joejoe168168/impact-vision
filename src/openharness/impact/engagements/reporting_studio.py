"""Consultant-grade reporting studio (roadmap-v4 Track 5).

Sits on top of v3 :mod:`openharness.impact.lp_narrative`,
:mod:`openharness.impact.lp_portal` and the agent-level
:mod:`openharness.tools.impact.impact_report_tool` to add three v4-specific
capabilities without forking any of them:

* **ReportBuilder** (5.1) — an audience-aware, evidence-depth-aware,
  approval-workflow-aware compositor over any number of v3 "section"
  payloads.
* **Named ReportTemplate catalogue** (5.2) — IMM baseline, Impact DD,
  ESG baseline, portfolio deep dive, annual report, exit report.
* **Executive deck outline** (5.3) — one-click structure for a
  board/IC-ready deck; the actual PPTX render is left to an optional
  ``python-pptx`` integration later. The outline is enough for a
  consultant to paste into any deck tool.
* **Public microsite bundle** (5.4) — structured case-study payload for
  the Track 7 website.
* **Claim review panel** (5.5) — approved / caveated / rejected / needs
  evidence per claim, wired into the audit trail.
* **Multi-audience narrative** (5.6) — rewrite a base narrative into
  founder / IC / LP / board / public / regulator / verifier register.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field


Audience = Literal[
    "founder",
    "ic",
    "lp",
    "board",
    "public",
    "regulator",
    "verifier",
]

EvidenceDepth = Literal["headline", "summary", "detailed", "forensic"]

ClaimStatus = Literal["approved", "caveated", "rejected", "needs_evidence"]

ApprovalState = Literal["draft", "in_review", "approved", "published", "superseded"]


# -------------------------------------------------------------- report sections


class ReportSection(BaseModel):
    """One section on a report (text + optional chart / table / claim refs)."""

    section_id: str = Field(default_factory=lambda: f"sec_{secrets.token_hex(4)}")
    title: str
    body: str = ""
    audience: Audience = "lp"
    evidence_depth: EvidenceDepth = "summary"
    tone: Literal["neutral", "narrative", "technical", "promotional"] = "neutral"
    visuals: list[str] = Field(default_factory=list)
    claim_refs: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ClaimReview(BaseModel):
    """Track 5.5 per-claim review row."""

    claim_id: str
    text: str
    status: ClaimStatus = "needs_evidence"
    caveat: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    reviewer: str = ""
    reviewed_at: str = ""


class ReportApprovalEvent(BaseModel):
    """One state transition on the report approval workflow."""

    actor: str
    from_state: ApprovalState
    to_state: ApprovalState
    note: str = ""
    at: str = Field(default_factory=lambda: _now())


class Report(BaseModel):
    """A Track 5.1 consultant-grade report."""

    model_config = {"validate_assignment": True}

    report_id: str = Field(default_factory=lambda: f"rep_{secrets.token_hex(6)}")
    engagement_id: str = ""
    template_id: str = ""
    title: str
    audience: Audience = "lp"
    sections: list[ReportSection] = Field(default_factory=list)
    claim_reviews: list[ClaimReview] = Field(default_factory=list)
    qa_findings: list[dict] = Field(default_factory=list)
    approval_state: ApprovalState = "draft"
    approval_history: list[ReportApprovalEvent] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def claim_status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {
            "approved": 0,
            "caveated": 0,
            "rejected": 0,
            "needs_evidence": 0,
        }
        for claim in self.claim_reviews:
            counts[claim.status] = counts.get(claim.status, 0) + 1
        return counts

    @computed_field  # type: ignore[prop-decorator]
    @property
    def claim_ready_pct(self) -> float:
        """Fraction of claims that are 'approved' or 'caveated'."""
        if not self.claim_reviews:
            return 0.0
        ready = sum(1 for c in self.claim_reviews if c.status in {"approved", "caveated"})
        return round(ready / len(self.claim_reviews), 3)


# ------------------------------------------------------- named template catalog


class ReportTemplate(BaseModel):
    """Named template (Track 5.2) referencing existing v3 tools."""

    template_id: str
    name: str
    audience: Audience
    section_titles: list[str] = Field(default_factory=list)
    tool_refs: list[str] = Field(default_factory=list)
    evidence_depth: EvidenceDepth = "summary"


REPORT_TEMPLATES: dict[str, ReportTemplate] = {
    "tisfd_beta": ReportTemplate(
        template_id="tisfd_beta",
        name="TISFD Disclosure (beta)",
        audience="board",
        section_titles=["Governance", "Strategy", "Risk & Impact Management", "Metrics & Targets"],
        tool_refs=["framework_assess", "cross_reference", "greenwashing_detect"],
        evidence_depth="detailed",
    ),
    "imm_baseline": ReportTemplate(
        template_id="imm_baseline",
        name="IMM Baseline",
        audience="ic",
        section_titles=[
            "Strategy & Thesis",
            "Theory of Change",
            "KPI Framework",
            "Risk & Opportunity",
            "Next Actions",
        ],
        tool_refs=["toc_builder", "impact_metric_recommender", "impact_risk_opportunity"],
        evidence_depth="detailed",
    ),
    "impact_dd": ReportTemplate(
        template_id="impact_dd",
        name="Impact Due Diligence",
        audience="ic",
        section_titles=[
            "Executive Summary",
            "DD Checklist Findings",
            "Five-Dimension Assessment",
            "SDG Alignment",
            "Risk & Opportunity",
            "Recommendation",
        ],
        tool_refs=[
            "dd_checklist",
            "five_dimension_assess",
            "sdg_mapper",
            "impact_risk_opportunity",
            "greenwashing_detect",
        ],
        evidence_depth="detailed",
    ),
    "esg_baseline": ReportTemplate(
        template_id="esg_baseline",
        name="ESG Baseline",
        audience="board",
        section_titles=[
            "Materiality Matrix",
            "Framework Coverage",
            "Data Quality",
            "Gap-Closure Roadmap",
        ],
        tool_refs=["framework_tool", "data_quality"],
    ),
    "portfolio_deep_dive": ReportTemplate(
        template_id="portfolio_deep_dive",
        name="Portfolio Deep Dive",
        audience="lp",
        section_titles=[
            "Portfolio Overview",
            "KPI Roll-up",
            "Peer Benchmarks",
            "Value Creation Plan",
            "Outlook",
        ],
        tool_refs=["portfolio_tool", "trend_analysis", "monitoring"],
        evidence_depth="detailed",
    ),
    "annual_impact": ReportTemplate(
        template_id="annual_impact",
        name="Annual Impact Report",
        audience="lp",
        section_titles=[
            "Year in Review",
            "Theory of Change Progress",
            "KPI Performance",
            "Stakeholder Voice",
            "Looking Ahead",
        ],
        tool_refs=["lp_narrative", "narrative_tool", "trend_analysis"],
    ),
    "exit_report": ReportTemplate(
        template_id="exit_report",
        name="Impact VDD / Exit Report",
        audience="ic",
        section_titles=[
            "Exit Overview",
            "Impact at Exit (OPIM P8)",
            "Durability Risks",
            "Post-Exit Follow-Up",
            "Lessons Learned",
        ],
        tool_refs=["exit_impact", "lp_narrative"],
        evidence_depth="detailed",
    ),
}


def list_report_templates() -> list[ReportTemplate]:
    return list(REPORT_TEMPLATES.values())


def get_report_template(template_id: str) -> ReportTemplate:
    try:
        return REPORT_TEMPLATES[template_id]
    except KeyError as exc:
        known = ", ".join(sorted(REPORT_TEMPLATES))
        raise KeyError(f"Unknown report template {template_id!r}. Known: {known}") from exc


# ---------------------------------------------------------------- report builder


def build_report_from_template(
    *,
    template_id: str,
    title: str,
    engagement_id: str = "",
    audience: Audience | None = None,
    sections: Iterable[ReportSection] | None = None,
    claim_reviews: Iterable[ClaimReview] | None = None,
) -> Report:
    """Build a draft report from a named template.

    Extra sections supplied by the caller override the template default for
    that title; missing titles get a placeholder body the consultant is
    expected to fill in.
    """
    template = get_report_template(template_id)
    supplied_by_title = {s.title.lower().strip(): s for s in (sections or [])}
    built_sections: list[ReportSection] = []
    for title_ in template.section_titles:
        existing = supplied_by_title.pop(title_.lower().strip(), None)
        if existing is not None:
            existing.audience = audience or template.audience
            built_sections.append(existing)
        else:
            built_sections.append(
                ReportSection(
                    title=title_,
                    body="",
                    audience=audience or template.audience,
                    evidence_depth=template.evidence_depth,
                )
            )
    # Any extra sections the caller passed that aren't in the template just
    # go at the end.
    built_sections.extend(supplied_by_title.values())
    return Report(
        engagement_id=engagement_id,
        template_id=template_id,
        title=title,
        audience=audience or template.audience,
        sections=built_sections,
        claim_reviews=list(claim_reviews or []),
    )


def transition_report(
    report: Report,
    next_state: ApprovalState,
    *,
    actor: str,
    note: str = "",
) -> Report:
    """Advance a report through draft → in_review → approved → published → superseded."""
    allowed: dict[ApprovalState, set[ApprovalState]] = {
        "draft": {"in_review"},
        "in_review": {"draft", "approved"},
        "approved": {"published", "in_review"},
        "published": {"superseded"},
        "superseded": set(),
    }
    if next_state == "approved" and any(
        item.get("priority") == "blocker" for item in report.qa_findings
    ):
        raise ValueError("Pre-publication QA blockers must be resolved before approval")
    if next_state not in allowed[report.approval_state]:
        raise ValueError(f"Invalid report transition {report.approval_state} -> {next_state}")
    event = ReportApprovalEvent(
        actor=actor,
        from_state=report.approval_state,
        to_state=next_state,
        note=note,
    )
    report.approval_state = next_state
    report.approval_history.append(event)
    report.updated_at = _now()
    return report


def decide_claim(
    report: Report,
    claim_id: str,
    *,
    status: ClaimStatus,
    reviewer: str,
    caveat: str = "",
    evidence_refs: Iterable[str] | None = None,
) -> ClaimReview:
    """Record a claim review decision (Track 5.5)."""
    for claim in report.claim_reviews:
        if claim.claim_id == claim_id:
            claim.status = status
            claim.reviewer = reviewer
            claim.reviewed_at = _now()
            if caveat:
                claim.caveat = caveat
            if evidence_refs is not None:
                claim.evidence_refs = list(evidence_refs)
            report.updated_at = _now()
            return claim
    raise KeyError(f"Unknown claim {claim_id!r}")


# --------------------------------------------------------- multi-audience rewrite


AUDIENCE_HINTS: dict[Audience, str] = {
    "founder": (
        "Direct, operational. Emphasise execution actions and founder asks. Avoid financial jargon."
    ),
    "ic": (
        "Structured, decision-oriented. Lead with recommendation, evidence, risks, and mitigants."
    ),
    "lp": (
        "LP-friendly narrative. Reference OPIM / IRIS+ / EDCI. Cite evidence behind every claim."
    ),
    "board": (
        "Strategic, governance-focused. Highlight fiduciary implications and oversight actions."
    ),
    "public": (
        "Accessible and inclusive. Avoid acronyms without explanation; "
        "tell the story through beneficiaries."
    ),
    "regulator": (
        "Compliance-focused. Map claims to the specific framework "
        "obligations (SFDR / SDR / CSRD / ISSB) and flag gaps."
    ),
    "verifier": (
        "Assurance-ready. Link every quantitative claim to an evidence "
        "reference and an OPIM principle."
    ),
}


class MultiAudienceRewrite(BaseModel):
    """Result of a multi-audience rewrite (Track 5.6)."""

    base_text: str
    variants: dict[str, str] = Field(default_factory=dict)


def rewrite_for_audiences(
    base_text: str,
    audiences: Iterable[Audience],
) -> MultiAudienceRewrite:
    """Produce audience-scoped variants of a base narrative.

    This is a deterministic re-framing scaffold — it prefaces each variant
    with an audience lens header and appends the appropriate style hint so
    the consultant has a structured starting point before an LLM pass
    (Track 8.1 will plug that in later).
    """
    variants: dict[str, str] = {}
    for audience in audiences:
        hint = AUDIENCE_HINTS.get(audience, "")
        variants[audience] = f"[For {audience}] {hint}\n\n{base_text.strip()}"
    return MultiAudienceRewrite(base_text=base_text, variants=variants)


# --------------------------------------------------------- executive deck outline


class DeckSlide(BaseModel):
    """One slide in the executive deck outline."""

    slide_id: str = Field(default_factory=lambda: f"slide_{secrets.token_hex(4)}")
    title: str
    bullets: list[str] = Field(default_factory=list)
    suggested_visual: str = ""


class ExecutiveDeckOutline(BaseModel):
    """Track 5.3: board/IC-ready deck outline."""

    outline_id: str = Field(default_factory=lambda: f"deck_{secrets.token_hex(4)}")
    engagement_id: str = ""
    report_id: str = ""
    title: str = ""
    slides: list[DeckSlide] = Field(default_factory=list)


def build_executive_deck(report: Report) -> ExecutiveDeckOutline:
    """One-click outline: cover + each section → slide, plus closing slide."""
    slides: list[DeckSlide] = [
        DeckSlide(
            title=report.title,
            bullets=[
                f"Audience: {report.audience}",
                f"Template: {report.template_id or '-'}",
                f"Claim coverage: {int(report.claim_ready_pct * 100)}% reviewed",
            ],
            suggested_visual="title_card",
        )
    ]
    for section in report.sections:
        bullets = [line.strip() for line in (section.body or "").splitlines() if line.strip()][:5]
        if not bullets:
            bullets = [f"Populate section '{section.title}'"]
        slides.append(
            DeckSlide(
                title=section.title,
                bullets=bullets,
                suggested_visual="chart" if section.visuals else "callout",
            )
        )
    slides.append(
        DeckSlide(
            title="Recommendations & Next Steps",
            bullets=[
                "Approve value-creation plan",
                "Schedule follow-up review",
                "Track leading KPIs quarterly",
            ],
            suggested_visual="checklist",
        )
    )
    return ExecutiveDeckOutline(
        engagement_id=report.engagement_id,
        report_id=report.report_id,
        title=f"{report.title} — Executive Deck",
        slides=slides,
    )


# --------------------------------------------------------- public microsite (5.4)


class PublicMicrositePage(BaseModel):
    """One page on a client-facing microsite."""

    page_id: str = Field(default_factory=lambda: f"page_{secrets.token_hex(4)}")
    slug: str
    title: str
    summary: str = ""
    body_markdown: str = ""
    hero_claim: str = ""


class PublicMicrositeBundle(BaseModel):
    """Track 5.4 public-facing microsite bundle."""

    bundle_id: str = Field(default_factory=lambda: f"site_{secrets.token_hex(4)}")
    engagement_id: str = ""
    base_path: str = "/impact"
    pages: list[PublicMicrositePage] = Field(default_factory=list)


def build_public_microsite(report: Report) -> PublicMicrositeBundle:
    """Structured microsite bundle derived from a report."""
    pages = [
        PublicMicrositePage(
            slug="overview",
            title=report.title,
            summary=report.sections[0].body[:240] if report.sections else "",
            body_markdown="\n\n".join(
                f"## {section.title}\n\n{section.body}" for section in report.sections[:5]
            ),
            hero_claim=(report.claim_reviews[0].text if report.claim_reviews else ""),
        ),
    ]
    for section in report.sections[1:]:
        if not section.body:
            continue
        pages.append(
            PublicMicrositePage(
                slug=_slug(section.title),
                title=section.title,
                summary=section.body[:240],
                body_markdown=section.body,
            )
        )
    return PublicMicrositeBundle(engagement_id=report.engagement_id, pages=pages)


def _slug(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_index_universe(framework: str) -> list[dict]:
    if framework == "sse_g14":
        from openharness.impact.engagements.regulatory import load_cn_topics

        return [
            {
                "topic": row["topic_id"],
                "requirement_ref": ",".join(map(str, row["articles"])),
                "mandatory": row["mandatory"],
            }
            for row in load_cn_topics()
        ]
    if framework == "gri":
        from openharness.impact.frameworks.gri import GRI_STANDARDS

        return [
            {"topic": disclosure.code, "requirement_ref": disclosure.code, "mandatory": True}
            for standard in GRI_STANDARDS
            for disclosure in standard.disclosures
        ]
    if framework == "esrs":
        from openharness.impact.frameworks.esrs import load_simplified_datapoints

        return [
            {
                "topic": row.datapoint_id,
                "requirement_ref": row.datapoint_id,
                "mandatory": row.mandatory,
            }
            for row in load_simplified_datapoints()
        ]
    if framework == "issb":
        from openharness.impact.frameworks.issb_ifrs_s1 import IFRS_S1

        return [
            {
                "topic": disclosure.code,
                "requirement_ref": disclosure.paragraph_ref or disclosure.code,
                "mandatory": True,
            }
            for pillar in IFRS_S1.pillars
            for disclosure in pillar.disclosures
        ]
    raise KeyError(f"Unknown content-index framework: {framework}")


def build_content_index(
    framework: Literal["sse_g14", "gri", "esrs", "issb"], covered: dict[str, str]
) -> dict:
    rows = []
    for item in _content_index_universe(framework):
        supplied = covered.get(item["topic"])
        if isinstance(supplied, dict):
            chapter = supplied.get("chapter", "")
            status = supplied.get("status", "disclosed")
            reason = supplied.get("reason", "")
        elif supplied:
            chapter = str(supplied)
            status = "disclosed"
            reason = ""
        else:
            chapter = ""
            status = "omitted"
            reason = ""
        if status == "omitted" and supplied and not reason:
            raise ValueError(f"Omission for {item['topic']} requires a reason")
        rows.append(
            {**item, "chapter": chapter, "status": status, "reason": reason, "also_satisfies": []}
        )
    return {"framework": framework, "rows": rows}


def completeness_check(framework: str, covered: dict) -> dict:
    index = build_content_index(framework, covered)
    complete = sum(row["status"] == "disclosed" for row in index["rows"])
    return {
        "framework": framework,
        "complete_pct": round(100 * complete / len(index["rows"]), 1) if index["rows"] else 100,
        "mandatory_gaps": [
            row for row in index["rows"] if row["mandatory"] and row["status"] != "disclosed"
        ],
        "encouraged_gaps": [
            row for row in index["rows"] if not row["mandatory"] and row["status"] != "disclosed"
        ],
    }


def prepublication_qa(report_sections: dict) -> list[dict]:
    checks = []

    def add(condition, item, basis, priority):
        if not condition:
            checks.append({"item": item, "basis": basis, "priority": priority})

    add(
        report_sections.get("mandatory_topics_covered", False),
        "Cover all mandatory topics",
        "applicable disclosure standard",
        "blocker",
    )
    add(
        report_sections.get("quantitative_claims_have_records", False),
        "Link every quantitative claim to a MetricRecord",
        "evidence graph",
        "blocker",
    )
    add(
        report_sections.get("claims_greenwashing_reviewed", False),
        "Complete greenwashing review for every claim",
        "claim review policy",
        "blocker",
    )
    add(
        report_sections.get("comparative_period_present", False),
        "Include comparative period",
        "reporting standard",
        "high",
    )
    add(
        report_sections.get("methodology_stated", False),
        "State measurement methodology",
        "assurance readiness",
        "high",
    )
    add(
        report_sections.get("content_index_present", False),
        "Include content index",
        "SSE art.57 / GRI / ESRS indexing",
        "advisory",
    )
    return checks


__all__ = [
    "AUDIENCE_HINTS",
    "Audience",
    "ApprovalState",
    "ClaimReview",
    "ClaimStatus",
    "DeckSlide",
    "EvidenceDepth",
    "ExecutiveDeckOutline",
    "MultiAudienceRewrite",
    "PublicMicrositeBundle",
    "PublicMicrositePage",
    "REPORT_TEMPLATES",
    "Report",
    "ReportApprovalEvent",
    "ReportSection",
    "ReportTemplate",
    "build_executive_deck",
    "build_public_microsite",
    "build_report_from_template",
    "decide_claim",
    "get_report_template",
    "list_report_templates",
    "rewrite_for_audiences",
    "transition_report",
    "build_content_index",
    "completeness_check",
    "prepublication_qa",
]
