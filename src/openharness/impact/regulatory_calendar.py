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
from openharness.impact.issb_reporting import s2_amendment_summary
from openharness.impact._paths import data_path as bundled_data_path


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
    statutory: bool = False


class RegulatoryCalendar(BaseModel):
    jurisdiction: str
    fiscal_year_end: str
    frameworks: list[str] = Field(default_factory=list)
    items: list[RegulatoryCalendarItem] = Field(default_factory=list)
    overdue_count: int = 0
    due_within_60_days_count: int = 0
    alerts: list[str] = Field(default_factory=list)
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
        alerts=calendar_alerts(items),
        notes=profile.notes,
    )


def calendar_alerts(items: list[RegulatoryCalendarItem], *, within_days: int = 60) -> list[str]:
    """Live alerts: statutory deadlines inside *within_days*, and anything overdue."""
    alerts: list[str] = []
    for item in items:
        if item.status == "overdue":
            alerts.append(f"OVERDUE: {item.title} ({item.framework}) was due {item.due_date}.")
        elif item.statutory and 0 <= item.days_until_due <= within_days:
            alerts.append(
                f"{item.title} ({item.framework}) is due {item.due_date} — "
                f"{item.days_until_due} days away (statutory date)."
            )
    return alerts


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
        statutory=deadline.statutory,
    )


def render_regulatory_calendar_text(calendar: RegulatoryCalendar) -> str:
    """Render a terminal-friendly regulatory calendar."""
    lines = [
        f"Regulatory Deadline Calendar - {calendar.jurisdiction}",
        f"Fiscal year end: {calendar.fiscal_year_end}",
        f"Frameworks: {', '.join(calendar.frameworks)}",
        f"Overdue: {calendar.overdue_count} | Due in 60 days: {calendar.due_within_60_days_count}",
        *[f"ALERT: {alert}" for alert in calendar.alerts],
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
    source_url: str = ""
    source: str = ""
    last_verified: str = ""


def _watchlist_rows() -> list[dict]:
    """Market-wide milestones from ``data/regulatory/watchlist.yaml`` (W5.1).

    Unlike the per-fund deadline calendar these are fixed calendar dates that
    apply regardless of fiscal year end.
    """
    from openharness.impact.knowledge import load_knowledge

    return list(load_knowledge("regulatory/watchlist.yaml").get("milestones", []))


def regulatory_watchlist(
    *,
    today: date | None = None,
    jurisdiction: str = "",
    include_passed: bool = False,
) -> list[RegulatoryWatchlistItem]:
    """Return the market-wide regulatory milestone watch-list, soonest first."""
    ref = today or date.today()
    items: list[RegulatoryWatchlistItem] = []
    for row in _watchlist_rows():
        event_date, event = str(row["event_date"]), row["event"]
        event_jurisdiction, source_url = row.get("jurisdiction", "EU"), row.get("source_url", "")
        source = row.get("source", "")
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
                source_url=source_url,
                last_verified=str(row.get("last_verified", "")),
                source=source,
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
        Path(path) if path else bundled_data_path("issb_adoption.yaml")
    )
    payload = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    required = {"jurisdiction", "status", "effective", "scope", "assurance_posture", "source"}
    rows = payload.get("jurisdictions", [])
    for index, row in enumerate(rows):
        missing = required - set(row)
        if missing:
            raise ValueError(f"ISSB adoption row {index} missing {sorted(missing)}")
    # The bundled index is a tracking aid, not a substitute for the IFRS
    # jurisdictional profiles.  Most rows intentionally contain an authority
    # name rather than a deep link; expose that provenance state to callers so
    # a legal workflow cannot mistake an editorial row for verified law.
    normalized: list[dict] = []
    for row in rows:
        item = dict(row)
        item.setdefault("source_url", "")
        item.setdefault("source_quality", "deep_link" if item["source_url"] else "authority_name_only")
        normalized.append(item)
    return normalized


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


def issb_s2_amendments(path: str | Path | None = None) -> dict:
    """Return the issued IFRS S2 targeted-amendment register."""
    return s2_amendment_summary(path)


# ---------------------------------------------------------------------------
# Moved from roadmap_v2 (v7 W5.4)
# ---------------------------------------------------------------------------

class JurisdictionProfile(BaseModel):
    """Jurisdiction-aware disclosure profile."""

    jurisdiction: str
    frameworks: list[str]
    climate_required: bool = True
    notes: str = ""


DISCLOSURE_PROFILES: dict[str, JurisdictionProfile] = {
    "EU": JurisdictionProfile(jurisdiction="EU", frameworks=["ESRS", "SFDR", "ISSB"], notes="CSRD/SFDR with ESRS versioning"),
    "UK": JurisdictionProfile(jurisdiction="UK", frameworks=["ISSB", "FCA SDR"], notes="UK SDR and ISSB-aligned climate reporting"),
    "Singapore": JurisdictionProfile(jurisdiction="Singapore", frameworks=["ISSB"], notes="ISSB climate disclosure baseline"),
    "Japan": JurisdictionProfile(jurisdiction="Japan", frameworks=["ISSB"], notes="SSBJ/ISSB-aligned profile"),
    "Australia": JurisdictionProfile(jurisdiction="Australia", frameworks=["AASB S2", "ISSB"], notes="AASB S2 climate profile"),
    "Canada": JurisdictionProfile(jurisdiction="Canada", frameworks=["ISSB"], notes="CSSB/ISSB-aligned profile"),
    "US": JurisdictionProfile(jurisdiction="US", frameworks=["California SB 253/261", "state climate"], notes="State-level climate profile (SEC climate rule rescission proposed 2026)"),
}


def select_jurisdiction_profile(jurisdiction: str) -> JurisdictionProfile:
    """Return a disclosure profile for a roadmap jurisdiction."""
    key = jurisdiction.strip()
    profile_by_lower = {name.lower(): profile for name, profile in DISCLOSURE_PROFILES.items()}
    profile = profile_by_lower.get(key.lower())
    if profile is None:
        raise KeyError(f"Unknown jurisdiction profile: {jurisdiction}")
    return profile


__all__ = [
    "JurisdictionProfile",
    "DISCLOSURE_PROFILES",
    "select_jurisdiction_profile",

    "RegulatoryCalendar",
    "RegulatoryCalendarItem",
    "RegulatoryWatchlistItem",
    "build_regulatory_calendar",
    "calendar_alerts",
    "default_fiscal_year_end",
    "jurisdiction_options",
    "issb_status",
    "issb_s2_amendments",
    "issb_summary",
    "regulatory_watchlist",
    "render_regulatory_calendar_text",
]
