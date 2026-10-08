"""Decision-first HTML impact report (v7 Wave 2).

Renders the same ``report_data`` dict as the classic report, but leads with a
decision: a verdict card, four headline numbers and "what would change our
mind", then the 5 Dimensions, SDGs, an evidence ledger, the greenwashing
review, risks, an action plan and an appendix (methodology + glossary).

Design: one token sheet (``design/tokens.css``) shared with every deliverable,
Jinja2 templates with autoescaping, HTML/CSS charts with table twins (no
Plotly, works offline, prints cleanly), light/dark themes, and audience
variants that leave internal content out of the HTML entirely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from openharness.impact.report_templates.design.strings import (
    SDG_NAMES,
    SECTOR_NAMES,
    normalize_lang,
    translator,
)
from openharness.impact.report_templates.report_v2 import SDG_COLORS, sdg_text_colour

_DESIGN = Path(__file__).resolve().parent / "design"

DIMENSIONS = ("what", "who", "how_much", "contribution", "risk")
AUDIENCES = ("full", "ic", "lp", "regulator", "public")


@dataclass(frozen=True)
class ReportSpec:
    """Which sections an audience sees, in order."""

    audience: str
    sections: tuple[str, ...]
    show_gate: bool
    show_greenwashing: bool


SPECS: dict[str, ReportSpec] = {
    "full": ReportSpec("full", ("verdict", "kpis", "mind", "impact", "glance", "five_d", "sdg", "evidence", "greenwashing",
                                "risks", "actions", "targets", "feedback", "appendix"), True, True),
    "ic": ReportSpec("ic", ("verdict", "kpis", "mind", "impact", "glance", "five_d", "sdg", "evidence", "greenwashing",
                            "risks", "actions", "appendix"), True, True),
    "lp": ReportSpec("lp", ("kpis", "impact", "glance", "five_d", "sdg", "evidence", "targets", "feedback", "risks",
                            "appendix"), False, False),
    "regulator": ReportSpec("regulator", ("kpis", "impact", "evidence", "greenwashing", "five_d", "sdg",
                                          "risks", "appendix"), False, True),
    "public": ReportSpec("public", ("kpis", "impact", "glance", "sdg", "five_d", "evidence", "feedback", "appendix"),
                         False, False),
}

SECTION_IDS = {
    "verdict": "sec-verdict", "mind": "sec-mind", "impact": "sec-impact", "glance": "sec-glance", "five_d": "sec-5d", "sdg": "sec-sdg",
    "evidence": "sec-evidence", "greenwashing": "sec-greenwashing", "risks": "sec-risks",
    "actions": "sec-actions", "targets": "sec-targets", "feedback": "sec-feedback",
    "appendix": "sec-appendix",
}
SECTION_TITLES = {
    "verdict": "sec_verdict", "mind": "sec_mind", "impact": "sec_impact", "glance": "sec_glance", "five_d": "sec_5d", "sdg": "sec_sdg",
    "evidence": "sec_evidence", "greenwashing": "sec_gw", "risks": "sec_risks",
    "actions": "sec_actions", "targets": "sec_targets", "feedback": "sec_feedback",
    "appendix": "sec_appendix",
}


# --------------------------------------------------------------------------- css / jinja


@lru_cache(maxsize=1)
def design_tokens_css() -> str:
    """The shared token sheet on its own (for the v2 deliverables)."""
    return (_DESIGN / "tokens.css").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def design_css() -> str:
    return (_DESIGN / "tokens.css").read_text(encoding="utf-8") + "\n" + (
        _DESIGN / "report.css"
    ).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _env():  # type: ignore[no-untyped-def]
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader(str(_DESIGN / "templates")),
        autoescape=select_autoescape(["html", "j2"], default=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["pct"] = lambda v, top=5.0: max(0.0, min(100.0, float(v or 0) / float(top) * 100))
    env.filters["num"] = _fmt_num
    return env


def _fmt_num(value: Any, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer() and digits <= 1:
        return f"{int(number):,}"
    return f"{number:,.{digits}f}"


# --------------------------------------------------------------------------- decision


def _decision(data: dict[str, Any]) -> dict[str, Any] | None:
    """IC gate summary: from report_data['decision'] or computed on the fly."""
    if data.get("decision"):
        return data["decision"]
    try:
        from openharness.impact.deal_gate import evaluate_deal
        from openharness.impact.fund_thesis import load_fund_thesis
        from openharness.impact.models import Assessment, Company, FiveDimensionScore, SDGAlignment

        fd = data.get("five_dimensions")
        assessment = Assessment(
            company=Company(**{k: v for k, v in data["company"].items() if k in Company.model_fields}),
            five_dimensions=FiveDimensionScore.model_validate(fd) if fd else None,
            sdg_alignments=[SDGAlignment.model_validate(a) for a in data.get("sdg_alignments", [])],
        )
        gw = (data.get("greenwashing") or {}).get("overall_score")
        scorecard = evaluate_deal(assessment, load_fund_thesis(), greenwashing_score=gw)
    except Exception:  # noqa: BLE001 - the report must render without a gate
        return None
    return decision_from_scorecard(scorecard)


def decision_from_scorecard(scorecard: Any, *, dd: Any | None = None) -> dict[str, Any]:
    """Serialisable IC-gate summary stored in ``report_data['decision']``."""
    payload = {
        "overall_status": scorecard.overall_status,
        "evidence_status": getattr(scorecard, "evidence_status", "sufficient"),
        "display_status": getattr(scorecard, "display_status", scorecard.overall_status.upper()),
        "recommendation": scorecard.recommendation,
        "fund": scorecard.fund,
        "checks": [c.model_dump(mode="json") for c in scorecard.checks],
    }
    if dd is not None:
        payload["dd_coverage_pct"] = dd.coverage_pct
        payload["dd_high_priority"] = [q.question for q in dd.high_priority_gaps[:5]]
    return payload


_ICON = {
    "good": '<path d="M7 12.5l3.2 3.2L17 9" />',
    "warning": '<path d="M12 7v6" /><path d="M12 16.5v.5" />',
    "serious": '<path d="M12 7v6" /><path d="M12 16.5v.5" />',
    "critical": '<path d="M8.5 8.5l7 7M15.5 8.5l-7 7" />',
    "neutral": '<path d="M8 12h8" />',
}


def _check_text(check: dict[str, Any], t=None) -> str:  # type: ignore[no-untyped-def]
    """'Greenwashing risk 50.6 (max 40)' rather than the gate's terse message."""
    t = t or translator("en")
    name, actual, threshold = check.get("name", ""), check.get("actual"), check.get("threshold")
    label = t(f"check_{name}") if t(f"check_{name}") != f"check_{name}" else name
    if name == "Top SDG score" and t("check_Top SDG score") == "Top SDG score":
        return check.get("message") or name
    if not isinstance(actual, (int, float)):
        return check.get("message") or label
    bound = t("bound_max") if "greenwashing" in name.lower() else t("bound_min")
    return f"{label} {actual:.1f} ({bound} {threshold:g})" if isinstance(threshold, (int, float)) else label


