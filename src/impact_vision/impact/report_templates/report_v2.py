"""Shared HTML report chrome (v2, v0.12.0).

All of the HTML surfaces emitted by Impact Vision -- the full Impact
Report (``impact_report_tool._to_html``), the IC memo
(``ic_memo.render_ic_memo_html``), and the DD coverage report
(``report_templates.dd_report_html.render_dd_report_html``) -- share the
same base CSS, the same header hero, the same KPI strip style, and the
same footer.

The helpers below are deliberately pure-string so they stay cheap to call
and printable to PDF via wkhtmltopdf / WeasyPrint / the browser ``Print``
dialog. CSS variables mirror the design tokens in the design system.
"""
from __future__ import annotations

import html

from typing import Any, Iterable


SDG_COLORS: dict[int, str] = {
    1: "#E5243B", 2: "#DDA63A", 3: "#4C9F38", 4: "#C5192D", 5: "#FF3A21",
    6: "#26BDE2", 7: "#FCC30B", 8: "#A21942", 9: "#FD6925", 10: "#DD1367",
    11: "#FD9D24", 12: "#BF8B2E", 13: "#3F7E44", 14: "#0A97D9",
    15: "#56C02B", 16: "#00689D", 17: "#19486A",
}

# Human-readable grade -> colour class
GRADE_CLASS: dict[str, str] = {
    "A+": "grade-A", "A": "grade-A", "A-": "grade-A",
    "B+": "grade-B", "B": "grade-B", "B-": "grade-B",
    "C+": "grade-C", "C": "grade-C", "C-": "grade-C",
    "D+": "grade-D", "D": "grade-D", "D-": "grade-D",
    "F": "grade-F",
}


