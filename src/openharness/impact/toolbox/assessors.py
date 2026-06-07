"""Deterministic ESG toolbox checklist, readiness, and crosswalk helpers."""

from __future__ import annotations

from openharness.impact.toolbox.models import AssessmentQuestion, ToolboxAssessmentResult, ToolboxToolSpec
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