def _verdict(decision: dict[str, Any] | None, fd: dict | None, t,  # type: ignore[no-untyped-def]
             gate2: dict[str, Any] | None = None, eq: dict[str, Any] | None = None) -> dict[str, Any]:
    if gate2 and decision is not None:
        # Gate 2.0: Ready / Evidence plan required / Fails thesis.
        state = gate2["state"]
        tone = {"ready": "good", "evidence_plan": "warning"}.get(state, "critical")
        return {
            "tone": tone,
            "label": t(f"verdict2_{state}"),
            "icon": _ICON.get(tone, _ICON["neutral"]),
            "recommendation": t(f"rec2_{state}"),
            "reasons": list(gate2.get("reasons") or [])[:3],
            "confidence": (t("eq_title") + f": {eq['score']}/100 · " + t(f"eq_{eq['label']}")) if eq else "",
        }
    if not decision:
        tone, label, recommendation, reasons = "neutral", t("verdict_unknown"), "", []
    else:
        status = decision["overall_status"]
        insufficient = decision.get("evidence_status") == "insufficient"
        tone, key = {
            "pass": ("good", "verdict_pass"),
            "warn": ("warning", "verdict_warn"),
        }.get(status, ("warning", "verdict_insufficient") if insufficient else ("critical", "verdict_fail"))
        label = t(key)
        # The gate's recommendation opens by restating the status; the card
        # already shows it as the headline.
        recommendation = t({
            "good": "rec_pass", "warning": "rec_insufficient" if insufficient else "rec_warn",
        }.get(tone, "rec_fail"))
        reasons = []
        for check in decision.get("checks", []):
            if check.get("status") in ("fail", "warn"):
                text = _check_text(check, t)
                if check.get("data_gap"):
                    text = f"{text} ({t('missing_data')})"
                reasons.append(text)
        reasons = reasons[:3]
    provenance = (fd or {}).get("overall_provenance", "estimated")
    return {
        "tone": tone,
        "label": label,
        "icon": _ICON.get(tone, _ICON["neutral"]),
        "recommendation": recommendation,
        "reasons": reasons,
        "confidence": t(f"confidence_{provenance}") if fd else "",
    }


# --------------------------------------------------------------------------- graphics

_SECTION_ICONS = {
    "impact": '<path d="M3 17l5-5 4 3 8-9"/><path d="M15 6h5v5"/>',
    "mind": '<path d="M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3z"/><path d="M9.5 19h5M10.5 21.5h3"/>',
    "glance": '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5V12l6 6"/>',
    "five_d": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "sdg": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5"/>',
    "evidence": '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M10 12h5M10 16h5"/>',
    "greenwashing": '<path d="M12 3l8 4v5c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V7z"/><path d="M9 12l2 2 4-4"/>',
    "risks": '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17v.5"/>',
    "actions": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2"/>',
    "targets": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/>',
    "feedback": '<path d="M4 5h16v11H9l-5 4z"/>',
    "appendix": '<path d="M5 4h10l4 4v12H5z"/><path d="M9 12h6M9 16h4"/>',
}


