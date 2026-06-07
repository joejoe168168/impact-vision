"""Deterministic ESG toolbox checklist, readiness, and crosswalk helpers."""

from __future__ import annotations

from openharness.impact.toolbox.models import (
    AssessmentQuestion,
    ToolboxImpactToolRecommendation,
    ToolboxInputField,
    ToolboxInputPlan,
    ToolboxOutputBlueprint,
    ToolboxAssessmentResult,
    ToolboxToolSpec,
    ToolboxWorkflowPlan,
)
from openharness.impact.toolbox.registry import get_toolbox_tool


METRIC_CROSSWALK: dict[str, dict[str, list[str]]] = {
    "OI4112": {
        "carbon": ["GHG Scope 1/2 emissions evidence", "ESRS E1-6", "ISSB IFRS S2 metrics and targets", "GRI 305"],
        "disclosure": ["ESRS E1", "ISSB IFRS S2", "GRI 305"],
    },
    "OI6697": {
        "carbon": ["Energy consumption activity data", "Scope 2 purchased energy support", "ESRS E1-5"],
        "disclosure": ["ESRS E1-5 energy consumption"],
    },
    "OI1479": {
        "carbon": ["Product or operational GHG emissions", "GHG Protocol inventory", "ESRS E1-6"],
        "export": ["CBAM embedded emissions support where product-specific"],
    },
    "PD9427": {
        "carbon": ["Product carbon footprint", "EU Battery/ESPR DPP carbon-footprint field"],
        "export": ["Product carbon-footprint data pack"],
    },
    "OI1697": {
        "disclosure": ["ESRS E3 water", "GRI 303", "AWS water stewardship evidence"],
    },
    "OI1120": {
        "supplier": ["Supplier code or supplier ESG screening evidence", "CSDDD value-chain due diligence"],
        "disclosure": ["ESRS S2/G1 supplier disclosures"],
    },
    "OI5942": {
        "export": ["ESPR/DPP substances of concern support"],
        "disclosure": ["ESRS E2 pollution support"],
    },
}


def build_tool_checklist(tool: ToolboxToolSpec | str) -> list[AssessmentQuestion]:
    """Build checklist questions from a toolbox spec."""
    spec = get_toolbox_tool(tool) if isinstance(tool, str) else tool
    return [
        AssessmentQuestion(
            id=f"{spec.tool_id}:{req.id}",
            requirement_id=req.id,
            question=f"Can the company evidence {req.title.lower()} for {spec.title}?",
            evidence_examples=req.evidence_examples,
        )
        for req in spec.requirements
    ]


def assess_tool_readiness(
    tool: ToolboxToolSpec | str,
    *,
    company_description: str = "",
    document_text: str = "",
    reported_metrics: dict[str, object] | None = None,
    product_code: str = "",
    country: str = "",
    supplier_profile: str = "",
) -> ToolboxAssessmentResult:
    """Score readiness using transparent keyword and provided-data coverage.

    This deliberately avoids proprietary rating calculations. It answers the
    narrower question: "which public/checklist requirements appear evidenced by
    the supplied text and metrics?"
    """
    spec = get_toolbox_tool(tool) if isinstance(tool, str) else tool
    metrics = {str(k).upper(): str(v) for k, v in (reported_metrics or {}).items()}
    haystack = " ".join([
        company_description,
        document_text,
        product_code,
        country,
        supplier_profile,
        " ".join(metrics.keys()),
        " ".join(metrics.values()),
    ]).lower()
    source_profile_terms: list[str] = []
    if spec.source_profile:
        source_profile_terms = [
            *spec.source_profile.keywords,
            *spec.source_profile.headings,
            spec.source_profile.meta_description,
            " ".join(spec.source_profile.embedded_data_keys),
        ]
    source_context = " ".join(source_profile_terms).lower()

    matched: list[str] = []
    gaps: list[str] = []
    evidence_gaps: list[str] = []
    recommendations: list[str] = []

    for req in spec.requirements:
        keywords = [kw.lower() for kw in req.keywords]
        framework_refs = [ref.lower() for ref in req.framework_refs]
        metric_hit = _metric_supports_requirement(metrics, spec.categories, req)
        text_hit = any(kw and kw in haystack for kw in [*keywords, *framework_refs])
        source_context_hit = any(
            kw and kw in haystack and kw in source_context
            for kw in [*keywords, *framework_refs]
        )
        special_hit = _special_input_supports_requirement(spec.tool_id, req.id, product_code, country)

        if metric_hit or text_hit or source_context_hit or special_hit:
            matched.append(req.id)
        else:
            gaps.append(req.id)
            evidence = ", ".join(req.evidence_examples[:2]) if req.evidence_examples else "documented evidence"
            evidence_gaps.append(f"{req.title}: provide {evidence}.")
            recommendations.append(f"Prepare evidence for {req.title.lower()} before using {spec.title} for external reporting or assurance.")

    total = max(len(spec.requirements), 1)
    score = round(len(matched) / total * 100)
    confidence = "high" if document_text and len(document_text) > 500 else "medium" if haystack.strip() else "low"

    if spec.tool_id in {"cbam", "cbam-export", "cbam-steel"}:
        if product_code:
            recommendations.insert(0, "Validate the product code against the current official CBAM CN-code list before filing.")
        else:
            evidence_gaps.insert(0, "CBAM applicability: provide product CN/HS code.")
        if not country:
            evidence_gaps.insert(0, "CBAM applicability: provide export/import country context.")

    return ToolboxAssessmentResult(
        tool_id=spec.tool_id,
        title=spec.title,
        score_pct=int(score),
        matched_requirement_ids=matched,
        gap_requirement_ids=gaps,
        evidence_gaps=evidence_gaps,
        recommendations=_dedupe(recommendations)[:8],
        source_urls=_dedupe([source.url for source in spec.sources]),
        confidence=confidence,
        as_of=spec.as_of,
    )


