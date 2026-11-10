"""F3: IC one-pager. One printed A4 page for the committee pack.

Built from :func:`decision_report.build_view`, so every number is the one in
the impact report. Fixed A4 layout; text is clamped so it cannot overflow.
"""

from __future__ import annotations

from html import escape as e
from typing import Any

# Labels come from the shared string table (design/strings.py, keys ``op_*``,
# ``cond_*``, ``eq_title``, ``impact_*``) so en, zh-HK and zh-CN match the other deliverables.
_KEYS = {"title": "op_title", "impact": "op_impact", "reasons": "op_reasons", "conditions": "op_conditions",
         "negative": "op_negative", "control": "op_control", "no_control": "op_no_control",
         "evidence": "eq_title", "none": "op_none"}


def _headings(lang: str) -> dict[str, str]:
    from impact_vision.impact.report_templates.design.strings import translator

    t = translator(lang)
    return {**{name: t(key) for name, key in _KEYS.items()}, "range": "P10–P90",
            "kind_people": t("impact_people"), "kind_climate": t("impact_climate")}


_TONES = {"good": "#1a7f4b", "warning": "#a15c00", "serious": "#a15c00", "critical": "#b3261e", "neutral": "#444c56"}

_CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font: 10.5pt/1.35 system-ui, -apple-system, "Segoe UI", "Noto Sans CJK TC", "PingFang HK", sans-serif;
       color: #1c2128; background: #fff; }
.page { width: 210mm; max-width: 100%; min-height: 297mm; margin: 0 auto; padding: 14mm 15mm 12mm;
        display: flex; flex-direction: column; gap: 5mm; overflow-wrap: anywhere; }
@media screen and (max-width: 210mm) {
  .page { width: auto; min-height: 0; padding: 6mm 5mm; } .grid { grid-template-columns: 1fr; }
  header { flex-wrap: wrap; gap: 2mm; }
}
@media print {
  .page { width: 210mm; height: 297mm; min-height: 0; margin: 0; overflow: hidden;
          page-break-after: avoid; break-after: avoid; }
}
header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1.5pt solid #1c2128;
         padding-bottom: 2mm; }