def section_icon(section: str) -> str:
    path = _SECTION_ICONS.get(section)
    if not path:
        return ""
    return (
        '<span class="h-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{path}</svg></span>"
    )


_LEGAL_SUFFIXES = {"sdn", "bhd", "ltd", "limited", "inc", "llc", "plc", "gmbh", "pte", "co", "corp"}


def monogram(name: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", name) if w.lower() not in _LEGAL_SUFFIXES]
    if not words:
        return (name.strip()[:1] or "?").upper()
    return "".join(w[0] for w in words[:2]).upper()


def sdg_wheel_svg(material: list[dict[str, Any]], *, center_label: str, title: str) -> str:
    """17-wedge SDG wheel: material goals in their official colour, others muted.

    The colours carry goal identity (like a logo), not magnitude; scores are in
    the bar chart and table beside it.
    """
    import math

    from markupsafe import escape

    lit = {int(g["goal"]): g for g in material}
    cx = cy = 130.0
    outer, inner = 120.0, 66.0
    gap = 0.012  # radians of surface between wedges
    parts = []
    for i in range(17):
        goal = i + 1
        a0 = -math.pi / 2 + i * 2 * math.pi / 17 + gap
        a1 = -math.pi / 2 + (i + 1) * 2 * math.pi / 17 - gap
        p = [
            (cx + outer * math.cos(a0), cy + outer * math.sin(a0)),
            (cx + outer * math.cos(a1), cy + outer * math.sin(a1)),
            (cx + inner * math.cos(a1), cy + inner * math.sin(a1)),
            (cx + inner * math.cos(a0), cy + inner * math.sin(a0)),
        ]
        d = (f"M{p[0][0]:.2f},{p[0][1]:.2f} A{outer},{outer} 0 0 1 {p[1][0]:.2f},{p[1][1]:.2f} "
             f"L{p[2][0]:.2f},{p[2][1]:.2f} A{inner},{inner} 0 0 0 {p[3][0]:.2f},{p[3][1]:.2f} Z")
        g = lit.get(goal)
        fill = SDG_COLORS.get(goal, "#888") if g else "var(--grid)"
        label = f"SDG {goal}" + (f" · {g['name']} · {g['score']:.0f}/100" if g else "")
        parts.append(f'<path d="{d}" fill="{fill}"><title>{escape(label)}</title></path>')
        am = (a0 + a1) / 2
        tx, ty = cx + 93 * math.cos(am), cy + 93 * math.sin(am)
        color = sdg_text_colour(goal) if g else "var(--muted)"
        parts.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" dominant-baseline="central" '
            f'style="fill:{color}" aria-hidden="true">{goal}</text>'
        )
    parts.append(
        f'<text class="center-num" x="{cx}" y="{cy - 6}" text-anchor="middle" '
        f'dominant-baseline="central">{len(lit)}</text>'
        f'<text class="center-lbl" x="{cx}" y="{cy + 18}" text-anchor="middle">{escape(center_label)}</text>'
    )
    return (
        f'<svg class="wheel" viewBox="0 0 260 260" role="img" aria-label="{escape(title)}">'
        + "".join(parts) + "</svg>"
    )


def _pathway(data: dict[str, Any], t) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    company = data.get("company") or {}
    description = str(company.get("description") or "").strip()
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", description) if len(x.strip()) > 25]
    business = re.compile(
        r"\b(?:is an?|are an?|sells|provides|offers|operates|runs|builds|develops|manufactures|"
        r"delivers|supplies|lends|serves)\b", re.IGNORECASE,
    )
    first = next((x for x in sentences if business.search(x) and "fictional" not in x.lower()),
                 sentences[0] if sentences else "")
    claims = data.get("impact_claims") or []

    def items(categories: tuple[str, ...]) -> list[dict[str, Any]]:
        chosen = [c for c in claims if c.get("category") in categories]
        chosen.sort(key=lambda c: -int(c.get("evidence_strength") or 1))
        return [
            {"text": _clip(str(c.get("text", "")), 120), "level": int(c.get("evidence_strength") or 1)}
            for c in chosen[:3]
        ]

    return [
        {"title": t("stage_activities"), "items": [{"text": _clip(first, 160), "level": 0}] if first else []},
        {"title": t("stage_outputs"), "items": items(("output", "activity"))},
        {"title": t("stage_outcomes"), "items": items(("outcome",))},
        {"title": t("stage_targets"), "items": items(("intent",))},
    ]


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "\u2026"


def _evidence_mix(data: dict[str, Any]) -> list[dict[str, int]]:
    counts = {lvl: 0 for lvl in range(1, 6)}
    for c in data.get("impact_claims") or []:
        lvl = min(5, max(1, int(c.get("evidence_strength") or 1)))
        counts[lvl] += 1
    return [{"level": lvl, "count": n} for lvl, n in counts.items() if n]


# --------------------------------------------------------------------------- sections


