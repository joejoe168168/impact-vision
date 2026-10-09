"""Run the held-out evaluation (roadmap v8 W2.4) and print a markdown report.

    python scripts/run_heldout_eval.py [--json out.json]

In CI the report is appended to the job summary, so every release shows its
numbers. tests/test_v8_heldout_eval.py fails if they fall below the baseline.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from impact_vision.impact.heldout_eval import evaluate, to_markdown

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", help="write the full result here")
    args = parser.parse_args()
    result = evaluate(ROOT / "tests" / "golden" / "heldout")
    report = to_markdown(result)
    print(report)
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report)


if __name__ == "__main__":
    main()