h1 { font-size: 17pt; margin: 0; } h2 { font-size: 9pt; letter-spacing: .06em; text-transform: uppercase;
     margin: 0 0 1.5mm; color: #57606a; }
.meta { font-size: 9pt; color: #57606a; }
.verdict { border-left: 4pt solid var(--tone); padding: 2mm 4mm; background: #f6f8fa; }
.verdict strong { font-size: 15pt; color: var(--tone); display: block; }
.clamp1, .clamp2, .clamp3 { display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; }
.clamp1 { -webkit-line-clamp: 1; } .clamp2 { -webkit-line-clamp: 2; } .clamp3 { -webkit-line-clamp: 3; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }
ol, ul { margin: 0; padding-left: 5mm; } li { margin-bottom: 1.2mm; }
.outcome { margin-bottom: 3mm; } .outcome b { font-size: 14pt; }
.bar { position: relative; height: 3mm; background: #eaeef2; border-radius: 1.5mm; margin: 1mm 0; }
.bar i { position: absolute; top: 0; height: 100%; background: #8fb8de; border-radius: 1.5mm; }
.bar u { position: absolute; top: -0.7mm; width: 0.8mm; height: 4.4mm; background: #1c2128; }
small { color: #57606a; font-size: 8.5pt; }
footer { margin-top: auto; border-top: .5pt solid #d0d7de; padding-top: 2mm; font-size: 7.5pt; color: #57606a; }
"""


def _items(rows: list[str], empty: str, tag: str = "ol", clamp: int = 2) -> str:
    if not rows:
        return f"<p>{e(empty)}</p>"
    return f"<{tag}>" + "".join(f"<li><span class='clamp{clamp}'>{e(r)}</span></li>" for r in rows) + f"</{tag}>"


def _condition_text(c: Any, lang: str = "en") -> str:
    """"Covenant: …" — the type label translated, the text through the phrasebook (quotes stay verbatim)."""
    from impact_vision.impact.i18n_phrasebook import localize
    from impact_vision.impact.report_templates.design.strings import translator

    if isinstance(c, dict):
        text = localize(str(c.get("text") or c.get("condition") or c.get("action") or ""), lang)
        kind = str(c.get("type") or c.get("kind") or "")
        if kind:
            label = translator(lang)(f"cond_{kind}")
            kind = kind.replace("_", " ") if label == f"cond_{kind}" else label
        sep = "：" if lang.startswith("zh") else ": "
        return f"{kind}{sep}{text}" if kind and text else str(text or next(iter(c.values()), ""))
    return str(c)


def build_onepager(data: dict[str, Any], lang: str = "en", branding: dict[str, Any] | None = None) -> dict[str, Any]:
    """The one-pager's content, from the same view the impact report uses."""
    from impact_vision.impact.expected_impact import suggest_conditions
    from impact_vision.impact.i18n_phrasebook import localize
    from impact_vision.impact.report_templates.decision_report import build_view

    view = build_view(data, audience="ic", lang=lang, branding=branding)
    verdict = view.get("verdict") or {}
    impact = view.get("impact") or {}
    negatives = sorted((data.get("negative_impacts") or {}).get("items") or [], key=lambda i: -(i.get("score") or 0))
    reasons = list(verdict.get("reasons") or [])[:3]
    return {
        "lang": view["lang"],
        "company": view["company"],
        "generated": view["generated"],
        "verdict": {"label": verdict.get("label", ""), "tone": verdict.get("tone", "neutral"),
                    "note": verdict.get("note") or verdict.get("recommendation", "")},
        "outcomes": [{k: r[k] for k in ("kind", "unit", "p10", "p50", "p90", "bar", "spread")}
                     for r in (impact.get("rows") or [])[:2]],
        "reasons": reasons,
        "conditions": [_condition_text(c, view["lang"]) for c in suggest_conditions(data.get("expected_impact"))[:3]],
        "negative": ({"impact": localize(negatives[0].get("impact", ""), view["lang"]), "band": negatives[0].get("band", ""),
                      "controlled": bool(negatives[0].get("controlled"))} if negatives else None),
        "evidence_quality": impact.get("eq"),
        "stamp": view.get("methodology_label", ""),
        "ai_disclosure": (view.get("ai") or {}).get("disclosure", ""),
    }


def render_ic_onepager(data: dict[str, Any], lang: str = "en", branding: dict[str, Any] | None = None) -> str:
    """One A4 page: verdict, expected impact, three reasons, three conditions, top negative impact."""
    from impact_vision.impact.ai_provenance import (
        ai_provenance_for_report,
        machine_marking,
        mark_html,
    )

    p = build_onepager(data, lang, branding)
    h = _headings(p["lang"])
    tone = _TONES.get(p["verdict"]["tone"], _TONES["neutral"])
    outcomes = "".join(
        f"<div class='outcome'><b>{e(str(o['p50']))}</b> {e(str(o['unit']))} <small>· {e(h.get('kind_' + str(o['kind']), str(o['kind'])))}</small>"
        f"<div class='bar'><i style='left:{o['bar']['left']}%;width:{o['bar']['width']}%'></i>"
        f"<u style='left:{o['bar']['mid']}%'></u></div>"
        f"<small class='clamp1'>{h['range']}: {e(str(o['p10']))}–{e(str(o['p90']))} · {e(str(o['spread']))}</small></div>"
        for o in p["outcomes"]) or f"<p>{e(h['none'])}</p>"
    neg = p["negative"]
    negative = (f"<p class='clamp2'><strong>{e(neg['impact'])}</strong></p>"
                f"<small>{e(h['control'] if neg['controlled'] else h['no_control'])}</small>") if neg else f"<p>{e(h['none'])}</p>"
    eq = p["evidence_quality"]
    evidence = (f"<p><b>{e(str(eq['score']))}/100</b> <small class='clamp1'>{e(str(eq.get('sub') or eq.get('label', '')))}</small></p>"
                if eq else f"<p>{e(h['none'])}</p>")
    c = p["company"]
    meta = " · ".join(x for x in (c.get("sector"), c.get("geography"), p["generated"]) if x)
    body = (
        f"<!doctype html><html lang='{e(p['lang'])}'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{e(h['title'])} · {e(c['name'])}</title><style>{_CSS}</style></head><body>"
        f"<main class='page' style='--tone:{tone}'>"
        f"<header><h1 class='clamp1'>{e(c['name'])}</h1><span class='meta'>{e(h['title'])} · {e(meta)}</span></header>"
        f"<section class='verdict'><strong>{e(p['verdict']['label'])}</strong>"
        f"<span class='clamp2'>{e(p['verdict']['note'])}</span></section>"
        f"<section><h2>{e(h['impact'])}</h2>{outcomes}</section>"
        f"<div class='grid'><section><h2>{e(h['reasons'])}</h2>{_items(p['reasons'], h['none'], 'ul')}</section>"
        f"<section><h2>{e(h['conditions'])}</h2>{_items(p['conditions'], h['none'], 'ol', 3)}</section></div>"
        f"<div class='grid'><section><h2>{e(h['negative'])}</h2>{negative}</section>"
        f"<section><h2>{e(h['evidence'])}</h2>{evidence}</section></div>"
        f"<footer><div class='clamp1'>{e(p['stamp'])}</div><div class='clamp2'>{e(p['ai_disclosure'])}</div></footer>"
        f"</main></body></html>"
    )
    return mark_html(body, machine_marking(ai_provenance_for_report(data)))