def _five_d(data: dict[str, Any], t) -> dict[str, Any] | None:  # type: ignore[no-untyped-def]
    fd = data.get("five_dimensions")
    if not fd:
        return None
    bench = (data.get("benchmark_comparison") or {}).get("dimensions", {})
    rows = []
    for key in DIMENSIONS:
        dim = fd.get(key) or {}
        notes = str(dim.get("notes") or "").strip()
        gaps = dim.get("gaps") or []
        sentence = notes if notes and "=" not in notes else (gaps[0] if gaps else "")
        rows.append({
            "key": key,
            "label": t(f"dim_{key}"),
            "score": float(dim.get("score") or 0),
            "benchmark": (bench.get(key) or {}).get("benchmark"),
            "provenance": dim.get("provenance", "estimated"),
            "sentence": str(sentence)[:180],
            "reported": dim.get("metrics_reported", 0),
        })
    return {
        "rows": rows,
        "overall": float(fd.get("overall_score") or 0),
        "grade": fd.get("overall_grade", ""),
        "provenance": fd.get("overall_provenance", "estimated"),
        "has_benchmark": any(r["benchmark"] is not None for r in rows),
        "benchmark_note": (data.get("benchmark_comparison") or {}).get("sample_note", ""),
    }


def _sdg(data: dict[str, Any], lang: str = "en") -> dict[str, Any]:
    alignments = sorted(data.get("sdg_alignments") or [], key=lambda a: -float(a.get("score") or 0))
    material = [a for a in alignments if a.get("material", True) and float(a.get("score") or 0) > 0]
    other = [a for a in alignments if a not in material]
    to_row = lambda a: {  # noqa: E731
        "goal": int(a["goal"]),
        "name": SDG_NAMES.get(lang, {}).get(int(a["goal"]), a.get("goal_name", "")),
        "score": float(a.get("score") or 0),
        "confidence": a.get("confidence", "low"),
        "metrics": a.get("matched_metrics", [])[:6],
        "color": SDG_COLORS.get(int(a["goal"]), "#888888"),
        "ink": sdg_text_colour(int(a["goal"])),
    }
    return {"material": [to_row(a) for a in material[:8]], "other": sorted(int(a["goal"]) for a in other)}


def _metric_names() -> dict[str, str]:
    try:
        from openharness.impact.database import get_metric_store

        return {m.id: m.name for m in get_metric_store().all_metrics()}
    except Exception:  # noqa: BLE001
        return {}


def _evidence(data: dict[str, Any], t) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    claims = []
    for c in data.get("impact_claims") or []:
        signals = (c.get("entities") or {}).get("evidence") or []
        claims.append({
            "text": str(c.get("text", "")).strip(),
            "category": c.get("category", ""),
            "level": int(c.get("evidence_strength") or 1),
            "signals": [t(f"signal_{s}") for s in signals],
            "metrics": c.get("mapped_metrics") or [],
        })
    names = _metric_names()
    for c in claims:  # show what each mapped ID is, not just the code
        c["metric_rows"] = [{"id": m, "name": names.get(m, "")} for m in c["metrics"]]
    metrics = []
    for metric_id, value in sorted((data.get("company") or {}).get("reported_metrics", {}).items()):
        text = str(value)
        origin = (
            t("origin_derived") if "derived" in text
            else t("origin_extracted") if any(metric_id in c["metrics"] for c in claims)
            else t("origin_reported")
        )
        metrics.append({"id": metric_id, "name": names.get(metric_id, ""), "value": text, "origin": origin})
    return {"claims": claims, "metrics": metrics}


_GW_COMPONENTS = ("claim_metric_gap", "adverse_omission", "specificity", "selectivity", "verification")


def _greenwashing(data: dict[str, Any], t) -> dict[str, Any] | None:  # type: ignore[no-untyped-def]
    gw = data.get("greenwashing")
    if not gw:
        return None
    subs = gw.get("sub_scores") or {k: gw.get(k) for k in _GW_COMPONENTS}
    from openharness.impact.methodology import section

    threshold = float(section("greenwashing").get("flag_threshold", 60))
    return {
        "threshold": threshold,
        "score": float(gw.get("overall_score") or 0),
        "classification": t(f"gwc_{gw.get('classification', '')}"),
        "components": [
            {"label": t(f"gw_{k}"), "value": float(subs.get(k) or 0),
             "over": float(subs.get(k) or 0) >= threshold}
            for k in _GW_COMPONENTS if subs.get(k) is not None
        ],
        "flags": [str(f).split(":", 1)[-1].strip() for f in gw.get("flags") or []],
    }


