"""Tool: Extract impact claims from PDF pitch decks, map to IRIS+/SDGs, and identify DD gaps."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pydantic import BaseModel, Field

from impact_vision.impact.database import ensure_catalog_loaded
from impact_vision.impact.dd_checklist import analyze_document_coverage, select_questions_for_document
from impact_vision.impact.greenwashing import assess_greenwashing
from impact_vision.impact.models import ImpactClaim
from impact_vision.impact.sdg_taxonomy import get_sdg_goal
from impact_vision.tools.base import BaseTool, ToolExecutionContext, ToolResult

logger = logging.getLogger(__name__)

IMPACT_KEYWORDS = [
    "impact", "sdg", "sustainable", "beneficiaries", "underserved", "marginalized",
    "poverty", "inclusion", "climate", "carbon", "emissions", "renewable", "clean energy",
    "gender", "women", "equality", "health", "education", "water", "sanitation",
    "food security", "nutrition", "jobs created", "employment", "livelihoods",
    "financial inclusion", "affordable", "access", "resilience", "biodiversity",
    "waste reduction", "circular economy", "social enterprise", "community",
    "smallholder", "rural", "low-income", "bottom of pyramid", "outcome",
    "theory of change", "impact measurement", "environmental",
]

SECTOR_THEME_MAP = {
    "health": ["Health", "Nutrition"],
    "education": ["Education", "Quality Education"],
    "finance": ["Financial Inclusion"],
    "microfinance": ["Financial Inclusion"],
    "energy": ["Clean Energy", "Energy Access", "Renewable Energy"],
    "solar": ["Clean Energy", "Energy Access"],
    "agriculture": ["Smallholder Agriculture", "Food Security"],
    "agricultural": ["Smallholder Agriculture", "Food Security"],
    "smallholder": ["Smallholder Agriculture"],
    "livestock": ["Smallholder Agriculture", "Food Security"],
    "biogas": ["Renewable Energy"],
    "water": ["Water", "Sustainable Water Management"],
    # "housing" alone matched pig pens ("slatted housing", "group-housing").
    "affordable housing": ["Affordable Housing"],
    "social housing": ["Affordable Housing"],
    "climate": ["Climate Mitigation", "Climate Adaptation"],
    "emissions": ["Climate Mitigation"],
}


class PitchDeckAnalyzeInput(BaseModel):
    file_path: str = Field(default="", description="Path to the PDF pitch deck or investment memo")
    text: str = Field(default="", description="Raw pitch deck or investment memo text")
    url: str = Field(default="", description="URL to a text-accessible pitch deck or memo")
    include_dd_checklist: bool = Field(
        default=True,
        description="Also run the DD checklist analysis to identify unanswered due diligence questions",
    )
    include_sdg_mapping: bool = Field(
        default=True,
        description="Map extracted claims to specific SDG goals and targets",
    )
    include_iris_suggestions: bool = Field(
        default=True,
        description="Suggest relevant IRIS+ metrics based on document content",
    )
    include_greenwashing_check: bool = Field(
        default=True,
        description="Run greenwashing / impact-washing risk detection on extracted claims",
    )
    extract_company: bool = Field(
        default=True,
        description="Auto-extract a Company model from the document for downstream tools (sdg_mapper, five_dimension_assess)",
    )
    save_company_yaml: str = Field(
        default="",
        description="If set, save the extracted Company model as YAML to this path for reuse",
    )
    max_dd_questions: int = Field(
        default=10, ge=1, le=30,
        description="Max DD questions to suggest",
    )


class PitchDeckAnalyzeTool(BaseTool):
    name = "pitch_deck_analyze"
    description = (
        "Extract text from a PDF pitch deck or investment memo and perform a comprehensive "
        "impact analysis:\n"
        "1. Identify and classify impact claims (outcome/output/activity/intent/risk)\n"
        "2. Map claims to relevant IRIS+ metrics from the catalog\n"
        "3. Detect SDG goal/target alignment from the content\n"
        "4. Run the DD checklist to identify which due diligence questions are addressed "
        "and which gaps remain\n"
        "5. Suggest the most important follow-up DD questions for the investment team\n\n"
        "This is the primary tool for initial intake of a new investment opportunity."
    )
    input_model = PitchDeckAnalyzeInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, PitchDeckAnalyzeInput) else PitchDeckAnalyzeInput.model_validate(arguments)
        return not args.save_company_yaml

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, PitchDeckAnalyzeInput) else PitchDeckAnalyzeInput.model_validate(arguments)

        if args.text.strip():
            text = args.text
            page_texts = [{"page": 1, "text": text}]
            source_name = "raw_text"
            source_stem = "raw_text"
        elif args.url.strip():
            try:
                text = _fetch_url_text(args.url)
            except _UrlFetchError as e:
                return ToolResult(output=f"Refused to fetch URL: {e}", is_error=True)
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Failed to fetch URL: {e}", is_error=True)
            page_texts = [{"page": 1, "text": text}]
            source_name = args.url
            source_stem = "url_document"
        elif args.file_path.strip():
            path = Path(args.file_path)
            if not path.is_absolute():
                path = context.cwd / path

            if not path.exists():
                return ToolResult(output=f"File not found: {path}", is_error=True)

            suffix = path.suffix.lower()
            try:
                if suffix == ".pdf":
                    text, page_texts = _extract_pdf_text(path)
                elif suffix in (".txt", ".md"):
                    raw = path.read_text(encoding="utf-8", errors="replace")
                    text, page_texts = raw, [{"page": 1, "text": raw}]
                else:
                    return ToolResult(output=f"Unsupported file type: {path.suffix}. Use PDF, TXT, or MD.", is_error=True)
                source_name = path.name
                source_stem = path.stem
            except Exception as e:
                return ToolResult(output=f"Failed to extract document text: {e}", is_error=True)
        else:
            return ToolResult(output="Provide file_path, text, or url.", is_error=True)

        if not text.strip():
            return ToolResult(output="No text could be extracted from the document", is_error=True)

        try:
            store = ensure_catalog_loaded()
        except FileNotFoundError as exc:
            return ToolResult(output=str(exc), is_error=True)
        claims = _extract_impact_claims(page_texts, store)
        detected_themes = _detect_themes(text)
        detected_sdgs = _detect_sdg_goals(text, claims)
        suggested_metrics = _suggest_iris_metrics(text, detected_themes, store) if args.include_iris_suggestions else []

        extracted_company = None
        if args.extract_company:
            extracted_company = _extract_company_model(
                text, source_stem, detected_themes, detected_sdgs,
                [m.id for m in suggested_metrics[:10]], store,
            )
            if args.save_company_yaml and extracted_company:
                _save_company_yaml(
                    extracted_company,
                    args.save_company_yaml,
                    context.cwd,
                    suggested_metric_ids=[m.id for m in suggested_metrics[:15]],
                )

        lines = [
            f"PITCH DECK / MEMO ANALYSIS: {source_name}",
            "=" * 70,
            f"Pages: {len(page_texts)} | Text: {len(text):,} chars",
            f"Impact claims found: {len(claims)}",
            f"Detected themes: {', '.join(detected_themes) if detected_themes else 'None'}",
            f"Detected SDGs: {', '.join(f'SDG {g}' for g in sorted(detected_sdgs)) if detected_sdgs else 'None'}",
            "",
        ]

        # Section 1: Impact Claims
        if claims:
            lines.append("IMPACT CLAIMS IDENTIFIED")
            lines.append("-" * 50)
            for i, claim in enumerate(claims, 1):
                lines.append(f"\n  {i}. [{claim.category.upper()}] (p.{claim.source_page or '?'}, confidence: {claim.confidence:.0%})")
                lines.append(f"     \"{claim.text[:200]}\"")
                if claim.mapped_metrics:
                    metric_names = []
                    for mid in claim.mapped_metrics[:3]:
                        m = store.get(mid)
                        metric_names.append(f"{mid} ({m.name})" if m else mid)
                    lines.append(f"     IRIS+ Metrics: {', '.join(metric_names)}")
                if claim.mapped_sdg_targets:
                    lines.append(f"     SDG Targets: {', '.join(claim.mapped_sdg_targets[:5])}")
            lines.append("")

        # Section 2: SDG Alignment
        if args.include_sdg_mapping and detected_sdgs:
            lines.append("SDG ALIGNMENT (from document content)")
            lines.append("-" * 50)
            for goal_num in sorted(detected_sdgs):
                goal = get_sdg_goal(goal_num)
                goal_name = goal.name if goal else f"Goal {goal_num}"
                goal_metrics = store.filter_by_sdg(goal_num)
                lines.append(f"  SDG {goal_num}: {goal_name}")
                lines.append(f"    Available IRIS+ metrics: {len(goal_metrics)}")
                relevant = [m for m in goal_metrics if any(t.lower() in m.name.lower() or t.lower() in m.definition.lower() for t in detected_themes)][:3]
                if relevant:
                    lines.append(f"    Suggested metrics: {', '.join(f'{m.id} ({m.name})' for m in relevant)}")
            lines.append("")

        # Section 3: Suggested IRIS+ Metrics
        if suggested_metrics:
            lines.append("SUGGESTED IRIS+ METRICS (based on document themes)")
            lines.append("-" * 50)
            for m in suggested_metrics[:15]:
                sdgs = ", ".join(f"SDG {g}" for g in m.sdg_goals[:3]) if m.sdg_goals else ""
                lines.append(f"  {m.id}: {m.name}")
                lines.append(f"    {m.primary_impact_category} | {sdgs}")
            lines.append("")

        # Section 4: DD Checklist
        if args.include_dd_checklist:
            dd_result = analyze_document_coverage(text, sector=_detect_sector(text) or "auto")
            lines.append("DUE DILIGENCE CHECKLIST COVERAGE")
            lines.append("-" * 50)
            lines.append(f"  Questions addressed: {len(dd_result.addressed)}/{dd_result.total_questions} ({dd_result.coverage_pct}%)")
            lines.append(f"  High-priority gaps: {len(dd_result.high_priority_gaps)}")
            lines.append("")

            if dd_result.high_priority_gaps:
                lines.append("  HIGH-PRIORITY DD GAPS (not addressed in document):")
                for q in dd_result.high_priority_gaps:
                    dim_tag = f" [{q.dimension}]" if q.dimension else ""
                    lines.append(f"    {q.id}: {q.question}{dim_tag}")
                lines.append("")

            suggested_qs = select_questions_for_document(text, max_questions=args.max_dd_questions)
            if suggested_qs:
                lines.append(f"  RECOMMENDED FOLLOW-UP QUESTIONS ({len(suggested_qs)}):")
                lines.append("  (Ask these to the investment team to complete the DD):")
                for i, q in enumerate(suggested_qs, 1):
                    priority_marker = {"high": "!!!", "medium": "..", "low": "."}.get(q.priority, "")
                    lines.append(f"    {i}. {priority_marker} {q.question}")
                    if q.follow_up:
                        lines.append(f"       Follow-up: {q.follow_up}")

        gw_signals = _detect_greenwashing_signals(claims, text) if args.include_greenwashing_check else []
        if gw_signals:
            lines.append("")
            lines.append("GREENWASHING SIGNAL ANALYSIS")
            lines.append("-" * 50)
            for signal in gw_signals:
                lines.append(f"  ⚠ {signal}")
            lines.append("")

        # Section 5: Greenwashing Risk
        gw_result = None
        if args.include_greenwashing_check and extracted_company:
            gw_result = assess_greenwashing(extracted_company)
            lines.append("")
            lines.append("GREENWASHING / IMPACT-WASHING RISK")
            lines.append("-" * 50)
            lines.append(f"  Overall Risk Score: {gw_result.overall_score}/100 — {gw_result.classification}")
            lines.append("  Sub-scores:")
            for sub_name, sub_val in [
                ("Claim-Metric Gap", gw_result.claim_metric_gap),
                ("Adverse Omission", gw_result.adverse_omission),
                ("Specificity", gw_result.specificity),
                ("Selectivity", gw_result.selectivity),
                ("Verification", gw_result.verification),
            ]:
                lines.append(f"    {sub_name}: {sub_val}/100")
            if gw_result.flags:
                lines.append(f"  Flags ({len(gw_result.flags)}):")
                for flag in gw_result.flags[:5]:
                    lines.append(f"    - {flag}")
            if gw_result.recommendations:
                lines.append("  Recommendations:")
                for rec in gw_result.recommendations[:3]:
                    lines.append(f"    - {rec}")
            lines.append("")

        # Section 6: Extracted Company Model
        if extracted_company:
            lines.append("")
            lines.append("EXTRACTED COMPANY MODEL (for downstream tools)")
            lines.append("-" * 50)
            lines.append(f"  Name: {extracted_company.name}")
            lines.append(f"  Sector: {extracted_company.sector or 'Unknown'}")
            lines.append(f"  Geography: {extracted_company.geography or 'Not detected'}")
            lines.append(f"  Themes: {', '.join(extracted_company.impact_themes) or 'None'}")
            lines.append(f"  SDG Claims: {', '.join(f'SDG {g}' for g in extracted_company.sdg_claims) or 'None'}")
            lines.append(f"  Reported Metrics: {len(extracted_company.reported_metrics)}")
            lines.append(f"  Suggested Metrics: {len(suggested_metrics[:15])}")
            if suggested_metrics:
                lines.append("  Note: suggested metrics are recommendations, not reported evidence.")
            if args.save_company_yaml:
                lines.append(f"  Saved to: {args.save_company_yaml}")
            lines.append("")
            lines.append("  You can now use this data directly with sdg_mapper, five_dimension_assess,")
            lines.append("  or impact_report tools by passing these values.")

        # Section 7: ESG compliance routing (same toolbox workflow as gap_analysis/impact_report)
        esg_workflow = None
        if extracted_company:
            from impact_vision.impact.toolbox import build_esg_workflow

            esg_workflow = build_esg_workflow(
                company_name=extracted_company.name,
                company_description=extracted_company.description,
                sector=extracted_company.sector,
                geography=extracted_company.geography,
                jurisdiction=extracted_company.geography,
                impact_themes=extracted_company.impact_themes,
                reported_metrics=dict(extracted_company.reported_metrics),
                document_text=text[:8000],
                country=extracted_company.geography,
                limit=5,
            )
            if esg_workflow.recommended_tools:
                lines.append("")
                lines.append("ESG COMPLIANCE ROUTING (ESG toolbox)")
                lines.append("-" * 50)
                for rec in esg_workflow.recommended_tools:
                    lines.append(f"  {rec.title} — readiness {rec.readiness_score_pct}%")
                    if rec.reason:
                        lines.append(f"    {rec.reason}")
                    if rec.missing_inputs:
                        lines.append(f"    Missing inputs: {', '.join(rec.missing_inputs[:4])}")
                if esg_workflow.next_questions:
                    lines.append("  Next questions:")
                    for question in esg_workflow.next_questions[:4]:
                        lines.append(f"    - {question}")

        metadata = {
            "claims": [c.model_dump() for c in claims],
            "detected_themes": detected_themes,
            "detected_sdgs": sorted(detected_sdgs),
            "suggested_metrics": [m.id for m in suggested_metrics[:15]],
            "suggested_metric_details": [
                {
                    "metric_id": m.id,
                    "name": m.name,
                    "primary_impact_category": m.primary_impact_category,
                    "sdg_goals": m.sdg_goals,
                }
                for m in suggested_metrics[:15]
            ],
            "evidence_note": (
                "suggested_metrics are recommendations only and are not included in "
                "extracted_company.reported_metrics unless a reported value/source is present"
            ),
            "text_length": len(text),
            "pages": len(page_texts),
        }
        if extracted_company:
            metadata["extracted_company"] = extracted_company.model_dump()
        if gw_result:
            metadata["greenwashing"] = gw_result.model_dump()
        if esg_workflow is not None:
            metadata["esg_toolbox"] = esg_workflow.model_dump(mode="json")

        return ToolResult(output="\n".join(lines), metadata=metadata)


_LANG_MARKERS = {
    "es": ["empresa", "impacto", "inversión", "comunidad", "sostenible", "objetivo", "beneficiarios"],
    "fr": ["entreprise", "investissement", "communauté", "durable", "objectif", "bénéficiaires"],
    "pt": ["empresa", "investimento", "comunidade", "sustentável", "objetivo", "beneficiários"],
    "zh": ["企业", "投资", "影响", "可持续", "社区", "目标"],
}


def _detect_language(text: str) -> str:
    """Detect document language from text content. Returns ISO 639-1 code.

    Falls back to ``en`` when no language scores ``>= 3`` matches; this avoids
    an insertion-order bias where ``max()`` would return whichever language
    happens to be defined first when every score is zero.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for lang, markers in _LANG_MARKERS.items():
        scores[lang] = sum(1 for m in markers if m in text_lower)
    if not scores or max(scores.values()) < 3:
        return "en"
    return max(scores, key=scores.get)


