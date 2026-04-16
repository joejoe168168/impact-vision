"""Jinja2-based HTML report template engine for Impact Vision.

Wraps the existing HTML generation logic with a clean API and
externalizes CSS/layout into reusable components.
"""

from __future__ import annotations

from typing import Any

try:
    from jinja2 import Environment, BaseLoader
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


REPORT_CSS = """\
:root {
  --primary: #0d47a1; --primary-light: #e3f2fd; --primary-dark: #002171;
  --accent: #1976d2; --accent-light: #63a4ff;
  --success: #2e7d32; --success-light: #e8f5e9;
  --warning: #f57c00; --warning-light: #fff3e0;
  --danger: #c62828; --danger-light: #ffebee;
  --surface: #ffffff; --bg: #f5f7fa; --text: #1a1a2e; --text-secondary: #5f6368;
  --border: #e0e4e8; --shadow-sm: 0 1px 3px rgba(0,0,0,0.08); --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
  --radius: 12px; --radius-sm: 8px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1080px; margin: 0 auto; padding: 32px 24px; color: var(--text); background: var(--bg); line-height: 1.5; }
.report-header { background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%); color: white; padding: 36px 40px; border-radius: var(--radius); margin-bottom: 28px; box-shadow: var(--shadow-md); }
.report-header h1 { font-size: 1.75em; font-weight: 700; margin-bottom: 6px; letter-spacing: -0.02em; }
.report-header .subtitle { opacity: 0.9; font-size: 0.95em; }
.report-header .meta-row { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 12px; opacity: 0.85; font-size: 0.85em; }
.report-header .meta-row span { display: flex; align-items: center; gap: 4px; }
.tag-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.tag { display: inline-block; background: rgba(255,255,255,0.2); padding: 3px 12px; border-radius: 20px; font-size: 0.8em; }
h2 { color: var(--primary); font-size: 1.3em; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 2px solid var(--primary-light); font-weight: 600; }
h3 { color: var(--text); font-size: 1.05em; margin: 20px 0 10px; font-weight: 600; }
.cards-row { display: flex; gap: 16px; flex-wrap: wrap; margin: 16px 0; }
.score-card { flex: 0 0 auto; background: var(--surface); border-radius: var(--radius); box-shadow: var(--shadow-sm); padding: 20px 28px; text-align: center; border: 1px solid var(--border); min-width: 130px; }
.score-card .value { font-size: 2.2em; font-weight: 700; line-height: 1.1; }
.score-card .label { font-size: 0.8em; color: var(--text-secondary); margin-top: 6px; text-transform: uppercase; letter-spacing: 0.03em; }
.grade-A { color: var(--success); } .grade-B { color: #558b2f; } .grade-C { color: #f9a825; } .grade-D { color: #e65100; } .grade-F { color: var(--danger); }
.chart-row { display: flex; gap: 20px; flex-wrap: wrap; margin: 16px 0; }
.chart-box { flex: 1 1 420px; min-width: 0; background: var(--surface); border-radius: var(--radius); box-shadow: var(--shadow-sm); padding: 20px; border: 1px solid var(--border); overflow: hidden; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; background: var(--surface); border-radius: var(--radius-sm); overflow: hidden; box-shadow: var(--shadow-sm); font-size: 0.9em; }
th { background: var(--primary); color: white; font-weight: 600; padding: 12px 14px; text-align: left; text-transform: uppercase; font-size: 0.75em; letter-spacing: 0.05em; }
td { border-bottom: 1px solid var(--border); padding: 10px 14px; }
tr:hover td { background: var(--primary-light); }
.bar-track { background: #e8eaed; border-radius: 6px; height: 10px; width: 100%; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 6px; transition: width 0.4s ease; }
.bar-fill.blue { background: linear-gradient(90deg, var(--accent), var(--accent-light)); }
.bar-fill.green { background: linear-gradient(90deg, #43a047, #66bb6a); }
.bar-fill.orange { background: linear-gradient(90deg, #ef6c00, #ffa726); }
.bar-fill.red { background: linear-gradient(90deg, #c62828, #ef5350); }
.bar-fill.coverage { background: linear-gradient(90deg, var(--primary), var(--accent)); }
.rec { background: var(--warning-light); padding: 14px 18px; border-left: 4px solid var(--warning); margin: 8px 0; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; font-size: 0.9em; line-height: 1.6; }
.bm-delta.positive { color: var(--success); font-weight: 700; }
.bm-delta.negative { color: var(--danger); font-weight: 700; }
.bm-delta.neutral { color: var(--text-secondary); font-weight: 600; }
.coverage-hero { background: var(--surface); border-radius: var(--radius); box-shadow: var(--shadow-sm); padding: 24px 28px; border: 1px solid var(--border); margin: 16px 0; display: flex; align-items: center; gap: 20px; }
.coverage-hero .pct { font-size: 2.5em; font-weight: 800; color: var(--primary); line-height: 1; }
.coverage-hero .detail { flex: 1; }
.coverage-hero .bar-track { height: 14px; margin-top: 8px; }
.footer { margin-top: 48px; padding: 20px 0; border-top: 2px solid var(--border); color: var(--text-secondary); font-size: 0.8em; text-align: center; }
.footer a { color: var(--accent); text-decoration: none; }
@media(max-width: 700px) { .chart-row { flex-direction: column; } .chart-box { flex-basis: 100%; } }
"""

