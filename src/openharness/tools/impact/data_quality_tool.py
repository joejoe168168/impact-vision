"""Tool: Assess quality/readiness of reported impact metrics."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.tools.impact.common import normalize_metric_map
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult

_PLACEHOLDER_VALUES = {"n/a", "na", "none", "unknown", "tbd", "-", "--"}


class DataQualityInput(BaseModel):
    action: Literal["assess"] = Field(default="assess", description="Action to perform.")
    reported_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="Metric values keyed by IRIS+ IDs.",
    )
    required_metrics: list[str] = Field(
        default_factory=list,
        description="Optional required metrics to verify (e.g., a fund's core reporting set).",
    )
    output_format: Literal["text", "json"] = Field(
        default="text",
        description="Return either human-readable text or JSON payload.",
    )


class DataQualityTool(BaseTool):
    name = "impact_data_quality"
    description = (
        "Assess the quality of reported IRIS+ metric data. Flags unknown IDs, placeholder values, "
        "and non-numeric entries where numeric values are expected. Produces a quality score and fixes."
    )
    input_model = DataQualityInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, DataQualityInput) else DataQualityInput.model_validate(arguments)
        if args.action != "assess":
            return ToolResult(output=f"Unknown action: {args.action}", is_error=True)
        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        metrics = normalize_metric_map(args.reported_metrics)
        required = [m.strip().upper() for m in args.required_metrics if m.strip()]

        unknown_ids: list[str] = []
        placeholder_values: list[str] = []
        non_numeric_values: list[str] = []

        for metric_id, value in metrics.items():
            metric = store.get(metric_id)
            if metric is None:
                unknown_ids.append(metric_id)
                continue
            if value.strip().lower() in _PLACEHOLDER_VALUES:
                placeholder_values.append(metric_id)
                continue
            metric_shape = f"{metric.quantity_type} {metric.reporting_format}"
            if _looks_numeric_metric(metric_shape):
                if _extract_number(value) is None:
                    non_numeric_values.append(metric_id)

        missing_required = [m for m in required if m not in metrics]

        penalties = (
            len(unknown_ids) * 12
            + len(placeholder_values) * 8
            + len(non_numeric_values) * 6
            + len(missing_required) * 10
        )
        quality_score = max(0, 100 - penalties)

        payload = {
            "metrics_provided": len(metrics),
            "quality_score": quality_score,
            "unknown_ids": unknown_ids,
            "placeholder_values": placeholder_values,
            "non_numeric_values": non_numeric_values,
            "missing_required": missing_required,
            "recommendations": _recommendations(unknown_ids, placeholder_values, non_numeric_values, missing_required),
        }

        if args.output_format == "json":
            import json

            return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)

        lines = [
            "IMPACT DATA QUALITY ASSESSMENT",
            "=" * 50,
            f"Metrics provided: {len(metrics)}",
            f"Quality score: {quality_score}/100",
            "",
        ]
        if required:
            lines.append(f"Required metrics checked: {len(required)}")
            lines.append(f"Missing required: {len(missing_required)}")
            lines.append("")
        if unknown_ids:
            lines.append(f"Unknown metric IDs ({len(unknown_ids)}): {', '.join(unknown_ids[:15])}")
        if placeholder_values:
            lines.append(f"Placeholder values ({len(placeholder_values)}): {', '.join(placeholder_values[:15])}")
        if non_numeric_values:
            lines.append(f"Non-numeric values on numeric metrics ({len(non_numeric_values)}): {', '.join(non_numeric_values[:15])}")
        if missing_required:
            lines.append(f"Missing required metrics ({len(missing_required)}): {', '.join(missing_required[:15])}")
        if not any((unknown_ids, placeholder_values, non_numeric_values, missing_required)):
            lines.append("No major quality issues detected.")

        recommendations = payload["recommendations"]
        if recommendations:
            lines.append("")
            lines.append("Recommended fixes:")
            for item in recommendations:
                lines.append(f"  - {item}")

        return ToolResult(
            output="\n".join(lines),
            metadata=payload,
        )


def _looks_numeric_metric(unit: str | None) -> bool:
    if not unit:
        return True
    text = unit.lower()
    numeric_cues = ("number", "count", "%", "usd", "eur", "ton", "kg", "kwh", "mwh", "hours", "days")
    return any(cue in text for cue in numeric_cues)


def _extract_number(value: str) -> float | None:
    match = re.search(r"-?\d+(\.\d+)?", value.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _recommendations(
    unknown_ids: list[str],
    placeholder_values: list[str],
    non_numeric_values: list[str],
    missing_required: list[str],
) -> list[str]:
    recs: list[str] = []
    if unknown_ids:
        recs.append("Verify IRIS+ IDs and replace unknown metrics with valid catalog IDs.")
    if placeholder_values:
        recs.append("Replace placeholders (N/A/TBD/etc.) with measured values or null handling policy.")
    if non_numeric_values:
        recs.append("Use numeric values (optionally with units) for metrics expected to be quantitative.")
    if missing_required:
        recs.append("Prioritize collection of missing required metrics before LP/investor reporting.")
    return recs
