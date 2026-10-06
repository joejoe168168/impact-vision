"""Smoke-test an *installed* Impact Vision wheel.

Run from outside the repo (e.g. ``cd /tmp``) inside a venv where the built
wheel is installed. It fails if bundled reference data is not found — the
failure mode where an installed copy silently scores with hard-coded fallbacks
and an empty DD checklist.

Usage::

    python -m build --wheel            # or: uv build --wheel
    python -m venv /tmp/wheel-venv && /tmp/wheel-venv/bin/pip install dist/*.whl
    cd /tmp && /tmp/wheel-venv/bin/python <repo>/scripts/wheel_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    import openharness
    from openharness.impact._paths import data_dir
    from openharness.impact.dd_checklist import load_checklist
    from openharness.impact.five_dimensions import _load_scoring_config
    from openharness.impact.sdg_mapper import _load_core_metrics_per_sdg

    failures: list[str] = []
    pkg = Path(openharness.__file__).resolve().parent
    root = data_dir()
    print(f"package:   {pkg}")
    print(f"data root: {root}")

    if "site-packages" in str(pkg) and not str(root).startswith(str(pkg)):
        failures.append(f"installed package resolved data outside the wheel: {root}")
    if not _load_scoring_config():
        failures.append("scoring_config.yaml not found (5D would use hard-coded fallbacks)")
    questions = load_checklist()
    if len(questions) < 100:
        failures.append(f"DD checklist has {len(questions)} questions (expected 100+)")
    if not _load_core_metrics_per_sdg():
        failures.append("core_metric_set_per_sdg.yaml not found")
    if (root / "impact_vision.db").exists():
        failures.append("impact_vision.db is shipped in the wheel")

    for msg in failures:
        print(f"FAIL: {msg}")
    if not failures:
        print(f"OK: {len(questions)} DD questions, scoring config and SDG core sets loaded")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