def _extract_pdf_text(path: Path) -> tuple[str, list[dict]]:
    try:
        import pymupdf
    except ImportError:
        raise ImportError("pymupdf is required for PDF extraction. Install with: pip install pymupdf")

    doc = pymupdf.open(str(path))
    page_texts: list[dict] = []
    all_text: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        page_texts.append({"page": page_num + 1, "text": text})
        all_text.append(text)

    doc.close()
    full_text = "\n".join(all_text)

    detected_lang = _detect_language(full_text)
    if detected_lang != "en":
        page_texts.insert(0, {"page": 0, "text": f"[Detected language: {detected_lang}]", "language": detected_lang})

    return full_text, page_texts


def _extract_impact_claims(page_texts: list[dict], store) -> list[ImpactClaim]:
    claims: list[ImpactClaim] = []

    for page_info in page_texts:
        page_num = page_info["page"]
        text = page_info["text"]
        if not text.strip():
            continue

        sentences = _split_sentences(text)
        for sentence in sentences:
            lower = sentence.lower()
            keyword_hits = sum(1 for kw in IMPACT_KEYWORDS if kw in lower)
            if keyword_hits < 1:
                continue

            negated_hits = sum(
                1 for kw in IMPACT_KEYWORDS
                if kw in lower and _is_negated_in_sentence(lower, kw)
            )
            effective_hits = keyword_hits - negated_hits
            if effective_hits < 1:
                continue

            category = _classify_claim(lower)
            mapped_metrics = _match_metrics(sentence, store)
            mapped_targets = _match_sdg_targets(sentence)

            claim = ImpactClaim(
                text=sentence.strip(),
                source_page=page_num,
                mapped_metrics=[m.id for m in mapped_metrics[:5]],
                mapped_sdg_targets=mapped_targets[:5],
                category=category,
            )
            claim.recalibrate_confidence()
            claims.append(claim)

    claims.sort(key=lambda c: c.confidence, reverse=True)
    return claims[:30]