def _risks(data: dict[str, Any]) -> dict[str, list[str]]:
    analysis = data.get("impact_analysis") or {}
    risks = analysis.get("risks") or []
    disclosed: list[str] = []
    for r in risks:
        if r.startswith("Disclosed:"):
            # "Risks we manage include: (i) ASF ...; (ii) run-off ..." -> one bullet each
            text = r.split(":", 1)[1].strip().rstrip("\u2026")
            parts = [p.strip(" ;,.") for p in re.split(r"\(\s*(?:i{1,3}|iv|vi{0,3})\s*\)", text)]
            items = [p for p in parts[1:] if len(p) > 12] if len(parts) > 2 else [text]
            disclosed.extend(items)
    sector = [r for r in risks if not r.startswith("Disclosed:") and not r.startswith("Further analysis")]
    opportunities = [o for o in analysis.get("opportunities") or [] if not o.startswith("Further analysis")]
    return {"disclosed": disclosed, "sector": sector[:6], "opportunities": opportunities[:6]}


def _sig(value: float) -> str:
    """Two significant figures: a range shouldn't look more precise than it is."""
    if value <= 0:
        return "0"
    if value < 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    digits = 2 - len(str(int(value)))
    return f"{round(value, digits):,.0f}"


def _factor_value(name: str, median: float) -> str:
    if name in {"Reach", "Tonnes per year"}:
        return f"{median:,.0f}"
    if name == "Duration (years)":
        return f"{median:g}"
    return f"{median:.0%}"


def _who(noun: str, lang: str) -> str:
    from openharness.impact.report_templates.design.strings import STAKEHOLDERS_ZH_CN, STAKEHOLDERS_ZH_HK

    table = {"zh-HK": STAKEHOLDERS_ZH_HK, "zh-CN": STAKEHOLDERS_ZH_CN}.get(lang)
    return table.get(noun, noun) if table else noun


def _impact(data: dict[str, Any], t, lang: str = "en") -> dict[str, Any] | None:  # type: ignore[no-untyped-def]
    """Methodology 2.0 block for the 'Expected impact' section (v8 Wave 1)."""
    import math

    def why(f: dict[str, Any]) -> str:
        args = dict(f.get("why_args") or {})
        if "who" in args:
            args["who"] = _who(str(args["who"]), lang)
        if "sector" in args:
            args["sector"] = SECTOR_NAMES.get(lang, {}).get(args["sector"], args["sector"])
        return t(f["why_key"], **args) if f.get("why_key") else f.get("why", "")

    block = data.get("expected_impact")
    if not block:
        return None
    rows = []
    for o in block.get("outcomes", []):
        lo, mid, hi = max(o["p10"], 1e-9), max(o["p50"], 1e-9), max(o["p90"], 1e-9)
        a, b = math.log10(lo) - 0.35, math.log10(hi) + 0.35
        pos = lambda v: round((math.log10(max(v, 1e-9)) - a) / (b - a) * 100, 1)  # noqa: E731
        per = o.get("per_usd_1m")
        rows.append({
            "kind": t(f"impact_{o['kind']}"),
            "unit": t(f"impact_unit_{o['kind']}"),
            "stakeholder": (o.get("stakeholder_raw") if lang != "en" and not str(o.get("stakeholder_raw", "")).isascii()
                            else _who(o.get("stakeholder", ""), lang)),
            "p10": _sig(o["p10"]), "p50": _sig(o["p50"]), "p90": _sig(o["p90"]),
            "bar": {"left": pos(lo), "width": max(1.0, pos(hi) - pos(lo)), "mid": pos(mid)},
            "spread": t("impact_spread", uncertainty=t(f"unc_{o['uncertainty']}"), spread=o.get("spread") or "—"),
            "factors": [{"name": t(f"factor_{f['name']}"), "value": _factor_value(f["name"], f["median"]),
                         "why": why(f)} for f in o.get("factors", [])],
            "drivers": [{"name": t(f"factor_{d['factor']}"), "share": round(d["share"] * 100)}
                        for d in o.get("drivers", [])],
            "per_m": t("impact_per_m", p50=_sig(per["p50"]), p10=_sig(per["p10"]), p90=_sig(per["p90"])) if per else "",
            "source": o.get("source", ""),
            "level": o.get("evidence_level", 1),
        })
    eq = block.get("evidence_quality") or {}
    levels = sorted(set(eq.get("levels") or []))
    return {
        "rows": rows,
        "eq": {"score": eq.get("score", 0), "label": t(f"eq_{eq.get('label', 'weak')}"),
               "sub": t("eq_sub", label=t(f"eq_{eq.get('label', 'weak')}"),
                        levels="/".join(str(x) for x in levels) or "—",
                        verified=t("eq_verified") if eq.get("verified") else "")},
        "completeness": block.get("data_completeness_pct"),
        "targets": block.get("targets") or [],
        "methodology": block.get("methodology") or {},
    }


def _v2_gate(data: dict[str, Any]) -> dict[str, Any] | None:
    from openharness.impact.expected_impact import methodology_mode

    gate = (data.get("expected_impact") or {}).get("gate")
    return gate if gate and methodology_mode() == "2" else None


