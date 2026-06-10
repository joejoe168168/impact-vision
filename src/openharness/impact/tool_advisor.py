"""Deterministic tool router for the Impact Vision tool surface.

Given a free-text user query, recommend the most relevant agent tools and
(optionally) a multi-step playbook. The routing table is static data so the
mapping can be audited at a glance; scoring is plain keyword/phrase overlap —
no LLM call, no network access.

Used by :class:`openharness.tools.impact.advisor_tool.ImpactAdvisorTool`.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

__all__ = [
    "ToolRoute",
    "Playbook",
    "TOOL_ROUTES",
    "PLAYBOOKS",
    "route_query",
    "get_playbook",
    "list_playbooks",
    "routed_tool_names",
]


class ToolRoute(BaseModel):
    """One entry in the routing table."""

    tool: str
    category: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    example: str = ""


class PlaybookStep(BaseModel):
    tool: str
    purpose: str


class Playbook(BaseModel):
    playbook_id: str
    name: str
    when_to_use: str
    keywords: list[str] = Field(default_factory=list)
    steps: list[PlaybookStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Routing table — keep in sync with create_default_tool_registry().
# Keywords are matched case-insensitively as whole words or phrases.
# ---------------------------------------------------------------------------

TOOL_ROUTES: list[ToolRoute] = [
    # --- Intake & screening -------------------------------------------------
    ToolRoute(
        tool="pitch_deck_analyze",
        category="intake",
        summary="Analyze a pitch deck / investment memo PDF end-to-end: claims, SDGs, DD gaps, company extraction.",
        keywords=["pitch deck", "deck", "memo", "pdf", "upload", "new deal", "intake", "analyze document", "investment memo"],
        example="pitch_deck_analyze(file_path='deck.pdf')",
    ),
    ToolRoute(
        tool="document_analysis",
        category="intake",
        summary="Extract impact-relevant content from arbitrary documents (reports, policies).",
        keywords=["document", "report text", "extract", "policy document", "annual report"],
    ),
    ToolRoute(
        tool="exclusion_screening",
        category="intake",
        summary="Screen a company against exclusion lists (weapons, tobacco, coal, etc.).",
        keywords=["exclusion", "excluded", "negative screen", "blacklist", "prohibited", "screening"],
    ),
    ToolRoute(
        tool="guided_assessment",
        category="intake",
        summary="Interactive step-by-step impact assessment when no documents are available.",
        keywords=["guided", "step by step", "interview", "questionnaire", "no documents", "manual assessment"],
    ),
    # --- Core scoring -------------------------------------------------------
    ToolRoute(
        tool="five_dimension_assess",
        category="scoring",
        summary="IMP 5-Dimension impact scoring (What/Who/How Much/Contribution/Risk) + additionality.",
        keywords=["five dimension", "5 dimension", "5d", "imp", "additionality", "impact score", "dimension"],
    ),
    ToolRoute(
        tool="sdg_mapper",
        category="scoring",
        summary="Map a company to UN SDG goals and targets with alignment scores.",
        keywords=["sdg", "sustainable development goal", "goal 7", "un goals", "sdg alignment", "targets"],
    ),
    ToolRoute(
        tool="gap_analysis",
        category="scoring",
        summary="Compare reported metrics against the IRIS+ Core Metric Set; find missing metrics.",
        keywords=["gap", "missing metrics", "coverage", "core metric", "what's missing"],
    ),
    ToolRoute(
        tool="iris_catalog",
        category="scoring",
        summary="Search and browse the IRIS+ metric catalog.",
        keywords=["iris", "iris+", "metric catalog", "search metric", "oi4112", "pi", "metric definition"],
    ),
    ToolRoute(
        tool="impact_metric_recommender",
        category="scoring",
        summary="Recommend IRIS+ metrics for a company's sector and themes.",
        keywords=["recommend metric", "which metrics", "kpi suggestion", "metric recommendation", "suggest kpi"],
    ),
    ToolRoute(
        tool="impact_quantifier",
        category="scoring",
        summary="Quantify impact in physical units (people reached, tCO2e avoided) from raw data.",
        keywords=["quantify", "how much impact", "people reached", "units", "impact quantification"],
    ),
    ToolRoute(
        tool="impact_valuation",
        category="scoring",
        summary="Monetize impact (SROI, impact-weighted accounts, IMM-style valuation).",
        keywords=["sroi", "monetize", "valuation", "impact multiple", "imm", "dollar value", "impact-weighted"],
    ),
    ToolRoute(
        tool="impact_data_quality",
        category="scoring",
        summary="Assess data quality of reported metrics (provenance, freshness, verification).",
        keywords=["data quality", "provenance", "reliable", "freshness", "verify data"],
    ),
    # --- DD & risk ----------------------------------------------------------
    ToolRoute(
        tool="dd_checklist",
        category="dd",
        summary="122-question due-diligence checklist (GIIN/PCV/Seraf/IMP) with NESTA evidence levels.",
        keywords=["due diligence", "dd", "checklist", "dd questions", "diligence questions", "nesta"],
    ),
    ToolRoute(
        tool="greenwashing_detect",
        category="dd",
        summary="Greenwashing risk score (0-100) plus per-claim explainable review (action='review_claims').",
        keywords=["greenwash", "greenwashing", "impact washing", "claims review", "unsubstantiated", "exaggerated claims", "vague claims"],
        example="greenwashing_detect(action='review_claims', claims=[...])",
    ),
    ToolRoute(
        tool="impact_risk_opportunity",
        category="dd",
        summary="Impact risk/opportunity register with likelihood x severity matrix (14 risk categories).",
        keywords=["impact risk", "risk register", "opportunity", "likelihood", "severity", "risk matrix"],
    ),
    ToolRoute(
        tool="hrdd_assess",
        category="dd",
        summary="Human-rights & value-chain due diligence incl. SMETA/SA8000/RBA/BSCI audit-scheme readiness.",
        keywords=["human rights", "hrdd", "labor", "labour", "supply chain audit", "smeta", "sa8000", "rba", "bsci", "conflict minerals", "csddd", "forced labor"],
    ),
    ToolRoute(
        tool="climate_scenario_risk",
        category="dd",
        summary="Climate scenario analysis (physical + transition risk) for TCFD/ISSB disclosure.",
        keywords=["climate scenario", "physical risk", "transition risk", "warming", "1.5c", "2c", "ngfs"],
    ),
    # --- Frameworks & compliance --------------------------------------------
    ToolRoute(
        tool="framework_assess",
        category="compliance",
        summary="Multi-framework assessment: SASB, GRI, TCFD, SFDR PAI, EDCI, UNPRI, ISSB S1/S2, ESRS, OPIM, CDP.",
        keywords=["sasb", "gri", "tcfd", "sfdr", "edci", "unpri", "issb", "esrs", "csrd", "cdp", "framework", "disclosure standard", "materiality"],
    ),
    ToolRoute(
        tool="cross_reference",
        category="compliance",
        summary="Translate a metric/concept across 10+ frameworks (59-concept map).",
        keywords=["cross reference", "crosswalk", "equivalent", "map metric", "correspond", "translate metric"],
    ),
    ToolRoute(
        tool="esg_toolbox",
        category="compliance",
        summary="33-module ESG toolbox router: ratings (MSCI/EcoVadis/CSA), export compliance (CBAM/EUDR/battery), supplier ESG, carbon schemes.",
        keywords=["esg toolbox", "ecovadis", "msci rating", "csa", "iss", "cbam", "eudr", "battery regulation", "espr", "export compliance", "supplier esg", "sbti", "carbon scheme"],
    ),
    ToolRoute(
        tool="regulatory_calendar",
        category="compliance",
        summary="Jurisdiction regulatory deadline calendar (EU/UK/US/SG/CH/CA/JP/AU) incl. SFDR, CSRD, CBAM, EUDR.",
        keywords=["regulatory", "deadline", "calendar", "compliance dates", "jurisdiction", "when due", "filing"],
    ),
    ToolRoute(
        tool="product_passport",
        category="compliance",
        summary="EU Digital Product Passport import/mapping + Battery Regulation / ESPR readiness.",
        keywords=["product passport", "dpp", "battery passport", "digital passport", "espr"],
    ),
    ToolRoute(
        tool="emission_factors",
        category="compliance",
        summary="Versioned emission-factor catalog with uncertainty bands and sensitivity analysis.",
        keywords=["emission factor", "ghg", "scope 1", "scope 2", "carbon accounting", "co2", "tco2e", "carbon footprint"],
    ),
    ToolRoute(
        tool="ai_governance",
        category="compliance",
        summary="AI governance review for AI-assisted impact analysis (EU AI Act aware).",
        keywords=["ai governance", "ai act", "model risk", "ai policy", "responsible ai"],
    ),
    # --- Evidence & verification ---------------------------------------------
    ToolRoute(
        tool="evidence_review",
        category="verification",
        summary="Review queue for AI-extracted evidence with policy-driven bulk/auto decisions.",
        keywords=["evidence review", "review queue", "approve extraction", "ai extraction"],
    ),
    ToolRoute(
        tool="verification_workspace",
        category="verification",
        summary="Verification prep (BlueMark/IFC OPIM/AA1000 readiness, evidence map) + third-party verifier workspace with findings and comments.",
        keywords=["verification", "verify", "assurance", "bluemark", "ifc opim", "aa1000", "auditor", "verifier", "readiness check", "findings"],
        example="verification_workspace(action='readiness_check', verification_target='bluemark', ...)",
    ),
    ToolRoute(
        tool="stakeholder_voice",
        category="verification",
        summary="Lean Data surveys, consent records, beneficiary feedback quality scoring, feedback-claim links.",
        keywords=["stakeholder", "survey", "lean data", "consent", "voice", "interview beneficiaries"],
    ),
    ToolRoute(
        tool="beneficiary_feedback",
        category="verification",
        summary="Import and analyze beneficiary feedback datasets.",
        keywords=["beneficiary", "feedback", "csat", "nps", "customer voice"],
    ),
    # --- Reporting & LP -------------------------------------------------------
    ToolRoute(
        tool="impact_report",
        category="reporting",
        summary="Full impact assessment report (HTML/XLSX/CSV/JSON/PDF) + LLM narrative prompts (exec summary, key findings, case study).",
        keywords=["report", "generate report", "html report", "executive summary", "narrative", "case study", "write up", "summary report"],
        example="impact_report(company_name=..., narrative_mode='narrative_prompt', narrative_section='executive_summary')",
    ),
    ToolRoute(
        tool="lp_narrative",
        category="reporting",
        summary="Audit-friendly LP narratives and Q&A workspace constrained to verified data.",
        keywords=["lp narrative", "lp letter", "limited partner", "investor letter", "lp q&a"],
    ),
    ToolRoute(
        tool="lp_ddq_export",
        category="reporting",
        summary="Export LP DDQ answers (ILPA/GIIN/EDCI/SFDR) to XLSX/CSV.",
        keywords=["ddq", "ilpa", "lp questionnaire", "ddq export", "due diligence questionnaire"],
    ),
    ToolRoute(
        tool="improvement_advisor",
        category="reporting",
        summary="Prioritized improvement roadmap for a company's impact measurement practice.",
        keywords=["improve", "next steps", "roadmap", "maturity", "what should we do"],
    ),
    # --- Portfolio & monitoring ----------------------------------------------
    ToolRoute(
        tool="portfolio_analyze",
        category="portfolio",
        summary="Batch analysis and scenario modeling across a portfolio of companies.",
        keywords=["portfolio", "batch", "all companies", "fund level", "aggregate", "scenario"],
    ),
    ToolRoute(
        tool="portfolio_query",
        category="portfolio",
        summary="Natural-language portfolio queries returning citations from approved data only.",
        keywords=["query portfolio", "which companies", "ask portfolio", "nlq", "natural language"],
    ),
    ToolRoute(
        tool="trend_analysis",
        category="portfolio",
        summary="Metric trend analysis and trajectory projection over time.",
        keywords=["trend", "over time", "trajectory", "historical", "time series", "progress"],
    ),
    ToolRoute(
        tool="monitoring",
        category="portfolio",
        summary="Set up ongoing monitoring rules and alerts for company metrics.",
        keywords=["monitor", "alert", "watch", "threshold", "ongoing"],
    ),
    ToolRoute(
        tool="pipeline",
        category="portfolio",
        summary="Multi-step analysis pipeline runner for repeatable assessments.",
        keywords=["pipeline", "workflow run", "automate steps"],
    ),
    ToolRoute(
        tool="decision_workflow",
        category="portfolio",
        summary="IC decision workflow with stage gates and recorded rationale.",
        keywords=["investment committee", "ic memo", "decision", "stage gate", "approve deal"],
    ),
    ToolRoute(
        tool="exit_impact",
        category="portfolio",
        summary="OPIM Principle 8 exit-impact assessment: durability of impact post-exit.",
        keywords=["exit", "divest", "post-exit", "opim 8", "responsible exit"],
    ),
    # --- Engagement / consultant ----------------------------------------------
    ToolRoute(
        tool="engagement_workspace",
        category="engagement",
        summary="Consultant engagement workspace: 12 productised bundles, proposals, checklists, deliverables.",
        keywords=["engagement", "proposal", "consultant", "client", "deliverable", "scope of work"],
    ),
    ToolRoute(
        tool="engagement_suite",
        category="engagement",
        summary="Consolidated consultant suite (46 actions): data room, value creation, reporting studio, training, regulatory, verification bundle.",
        keywords=["data room", "value creation", "reporting studio", "training", "workshop", "coaching", "microsite", "benchmark"],
    ),
    ToolRoute(
        tool="toc_builder",
        category="engagement",
        summary="Theory of Change canvas + 11-rule logic validator + multi-framework KPI generator.",
        keywords=["theory of change", "toc", "logic model", "outcomes chain", "kpi framework", "causal chain"],
    ),
    ToolRoute(
        tool="investee_portal",
        category="engagement",
        summary="Investee-facing data collection portal: questionnaires, submissions, reminders.",
        keywords=["investee", "portal", "data collection", "questionnaire submission", "request data"],
    ),
]


# ---------------------------------------------------------------------------
# Playbooks — multi-step plans for common fund workflows.
# ---------------------------------------------------------------------------

PLAYBOOKS: list[Playbook] = [
    Playbook(
        playbook_id="deal_screening",
        name="New deal screening & impact DD",
        when_to_use="A new pitch deck or investment memo arrives and you need a full impact DD pass.",
        keywords=["new deal", "pitch deck", "screen", "due diligence", "dd", "evaluate company", "assess startup"],
        steps=[
            PlaybookStep(tool="pitch_deck_analyze", purpose="Extract text, claims, SDGs, company model; run DD checklist."),
            PlaybookStep(tool="exclusion_screening", purpose="Confirm no exclusion-list conflicts."),
            PlaybookStep(tool="five_dimension_assess", purpose="Score the 5 IMP dimensions + additionality."),
            PlaybookStep(tool="sdg_mapper", purpose="Score SDG goal/target alignment."),
            PlaybookStep(tool="gap_analysis", purpose="Find missing core metrics vs sector benchmark."),
            PlaybookStep(tool="greenwashing_detect", purpose="Risk-score claims; action='review_claims' for per-claim review."),
            PlaybookStep(tool="impact_report", purpose="Generate the assessment report (+ narrative prompts)."),
        ],
    ),
    Playbook(
        playbook_id="lp_reporting",
        name="LP reporting & DDQ",
        when_to_use="Quarterly/annual LP reporting, LP letters, or answering an LP due-diligence questionnaire.",
        keywords=["lp report", "lp letter", "quarterly report", "annual report", "ddq", "limited partner", "investor update"],
        steps=[
            PlaybookStep(tool="impact_report", purpose="Generate company/fund assessment (report_type='lp_ready')."),
            PlaybookStep(tool="lp_narrative", purpose="Produce audit-friendly LP narrative bound to verified data."),
            PlaybookStep(tool="lp_ddq_export", purpose="Export ILPA/GIIN/EDCI/SFDR DDQ answers to XLSX."),
        ],
    ),
    Playbook(
        playbook_id="regulatory_compliance",
        name="Regulatory & disclosure compliance",
        when_to_use="You need to know which regulations apply, deadlines, and disclosure readiness (SFDR, CSRD, CBAM, EUDR...).",
        keywords=["regulation", "compliance", "sfdr", "csrd", "deadline", "disclosure", "cbam", "eudr", "filing"],
        steps=[
            PlaybookStep(tool="regulatory_calendar", purpose="Build the jurisdiction deadline calendar."),
            PlaybookStep(tool="framework_assess", purpose="Assess readiness per framework (ESRS, SFDR, ISSB, CDP...)."),
            PlaybookStep(tool="esg_toolbox", purpose="Drill into specific schemes (CBAM, EUDR, battery, ratings)."),
        ],
    ),
    Playbook(
        playbook_id="verification_assurance",
        name="Verification & assurance",
        when_to_use="Preparing for third-party verification (BlueMark, IFC OPIM, AA1000) or running a verifier engagement.",
        keywords=["verification", "assurance", "bluemark", "audit", "verifier", "aa1000", "opim"],
        steps=[
            PlaybookStep(tool="verification_workspace", purpose="action='readiness_check' then 'evidence_map' to find gaps."),
            PlaybookStep(tool="evidence_review", purpose="Clear the AI-extraction review queue."),
            PlaybookStep(tool="verification_workspace", purpose="action='open' to run the verifier workspace with findings."),
        ],
    ),
    Playbook(
        playbook_id="portfolio_review",
        name="Portfolio review & monitoring",
        when_to_use="Fund-level portfolio analysis, trends, and ongoing monitoring.",
        keywords=["portfolio", "fund level", "trends", "monitor", "aggregate", "all companies"],
        steps=[
            PlaybookStep(tool="portfolio_analyze", purpose="Batch-score all companies; scenario modeling."),
            PlaybookStep(tool="trend_analysis", purpose="Trajectories vs targets per metric."),
            PlaybookStep(tool="portfolio_query", purpose="Ad-hoc natural-language questions with citations."),
            PlaybookStep(tool="monitoring", purpose="Set alerts for off-track metrics."),
        ],
    ),
    Playbook(
        playbook_id="supply_chain_hrdd",
        name="Supply chain & human rights DD",
        when_to_use="Supplier/labor/human-rights risk, audit schemes (SMETA, SA8000, RBA), export compliance.",
        keywords=["supply chain", "human rights", "supplier", "labor", "smeta", "sa8000", "conflict minerals", "csddd"],
        steps=[
            PlaybookStep(tool="hrdd_assess", purpose="OECD due-diligence scoring + audit-scheme readiness."),
            PlaybookStep(tool="esg_toolbox", purpose="Scheme deep-dives (BSCI, RBA, conflict minerals, EUDR)."),
            PlaybookStep(tool="product_passport", purpose="If physical products: DPP / battery / ESPR readiness."),
        ],
    ),
    Playbook(
        playbook_id="carbon_climate",
        name="Carbon accounting & climate risk",
        when_to_use="GHG inventory, emission factors, climate scenarios, TCFD/ISSB climate disclosure.",
        keywords=["carbon", "ghg", "emissions", "climate", "tcfd", "scope 1", "scope 2", "net zero", "sbti"],
        steps=[
            PlaybookStep(tool="emission_factors", purpose="Price the inventory with versioned factors + sensitivity."),
            PlaybookStep(tool="climate_scenario_risk", purpose="Physical + transition scenario analysis."),
            PlaybookStep(tool="framework_assess", purpose="TCFD / ISSB S2 disclosure readiness."),
            PlaybookStep(tool="esg_toolbox", purpose="SBTi target validation and carbon schemes."),
        ],
    ),
    Playbook(
        playbook_id="data_collection",
        name="Investee data collection & quality",
        when_to_use="Collecting metrics and stakeholder evidence from portfolio companies.",
        keywords=["collect data", "investee data", "survey", "stakeholder", "data quality", "questionnaire"],
        steps=[
            PlaybookStep(tool="investee_portal", purpose="Issue questionnaires and track submissions."),
            PlaybookStep(tool="stakeholder_voice", purpose="Lean Data surveys + consent + feedback quality."),
            PlaybookStep(tool="beneficiary_feedback", purpose="Import and analyze feedback datasets."),
            PlaybookStep(tool="impact_data_quality", purpose="Score the collected data's quality."),
        ],
    ),
    Playbook(
        playbook_id="theory_of_change",
        name="Theory of Change & KPI design",
        when_to_use="Designing or validating a ToC and selecting a KPI framework for a company or fund.",
        keywords=["theory of change", "toc", "logic model", "kpi", "outcomes", "design metrics"],
        steps=[
            PlaybookStep(tool="toc_builder", purpose="Build the ToC canvas; run the 11-rule logic validator."),
            PlaybookStep(tool="impact_metric_recommender", purpose="Recommend IRIS+ metrics per outcome."),
            PlaybookStep(tool="cross_reference", purpose="Map chosen KPIs across reporting frameworks."),
        ],
    ),
]

_PLAYBOOK_INDEX = {p.playbook_id: p for p in PLAYBOOKS}


def routed_tool_names() -> set[str]:
    """All tool names referenced by routes and playbooks (for registry sync tests)."""
    names = {r.tool for r in TOOL_ROUTES}
    for p in PLAYBOOKS:
        names.update(s.tool for s in p.steps)
    return names


_WORD_RE = re.compile(r"[a-z0-9+]+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _phrase_in(phrase: str, query_lower: str, query_tokens: set[str]) -> bool:
    if " " in phrase:
        return phrase in query_lower
    return phrase in query_tokens


def _score_keywords(keywords: list[str], query_lower: str, query_tokens: set[str]) -> tuple[float, list[str]]:
    score = 0.0
    matched: list[str] = []
    for kw in keywords:
        if _phrase_in(kw.lower(), query_lower, query_tokens):
            # Multi-word phrases are stronger signals than single tokens.
            score += 2.0 if " " in kw else 1.0
            matched.append(kw)
    return score, matched


def route_query(query: str, *, limit: int = 5) -> dict:
    """Rank tools and playbooks for a free-text query.

    Returns a dict with ``recommendations`` (ranked tools with matched
    keywords) and ``playbook`` (best-matching playbook, if any).
    """
    query_lower = query.lower()
    query_tokens = set(_tokens(query))

    scored: list[dict] = []
    for route in TOOL_ROUTES:
        score, matched = _score_keywords(route.keywords, query_lower, query_tokens)
        if score > 0:
            scored.append(
                {
                    "tool": route.tool,
                    "category": route.category,
                    "summary": route.summary,
                    "score": score,
                    "matched_keywords": matched,
                    "example": route.example,
                }
            )
    scored.sort(key=lambda r: (-r["score"], r["tool"]))

    best_playbook: dict | None = None
    best_pb_score = 0.0
    for pb in PLAYBOOKS:
        score, matched = _score_keywords(pb.keywords, query_lower, query_tokens)
        if score > best_pb_score:
            best_pb_score = score
            best_playbook = {
                "playbook_id": pb.playbook_id,
                "name": pb.name,
                "when_to_use": pb.when_to_use,
                "score": score,
                "matched_keywords": matched,
                "steps": [{"tool": s.tool, "purpose": s.purpose} for s in pb.steps],
            }

    return {
        "query": query,
        "recommendations": scored[:limit],
        "playbook": best_playbook,
    }


def get_playbook(playbook_id: str) -> Playbook | None:
    return _PLAYBOOK_INDEX.get(playbook_id)


def list_playbooks() -> list[dict]:
    return [
        {
            "playbook_id": p.playbook_id,
            "name": p.name,
            "when_to_use": p.when_to_use,
            "steps": [s.tool for s in p.steps],
        }
        for p in PLAYBOOKS
    ]