def crosswalk_reported_metrics(
    reported_metrics: dict[str, object],
    *,
    tool_id: str = "",
    category: str = "",
) -> dict[str, list[str]]:
    """Map known Impact Vision metric IDs to toolbox/framework evidence uses."""
    categories: list[str]
    if tool_id:
        categories = list(get_toolbox_tool(tool_id).categories)
    elif category and category != "all":
        categories = [category]
    else:
        categories = ["carbon", "disclosure", "export", "supplier", "rating"]

    out: dict[str, list[str]] = {}
    for raw_id in reported_metrics:
        metric_id = str(raw_id).upper()
        mappings = METRIC_CROSSWALK.get(metric_id, {})
        refs: list[str] = []
        for cat in categories:
            refs.extend(mappings.get(cat, []))
        if refs:
            out[metric_id] = _dedupe(refs)
    return out


def build_toolbox_workflow_plan(
    tool: ToolboxToolSpec | str,
    *,
    company_description: str = "",
    sector: str = "",
    jurisdiction: str = "",
    document_text: str = "",
    reported_metrics: dict[str, object] | None = None,
    product_code: str = "",
    country: str = "",
    supplier_profile: str = "",
) -> ToolboxWorkflowPlan:
    """Plan how an ESG toolbox module should be used in the impact workflow.

    The result is deterministic product intelligence rather than a legal or
    assurance opinion. It helps agents and UI surfaces ask fewer questions,
    reuse existing Impact Vision context, and route outputs to the right tools.
    """
    spec = get_toolbox_tool(tool) if isinstance(tool, str) else tool
    metrics = {str(k).upper(): v for k, v in (reported_metrics or {}).items()}
    categories = set(spec.categories)
    input_plan = build_toolbox_input_plan(
        spec,
        company_description=company_description,
        sector=sector,
        jurisdiction=jurisdiction,
        document_text=document_text,
        reported_metrics=metrics,
        product_code=product_code,
        country=country,
        supplier_profile=supplier_profile,
    )
    return ToolboxWorkflowPlan(
        tool_id=spec.tool_id,
        title=spec.title,
        categories=spec.categories,
        improves_impact_tools=_impact_tool_recommendations(categories),
        input_plan=input_plan,
        output_blueprint=build_toolbox_output_blueprint(spec),
        suggested_sequence=_workflow_sequence(categories),
    )


