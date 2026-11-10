"""Versioned scoring methodology (v7 W5.2).

The 5D, SDG and greenwashing scorers read every weight and threshold from
``data/methodology/v1.yaml``; expected impact and the IC gate read
``data/methodology/v2.yaml``. :func:`methodology_stamp` returns both versions
plus one ``config_hash``: SHA-256 over every file that can change a score or
the verdict (the two methodology files, ``scoring_config.yaml``, the SDG
keyword maps, the contribution rubric and the negative-impact catalogue).
Every output carries this stamp, so two reports are comparable only when the
stamps match.

Set ``IMPACT_VISION_METHODOLOGY`` to a YAML path to run a custom methodology;
its own ``version`` and a different hash then appear on every output.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from impact_vision.impact._paths import data_path

DEFAULT_METHODOLOGY = "methodology/v1.yaml"
EXPECTED_IMPACT_METHODOLOGY = "methodology/v2.yaml"
# Everything besides the methodology file itself that can change a score or the
# verdict. A file left out of this list can be edited without the stamp moving.
HASHED_FILES = (
    "scoring_config.yaml", "sdg_keywords.yaml", "sdg_keywords_es.yaml", "sdg_keywords_fr.yaml",
    "sdg_keywords_pt.yaml", "sdg_keywords_zh.yaml",
    EXPECTED_IMPACT_METHODOLOGY,                 # expected impact, evidence quality, the IC gate
    "methodology/contribution_rubric.yaml",      # 5D Contribution and the enterprise / investor split
    "negative_impacts.yaml",                     # negative impacts and the evidence plan
)


def _methodology_path() -> Path:
    override = os.environ.get("IMPACT_VISION_METHODOLOGY", "").strip()
    return Path(override) if override else data_path(*DEFAULT_METHODOLOGY.split("/"))


@lru_cache(maxsize=4)
def _load(path: str) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw)
    # Sector baselines / keyword boosts and the SDG keyword map shape scores
    # too, so they are part of the hash.
    for extra in HASHED_FILES:
        extra_path = data_path(*extra.split("/"))
        if extra_path.exists():
            digest.update(extra_path.read_bytes())
    return (yaml.safe_load(raw.decode("utf-8")) or {}), digest.hexdigest()


def load_methodology() -> dict[str, Any]:
    return _load(str(_methodology_path()))[0]


def section(name: str) -> dict[str, Any]:
    return load_methodology().get(name) or {}


def methodology_version() -> str:
    return str(load_methodology().get("version", "unversioned"))


def config_hash(short: bool = True) -> str:
    digest = _load(str(_methodology_path()))[1]
    return digest[:12] if short else digest


def expected_impact_version() -> str:
    """Version of the expected-impact methodology, or "" when it does not drive the verdict."""
    from impact_vision.impact.expected_impact import methodology_mode

    if methodology_mode() != "2":
        return ""
    from impact_vision.impact.expected_impact import params

    return str(params().get("version", ""))


def methodology_stamp() -> dict[str, str]:
    """The stamp every output carries.

    ``methodology_version`` is the 5D / SDG / greenwashing methodology,
    ``expected_impact_version`` the one behind expected impact and the IC gate
    (absent when ``IMPACT_VISION_METHODOLOGY_VERSION=1``), and ``config_hash``
    covers both plus the data files in :data:`HASHED_FILES`.
    """
    stamp = {"methodology_version": methodology_version(), "config_hash": config_hash()}
    v2 = expected_impact_version()
    if v2:
        stamp["expected_impact_version"] = v2
    return stamp


def stamp_text(stamp: dict[str, str] | None = None) -> str:
    """One line for footers: both methodology versions and the config hash."""
    stamp = stamp or methodology_stamp()
    v1, v2 = stamp.get("methodology_version", ""), stamp.get("expected_impact_version", "")
    versions = f"v{v2} (expected impact, IC gate) · v{v1} (5D, SDG, greenwashing)" if v2 else f"v{v1}"
    return f"Methodology {versions} · config {stamp.get('config_hash', '')}"


def stamp_label() -> str:
    return stamp_text(methodology_stamp())


def clear_cache() -> None:
    _load.cache_clear()


# ---------------------------------------------------------------- appendix
def methodology_appendix() -> list[tuple[str, str]]:
    """Plain-English methodology rows generated from the YAML (English)."""
    fd, sdg, gw = section("five_dimensions"), section("sdg"), section("greenwashing")
    w = gw.get("weights", {})
    pts = sdg.get("max_points", {})
    bands = ", ".join(f"{b['grade']} ≥ {b['min']}" for b in fd.get("grade_bands", []) if b["min"] > 0)
    gw_bands = "; ".join(f"≤{b['max']} {b['label']}" for b in gw.get("classification", []))
    return [
        ("5 Dimensions",
         f"Each dimension scores 1–5: coverage of the theme's IRIS+ reference set × {fd.get('metric_scale')} "
         f"+ {fd.get('report_bonus')} when any metric is reported, plus up to {fd['extra_bonus']['max']} for "
         f"extra metrics. A dimension stays at or below {fd.get('cap_below_min_metrics')} until "
         f"{fd.get('min_metrics_for_above_baseline')} metrics hit its reference set; text-only inference is "
         f"clamped to {fd['baseline_clamp'][0]}–{fd['baseline_clamp'][1]}. Grades: {bands}."),
        ("5D penalties",
         f"Risk loses {fd['penalties']['adverse_per_unmitigated']} per unmitigated adverse impact (max "
         f"{fd['penalties']['adverse_max']}) and {fd['penalties']['exclusion_per_flag']} per exclusion flag "
         f"(max {fd['penalties']['exclusion_max']})."),
        ("SDGs",
         f"Each goal scores 0–100: up to {pts.get('metrics')} points from goal-specific metric coverage "
         f"(metrics tagged to {sdg.get('cross_cutting_min_goals')}+ goals count at "
         f"{sdg.get('cross_cutting_weight')} weight), up to {pts.get('inference')} from the business "
         f"description and up to {pts.get('theme')} from impact themes. High confidence needs "
         f"≥{sdg['confidence_bands']['high']} points and at least one goal-specific metric. "
         f"Own-footprint metrics ({', '.join(sdg.get('operational_footprint_metrics', []))}) are "
         "disclosure, not contribution, and count at the reduced weight."),
        ("Greenwashing",
         "Risk (0–100) weights claim–metric gaps ({:.0%}), missing negative impacts ({:.0%}), vague language "
         "({:.0%}), selective reporting ({:.0%}) and lack of verification ({:.0%}). Bands: {}.".format(
             w.get("claim_metric_gap", 0), w.get("adverse_omission", 0), w.get("specificity", 0),
             w.get("selectivity", 0), w.get("verification", 0), gw_bands)),
        ("Version", f"{stamp_label()} (effective {load_methodology().get('effective', '')})."),
    ]


__all__ = [
    "clear_cache",
    "config_hash",
    "load_methodology",
    "methodology_appendix",
    "methodology_stamp",
    "methodology_version",
    "section",
    "EXPECTED_IMPACT_METHODOLOGY",
    "HASHED_FILES",
    "expected_impact_version",
    "stamp_label",
    "stamp_text",
]
