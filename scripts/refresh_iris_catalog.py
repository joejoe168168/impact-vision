"""Refresh the IRIS+ catalog from the latest GIIN release.

Usage::

    python scripts/refresh_iris_catalog.py \
        --excel "data/raw/IRIS 5.3c Catalog of Metrics.xlsx" \
        --out   "data/processed/iris_catalog_5.3c.json"

The script:
  1. Loads metrics from the IRIS+ Excel using `catalog.load_catalog_from_excel`.
  2. Saves them to JSON at the target path.
  3. Computes a small diff against the previously-shipped JSON (if any) so
     reviewers can see additions / removals / category churn before committing.
  4. Refuses to overwrite if the new catalog is materially smaller (>10%
     reduction) — that would silently regress dashboards. Use `--force` to
     override after a sanity check.

GIIN publishes a new minor version of IRIS+ roughly annually; running this
script periodically keeps the bundled catalog in sync.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable


def _add_repo_root_to_path() -> None:
    here = Path(__file__).resolve().parent.parent
    src = here / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _hash_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:12]


def _summarise(metrics: Iterable) -> dict:
    metrics = list(metrics)
    by_category: dict[str, int] = {}
    for m in metrics:
        cat = getattr(m, "primary_impact_category", None) or "Uncategorised"
        by_category[cat] = by_category.get(cat, 0) + 1
    return {
        "total": len(metrics),
        "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
    }


def _diff(old_ids: set[str], new_ids: set[str]) -> tuple[list[str], list[str]]:
    return sorted(new_ids - old_ids), sorted(old_ids - new_ids)


def main() -> int:
    _add_repo_root_to_path()
    from openharness.impact.catalog import (
        load_catalog_from_excel, save_catalog_json, load_catalog_json,
        get_default_excel_path, get_default_json_path,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--excel", default=None, help="Path to IRIS+ Excel.")
    p.add_argument("--out", default=None, help="Output JSON path.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite even if the new catalog is materially smaller.")
    p.add_argument("--max-shrink-pct", type=float, default=10.0,
                   help="Max acceptable size reduction without --force.")
    args = p.parse_args()

    excel_path = Path(args.excel) if args.excel else get_default_excel_path()
    out_path = Path(args.out) if args.out else get_default_json_path()

    if not excel_path.exists():
        print(f"ERROR: IRIS+ Excel not found at {excel_path}", file=sys.stderr)
        print("Download the latest from https://iris.thegiin.com/ and re-run.", file=sys.stderr)
        return 2

    print(f"Loading IRIS+ Excel from {excel_path} ...")
    new_metrics = load_catalog_from_excel(excel_path)
    print(f"  -> parsed {len(new_metrics)} metrics")

    old_metrics = []
    if out_path.exists():
        try:
            old_metrics = load_catalog_json(out_path)
            print(f"  -> existing JSON has {len(old_metrics)} metrics")
        except Exception as exc:  # noqa: BLE001
            print(f"  -> WARNING: could not read existing JSON ({exc})")

    new_ids = {m.metric_id for m in new_metrics}
    old_ids = {m.metric_id for m in old_metrics}
    added, removed = _diff(old_ids, new_ids)

    if old_metrics:
        shrink_pct = (1 - len(new_metrics) / len(old_metrics)) * 100
        if shrink_pct > args.max_shrink_pct and not args.force:
            print(f"REFUSING: new catalog is {shrink_pct:.1f}% smaller than the existing one.")
            print("  Re-run with --force after sanity-checking the upstream Excel.")
            return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_catalog_json(new_metrics, out_path)

    summary = {
        "source_excel": str(excel_path),
        "source_excel_sha256_12": _hash_file(excel_path),
        "output": str(out_path),
        "output_sha256_12": _hash_file(out_path),
        "summary": _summarise(new_metrics),
        "diff": {
            "added_count": len(added),
            "removed_count": len(removed),
            "added": added[:50],
            "removed": removed[:50],
            "truncated": len(added) > 50 or len(removed) > 50,
        },
    }
    log_path = out_path.with_suffix(out_path.suffix + ".refresh.json")
    log_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print(f"Wrote   : {out_path}")
    print(f"Refresh log: {log_path}")
    print(f"Added   : {len(added)} metric(s)")
    print(f"Removed : {len(removed)} metric(s)")
    if len(added) + len(removed) == 0:
        print("No changes vs previous catalog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
