"""Reproducible extraction benchmark and CI gate (blocking since v7 W5.6).

Scores the production extraction chain on ``data/eval/extraction_gold.jsonl``:

* ``claims`` – gold claim phrases found in an extracted claim (token containment);
* ``metrics`` – IRIS+ IDs (extractor suggestion + claim→metric mapper);
* ``sdgs`` – goals detected from the text;
* ``categories`` – outcome / output / activity / intent classification;
* ``quantities`` – value + unit pairs (decimals and thousands separators).

Fields a gold row omits are not scored for that row. Forward-looking and
negated sentences have empty expectations, so mapping them costs precision.
"""

from __future__ import annotations
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from pydantic import BaseModel, Field
from impact_vision.impact._paths import data_path


# Blocking CI threshold for the regex extractor on the bundled gold set; raise
# it as extraction improves (never lower it to make a regression pass).
GATE = 0.95  # regex extractor measured 0.978 on 18 docs (2026-10-06)


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


def _claim_match(expected, actual):
    """Share of the gold phrase's tokens present in the extracted claim (>= 0.6).

    Extractors return sentence-level claims while gold phrases are short, so
    containment (not Jaccard) is the fair test.
    """
    gold, got = _tokens(expected), _tokens(actual)
    return len(gold & got) / len(gold) >= 0.6 if gold else True


def _norm_quantity(value) -> str:
    text = str(value).lower().replace(",", "").strip()
    match = re.match(r"(-?\d+(?:\.\d+)?)\s*(.*)", text)
    if not match:
        return text
    number = float(match.group(1))
    unit = re.sub(r"\s+", "", match.group(2))
    return f"{number:g} {unit}".strip()


FIELDS = ("claims", "metrics", "sdgs", "categories", "quantities")


def production_extract(text: str, *, extractor_id: str = "auto") -> dict:
    """Run the same chain ``assess``/``pitch_deck_analyze`` use on *text*."""
    from impact_vision.impact.claim_metric_mapper import map_claim_metrics
    from impact_vision.impact.extractors import get_extractor
    from impact_vision.impact.extractors.base import to_impact_claims
    from impact_vision.tools.impact.pitch_deck_analyze_tool import _detect_sdg_goals

    claims = get_extractor(extractor_id).extract(text)
    impact = to_impact_claims(claims)
    metrics: set[str] = set()
    quantities: set[str] = set()
    for claim in claims:
        if claim.suggested_iris_metric_id:
            metrics.add(claim.suggested_iris_metric_id)
        if claim.metric_value is not None and claim.metric_unit:
            quantities.add(_norm_quantity(f"{claim.metric_value} {claim.metric_unit}"))
        forward = claim.category == "commitment"
        for mapping in map_claim_metrics(claim.text, forward_looking=forward):
            metrics.add(mapping.metric_id)
    return {
        "claims": [c.text for c in claims],
        "metrics": sorted(metrics),
        "sdgs": sorted(_detect_sdg_goals(text, impact)),
        "categories": sorted({c.category for c in impact}),
        "quantities": sorted(quantities),
    }


def run_eval(extract_fn: Callable[[str], dict], gold_path: str) -> EvalResult:
    docs = [
        json.loads(line)
        for line in Path(gold_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    totals = {}
    failures = []
    cache = {doc["doc_id"]: extract_fn(doc["source_text"]) for doc in docs}
    for field in FIELDS:
        tp = fp = fn = 0
        scored = 0
        for doc in docs:
            if f"expected_{field}" not in doc:
                continue
            scored += 1
            actual = cache[doc["doc_id"]].get(field, [])
            expected = doc[f"expected_{field}"]
            if field == "quantities":
                actual = [_norm_quantity(v) for v in actual]
                expected = [_norm_quantity(v) for v in expected]
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
        if not scored:
            continue
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        totals[field] = {
            "docs": scored,
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        }
    precision = sum(v["precision"] for v in totals.values()) / len(totals)
    recall = sum(v["recall"] for v in totals.values()) / len(totals)
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
    parser.add_argument("--gate", type=float, default=GATE)
    parser.add_argument("--extractor", default="auto", help="auto | regex | llm")
    parser.add_argument("--summary", action="store_true", help="print scores only, not failures")
    parser.add_argument(
        "--gold",
        default=str(data_path("eval", "extraction_gold.jsonl")),
    )
    args = parser.parse_args()
    from impact_vision.impact.extractors import resolve_extractor_id

    extractor = resolve_extractor_id(args.extractor)

    def extract(text: str) -> dict:
        return production_extract(text, extractor_id=extractor)

    extract.version = extractor  # type: ignore[attr-defined]
    result = run_eval(extract, args.gold)
    payload = result.model_dump(mode="json")
    if args.summary:
        payload.pop("failures")
    print(json.dumps(payload, indent=2))
    verdict = "PASS" if result.f1 >= args.gate else "FAIL"
    print(f"{verdict}: F1 {result.f1:.3f} vs gate {args.gate:.2f} ({extractor} extractor)")
    raise SystemExit(0 if result.f1 >= args.gate else 1)


if __name__ == "__main__":
    main()
__all__ = ["EvalResult", "FIELDS", "GATE", "production_extract", "run_eval", "update_model_card"]
