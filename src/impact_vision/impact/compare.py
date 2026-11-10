"""F2: deal comparison. Two or more assessments side by side, on what an IC weighs.

No composite score and no "winner". Expected impact is shown per outcome kind
and never summed or ranked across kinds; where the P10–P90 ranges of two deals
overlap, the table says they cannot be told apart.
"""

from __future__ import annotations

from html import escape
from itertools import combinations
from typing import Any

_ASK_FIELDS = ("investment_ask_usd", "ask_usd", "investment_ask", "investment_amount", "investment_size_usd")


def _ask_usd(company: Any) -> float | None:
    for name in _ASK_FIELDS:
        value = getattr(company, name, None)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _column(bundle: Any) -> dict[str, Any]:
    data = bundle.report_data
    v2 = data.get("expected_impact") or {}
    gate = v2.get("gate") or {}
    ask = _ask_usd(bundle.company)
    outcomes: dict[str, dict[str, Any]] = {}
    for o in v2.get("outcomes") or []:
        kind = o.get("kind", "")
        if not kind or kind in outcomes:  # the first outcome of a kind is the headline for it
            continue
        row = {k: o.get(k) for k in ("unit", "stakeholder", "p10", "p50", "p90", "uncertainty", "evidence_level")}
        row["p50_per_usd_1m"] = round(o["p50"] / (ask / 1e6), 2) if ask and o.get("p50") is not None else None
        outcomes[kind] = row
    negatives = sorted((data.get("negative_impacts") or {}).get("items") or [],
                       key=lambda i: -(i.get("score") or 0))
    top = negatives[0] if negatives else None
    eq = v2.get("evidence_quality") or {}
    gw = bundle.greenwashing
    return {
        "company": bundle.company.name,
        "sector": bundle.company.sector,
        "gate": gate.get("label") or getattr(bundle.scorecard, "display_status", ""),
        "gate_state": gate.get("state", ""),
        "ask_usd": ask,
        "outcomes": outcomes,
        "evidence_quality": {"score": eq.get("score"), "label": eq.get("label")},
        "greenwashing": {"score": getattr(gw, "overall_score", None),
                         "classification": getattr(gw, "classification", "")},
        "top_negative_impact": ({"impact": top.get("impact"), "band": top.get("band"),
                                 "controlled": bool(top.get("controlled"))} if top else None),
        "open_plan_items": [p.get("action", "") for p in gate.get("plan") or []],
    }


