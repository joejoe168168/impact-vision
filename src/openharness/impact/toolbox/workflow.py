"""Workflow helpers that connect the ESG toolbox to Impact Vision analyses.

The registry is intentionally broad. These helpers turn it into a smaller
analyst-facing workflow: which modules matter, what can be inferred from the
company context, what evidence is still missing, and what the UI should show.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from openharness.impact.toolbox.assessors import assess_tool_readiness, crosswalk_reported_metrics
from openharness.impact.toolbox.models import ToolboxAssessmentResult, ToolboxToolSpec
from openharness.impact.toolbox.registry import TOOLBOX_CATEGORIES, list_toolbox_tools, search_toolbox_tools


class ToolboxInputSuggestion(BaseModel):
    """One inferred/defaulted field that can reduce user typing."""

    field: str
    value: object
    confidence: str = "medium"
    reason: str = ""
    source: str = "company_context"


class ToolboxModuleRecommendation(BaseModel):
    """Recommended module with readiness, rationale, and next inputs."""

    tool_id: str
    title: str
    categories: list[str] = Field(default_factory=list)
    score: int
    readiness_score_pct: int
    reason: str = ""
    matched_terms: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    crosswalk: dict[str, list[str]] = Field(default_factory=dict)


class ToolboxUICard(BaseModel):
    """Compact card data for browser or report rendering."""

    tool_id: str
    title: str
    category: str
    readiness_score_pct: int
    priority: str
    status: str
    summary: str
    next_questions: list[str] = Field(default_factory=list)


class ToolboxWorkflowResult(BaseModel):
    """End-to-end ESG workflow bundle for impact tools and UI surfaces."""

    recommended_tools: list[ToolboxModuleRecommendation] = Field(default_factory=list)
    input_suggestions: list[ToolboxInputSuggestion] = Field(default_factory=list)
    metric_crosswalk: dict[str, list[str]] = Field(default_factory=dict)
    ui: dict[str, object] = Field(default_factory=dict)
    next_questions: list[str] = Field(default_factory=list)


_FIELD_SUGGESTION_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "sector",
        (
            "agriculture",
            "agritech",
            "food",
            "solar",
            "energy",
            "fintech",
            "finance",
            "health",
            "education",
            "water",
            "manufacturing",
            "mining",
            "battery",
            "steel",
            "cement",
        ),
        ("company_description",),
    ),
    (
        "jurisdiction",
        (
            "EU",
            "European Union",
            "US",
            "United States",
            "UK",
            "Singapore",
            "Hong Kong",
            "China",
            "Africa",
            "Kenya",
            "India",
        ),
        ("company_description", "geography"),
    ),
)

_TOOL_ROUTE_TERMS: dict[str, list[str]] = {
    "ghg": ["scope 1", "scope 2", "ghg", "greenhouse", "emission", "carbon inventory"],
    "carbon-calculator": ["manufacturing", "factory", "electricity", "fuel", "scope 3", "carbon footprint"],
    "carbon-iso": ["iso 14064", "iso 14067", "iso 14068", "product carbon", "verification"],
    "sbti": ["science based", "net zero", "decarbon", "scope 3", "supplier engagement"],
    "cbam": ["cbam", "cement", "iron", "steel", "aluminium", "fertilizer", "hydrogen", "eu import"],
    "cbam-export": ["export", "cn code", "hs code", "customs", "eu customer"],
    "cbam-steel": ["steel", "iron", "aluminum", "aluminium", "embedded emissions"],
    "battery": ["battery", "digital product passport", "dpp", "recycling", "ev"],
    "eudr": ["deforestation", "forest", "cocoa", "coffee", "rubber", "soy", "palm", "cattle", "wood"],
    "espr": ["ecodesign", "product passport", "repairability", "durability", "circular"],
    "csddd": ["human rights", "value chain", "supplier due diligence", "forced labor", "grievance"],
    "smeta": ["sedex", "smeta", "audit", "labor", "worker"],
    "sa8000": ["social accountability", "worker", "child labor", "forced labor"],
    "amfori-bsci": ["bsci", "supplier audit", "factory audit", "capa"],
    "rba": ["electronics", "responsible business alliance", "vap", "forced labor"],
    "conflict-minerals": ["conflict minerals", "cmrt", "emrt", "smelter", "cobalt", "mica"],
    "aws": ["water", "catchment", "withdrawal", "discharge", "stewardship"],
    "irma": ["mining", "mine", "tailings", "community", "responsible mining"],
    "icma": ["green bond", "social bond", "sustainability bond", "use of proceeds"],
    "climate-bonds": ["climate bond", "certification", "taxonomy"],
    "issb": ["issb", "ifrs s1", "ifrs s2", "sasb"],
    "esrs": ["csrd", "esrs", "double materiality", "european sustainability"],
    "gri": ["gri", "sustainability report", "universal standards"],
    "material": ["materiality", "double materiality", "stakeholder consultation"],
    "cdp": ["cdp", "climate questionnaire", "water questionnaire", "forest questionnaire"],
    "ecovadis": ["ecovadis", "supply chain rating", "scorecard"],
    "msci": ["msci", "esg rating"],
    "csa": ["csa", "s&p global", "corporate sustainability assessment"],
    "iss": ["iss", "stoxx", "governance rating"],
    "aa1000": ["assurance", "stakeholder engagement", "accountability principles"],
    "eu-green-deal": ["green deal", "eu taxonomy", "fit for 55", "omnibus"],
    "nav": ["regulation navigator", "jurisdiction", "source authority"],
    "glossary": ["definition", "terminology", "framework routing"],
}

_CATEGORY_INPUTS: dict[str, list[str]] = {
    "disclosure": ["document_text", "reported_metrics", "sector"],
    "rating": ["document_text", "sector", "reported_metrics"],
    "export": ["product_code", "country", "supplier_profile"],
    "supplier": ["supplier_profile", "country", "document_text"],
    "carbon": ["reported_metrics", "document_text", "sector"],
}

_TOOL_INPUTS: dict[str, list[str]] = {
    "cbam": ["product_code", "country"],
    "cbam-export": ["product_code", "country"],
    "cbam-steel": ["product_code", "country"],
    "battery": ["product_code", "country"],
    "eudr": ["product_code", "country", "supplier_profile"],
    "espr": ["product_code", "country"],
    "conflict-minerals": ["supplier_profile", "country"],
    "smeta": ["supplier_profile", "country"],
    "sa8000": ["supplier_profile", "country"],
    "rba": ["supplier_profile", "country"],
    "amfori-bsci": ["supplier_profile", "country"],
}


def build_esg_workflow(
    *,
    company_name: str = "",
    company_description: str = "",
    sector: str = "",
    geography: str = "",
    jurisdiction: str = "",
    impact_themes: list[str] | None = None,
    reported_metrics: dict[str, object] | None = None,
    document_text: str = "",
    product_code: str = "",
    country: str = "",
    supplier_profile: str = "",
    query: str = "",
    limit: int = 8,
    include_low_score: bool = False,
) -> ToolboxWorkflowResult:
    """Build a compact ESG toolbox workflow from existing impact inputs."""
    context = _context_text(
        company_name=company_name,
        company_description=company_description,
        sector=sector,
        geography=geography,
        jurisdiction=jurisdiction,
        impact_themes=impact_themes or [],
        reported_metrics=reported_metrics or {},
        document_text=document_text,
        product_code=product_code,
        country=country,
        supplier_profile=supplier_profile,
        query=query,
    )
    suggestions = infer_toolbox_inputs(
        company_description=company_description,
        sector=sector,
        geography=geography,
        jurisdiction=jurisdiction,
        reported_metrics=reported_metrics or {},
        document_text=document_text,
        product_code=product_code,
        country=country,
        supplier_profile=supplier_profile,
    )
    suggestion_map = {item.field: item.value for item in suggestions if item.value}
    assessment_kwargs = {
        "company_description": " ".join(
            part
            for part in [
                company_description,
                sector or str(suggestion_map.get("sector", "")),
                jurisdiction or geography or str(suggestion_map.get("jurisdiction", "")),
            ]
            if part
        ),
        "document_text": document_text,
        "reported_metrics": reported_metrics or {},
        "product_code": product_code or str(suggestion_map.get("product_code", "")),
        "country": country or geography or jurisdiction or str(suggestion_map.get("country", "")),
        "supplier_profile": supplier_profile,
    }

    scored: list[tuple[int, ToolboxToolSpec, list[str], ToolboxAssessmentResult]] = []
    for tool in list_toolbox_tools():
        route_terms = _TOOL_ROUTE_TERMS.get(tool.tool_id, [])
        matched_terms = _matched_terms(context, [*route_terms, *tool.tags, *tool.aliases, *tool.source_tags])
        category_score = _category_score(tool.categories, context, reported_metrics or {})
        search_score = _search_boost(tool, context)
        metric_score = _metric_score(tool, reported_metrics or {})
        score = len(matched_terms) * 12 + category_score + search_score + metric_score
        if not score and not include_low_score:
            continue
        readiness = assess_tool_readiness(tool, **assessment_kwargs)
        scored.append((score, tool, matched_terms, readiness))

    scored.sort(key=lambda item: (-item[0], -item[3].score_pct, item[1].tool_id))
    recommended: list[ToolboxModuleRecommendation] = []
    for score, tool, matched_terms, readiness in scored[: max(1, limit)]:
        missing_inputs = _missing_inputs(
            tool,
            reported_metrics=reported_metrics or {},
            document_text=document_text,
            product_code=assessment_kwargs["product_code"],
            country=assessment_kwargs["country"],
            supplier_profile=supplier_profile,
        )
        crosswalk = crosswalk_reported_metrics(reported_metrics or {}, tool_id=tool.tool_id)
        recommended.append(
            ToolboxModuleRecommendation(
                tool_id=tool.tool_id,
                title=tool.title,
                categories=list(tool.categories),
                score=max(score, readiness.score_pct),
                readiness_score_pct=readiness.score_pct,
                reason=_recommendation_reason(tool, matched_terms, crosswalk),
                matched_terms=matched_terms[:8],
                missing_inputs=missing_inputs,
                evidence_gaps=readiness.evidence_gaps[:5],
                recommendations=readiness.recommendations[:5],
                crosswalk=crosswalk,
            )
        )

    metric_crosswalk = crosswalk_reported_metrics(reported_metrics or {})
    ui_cards = build_toolbox_ui_cards(recommended)
    next_questions = _next_questions(recommended)
    return ToolboxWorkflowResult(
        recommended_tools=recommended,
        input_suggestions=suggestions,
        metric_crosswalk=metric_crosswalk,
        ui={
            "summary": {
                "recommended_count": len(recommended),
                "categories": _category_counts(recommended),
                "highest_priority": recommended[0].tool_id if recommended else "",
            },
            "cards": [card.model_dump(mode="json") for card in ui_cards],
            "groups": _group_cards(ui_cards),
        },
        next_questions=next_questions,
    )


def infer_toolbox_inputs(
    *,
    company_description: str = "",
    sector: str = "",
    geography: str = "",
    jurisdiction: str = "",
    reported_metrics: dict[str, object] | None = None,
    document_text: str = "",
    product_code: str = "",
    country: str = "",
    supplier_profile: str = "",
) -> list[ToolboxInputSuggestion]:
    """Infer defaults and identify the smallest useful follow-up inputs."""
    metrics = {str(k).upper(): v for k, v in (reported_metrics or {}).items()}
    text_by_field = {
        "company_description": company_description,
        "sector": sector,
        "geography": geography,
        "jurisdiction": jurisdiction,
        "document_text": document_text,
        "product_code": product_code,
        "country": country,
        "supplier_profile": supplier_profile,
        "reported_metrics": " ".join(metrics),
    }
    haystack = " ".join(str(value) for value in text_by_field.values()).lower()
    suggestions: list[ToolboxInputSuggestion] = []

    if not sector:
        inferred = _infer_sector(haystack)
        if inferred:
            suggestions.append(
                ToolboxInputSuggestion(
                    field="sector",
                    value=inferred,
                    confidence="medium",
                    reason=f"Inferred from terms related to {inferred}.",
                )
            )

    if not country and (geography or jurisdiction):
        suggestions.append(
            ToolboxInputSuggestion(
                field="country",
                value=geography or jurisdiction,
                confidence="medium",
                reason="Reused geography/jurisdiction as country context for export and supplier modules.",
                source="geography",
            )
        )

    if not jurisdiction:
        inferred_jurisdiction = _infer_jurisdiction(haystack)
        if inferred_jurisdiction:
            suggestions.append(
                ToolboxInputSuggestion(
                    field="jurisdiction",
                    value=inferred_jurisdiction,
                    confidence="medium",
                    reason="Inferred likely reporting/export jurisdiction from company context.",
                )
            )

    if not product_code and any(term in haystack for term in ("export", "cbam", "battery", "steel", "cement", "aluminium", "aluminum", "customs")):
        suggestions.append(
            ToolboxInputSuggestion(
                field="product_code",
                value="",
                confidence="low",
                reason="Needed for export-compliance routing; ask for CN/HS/product code only if export modules are in scope.",
                source="missing_required_input",
            )
        )

    if not supplier_profile and any(term in haystack for term in ("supplier", "factory", "audit", "worker", "value chain", "procurement")):
        suggestions.append(
            ToolboxInputSuggestion(
                field="supplier_profile",
                value="",
                confidence="low",
                reason="Needed to assess supplier ESG, human-rights due diligence, and audit readiness.",
                source="missing_required_input",
            )
        )

    if metrics and not document_text:
        suggestions.append(
            ToolboxInputSuggestion(
                field="document_text",
                value="",
                confidence="low",
                reason="Reported metrics can support crosswalks, but document text is needed to verify policies, boundaries, and assurance evidence.",
                source="missing_evidence_context",
            )
        )

    if {"OI4112", "OI1479", "PD9427", "OI6697"} & set(metrics):
        suggestions.append(
            ToolboxInputSuggestion(
                field="tool_focus",
                value="carbon",
                confidence="high",
                reason="Reported metrics include carbon or energy IDs that can prefill carbon/disclosure readiness checks.",
                source="reported_metrics",
            )
        )

    return _dedupe_suggestions(suggestions)


def build_toolbox_ui_cards(recommendations: list[ToolboxModuleRecommendation]) -> list[ToolboxUICard]:
    """Convert recommendations into compact cards for the web console/reports."""
    cards: list[ToolboxUICard] = []
    for item in recommendations:
        score = item.readiness_score_pct
        status = "ready" if score >= 80 else "needs evidence" if score >= 45 else "early"
        priority = "high" if item.score >= 65 or item.missing_inputs else "medium" if item.score >= 30 else "low"
        category = item.categories[0] if item.categories else "disclosure"
        cards.append(
            ToolboxUICard(
                tool_id=item.tool_id,
                title=item.title,
                category=category,
                readiness_score_pct=score,
                priority=priority,
                status=status,
                summary=item.reason or "Relevant ESG module for this company context.",
                next_questions=_questions_for_recommendation(item)[:3],
            )
        )
    return cards


def _context_text(**values: Any) -> str:
    parts: list[str] = []
    for value in values.values():
        if isinstance(value, dict):
            parts.extend([str(k) for k in value])
            parts.extend([str(v) for v in value.values()])
        elif isinstance(value, list):
            parts.extend(str(v) for v in value)
        else:
            parts.append(str(value))
    return " ".join(parts).lower()


def _matched_terms(context: str, terms: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in terms:
        term = " ".join(str(raw).lower().replace("_", " ").replace("-", " ").split())
        if not term or term in seen:
            continue
        pattern = r"\b" + re.escape(term).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, context):
            seen.add(term)
            out.append(raw)
    return out


def _category_score(categories: list[str], context: str, metrics: dict[str, object]) -> int:
    score = 0
    if "carbon" in categories and (
        any(term in context for term in ("carbon", "emission", "scope 1", "scope 2", "scope 3", "net zero"))
        or {"OI4112", "OI1479", "PD9427", "OI6697"} & {str(k).upper() for k in metrics}
    ):
        score += 22
    if "export" in categories and any(term in context for term in ("export", "eu", "cbam", "battery", "customs", "deforestation")):
        score += 18
    if "supplier" in categories and any(term in context for term in ("supplier", "factory", "audit", "worker", "value chain", "procurement")):
        score += 18
    if "disclosure" in categories and any(term in context for term in ("report", "disclosure", "sustainability", "csrd", "issb", "esrs", "gri")):
        score += 14
    if "rating" in categories and any(term in context for term in ("rating", "scorecard", "ecovadis", "msci", "supplier score")):
        score += 12
    return score


def _search_boost(tool: ToolboxToolSpec, context: str) -> int:
    queries = [
        term
        for term in ("battery", "deforestation", "water stewardship", "responsible mining", "sustainable bond", "science based targets", "cbam")
        if term in context
    ]
    boost = 0
    for query in queries:
        matches = search_toolbox_tools(query)[:5]
        if any(match.tool_id == tool.tool_id for match in matches):
            boost += 8
    return boost


def _metric_score(tool: ToolboxToolSpec, metrics: dict[str, object]) -> int:
    if not metrics:
        return 0
    mappings = crosswalk_reported_metrics(metrics, tool_id=tool.tool_id)
    return min(24, len(mappings) * 12)


def _missing_inputs(
    tool: ToolboxToolSpec,
    *,
    reported_metrics: dict[str, object],
    document_text: str,
    product_code: object,
    country: object,
    supplier_profile: str,
) -> list[str]:
    present = {
        "reported_metrics": bool(reported_metrics),
        "document_text": bool(document_text),
        "product_code": bool(product_code),
        "country": bool(country),
        "supplier_profile": bool(supplier_profile),
        "sector": True,
    }
    required = list(_TOOL_INPUTS.get(tool.tool_id, []))
    for category in tool.categories:
        required.extend(_CATEGORY_INPUTS.get(category, []))
    return _dedupe([field for field in required if not present.get(field, False)])


def _recommendation_reason(
    tool: ToolboxToolSpec,
    matched_terms: list[str],
    crosswalk: dict[str, list[str]],
) -> str:
    if matched_terms:
        return f"Matched company context terms: {', '.join(matched_terms[:4])}."
    if crosswalk:
        return f"Reported metrics map to {tool.title} evidence uses."
    if tool.categories:
        labels = [TOOLBOX_CATEGORIES.get(category, category) for category in tool.categories[:2]]
        return f"Relevant to {', '.join(labels).lower()} workflow coverage."
    return "Relevant ESG toolbox module."


def _next_questions(recommendations: list[ToolboxModuleRecommendation]) -> list[str]:
    questions: list[str] = []
    for item in recommendations[:5]:
        questions.extend(_questions_for_recommendation(item))
    return _dedupe(questions)[:8]


def _questions_for_recommendation(item: ToolboxModuleRecommendation) -> list[str]:
    questions: list[str] = []
    for field in item.missing_inputs:
        if field == "reported_metrics":
            questions.append(f"Which reported IRIS+ or ESG metrics should be reused for {item.title}?")
        elif field == "document_text":
            questions.append(f"Which policy, report, or evidence text should be checked for {item.title}?")
        elif field == "product_code":
            questions.append(f"What product/CN/HS code should be used for {item.title}?")
        elif field == "country":
            questions.append(f"Which country or export market should be used for {item.title}?")
        elif field == "supplier_profile":
            questions.append(f"Which supplier, facility, or audit profile should be used for {item.title}?")
    if not questions and item.evidence_gaps:
        questions.append(item.evidence_gaps[0])
    return questions


def _group_cards(cards: list[ToolboxUICard]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for card in cards:
        grouped[card.category].append(card.model_dump(mode="json"))
    return dict(grouped)


def _category_counts(recommendations: list[ToolboxModuleRecommendation]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in recommendations:
        for category in item.categories:
            counts[category] = counts.get(category, 0) + 1
    return counts


def _infer_sector(haystack: str) -> str:
    sector_terms = {
        "energy": ("solar", "renewable", "electricity", "energy", "power"),
        "manufacturing": ("manufacturing", "factory", "production line", "industrial"),
        "agriculture": ("farm", "agriculture", "smallholder", "crop", "coffee", "cocoa", "soy"),
        "financial services": ("fintech", "microfinance", "loan", "insurance", "bank"),
        "healthcare": ("health", "clinic", "patient", "medical"),
        "education": ("school", "student", "education", "learning"),
        "mining": ("mine", "mining", "tailings", "smelter"),
        "battery": ("battery", "cell", "module", "ev"),
    }
    for sector, terms in sector_terms.items():
        if any(term in haystack for term in terms):
            return sector
    return ""


def _infer_jurisdiction(haystack: str) -> str:
    jurisdiction_terms = {
        "EU": ("eu", "european union", "csrd", "esrs", "cbam", "sfdr", "battery regulation", "eudr"),
        "US": ("united states", "sec", "california"),
        "UK": ("united kingdom", "uk", "fca"),
        "Singapore": ("singapore", "mas"),
        "Hong Kong": ("hong kong", "hkex"),
        "China": ("china", "mainland"),
    }
    for jurisdiction, terms in jurisdiction_terms.items():
        if any(term in haystack for term in terms):
            return jurisdiction
    return ""


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


def _dedupe_suggestions(values: list[ToolboxInputSuggestion]) -> list[ToolboxInputSuggestion]:
    out: list[ToolboxInputSuggestion] = []
    seen: set[str] = set()
    for item in values:
        if item.field in seen:
            continue
        seen.add(item.field)
        out.append(item)
    return out


__all__ = [
    "ToolboxInputSuggestion",
    "ToolboxModuleRecommendation",
    "ToolboxUICard",
    "ToolboxWorkflowResult",
    "build_esg_workflow",
    "build_toolbox_ui_cards",
    "infer_toolbox_inputs",
]
