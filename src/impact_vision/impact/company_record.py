"""The company record: one company from pipeline to exit (roadmap v8 Wave 3).

Builds on the existing ``pipeline`` table (stages + transitions) and the
``assessments`` table, and adds what an investment team needs over time:

* **Expected vs actual.**  Every assessment made before investment stores its
  expected impact (P10/P50/P90) as the ex-ante expectation; assessments made
  once the company is invested or being monitored store *actual* results.
  :func:`company_timeline` compares the latest actual with the expectation set
  at IC (Impact Frontiers performance-reporting norms: expected vs actual).
* **Collaboration.**  Comments, IC approvals / declines and corrections, each
  attributed and time-stamped (``company_events``), recorded as the human
  review that ISSA 5000 and the AI Act's editorial-responsibility route ask for.
* **Stages.**  ``sourcing → screening → dd_in_progress → ic_review → invested →
  monitoring → exited`` (or ``passed``), with every move logged.
"""
from __future__ import annotations

from typing import Any

from impact_vision.impact.models import PIPELINE_STAGES

PRE_INVESTMENT = {"sourcing", "screening", "dd_in_progress", "ic_review"}
POST_INVESTMENT = {"invested", "monitoring", "exited"}
EVENT_KINDS = {"comment", "approval", "decline", "correction", "stage"}


def _store():  # type: ignore[no-untyped-def]
    from impact_vision.impact.storage import get_assessment_store

    return get_assessment_store()


def record_assessment(bundle: Any, assessment_id: str = "", *, period: str = "", stage: str = "") -> dict[str, Any]:
    """File an assessment on the company record.

    New companies enter the pipeline at ``screening``. Before investment the
    expected impact is stored as an expectation; once invested it is stored as
    an actual result for *period* (default: the assessment date's year).
    """
    store = _store()
    company = bundle.company
    name = company.name
    entry = store.get_pipeline_entry(name)
    if entry is None:
        store.upsert_pipeline_entry(name, pipeline_stage=stage or "screening", sector=company.sector,
                                    geography=company.geography)
        entry = store.get_pipeline_entry(name) or {}
    elif stage and stage != entry.get("pipeline_stage"):
        store.transition_stage(name, stage, actor="impact-vision", rationale="set with assessment")
        entry = store.get_pipeline_entry(name) or entry
    current_stage = str(entry.get("pipeline_stage") or "screening")
    block = bundle.report_data.get("expected_impact") or {}
    kind = "actual" if current_stage in POST_INVESTMENT else "expected"
    eq = (block.get("evidence_quality") or {}).get("score")
    when = str(bundle.report_data.get("generated_at", ""))[:4]
    for o in block.get("outcomes") or []:
        reach = next((f["median"] for f in o.get("factors", []) if f["name"] in {"Reach", "Tonnes per year"}), None)
        store.add_outcome_record(name, {
            "assessment_id": assessment_id, "record_kind": kind, "outcome": o["kind"], "unit": o["unit"],
            "stakeholder": o.get("stakeholder", ""), "reach": reach, "p10": o["p10"], "p50": o["p50"],
            "p90": o["p90"], "evidence_quality": eq, "period": period or when, "stage": current_stage,
            "source": bundle.source_label,
        })
    return {"company": name, "stage": current_stage, "record_kind": kind}


def set_stage(company_name: str, stage: str, *, actor: str = "", rationale: str = "") -> dict[str, Any]:
    if stage not in PIPELINE_STAGES:
        raise ValueError(f"Unknown stage {stage!r}; use one of {', '.join(PIPELINE_STAGES)}")
    store = _store()
    if store.get_pipeline_entry(company_name) is None:
        store.upsert_pipeline_entry(company_name, pipeline_stage=stage)
    else:
        store.transition_stage(company_name, stage, actor=actor, rationale=rationale)
    store.add_company_event(company_name, "stage", author=actor, target=stage, text=rationale)
    return company_timeline(company_name)


def add_event(company_name: str, kind: str, *, author: str = "", text: str = "", target: str = "",
              assessment_id: str = "") -> dict[str, Any]:
    if kind not in EVENT_KINDS - {"stage"}:
        raise ValueError("kind must be one of comment, approval, decline, correction")
    if kind in {"approval", "decline"} and not author.strip():
        raise ValueError("An IC approval or decline needs the reviewer's name")
    _store().add_company_event(company_name, kind, author=author.strip(), text=text.strip(), target=target,
                               assessment_id=assessment_id)
    return company_timeline(company_name)


