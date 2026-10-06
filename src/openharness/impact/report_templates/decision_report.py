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
from openharness.impact.report_templates.report_v2 import SDG_COLORS

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
    "full": ReportSpec("full", ("verdict", "kpis", "mind", "five_d", "sdg", "evidence", "greenwashing",
                                "risks", "actions", "targets", "feedback", "appendix"), True, True),
    "ic": ReportSpec("ic", ("verdict", "kpis", "mind", "five_d", "sdg", "evidence", "greenwashing",
                            "risks", "actions", "appendix"), True, True),
    "lp": ReportSpec("lp", ("kpis", "five_d", "sdg", "evidence", "targets", "feedback", "risks",
                            "appendix"), False, False),
    "regulator": ReportSpec("regulator", ("kpis", "evidence", "greenwashing", "five_d", "sdg",
                                          "risks", "appendix"), False, True),
    "public": ReportSpec("public", ("kpis", "sdg", "five_d", "evidence", "feedback", "appendix"),
                         False, False),
}

SECTION_IDS = {
    "verdict": "sec-verdict", "mind": "sec-mind", "five_d": "sec-5d", "sdg": "sec-sdg",
    "evidence": "sec-evidence", "greenwashing": "sec-greenwashing", "risks": "sec-risks",
    "actions": "sec-actions", "targets": "sec-targets", "feedback": "sec-feedback",
    "appendix": "sec-appendix",
}
SECTION_TITLES = {
    "verdict": "sec_verdict", "mind": "sec_mind", "five_d": "sec_5d", "sdg": "sec_sdg",
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


def _verdict(decision: dict[str, Any] | None, fd: dict | None, t) -> dict[str, Any]:  # type: ignore[no-untyped-def]
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
    }
    return {"material": [to_row(a) for a in material[:8]], "other": [int(a["goal"]) for a in other]}


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
    return {
        "score": float(gw.get("overall_score") or 0),
        "classification": t(f"gwc_{gw.get('classification', '')}"),
        "components": [
            {"label": t(f"gw_{k}"), "value": float(subs.get(k) or 0)} for k in _GW_COMPONENTS
            if subs.get(k) is not None
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


def _mind(data: dict[str, Any], five_d: dict | None, decision: dict | None, t) -> list[dict[str, str]]:  # type: ignore[no-untyped-def]
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


def _actions(data: dict[str, Any], spec: ReportSpec, t) -> list[dict[str, str]]:  # type: ignore[no-untyped-def]
    seen: set[str] = set()
    out: list[dict[str, str]] = []

    def add(text: str, area: str) -> None:
        key = _norm(text)
        if text and key not in seen:
            seen.add(key)
            out.append({"text": text.strip(), "area": t(area)})

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
    if view["five_d"]:
        fd = view["five_d"]
        tiles.append({"label": t("kpi_5d"), "value": f"{fd['overall']:.1f}", "unit": "/5",
                      "sub": t("kpi_5d_sub", grade=fd["grade"], evidence=t(fd["provenance"]))})
    material = view["sdg"]["material"]
    if material:
        top = material[0]
        tiles.append({"label": t("kpi_sdg"), "value": f"SDG {top['goal']}", "unit": "",
                      "sub": f"{top['name']} · {top['score']:.0f}/100"})
    else:
        tiles.append({"label": t("kpi_sdg"), "value": "—", "unit": "", "sub": t("kpi_sdg_none")})
    if spec.show_greenwashing and view["greenwashing"]:
        gw = view["greenwashing"]
        tiles.append({"label": t("kpi_gw"), "value": f"{gw['score']:.0f}", "unit": "/100",
                      "sub": gw["classification"]})
    ev = view["evidence"]
    dd = (decision or {}).get("dd_coverage_pct") if spec.show_gate else None
    tiles.append({
        "label": t("kpi_evidence"),
        "value": t("kpi_evidence_value", claims=len(ev["claims"])),
        "unit": "",
        "sub": (t("kpi_evidence_sub", metrics=len(ev["metrics"]), dd=f"{dd:.0f}") if dd is not None
                else t("kpi_evidence_sub_nodd", metrics=len(ev["metrics"]))),
    })
    return tiles


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
    view["verdict"] = _verdict(decision, data.get("five_dimensions"), t)
    view["kpis"] = _kpis(view, spec, decision, t)
    view["mind"] = _mind(data, view["five_d"], decision, t)
    view["actions"] = _actions(data, spec, t)
    view["methodology"] = [t("method_1"), t("method_2"), t("method_3")]
    if spec.show_greenwashing:
        view["methodology"].append(t("method_4"))
    if spec.show_gate:
        view["methodology"].append(t("method_5"))

    present = {
        "verdict": decision is not None,
        "kpis": bool(view["kpis"]),
        "mind": bool(view["mind"]),
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
    return body


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
