"""Fund-level regulatory deadline calendar.

This is a fund-manager/LP-facing wrapper around the v4 engagement regulatory
workbench. It exposes the deadline view directly through the SDK and tools
without requiring users to know the consultant engagement-suite action names.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
import yaml

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


class RegulatoryWatchlistItem(BaseModel):
    """One market-wide regulatory milestone (not fund-specific)."""

    event_date: str
    event: str
    jurisdiction: str = "EU"
    days_until: int = 0
    status: Literal["upcoming", "due_soon", "passed"] = "upcoming"


# Market-wide milestones verified by web research 2026-07 (see
# docs/roadmap-updates-2026-07.md). Unlike the per-fund deadline calendar,
# these are fixed calendar dates that apply regardless of fiscal year end.
_REGULATORY_WATCHLIST: list[tuple[str, str, str]] = [
    ("2026-09-27", "ECGT Directive (EU) 2024/825 applies — generic green claims banned", "EU"),
    (
        "2026-10-31",
        "ISSB nature-related disclosures Practice Statement exposure draft (October 2026)",
        "Global",
    ),
    ("2026-12-31", "Revised ESRS + VSME delegated acts expected adopted (Q3/Q4 2026)", "EU"),
    ("2026-11-10", "First California SB 253 Scope 1+2 GHG reports due", "US"),
    ("2027-12-31", "California SB 253 Scope 3 reporting phase begins", "US"),
    (
        "2026-12-15",
        "ISSA 5000 sustainability assurance effective (periods beginning on/after)",
        "Global",
    ),
    ("2026-12-30", "EUDR obligations apply (large/medium operators)", "EU"),
    ("2027-01-01", "Revised ESRS applies (FY2027; early adoption FY2026)", "EU"),
    ("2027-03-19", "CSRD (as amended by Omnibus I) member-state transposition deadline", "EU"),
    ("2028-07-26", "CSDDD member-state transposition deadline", "EU"),
    ("2029-07-26", "CSDDD applies to first wave (>5,000 employees + €1.5B turnover)", "EU"),
    (
        "2029-12-31",
        "SFDR 2.0 expected application (Council: 24-month implementation; trilogue from late 2026)",
        "EU",
    ),
]


def regulatory_watchlist(
    *,
    today: date | None = None,
    jurisdiction: str = "",
    include_passed: bool = False,
) -> list[RegulatoryWatchlistItem]:
    """Return the market-wide regulatory milestone watch-list, soonest first."""
    ref = today or date.today()
    items: list[RegulatoryWatchlistItem] = []
    for event_date, event, event_jurisdiction in _REGULATORY_WATCHLIST:
        if jurisdiction and event_jurisdiction.lower() != jurisdiction.strip().lower():
            continue
        days = (date.fromisoformat(event_date) - ref).days
        if days < 0 and not include_passed:
            continue
        status = "passed" if days < 0 else "due_soon" if days <= 60 else "upcoming"
        items.append(
            RegulatoryWatchlistItem(
                event_date=event_date,
                event=event,
                jurisdiction=event_jurisdiction,
                days_until=days,
                status=status,
            )
        )
    items.sort(key=lambda item: item.event_date)
    return items


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


def issb_summary(path: str | Path | None = None) -> list[dict]:
    data_path = (
        Path(path) if path else Path(__file__).resolve().parents[3] / "data" / "issb_adoption.yaml"
    )
    payload = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    required = {"jurisdiction", "status", "effective", "scope", "assurance_posture", "source"}
    rows = payload.get("jurisdictions", [])
    for index, row in enumerate(rows):
        missing = required - set(row)
        if missing:
            raise ValueError(f"ISSB adoption row {index} missing {sorted(missing)}")
    return rows


def issb_status(jurisdiction: str) -> dict:
    needle = jurisdiction.strip().casefold()
    aliases = {"hk": "hong kong", "hong kong sar": "hong kong", "uk": "united kingdom"}
    needle = aliases.get(needle, needle)
    for row in issb_summary():
        if row["jurisdiction"].casefold() == needle:
            return row
    return {
        "jurisdiction": jurisdiction,
        "status": "unknown",
        "effective": None,
        "scope": "No tracked profile",
        "assurance_posture": "unknown",
        "source": "",
    }


__all__ = [
    "RegulatoryCalendar",
    "RegulatoryCalendarItem",
    "RegulatoryWatchlistItem",
    "build_regulatory_calendar",
    "default_fiscal_year_end",
    "jurisdiction_options",
    "issb_status",
    "issb_summary",
    "regulatory_watchlist",
    "render_regulatory_calendar_text",
]
