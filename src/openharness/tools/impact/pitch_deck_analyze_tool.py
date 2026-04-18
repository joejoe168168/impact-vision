"""Tool: Extract impact claims from PDF pitch decks, map to IRIS+/SDGs, and identify DD gaps."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.dd_checklist import analyze_document_coverage, select_questions_for_document
from openharness.impact.greenwashing import assess_greenwashing
from openharness.impact.models import ImpactClaim
from openharness.impact.sdg_taxonomy import get_sdg_goal
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult

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
    "water": ["Water", "Sustainable Water Management"],
    "housing": ["Affordable Housing"],
    "climate": ["Climate Mitigation", "Climate Adaptation"],
}


class PitchDeckAnalyzeInput(BaseModel):
    file_path: str = Field(description="Path to the PDF pitch deck or investment memo")
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
        except Exception as e:
            return ToolResult(output=f"Failed to extract document text: {e}", is_error=True)

        if not text.strip():
            return ToolResult(output="No text could be extracted from the document", is_error=True)

        store = get_metric_store()
        claims = _extract_impact_claims(page_texts, store)
        detected_themes = _detect_themes(text)
        detected_sdgs = _detect_sdg_goals(text, claims)
        suggested_metrics = _suggest_iris_metrics(text, detected_themes, store) if args.include_iris_suggestions else []

        extracted_company = None
        if args.extract_company:
            extracted_company = _extract_company_model(
                text, path.stem, detected_themes, detected_sdgs,
                [m.id for m in suggested_metrics[:10]], store,
            )
            if args.save_company_yaml and extracted_company:
                _save_company_yaml(extracted_company, args.save_company_yaml, context.cwd)

        lines = [
            f"PITCH DECK / MEMO ANALYSIS: {path.name}",
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
            dd_result = analyze_document_coverage(text)
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
            lines.append(f"  Suggested Metrics: {len(extracted_company.reported_metrics)}")
            if args.save_company_yaml:
                lines.append(f"  Saved to: {args.save_company_yaml}")
            lines.append("")
            lines.append("  You can now use this data directly with sdg_mapper, five_dimension_assess,")
            lines.append("  or impact_report tools by passing these values.")

        metadata = {
            "claims": [c.model_dump() for c in claims],
            "detected_themes": detected_themes,
            "detected_sdgs": sorted(detected_sdgs),
            "suggested_metrics": [m.id for m in suggested_metrics[:15]],
            "text_length": len(text),
            "pages": len(page_texts),
        }
        if extracted_company:
            metadata["extracted_company"] = extracted_company.model_dump()
        if gw_result:
            metadata["greenwashing"] = gw_result.model_dump()

        return ToolResult(output="\n".join(lines), metadata=metadata)


_LANG_MARKERS = {
    "es": ["empresa", "impacto", "inversión", "comunidad", "sostenible", "objetivo", "beneficiarios"],
    "fr": ["entreprise", "investissement", "communauté", "durable", "objectif", "bénéficiaires"],
    "pt": ["empresa", "investimento", "comunidade", "sustentável", "objetivo", "beneficiários"],
    "zh": ["企业", "投资", "影响", "可持续", "社区", "目标"],
}


def _detect_language(text: str) -> str:
    """Detect document language from text content. Returns ISO 639-1 code."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for lang, markers in _LANG_MARKERS.items():
        scores[lang] = sum(1 for m in markers if m in text_lower)
    best = max(scores, key=scores.get) if scores else "en"
    return best if scores.get(best, 0) >= 3 else "en"


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

            confidence = min(1.0, effective_hits * 0.15)
            if negated_hits > 0:
                confidence *= 0.5
            category = _classify_claim(lower)
            mapped_metrics = _match_metrics(sentence, store)
            mapped_targets = _match_sdg_targets(sentence)

            claims.append(ImpactClaim(
                text=sentence.strip(),
                source_page=page_num,
                mapped_metrics=[m.id for m in mapped_metrics[:5]],
                mapped_sdg_targets=mapped_targets[:5],
                confidence=round(confidence, 2),
                category=category,
            ))

    claims.sort(key=lambda c: c.confidence, reverse=True)
    return claims[:30]


def _detect_themes(text: str) -> list[str]:
    """Detect impact themes from document text."""
    text_lower = text.lower()
    themes: list[str] = []
    for keyword, theme_list in SECTOR_THEME_MAP.items():
        if keyword in text_lower:
            for t in theme_list:
                if t not in themes:
                    themes.append(t)
    return themes


