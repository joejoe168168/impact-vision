"""Annual monitoring linked to the company record (roadmap v8 W3.4).

Once a company is invested, the fund asks once a year for the results it
expected at IC:

1. :func:`create_request` builds the request from the expectations on the
   company record (reach, depth of change, tonnes) plus a few VSME Basic Module
   datapoints, and returns a private portal link for the investee. Only the
   link's hash is stored.
2. The investee answers at ``/portal/<token>``. :func:`submit_response` turns
   the answers into a short results statement and scores it with the same
   methodology as the IC assessment, so the actual is like-for-like with the
   expectation. It is filed on the record as an *actual* for the period.
3. :func:`variance_explanations` says why actual differs from expected:
   reach, depth or evidence, plus the company's own explanation.
4. :func:`due_reminders` / :func:`send_reminders` remind the contact by email
   (SMTP, when configured) and fire a ``monitoring_reminder`` webhook,
   14 days before the due date, on it, and weekly once overdue.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import smtplib
from datetime import date, datetime, timezone
from email.message import EmailMessage
from functools import lru_cache
from typing import Any

import yaml

from impact_vision.impact._paths import data_path

KIND = "monitoring_request"
INDEX_TENANT, INDEX_KIND = "_portal", "portal_token"
EVIDENCE_CHOICES = {
    "records": "Our own monitoring records",
    "before_after": "Before/after survey of the same people",
    "comparison": "Independent study against a comparison group",
}
_EVIDENCE_PHRASE = {
    "records": "(from our monitoring records)",
    "before_after": "(survey of the same customers, before and after, versus the baseline)",
    "comparison": "(independent evaluation versus a matched comparison group)",
}
REMIND_BEFORE_DAYS = 14
REMIND_EVERY_DAYS = 7


@lru_cache(maxsize=1)
def vsme_datapoints() -> list[dict[str, str]]:
    path = data_path("monitoring/vsme_basic.yaml")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return list((doc or {}).get("datapoints") or [])


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _store() -> Any:
    from impact_vision.impact.state_store import get_state_store

    return get_state_store()


def _latest_expected(company: str) -> list[dict[str, Any]]:
    from impact_vision.impact.company_record import company_timeline

    rows = []
    for cmp in company_timeline(company)["expected_vs_actual"]:
        if cmp.get("expected"):
            rows.append(cmp["expected"])
    return rows


def _questions(company: str, period: str, expected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outcomes = {e["outcome"]: e for e in expected} or {"people": {"stakeholder": "people", "reach": None}}
    qs: list[dict[str, Any]] = []
    if "people" in outcomes:
        e = outcomes["people"]
        who = e.get("stakeholder") or "people"
        plan = f" (plan at investment: {e['reach']:,.0f})" if e.get("reach") else ""
        qs += [
            {"id": "reach", "type": "number", "required": True,
             "label": f"How many {who} did {company} serve in {period}?{plan}"},
            {"id": "depth_measure", "type": "text",
             "label": f"Which change do you measure for the {who}? (e.g. household income, energy spend, test scores)"},
            {"id": "depth_pct", "type": "number", "label": "By how much did it change, in %? (use a minus sign for a fall)"},
            {"id": "evidence", "type": "select", "options": EVIDENCE_CHOICES, "label": "How do you know?"},
        ]
    if "climate" in outcomes:
        e = outcomes["climate"]
        plan = f" (plan at investment: {e['reach']:,.0f})" if e.get("reach") else ""
        qs.append({"id": "tco2e", "type": "number", "required": True,
                   "label": f"Tonnes of CO2e avoided or removed in {period}{plan}"})
    qs.append({"id": "verified", "type": "checkbox",
               "label": "These figures were verified by an independent third party"})
    for dp in vsme_datapoints():
        qs.append({"id": dp["id"], "type": "number", "label": f"{dp['label']} ({dp['unit']})", "ref": dp["ref"]})
    qs.append({"id": "variance", "type": "textarea",
               "label": "If results differ from the plan, what explains the difference?"})
    return qs


def create_request(company: str, period: str, *, due: str = "", contact_email: str = "",
                   created_by: str = "") -> dict[str, Any]:
    """Create the yearly request; the result's ``token`` is shown once."""
    from impact_vision.impact.company_record import POST_INVESTMENT, company_timeline
    from impact_vision.impact.identity import current_tenant
    from impact_vision.impact.state_store import raw_state_store

    timeline = company_timeline(company)
    if timeline["stage"] not in POST_INVESTMENT - {"exited"}:
        raise ValueError(f"{company} is at stage {timeline['stage'] or 'unknown'}; "
                         "annual monitoring starts once it is invested")
    if not (period.isdigit() and len(period) == 4):
        raise ValueError("period must be a year, e.g. 2026")
    due = due or f"{int(period) + 1}-03-31"
    date.fromisoformat(due)
    expected = _latest_expected(company)
    token = secrets.token_urlsafe(32)
    key = f"{company}|{period}"
    request = {
        "key": key, "company": company, "period": period, "due": due, "contact_email": contact_email.strip(),
        "created_at": _now(), "created_by": created_by, "status": "open", "token_hash": _hash(token),
        "expected": [{k: e.get(k) for k in ("outcome", "unit", "stakeholder", "reach", "p10", "p50", "p90",
                                            "evidence_quality")} for e in expected],
        "questions": _questions(company, period, expected), "reminders": [],
    }
    _store().put("default", KIND, key, request)
    raw_state_store().put(INDEX_TENANT, INDEX_KIND, _hash(token), {"tenant": current_tenant(), "key": key})
    return {**request, "token": token}