REPORT_CSS_V2 = r"""
/* v7 W2.1: the v2 deliverables (IC memo, DD report, investee portal) alias
   their variable names onto the shared design tokens (design/tokens.css), so
   every deliverable shares one palette, light/dark behaviour and type. */
:root {
  --primary: var(--brand); --primary-light: var(--surface-2); --primary-dark: var(--brand);
  --accent: var(--series-1); --accent-light: var(--series-1-wash);
  --success: var(--good); --success-light: var(--good-wash); --success-dark: var(--good-ink);
  /* --warning itself comes from tokens.css; aliasing it to itself made it invalid. */
  --warning-light: var(--warning-wash); --warning-dark: var(--warning-ink);
  --danger: var(--critical-ink); --danger-light: var(--critical-wash); --danger-dark: var(--critical-ink);
  --neutral: var(--ink-2); --neutral-light: var(--surface-2);
  --bg: var(--page);
  --text: var(--ink); --text-secondary: var(--ink-2); --text-muted: var(--muted);
  --border-strong: var(--axis);
  --shadow-sm: none; --shadow-md: none; --shadow-lg: none;
  --radius-pill: 9999px;
  --font-sans: var(--font);
  --font-mono: var(--mono);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: var(--font-sans); color: var(--text); background: var(--bg);
  line-height: 1.55; -webkit-font-smoothing: antialiased;
  font-feature-settings: "cv11","ss01","ss03"; text-rendering: optimizeLegibility;
}
.page {
  max-width: 1200px; margin: 0 auto; padding: 32px 24px 64px;
  display: grid; grid-template-columns: 220px 1fr; gap: 28px;
}
@media(max-width: 900px){ .page { grid-template-columns: 1fr; } aside.toc { display: none; } }

/* ---------- Sticky Table of Contents ---------- */
aside.toc {
  position: sticky; top: 24px; align-self: start;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 18px 16px; box-shadow: var(--shadow-sm); font-size: 0.85em;
}
aside.toc h4 {
  font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--text-muted); margin-bottom: 10px; font-weight: 700;
}
aside.toc a {
  display: block; color: var(--text-secondary); text-decoration: none;
  padding: 6px 10px; border-radius: var(--radius-sm); margin: 2px 0;
  border-left: 2px solid transparent; transition: all 0.15s;
}
aside.toc a:hover, aside.toc a.active {
  color: var(--primary); background: var(--primary-light); border-left-color: var(--primary);
}
main, .memo-main { min-width: 0; }

/* ---------- Header (masthead, same as the decision report) ---------- */
.report-hero {
  background: var(--surface); color: var(--ink); padding: 24px 28px;
  border: 1px solid var(--border); border-bottom: 3px solid var(--brand);
  border-radius: var(--radius); margin-bottom: 24px;
}
.report-hero .eyebrow {
  text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.78em;
  color: var(--ink-2); margin-bottom: 6px; font-weight: 600;
}
.report-hero h1 { font-size: 1.9em; font-weight: 750; margin-bottom: 8px; line-height: 1.15; }
.report-hero .subtitle { color: var(--ink); font-size: 0.98em; max-width: 70ch; }
.report-hero .meta-row {
  display: flex; gap: 20px; flex-wrap: wrap; margin-top: 14px; color: var(--ink-2); font-size: 0.85em;
}
.report-hero .meta-row b { font-weight: 600; color: var(--ink); }
.tag-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.tag {
  display: inline-block; background: var(--surface-2); color: var(--ink-2);
  border: 1px solid var(--border);
  padding: 3px 11px; border-radius: var(--radius-pill); font-size: 0.78em; font-weight: 500;
}

.tag.sdg-tag { display: inline-flex; align-items: center; gap: 6px; }
/* Wide tables scroll inside themselves on phones instead of widening the page. */
@media (max-width: 760px) {
  table.data, section.card table { display: block; max-width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
}
.sdg-dot { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
@media print { .sdg-dot { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }

/* ---------- KPI strip ---------- */
.kpi-strip {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px; margin: 20px 0 30px;
}
.kpi-tile {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 18px 20px 16px;
  box-shadow: var(--shadow-sm); position: relative; overflow: hidden;
}
.kpi-tile::before {
  /* A coloured edge only when the tile carries a status (pass / warn / fail). */
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: transparent;
}
.kpi-tile.pass::before { background: var(--success); }
.kpi-tile.warn::before { background: var(--warning); }
.kpi-tile.fail::before, .kpi-tile.bad::before { background: var(--danger); }
.kpi-tile .kpi-label {
  font-size: 0.72em; color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.08em; font-weight: 600; margin-bottom: 8px;
}
.kpi-tile .kpi-value { font-size: 1.7em; font-weight: 750; line-height: 1.05; color: var(--text); overflow-wrap: anywhere; }
.kpi-tile .kpi-sub { font-size: 0.78em; color: var(--text-secondary); margin-top: 6px; }
.kpi-tile .kpi-badge {
  display: inline-block; padding: 2px 10px; border-radius: var(--radius-pill);
  font-size: 0.68em; font-weight: 700; text-transform: uppercase;
}
.kpi-badge.pass { background: var(--success-light); color: var(--success-dark); }
.kpi-badge.warn { background: var(--warning-light); color: var(--warning-dark); }
.kpi-badge.fail { background: var(--danger-light);  color: var(--danger-dark); }
.kpi-badge.neutral { background: var(--neutral-light); color: var(--neutral); }

/* ---------- Sections ---------- */
section.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px 28px;
  margin: 22px 0; box-shadow: var(--shadow-sm);
}
h2.section-title {
  color: var(--text); font-size: 1.25em; font-weight: 700;
  margin-bottom: 6px; display: flex; align-items: center; gap: 10px;
}
h2.section-title::before {
  content: ""; width: 4px; height: 22px; background: var(--primary);
  border-radius: 2px;
}
.section-lede {
  color: var(--text-secondary); font-size: 0.92em; margin-bottom: 18px;
}
h3 { color: var(--text); font-size: 1.02em; margin: 18px 0 8px; font-weight: 650; }

/* ---------- Score / grade cards ---------- */
.cards-row { display: flex; gap: 14px; flex-wrap: wrap; margin: 14px 0; }
.score-card {
  flex: 0 0 auto; background: var(--neutral-light);
  border-radius: var(--radius); padding: 18px 24px; text-align: center;
  border: 1px solid var(--border); min-width: 120px;
}
.score-card .value { font-size: 2.2em; font-weight: 750; line-height: 1.05; color: var(--text); }
.score-card .label {
  font-size: 0.72em; color: var(--text-muted); margin-top: 6px;
  text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600;
}
/* Grades are text: they wear the ink tokens (AA contrast in light and dark), never fill colours. */
.grade-A, .grade-B { color: var(--good-ink); }
.grade-C { color: var(--warning-ink); }
.grade-D { color: var(--serious-ink); }
.grade-F { color: var(--critical-ink); }

/* ---------- Tables ---------- */
table.data {
  border-collapse: collapse; width: 100%; margin: 12px 0;
  background: var(--surface); border-radius: var(--radius-sm);
  overflow: hidden; border: 1px solid var(--border); font-size: 0.9em;
}
table.data th {
  background: var(--neutral-light); color: var(--text);
  font-weight: 650; padding: 10px 14px; text-align: left;
  text-transform: uppercase; font-size: 0.72em; letter-spacing: 0.06em;
  border-bottom: 1px solid var(--border);
}
table.data td { border-bottom: 1px solid var(--border); padding: 10px 14px; }
table.data tbody tr:last-child td { border-bottom: none; }
table.data tbody tr:hover td { background: var(--primary-light); }

/* ---------- Progress bars ---------- */
.bar-track {
  background: var(--border); border-radius: 999px; height: 8px; width: 100%; overflow: hidden;
}
/* Flat fills from the status / brand tokens (no gradients: they read as decoration). */
.bar-fill { height: 100%; border-radius: 999px; transition: width 0.4s ease; }
.bar-fill.blue, .bar-fill.coverage { background: var(--primary); }
.bar-fill.green  { background: var(--success); }
.bar-fill.orange { background: var(--warning); }
.bar-fill.red    { background: var(--danger); }

/* ---------- Status pills ---------- */
.pill {
  display: inline-block; padding: 3px 10px; border-radius: var(--radius-pill);
  font-size: 0.72em; font-weight: 650; text-transform: uppercase; letter-spacing: 0.04em;
  white-space: nowrap;
}
.pill.pass { background: var(--success-light); color: var(--success-dark); }
.pill.warn { background: var(--warning-light); color: var(--warning-dark); }
.pill.fail { background: var(--danger-light);  color: var(--danger-dark); }
.pill.na   { background: var(--neutral-light); color: var(--neutral); }

/* ---------- Callouts ---------- */
.callout {
  border-left: 4px solid var(--primary); background: var(--primary-light);
  padding: 14px 18px; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  margin: 10px 0; font-size: 0.9em; color: var(--text);
}
.callout.warn   { border-color: var(--warning); background: var(--warning-light); }
.callout.danger { border-color: var(--danger);  background: var(--danger-light); }
.callout.ok     { border-color: var(--success); background: var(--success-light); }
.callout ul, .callout ol { margin: 6px 0 0; padding-left: 1.25em; }
.callout li { margin: 2px 0; }

/* ---------- Footer ---------- */
.footer {
  margin-top: 40px; padding: 18px 0; border-top: 1px solid var(--border);
  color: var(--text-muted); font-size: 0.8em; text-align: center;
}
.footer a { color: var(--link); text-decoration: underline; }
.footer a:hover { text-decoration: underline; }

/* ---------- Accessibility (WCAG 2.2 AA) ---------- */
.skip-link {
  position: absolute; left: -9999px; top: 0; z-index: 1000;
  background: var(--primary); color: var(--brand-ink); padding: 10px 16px;
  border-radius: 0 0 var(--radius-sm) 0; font-weight: 600; text-decoration: none;
}
.skip-link:focus { left: 0; }
a:focus-visible, button:focus-visible, [tabindex]:focus-visible,
summary:focus-visible, .toc a:focus-visible {
  outline: 3px solid var(--accent); outline-offset: 2px; border-radius: 3px;
}
.visually-hidden {
  position: absolute !important; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important; scroll-behavior: auto !important;
  }
}

/* ---------- Evidence-provenance badges (Track D3) ---------- */
.evidence-badge {
  display: inline-flex; align-items: center; gap: 5px; vertical-align: middle;
  padding: 2px 9px; border-radius: var(--radius-pill);
  font-size: 0.7em; font-weight: 650; letter-spacing: 0.02em;
  border: 1px solid var(--border-strong); background: var(--neutral-light);
  color: var(--text-secondary); text-decoration: none;
}
.evidence-badge::before {
  content: ""; width: 7px; height: 7px; border-radius: 50%;
  background: var(--neutral); flex: 0 0 auto;
}
.evidence-badge.verified { background: var(--success-light); color: var(--success-dark); border-color: var(--success); }
.evidence-badge.verified::before { background: var(--success); }
.evidence-badge.reported { background: var(--primary-light); color: var(--primary-dark); border-color: var(--accent); }
.evidence-badge.reported::before { background: var(--accent); }
.evidence-badge.estimated, .evidence-badge.proxy { background: var(--warning-light); color: var(--warning-dark); border-color: var(--warning); }
.evidence-badge.estimated::before, .evidence-badge.proxy::before { background: var(--warning); }
.evidence-badge.unverified, .evidence-badge.suggested { background: var(--danger-light); color: var(--danger-dark); border-color: var(--danger); }
.evidence-badge.unverified::before, .evidence-badge.suggested::before { background: var(--danger); }
.evidence-legend { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 10px 0; font-size: 0.86em; }
.evidence-legend .ev-title { font-weight: 650; color: var(--text-secondary); }

/* Dark mode comes from design/tokens.css (prefers-color-scheme, or
   data-theme="dark" on <html> when a report is rendered with theme="dark"). */

/* ---------- Print ---------- */
@media print {
  body { background: white; }
  .page { display: block; max-width: 100%; padding: 0; }
  aside.toc { display: none; }
  .skip-link { display: none; }
  .report-hero { border-color: #ccc; }
  section.card { box-shadow: none; border: 1px solid #ccc; break-inside: avoid; page-break-inside: avoid; }
  .kpi-tile { box-shadow: none; break-inside: avoid; }
  h2.section-title { break-after: avoid; }
}
"""


