"""Single-file HTML renderer for the v6 portfolio report payload."""

from __future__ import annotations
import html
import json


def render_portfolio_report(payload: dict) -> str:
    data = json.dumps(payload, default=str).replace("</", "<\\/")
    rows = payload.get("sections", {}).get("shared_concept_comparison", [])
    table = "".join(
        f"<tr><td>{html.escape(str(row['concept_id']))}</td><td><pre>{html.escape(json.dumps({k: v for k, v in row.items() if k != 'concept_id'}, default=str))}</pre></td></tr>"
        for row in rows
    )
    context = payload.get("sections", {}).get("sdg_need_context", [])
    ribbons = "".join(
        f"<li><strong>{html.escape(str(item.get('company', '')))}</strong>: "
        f"{html.escape(str(item.get('summary', item.get('contexts', 'neutral context'))))}</li>"
        for item in context
    )
    return f"<!doctype html><html><head><meta charset='utf-8'><title>Portfolio Impact Report</title><style>body{{font-family:system-ui;margin:2rem}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:.5rem}}</style></head><body><h1>Portfolio Impact Report</h1><h2>SDG need context</h2><ul>{ribbons}</ul><h2>Comparable core</h2><table><tr><th>Concept</th><th>Companies</th></tr>{table}</table><script type='application/json' id='portfolio-data'>{data}</script></body></html>"


__all__ = ["render_portfolio_report"]