def build_toolbox_input_plan(
    tool: ToolboxToolSpec | str,
    *,
    company_description: str = "",
    sector: str = "",
    jurisdiction: str = "",
    document_text: str = "",
    reported_metrics: dict[str, object] | None = None,
    product_code: str = "",
    country: str = "",
    supplier_profile: str = "",
) -> ToolboxInputPlan:
    """Build a minimal-input plan and autofill status for one module."""
    spec = get_toolbox_tool(tool) if isinstance(tool, str) else tool
    metrics = reported_metrics or {}
    categories = set(spec.categories)
    inferred_context = _infer_context(
        spec,
        company_description=company_description,
        sector=sector,
        jurisdiction=jurisdiction,
        document_text=document_text,
        reported_metrics=metrics,
        product_code=product_code,
        country=country,
        supplier_profile=supplier_profile,
    )

    minimum: list[ToolboxInputField] = [
        _field(
            "company_description",
            "Company or product summary",
            "Scopes the module and lets the agent match requirements to the business model.",
            bool(company_description),
            bool(document_text),
            "Extract from pitch deck, IC memo, company profile, or report text.",
            company_description or _preview(document_text),
        ),
        _field(
            "sector",
            "Sector",
            "Narrows material topics, rating questionnaires, export rules, and benchmark context.",
            bool(sector),
            bool(inferred_context.get("sector")),
            "Infer from company profile, SASB match, product description, or keywords.",
            sector or str(inferred_context.get("sector", "")),
        ),
        _field(
            "jurisdiction",
            "Jurisdiction or market",
            "Determines reporting, import, audit, and disclosure routing.",
            bool(jurisdiction or country),
            bool(inferred_context.get("jurisdiction")),
            "Infer from headquarters, operating geography, export destination, or fund thesis.",
            jurisdiction or country or str(inferred_context.get("jurisdiction", "")),
        ),
        _field(
            "reported_metrics",
            "Existing Impact Vision metrics",
            "Reuses IRIS+ and operational data for ESG evidence crosswalks.",
            bool(metrics),
            False,
            "Use metrics already captured by gap analysis, reports, or investee submissions.",
            ", ".join(sorted(str(k) for k in metrics))[:120],
        ),
        _field(
            "document_text",
            "Evidence text or data-room extract",
            "Lets the readiness engine score evidence coverage without asking every checklist question.",
            bool(document_text),
            bool(company_description),
            "Paste or upload pitch decks, policies, reports, supplier docs, or calculation workbooks.",
            _preview(document_text or company_description),
        ),
    ]

    product_specific_carbon_modules = {"battery", "carbon-iso", "espr"}
    if "export" in categories or spec.tool_id in product_specific_carbon_modules:
        minimum.append(
            _field(
                "product_code",
                "Product, CN, HS, or SKU code",
                "Screens applicability for product rules and routes product-carbon evidence.",
                bool(product_code),
                bool(inferred_context.get("product_code")),
                "Extract from product passport, invoice, bill of materials, or export records.",
                product_code or str(inferred_context.get("product_code", "")),
            )
        )
    if categories & {"supplier", "rating"}:
        minimum.append(
            _field(
                "supplier_profile",
                "Supplier or site profile",
                "Reduces supplier audit questions by reusing known site, labor, and policy context.",
                bool(supplier_profile),
                bool(inferred_context.get("supplier_profile")),
                "Extract from investee portal, supplier questionnaire, audit report, or policy pack.",
                supplier_profile or str(inferred_context.get("supplier_profile", "")),
            )
        )

    optional = [
        ToolboxInputField(
            field="tool_id",
            label="Module",
            reason="Can be chosen automatically from a plain-English query.",
            can_auto_fill=True,
            source_hint="Use search results and aliases.",
            status="provided",
            value_preview=spec.tool_id,
        ),
        ToolboxInputField(
            field="requirements",
            label="Requirement checklist",
            reason="Generated from the module registry; no user input needed.",
            can_auto_fill=True,
            source_hint="Build from normalized module requirements.",
            status="inferable",
            value_preview=f"{len(spec.requirements)} requirements",
        ),
    ]
    completion_fields = minimum
    complete = sum(1 for field in completion_fields if field.status in {"provided", "inferable"})
    completion_pct = round(complete / max(len(completion_fields), 1) * 100)
    return ToolboxInputPlan(
        tool_id=spec.tool_id,
        title=spec.title,
        minimum_fields=minimum,
        optional_fields=optional,
        inferred_context=inferred_context,
        next_questions=_next_questions(minimum),
        ai_assist_steps=_ai_assist_steps(categories),
        completion_pct=completion_pct,
    )


