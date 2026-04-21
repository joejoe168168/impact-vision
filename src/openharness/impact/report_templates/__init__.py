"""Report template engine for Impact Vision.

Provides Jinja2-based HTML report generation as well as helpers
for CSV, JSON, and text output formats.

The v2 templates (`report_v2`) add a shared CSS, sticky TOC, KPI strip
and print-first layout used by the full Impact Report, the IC memo HTML
renderer, and the DD coverage HTML renderer.
"""

from openharness.impact.report_templates.dd_report_html import (
    render_dd_questionnaire_docx,
    render_dd_questionnaire_html,
    render_dd_report_html,
    save_dd_questionnaire_html,
    save_dd_report_html,
)
from openharness.impact.report_templates.html_template import render_html_report
from openharness.impact.report_templates.report_v2 import (
    GRADE_CLASS,
    REPORT_CSS_V2,
    SDG_COLORS,
    render_footer,
    render_hero,
    render_kpi_strip,
    render_toc,
    sdg_swatch,
    wrap_document,
)

__all__ = [
    "render_html_report",
    "render_dd_questionnaire_html",
    "save_dd_questionnaire_html",
    "render_dd_questionnaire_docx",
    "render_dd_report_html",
    "save_dd_report_html",
    "REPORT_CSS_V2",
    "GRADE_CLASS",
    "SDG_COLORS",
    "render_hero",
    "render_kpi_strip",
    "render_toc",
    "render_footer",
    "sdg_swatch",
    "wrap_document",
]