def _detect_sdg_goals(text: str, claims: list[ImpactClaim]) -> set[int]:
    """Detect SDG goals from explicit references and claim mappings."""
    import re
    goals: set[int] = set()

    sdg_refs = re.findall(r'SDG\s*(\d{1,2})', text, re.IGNORECASE)
    for ref in sdg_refs:
        num = int(ref)
        if 1 <= num <= 17:
            goals.add(num)

    theme_sdg_hints = {
        "poverty": [1], "hunger": [2], "food": [2], "nutrition": [2],
        "health": [3], "medical": [3], "healthcare": [3],
        "education": [4], "learning": [4], "school": [4],
        "gender": [5], "women": [5], "girl": [5],
        "water": [6], "sanitation": [6],
        "energy": [7], "solar": [7], "renewable": [7],
        "employment": [8], "job": [8], "decent work": [8],
        "infrastructure": [9], "innovation": [9],
        "inequality": [10], "inclusion": [10],
        "urban": [11], "city": [11], "housing": [11],
        "waste": [12], "circular": [12], "recycl": [12],
        "climate": [13], "carbon": [13], "emission": [13],
        "ocean": [14], "marine": [14],
        "forest": [15], "biodiversity": [15], "land": [15],
    }
    text_lower = text.lower()
    for keyword, sdg_list in theme_sdg_hints.items():
        if keyword in text_lower:
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
    lower = sentence.lower()
    keywords = [
        "revenue", "employee", "client", "beneficiar", "emission", "carbon",
        "energy", "water", "waste", "health", "education", "job", "wage",
        "poverty", "inclusion", "gender", "women", "training",
    ]
    matched: list = []
    for kw in keywords:
        if kw in lower:
            results = store.search(kw, limit=3)
            matched.extend(results)
    seen = set()
    deduped = []
    for m in matched:
        if m.id not in seen:
            seen.add(m.id)
            deduped.append(m)
    return deduped[:5]


def _match_sdg_targets(sentence: str) -> list[str]:
    import re
    targets: list[str] = []
    sdg_refs = re.findall(r'SDG\s*(\d{1,2})', sentence, re.IGNORECASE)
    for ref in sdg_refs:
        num = int(ref)
        if 1 <= num <= 17:
            targets.append(f"{num}.0")
    return targets


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
    from openharness.impact.models import Company

    company_name = filename.replace("_", " ").replace("-", " ").title()
    name_patterns = [
        r'(?:Company|Firm|Organization|Fund|Venture|Startup)\s*(?:Name|:)\s*[:\-]?\s*([A-Z][A-Za-z\s&\.]{2,30})',
        r'^([A-Z][A-Za-z\s&\.]{2,25})(?:\s*[-–—|]\s*(?:Pitch|Investor|Impact))',
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
    reported = {mid: "pending" for mid in suggested_metric_ids}

    return Company(
        name=company_name,
        description=text[:500].strip(),
        sector=sector,
        geography=geography,
        impact_themes=themes,
        reported_metrics=reported,
        sdg_claims=sorted(sdgs),
    )


def _detect_sector(text: str) -> str:
    """Detect company sector from document text."""
    text_lower = text.lower()
    sector_keywords = {
        "Financial Services": ["fintech", "microfinance", "banking", "lending", "insurance", "payment"],
        "Healthcare": ["health", "medical", "pharmaceutical", "clinic", "hospital", "telemedicine"],
        "Education": ["education", "edtech", "school", "university", "learning", "training platform"],
        "Agriculture": ["agriculture", "agritech", "farming", "smallholder", "crop", "livestock"],
        "Energy": ["energy", "solar", "wind", "renewable", "power", "electricity", "cleantech"],
        "Technology": ["software", "platform", "saas", "app", "digital", "technology"],
        "Real Estate": ["housing", "real estate", "property", "affordable housing", "construction"],
        "Water & Sanitation": ["water", "sanitation", "waste management", "recycling"],
        "Transportation": ["transport", "mobility", "logistics", "fleet"],
        "Food & Beverage": ["food", "nutrition", "beverage", "restaurant", "meal"],
    }
    best_sector = ""
    best_hits = 0
    for sector, keywords in sector_keywords.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > best_hits:
            best_hits = hits
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
        "Sub-Saharan Africa": ["sub-saharan", "east africa", "west africa", "central africa", "southern africa"],
        "Kenya": ["kenya", "nairobi"],
        "Nigeria": ["nigeria", "lagos", "abuja"],
        "South Africa": ["south africa", "johannesburg", "cape town"],
        "India": ["india", "mumbai", "delhi", "bangalore", "hyderabad"],
        "China": ["china", "beijing", "shanghai", "shenzhen"],
        "Indonesia": ["indonesia", "jakarta"],
        "Malaysia": ["malaysia", "kuala lumpur"],
        "Vietnam": ["vietnam", "ho chi minh"],
        "Brazil": ["brazil", "são paulo", "sao paulo"],
        "Colombia": ["colombia", "bogotá", "bogota"],
        "Mexico": ["mexico", "mexico city"],
        "Southeast Asia": ["southeast asia", "asean", "mekong"],
        "South Asia": ["south asia", "subcontinent"],
        "Latin America": ["latin america", "latam", "central america"],
        "Middle East": ["middle east", "mena", "gulf states"],
        "Europe": ["europe", "european union"],
        "North America": ["united states", "usa", "canada"],
        "Pacific": ["pacific island", "oceania"],
    }
    best_geo = ""
    best_count = 0
    for region, keywords in geo_patterns.items():
        count = sum(1 for kw in keywords if kw in text_lower)
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


def _save_company_yaml(company, yaml_path: str, cwd) -> None:
    """Save a Company model as YAML for reuse."""
    import yaml
    from pathlib import Path

    path = Path(yaml_path)
    if not path.is_absolute():
        path = cwd / path
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "name": company.name,
        "description": company.description[:300],
        "sector": company.sector,
        "geography": company.geography,
        "impact_themes": company.impact_themes,
        "sdg_claims": company.sdg_claims,
        "reported_metrics": {k: v for k, v in company.reported_metrics.items()},
    }
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