def list_requests(company: str = "") -> list[dict[str, Any]]:
    store = _store()
    rows = [r for k in store.keys("default", KIND) if (r := store.get("default", KIND, k))]
    return [r for r in rows if not company or r["company"] == company]


def resolve_token(token: str) -> tuple[str, dict[str, Any]] | None:
    """(tenant, request) for a portal token, or None. Constant-time on the hash lookup."""
    from impact_vision.impact.identity import Identity, acting_as
    from impact_vision.impact.state_store import raw_state_store

    if not token or len(token) > 200:
        return None
    index = raw_state_store().get(INDEX_TENANT, INDEX_KIND, _hash(token))
    if not index:
        return None
    with acting_as(Identity(sub="portal", tenant_id=index["tenant"], roles=("viewer",), auth="portal")):
        request = _store().get("default", KIND, index["key"])
    if not request or request.get("token_hash") != _hash(token):
        return None
    return index["tenant"], request


def _num(answers: dict[str, Any], key: str) -> float | None:
    raw = str(answers.get(key, "")).replace(",", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{key}: {raw!r} is not a number") from exc


def results_statement(request: dict[str, Any], answers: dict[str, Any]) -> str:
    """The submission as a short document the standard pipeline can score."""
    company, period = request["company"], request["period"]
    who = next((e.get("stakeholder") for e in request["expected"] if e["outcome"] == "people"), "") or "people"
    lines = [f"# {company} — annual monitoring {period}", "",
             f"{company} reports its impact results for {period}.", "", f"## Results {period}"]
    evidence = _EVIDENCE_PHRASE.get(str(answers.get("evidence") or "records"), _EVIDENCE_PHRASE["records"])
    reach = _num(answers, "reach")
    if reach is not None:
        lines.append(f"- {reach:,.0f} {who} served in {period} {evidence}.")
    depth = _num(answers, "depth_pct")
    if depth is not None:
        measure = str(answers.get("depth_measure") or "Their main outcome").strip().rstrip(".")[:120]
        verb = "improved by" if depth >= 0 else "fell by"
        lines.append(f"- {measure[:1].upper() + measure[1:]} {verb} {abs(depth):g}% for the {who} {evidence}.")
    tonnes = _num(answers, "tco2e")
    if tonnes is not None:
        lines.append(f"- {tonnes:,.0f} tCO2e avoided in {period} {evidence}.")
    if str(answers.get("verified", "")).lower() in {"1", "true", "on", "yes"}:
        lines.append("- These figures were verified by an independent third-party auditor.")
    for dp in vsme_datapoints():
        value = _num(answers, dp["id"])
        if value is not None:
            lines.append(f"- {dp['label']}: {value:,.0f} {dp['unit']} ({dp['ref']}).")
    return "\n".join(lines) + "\n"


def submit_response(token: str, answers: dict[str, Any], *, submitted_by: str = "") -> dict[str, Any]:
    """Score and file the investee's answers as the period's actuals."""
    from impact_vision.impact.company_record import add_event, company_timeline
    from impact_vision.impact.identity import Identity, acting_as
    from impact_vision.impact.pipeline import assess_document, save_bundle

    found = resolve_token(token)
    if not found:
        raise PermissionError("unknown or revoked link")
    tenant, request = found
    if request["status"] == "submitted":
        raise ValueError("this request has already been answered")
    missing = [q["label"] for q in request["questions"] if q.get("required") and _num(answers, q["id"]) is None]
    if missing:
        raise ValueError("Please answer: " + "; ".join(missing))
    clean = {q["id"]: str(answers.get(q["id"], "")).strip()[:2000] for q in request["questions"]}
    text = results_statement(request, clean)
    with acting_as(Identity(sub="portal", tenant_id=tenant, roles=("analyst",), auth="portal")):
        entry = company_timeline(request["company"])
        bundle = assess_document(text, name=request["company"], sector=entry.get("sector") or "",
                                 geography=entry.get("geography") or "")
        assessment_id = save_bundle(bundle, source_label=f"Annual monitoring {request['period']}",
                                    period=request["period"])
        if clean.get("variance"):
            add_event(request["company"], "comment", author=submitted_by or request["contact_email"] or "investee",
                      text=clean["variance"], target=f"variance {request['period']}", assessment_id=assessment_id)
        request.update(status="submitted", submitted_at=_now(), answers=clean, assessment_id=assessment_id,
                       statement=text)
        _store().put("default", KIND, request["key"], request)
        explanations = variance_explanations(request["company"])
    return {"company": request["company"], "period": request["period"], "assessment_id": assessment_id,
            "variance": explanations}


def variance_explanations(company: str) -> list[dict[str, Any]]:
    """Why the latest actual differs from the expectation, outcome by outcome."""
    from impact_vision.impact.company_record import company_timeline

    t = company_timeline(company)
    notes = {e["target"]: e["text"] for e in t["events"] if e["kind"] == "comment"
             and str(e.get("target", "")).startswith("variance ")}
    out = []
    for cmp in t["expected_vs_actual"]:
        exp, act = cmp.get("expected"), cmp.get("actual")
        if not (exp and act):
            continue
        drivers = []
        if exp.get("reach") and act.get("reach"):
            pct = round((act["reach"] - exp["reach"]) / exp["reach"] * 100)
            if abs(pct) >= 10:
                what = "reach" if cmp["outcome"] == "people" else "tonnes per year"
                drivers.append(f"{what} {'+' if pct > 0 else ''}{pct}% against plan "
                               f"({act['reach']:,.0f} vs {exp['reach']:,.0f})")
        if exp.get("evidence_quality") is not None and act.get("evidence_quality") is not None:
            diff = round(act["evidence_quality"] - exp["evidence_quality"])
            if abs(diff) >= 5:
                drivers.append(f"evidence quality {'up' if diff > 0 else 'down'} {abs(diff)} points "
                               f"({act['evidence_quality']:.0f}/100)")
        if not drivers and cmp.get("variance_pct") is not None and abs(cmp["variance_pct"]) >= 10:
            drivers.append("depth or duration of change differs from the plan")
        out.append({"outcome": cmp["outcome"], "unit": cmp["unit"], "status": cmp["status"],
                    "variance_pct": cmp.get("variance_pct"), "drivers": drivers,
                    "company_explanation": notes.get(f"variance {act.get('period', '')}", "")})
    return out


# ------------------------------------------------------------------ reminders


def due_reminders(today: date | None = None) -> list[dict[str, Any]]:
    """Open requests that need a reminder today."""
    today = today or date.today()
    due_now = []
    for r in list_requests():
        if r["status"] != "open":
            continue
        due = date.fromisoformat(r["due"])
        last = max((date.fromisoformat(x["at"][:10]) for x in r.get("reminders") or []), default=None)
        days_left = (due - today).days
        window = days_left <= REMIND_BEFORE_DAYS
        spaced = last is None or (today - last).days >= REMIND_EVERY_DAYS or (days_left == 0 and last < today)
        if window and spaced:
            due_now.append({**r, "days_left": days_left})
    return due_now


def _email(to: str, subject: str, body: str) -> str:
    host = os.environ.get("IMPACT_VISION_SMTP_HOST", "").strip()
    if not host or not to:
        return "skipped (no SMTP host)" if not host else "skipped (no contact email)"
    msg = EmailMessage()
    msg["From"] = os.environ.get("IMPACT_VISION_SMTP_FROM", "impact-vision@localhost")
    msg["To"], msg["Subject"] = to, subject
    msg.set_content(body)
    port = int(os.environ.get("IMPACT_VISION_SMTP_PORT", "587"))
    user, password = os.environ.get("IMPACT_VISION_SMTP_USER", ""), os.environ.get("IMPACT_VISION_SMTP_PASSWORD", "")
    smtp_cls = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
    with smtp_cls(host, port, timeout=20) as smtp:
        if port != 465:
            smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)
    return "sent"