def _has_term(text_lower: str, term: str) -> bool:
    """Whole-word match that also refuses hyphen compounds.

    "housing" must not fire on "group-housing", nor "school" on
    "pre-school-age" style compounds — those produced Affordable Housing /
    SDG 11 themes for a pig farm.
    """
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", text_lower) is not None


def _has_inflected(text_lower: str, term: str) -> bool:
    """Like :func:`_has_term` but accepts simple inflections of the term.

    "emission" matches "emissions", "job" matches "jobs" and the stem "recycl"
    matches "recycling" / "recycled". Hyphen compounds are still refused.
    """
    suffix = r"(?:s|es|e|ed|ing|er|ers|able)?"  # inflections only, never compounds
    return re.search(rf"(?<![\w-]){re.escape(term)}{suffix}(?![\w-])", text_lower) is not None


_FOOTPRINT_SENTENCE = re.compile(
    r"\b(scope\s*[123]|our (?:own )?(?:carbon |ghg |operational )?(?:footprint|emissions)|"
    r"operational (?:footprint|emissions))\b",
    re.IGNORECASE,
)
_MITIGATION_WORDS = re.compile(
    r"\b(avoid\w*|reduc\w*|displac\w*|abat\w*|replac\w*|renewable|clean energy|decarboni[sz]\w*|"
    r"solar|biogas|sequest\w*|net[- ]zero)\b",
    re.IGNORECASE,
)