def _mind(data: dict[str, Any], five_d: dict | None, decision: dict | None, t) -> list[dict[str, str]]:  # type: ignore[no-untyped-def]
    gate2 = _v2_gate(data)
    plan = (data.get("expected_impact") or {}).get("evidence_plan") or []
    if gate2 and plan:
        # Methodology 2.0: the evidence that narrows the range most, in order.
        return [{"what": item["action"], "why": item["why"]} for item in plan[:3]]
    items: list[dict[str, str]] = []
    gaps = data.get("gap_analysis") or {}
    if five_d:
        weakest = min(five_d["rows"], key=lambda r: r["score"])
        group = {"how_much": "How Much"}.get(weakest["key"], weakest["label"].title())
        names = {m["id"]: m["name"] for m in gaps.get("missing", [])}
        for metric_id in (gaps.get("missing_by_dimension") or {}).get(group, [])[:1]:
            items.append({
                "what": t("mind_metric", name=names.get(metric_id, metric_id), id=metric_id),
                "why": t("mind_metric_why", dimension=weakest["label"], score=f"{weakest['score']:.1f}",
                         evidence=t(weakest["provenance"])),
            })
    gw = data.get("greenwashing") or {}
    subs = gw.get("sub_scores") or gw
    claims = data.get("impact_claims") or []
    signals = {s for c in claims for s in (c.get("entities") or {}).get("evidence", [])}
    if float(subs.get("verification") or 0) > 40 or not signals & {"third_party_verified", "audited", "certified"}:
        items.append({"what": t("mind_verify"), "why": t("mind_verify_why")})
    if claims and "controlled_evaluation" not in signals:
        items.append({"what": t("mind_outcome"), "why": t("mind_outcome_why")})
    if float(subs.get("adverse_omission") or 0) > 60:
        items.append({"what": t("mind_adverse"), "why": t("mind_adverse_why")})
    for question in (decision or {}).get("dd_high_priority", [])[:2]:
        items.append({"what": t("mind_dd", question=question), "why": t("mind_dd_why")})
    return items[:3]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()[:70]