def render_hero(
    *,
    eyebrow: str,
    title: str,
    subtitle: str = "",
    meta: Iterable[tuple[str, str]] = (),
    tags: Iterable[str] = (),
) -> str:
    """Render the top hero block.

    ``meta`` is a list of (label, value) tuples. ``tags`` is a list of
    short strings displayed as pills (impact themes, SDG numbers, …).

    ``title`` / ``subtitle`` / ``eyebrow`` may carry intentional markup, so
    callers escape those; ``tags`` and ``meta`` are plain user-derived strings
    (impact themes, company facts) and are escaped here.
    """
    from html import escape as _escape

    tag_items = "".join(f'<span class="tag">{_escape(str(t))}</span>' for t in tags)
    tag_row = f'<div class="tag-row">{tag_items}</div>' if tag_items else ""
    meta_items = "".join(
        f"<span><b>{_escape(str(k))}:</b> {_escape(str(v))}</span>" for k, v in meta
    )
    meta_row = f'<div class="meta-row">{meta_items}</div>' if meta_items else ""
    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    return (
        f'<div class="report-hero">'
        f'  <div class="eyebrow">{eyebrow}</div>'
        f'  <h1>{title}</h1>'
        f'  {subtitle_html}'
        f'  {meta_row}'
        f'  {tag_row}'
        f'</div>'
    )