def build_toolbox_output_blueprint(tool: ToolboxToolSpec | str) -> ToolboxOutputBlueprint:
    """Recommend UX components for presenting a module result."""
    spec = get_toolbox_tool(tool) if isinstance(tool, str) else tool
    categories = set(spec.categories)
    widgets = ["readiness score", "matched vs missing requirements", "evidence gap cards"]
    exports = ["json", "csv", "markdown"]
    evidence = ["required evidence", "source links", "owner and deadline"]
    comparisons: list[str] = []
    primary_view = "Evidence readiness workspace"

    if "carbon" in categories:
        primary_view = "Carbon readiness and calculation workspace"
        widgets.extend(["Scope 1/2/3 coverage matrix", "activity data table", "target trajectory"])
        exports.extend(["xlsx", "assurance pack"])
        comparisons.extend(["baseline vs current year", "location-based vs market-based Scope 2"])
    if "export" in categories:
        primary_view = "Export compliance applicability workspace"
        widgets.extend(["applicability decision tree", "product-code evidence panel", "filing calendar"])
        exports.extend(["customer data pack", "regulatory checklist"])
        comparisons.extend(["covered vs not covered products", "country and route comparison"])
    if "supplier" in categories:
        primary_view = "Supplier ESG audit workspace"
        widgets.extend(["supplier risk heatmap", "CAPA tracker", "policy evidence table"])
        exports.extend(["supplier questionnaire", "CAPA register"])
        comparisons.extend(["supplier vs supplier", "pre-audit vs post-audit"])
    if "rating" in categories:
        if "supplier" not in categories:
            primary_view = "Rating and audit preparation workspace"
        widgets.extend(["theme scorecards", "document expiry tracker", "questionnaire coverage"])
        exports.extend(["rating prep pack", "document request list"])
        comparisons.extend(["current vs target rating readiness"])
    if "disclosure" in categories:
        primary_view = "Disclosure gap and crosswalk workspace"
        widgets.extend(["framework crosswalk", "material topic matrix", "disclosure status table"])
        exports.extend(["disclosure index", "board summary"])
        comparisons.extend(["framework vs framework", "reported vs required disclosures"])

    return ToolboxOutputBlueprint(
        tool_id=spec.tool_id,
        title=spec.title,
        primary_view=primary_view,
        widgets=_dedupe(widgets),
        export_formats=_dedupe(exports),
        evidence_sections=_dedupe(evidence),
        comparison_views=_dedupe(comparisons),
    )


def _metric_supports_requirement(metrics: dict[str, str], categories: list[str], req: object) -> bool:
    if not metrics:
        return False
    title = getattr(req, "title", "").lower()
    req_id = getattr(req, "id", "").lower()
    metric_ids = set(metrics)
    if any(cat in categories for cat in ("carbon", "export")) and {"OI4112", "OI1479", "PD9427"} & metric_ids:
        return any(token in title or token in req_id for token in ("emission", "carbon", "activity", "technical", "metric", "target"))
    if any(cat in categories for cat in ("carbon", "export")) and {"OI6697"} & metric_ids:
        return any(token in title or token in req_id for token in ("energy", "electricity", "scope 2", "activity", "metric", "target"))
    if "disclosure" in categories and {"OI1697", "OI1120", "OI5942"} & metric_ids:
        return any(token in title or token in req_id for token in ("metric", "water", "supplier", "technical"))
    return False