SDG_COLORS = {
    1: "#E5243B", 2: "#DDA63A", 3: "#4C9F38", 4: "#C5192D", 5: "#FF3A21",
    6: "#26BDE2", 7: "#FCC30B", 8: "#A21942", 9: "#FD6925", 10: "#DD1367",
    11: "#FD9D24", 12: "#BF8B2E", 13: "#3F7E44", 14: "#0A97D9", 15: "#56C02B",
    16: "#00689D", 17: "#19486A",
}

_HEADER_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Impact Report: {{ company_name }}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>{{ css }}</style>
{{ extra_css }}
</head>
<body>
<div class="report-header">
<h1>Impact Assessment Report</h1>
<p class="subtitle">{{ company_name }}{{ ' | ' + sector if sector else '' }}</p>
<div class="meta-row">
  <span>Generated: {{ generated_date }}</span>
  <span>Standard: {{ catalog_version }}</span>
</div>
{% if themes or sdg_claims %}
<div class="tag-row">
{% for t in themes %}<span class="tag">{{ t }}</span>{% endfor %}
{% for g in sdg_claims %}<span class="tag">SDG {{ g }}</span>{% endfor %}
</div>
{% endif %}
</div>
"""

_FOOTER_TEMPLATE = """\
<div class="footer">
  Generated by <a href="https://github.com/joejoe168168/impact-vision">Impact Vision</a> — Open-source impact measurement
</div>
</body>
</html>
"""


def _get_jinja_env() -> Any:
    """Get or create a Jinja2 environment."""
    if not HAS_JINJA2:
        return None
    return Environment(loader=BaseLoader(), autoescape=False)


def render_header(data: dict) -> str:
    """Render the HTML report header section."""
    company = data.get("company", {})
    env = _get_jinja_env()
    if env:
        template = env.from_string(_HEADER_TEMPLATE)
        return template.render(
            company_name=company.get("name", "Unknown"),
            sector=company.get("sector", ""),
            generated_date=data.get("generated_at", "")[:10],
            catalog_version=data.get("catalog_version", "IRIS+ 5.3c"),
            themes=company.get("impact_themes", []),
            sdg_claims=company.get("sdg_claims", []),
            css=REPORT_CSS,
            extra_css="",
        )
    return _render_header_fallback(data)


def render_footer() -> str:
    """Render the HTML report footer section."""
    env = _get_jinja_env()
    if env:
        template = env.from_string(_FOOTER_TEMPLATE)
        return template.render()
    return _FOOTER_TEMPLATE


def _render_header_fallback(data: dict) -> str:
    """Fallback string-format header when Jinja2 is not available."""
    company = data.get("company", {})
    name = company.get("name", "Unknown")
    sector = company.get("sector", "")
    date = data.get("generated_at", "")[:10]
    catalog = data.get("catalog_version", "IRIS+ 5.3c")

    tags = ""
    themes = company.get("impact_themes", [])
    sdg_claims = company.get("sdg_claims", [])
    if themes or sdg_claims:
        tag_items = "".join(f'<span class="tag">{t}</span>' for t in themes)
        tag_items += "".join(f'<span class="tag">SDG {g}</span>' for g in sdg_claims)
        tags = f'<div class="tag-row">{tag_items}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Impact Report: {name}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>{REPORT_CSS}</style>
</head>
<body>
<div class="report-header">
<h1>Impact Assessment Report</h1>
<p class="subtitle">{name}{' | ' + sector if sector else ''}</p>
<div class="meta-row">
  <span>Generated: {date}</span>
  <span>Standard: {catalog}</span>
</div>
{tags}
</div>
"""


def render_html_report(data: dict) -> str:
    """Render a complete HTML impact report from assessment data.

    This is the main entry point for report generation. It delegates to
    the existing _to_html logic in impact_report_tool.py for backward
    compatibility while providing a clean API.

    Args:
        data: Assessment data dict with keys like 'company', 'five_dimensions',
              'sdg_alignments', 'gap_analysis', 'greenwashing', etc.

    Returns:
        Complete HTML string.
    """
    from openharness.tools.impact.impact_report_tool import _to_html
    return _to_html(data)


def get_css() -> str:
    """Get the shared CSS for Impact Vision reports."""
    return REPORT_CSS


def get_sdg_colors() -> dict[int, str]:
    """Get the SDG goal color mapping."""
    return SDG_COLORS.copy()
