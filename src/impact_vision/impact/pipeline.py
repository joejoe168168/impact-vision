"""One document in, a full set of deliverables out (v7 Wave 1).

``assess_document`` runs the whole deal-screening chain on a pitch deck /
memo — claim extraction, IRIS+ mapping, 5D, SDG, gap analysis, DD coverage,
greenwashing, IC gate — without an LLM or API key. ``write_deliverables``
renders the impact report, IC memo and DD report next to each other.

This is the engine behind ``impact-vision assess`` / ``impact-vision demo``
and the ``assess_deal`` agent tool; examples and demos reuse it instead of
re-assembling the pipeline by hand.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from impact_vision.impact.models import Assessment, Company

SUPPORTED_SUFFIXES = (".pdf", ".txt", ".md", ".markdown", ".docx", ".pptx")
AUDIENCES = ("full", "ic", "lp", "regulator", "public")


@dataclass
class AssessmentBundle:
    """Everything one assessment produced, ready to render or serialise."""

    company: Company
    assessment: Assessment
    dd: Any
    greenwashing: Any
    thesis: Any
    scorecard: Any
    report_data: dict[str, Any]
    source_label: str = "Source document"
    files: list[Path] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        """Compact, JSON-safe headline numbers."""
        from impact_vision.impact.ai_provenance import ai_provenance_for_report, machine_marking

        fd = self.assessment.five_dimensions
        top = [
            {"goal": a.goal, "name": a.goal_name, "score": a.score, "confidence": a.confidence}
            for a in self.assessment.sdg_alignments
            if a.material
        ][:3]
        from impact_vision.impact.expected_impact import headline, methodology_mode

        v2 = self.report_data.get("expected_impact") or {}
        gate2 = v2.get("gate") or {}
        use_v2 = bool(gate2) and methodology_mode() == "2"
        plan = gate2.get("plan") or []
        return {
            "company": self.company.name,
            "sector": self.company.sector,
            "geography": self.company.geography,
            "gate": gate2["label"].upper() if use_v2 else self.scorecard.display_status,
            "recommendation": ((plan[0]["action"] if plan else "; ".join(gate2.get("reasons", [])))
                               if use_v2 else self.scorecard.recommendation),
            "thesis_gate": self.scorecard.display_status,
            "expected_impact": headline(v2),
            "evidence_quality": (v2.get("evidence_quality") or {}).get("score"),
            "five_d_score": round(fd.overall_score, 2) if fd else None,
            "five_d_grade": fd.overall_grade if fd else None,
            "five_d_evidence": fd.overall_provenance if fd else None,
            "top_sdgs": top,
            "greenwashing_risk": self.greenwashing.overall_score,
            "greenwashing_class": self.greenwashing.classification,
            "dd_coverage_pct": self.dd.coverage_pct,
            "claims": len(self.assessment.impact_claims),
            "reported_metrics": dict(self.company.reported_metrics),
            "files": [Path(p).name for p in self.files],
            "ai_disclosure": ai_provenance_for_report(self.report_data).disclosure,
            "ai_marking": machine_marking(ai_provenance_for_report(self.report_data)),
            "methodology": self.assessment.methodology,
        }


def reflow_pdf_text(text: str) -> str:
    """Undo PDF line wrapping inside sentences, keep headings on their own line.

    PDF extraction ends every visual line with a newline, which splits phrases
    such as "142\nstaff" or "(OI8869:\n180)". A line break is joined into a
    space when the line is a wrapped body line (long, not ending a sentence) or
    the next line plainly continues it (starts lowercase / with a digit or
    punctuation). Short unpunctuated lines are headings and keep their break,
    so "People & smallholders" doesn't bleed into "We employ 142 staff".
    """
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        if out:
            prev = out[-1].rstrip()
            stripped = line.lstrip()
            continues = bool(stripped) and (stripped[0].islower() or stripped[0].isdigit()
                                            or stripped[0] in "(%,;&-[")
            wrapped = len(prev) >= 60 and not prev.endswith((".", "!", "?", ":"))
            if prev and stripped and (wrapped or (continues and not prev.endswith((".", "!", "?")))):
                out[-1] = f"{prev} {stripped}"
                continue
        out.append(line)
    return "\n".join(out)


def _office_missing(kind: str) -> ValueError:
    return ValueError(f"Reading {kind} files needs the office extra: pip install 'impact-vision[office]'")


def _read_docx(path: Path) -> str:
    """Paragraphs (headings as markdown ``#`` lines, so sections are found) and tables."""
    try:
        import docx  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - optional extra
        raise _office_missing("Word") from exc
    document = docx.Document(str(path))
    lines: list[str] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            lines.append("")
            continue
        style = (para.style.name or "").lower() if para.style is not None else ""
        if style.startswith("heading") or style == "title":
            lines += ["", f"# {text}"]
        elif style.startswith("list"):
            lines.append(f"- {text}")
        else:
            lines.append(text)
    for table in document.tables:
        lines.append("")
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            lines.append(" | ".join(dict.fromkeys(c for c in cells if c)))
    return "\n".join(lines).strip()


def _read_pptx(path: Path) -> str:
    """One section per slide: the title as a heading, then the text frames."""
    try:
        from pptx import Presentation  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - optional extra
        raise _office_missing("PowerPoint") from exc
    lines: list[str] = []
    for slide in Presentation(str(path)).slides:
        title = slide.shapes.title.text.strip() if slide.shapes.title is not None and slide.shapes.title.has_text_frame else ""
        if title:
            lines += ["", f"# {title}"]
        for shape in slide.shapes:
            if shape == slide.shapes.title or not getattr(shape, "has_text_frame", False):
                continue
            for para in shape.text_frame.paragraphs:
                text = "".join(run.text for run in para.runs).strip()
                if text:
                    lines.append(text)
        if getattr(slide, "has_notes_slide", False) and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                lines.append(notes)
    return "\n".join(lines).strip()


def read_document_pages(path: str | Path) -> list[tuple[int, str]]:
    """``[(page, text)]`` for PDFs (pages) and PowerPoint (slides); [] otherwise."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        from impact_vision.tools.impact.pitch_deck_analyze_tool import _extract_pdf_text

        _text, pages = _extract_pdf_text(p)
        return [(int(pg["page"]), str(pg.get("text", ""))) for pg in pages if int(pg.get("page", 0)) > 0]
    if suffix == ".pptx":
        try:
            from pptx import Presentation  # type: ignore[import-not-found]
        except ImportError:
            return []
        out = []
        for i, slide in enumerate(Presentation(str(p)).slides, 1):
            texts = [para_text for shape in slide.shapes if getattr(shape, "has_text_frame", False)
                     for para_text in (shape.text_frame.text,)]
            out.append((i, "\n".join(texts)))
        return out
    return []


def _norm(text: str) -> str:
    import re

    text = re.sub(r"-\s*\n\s*", "", text or "")  # hyphenation across lines
    return re.sub(r"\s+", " ", text).strip().lower()


def attach_citations(bundle: "AssessmentBundle", pages: list[tuple[int, str]], source_file: str = "") -> int:
    """Give each claim the page (or slide) it was read from (v8 W2.2).

    Returns how many claims were located. Matching uses the first 60 normalised
    characters of the claim, then a shorter prefix, so line wrapping and
    hyphenation in the PDF don't break it.
    """
    if not pages:
        return 0
    normed = [(page, _norm(text)) for page, text in pages]
    found = 0
    for claim, row in zip(bundle.assessment.impact_claims, bundle.report_data.get("impact_claims") or []):
        if claim.source_page:
            continue
        needle = _norm(claim.text)
        for size in (60, 35):
            probe = needle[:size]
            hit = next((page for page, text in normed if probe and probe in text), None)
            if hit is not None:
                claim.source_page = hit
                row["source_page"] = hit
                if source_file:
                    claim.source_file = source_file
                    row["source_file"] = source_file
                found += 1
                break
    return found


def read_document(path: str | Path) -> str:
    """Return the text of a PDF / Word / PowerPoint / TXT / Markdown document."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"No such file: {p}")
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        from impact_vision.tools.impact.pitch_deck_analyze_tool import _extract_pdf_text

        text, _pages = _extract_pdf_text(p)
        return reflow_pdf_text(text)
    if suffix == ".docx":
        return _read_docx(p)
    if suffix == ".pptx":
        return _read_pptx(p)
    if suffix in SUPPORTED_SUFFIXES:
        return p.read_text(encoding="utf-8", errors="replace")
    raise ValueError(
        f"Unsupported file type {suffix!r}. Use one of: {', '.join(SUPPORTED_SUFFIXES)}"
    )


def assess_document(
    text: str,
    *,
    name: str = "",
    sector: str = "",
    geography: str = "",
    description: str = "",
    impact_themes: list[str] | None = None,
    sdg_claims: list[int] | None = None,
    reported_metrics: dict[str, Any] | None = None,
    source_label: str = "Source document",
    audience: str = "full",
    theme: str = "",
    stage: str = "",
) -> AssessmentBundle:
    """Run the full no-LLM assessment chain on one document.

    Anything not passed explicitly (name, sector, geography, themes, SDG
    claims) is inferred from the text with the same rules as the
    ``pitch_deck_analyze`` tool.
    """
    from impact_vision.impact.benchmarks import compare_to_benchmark
    from impact_vision.impact.database import get_metric_store
    from impact_vision.impact.gap_analysis import analyze_gaps
    from impact_vision.impact.sdg_mapper import generate_sdg_gap_recommendations
    from impact_vision.impact.sdk import ImpactVision
    from impact_vision.impact.text_sections import scoring_text
    from impact_vision.tools.impact.impact_report_tool import _infer_opportunities_and_risks
    from impact_vision.tools.impact.pitch_deck_analyze_tool import (
        _detect_sdg_goals,
        _detect_themes,
        _extract_company_model,
    )

    if audience not in AUDIENCES:
        raise ValueError(f"audience must be one of {', '.join(AUDIENCES)}")
    if not text or not text.strip():
        raise ValueError("The document has no extractable text.")

    themes_guess = _detect_themes(text)
    inferred = _extract_company_model(
        text, name or "Company", themes_guess, _detect_sdg_goals(text, []), [], None
    )

    iv = ImpactVision()
    assessment = iv.assess_company_text(
        name or inferred.name,
        text=text,
        sector=sector or inferred.sector,
        geography=geography or inferred.geography,
        impact_themes=impact_themes if impact_themes is not None else inferred.impact_themes,
    )
    company = assessment.company
    if stage:
        stage_key = stage.strip().lower().replace(" ", "-")
        if stage_key in {"pre-seed", "seed", "series-a", "series-b", "growth", "mature"}:
            company.stage = stage_key  # type: ignore[assignment]
    company.description = description or text[:1000]
    # Scorers read the whole document minus problem/market/team/ask sections.
    company.assessment_text = scoring_text(text) if not description else ""
    company.sdg_claims = list(sdg_claims) if sdg_claims is not None else list(inferred.sdg_claims)
    # IDs the document cites explicitly ("PI4060: 45,000") beat mapped values.
    explicit = dict(inferred.reported_metrics)
    for metric_id, value in explicit.items():
        company.reported_metrics.setdefault(metric_id, value)
    for metric_id, value in (reported_metrics or {}).items():
        company.reported_metrics[metric_id] = value  # caller-supplied values win
    if explicit or reported_metrics or sdg_claims is not None or description:
        assessment = iv.assess_company(company).model_copy(
            update={"impact_claims": assessment.impact_claims}
        )
        company = assessment.company

    dd = iv.run_dd_coverage(text, sector=company.sector or "auto")
    gw = iv.screen_greenwashing(assessment)
    thesis = iv.load_thesis()
    scorecard = iv.evaluate_deal_against_thesis(
        assessment,
        thesis=thesis,
        dd_coverage_pct=dd.coverage_pct,
        greenwashing_score=gw.overall_score,
    )

    store = get_metric_store()
    sdg_recs = generate_sdg_gap_recommendations(assessment.sdg_alignments, company, store)
    sdg_dicts = []
    for a in assessment.sdg_alignments:
        d = a.model_dump()
        d["recommendations"] = sdg_recs.get(a.goal, [])
        sdg_dicts.append(d)

    gap_result = analyze_gaps(company, store)
    gw_dump = gw.model_dump()
    from impact_vision.impact.greenwashing_reviewer import review_claims_v2

    gw_dump["claims_review"] = review_claims_v2(  # v8 W1.9
        assessment.impact_claims, text=company.assessment_text or text)
    gw_dump["sub_scores"] = {
        "claim_metric_gap": gw.claim_metric_gap,
        "adverse_omission": gw.adverse_omission,
        "specificity": gw.specificity,
        "selectivity": gw.selectivity,
        "verification": gw.verification,
    }
    report_data: dict[str, Any] = {
        "company": company.model_dump(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "catalog_version": "IRIS+ 5.3c",
        "five_dimensions": (
            assessment.five_dimensions.model_dump() if assessment.five_dimensions else None
        ),
        "sdg_alignments": sdg_dicts,
        "sdg_alignment": sdg_dicts,  # executive summary reads the singular key
        "gap_analysis": gap_result,
        "greenwashing": gw_dump,
        # Problem / market sections describe the world, not the company's risks (v8).
        "impact_analysis": _infer_opportunities_and_risks(company, company.assessment_text or text),
        "impact_claims": [c.model_dump() for c in assessment.impact_claims],
        "audience": audience,
        "theme": theme,
        "source_label": source_label,
        # Extraction/tagging provenance comes from each claim's extracted_by
        # (regex, or llm when a key is configured); no narrative is AI-drafted.
        "ai_usage": {"drafting": "none"},
        "methodology": assessment.methodology,
    }
    from impact_vision.impact.report_templates.decision_report import decision_from_scorecard

    report_data["decision"] = decision_from_scorecard(scorecard, dd=dd)
    # Methodology 2.0 (v8 Wave 1): expected impact with ranges, evidence
    # quality as its own axis, gate 2.0 and a quantitative evidence plan.
    from impact_vision.impact.expected_impact import assess_expected_impact
    from impact_vision.impact.negative_impacts import assess_negative_impacts

    report_data["negative_impacts"] = assess_negative_impacts(company.sector, company.assessment_text or text)
    report_data["expected_impact"] = assess_expected_impact(
        assessment.impact_claims,
        company.assessment_text or text,
        sector=company.sector,
        company_name=company.name,
        data_completeness_pct=gap_result.get("coverage_percentage"),
        greenwashing=gw,
        v1_checks=report_data["decision"].get("checks", []),
        missing_metrics=[m["name"] for m in gap_result.get("missing", [])[:5]],
        negative=report_data["negative_impacts"],
        claims_review=gw_dump.get("claims_review"),
    )
    # v8 W1.4: enterprise vs investor contribution, on evidence only. The
    # investor half reads the whole text (terms usually sit in "The ask").
    from impact_vision.impact.contribution_split import contribution_split

    report_data["contribution_split"] = contribution_split(
        company.assessment_text or text, report_data["expected_impact"], investor_text=text)
    fd = report_data["five_dimensions"]
    if fd and company.sector:
        scores = {k: fd[k]["score"] for k in ("what", "who", "how_much", "contribution", "risk")}
        bm = compare_to_benchmark(
            company.sector, scores, fd["overall_score"], gap_result["coverage_percentage"]
        )
        if bm.get("benchmark_available"):
            report_data["benchmark_comparison"] = bm

    return AssessmentBundle(
        company=company,
        assessment=assessment,
        dd=dd,
        greenwashing=gw,
        thesis=thesis,
        scorecard=scorecard,
        report_data=report_data,
        source_label=source_label,
    )


def assess_file(path: str | Path, **kwargs: Any) -> AssessmentBundle:
    """Read *path* and run :func:`assess_document` on it; claims get page citations."""
    p = Path(path)
    kwargs.setdefault("source_label", p.name)
    bundle = assess_document(read_document(p), **kwargs)
    attach_citations(bundle, read_document_pages(p))
    return bundle


def assess_files(paths: list[str | Path], **kwargs: Any) -> AssessmentBundle:
    """Assess several documents about one company (deck + impact report + …) together.

    Each file becomes a ``# <file name>`` section of one combined text, so the
    evidence in any of them counts.
    """
    from impact_vision.impact.metric_import import SPREADSHEET_SUFFIXES, import_metrics

    all_files = [Path(p) for p in paths]
    sheets = [f for f in all_files if f.suffix.lower() in SPREADSHEET_SUFFIXES]
    files = [f for f in all_files if f not in sheets]
    if not files:
        raise ValueError("Add a pitch deck or impact report next to the spreadsheet: the metrics need a company to "
                         "belong to.")
    imports = [import_metrics(f) for f in sheets]
    if imports:
        # Spreadsheet KPIs are reported figures (v8 W3.5); explicit kwargs still win.
        merged: dict[str, Any] = {}
        for imp in imports:
            merged.update(imp.metrics)
        merged.update(kwargs.get("reported_metrics") or {})
        kwargs["reported_metrics"] = merged
    kwargs.setdefault("source_label", " + ".join(f.name for f in all_files))
    if len(files) == 1:
        bundle = assess_file(files[0], **kwargs)
    else:
        parts = [f"# {f.name}\n\n{read_document(f)}" for f in files]
        bundle = assess_document("\n\n".join(parts), **kwargs)
        for f in files:
            attach_citations(bundle, read_document_pages(f), source_file=f.name)
    if imports:
        bundle.report_data["metric_import"] = [
            {"source": imp.source, "rows": imp.rows, "matched": sorted(imp.metrics), "unmatched": imp.unmatched[:20],
             "series": {k: v for k, v in imp.series.items() if len(v) > 1}} for imp in imports]
    return bundle


def slugify(name: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:60] or "company"


def write_deliverables(
    bundle: AssessmentBundle,
    out_dir: str | Path,
    *,
    basename: str | None = None,
    include_docx: bool = True,
    pdf: bool = False,
    lang: str = "en",
    include_data: bool = True,
) -> list[Path]:
    """Write the impact report, IC memo, DD report (+ DOCX, data workbook/CSV, JSON summary).

    ``pdf=True`` also prints the impact report and IC memo to PDF (needs the
    ``[pdf]`` extra; raises :class:`PdfUnavailable` with an install hint).
    """
    from impact_vision.impact.ic_memo import render_ic_memo_html
    from impact_vision.impact.report_templates import (
        render_dd_questionnaire_docx,
        render_dd_report_html,
    )
    from impact_vision.impact.report_templates.decision_report import render_decision_report

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = basename or slugify(bundle.company.name)
    files: list[Path] = []

    report = out / f"{stem}_impact_report.html"
    report.write_text(render_decision_report(bundle.report_data, lang=lang), encoding="utf-8")
    files.append(report)

    from impact_vision.impact.ai_provenance import ai_provenance_for_report, machine_marking, mark_html

    marking = machine_marking(ai_provenance_for_report(bundle.report_data))
    memo = out / f"{stem}_ic_memo.html"
    memo.write_text(
        mark_html(render_ic_memo_html(
            bundle.assessment,
            bundle.scorecard,
            bundle.thesis,
            dd_coverage_pct=bundle.dd.coverage_pct,
            greenwashing_score=bundle.greenwashing.overall_score,
            greenwashing_classification=bundle.greenwashing.classification,
            expected_impact=bundle.report_data.get("expected_impact"),
        ), marking),
        encoding="utf-8",
    )
    files.append(memo)

    dd_path = out / f"{stem}_dd_report.html"
    dd_path.write_text(
        mark_html(render_dd_report_html(
            bundle.dd,
            company_name=bundle.company.name,
            document_label=bundle.source_label,
            reviewer="Impact Vision",
        ), marking),
        encoding="utf-8",
    )
    files.append(dd_path)

    if pdf:
        from impact_vision.impact.report_templates.pdf import html_to_pdf

        for html_file in (report, memo):
            pdf_path, _engine = html_to_pdf(
                html_file.read_text(encoding="utf-8"), html_file.with_suffix(".pdf")
            )
            files.append(pdf_path)

    if include_docx:
        from impact_vision.impact.ic_memo import render_ic_memo

        try:
            files.append(Path(render_ic_memo(
                bundle.assessment, bundle.scorecard, bundle.thesis,
                output_format="docx", path=out / f"{stem}_ic_memo.docx",
                expected_impact=bundle.report_data.get("expected_impact"),
            )))
        except ImportError:
            pass  # python-docx is optional ([office] extra)
        docx = out / f"{stem}_dd_questionnaire.docx"
        try:
            render_dd_questionnaire_docx(
                bundle.dd, docx, company_name=bundle.company.name,
                document_label=bundle.source_label, reviewer="Impact Vision",
            )
            files.append(docx)
        except ImportError:
            pass  # python-docx is optional

    if include_data:
        from impact_vision.impact.exports import to_csv, write_xlsx

        try:
            files.append(write_xlsx(bundle.report_data, out / f"{stem}_data.xlsx"))
        except ImportError:
            pass  # openpyxl missing
        data_csv = out / f"{stem}_data.csv"
        data_csv.write_text(to_csv(bundle.report_data), encoding="utf-8")
        files.append(data_csv)

    bundle.files = files
    summary = out / f"{stem}_summary.json"
    summary.write_text(json.dumps(bundle.summary(), indent=2, default=str), encoding="utf-8")
    files.append(summary)
    bundle.files = files
    return files


def save_bundle(bundle: AssessmentBundle, *, source_label: str = "", period: str = "") -> str:
    """Persist *bundle* in the AssessmentStore; returns the shared ``assessment_id``."""
    from impact_vision.impact.storage import get_assessment_store

    a = bundle.assessment
    row_id = get_assessment_store().save_assessment(
        bundle.company.name,
        bundle.company.model_dump(mode="json"),
        five_dimensions=a.five_dimensions.model_dump(mode="json") if a.five_dimensions else None,
        sdg_alignments=[s.model_dump(mode="json") for s in a.sdg_alignments],
        gap_analysis=bundle.report_data.get("gap_analysis"),
        greenwashing=bundle.greenwashing.model_dump(mode="json"),
        metadata={
            "source": source_label or bundle.source_label,
            "summary": bundle.summary(),
            "impact_claims": [c.model_dump(mode="json") for c in a.impact_claims],
            "dd_coverage_pct": bundle.dd.coverage_pct,
            "gate": bundle.scorecard.model_dump(mode="json"),
            "expected_impact": bundle.report_data.get("expected_impact"),
            "negative_impacts": bundle.report_data.get("negative_impacts"),
        },
        new_version=True,
    )
    # v8 W3: file it on the company record (stage, expected vs actual).
    try:
        from impact_vision.impact.company_record import record_assessment

        record_assessment(bundle, str(row_id), period=period)
    except Exception:  # noqa: BLE001 - the assessment is saved even if the record update fails
        pass
    return str(row_id)


# Fictional sample decks bundled for ``impact-vision demo`` (data/sample_decks).
SAMPLE_DECKS: dict[str, tuple[str, str]] = {
    "pig-farm": ("kampung_makmur_pig_farm.pdf", "Integrated pig farm + biogas, Malaysia"),
    "solar": ("sunpath_solar.pdf", "Pay-as-you-go solar home systems, Kenya"),
    "microfinance": ("brightpath_microfinance.pdf", "Digital microfinance, Sub-Saharan Africa"),
}


def sample_deck_path(key: str) -> Path:
    from impact_vision.impact._paths import data_path

    if key not in SAMPLE_DECKS:
        raise KeyError(f"Unknown sample deck {key!r}. Choose from: {', '.join(SAMPLE_DECKS)}")
    return data_path("sample_decks", SAMPLE_DECKS[key][0])


def _impact_line(h: dict[str, Any]) -> str:
    return (f"{h['p50']:,.0f} {h['unit']} (P10 {h['p10']:,.0f} – P90 {h['p90']:,.0f}, "
            f"{h['uncertainty']} uncertainty)")


def format_summary(bundle: AssessmentBundle) -> str:
    """Plain-text headline for terminals."""
    s = bundle.summary()
    sdgs = ", ".join(f"SDG {t['goal']} ({t['score']:.0f})" for t in s["top_sdgs"]) or "none material"
    lines = [
        f"{s['company']}  ·  {s['sector'] or 'sector unknown'}  ·  {s['geography'] or 'geography unknown'}",
        f"  IC gate:          {s['gate']}",
        f"                    {s['recommendation']}",
        *([f"  Expected impact:  {_impact_line(s['expected_impact'])}"] if s.get("expected_impact") else []),
        *([f"  Evidence quality: {s['evidence_quality']}/100"] if s.get("evidence_quality") is not None else []),
        f"  5D score:         {s['five_d_score']}/5 (grade {s['five_d_grade']}, {s['five_d_evidence']})",
        f"  Top SDGs:         {sdgs}",
        f"  Greenwashing:     {s['greenwashing_risk']:.0f}/100 ({s['greenwashing_class']})",
        f"  DD coverage:      {s['dd_coverage_pct']:.0f}%",
        f"  Evidence:         {s['claims']} claims, {len(s['reported_metrics'])} IRIS+ metrics",
    ]
    return "\n".join(lines)


def write_gallery(
    bundles: list[AssessmentBundle],
    out_dir: str | Path,
    *,
    extras: dict[str, list[tuple[str, str]]] | None = None,
    title: str = "Impact Vision results",
    intro: str = "",
    home_href: str = "",
) -> Path:
    """Write an index.html linking every company's deliverables.

    *extras* maps a company name to extra ``(label, relative path)`` links
    (e.g. audience or language variants), shown as their own group.
    """
    from impact_vision.impact.report_templates.decision_report import (
        _env,
        design_css,
        monogram,
    )
    from impact_vision.impact.report_templates.report_v2 import SDG_COLORS, sdg_text_colour

    out = Path(out_dir)
    cards = []
    for b in bundles:
        s = b.summary()
        gate = s["gate"]
        tone = ("warning" if "INSUFFICIENT" in gate else
                {"PASS": "good", "WARN": "warning", "FAIL": "critical"}.get(gate, ""))
        deliverables = []
        for f in b.files:
            p = Path(f)
            if p.suffix in {".html", ".pdf", ".docx", ".xlsx", ".csv", ".json"}:
                try:
                    href = p.resolve().relative_to(out.resolve()).as_posix()
                except ValueError:
                    href = p.name
                deliverables.append({"href": href, "label": _label(p).split(" (")[0],
                                     "kind": p.suffix.lstrip(".").upper()})
        groups = [{"label": "Deliverables", "links": deliverables}]
        if extras and b.company.name in extras:
            groups.append({"label": "Variants", "links": [
                {"href": href, "label": label, "kind": Path(href).suffix.lstrip(".").upper()}
                for label, href in extras[b.company.name]
            ]})
        gw = s["greenwashing_risk"] or 0
        cards.append({
            "company": s["company"],
            "monogram": monogram(s["company"]),
            "meta": " · ".join(x for x in (s["sector"], s["geography"]) if x),
            "gate": gate.title() if gate.isupper() else gate,
            "tone": tone,
            "five_d": f"{s['five_d_score'] or 0:.1f}",
            "five_d_pct": (s["five_d_score"] or 0) / 5 * 100,
            "gw": f"{gw:.0f}",
            "gw_tone": "good" if gw < 40 else "warning" if gw < 60 else "critical",
            "sdgs": [{"goal": g["goal"], "color": SDG_COLORS.get(g["goal"], "#888"),
                      "ink": sdg_text_colour(g["goal"])} for g in s["top_sdgs"]],
            "sdg_text": ", ".join(str(g["goal"]) for g in s["top_sdgs"]) or "—",
            "claims": s["claims"],
            "metrics": len(s["reported_metrics"]),
            "groups": groups,
        })
    page = _env().get_template("gallery.html.j2").render(
        css=design_css(),
        title=title,
        subtitle=f"{len(bundles)} assessment{'s' if len(bundles) != 1 else ''} generated offline",
        intro=intro,
        home_href=home_href,
        cards=cards,
        footer="Generated by Impact Vision — open-source impact measurement. Sample companies are fictional.",
    )
    path = out / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def _label(path: Path) -> str:
    name = path.stem
    labels = (
        ("_impact_report", "Impact report"),
        ("_ic_memo", "IC memo"),
        ("_dd_report", "DD report"),
        ("_dd_questionnaire", "DD questionnaire"),
        ("_summary", "Summary"),
        ("_data", "Data"),
    )
    base = next((label for suffix, label in labels if name.endswith(suffix)), path.name)
    return base if path.suffix == ".html" else f"{base} ({path.suffix})"


__all__ = [
    "AUDIENCES",
    "AssessmentBundle",
    "SAMPLE_DECKS",
    "SUPPORTED_SUFFIXES",
    "assess_document",
    "assess_file",
    "format_summary",
    "read_document",
    "sample_deck_path",
    "save_bundle",
    "slugify",
    "write_deliverables",
    "write_gallery",
]