def _impact_tool_recommendations(categories: set[str]) -> list[ToolboxImpactToolRecommendation]:
    recommendations = [
        ToolboxImpactToolRecommendation(
            impact_tool="gap_analysis",
            improvement="Use ESG module requirements to turn missing impact metrics into disclosure-ready evidence gaps.",
            handoff="Feed crosswalk results and missing requirement IDs into gap-analysis remediation cards.",
            priority="high",
        ),
        ToolboxImpactToolRecommendation(
            impact_tool="evidence_review",
            improvement="Use module checklists as evidence prompts for policy, calculation, audit, and report review.",
            handoff="Create evidence review tasks from missing requirements and source URLs.",
            priority="high",
        ),
        ToolboxImpactToolRecommendation(
            impact_tool="impact_report",
            improvement="Add an ESG readiness section next to SDG, 5D, and IRIS+ outputs.",
            handoff="Render score, evidence gaps, crosswalks, and source-backed recommendations.",
            priority="medium",
        ),
    ]
    if "carbon" in categories:
        recommendations.extend([
            ToolboxImpactToolRecommendation(
                impact_tool="emission_factors",
                improvement="Use carbon modules to route activity data, emission factors, Scope 2 methods, and assurance checks.",
                handoff="Pass activity-data gaps and metric IDs such as OI4112/OI6697 into carbon calculations.",
                priority="high",
            ),
            ToolboxImpactToolRecommendation(
                impact_tool="climate_scenario_risk",
                improvement="Use inventory and target readiness to strengthen transition-risk assumptions.",
                handoff="Use GHG coverage and SBTi gaps as inputs to climate scenario notes.",
                priority="medium",
            ),
        ])
    if "export" in categories:
        recommendations.extend([
            ToolboxImpactToolRecommendation(
                impact_tool="product_passport",
                improvement="Route product-code, origin, traceability, and carbon-footprint fields into passport readiness.",
                handoff="Use product_code, country, and technical-data gaps as DPP/product-passport fields.",
                priority="high",
            ),
            ToolboxImpactToolRecommendation(
                impact_tool="regulatory_calendar",
                improvement="Convert applicability decisions into filing, customer data request, and review deadlines.",
                handoff="Add filing-deadline requirement gaps to the regulatory calendar.",
                priority="medium",
            ),
        ])
    if "supplier" in categories:
        recommendations.extend([
            ToolboxImpactToolRecommendation(
                impact_tool="hrdd_assess",
                improvement="Use supplier due-diligence modules to enrich salience, grievance, remediation, and CSDDD readiness.",
                handoff="Pass supplier profile and missing labor/traceability evidence to HRDD scoring.",
                priority="high",
            ),
            ToolboxImpactToolRecommendation(
                impact_tool="investee_portal",
                improvement="Generate shorter supplier questionnaires from only missing ESG/audit evidence fields.",
                handoff="Seed portal questions from missing requirements and evidence examples.",
                priority="high",
            ),
        ])
    if "rating" in categories:
        recommendations.extend([
            ToolboxImpactToolRecommendation(
                impact_tool="verification_workspace",
                improvement="Turn rating/audit readiness gaps into document collection and reviewer workflow tasks.",
                handoff="Create owner, due-date, and evidence-review items from low-coverage requirements.",
                priority="medium",
            ),
            ToolboxImpactToolRecommendation(
                impact_tool="greenwashing_reviewer",
                improvement="Use weak-documentation gaps to identify claims that need substantiation before external rating submissions.",
                handoff="Flag unsupported claims and stale policy evidence.",
                priority="medium",
            ),
        ])
    if "disclosure" in categories:
        recommendations.extend([
            ToolboxImpactToolRecommendation(
                impact_tool="framework_assess",
                improvement="Use disclosure modules as routing and crosswalk layers across ISSB, ESRS, GRI, SASB, CDP, and related standards.",
                handoff="Pass material topics, known metrics, and missing disclosures to framework scans.",
                priority="high",
            ),
            ToolboxImpactToolRecommendation(
                impact_tool="lp_narrative",
                improvement="Convert technical ESG disclosure status into LP-ready narrative with caveats and evidence links.",
                handoff="Use readiness bands, matched requirements, and source URLs in LP Q&A responses.",
                priority="medium",
            ),
        ])
    return recommendations


def _workflow_sequence(categories: set[str]) -> list[str]:
    sequence = [
        "Start from existing company profile, sector, geography, reported metrics, and uploaded evidence.",
        "Search or select the most relevant ESG module, then run the input plan before asking new questions.",
        "Run readiness assessment and crosswalk known Impact Vision metrics into ESG evidence uses.",
        "Create evidence-review tasks for only the missing requirements.",
    ]
    if categories & {"export", "supplier"}:
        sequence.append("Generate a focused investee or supplier request pack for unresolved product, origin, site, and audit fields.")
    if "carbon" in categories:
        sequence.append("Route activity-data and emission-factor gaps into carbon accounting and target-setting workflows.")
    if "disclosure" in categories:
        sequence.append("Render framework crosswalk and disclosure index outputs for reporting and LP review.")
    return sequence


