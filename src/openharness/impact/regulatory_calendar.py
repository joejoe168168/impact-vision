"""Fund-level regulatory deadline calendar.

This is a fund-manager/LP-facing wrapper around the v4 engagement regulatory
workbench. It exposes the deadline view directly through the SDK and tools
without requiring users to know the consultant engagement-suite action names.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.engagements.regulatory import (
    Jurisdiction,
    RegulatoryDeadline,
    get_jurisdiction_profile,
    list_jurisdictions,
    schedule_deadlines,
)


class RegulatoryCalendarItem(BaseModel):
    deadline_id: str
    obligation_id: str
    framework: str
    title: str
    due_date: str
    days_until_due: int
    status: Literal["upcoming", "due_soon", "overdue", "met"]
    owner: str = ""
    due_within_60_days: bool = False


class RegulatoryCalendar(BaseModel):
    jurisdiction: str
    fiscal_year_end: str
    frameworks: list[str] = Field(default_factory=list)
    items: list[RegulatoryCalendarItem] = Field(default_factory=list)
    overdue_count: int = 0
    due_within_60_days_count: int = 0
    notes: str = ""


def default_fiscal_year_end(today: date | None = None) -> date:
    """Return a sane default fiscal year end for calendar previews."""
    today = today or date.today()
    return date(today.year, 12, 31)


def build_regulatory_calendar(
    *,
    jurisdiction: Jurisdiction,
    fiscal_year_end: date | str | None = None,
    engagement_id: str = "",
    owner: str = "",
) -> RegulatoryCalendar:
    """Build a jurisdiction-specific regulatory deadline calendar."""
    fy_end = fiscal_year_end or default_fiscal_year_end()
    if isinstance(fy_end, str):
        fy_end_date = date.fromisoformat(fy_end[:10])
    else:
        fy_end_date = fy_end

    profile = get_jurisdiction_profile(jurisdiction)
    deadlines = schedule_deadlines(
        engagement_id=engagement_id or f"{jurisdiction.lower()}-calendar",
        jurisdiction=jurisdiction,
        fiscal_year_end=fy_end_date,
        owner=owner,
    )
    items = [_calendar_item(deadline) for deadline in deadlines]
    return RegulatoryCalendar(
        jurisdiction=jurisdiction,
        fiscal_year_end=fy_end_date.isoformat(),
        frameworks=profile.frameworks,
        items=items,
        overdue_count=sum(1 for item in items if item.status == "overdue"),
        due_within_60_days_count=sum(1 for item in items if item.due_within_60_days),
        notes=profile.notes,
    )


def _calendar_item(deadline: RegulatoryDeadline) -> RegulatoryCalendarItem:
    days = deadline.days_until_due
    return RegulatoryCalendarItem(
        deadline_id=deadline.deadline_id,
        obligation_id=deadline.obligation_id,
        framework=deadline.framework,
        title=deadline.title,
        due_date=deadline.due_date,
        days_until_due=days,
        status=deadline.status,
        owner=deadline.owner,
        due_within_60_days=0 <= days <= 60,
    )


def render_regulatory_calendar_text(calendar: RegulatoryCalendar) -> str:
    """Render a terminal-friendly regulatory calendar."""
    lines = [
        f"Regulatory Deadline Calendar - {calendar.jurisdiction}",
        f"Fiscal year end: {calendar.fiscal_year_end}",
        f"Frameworks: {', '.join(calendar.frameworks)}",
        f"Overdue: {calendar.overdue_count} | Due in 60 days: {calendar.due_within_60_days_count}",
        "",
        f"{'Due date':<12} {'Status':<10} {'Framework':<18} Obligation",
        "-" * 80,
    ]
    for item in calendar.items:
        lines.append(
            f"{item.due_date:<12} {item.status:<10} {item.framework:<18} "
            f"{item.title} ({item.days_until_due:+}d)"
        )
    if calendar.notes:
        lines.extend(["", f"Notes: {calendar.notes}"])
    return "\n".join(lines)


def jurisdiction_options() -> list[dict[str, object]]:
    """Return lightweight jurisdiction metadata for UIs/tools."""
    return [
        {
            "jurisdiction": profile.jurisdiction,
            "frameworks": profile.frameworks,
            "obligations": len(profile.obligations),
            "notes": profile.notes,
        }
        for profile in list_jurisdictions()
    ]


__all__ = [
    "RegulatoryCalendar",
    "RegulatoryCalendarItem",
    "build_regulatory_calendar",
    "default_fiscal_year_end",
    "jurisdiction_options",
    "render_regulatory_calendar_text",
]
