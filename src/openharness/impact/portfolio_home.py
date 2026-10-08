"""Portfolio home: one page per fund (v7 W3.4).

Built from saved assessments (web-app reports, ``impact-vision assess``
bundles or any ``{company, created_at, summary, report_data}`` records):

* headline tiles – companies, average 5D, IC-ready count, greenwashing
  flags, deadlines in the next 90 days;
* pipeline – companies by IC-gate status (plus CRM pipeline stages when the
  AssessmentStore has them);
* heat-map – 5 Dimensions and material-SDG scores per company;
* regulatory deadlines – SFDR, CSRD/ESRS, California SB 253/261, UK SDR …
  for the fund's jurisdictions, next 180 days and overdue;
* evidence-review queue – low-confidence AI-extracted claims to confirm, plus
  pending items in the persisted review queues (radar, DDQ drafts, deals);
* needs attention – stale assessments and companies held back by missing data.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any, Iterable

DIMENSIONS = (("what", "What"), ("who", "Who"), ("how_much", "How much"),
              ("contribution", "Contribution"), ("risk", "Risk"))
GATE_ORDER = ("PASS", "WARN", "INSUFFICIENT EVIDENCE", "FAIL")
GATE_LABEL = {"PASS": "IC-ready", "WARN": "Conditional", "INSUFFICIENT EVIDENCE": "Needs data",
              "FAIL": "Do not proceed"}
GATE_TONE = {"PASS": "good", "WARN": "warning", "INSUFFICIENT EVIDENCE": "warning", "FAIL": "critical"}
REVIEW_CONFIDENCE = 0.5
_QUEUE_LABELS = {"regulatory_radar": "Regulatory radar", "ddq_drafts": "DDQ drafts"}
def _gw_flag() -> float:
    from openharness.impact.greenwashing import finding_threshold

    return finding_threshold()


def _when(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _lvl(value: float | None, top: float) -> int:
    if value is None:
        return 0
    return max(1, min(5, int(-(-float(value) * 5 // top))))  # ceil into 1..5


# Geography (as detected or entered) → statutory calendar jurisdictions.
_GEO_JURISDICTIONS: dict[str, tuple[str, ...]] = {
    "hong kong": ("HK",), "china": ("CN",), "mainland china": ("CN",), "singapore": ("SG",),
    "japan": ("JP",), "australia": ("AU",), "united kingdom": ("UK",), "uk": ("UK",),
    "england": ("UK",), "scotland": ("UK",), "united states": ("US",), "usa": ("US",),
    "north america": ("US", "CA"), "canada": ("CA",), "switzerland": ("CH",), "europe": ("EU",),
    "european union": ("EU",), "germany": ("EU",), "france": ("EU",), "netherlands": ("EU",),
    "spain": ("EU",), "italy": ("EU",), "ireland": ("EU",), "sweden": ("EU",), "denmark": ("EU",),
    "belgium": ("EU",), "portugal": ("EU",), "finland": ("EU",), "austria": ("EU",), "poland": ("EU",),
    "nordics": ("EU",),
}


def jurisdictions_for(records: Iterable[dict[str, Any]], domicile: str | Iterable[str] = "") -> list[str]:
    """Calendars that apply: the fund's domicile plus where portfolio companies operate.

    A Kenya-only portfolio of a fund with no domicile set gets no statutory
    calendar (instead of California SB 253).
    """
    codes: list[str] = []
    raw = [domicile] if isinstance(domicile, str) else list(domicile)
    for item in raw:
        codes += [c.strip().upper() for c in str(item).split(",") if c.strip()]
    for record in records:
        geo = str((record.get("summary") or {}).get("geography", "")).strip().lower()
        codes += list(_GEO_JURISDICTIONS.get(geo, ()))
    return list(dict.fromkeys(codes))


def record_from_bundle(bundle: Any, *, link: str = "") -> dict[str, Any]:
    """Adapt a pipeline ``AssessmentBundle`` to a portfolio-home record."""
    return {"company": bundle.company.name, "created_at": time.time(), "summary": bundle.summary(),
            "report_data": bundle.report_data, "link": link}


def build_portfolio_home(
    records: Iterable[dict[str, Any]],
    *,
    fund_name: str = "Portfolio",
    jurisdictions: Iterable[str] = ("EU", "US", "UK", "HK"),
    today: date | None = None,
    stale_days: int = 180,
    pipeline_rows: Iterable[dict[str, Any]] = (),
    deadline_window_days: int = 180,
    review_queues: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """``review_queues`` (name → ``ReviewQueue``, e.g. from
    ``evidence_workflow.list_review_queues()``) adds their pending items to the
    evidence-review list next to the low-confidence claims in saved reports."""
    today = today or datetime.now(timezone.utc).date()
    now = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    rows = sorted(records, key=lambda r: str(r.get("company", "")).lower())

    companies: list[dict[str, Any]] = []
    sdg_goals: dict[int, str] = {}
    for r in rows:
        s = r.get("summary") or {}
        for g in s.get("top_sdgs") or []:
            sdg_goals.setdefault(int(g["goal"]), g.get("name", ""))
    sdg_cols = sorted(sdg_goals)[:8]

    review: list[dict[str, Any]] = []
    attention: list[dict[str, Any]] = []
    for r in rows:
        s, data = r.get("summary") or {}, r.get("report_data") or {}
        fd = data.get("five_dimensions") or {}
        sdg_scores = {int(a["goal"]): a.get("score") for a in data.get("sdg_alignments") or []}
        gate = s.get("gate") or "—"
        created = _when(r.get("created_at") or data.get("generated_at"))
        age = (now - created).days if created else None
        companies.append({
            "name": s.get("company") or r.get("company", ""),
            "meta": " · ".join(x for x in (s.get("sector"), s.get("geography")) if x),
            "link": r.get("link", ""),
            "gate": gate, "gate_label": GATE_LABEL.get(gate, gate.title()), "tone": GATE_TONE.get(gate, ""),
            "five_d": s.get("five_d_score"),
            "greenwashing": s.get("greenwashing_risk"),
            "dims": [{"label": label, "value": (fd.get(key) or {}).get("score"),
                      "lvl": _lvl((fd.get(key) or {}).get("score"), 5)} for key, label in DIMENSIONS],
            "sdgs": [{"goal": g, "value": sdg_scores.get(g), "lvl": _lvl(sdg_scores.get(g), 100)}
                     for g in sdg_cols],
            "age_days": age,
        })
        for claim in data.get("impact_claims") or []:
            conf = claim.get("confidence")
            if isinstance(conf, (int, float)) and conf < REVIEW_CONFIDENCE and not claim.get("negation_detected"):
                review.append({"company": companies[-1]["name"], "text": _clip(claim.get("text", ""), 180),
                               "category": claim.get("category", ""), "confidence": conf,
                               "nesta": claim.get("evidence_strength")})
        if age is not None and age > stale_days:
            attention.append({"company": companies[-1]["name"], "reason": f"Assessed {age} days ago — refresh",
                              "tone": "warning"})
        if gate == "INSUFFICIENT EVIDENCE":
            attention.append({"company": companies[-1]["name"],
                              "reason": "Held back by missing data, not by a negative finding", "tone": "warning"})
        if (s.get("greenwashing_risk") or 0) >= _gw_flag():
            attention.append({"company": companies[-1]["name"],
                              "reason": f"Greenwashing risk {s['greenwashing_risk']:.0f}/100 — review claims",
                              "tone": "critical"})
    for name, queue in (review_queues or {}).items():
        label = _QUEUE_LABELS.get(name, name.replace("_", " ").replace(":", ": "))
        for item in queue.items:
            if item.review.decision != "pending":
                continue
            review.append({"company": label, "text": _clip(item.review.extracted_text, 180),
                           "category": f"review queue · {item.verdict.replace('_', ' ')}",
                           "confidence": item.review.confidence, "nesta": None, "queue": name})
    review.sort(key=lambda x: (x["confidence"], x["company"]))

    deadlines = _deadlines(jurisdictions, today, deadline_window_days)
    for d in deadlines:
        if d["statutory"] and 0 <= d["days"] <= 60:
            attention.insert(0, {"company": d["framework"], "tone": "critical",
                                 "reason": f"{d['title']} due {d['due']} — {d['days']} days away"})
    five_d = [c["five_d"] for c in companies if isinstance(c["five_d"], (int, float))]
    gw = [c["greenwashing"] for c in companies if isinstance(c["greenwashing"], (int, float))]
    gate_counts = {g: sum(1 for c in companies if c["gate"] == g) for g in GATE_ORDER}
    stages: dict[str, int] = {}
    for p in pipeline_rows:
        stage = str(p.get("pipeline_stage") or p.get("stage") or "").strip() or "unstaged"
        stages[stage] = stages.get(stage, 0) + 1

    return {
        "fund_name": fund_name,
        "as_of": today.isoformat(),
        "jurisdictions": list(jurisdictions),
        "kpis": [
            {"label": "Companies", "value": str(len(companies)), "sub": "assessed"},
            {"label": "Average 5D", "value": f"{sum(five_d) / len(five_d):.1f}" if five_d else "—",
             "sub": "out of 5", "meter": (sum(five_d) / len(five_d) / 5 * 100) if five_d else 0},
            {"label": "IC-ready", "value": f"{gate_counts['PASS']}/{len(companies)}",
             "sub": f"{gate_counts['INSUFFICIENT EVIDENCE']} need data"},
            {"label": "Greenwashing flags", "value": str(sum(1 for v in gw if v >= _gw_flag())),
             "sub": f"risk ≥ {_gw_flag():g}/100"},
            {"label": "Deadlines ≤ 90 days",
             "value": str(sum(1 for d in deadlines if d["days"] <= 90)),
             "sub": f"{sum(1 for d in deadlines if d['status'] == 'overdue')} overdue"},
        ],
        "pipeline": [{"gate": g, "label": GATE_LABEL[g], "tone": GATE_TONE[g], "count": gate_counts[g],
                      "pct": (gate_counts[g] / len(companies) * 100) if companies else 0}
                     for g in GATE_ORDER],
        "stages": sorted(stages.items(), key=lambda kv: -kv[1]),
        "companies": companies,
        "dim_labels": [label for _, label in DIMENSIONS],
        "sdg_cols": [{"goal": g, "name": sdg_goals[g]} for g in sdg_cols],
        "deadlines": deadlines[:10],
        "deadlines_total": len(deadlines),
        "review": review[:8],
        "review_total": len(review),
        "attention": attention,
    }


def _deadlines(jurisdictions: Iterable[str], today: date, window: int) -> list[dict[str, Any]]:
    from openharness.impact.regulatory_calendar import build_regulatory_calendar

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for j in jurisdictions:
        try:
            cal = build_regulatory_calendar(jurisdiction=j)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001 - unknown jurisdiction: skip, don't break the page
            continue
        for item in cal.items:
            due = date.fromisoformat(item.due_date[:10])
            days = (due - today).days
            key = (item.framework, item.title)
            if key in seen or days > window or item.status == "met":
                continue
            seen.add(key)
            out.append({"jurisdiction": j, "framework": item.framework, "title": item.title,
                        "due": item.due_date[:10], "days": days, "statutory": item.statutory,
                        "status": "overdue" if days < 0 else "due_soon" if days <= 60 else "upcoming"})
    return sorted(out, key=lambda d: (d["days"], d["framework"]))


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render_portfolio_home(view: dict[str, Any], *, theme: str = "") -> str:
    from openharness.impact.report_templates.decision_report import _env, design_css, monogram
    from openharness.impact.report_templates.report_v2 import SDG_COLORS, sdg_text_colour

    for c in view["companies"]:
        c["monogram"] = monogram(c["name"])
    for col in view["sdg_cols"]:
        col["color"], col["ink"] = SDG_COLORS.get(col["goal"], "#888"), sdg_text_colour(col["goal"])
    return _env().get_template("portfolio_home.html.j2").render(
        v=view, css=design_css(), theme=theme if theme in {"light", "dark"} else "")


__all__ = ["build_portfolio_home", "record_from_bundle", "render_portfolio_home"]