def send_reminders(*, base_url: str = "", today: date | None = None, dry_run: bool = False,
                   webhook: Any = None) -> list[dict[str, Any]]:
    """Remind every contact whose request is due; returns what was done.

    The portal token is never stored, so the email links to the fund's portal
    page for the company and asks the contact to use the link they were sent.
    ``webhook`` is an optional ``callable(event, payload)``.
    """
    done = []
    for r in due_reminders(today):
        when = "are due today" if r["days_left"] == 0 else (
            f"are due in {r['days_left']} days" if r["days_left"] > 0 else f"were due {-r['days_left']} days ago")
        subject = f"{r['company']}: {r['period']} impact results {when}"
        body = (f"Hello,\n\nThe {r['period']} annual impact results for {r['company']} {when} ({r['due']}).\n"
                "Please use the private link you received with the request"
                + (f" ({base_url.rstrip('/')}/portal/…)" if base_url else "") + ".\n\nThank you.\n")
        result = {"company": r["company"], "period": r["period"], "days_left": r["days_left"],
                  "email": "dry run" if dry_run else "", "webhook": ""}
        if not dry_run:
            try:
                result["email"] = _email(r["contact_email"], subject, body)
            except (OSError, smtplib.SMTPException) as exc:
                result["email"] = f"failed: {exc}"
            if webhook is not None:
                try:
                    webhook("monitoring_reminder", {"company": r["company"], "period": r["period"],
                                                    "due": r["due"], "days_left": r["days_left"]})
                    result["webhook"] = "fired"
                except Exception as exc:  # noqa: BLE001
                    result["webhook"] = f"failed: {exc}"
            stored = _store().get("default", KIND, r["key"]) or r
            stored.setdefault("reminders", []).append({"at": (today or date.today()).isoformat(),
                                                       "email": result["email"], "webhook": result["webhook"]})
            _store().put("default", KIND, r["key"], stored)
        done.append(result)
    return done


def render_portal(request: dict[str, Any], *, values: dict[str, Any] | None = None, error: str = "",
                  done: bool = False) -> str:
    from impact_vision.impact.report_templates.decision_report import _env, design_css

    return str(_env().get_template("portal.html.j2").render(r=request, values=values or {}, error=error,
                                                         done=done or request.get("status") == "submitted",
                                                         css=design_css()))


__all__ = ["render_portal", "EVIDENCE_CHOICES", "create_request", "due_reminders", "list_requests", "resolve_token",
           "results_statement", "send_reminders", "submit_response", "variance_explanations", "vsme_datapoints"]