def _overlaps(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a["p10"] <= b["p90"] and b["p10"] <= a["p90"]


def compare_bundles(bundles: list[Any]) -> dict[str, Any]:
    """One column per deal, plus range-overlap notes per outcome kind. No composite, no winner."""
    if len(bundles) < 2:
        raise ValueError("compare needs at least two assessments")
    deals = [_column(b) for b in bundles]
    kinds: list[str] = []
    for d in deals:
        kinds.extend(k for k in d["outcomes"] if k not in kinds)
    notes: list[dict[str, Any]] = []
    for kind in kinds:
        have = [d for d in deals if kind in d["outcomes"]
                and None not in (d["outcomes"][kind]["p10"], d["outcomes"][kind]["p90"])]
        if len(have) < 2:
            if len(have) == 1 and len(deals) > 1:
                notes.append({"kind": kind, "deals": [have[0]["company"]], "overlap": None,
                              "text": f"{kind}: only {have[0]['company']} has an estimate; "
                                      "it is not ranked against other outcome kinds."})
            continue
        for a, b in combinations(have, 2):
            oa, ob = a["outcomes"][kind], b["outcomes"][kind]
            if oa.get("unit") != ob.get("unit"):
                notes.append({"kind": kind, "deals": [a["company"], b["company"]], "overlap": None,
                              "text": f"{kind}: {a['company']} and {b['company']} use different units; not compared."})
                continue
            overlap = _overlaps(oa, ob)
            if overlap:
                text = (f"{kind}: the P10–P90 ranges of {a['company']} and {b['company']} overlap; "
                        "they cannot be told apart.")
            else:
                hi, lo = (a, b) if oa["p10"] > ob["p90"] else (b, a)
                text = (f"{kind}: the whole range of {hi['company']} is above the range of {lo['company']}.")
            notes.append({"kind": kind, "deals": [a["company"], b["company"]], "overlap": overlap, "text": text})
    return {"deals": deals, "outcome_kinds": kinds, "notes": notes}


def _num(value: Any) -> str:
    if value is None:
        return "–"
    value = float(value)
    return f"{value:,.0f}" if abs(value) >= 100 else f"{value:,.1f}"


def format_comparison(comparison: dict[str, Any]) -> str:
    """Plain-text table for the terminal."""
    deals = comparison["deals"]
    rows: list[tuple[str, list[str]]] = [
        ("Verdict", [str(d["gate"]) for d in deals]),
        ("Evidence quality", [f"{d['evidence_quality']['score']}/100" if d["evidence_quality"]["score"] is not None
                              else "–" for d in deals]),
        ("Greenwashing risk", [f"{_num(d['greenwashing']['score'])} ({d['greenwashing']['classification']})"
                               for d in deals]),
    ]
    for kind in comparison["outcome_kinds"]:
        cells = []
        for d in deals:
            o = d["outcomes"].get(kind)
            cells.append(f"{_num(o['p50'])} ({_num(o['p10'])}–{_num(o['p90'])}) {o['unit']}" if o else "–")
        rows.append((f"Expected impact: {kind}", cells))
    rows.append(("Top negative impact", [
        (f"{d['top_negative_impact']['impact']} "
         f"[{'control described' if d['top_negative_impact']['controlled'] else 'no control described'}]")
        if d["top_negative_impact"] else "–" for d in deals]))
    rows.append(("Open plan items", [str(len(d["open_plan_items"])) for d in deals]))
    lines = []
    for i, d in enumerate(deals):
        lines.append(f"[{i + 1}] {d['company']}")
    for label, cells in rows:
        lines.append(f"\n{label}")
        lines.extend(f"  [{i + 1}] {c}" for i, c in enumerate(cells))
    if comparison["notes"]:
        lines.append("\nRanges")
        lines.extend(f"  - {n['text']}" for n in comparison["notes"])
    return "\n".join(lines)


def render_comparison_html(comparison: dict[str, Any]) -> str:
    """Self-contained HTML table through the design system's CSS."""
    from impact_vision.impact.report_templates.decision_report import design_css

    deals = comparison["deals"]
    e = escape

    def row(label: str, cells: list[str]) -> str:
        return f"<tr><th scope='row'>{e(label)}</th>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    body = [row("Verdict", [f"<strong>{e(str(d['gate']))}</strong>" for d in deals])]
    for kind in comparison["outcome_kinds"]:
        cells = []
        for d in deals:
            o = d["outcomes"].get(kind)
            if not o:
                cells.append("–")
                continue
            per = f"<br><small>{_num(o['p50_per_usd_1m'])} per US$1m</small>" if o.get("p50_per_usd_1m") else ""
            cells.append(f"<strong>{_num(o['p50'])}</strong> {e(str(o['unit']))}"
                         f"<br><small>P10–P90: {_num(o['p10'])}–{_num(o['p90'])}</small>{per}")
        body.append(row(f"Expected impact: {kind}", cells))
    body.append(row("Evidence quality", [
        f"{d['evidence_quality']['score']}/100 · {e(str(d['evidence_quality']['label'] or ''))}"
        if d["evidence_quality"]["score"] is not None else "–" for d in deals]))
    body.append(row("Greenwashing risk", [
        f"{_num(d['greenwashing']['score'])} · {e(str(d['greenwashing']['classification']))}" for d in deals]))
    body.append(row("Top negative impact", [
        (f"{e(str(d['top_negative_impact']['impact']))}<br><small>"
         f"{'Control described' if d['top_negative_impact']['controlled'] else 'No control described'}</small>")
        if d["top_negative_impact"] else "–" for d in deals]))
    body.append(row("Open plan items", [
        ("<ol>" + "".join(f"<li>{e(a)}</li>" for a in d["open_plan_items"][:3]) + "</ol>"
         + (f"<small>+{len(d['open_plan_items']) - 3} more</small>" if len(d["open_plan_items"]) > 3 else ""))
        if d["open_plan_items"] else "None" for d in deals]))
    head = "<tr><td></td>" + "".join(
        f"<th scope='col'>{e(d['company'])}<br><small>{e(str(d['sector'] or ''))}</small></th>" for d in deals) + "</tr>"
    notes = "".join(f"<li>{e(n['text'])}</li>" for n in comparison["notes"])
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Deal comparison</title><style>" + design_css() +
        ".cmp{max-width:1100px;margin:2rem auto;padding:0 1rem}"
        ".cmp table{width:100%;border-collapse:collapse;table-layout:fixed}"
        ".cmp th,.cmp td{padding:.6rem .7rem;border-bottom:1px solid #d9dde3;text-align:left;vertical-align:top}"
        ".cmp ol{margin:0;padding-left:1.1rem}</style></head><body><main class='cmp'>"
        "<h1>Deal comparison</h1>"
        "<p>Side by side, with no composite score and no ranking. Expected impact is shown per outcome kind; "
        "different kinds are not compared with each other.</p>"
        f"<table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"
        + (f"<h2>Can the ranges be told apart?</h2><ul>{notes}</ul>" if notes else "")
        + "</main></body></html>"
    )
