"""Reproducible extraction benchmark and CI gate."""

from __future__ import annotations
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from pydantic import BaseModel, Field


class EvalResult(BaseModel):
    precision: float
    recall: float
    f1: float
    per_field: dict[str, dict] = Field(default_factory=dict)
    failures: list[dict] = Field(default_factory=list)
    extractor_version: str = "unknown"
    run_at: str


def _tokens(value):
    return set(re.findall(r"[a-z0-9]+", str(value).lower()))


def _claim_match(a, b):
    left, right = _tokens(a), _tokens(b)
    return len(left & right) / len(left | right) >= 0.6 if left | right else True


def run_eval(extract_fn: Callable[[str], dict], gold_path: str) -> EvalResult:
    docs = [
        json.loads(line)
        for line in Path(gold_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    totals = {}
    failures = []
    for field in ("claims", "metrics", "sdgs"):
        tp = fp = fn = 0
        for doc in docs:
            actual = extract_fn(doc["source_text"]).get(field, [])
            expected = doc[f"expected_{field}"]
            if field == "claims":
                matched = {
                    i
                    for i, exp in enumerate(expected)
                    if any(_claim_match(exp, value) for value in actual)
                }
            else:
                matched = {
                    i
                    for i, exp in enumerate(expected)
                    if str(exp).upper() in {str(value).upper() for value in actual}
                }
            tp += len(matched)
            fn += len(expected) - len(matched)
            fp += max(0, len(actual) - len(matched))
            if len(matched) != len(expected):
                failures.append(
                    {
                        "doc_id": doc["doc_id"],
                        "field": field,
                        "expected": expected,
                        "actual": actual,
                    }
                )
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        totals[field] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        }
    precision = sum(v["precision"] for v in totals.values()) / 3
    recall = sum(v["recall"] for v in totals.values()) / 3
    return EvalResult(
        precision=precision,
        recall=recall,
        f1=2 * precision * recall / (precision + recall) if precision + recall else 0,
        per_field=totals,
        failures=failures,
        extractor_version=getattr(extract_fn, "version", "unknown"),
        run_at=datetime.now(timezone.utc).isoformat(),
    )


def update_model_card(result: EvalResult) -> dict:
    return {
        "evaluation_notes": f"Extraction benchmark F1={result.f1:.3f}, precision={result.precision:.3f}, recall={result.recall:.3f} at {result.run_at}",
        "evaluation": result.model_dump(mode="json"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=float, default=0.75)
    parser.add_argument(
        "--gold",
        default=str(Path(__file__).resolve().parents[3] / "data/eval/extraction_gold.jsonl"),
    )
    args = parser.parse_args()
    result = run_eval(lambda text: {"claims": [], "metrics": [], "sdgs": []}, args.gold)
    print(result.model_dump_json(indent=2))
    raise SystemExit(0 if result.f1 >= args.gate else 1)


if __name__ == "__main__":
    main()
__all__ = ["EvalResult", "run_eval", "update_model_card"]
