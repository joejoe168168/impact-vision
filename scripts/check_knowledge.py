"""CI gate: every knowledge row has provenance and was (re)verified recently.

Usage: python scripts/check_knowledge.py [--max-age-days 180] [--today YYYY-MM-DD]
Exits 1 when a row lacks as_of / source, or is older than the max age
without re-verification (docs/roadmap-v7.md W5.1).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from impact_vision.impact.knowledge import MAX_AGE_DAYS, freshness_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-age-days", type=int, default=MAX_AGE_DAYS)
    parser.add_argument("--today", default="")
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else None
    report = freshness_report(today=today, max_age_days=args.max_age_days)
    print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
