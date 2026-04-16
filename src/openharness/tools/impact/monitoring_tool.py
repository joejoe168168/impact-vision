"""Tool: Continuous monitoring for invested portfolio companies.

Manage monitoring schedules, record metric updates, detect deviations,
trigger re-assessments, and manage alerts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.storage import get_assessment_store
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MonitoringInput(BaseModel):
    action: Literal[
        "set_schedule", "get_schedule", "list_due",
        "record_metric", "check_alerts", "list_alerts", "acknowledge_alert",
        "reassess", "dashboard",
    ] = Field(description="Monitoring operation to perform")
    company_name: str = Field(default="", description="Company name")
    frequency: Literal["monthly", "quarterly", "semi_annual", "annual"] = "quarterly"
    next_review_date: str = Field(default="", description="ISO date for next review")
    alert_thresholds: dict[str, float] = Field(
        default_factory=dict,
        description="Metric ID -> deviation threshold (e.g. {'OI4112': 0.2} means 20% deviation triggers alert)",
    )
    watch_metrics: list[str] = Field(default_factory=list, description="Metric IDs to monitor")
    metric_id: str = Field(default="", description="Metric ID for record_metric")
    metric_value: float | None = Field(default=None, description="New metric value")
    alert_id: int | None = Field(default=None, description="Alert ID for acknowledge_alert")
    as_of_date: str = Field(default="", description="Date reference for list_due (defaults to today)")


class MonitoringTool(BaseTool):
    name = "monitoring"
    description = (
        "Manage continuous monitoring for invested companies: set review schedules, "
        "record metric updates with deviation detection, trigger re-assessments, "
        "and manage alerts for threshold breaches."
    )
    input_model = MonitoringInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, MonitoringInput) else MonitoringInput.model_validate(arguments)
        return args.action in ("get_schedule", "list_due", "list_alerts", "dashboard")

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, MonitoringInput) else MonitoringInput.model_validate(arguments)
        store = get_assessment_store()

        handlers = {
            "set_schedule": self._handle_set_schedule,
            "get_schedule": self._handle_get_schedule,
            "list_due": self._handle_list_due,
            "record_metric": self._handle_record_metric,
            "check_alerts": self._handle_check_alerts,
            "list_alerts": self._handle_list_alerts,
            "acknowledge_alert": self._handle_ack_alert,
            "reassess": self._handle_reassess,
            "dashboard": self._handle_dashboard,
        }
        handler = handlers.get(args.action)
        if not handler:
            return ToolResult(output=f"Unknown action: {args.action}", is_error=True)
        return await handler(args, store, context)

    async def _handle_set_schedule(self, args: MonitoringInput, store, context) -> ToolResult:
        if not args.company_name:
            return ToolResult(output="company_name is required", is_error=True)
        row_id = store.upsert_monitoring_schedule(
            company_name=args.company_name,
            frequency=args.frequency,
            next_review_date=args.next_review_date,
            alert_thresholds=args.alert_thresholds or None,
            watch_metrics=args.watch_metrics or None,
        )
        return ToolResult(
            output=f"Monitoring schedule set for {args.company_name}: {args.frequency} (next: {args.next_review_date or 'TBD'}, id: {row_id})",
        )

    async def _handle_get_schedule(self, args: MonitoringInput, store, context) -> ToolResult:
        if not args.company_name:
            return ToolResult(output="company_name is required", is_error=True)
        sched = store.get_monitoring_schedule(args.company_name)
        if not sched:
            return ToolResult(output=f"No monitoring schedule for {args.company_name}")
        lines = [
            f"Monitoring: {sched['company_name']}",
            f"Frequency: {sched['frequency']}",
            f"Next Review: {sched.get('next_review_date', 'TBD')}",
            f"Last Review: {sched.get('last_review_date', 'N/A')}",
            f"Status: {sched.get('status', 'active')}",
            f"Watch Metrics: {', '.join(sched.get('watch_metrics', []))}",
            f"Alert Thresholds: {sched.get('alert_thresholds', {})}",
        ]
        return ToolResult(output="\n".join(lines))

    async def _handle_list_due(self, args: MonitoringInput, store, context) -> ToolResult:
        due = store.list_monitoring_due(args.as_of_date)
        if not due:
            return ToolResult(output="No reviews currently due")
        lines = [f"Reviews due ({len(due)}):"]
        for d in due:
            lines.append(f"  {d['company_name']}: due {d['next_review_date']} ({d['frequency']})")
        return ToolResult(output="\n".join(lines))

    async def _handle_record_metric(self, args: MonitoringInput, store, context) -> ToolResult:
        if not args.company_name or not args.metric_id:
            return ToolResult(output="company_name and metric_id are required", is_error=True)
        if args.metric_value is None:
            return ToolResult(output="metric_value is required", is_error=True)

        sched = store.get_monitoring_schedule(args.company_name)
        alerts_created = []

        if sched and sched.get("alert_thresholds"):
            threshold = sched["alert_thresholds"].get(args.metric_id)
            if threshold is not None:
                prev = store.get_assessment(args.company_name)
                if prev and prev.get("company", {}).get("reported_metrics", {}).get(args.metric_id):
                    try:
                        prev_val = float(prev["company"]["reported_metrics"][args.metric_id])
                        if prev_val > 0:
                            deviation = abs(args.metric_value - prev_val) / prev_val
                            if deviation > threshold:
                                alert_id = store.create_alert(
                                    company_name=args.company_name,
                                    alert_type="metric_deviation",
                                    message=f"{args.metric_id}: {prev_val} -> {args.metric_value} ({deviation:.0%} deviation, threshold: {threshold:.0%})",
                                    severity="warning" if deviation < threshold * 2 else "critical",
                                    metric_id=args.metric_id,
                                    current_value=args.metric_value,
                                    threshold_value=threshold,
                                )
                                alerts_created.append(alert_id)
                    except (ValueError, TypeError):
                        pass

        output = f"Recorded {args.metric_id} = {args.metric_value} for {args.company_name}"
        if alerts_created:
            output += f"\n⚠ Alert(s) triggered: {alerts_created}"
        return ToolResult(output=output)

    async def _handle_check_alerts(self, args: MonitoringInput, store, context) -> ToolResult:
        """Check all monitoring schedules and create alerts for overdue reviews."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        due = store.list_monitoring_due(now)
        created = 0
        for d in due:
            store.create_alert(
                company_name=d["company_name"],
                alert_type="review_due",
                message=f"Review due: {d['next_review_date']} ({d['frequency']})",
                severity="warning",
            )
            created += 1
        return ToolResult(output=f"Checked monitoring schedules: {created} review-due alerts created")

    async def _handle_list_alerts(self, args: MonitoringInput, store, context) -> ToolResult:
        alerts = store.list_alerts(
            company_name=args.company_name or None,
            unacknowledged_only=True,
        )
        if not alerts:
            return ToolResult(output="No unacknowledged alerts")
        severity_icon = {"info": "ℹ", "warning": "⚠", "critical": "🔴"}
        lines = [f"Alerts ({len(alerts)} unacknowledged):"]
        for a in alerts:
            icon = severity_icon.get(a["severity"], "?")
            lines.append(f"  [{a['id']}] {icon} {a['alert_type']}: {a['company_name']} — {a['message']}")
        return ToolResult(output="\n".join(lines))

    async def _handle_ack_alert(self, args: MonitoringInput, store, context) -> ToolResult:
        if args.alert_id is None:
            return ToolResult(output="alert_id is required", is_error=True)
        ok = store.acknowledge_alert(args.alert_id)
        msg = f"Alert {args.alert_id} acknowledged" if ok else f"Alert {args.alert_id} not found"
        return ToolResult(output=msg)

    async def _handle_reassess(self, args: MonitoringInput, store, context) -> ToolResult:
        """Trigger a full re-assessment for a company using stored data."""
        if not args.company_name:
            return ToolResult(output="company_name is required", is_error=True)

        prev = store.get_assessment(args.company_name)
        if not prev:
            return ToolResult(output=f"No previous assessment for {args.company_name}. Run impact_report first.")

        from openharness.impact.database import get_metric_store
        from openharness.impact.five_dimensions import assess_five_dimensions
        from openharness.impact.models import Company
        from openharness.impact.sdg_mapper import map_sdg_alignment

        company_data = prev.get("company", {})
        company = Company.model_validate(company_data)

        try:
            metric_store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        new_fd = assess_five_dimensions(company, metric_store)
        new_sdg = map_sdg_alignment(company, metric_store)

        prev_fd = prev.get("five_dimensions", {})
        old_score = prev_fd.get("overall_score", 0) if prev_fd else 0
        new_score = new_fd.overall_score
        delta = round(new_score - old_score, 2)

        store.save_assessment(
            company_name=args.company_name,
            company_data=company_data,
            five_dimensions=new_fd.model_dump(),
            sdg_alignments=[a.model_dump() for a in new_sdg],
        )

        if abs(delta) > 0.5:
            direction = "improved" if delta > 0 else "declined"
            store.create_alert(
                company_name=args.company_name,
                alert_type="score_change",
                message=f"5D score {direction}: {old_score:.1f} -> {new_score:.1f} (delta: {delta:+.1f})",
                severity="info" if delta > 0 else "warning",
            )

        lines = [
            f"Re-assessment complete for {args.company_name}",
            f"5D Score: {old_score:.1f} -> {new_score:.1f} (delta: {delta:+.1f})",
            f"Grade: {new_fd.overall_grade}",
            f"SDG alignments updated: {len(new_sdg)} goals scored",
        ]
        return ToolResult(output="\n".join(lines))

    async def _handle_dashboard(self, args: MonitoringInput, store, context) -> ToolResult:
        """Generate a text-based monitoring dashboard for a company or all companies."""
        if args.company_name:
            return self._company_dashboard(args.company_name, store)
        schedules = store.list_monitoring_due(
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        alerts = store.list_alerts(unacknowledged_only=True)
        lines = ["=== MONITORING DASHBOARD ===", ""]
        lines.append(f"Reviews Due: {len(schedules)}")
        for s in schedules[:10]:
            lines.append(f"  - {s['company_name']}: due {s['next_review_date']} ({s['frequency']})")
        lines.append(f"\nUnacknowledged Alerts: {len(alerts)}")
        sev_count = {"critical": 0, "warning": 0, "info": 0}
        for a in alerts:
            sev_count[a.get("severity", "info")] = sev_count.get(a.get("severity", "info"), 0) + 1
        lines.append(f"  Critical: {sev_count['critical']} | Warning: {sev_count['warning']} | Info: {sev_count['info']}")
        for a in alerts[:10]:
            lines.append(f"  [{a['id']}] {a['severity'].upper()} {a['company_name']}: {a['message']}")
        return ToolResult(output="\n".join(lines))

    def _company_dashboard(self, company_name: str, store) -> ToolResult:
        sched = store.get_monitoring_schedule(company_name)
        alerts = store.list_alerts(company_name=company_name)
        assessment = store.get_assessment(company_name)
        lines = [f"=== MONITORING: {company_name} ===", ""]
        if sched:
            lines.append(f"Schedule: {sched['frequency']} | Next: {sched.get('next_review_date', 'TBD')} | Status: {sched.get('status', 'active')}")
            lines.append(f"Watch Metrics: {', '.join(sched.get('watch_metrics', []))}")
        else:
            lines.append("No monitoring schedule configured")
        if assessment:
            fd = assessment.get("five_dimensions", {})
            if fd:
                lines.append(f"\nLatest 5D Score: {fd.get('overall_score', 'N/A')}/5 (Grade: {fd.get('overall_grade', 'N/A')})")
        if alerts:
            lines.append(f"\nAlerts ({len(alerts)}):")
            for a in alerts[:10]:
                ack = "✓" if a.get("acknowledged") else "○"
                lines.append(f"  [{ack}] {a['severity'].upper()} {a['alert_type']}: {a['message']}")
        return ToolResult(output="\n".join(lines))
