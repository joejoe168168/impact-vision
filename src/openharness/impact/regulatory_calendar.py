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


# Market-wide milestones, re-verified 2026-10-06 (see docs/roadmap-v7.md §2
# and §9). Unlike the per-fund deadline calendar, these are fixed calendar
# dates that apply regardless of fiscal year end.
# (date, event, jurisdiction, source_url)
_LINKLATERS_ESRS = "https://sustainablefutures.linklaters.com/post/102o1ou/eu-csrd-revised-esrs-and-voluntary-reporting-standard-are-published-in-the-offic"
_REGULATORY_WATCHLIST: list[tuple[str, str, str, str]] = [
    ("2026-09-24", "VSME Delegated Regulation (EU) 2026/1560 in force (voluntary SME standard; value-chain cap from FY2027)", "EU", _LINKLATERS_ESRS),
    ("2026-09-27", "ECGT Directive (EU) 2024/825 applies — generic green claims banned", "EU",
     "https://www.lw.com/en/insights/eu-empowering-consumers-directive-new-rules-on-green-claims-apply-from-27-september-2026"),
    ("2026-10-07", "Hong Kong Taxonomy Phase 2B prototype consultation closes", "HK",
     "https://www.info.gov.hk/gia/general/202609/07/P2026090700249.htm"),
    ("2026-10-31", "European Parliament plenary vote on the SFDR 2.0 mandate (expected October 2026)", "EU",
     "https://www.debevoise.com/insights/publications/2026/09/sfdr-20-recap-briefing"),
    ("2026-10-31", "ISSB nature-related Practice Statement exposure draft (targeted for CBD COP17, October 2026)", "Global",
     "https://www.ifrs.org/content/ifrs/home/news-and-events/updates/issb/2026/issb-update-september-2026.html"),
    ("2026-11-10", "First California SB 253 Scope 1+2 GHG reports due (limited assurance waived this cycle)", "US",
     "https://ww2.arb.ca.gov/our-work/programs/california-corporate-greenhouse-gas-reporting"),
    ("2026-11-10", "Revised ESRS Delegated Regulation (EU) 2026/1563 enters into force", "EU", _LINKLATERS_ESRS),
    ("2026-11-11", "EFRAG draft ESRS XBRL taxonomy consultation closes", "EU",
     "https://www.xbrl.org/news/efrag-advances-the-revised-esrs-toward-a-digital-taxonomy/"),
    ("2026-12-02", "EU AI Act Art 50 marking of AI-generated content applies to systems placed on the market before 2026-08-02", "EU",
     "https://www.hunton.com/privacy-and-cybersecurity-law-blog/eu-digital-omnibus-on-ai-enters-into-force"),
    ("2026-12-15", "ISSA 5000 sustainability assurance effective (periods beginning on/after)", "Global",
     "https://www.iaasb.org/consultations-projects/issa-5000-adoption-and-implementation"),
    ("2026-12-15", "HKSSA 5000 effective in Hong Kong (periods beginning on/after)", "HK",
     "https://www.hkicpa.org.hk/-/media/HKICPA-Website/Members-Handbook/volumeIII/324ssa5.pdf"),
    ("2026-12-30", "EUDR obligations apply (large/medium operators)", "EU", ""),
    ("2027-01-01", "Revised ESRS mandatory (financial years beginning on/after); VSME value-chain cap applies", "EU", _LINKLATERS_ESRS),
    ("2027-01-01", "UK SRS comply-or-explain for listed issuers (periods beginning on/after; FCA PS26/19)", "UK",
     "https://www.fca.org.uk/publications/policy-statements/ps26-19-aligning-listed-issuers-sustainability-disclosures-international-standards"),
    ("2027-01-01", "IFRS S2 targeted amendments effective", "Global", ""),
    ("2027-03-19", "CSRD (as amended by Omnibus I) member-state transposition deadline", "EU", ""),
    ("2027-03-31", "Japan SSBJ standards mandatory for Prime-listed companies with ≥¥3tn market cap (FY ending March 2027)", "Japan",
     "https://www.fsa.go.jp/en/news/2025/20251106/02.pdf"),
    ("2027-06-30", "EUDR obligations apply to other micro and small operators", "EU", ""),
    ("2027-12-02", "EU AI Act Annex III high-risk obligations apply (deferred by Reg (EU) 2026/1744)", "EU",
     "https://www.hunton.com/privacy-and-cybersecurity-law-blog/eu-digital-omnibus-on-ai-enters-into-force"),
    ("2027-12-31", "California SB 253 Scope 3 reporting phase begins", "US",
     "https://ww2.arb.ca.gov/our-work/programs/california-corporate-greenhouse-gas-reporting"),
    ("2028-01-01", "Singapore: non-STI listed issuers ≥S$1bn market cap begin ISSB-based climate reporting (FY2028)", "Singapore",
     "https://www.acra.gov.sg/news-events/news-details/id/887"),
    ("2028-07-26", "CSDDD member-state transposition deadline", "EU", ""),
    ("2029-06-30", "SFDR 2.0 expected application (24 months after adoption; Council and Parliament both propose 24)", "EU",
     "https://www.debevoise.com/insights/publications/2026/09/sfdr-20-recap-briefing"),
    ("2029-07-26", "CSDDD applies to first wave (>5,000 employees + €1.5B turnover)", "EU", ""),
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
    for event_date, event, event_jurisdiction, source_url in _REGULATORY_WATCHLIST:
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


__all__ = [
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
