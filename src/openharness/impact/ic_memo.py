"""IC (Investment Committee) memo generator.

Produces a structured IC memo from an `Assessment`, an `IC gate scorecard`,
and an optional `FundThesis`. Outputs in Markdown by default; if optional
deps are installed (`python-docx`, `python-pptx`), the same content is
emitted as Word / PowerPoint.

The Markdown is intentionally LP-friendly and follows a format that maps to
each common GP IC template (Sequoia / TPG Rise / generic), so a GP can paste
the output directly or pipe it through `pandoc` to their preferred format.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from openharness.impact.deal_gate import DealScorecard
from openharness.impact.fund_thesis import FundThesis, weighted_5d_overall, weighted_sdg_overall
from openharness.impact.models import Assessment


def _fmt_pct(x: float) -> str:
    return f"{x:.1f}%"


def _fmt_score(x: float) -> str:
    return f"{x:.1f}/5"


def render_ic_memo_markdown(
    assessment: Assessment,
    scorecard: DealScorecard,
    thesis: FundThesis | None = None,
    *,
    dd_coverage_pct: float | None = None,
    greenwashing_score: float | None = None,
    greenwashing_classification: str | None = None,
    deal_size_eur_m: float | None = None,
) -> str:
    """Build a Markdown IC memo string."""
    company = assessment.company
    fd = assessment.five_dimensions
    sdgs = sorted(assessment.sdg_alignments, key=lambda a: a.score, reverse=True)
    today = date.today().isoformat()

    out: list[str] = []
    out.append(f"# Investment Committee Memo — {company.name or 'Unnamed Company'}")
    out.append("")
    out.append(f"- **Date**: {today}")
    out.append(f"- **Fund**: {scorecard.fund}")
    out.append(f"- **Sector**: {company.sector or 'n/a'}")
    if deal_size_eur_m is not None:
        out.append(f"- **Proposed deal size**: EUR {deal_size_eur_m:.1f}m")
    out.append(f"- **IC gate result**: **{scorecard.overall_status.upper()}** — {scorecard.recommendation}")
    out.append("")

    out.append("## 1. Impact Thesis Fit")
    if thesis and not thesis.is_default:
        out.append(f"Fund thesis: *{thesis.name}* ({thesis.strategy}, vintage {thesis.vintage_year})")
        if fd:
            w5d = weighted_5d_overall(fd, thesis)
            out.append(f"- Fund-weighted 5D overall: **{w5d:.2f}/5** (unweighted: {_fmt_score(fd.overall_score)})")
        if sdgs:
            wsdg = weighted_sdg_overall(sdgs, thesis)
            out.append(f"- Fund-weighted SDG score: **{wsdg:.1f}/100**")
    else:
        out.append("*No fund thesis loaded — using equal-weight defaults. Set `data/fund_thesis.yaml` for fund-specific weighting.*")
    out.append("")

    out.append("## 2. 5-Dimension Impact Score")
    if fd:
        out.append("| Dimension | Score | Provenance | Notes |")
        out.append("|---|---|---|---|")
        for dim_name, ds in (
            ("What", fd.what), ("Who", fd.who), ("How Much", fd.how_much),
            ("Contribution", fd.contribution), ("Risk", fd.risk),
        ):
            out.append(f"| {dim_name} | {_fmt_score(ds.score)} | {ds.provenance} | {ds.notes} |")
        out.append(f"| **Overall** | **{_fmt_score(fd.overall_score)}** | {fd.overall_provenance} | Grade: {fd.overall_grade} |")
        if fd.recommendations:
            out.append("")
            out.append("**Recommendations:**")
            for r in fd.recommendations:
                out.append(f"- {r}")
    else:
        out.append("*No 5D assessment available.*")
    out.append("")

    out.append("## 3. SDG Alignment (top 5)")
    if sdgs:
        out.append("| SDG | Score | Targets matched | Provenance |")
        out.append("|---|---|---|---|")
        for a in sdgs[:5]:
            out.append(
                f"| SDG {a.goal} ({a.goal_name}) | {a.score:.0f}/100 "
                f"| {len(a.matched_targets)} | {a.provenance} ({a.scoring_basis}) |"
            )
    out.append("")

    out.append("## 4. Due Diligence Coverage")
    if dd_coverage_pct is not None:
        out.append(f"- Coverage: **{_fmt_pct(dd_coverage_pct)}**")
    else:
        out.append("- Coverage: *not run*")
    out.append("")

    out.append("## 5. Greenwashing & Authenticity")
    if greenwashing_score is not None:
        out.append(f"- Composite risk: **{greenwashing_score:.1f}/100**"
                   + (f" — {greenwashing_classification}" if greenwashing_classification else ""))
    else:
        out.append("- *Greenwashing screen not run.*")
    out.append("")

    out.append("## 6. IC Gate Detail")
    out.append("| Check | Status | Actual | Threshold | Note |")
    out.append("|---|---|---|---|---|")
    for c in scorecard.checks:
        out.append(f"| {c.name} | {c.status} | {c.actual} | {c.threshold} | {c.message} |")
    out.append("")

    if scorecard.blocking_failures:
        out.append("### Blocking failures")
        for m in scorecard.blocking_failures:
            out.append(f"- ❌ {m}")
        out.append("")
    if scorecard.warnings_list:
        out.append("### Warnings")
        for m in scorecard.warnings_list:
            out.append(f"- ⚠️ {m}")
        out.append("")

    out.append("## 7. Recommendation")
    out.append(f"> {scorecard.recommendation}")
    out.append("")
    out.append("---")
    out.append("*Generated by Impact Vision — review before submission.*")

    return "\n".join(out)


def render_ic_memo_docx(markdown: str, path: str | Path) -> Path:
    """Render an IC memo as a .docx file.

    Requires `python-docx`. If not installed, raises ImportError with a clear
    install hint. Heading detection is intentionally simple — production GPs
    will pipe the markdown through pandoc for richer formatting.
    """
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Word export requires the optional dependency 'python-docx'. "
            "Install with: pip install python-docx"
        ) from exc

    doc = Document()
    for line in markdown.splitlines():
        if line.startswith("# "):
            doc.add_heading(line[2:], level=0)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=1)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=2)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.startswith("> "):
            doc.add_paragraph(line[2:], style="Intense Quote")
        elif line.startswith("|"):
            # leave tables as plain text — pandoc / a richer renderer handles
            # actual table layout. Avoid silent formatting bugs.
            doc.add_paragraph(line)
        else:
            doc.add_paragraph(line)

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(p))
    return p


def render_ic_memo_pptx(
    assessment: Assessment,
    scorecard: DealScorecard,
    thesis: FundThesis | None = None,
    path: str | Path = "ic_memo.pptx",
) -> Path:
    """Render a 4-slide IC summary deck.

    Requires `python-pptx`.
    """
    try:
        from pptx import Presentation  # type: ignore
        from pptx.util import Inches
    except ImportError as exc:
        raise ImportError(
            "PowerPoint export requires 'python-pptx'. Install with: pip install python-pptx"
        ) from exc

    prs = Presentation()

    # Slide 1: Title
    blank = prs.slide_layouts[5]
    s1 = prs.slides.add_slide(blank)
    s1.shapes.title.text = f"IC Memo — {assessment.company.name or 'Unnamed'}"

    # Slide 2: 5D
    s2 = prs.slides.add_slide(blank)
    s2.shapes.title.text = "5-Dimension Impact Score"
    if assessment.five_dimensions:
        fd = assessment.five_dimensions
        body = (f"Overall: {fd.overall_score:.1f}/5 ({fd.overall_grade})\n"
                f"What: {fd.what.score} | Who: {fd.who.score} | "
                f"How Much: {fd.how_much.score} | "
                f"Contribution: {fd.contribution.score} | Risk: {fd.risk.score}")
        s2.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(2)).text_frame.text = body

    # Slide 3: SDG
    s3 = prs.slides.add_slide(blank)
    s3.shapes.title.text = "SDG Alignment"
    sdg_lines = "\n".join(
        f"SDG {a.goal} ({a.goal_name}): {a.score:.0f}/100"
        for a in sorted(assessment.sdg_alignments, key=lambda a: a.score, reverse=True)[:5]
    )
    s3.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(4)).text_frame.text = sdg_lines

    # Slide 4: IC gate
    s4 = prs.slides.add_slide(blank)
    s4.shapes.title.text = f"IC Gate: {scorecard.overall_status.upper()}"
    body = "\n".join(f"- {c.name}: {c.status}" for c in scorecard.checks)
    body += "\n\nRecommendation:\n" + scorecard.recommendation
    s4.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(4)).text_frame.text = body

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(p))
    return p


def render_ic_memo(
    assessment: Assessment,
    scorecard: DealScorecard,
    thesis: FundThesis | None = None,
    *,
    output_format: Literal["markdown", "docx", "pptx"] = "markdown",
    path: str | Path | None = None,
    **kwargs,
) -> str | Path:
    """Single entry point — returns markdown string or written file path."""
    md = render_ic_memo_markdown(assessment, scorecard, thesis, **kwargs)
    if output_format == "markdown":
        if path:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(md, encoding="utf-8")
            return p
        return md
    if output_format == "docx":
        return render_ic_memo_docx(md, path or "ic_memo.docx")
    if output_format == "pptx":
        return render_ic_memo_pptx(assessment, scorecard, thesis, path or "ic_memo.pptx")
    raise ValueError(f"Unknown output_format: {output_format}")
