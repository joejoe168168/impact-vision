"""Engagement view: one page across a consultant's engagements.

This is the W3.2 "engagement view" that waited for persistence (W5.3). It is
built from the persisted :class:`~openharness.impact.engagements.workspace.EngagementWorkspace`:

* headline tiles: active engagements, deliverables awaiting review, overdue
  items, items due in the next 14 days;
* one card per engagement: status, deliverable and checklist completion, the
  open deliverables, and the next due or overdue items.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable

ACTIVE = {"proposal", "active"}  # vs on_hold / closed / cancelled
DONE_DELIVERABLE = {"final", "cancelled"}
DONE_CHECKLIST = {"completed", "skipped"}
_STATE_TONE = {"final": "good", "client_review": "warning", "draft": "", "in_progress": "",
               "planned": "", "cancelled": ""}
SOON_DAYS = 14


def _due(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _item(kind: str, title: str, due: date | None, owner: str, today: date) -> dict[str, Any]:
    days = (due - today).days if due else None
    status = "overdue" if days is not None and days < 0 else "due_soon" if days is not None and days <= SOON_DAYS else ""
    return {"kind": kind, "title": title, "due": due.isoformat() if due else "", "days": days,
            "status": status, "owner": owner}


def build_engagement_home(engagements: Iterable[Any], *, today: date | None = None,
                          title: str = "Engagements") -> dict[str, Any]:
    today = today or datetime.now(timezone.utc).date()
    cards: list[dict[str, Any]] = []
    overdue = soon = in_review = active = 0
    for eng in sorted(engagements, key=lambda e: (e.status not in ACTIVE, e.name.lower())):
        is_active = eng.status in ACTIVE
        active += is_active
        open_deliverables = [d for d in eng.deliverables if d.state not in DONE_DELIVERABLE]
        in_review += sum(1 for d in eng.deliverables if d.state == "client_review")
        upcoming = [
            _item("Deliverable", d.name, _due(d.due_date), d.owner, today)
            for d in open_deliverables if _due(d.due_date)
        ] + [
            _item(f"Checklist · {c.phase}", c.title, _due(c.due_date), c.owner, today)
            for c in eng.checklist if c.status not in DONE_CHECKLIST and _due(c.due_date)
        ]
        upcoming.sort(key=lambda i: i["days"])
        if is_active:
            overdue += sum(1 for i in upcoming if i["status"] == "overdue")
            soon += sum(1 for i in upcoming if i["status"] == "due_soon")
        cards.append({
            "id": eng.engagement_id, "name": eng.name, "client": eng.client_name,
            "status": eng.status.replace("_", " "), "active": is_active,
            "bundle": eng.bundle.replace("_", " "),
            "timeline": " → ".join(x for x in (eng.timeline_start, eng.timeline_end) if x),
            # The model's completion properties are fractions (0-1).
            "deliverable_pct": round(100 * float(eng.deliverable_completion_pct or 0)),
            "checklist_pct": round(100 * float(eng.checklist_completion_pct or 0)) if eng.checklist else None,
            "checklist_count": len(eng.checklist),
            "deliverables": [{"name": d.name, "state": d.state.replace("_", " "),
                              "tone": _STATE_TONE.get(d.state, ""), "owner": d.owner,
                              "due": d.due_date[:10]} for d in eng.deliverables],
            "open_deliverables": len(open_deliverables),
            "upcoming": upcoming[:6],
            "overdue": sum(1 for i in upcoming if i["status"] == "overdue"),
            "updated": str(eng.updated_at)[:10],
        })
    return {
        "title": title,
        "as_of": today.isoformat(),
        "kpis": [
            {"label": "Active engagements", "value": str(active), "sub": f"{len(cards)} in total"},
            {"label": "In client review", "value": str(in_review), "sub": "deliverables awaiting sign-off"},
            {"label": "Overdue", "value": str(overdue), "sub": "deliverables + checklist items"},
            {"label": f"Due in {SOON_DAYS} days", "value": str(soon), "sub": "active engagements"},
        ],
        "engagements": cards,
    }


def render_engagement_home(view: dict[str, Any], *, theme: str = "") -> str:
    from openharness.impact.report_templates.decision_report import _env, design_css

    return _env().get_template("engagements.html.j2").render(
        v=view, css=design_css(), theme=theme if theme in {"light", "dark"} else "")


__all__ = ["build_engagement_home", "render_engagement_home"]