def _without_footprint_disclosures(text: str) -> str:
    """Drop sentences that only disclose the company's own footprint.

    "Our own footprint is 120 tCO2e … Scope 1 emissions" is ESG disclosure,
    not a climate-mitigation business: it must not add the Climate Mitigation
    theme or SDG 13 hints to a fintech. Sentences that also describe
    mitigation ("avoided 920 t CO2e", "replacing diesel") are kept.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(
        s for s in sentences
        if not (_FOOTPRINT_SENTENCE.search(s) and not _MITIGATION_WORDS.search(s))
    )


def _detect_themes(text: str) -> list[str]:
    """Detect impact themes from document text (own-footprint disclosures ignored)."""
    text_lower = _without_footprint_disclosures(text).lower()
    themes: list[str] = []
    for keyword, theme_list in SECTOR_THEME_MAP.items():
        if _has_term(text_lower, keyword):
            for t in theme_list:
                if t not in themes:
                    themes.append(t)
    return themes


_SDG_LIST_RE = re.compile(
    r"\bSDGs?\s*#?\s*(\d{1,2}(?:\s*(?:[/,&+]|and|\.)\s*\d{1,2})*)", re.IGNORECASE
)


def _explicit_sdg_refs(text: str) -> set[int]:
    """Goals explicitly referenced, including lists like "SDG 2/6/7" or "SDGs 1, 5 and 8"."""
    goals: set[int] = set()
    for match in _SDG_LIST_RE.finditer(text):
        for num in re.findall(r"\d{1,2}", match.group(1)):
            if 1 <= int(num) <= 17:
                goals.add(int(num))
    return goals


def _detect_sdg_goals(text: str, claims: list[ImpactClaim]) -> set[int]:
    """Detect SDG goals from explicit references and claim mappings."""
    goals: set[int] = set()

    explicit = _explicit_sdg_refs(text)
    if explicit:
        # The document states its SDGs ("SDG 2/6/7/8/12/13"): those are the
        # claims. Keyword hints would only add goals the company never claimed.
        return explicit

    theme_sdg_hints = {
        "poverty": [1], "low-income": [1], "livelihood": [1],
        "hunger": [2], "food": [2], "nutrition": [2], "smallholder": [2], "farmer": [2],
        "health": [3], "medical": [3], "healthcare": [3], "patient": [3], "clinic": [3],
        "education": [4], "learning": [4], "school": [4],
        "gender": [5], "women": [5], "girl": [5],
        "water": [6], "sanitation": [6],
        "energy": [7], "solar": [7], "renewable": [7],
        "employment": [8], "job": [8], "decent work": [8],
        "infrastructure": [9], "innovation": [9],
        "inequality": [10], "inclusion": [10],
        "urban": [11], "city": [11], "housing": [11],
        "waste": [12], "circular": [12], "recycl": [12],
        "climate": [13], "carbon": [13], "emission": [13], "net zero": [13], "net-zero": [13],
        "ghg": [13], "co2": [13], "co2e": [13],
        "ocean": [14], "marine": [14],
        "forest": [15], "biodiversity": [15], "land": [15],
    }
    text_lower = _without_footprint_disclosures(text).lower()
    for keyword, sdg_list in theme_sdg_hints.items():
        if _has_inflected(text_lower, keyword):
            goals.update(sdg_list)

    for claim in claims:
        for target in claim.mapped_sdg_targets:
            try:
                goals.add(int(target.split(".")[0]))
            except ValueError:
                pass

    return goals


def _suggest_iris_metrics(text: str, themes: list[str], store) -> list:
    """Suggest IRIS+ metrics based on detected themes."""
    all_suggested = []
    seen_ids: set[str] = set()

    for theme in themes:
        results = store.filter_by_theme(theme)
        for m in results[:10]:
            if m.id not in seen_ids:
                seen_ids.add(m.id)
                all_suggested.append(m)

    search_terms = ["beneficiar", "client", "revenue", "employee", "outcome"]
    for term in search_terms:
        if term in text.lower():
            for m in store.search(term, limit=5):
                if m.id not in seen_ids:
                    seen_ids.add(m.id)
                    all_suggested.append(m)

    return all_suggested[:20]


def _split_sentences(text: str) -> list[str]:
    import re
    sentences = re.split(r'(?<=[.!?])\s+|\n\n+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def _classify_claim(text_lower: str) -> str:
    if any(w in text_lower for w in ["result", "outcome", "achieved", "improved", "reduced", "increased"]):
        return "outcome"
    if any(w in text_lower for w in ["delivered", "served", "produced", "built", "trained"]):
        return "output"
    if any(w in text_lower for w in ["plan", "intend", "will", "aim", "target", "goal"]):
        return "intent"
    if any(w in text_lower for w in ["risk", "challenge", "barrier", "threat"]):
        return "risk"
    return "activity"


def _match_metrics(sentence: str, store) -> list:
    """Attach IRIS+ IDs only when they actually appear in the claim sentence."""
    import re

    matched: list = []
    seen: set[str] = set()
    for metric_id in re.findall(r"\b((?:PI|OI|OD|FP|PD)\d{4})\b", sentence, re.IGNORECASE):
        metric = store.get(metric_id.upper())
        if metric is not None and metric.id not in seen:
            seen.add(metric.id)
            matched.append(metric)
    return matched[:5]


def _match_sdg_targets(sentence: str) -> list[str]:
    import re
    targets: list[str] = []
    sdg_refs = re.findall(r'SDG\s*(\d{1,2})', sentence, re.IGNORECASE)
    for ref in sdg_refs:
        num = int(ref)
        if 1 <= num <= 17:
            targets.append(f"{num}.0")
    return targets


def _extract_reported_metrics(text: str) -> dict[str, str]:
    """Pull IRIS+ IDs that appear next to an actual reported value.

    Suggestions without a value must never land in ``reported_metrics`` —
    that path previously inflated 5D / SDG / greenwashing scores.
    """
    import re

    if not text:
        return {}
    pattern = re.compile(
        r"\b((?:PI|OI|OD|FP|PD)\d{4})\b\s*[)\]]?\s*"
        r"(?:[:\-=]|is|was|of|at|equals)\s*"
        r"([+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%|tCO2e|tCO₂e|tCO2|MW|kWh|MWh|ha|USD|US\$|\$|people|clients|customers|households|employees))?)",
        re.IGNORECASE,
    )
    reported: dict[str, str] = {}
    for match in pattern.finditer(text):
        metric_id = match.group(1).upper()
        raw_value = (match.group(2) or "").strip()
        if not raw_value:
            continue
        number = re.sub(r"[^\d.\-]", "", raw_value.split()[0])
        try:
            numeric = float(number)
        except ValueError:
            continue
        # Bare years next to an ID are almost always a reporting period, not a value.
        if 1990 <= numeric <= 2040 and not re.search(r"[%a-z$]", raw_value, re.IGNORECASE):
            continue
        reported[metric_id] = raw_value
    return reported


def _extract_company_model(
    text: str,
    filename: str,
    themes: list[str],
    sdgs: set[int],
    suggested_metric_ids: list[str],
    store,
):
    """Extract a Company model from document text for downstream tools."""
    import re
    from impact_vision.impact.models import Company

    del suggested_metric_ids, store

    company_name = filename.replace("_", " ").replace("-", " ").title()
    name_patterns = [
        r'(?:Company|Firm|Organization|Fund|Venture|Startup)\s*(?:Name|:)\s*[:\-]?\s*([A-Z][A-Za-z\s&\.]{2,30})',
        r'^([A-Z][A-Za-z\s&\.]{2,25})(?:\s*[-–—|]\s*(?:Pitch|Investor|Impact))',
        # Legal-entity suffix anywhere near the top: "Kampung Makmur Sdn Bhd".
        r"\b((?:[A-Z][\w&'.-]*[ \t]+){0,5}(?:Sdn\.?[ \t]*Bhd|Pte\.?[ \t]*Ltd|Ltd|Limited|Inc|LLC|PLC|GmbH|S\.A\.|Co\.,?[ \t]*Ltd)\.?)",
        # Title line: "BrightPath Finance — Growth Round Investor Memo".
        r"^[ \t#]*([A-Z][\w&'.-]*(?:[ \t]+[A-Z][\w&'.-]*){0,4})[ \t]+[\u2014\u2013|-][ \t]+[^\n]*\b"
        r"(?i:pitch|investor|memo|deck|overview|round|raise|seed|series|teaser|one-pager|executive summary)\b",
        # Chinese title line: "# 頤康長者護理 — A輪融資簡報".
        r"^[ \t#]*([\u4e00-\u9fff][\u4e00-\u9fff\w]{1,15})[ \t]*[\u2014\u2013|-]",
        # Opening sentence: "Kampung Makmur is a 3,000-sow integrated pig farm".
        r"^[ \t]*((?:[A-Z][\w&'.-]*)(?:[ \t]+[A-Z][\w&'.-]*){0,5})[ \t]+(?:is|are)[ \t]+(?:a|an|the)\b",
    ]
    for pat in name_patterns:
        match = re.search(pat, text[:2000], re.MULTILINE)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) > 3 and not candidate.lower().startswith(("the ", "our ", "this ")):
                company_name = candidate
                break

    sector = _detect_sector(text)
    geography = _detect_geography(text)
    reported = _extract_reported_metrics(text)
    # Quantified claims without an explicit IRIS+ ID (W0.10). Explicit IDs win.
    from impact_vision.impact.claim_metric_mapper import map_claim_metrics
    from impact_vision.impact.extractors.regex_extractor import RegexExtractor

    for claim in RegexExtractor().extract(text):
        for mapping in map_claim_metrics(claim.text, forward_looking=claim.category == "commitment"):
            reported.setdefault(mapping.metric_id, mapping.display)

    return Company(
        name=company_name,
        description=text[:500].strip(),
        sector=sector,
        geography=geography,
        impact_themes=themes,
        reported_metrics=reported,
        sdg_claims=sorted(sdgs),
    )


_SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Financial Services": ("金融", "貸款", "贷款", "小額", "小额", "fintech", "microfinance", "banking", "lending", "loan", "loans",
                           "borrower", "borrowers", "insurance", "payment", "payments", "credit"),
    "Healthcare": ("醫療", "医疗", "診所", "诊所", "醫院", "医院", "病人", "安老", "養老", "养老", "護理", "护理", "長者", "长者", "health", "healthcare", "medical", "pharmaceutical", "clinic", "clinics",
                   "hospital", "telemedicine", "patient", "patients"),
    "Education": ("教育", "學生", "学生", "學校", "学校", "教師", "教师", "education", "edtech", "school", "schools", "university", "learning",
                  "student", "students", "teacher", "teachers", "curriculum"),
    "Agriculture": ("農業", "农业", "農民", "农民", "農場", "农场", "agriculture", "agricultural", "agritech", "farming", "farm", "farms",
                    "farmer", "farmers", "smallholder", "smallholders", "crop", "crops",
                    "livestock", "pig", "pigs", "swine", "piggery", "piggeries", "hog", "hogs",
                    "sow", "sows", "poultry", "cattle", "dairy", "outgrower", "harvest",
                    "veterinary", "feed"),
    "Energy": ("太陽能", "太阳能", "能源", "電力", "电力", "energy", "solar", "wind", "renewable", "electricity", "cleantech", "mini-grid",
               "off-grid", "grid", "heat pump", "heat pumps", "gas boiler", "gas boilers", "heating",
               "retrofit", "retrofits", "energy efficiency", "insulation", "battery", "batteries"),
    # "app" / "platform" alone don't make a tech company: most decks have an app.
    "Technology": ("software", "saas", "technology company", "tech company", "cybersecurity",
                   "data platform", "ai platform", "developer"),
    "Waste Management": ("回收", "循環", "循环", "廢物", "废物", "堆填", "recycling", "recycled", "recycle", "circular", "circularity", "waste",
                         "landfill", "upcycling", "upcycled", "take-back", "resale",
                         "second-hand", "secondhand", "reuse", "reused", "textile", "textiles",
                         "e-waste", "compost", "composting"),
    "Retail": ("retail", "retailer", "retailers", "fashion", "apparel", "garment", "garments",
               "clothing", "e-commerce", "consumer brand"),
    "Manufacturing": ("manufacturing", "manufacturer", "factory", "factories", "production line"),
    "Tourism": ("tourism", "tourist", "tourists", "hotel", "hotels", "hospitality", "ecotourism"),
    "Real Estate": ("real estate", "property", "properties", "affordable housing", "construction",
                    "housing units", "housing", "homes", "rental", "tenant", "tenants", "landlord",
                    "landlords", "房屋", "住房"),
    "Water & Sanitation": ("sanitation", "drinking water", "water treatment", "wash",
                           "wastewater", "water utility"),
    "Transportation": ("transport", "mobility", "logistics", "fleet"),
    "Food & Beverage": ("food", "nutrition", "beverage", "restaurant", "meal"),
}


def _detect_sector(text: str) -> str:
    """Detect company sector from document text.

    Scores whole-word occurrences per sector (the opening 400 characters, which
    usually say what the company *is*, count double). Previously each keyword
    counted once as a substring, so one mention of "school attendance" made a
    pig farm an education company.
    """
    text_lower = text.lower()
    opening = text_lower[:400]
    best_sector = ""
    best_score = 0
    for sector, keywords in _SECTOR_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if not kw.isascii():  # CJK: no word boundaries
                score += text_lower.count(kw) + opening.count(kw)
                continue
            pattern = rf"(?<![\w-]){re.escape(kw)}(?![\w-])"
            score += len(re.findall(pattern, text_lower)) + len(re.findall(pattern, opening))
        if score > best_score:
            best_score = score
            best_sector = sector
    return best_sector


_NEGATION_PHRASES = ("not ", "no ", "don't ", "doesn't ", "do not ", "does not ", "without ", "lack ", "unable to ")


def _is_negated_in_sentence(text: str, keyword: str) -> bool:
    """Check if keyword appears near a negation phrase within 30 chars."""
    idx = text.find(keyword)
    while idx >= 0:
        window = text[max(0, idx - 30):idx]
        if any(neg in window for neg in _NEGATION_PHRASES):
            return True
        idx = text.find(keyword, idx + len(keyword))
    return False


def _detect_greenwashing_signals(claims: list, text: str) -> list[str]:
    """Detect specific greenwashing signal phrases from extracted claims."""
    signals: list[str] = []
    vague_claims = [c for c in claims if c.category in ("intent", "activity")]
    outcome_claims = [c for c in claims if c.category in ("outcome", "output")]

    if len(vague_claims) > len(outcome_claims) * 2 and len(vague_claims) > 3:
        signals.append(
            f"Aspirational bias: {len(vague_claims)} intent/activity claims vs {len(outcome_claims)} outcome/output claims"
        )

    unsubstantiated = [c for c in claims if not c.mapped_metrics and c.confidence < 0.5]
    if len(unsubstantiated) > len(claims) * 0.5 and len(unsubstantiated) > 2:
        signals.append(
            f"Low substantiation: {len(unsubstantiated)}/{len(claims)} claims lack metric mappings"
        )

    import re
    text_lower = text[:5000].lower()
    vague_phrases = [
        "committed to", "dedicated to", "striving for", "aim to", "aspire to",
        "plan to", "working toward", "believe in", "hope to",
    ]
    buzzwords = [
        "sustainable", "green", "eco-friendly", "purpose-driven", "impact-driven",
        "carbon-neutral", "net-zero", "climate-positive",
    ]
    vague_found = [p for p in vague_phrases if p in text_lower]
    if len(vague_found) >= 3:
        signals.append(
            f"Vague language: found {len(vague_found)} aspiration phrases ({', '.join(vague_found[:4])})"
        )
    buzz_found = [b for b in buzzwords if b in text_lower]
    if len(buzz_found) >= 4:
        signals.append(
            f"Buzzword density: {len(buzz_found)} buzzwords without substantiation ({', '.join(buzz_found[:4])})"
        )

    has_numeric = bool(re.search(r"\b\d+[%,.\d]*\s*(?:beneficiar|people|household|farmer|patient|student)", text_lower))
    if not has_numeric and claims:
        signals.append("No quantified beneficiary numbers found in the document")

    return signals


def _detect_geography(text: str) -> str:
    """Detect primary geography from document text using region and country mentions."""
    import re
    text_lower = text[:5000].lower()
    geo_patterns: dict[str, list[str]] = {
        "Hong Kong": ["hong kong", "kowloon", "kwai chung", "sha tin", "tsuen wan", "new territories",
                      "hksar", "香港", "九龍", "新界"],
        "Singapore": ["singapore", "新加坡"],
        "Philippines": ["philippines", "manila", "菲律賓", "菲律宾"],
        "Thailand": ["thailand", "bangkok", "泰國", "泰国"],
        "Bangladesh": ["bangladesh", "dhaka"],
        "Pakistan": ["pakistan", "karachi", "lahore"],
        "Japan": ["japan", "tokyo", "osaka", "日本"],
        "United Kingdom": ["united kingdom", "england", "scotland", "wales", "london", "manchester"],
        "Uganda": ["uganda", "kampala"],
        "Tanzania": ["tanzania", "dar es salaam"],
        "Rwanda": ["rwanda", "kigali"],
        "Ghana": ["ghana", "accra"],
        "Ethiopia": ["ethiopia", "addis ababa"],
        "Egypt": ["egypt", "cairo"],
        "Peru": ["peru", "lima"],
        "Chile": ["chile", "santiago"],
        "Argentina": ["argentina", "buenos aires"],
        "Sub-Saharan Africa": ["sub-saharan", "east africa", "west africa", "central africa", "southern africa"],
        "Kenya": ["kenya", "nairobi"],
        "Nigeria": ["nigeria", "lagos", "abuja"],
        "South Africa": ["south africa", "johannesburg", "cape town"],
        "India": ["india", "mumbai", "delhi", "bangalore", "hyderabad"],
        "China": ["mainland china", "china", "beijing", "shanghai", "shenzhen", "guangzhou", "中國", "中国",
                  "北京", "上海", "深圳", "广州", "廣州"],
        "Indonesia": ["indonesia", "jakarta", "印尼", "印度尼西亞"],
        "Malaysia": ["malaysia", "kuala lumpur", "johor", "馬來西亞", "马来西亚"],
        "Vietnam": ["vietnam", "ho chi minh"],
        "Brazil": ["brazil", "são paulo", "sao paulo"],
        "Colombia": ["colombia", "bogotá", "bogota"],
        "Mexico": ["mexico", "mexico city"],
        "Southeast Asia": ["southeast asia", "asean", "mekong"],
        "South Asia": ["south asia", "subcontinent"],
        "Latin America": ["latin america", "latam", "central america"],
        "Middle East": ["middle east", "mena", "gulf states"],
        "Netherlands": ["netherlands", "the dutch", "amsterdam", "rotterdam"],
        "Germany": ["germany", "berlin", "munich"],
        "France": ["france", "paris", "lyon"],
        "Spain": ["spain", "madrid", "barcelona"],
        "Italy": ["italy", "milan", "rome"],
        "Belgium": ["belgium", "brussels"],
        "Ireland": ["ireland", "dublin"],
        "Nordics": ["sweden", "denmark", "finland", "norway", "stockholm", "copenhagen"],
        "Europe": ["europe", "european union"],
        "North America": ["united states", "usa", "canada"],
        "Pacific": ["pacific island", "oceania"],
    }
    best_geo = ""
    best_count = 0
    def _mentioned(kw: str) -> bool:
        # Whole words for Latin names ("lima" must not match "climate");
        # CJK names have no word boundaries, so they match as substrings.
        if kw.isascii():
            return re.search(r"(?<![\w-])" + re.escape(kw) + r"(?![\w-])", text_lower) is not None
        return kw in text_lower

    for region, keywords in geo_patterns.items():
        count = sum(1 for kw in keywords if _mentioned(kw))
        if count > best_count:
            best_count = count
            best_geo = region
    country_pattern = re.search(
        r'(?:headquartered|based|located|operating|operations)\s+in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        text[:3000],
    )
    if country_pattern and not best_geo:
        best_geo = country_pattern.group(1).strip()
    return best_geo


class _UrlFetchError(Exception):
    """Raised when ``_fetch_url_text`` refuses to fetch a URL."""


_URL_MAX_BYTES = 50 * 1024 * 1024  # 50 MB cap on remote document size


def _ensure_public_url(url: str) -> None:
    """Reject non-http(s) URLs and hosts that resolve to non-public addresses."""
    from impact_vision.utils.safe_fetch import UnsafeUrlError, ensure_public_url

    try:
        ensure_public_url(url)
    except UnsafeUrlError as exc:
        raise _UrlFetchError(str(exc)) from exc


def _fetch_url_text(url: str) -> str:
    """Fetch a URL and return decoded text with SSRF / size guardrails.

    The original implementation passed any URL straight to ``urlopen`` with no
    scheme allow-list, no host filtering and no size cap, which made the tool a
    classic SSRF vector when mounted via MCP/HTTP. This wrapper enforces:

    * scheme must be ``http`` or ``https``;
    * host must not resolve to a private/loopback/link-local address, and
      neither may any redirect target;
    * response is capped at ``_URL_MAX_BYTES``;
    * binary content (e.g. ``application/pdf``) is rejected with a clear
      message that asks the caller to download the file locally and use
      ``file_path`` instead.
    """
    from impact_vision.utils.safe_fetch import UnsafeUrlError, open_public

    try:
        response_cm = open_public(url, timeout=10)
    except UnsafeUrlError as exc:
        raise _UrlFetchError(str(exc)) from exc
    with response_cm as response:
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "pdf" in content_type or content_type.startswith(("application/octet-stream", "image/", "video/", "audio/")):
            raise _UrlFetchError(
                f"Remote content type '{content_type}' is not text. Download "
                "the file locally and pass it via 'file_path' instead."
            )
        raw = response.read(_URL_MAX_BYTES + 1)
    if len(raw) > _URL_MAX_BYTES:
        raise _UrlFetchError(
            f"Remote document exceeds {_URL_MAX_BYTES // (1024 * 1024)} MB cap."
        )
    return raw.decode("utf-8", errors="replace")


def _save_company_yaml(
    company,
    yaml_path: str,
    cwd,
    *,
    suggested_metric_ids: list[str] | None = None,
) -> None:
    """Save a Company model as YAML for reuse."""
    import yaml
    from pathlib import Path

    raw_path = Path(yaml_path).expanduser()
    is_absolute = raw_path.is_absolute()
    candidate = raw_path if is_absolute else (cwd / raw_path)
    resolved = candidate.resolve()

    # Confine relative paths under ``cwd`` so a malicious payload like
    # ``save_company_yaml="../../etc/passwd"`` cannot escape the project root
    # when the tool is mounted in a multi-tenant MCP/HTTP runtime. Absolute
    # paths are trusted because the caller has explicitly opted into a
    # specific destination — the typical library / CLI flow.
    if not is_absolute:
        try:
            cwd_resolved = Path(cwd).resolve()
        except Exception:
            cwd_resolved = Path.cwd().resolve()
        try:
            resolved.relative_to(cwd_resolved)
        except ValueError as e:
            raise PermissionError(
                f"Refusing to write '{resolved}' outside of working directory "
                f"'{cwd_resolved}'"
            ) from e
    path = resolved
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "name": company.name,
        "description": company.description[:300],
        "sector": company.sector,
        "geography": company.geography,
        "impact_themes": company.impact_themes,
        "sdg_claims": company.sdg_claims,
        "reported_metrics": {k: v for k, v in company.reported_metrics.items()},
        "metric_recommendations": suggested_metric_ids or [],
        "evidence_note": (
            "metric_recommendations are suggested IRIS+ metrics only; they are not "
            "reported evidence and should not be copied into reported_metrics until "
            "a source value is available."
        ),
    }
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
