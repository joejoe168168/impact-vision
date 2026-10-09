"""Survey connectors (Phase 19).

Lightweight ingestion layer for four of the most common primary-data
survey tools used in impact investing:

* **SurveyCTO** (form CSV / JSON export)
* **KoboToolbox / ODK** (XLSForm-based)
* **60 Decibels** (CSV export of "DX5" / lean-data)

The :class:`SurveyProvider` Protocol normalises a survey export into a
common :class:`SurveyResponse` shape so downstream tools (the Who
dimension scorer, the DD questionnaire renderer) don't have to know
which vendor a dataset came from.

All real adapters should stream — the offline default fits everything
in memory because the test corpus is tiny.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Iterable, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


SurveyPlatform = Literal["surveycto", "kobo", "odk", "60decibels", "other"]


class SurveyResponse(BaseModel):
    """One respondent's completed form."""

    respondent_id: str
    platform: SurveyPlatform
    submitted_at: str = ""
    answers: dict[str, object] = Field(default_factory=dict)


class SurveyDataset(BaseModel):
    platform: SurveyPlatform
    form_id: str
    responses: list[SurveyResponse] = Field(default_factory=list)

    def n(self) -> int:
        return len(self.responses)


@runtime_checkable
class SurveyProvider(Protocol):
    id: str
    platform: SurveyPlatform
    def load_csv(self, blob: str, *, form_id: str) -> SurveyDataset:  # pragma: no cover
        ...


@dataclass
class GenericCSVProvider:
    """CSV loader suitable for SurveyCTO / Kobo / 60Decibels exports.

    Assumes the first column is a respondent id; all other columns are
    question codes. Rows with empty respondent ids are skipped.
    """

    id: str = "generic-csv"
    platform: SurveyPlatform = "surveycto"

    def load_csv(self, blob: str, *, form_id: str) -> SurveyDataset:
        reader = csv.DictReader(io.StringIO(blob))
        responses: list[SurveyResponse] = []
        for row in reader:
            if not row:
                continue
            first_key = next(iter(row))
            rid = str(row.get(first_key, "")).strip()
            if not rid:
                continue
            answers = {k: v for k, v in row.items() if k != first_key}
            responses.append(SurveyResponse(
                respondent_id=rid, platform=self.platform, answers=answers,
            ))
        return SurveyDataset(platform=self.platform, form_id=form_id, responses=responses)


def aggregate_categorical(
    dataset: SurveyDataset, *, column: str
) -> dict[str, int]:
    """Frequency table for one categorical column."""
    counts: dict[str, int] = {}
    for r in dataset.responses:
        v = r.answers.get(column)
        if v is None or v == "":
            continue
        key = str(v)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def aggregate_numeric(
    dataset: SurveyDataset, *, column: str
) -> dict[str, float]:
    """Mean / median / count for a numeric column."""
    vals: list[float] = []
    for r in dataset.responses:
        v = r.answers.get(column)
        try:
            if v is None or v == "":
                continue
            vals.append(float(v))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
    vals.sort()
    median = (vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2)
    return {
        "n": float(n),
        "mean": round(sum(vals) / n, 4),
        "median": round(median, 4),
        "min": vals[0],
        "max": vals[-1],
    }


def aggregate_worker_voice(dataset: SurveyDataset) -> dict[str, float]:
    """Convenience aggregator used by :mod:`worker_voice`."""
    # Look for common NPS / satisfaction columns first
    satisfaction = None
    for col in ("satisfaction", "worker_satisfaction", "overall_sat"):
        if any(col in r.answers for r in dataset.responses):
            satisfaction = aggregate_numeric(dataset, column=col)
            break
    return satisfaction or {"n": float(dataset.n()), "mean": 0.0}


def stack_datasets(datasets: Iterable[SurveyDataset]) -> SurveyDataset:
    """Concatenate multiple datasets (same platform recommended)."""
    datasets = list(datasets)
    if not datasets:
        return SurveyDataset(platform="other", form_id="stacked")
    platform = datasets[0].platform
    responses: list[SurveyResponse] = []
    for d in datasets:
        responses.extend(d.responses)
    return SurveyDataset(platform=platform, form_id="stacked", responses=responses)


__all__ = [
    "SurveyPlatform",
    "SurveyResponse",
    "SurveyDataset",
    "SurveyProvider",
    "GenericCSVProvider",
    "aggregate_categorical",
    "aggregate_numeric",
    "aggregate_worker_voice",
    "stack_datasets",
]