def _infer_context(
    spec: ToolboxToolSpec,
    *,
    company_description: str,
    sector: str,
    jurisdiction: str,
    document_text: str,
    reported_metrics: dict[str, object],
    product_code: str,
    country: str,
    supplier_profile: str,
) -> dict[str, object]:
    text = " ".join([company_description, document_text, supplier_profile]).lower()
    inferred: dict[str, object] = {}
    if not sector:
        if any(term in text for term in ("steel", "aluminium", "cement", "fertilizer", "hydrogen")):
            inferred["sector"] = "heavy industry"
        elif any(term in text for term in ("battery", "vehicle", "electronics", "sku", "product")):
            inferred["sector"] = "manufacturing"
        elif any(term in text for term in ("finance", "loan", "fund", "investment", "portfolio")):
            inferred["sector"] = "financial services"
        elif any(term in text for term in ("mine", "mining", "mineral", "smelter")):
            inferred["sector"] = "mining"
    if not jurisdiction and not country:
        if any(term in text for term in ("eu", "europe", "csrd", "cbam", "esrs", "sfdr")) or set(spec.categories) & {"export"}:
            inferred["jurisdiction"] = "EU"
        elif "hong kong" in text or "hkex" in text:
            inferred["jurisdiction"] = "Hong Kong"
    if not product_code:
        import re

        match = re.search(r"\b(?:cn|hs)\s*code\s*[:#-]?\s*([0-9]{4,10})\b", text)
        if match:
            inferred["product_code"] = match.group(1)
    if not supplier_profile and set(spec.categories) & {"supplier", "rating"}:
        supplier_terms = [term for term in ("supplier", "site", "factory", "audit", "worker", "policy") if term in text]
        if supplier_terms:
            inferred["supplier_profile"] = ", ".join(supplier_terms)
    if reported_metrics:
        inferred["metric_count"] = len(reported_metrics)
        inferred["metric_crosswalk"] = crosswalk_reported_metrics(reported_metrics, tool_id=spec.tool_id)
    return inferred


def _field(
    field: str,
    label: str,
    reason: str,
    provided: bool,
    inferable: bool,
    source_hint: str,
    value_preview: str = "",
) -> ToolboxInputField:
    status = "provided" if provided else "inferable" if inferable else "missing"
    return ToolboxInputField(
        field=field,
        label=label,
        reason=reason,
        can_auto_fill=provided or inferable,
        source_hint=source_hint,
        status=status,
        value_preview=_preview(value_preview),
    )


def _next_questions(fields: list[ToolboxInputField]) -> list[str]:
    questions: list[str] = []
    for field in fields:
        if field.status == "missing":
            questions.append(f"Please provide {field.label.lower()}.")
    return questions[:4]


def _ai_assist_steps(categories: set[str]) -> list[str]:
    steps = [
        "Extract company summary, sector, geography, products, and known metrics from uploaded documents.",
        "Use existing Impact Vision reported_metrics before asking for new ESG data.",
        "Ask only for fields still marked missing after document and context inference.",
    ]
    if "carbon" in categories:
        steps.append("Parse GHG inventory tables, utility bills, fuel records, and target statements into activity-data prompts.")
    if "export" in categories:
        steps.append("Extract product codes, origin, destination, bill-of-materials, and traceability fields from invoices or product passports.")
    if "supplier" in categories:
        steps.append("Summarize supplier policies, audits, CAPA logs, and grievance records into supplier-profile fields.")
    if "rating" in categories:
        steps.append("Detect policy names, expiry dates, training logs, incident records, and rating-questionnaire evidence.")
    if "disclosure" in categories:
        steps.append("Map claims and metrics to disclosure topics and prepare a framework crosswalk.")
    return steps


def _preview(value: object, limit: int = 120) -> str:
    text = str(value or "").strip().replace("\n", " ")
    return text[: limit - 1] + "..." if len(text) > limit else text


def _special_input_supports_requirement(tool_id: str, req_id: str, product_code: str, country: str) -> bool:
    if tool_id == "carbon-iso":
        if req_id == "standard-selection" and (product_code or country):
            return True
    if tool_id in {"cbam", "cbam-export", "cbam-steel", "battery", "eudr", "espr"}:
        if req_id == "applicability" and (product_code or country):
            return True
        if req_id == "technical-data" and product_code:
            return True
    return False


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
    return out
