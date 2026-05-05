"""LP reporting calendar generator.

Reads the `reporting_cadence` block of a `FundThesis` and produces a 12-month
calendar of LP report deliverables, with deadlines and a checklist of inputs
required to assemble each one.

Useful as a Streamlit calendar widget, an iCal export, and a JSON feed for a
team's task tracker.
"""
from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, Field

from openharness.impact.fund_thesis import FundThesis, ReportingCadence


CADENCE_MONTHS = {
    "monthly": 1,
    "quarterly": 3,
    "semi_annually": 6,
    "annually": 12,
    "never": 0,
}


REPORT_INPUT_CHECKLIST: dict[str, list[str]] = {
    "ilpa_esg": [
        "ILPA ESG DDQ v3.0 responses (firm-level + per-fund)",
        "Diversity, equity & inclusion metrics",
        "Climate risk integration narrative",
        "Engagement & escalation log",
    ],
    "giin_iris": [
        "Per-portco IRIS+ Core Metric Set values",
        "Year-on-year comparison + variance commentary",
        "Anonymised peer-cohort context (if available)",
        "Strategy & theory of change narrative",
    ],
    "edci": [
        "EDCI 2026 KPI values per portco",
        "Workforce and engagement fields (S1-S11)",
        "Climate and decarbonization fields (E1-E7)",
        "Cybersecurity testing field (G1)",
    ],
    "sfdr_pai": [
        "All 14 mandatory PAI indicator values",
        "Carbon footprint and GHG intensity (PAI 1-3)",
        "Energy mix (PAI 5)",
        "Board diversity, gender pay gap (PAI 12-13)",
        "DNSH & minimum-safeguards sign-off",
    ],
    "fund_impact_letter": [
        "Headline 5D and SDG progress vs. last period",
        "Top 3 impact wins / case studies",
        "Adverse incidents & remediation actions",
        "Outlook & priorities for next period",
    ],
}


class CalendarItem(BaseModel):
    report_type: str
    report_label: str
    period_label: str
    deadline: date
    inputs_required: list[str] = Field(default_factory=list)


class LPCalendar(BaseModel):
    fund_name: str
    horizon_months: int
    items: list[CalendarItem] = Field(default_factory=list)


def _next_period_end(start: date, months: int) -> date:
    """Return the last day of the period that contains `start + months`."""
    y, m = start.year, start.month
    m += months
    while m > 12:
        m -= 12
        y += 1
    # Snap to last day of the previous month for clean reporting periods
    if m == 1:
        return date(y - 1, 12, 31)
    return date(y, m, 1) - timedelta(days=1)


def _label(report_type: str) -> str:
    return {
        "ilpa_esg": "ILPA ESG Data Convergence Report",
        "giin_iris": "GIIN IRIS+ Annual Report",
        "edci": "EDCI Annual Report",
        "sfdr_pai": "SFDR Principal Adverse Impact Statement",
        "fund_impact_letter": "Fund Impact Letter to LPs",
    }.get(report_type, report_type)


def build_calendar(
    thesis: FundThesis,
    horizon_months: int = 12,
    start: date | None = None,
) -> LPCalendar:
    """Generate an LP reporting calendar for the next `horizon_months` months."""
    today = start or date.today()
    items: list[CalendarItem] = []

    cadence: ReportingCadence = thesis.reporting_cadence
    for report_type, freq in cadence.model_dump().items():
        months = CADENCE_MONTHS.get(freq, 0)
        if months == 0:
            continue
        # Generate every `months`-period deadline within the horizon
        offset = months
        while offset <= horizon_months:
            deadline = _next_period_end(today, offset) + timedelta(days=45)
            period_label = f"{deadline.year} period ending {_next_period_end(today, offset).isoformat()}"
            items.append(CalendarItem(
                report_type=report_type,
                report_label=_label(report_type),
                period_label=period_label,
                deadline=deadline,
                inputs_required=REPORT_INPUT_CHECKLIST.get(report_type, []),
            ))
            offset += months

    items.sort(key=lambda i: i.deadline)
    return LPCalendar(
        fund_name=thesis.name,
        horizon_months=horizon_months,
        items=items,
    )


def render_calendar_text(cal: LPCalendar) -> str:
    """Plain-text rendering for terminal / Slack."""
    lines = [
        f"LP Reporting Calendar — {cal.fund_name}",
        f"Horizon: {cal.horizon_months} months",
        "",
        f"{'Deadline':<12} {'Report':<40} Period",
        "-" * 80,
    ]
    for item in cal.items:
        lines.append(f"{item.deadline.isoformat():<12} {item.report_label:<40} {item.period_label}")
    return "\n".join(lines)
