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
:root {
  --primary: #0d47a1; --primary-light: #e3f2fd; --primary-dark: #002171;
  --accent: #1976d2; --accent-light: #63a4ff;
  --success: #2e7d32; --success-light: #e8f5e9; --success-dark: #1b5e20;
  --warning: #f57c00; --warning-light: #fff3e0; --warning-dark: #e65100;
  --danger: #c62828;  --danger-light: #ffebee;  --danger-dark: #b71c1c;
  --neutral: #5f6368; --neutral-light: #f5f7fa;
  --surface: #ffffff; --bg: #f5f7fa;
  --text: #1a1a2e; --text-secondary: #5f6368; --text-muted: #9aa0a6;
  --border: #e0e4e8; --border-strong: #bdc1c6;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 10px 25px rgba(0,0,0,0.10);
  --radius: 14px; --radius-sm: 8px; --radius-pill: 9999px;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
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
main { min-width: 0; }

/* ---------- Header hero ---------- */
.report-hero {
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 55%, #4fc3f7 100%);
  color: white; padding: 40px 44px; border-radius: var(--radius);
  margin-bottom: 28px; box-shadow: var(--shadow-lg);
  position: relative; overflow: hidden;
}
.report-hero::after {
  content: ""; position: absolute; top: -40%; right: -10%;
  width: 380px; height: 380px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 65%);
  pointer-events: none;
}
.report-hero .eyebrow {
  text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.72em;
  opacity: 0.85; margin-bottom: 6px; font-weight: 600;
}
.report-hero h1 {
  font-size: 1.9em; font-weight: 750; margin-bottom: 8px;
  letter-spacing: -0.02em; line-height: 1.15;
}
.report-hero .subtitle { opacity: 0.92; font-size: 0.98em; max-width: 65ch; }
.report-hero .meta-row {
  display: flex; gap: 20px; flex-wrap: wrap; margin-top: 16px;
  opacity: 0.85; font-size: 0.82em;
}
.report-hero .meta-row b { font-weight: 600; opacity: 0.95; }
.tag-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.tag {
  display: inline-block; background: rgba(255,255,255,0.22);
  backdrop-filter: blur(6px);
  padding: 4px 12px; border-radius: var(--radius-pill); font-size: 0.78em; font-weight: 500;
}

/* ---------- KPI strip ---------- */
.kpi-strip {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px; margin: 20px 0 30px;
}
.kpi-tile {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 18px 20px 16px;
  box-shadow: var(--shadow-sm); position: relative; overflow: hidden;
}
.kpi-tile::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: var(--accent);
}
.kpi-tile.pass::before { background: var(--success); }
.kpi-tile.warn::before { background: var(--warning); }
.kpi-tile.fail::before, .kpi-tile.bad::before { background: var(--danger); }
.kpi-tile .kpi-label {
  font-size: 0.72em; color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.08em; font-weight: 600; margin-bottom: 8px;
}
.kpi-tile .kpi-value { font-size: 1.9em; font-weight: 750; line-height: 1.05; color: var(--text); }
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
.grade-A { color: var(--success); }
.grade-B { color: #558b2f; }
.grade-C { color: #f9a825; }
.grade-D { color: #e65100; }
.grade-F { color: var(--danger); }

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
  background: #eceff1; border-radius: 6px; height: 10px; width: 100%; overflow: hidden;
}
.bar-fill { height: 100%; border-radius: 6px; transition: width 0.4s ease; }
.bar-fill.blue   { background: linear-gradient(90deg, var(--accent), var(--accent-light)); }
.bar-fill.green  { background: linear-gradient(90deg, #43a047, #66bb6a); }
.bar-fill.orange { background: linear-gradient(90deg, #ef6c00, #ffa726); }
.bar-fill.red    { background: linear-gradient(90deg, var(--danger), #ef5350); }
.bar-fill.coverage { background: linear-gradient(90deg, var(--primary), var(--accent)); }

/* ---------- Status pills ---------- */
.pill {
  display: inline-block; padding: 3px 10px; border-radius: var(--radius-pill);
  font-size: 0.72em; font-weight: 650; text-transform: uppercase; letter-spacing: 0.04em;
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

/* ---------- Footer ---------- */
.footer {
  margin-top: 40px; padding: 18px 0; border-top: 1px solid var(--border);
  color: var(--text-muted); font-size: 0.8em; text-align: center;
}
.footer a { color: var(--accent); text-decoration: none; }
.footer a:hover { text-decoration: underline; }

/* ---------- Accessibility (WCAG 2.2 AA) ---------- */
.skip-link {
  position: absolute; left: -9999px; top: 0; z-index: 1000;
  background: var(--primary); color: #fff; padding: 10px 16px;
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

/* ---------- Dark mode + white-label opt-in (Track D7) ---------- */
.theme-dark {
  --surface: #1c2128; --bg: #0d1117; --text: #e6edf3;
  --text-secondary: #b6bec8; --text-muted: #8b949e;
  --border: #30363d; --border-strong: #454d56;
  --primary-light: #15304d; --neutral-light: #1b222b;
  --success-light: #12351d; --warning-light: #3a2a12; --danger-light: #3a1518;
}

/* ---------- Print ---------- */
@media print {
  body { background: white; }
  .page { display: block; max-width: 100%; padding: 0; }
  aside.toc { display: none; }
  .skip-link { display: none; }
  .report-hero { background: var(--primary) !important;
                 -webkit-print-color-adjust: exact; print-color-adjust: exact; }
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
    """
    tag_items = "".join(f'<span class="tag">{t}</span>' for t in tags)
    tag_row = f'<div class="tag-row">{tag_items}</div>' if tag_items else ""
    meta_items = "".join(f"<span><b>{k}:</b> {v}</span>" for k, v in meta)
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


def render_footer(note: str | None = None) -> str:
    note_html = f"<br><span>{note}</span>" if note else ""
    return (
        f'<div class="footer">'
        f'Generated by <a href="https://github.com/joejoe168168/impact-vision">Impact Vision</a>'
        f' — open-source impact measurement.{note_html}'
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
    body_class = ' class="theme-dark"' if theme.strip().lower() == "dark" else ""
    return (
        '<!DOCTYPE html>'
        '<html lang="en"><head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{title}</title>'
        f'{plotly}'
        f'<style>{REPORT_CSS_V2}</style>'
        f'{extra_head}'
        f'</head><body{body_class}>'
        '<a class="skip-link" href="#main-content">Skip to main content</a>'
        '<main id="main-content" tabindex="-1">'
        f'{body_html}'
        '</main>'
        '</body></html>'
    )


def sdg_swatch(goal: int, score: float | None = None) -> str:
    """Small pill showing SDG number in the official UN colour."""
    colour = SDG_COLORS.get(goal, "#666")
    score_suffix = f" · {score:.0f}/100" if score is not None else ""
    return (
        f'<span class="tag" style="background:{colour};color:#fff">'
        f'SDG {goal}{score_suffix}</span>'
    )
