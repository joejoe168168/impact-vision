"""Report template engine for Impact Vision.

Provides Jinja2-based HTML report generation as well as helpers
for CSV, JSON, and text output formats.
"""

from openharness.impact.report_templates.html_template import render_html_report

__all__ = ["render_html_report"]