def _stems(text: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


_IRIS_ID = re.compile(r"\b([A-Z]{2}\d{4})\b(?!\s*\()")


def _actions(data: dict[str, Any], spec: ReportSpec, t) -> list[dict[str, str]]:  # type: ignore[no-untyped-def]
    seen: set[str] = set()
    kept: list[set[str]] = []
    out: list[dict[str, str]] = []
    names = _metric_names()

    def add(text: str, area: str) -> None:
        key = _norm(text)
        if not text or key in seen:
            return
        stems = _stems(text)
        # Near-duplicates ("Start with: X, Y" vs "Priority missing metrics: X (..), Y (..)"):
        # skip when most of this action's words already appear in an earlier one.
        if stems and any(len(stems & prev) / len(stems) >= 0.6 or (prev and len(stems & prev) / len(prev) >= 0.6)
                         for prev in kept):
            return
        seen.add(key)
        kept.append(stems)
        text = _IRIS_ID.sub(lambda m: f"{m.group(1)} ({names[m.group(1)]})" if m.group(1) in names else m.group(1),
                            text.strip())
        out.append({"text": text, "area": t(area)})

    for rec in (data.get("gap_analysis") or {}).get("recommendations", []):
        add(rec, "area_metrics")
    for rec in (data.get("five_dimensions") or {}).get("recommendations", []):
        add(rec, "area_5d")
    if spec.show_greenwashing:
        for rec in (data.get("greenwashing") or {}).get("recommendations", []):
            add(rec, "area_evidence_quality")
    for a in data.get("sdg_alignments") or []:
        if a.get("material", True):
            for rec in (a.get("recommendations") or [])[:1]:
                add(rec, "area_sdg")
    return out[:10]


def _kpis(view: dict[str, Any], spec: ReportSpec, decision: dict | None, t) -> list[dict[str, str]]:  # type: ignore[no-untyped-def]
    tiles = []
    impact = view.get("impact")
    if impact and impact["rows"]:
        # Methodology 2.0 leads: how much change, and how sure we are.
        top = impact["rows"][0]
        tiles.append({"label": t("kpi_impact"), "value": top["p50"], "unit": "",
                      "sub": t("kpi_impact_sub", unit=top["unit"], p10=top["p10"], p90=top["p90"])})
        comp = impact.get("completeness")
        tiles.append({"label": t("kpi_eq"), "value": str(impact["eq"]["score"]), "unit": "/100",
                      "sub": t("kpi_eq_sub", label=impact["eq"]["label"],
                               completeness=f"{comp:.0f}" if comp is not None else "—"),
                      "meter": {"pct": impact["eq"]["score"], "tone": "good" if impact["eq"]["score"] >= 60
                                else "warning", "tick": 60}})
    elif view["five_d"]:
        fd = view["five_d"]
        tiles.append({"label": t("kpi_5d"), "value": f"{fd['overall']:.1f}", "unit": "/5",
                      "sub": t("kpi_5d_sub", grade=fd["grade"], evidence=t(fd["provenance"])),
                      "meter": {"pct": fd["overall"] / 5 * 100, "tone": ""}})
    material = view["sdg"]["material"]
    if material:
        top = material[0]
        tiles.append({"label": t("kpi_sdg"), "value": "", "unit": "", "badge": top,
                      "sub": f"{top['name']} · {top['score']:.0f}/100"})
    else:
        tiles.append({"label": t("kpi_sdg"), "value": "—", "unit": "", "sub": t("kpi_sdg_none")})
    if spec.show_greenwashing and view["greenwashing"]:
        gw = view["greenwashing"]
        tone = "good" if gw["score"] < 40 else "warning" if gw["score"] < 60 else "critical"
        tiles.append({"label": t("kpi_gw"), "value": f"{gw['score']:.0f}", "unit": "/100",
                      "sub": f"{gw['classification']} · {t('tile_threshold')}",
                      "meter": {"pct": gw["score"], "tone": tone, "tick": 60}})
    if len(tiles) >= 4:
        return tiles[:4]
    ev = view["evidence"]
    dd = (decision or {}).get("dd_coverage_pct") if spec.show_gate else None
    tiles.append({
        "label": t("kpi_evidence"),
        "value": t("kpi_evidence_value", claims=len(ev["claims"])),
        "unit": "",
        "mix": view["evidence_mix"],
        "sub": (t("kpi_evidence_sub", metrics=len(ev["metrics"]), dd=f"{dd:.0f}") if dd is not None
                else t("kpi_evidence_sub_nodd", metrics=len(ev["metrics"]))),
    })
    return tiles


def _ai(data: dict[str, Any], t) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Localised AI-provenance badge + disclosure (EU AI Act Art 50, W4.5)."""
    from openharness.impact.ai_provenance import ai_provenance_for_report

    prov = ai_provenance_for_report(data)
    if prov.ai_generated:
        stages = [t(f"ai_stage_{s}").lower() if t(f"ai_stage_{s}").isascii() else t(f"ai_stage_{s}")
                  for s in ("extraction", "tagging", "drafting") if getattr(prov, s) == "llm"]
        sentence = t("ai_assisted", model=f" ({prov.llm_model})" if prov.llm_model else "",
                     stages=", ".join(stages))
    else:
        sentence = t("ai_auto")
    if prov.estimated_figures:
        sentence += " " + t("ai_estimated", n=prov.estimated_figures, total=prov.total_figures)
    sentence += " " + t("ai_reviewed" if prov.human_reviewed else "ai_review")
    badges = [t("ai_badge_ai" if prov.extraction == "llm" else "ai_badge_rules")]
    if prov.estimated_figures:
        badges.append(t("ai_badge_estimated", n=prov.estimated_figures, total=prov.total_figures))
    if prov.drafting == "llm":
        badges.append(t("ai_badge_drafted"))
    return {
        "generated": prov.ai_generated,
        "badges": badges,
        "disclosure": sentence,
        "rows": [(t(f"ai_stage_{s}"), t(f"ai_m_{getattr(prov, s)}"))
                 for s in ("extraction", "calculation", "tagging", "drafting")],
    }


_BRANDING_KEYS = ("fund_name", "logo_url", "footer_text", "primary_color", "hide_attribution")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _branding(raw: dict[str, Any] | None) -> dict[str, Any]:
    """White-label settings; only a valid hex colour may reach the CSS."""
    raw = dict(raw or {})
    out = {key: raw.get(key) or "" for key in _BRANDING_KEYS}
    if not _HEX.match(str(out["primary_color"])):
        out["primary_color"] = ""
    logo = str(out["logo_url"])
    if logo and not logo.startswith(("https://", "data:image/")):
        out["logo_url"] = ""
    out["hide_attribution"] = bool(raw.get("hide_attribution"))
    return out


def build_view(data: dict[str, Any], *, audience: str | None = None, lang: str = "en",
               branding: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assemble everything the template needs from ``report_data``."""
    lang = normalize_lang(lang)
    audience = (audience or data.get("audience") or "full").lower()
    if data.get("report_type") == "lp_ready" and audience == "full":
        audience = "lp"
    spec = SPECS.get(audience, SPECS["full"])
    t = translator(lang)
    company = data.get("company") or {}
    decision = _decision(data) if spec.show_gate else None

    view: dict[str, Any] = {
        "t": t,
        "lang": lang,
        "theme": "dark" if str(data.get("theme", "")).lower() == "dark" else "",
        "audience": spec.audience,
        "notice": t(f"notice_{spec.audience}"),
        "company": {
            "name": company.get("name") or "Company",
            "sector": SECTOR_NAMES.get(lang, {}).get(company.get("sector", ""), company.get("sector", "")),
            "geography": company.get("geography", ""),
        },
        "generated": str(data.get("generated_at", ""))[:10],
        "catalog_version": str(data.get("catalog_version", "IRIS+ 5.3c")).replace("IRIS+ ", ""),
        "source": data.get("source_label", ""),
        "branding": _branding(branding),
        "five_d": _five_d(data, t),
        "sdg": _sdg(data, lang),
        "lang_note": t("lang_note"),
        "evidence": _evidence(data, t),
        "greenwashing": _greenwashing(data, t) if spec.show_greenwashing else None,
        "risks": _risks(data),
        "targets": (data.get("target_tracking") or {}).get("targets", []),
        "feedback": data.get("beneficiary_feedback"),
    }
    view["impact"] = _impact(data, t, lang)
    view["ai"] = _ai(data, t)
    view["evidence_mix"] = _evidence_mix(data)
    view["pathway"] = _pathway(data, t)
    view["monogram"] = monogram(view["company"]["name"])
    view["sdg_wheel"] = sdg_wheel_svg(
        view["sdg"]["material"], center_label=t("wheel_center"), title=t("sec_sdg")
    )
    view["icons"] = {key: section_icon(key) for key in _SECTION_ICONS}
    gate2 = _v2_gate(data) if decision else None
    view["verdict"] = _verdict(decision, data.get("five_dimensions"), t, gate2,
                               (data.get("expected_impact") or {}).get("evidence_quality"))
    if decision and gate2:
        view["pill"] = {"tone": view["verdict"]["tone"], "label": t(f"pill2_{gate2['state']}")}
    elif decision:
        insufficient = decision.get("evidence_status") == "insufficient"
        view["pill"] = {
            "tone": view["verdict"]["tone"],
            "label": t({"pass": "pill_pass", "warn": "pill_warn"}.get(
                decision["overall_status"], "pill_insufficient" if insufficient else "pill_fail")),
        }
    else:
        view["pill"] = None
    view["kpis"] = _kpis(view, spec, decision, t)
    view["mind"] = _mind(data, view["five_d"], decision, t)
    view["mind_is_plan"] = bool(_v2_gate(data) and (data.get("expected_impact") or {}).get("evidence_plan"))
    view["actions"] = _actions(data, spec, t)
    from openharness.impact.methodology import methodology_stamp, section

    view["methodology"] = [t("method_1"), t("method_2"), t("method_3")]
    if spec.show_greenwashing:
        w = section("greenwashing").get("weights", {})
        view["methodology"].append(t(
            "method_4",
            gap=round(w.get("claim_metric_gap", 0) * 100), omission=round(w.get("adverse_omission", 0) * 100),
            specificity=round(w.get("specificity", 0) * 100), selectivity=round(w.get("selectivity", 0) * 100),
            verification=round(w.get("verification", 0) * 100),
        ))
    if spec.show_gate:
        view["methodology"].append(t("method_5"))
    stamp = data.get("methodology") or methodology_stamp()
    view["methodology_stamp"] = stamp
    view["methodology"].append(t("method_version", version=stamp["methodology_version"], hash=stamp["config_hash"]))
    if view["impact"]:
        from openharness.impact.expected_impact import params as v2_params

        m2 = view["impact"]["methodology"]
        view["methodology"].append(t("method_v2", version=m2.get("methodology_version", "2"),
                                     status=m2.get("status", ""),
                                     draws=(v2_params().get("monte_carlo") or {}).get("draws", 4000)))

    present = {
        "verdict": decision is not None,
        "kpis": bool(view["kpis"]),
        "glance": bool(view["sdg"]["material"]) or any(st["items"] for st in view["pathway"][1:]),
        "mind": bool(view["mind"]),
        "impact": view["impact"] is not None,
        "five_d": view["five_d"] is not None,
        "sdg": bool(view["sdg"]["material"] or view["sdg"]["other"]),
        "evidence": bool(view["evidence"]["claims"] or view["evidence"]["metrics"]),
        "greenwashing": view["greenwashing"] is not None,
        "risks": any(view["risks"].values()),
        "actions": bool(view["actions"]),
        "targets": bool(view["targets"]),
        "feedback": bool(view["feedback"]),
        "appendix": True,
    }
    view["sections"] = [s for s in spec.sections if present.get(s)]
    view["toc"] = [(SECTION_IDS[s], t(SECTION_TITLES[s])) for s in view["sections"] if s in SECTION_IDS]
    return view


def render_decision_report(data: dict[str, Any], *, audience: str | None = None, lang: str = "en",
                           branding: dict[str, Any] | None = None) -> str:
    """Render ``report_data`` as the decision-first HTML report."""
    from openharness.impact.glossary import render_glossary_html

    view = build_view(data, audience=audience, lang=lang, branding=branding)
    env = _env()
    body = env.get_template("report.html.j2").render(css=design_css(), glossary_html="", **view)
    visible = re.sub(r"<style.*?</style>|<script.*?</script>|<[^>]+>", " ", body, flags=re.S)
    glossary = render_glossary_html(visible) if view["lang"] == "en" else ""
    if glossary:
        from markupsafe import Markup

        body = env.get_template("report.html.j2").render(
            css=design_css(), glossary_html=Markup(glossary), **view
        )
    from openharness.impact.ai_provenance import ai_provenance_for_report, machine_marking, mark_html

    return mark_html(body, machine_marking(ai_provenance_for_report(data)))


__all__ = [
    "AUDIENCES",
    "ReportSpec",
    "SPECS",
    "build_view",
    "decision_from_scorecard",
    "design_css",
    "design_tokens_css",
    "render_decision_report",
]
