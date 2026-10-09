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
    import impact_vision
    from impact_vision.impact._paths import data_dir
    from impact_vision.impact.dd_checklist import load_checklist
    from impact_vision.impact.five_dimensions import _load_scoring_config
    from impact_vision.impact.sdg_mapper import _load_core_metrics_per_sdg

    failures: list[str] = []
    pkg = Path(impact_vision.__file__).resolve().parent
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

    # The no-key quickstart must work from an installed wheel (W1.1).
    import tempfile

    from impact_vision.impact.pipeline import SAMPLE_DECKS, assess_file, sample_deck_path
    from impact_vision.impact.pipeline import write_deliverables

    for key in SAMPLE_DECKS:
        deck = sample_deck_path(key)
        if not deck.is_file():
            failures.append(f"sample deck missing from the wheel: {deck}")
    if not failures:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = assess_file(sample_deck_path("pig-farm"))
            files = write_deliverables(bundle, tmp)
            if bundle.summary()["claims"] == 0 or not files[0].is_file():
                failures.append("demo assessment produced no claims or no report")

    for msg in failures:
        print(f"FAIL: {msg}")
    if not failures:
        print(f"OK: {len(questions)} DD questions, scoring config and SDG core sets loaded")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