def render_kpi_strip(kpis: list[dict[str, Any]]) -> str:
    """Render a grid of KPI tiles.

    Each dict may include ``label`` (required), ``value`` (required),
    ``sub`` (sub-label under the number), ``badge`` (pill text),
    ``badge_kind`` (``pass`` / ``warn`` / ``fail`` / ``neutral``), and
    ``kind`` (tile accent: ``pass`` / ``warn`` / ``fail`` / ``neutral``).
    """
    if not kpis:
        return ""
    tiles: list[str] = []
    for k in kpis:
        kind = k.get("kind", "")
        badge_html = ""
        if k.get("badge"):
            bk = k.get("badge_kind", "neutral")
            badge_html = f' <span class="kpi-badge {bk}">{k["badge"]}</span>'
        sub_html = f'<div class="kpi-sub">{k["sub"]}</div>' if k.get("sub") else ""
        tiles.append(
            f'<div class="kpi-tile {kind}">'
            f'  <div class="kpi-label">{k["label"]}{badge_html}</div>'
            f'  <div class="kpi-value">{k["value"]}</div>'
            f'  {sub_html}'
            f'</div>'
        )
    return f'<div class="kpi-strip">{"".join(tiles)}</div>'


def render_toc(sections: list[tuple[str, str]]) -> str:
    """Render a sticky table-of-contents aside from (anchor_id, label) tuples."""
    if not sections:
        return ""
    items = "".join(f'<a href="#{sid}">{label}</a>' for sid, label in sections)
    return f'<aside class="toc"><h4>On this page</h4>{items}</aside>'


def render_footer(note: str | None = None, *, ai_disclosure: str | None = None) -> str:
    """Shared footer. Always carries an AI / automation disclosure (EU AI Act Art 50)."""
    from html import escape

    from impact_vision.impact.ai_provenance import GENERIC_DISCLOSURE

    note_html = f"<br><span>{note}</span>" if note else ""
    ai_html = f'<br><span class="ai-disclosure">{escape(ai_disclosure or GENERIC_DISCLOSURE)}</span>'
    return (
        f'<div class="footer">'
        f'Generated by <a href="https://github.com/joejoe168168/impact-vision">Impact Vision</a>'
        f' — open-source impact measurement.{note_html}{ai_html}'
        f'</div>'
    )


