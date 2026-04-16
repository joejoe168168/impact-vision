#!/usr/bin/env python3
"""Extract GIIN Core Metric Set from the full IRIS+ catalog JSON."""
from __future__ import annotations

import json
from pathlib import Path

CORE_IDS = {
    "OD8350", "OI4753", "PI4060", "OI8869", "OI1571", "OI6213",
    "FP3021", "FP4761", "OI1479", "OI4112", "OD4091", "OI4732",
    "OI1582", "OI1075", "OI5049", "OI4324",
}

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "iris_catalog_5.3c.json"
DST = ROOT / "src" / "openharness" / "impact" / "core_metrics.json"

data = json.loads(SRC.read_text(encoding="utf-8"))
core = [m for m in data if m["id"] in CORE_IDS]
print(f"Found {len(core)} / {len(CORE_IDS)} core metrics")
for m in core:
    pid = m["id"]
    print(f"  {pid}: {m['name'][:60]}")

DST.write_text(json.dumps(core, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nSaved to {DST} ({DST.stat().st_size} bytes)")