def _comparison(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest actual vs the last expectation set before investment, per outcome."""
    rows = []
    for outcome in ("people", "climate"):
        expected = [r for r in records if r["outcome"] == outcome and r["record_kind"] == "expected"]
        actual = [r for r in records if r["outcome"] == outcome and r["record_kind"] == "actual"]
        if not expected and not actual:
            continue
        exp = expected[-1] if expected else None
        act = actual[-1] if actual else None
        row: dict[str, Any] = {"outcome": outcome, "unit": (exp or act)["unit"],
                               "expected": exp, "actual": act, "status": "no actual yet" if act is None else ""}
        if exp and act and exp["p50"]:
            row["variance_pct"] = round((act["p50"] - exp["p50"]) / exp["p50"] * 100)
            if act["p50"] < exp["p10"]:
                row["status"] = "below the expected range"
            elif act["p50"] > exp["p90"]:
                row["status"] = "above the expected range"
            else:
                row["status"] = "within the expected range"
        rows.append(row)
    return rows


def company_timeline(company_name: str) -> dict[str, Any]:
    """Everything on file for one company, oldest first."""
    store = _store()
    entry = store.get_pipeline_entry(company_name) or {}
    assessments = []
    for a in store.list_assessments_for(company_name):
        summary = (a.get("metadata") or {}).get("summary") or {}
        assessments.append({
            "id": str(a.get("id", "")), "created_at": a.get("created_at", ""),
            "source": (a.get("metadata") or {}).get("source", ""), "gate": summary.get("gate"),
            "evidence_quality": summary.get("evidence_quality"), "expected_impact": summary.get("expected_impact"),
        })
    records = store.list_outcome_records(company_name)
    events = store.list_company_events(company_name)
    approvals = [e for e in events if e["kind"] in {"approval", "decline"}]
    return {
        "company": company_name,
        "stage": entry.get("pipeline_stage", ""),
        "sector": entry.get("sector", ""),
        "geography": entry.get("geography", ""),
        "stages": list(PIPELINE_STAGES),
        "transitions": store.get_transitions(company_name),
        "assessments": assessments,
        "outcomes": records,
        "expected_vs_actual": _comparison(records),
        "events": events,
        "ic_decision": approvals[-1] if approvals else None,
    }


def list_companies() -> list[dict[str, Any]]:
    """Pipeline and portfolio in one list, with each company's latest numbers."""
    store = _store()
    out = []
    for entry in store.list_pipeline(limit=500):
        name = entry["company_name"]
        latest = (store.list_assessments_for(name) or [None])[-1]
        summary = ((latest or {}).get("metadata") or {}).get("summary") or {}
        out.append({
            "company": name, "stage": entry.get("pipeline_stage", ""),
            "portfolio": entry.get("pipeline_stage") in POST_INVESTMENT,
            "sector": entry.get("sector", ""), "geography": entry.get("geography", ""),
            "gate": summary.get("gate"), "expected_impact": summary.get("expected_impact"),
            "evidence_quality": summary.get("evidence_quality"), "updated_at": entry.get("updated_at", ""),
        })
    return out


# ------------------------------------------------------------------ exit (W3.6)
_NEG_CATEGORY = {"labour": "supply_chain", "supply": "supply_chain", "data": "governance", "pollution": "climate",
                 "carbon": "climate", "emission": "climate", "water": "climate", "overindebt": "stakeholder",
                 "pricing": "stakeholder", "access": "stakeholder", "displacement": "stakeholder",
                 "safety": "stakeholder", "quality": "stakeholder", "waste": "climate"}


def exit_assessment(company_name: str, *, exit_date: str = "") -> dict[str, Any]:
    """OPIM Principle 8 residual-impact score, pre-filled from the company record."""
    from impact_vision.impact.exit_impact import (
        ExitDurabilityRisk,
        PostExitFollowUp,
        build_exit_plan,
        score_exit_impact,
    )
    from impact_vision.impact.models import Company, ImpactClaim

    store = _store()
    history = store.list_assessments_for(company_name)
    if not history:
        raise ValueError(f"No assessments on record for {company_name!r}")
    latest = history[-1]
    meta = latest.get("metadata") or {}
    company = Company(**{k: v for k, v in (latest.get("company") or {}).items() if k in Company.model_fields})
    claims = [ImpactClaim(**{k: v for k, v in c.items() if k in ImpactClaim.model_fields})
              for c in meta.get("impact_claims") or [] if isinstance(c, dict)]
    risks: list[ExitDurabilityRisk] = []
    for i, r in enumerate((meta.get("negative_impacts") or {}).get("items", [])):
        if r.get("band") == "low":
            continue
        category = next((v for k, v in _NEG_CATEGORY.items() if k in r["id"]), "stakeholder")
        risks.append(ExitDurabilityRisk(
            risk_id=f"neg-{i}", category=category, description=r["impact"],  # type: ignore[arg-type]
            likelihood="possible" if r.get("controlled") else "likely",
            severity="major" if r.get("severity", 1) >= 3 else "moderate",
            mitigation="; ".join(r.get("evidence") or []), accepted=bool(r.get("controlled"))))
    timeline = company_timeline(company_name)
    for row in timeline["expected_vs_actual"]:
        if "below" in (row.get("status") or ""):
            risks.append(ExitDurabilityRisk(
                risk_id=f"under-{row['outcome']}", category="commercial",
                description=f"{row['outcome']} impact is {row['status']} ({row.get('variance_pct')}% vs IC)",
                likelihood="likely", severity="major"))
    metric_ids = sorted((company.reported_metrics or {}).keys())[:5]
    follow_ups = [PostExitFollowUp(follow_up_id=f"fu-{m}", description=f"Collect reported metrics at {m}",
                                   period=m, metric_ids=metric_ids) for m in ("12m", "24m", "36m")]
    plan = build_exit_plan(company=company, exit_date=exit_date, risks=risks, follow_ups=follow_ups,
                           claims=claims)
    score = score_exit_impact(plan)
    store.add_company_event(company_name, "comment", author="impact-vision", target="exit",
                            text=f"Exit assessment: residual impact {score.residual_score}/100 ({score.band}).")
    return {"company": company_name, "score": score.model_dump(mode="json"),
            "risks": [r.model_dump(mode="json") for r in risks],
            "follow_ups": [f.model_dump(mode="json") for f in follow_ups]}


# ------------------------------------------------------------- LP report (W3.6)
def lp_report_view(fund_name: str = "Portfolio") -> dict[str, Any]:
    """Fund-level LP view from the record: invested companies, expected vs actual."""
    from datetime import date

    rows = []
    totals: dict[str, dict[str, float]] = {}
    for c in list_companies():
        if not c["portfolio"]:
            continue
        t = company_timeline(c["company"])
        for cmp in t["expected_vs_actual"]:
            unit = cmp["unit"]
            agg = totals.setdefault(unit, {"expected": 0.0, "actual": 0.0, "expected_matched": 0.0, "reporting": 0})
            if cmp.get("expected"):
                agg["expected"] += float(cmp["expected"]["p50"])
            if cmp.get("actual"):
                agg["actual"] += float(cmp["actual"]["p50"])
                agg["reporting"] += 1
                if cmp.get("expected"):
                    # Variance only compares companies that have both (like with like).
                    agg["expected_matched"] += float(cmp["expected"]["p50"])
        rows.append({"company": c["company"], "stage": c["stage"], "sector": c["sector"],
                     "geography": c["geography"], "evidence_quality": c["evidence_quality"],
                     "comparisons": t["expected_vs_actual"], "ic_decision": t["ic_decision"]})
    return {"fund_name": fund_name, "as_of": date.today().isoformat(), "companies": rows,
            "totals": [{"unit": u, **v} for u, v in totals.items()],
            "pipeline": sum(1 for c in list_companies() if not c["portfolio"])}


def render_lp_report(view: dict[str, Any], *, theme: str = "") -> str:
    from impact_vision.impact.ai_provenance import machine_marking, mark_html
    from impact_vision.impact.report_templates.decision_report import _env, _sig, design_css

    html = _env().get_template("lp_report.html.j2").render(
        v=view, css=design_css(), sig=_sig, theme=theme if theme in {"light", "dark"} else "")
    return mark_html(html, machine_marking())


__all__ = ["add_event", "company_timeline", "exit_assessment", "list_companies", "lp_report_view",
           "record_assessment", "render_lp_report", "set_stage"]