EVIDENCE_BADGE_KINDS = {"verified", "reported", "estimated", "proxy", "unverified", "suggested"}

# Default human-readable labels for each provenance kind.
_EVIDENCE_LABELS: dict[str, str] = {
    "verified": "Verified",
    "reported": "Reported",
    "estimated": "Estimated",
    "proxy": "Proxy",
    "unverified": "Unverified",
    "suggested": "Suggested",
}


def render_provenance_badge(
    kind: str,
    *,
    label: str | None = None,
    source: str = "",
    confidence: str = "",
) -> str:
    """Render an inline evidence-provenance badge (Track D3).

    ``kind`` is one of ``verified`` / ``reported`` / ``estimated`` / ``proxy`` /
    ``unverified`` / ``suggested``. ``source`` and ``confidence`` are surfaced as
    an accessible ``title`` tooltip so an LP or verifier can see, at a glance,
    where a number came from and how trustworthy it is.
    """
    k = kind.strip().lower()
    if k not in EVIDENCE_BADGE_KINDS:
        k = "unverified"
    text = label or _EVIDENCE_LABELS.get(k, k.title())
    tip_parts = [_EVIDENCE_LABELS.get(k, k.title())]
    if source:
        tip_parts.append(f"source: {source}")
    if confidence:
        tip_parts.append(f"confidence: {confidence}")
    title = " · ".join(tip_parts)
    return (
        f'<span class="evidence-badge {k}" title="{title}" '
        f'role="img" aria-label="Evidence: {title}">{text}</span>'
    )


def render_evidence_legend(kinds: Iterable[str] | None = None) -> str:
    """Render a legend explaining the evidence-provenance badges."""
    selected = list(kinds) if kinds is not None else [
        "verified", "reported", "estimated", "unverified",
    ]
    badges = "".join(render_provenance_badge(k) for k in selected)
    return (
        '<div class="evidence-legend">'
        '<span class="ev-title">Evidence provenance:</span>'
        f'{badges}'
        '</div>'
    )


def wrap_document(
    *,
    title: str,
    body_html: str,
    extra_head: str = "",
    include_plotly: bool = False,
    theme: str = "",
) -> str:
    """Return a complete self-contained HTML document with the shared CSS.

    Adds a skip link and a ``<main>`` landmark for keyboard / screen-reader
    accessibility (WCAG 2.2 AA). ``theme="dark"`` opts into the dark palette.
    """
    plotly = (
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        if include_plotly else ""
    )
    dark = theme.strip().lower() == "dark"
    # Keep the legacy class for any custom CSS, but drive colours from tokens.
    body_class = ' class="theme-dark"' if dark else ""
    from impact_vision.impact.report_templates.decision_report import design_tokens_css

    html_open = '<html lang="en" data-theme="dark"><head>' if dark else '<html lang="en"><head>'
    return (
        '<!DOCTYPE html>'
        f'{html_open}'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{html.escape(title, quote=False)}</title>'
        f'{plotly}'
        f'<style>{design_tokens_css()}\n{REPORT_CSS_V2}</style>'
        f'{extra_head}'
        f'</head><body{body_class}>'
        '<a class="skip-link" href="#main-content">Skip to main content</a>'
        '<main id="main-content" tabindex="-1">'
        f'{body_html}'
        '</main>'
        '</body></html>'
    )


def _luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def sdg_text_colour(goal: int) -> str:
    """Ink that clears contrast on the official SDG colour (white fails on 2, 6, 7, 11, 12, 15)."""
    lum = _luminance(SDG_COLORS.get(goal, "#666666"))
    return "#ffffff" if (1.05 / (lum + 0.05)) >= (lum + 0.05) / 0.05 else "#0b0b0b"


def sdg_swatch(goal: int, score: float | None = None) -> str:
    """Small pill showing SDG number in the official UN colour."""
    colour = SDG_COLORS.get(goal, "#666")
    score_suffix = f" · {score:.0f}/100" if score is not None else ""
    return (
        '<span class="tag sdg-tag">'
        f'<span class="sdg-dot" style="background:{colour}" aria-hidden="true"></span>'
        f'SDG {goal}{score_suffix}</span>'
    )
