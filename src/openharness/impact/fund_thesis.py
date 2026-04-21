"""Fund Impact Thesis — per-fund weights for SDGs and 5-Dimension scoring.

A fund-specific YAML controls (a) which SDGs the fund cares about and how
much, (b) how the 5 dimensions are weighted in the overall score, (c) the
pass-fail thresholds for IC submission, and (d) the LP reporting cadence.

Loading order (first match wins):
    1. Path passed to `load_fund_thesis(path=...)`
    2. $IMPACT_VISION_FUND_THESIS environment variable
    3. `data/fund_thesis.yaml` in the working directory
    4. `data/fund_thesis.example.yaml` (shipped) — for documentation

If nothing is loaded, an equal-weight default is returned and `is_default`
will be True so the dashboard can warn the analyst.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class ICGate(BaseModel):
    min_5d_overall: float = 2.5
    min_dd_coverage_pct: float = 70.0
    min_top_sdg_score: float = 60.0
    max_greenwashing_score: float = 40.0
    exclusion_must_pass: bool = True
    required_sectors: list[str] = Field(default_factory=list)
    forbidden_sectors: list[str] = Field(default_factory=list)


class AdverseThresholds(BaseModel):
    scope1_intensity_max_tco2e_per_eur_m: float | None = None
    worker_fatality_max_per_year: int | None = None
    npl_ratio_max_pct: float | None = None


class ReportingCadence(BaseModel):
    ilpa_esg: Literal["monthly", "quarterly", "semi_annually", "annually", "never"] = "annually"
    giin_iris: Literal["monthly", "quarterly", "semi_annually", "annually", "never"] = "annually"
    edci: Literal["monthly", "quarterly", "semi_annually", "annually", "never"] = "annually"
    sfdr_pai: Literal["monthly", "quarterly", "semi_annually", "annually", "never"] = "annually"
    fund_impact_letter: Literal["monthly", "quarterly", "semi_annually", "annually", "never"] = "semi_annually"


class FundThesis(BaseModel):
    """Resolved fund impact thesis."""

    name: str = "Default Fund"
    manager: str = ""
    vintage_year: int = 0
    fund_size_eur_m: float = 0
    strategy: str = "impact_first"
    asset_class: str = "private_equity"
    geography_focus: list[str] = Field(default_factory=list)

    sdg_weights: dict[int, float] = Field(default_factory=dict)
    five_d_weights: dict[str, float] = Field(default_factory=dict)
    ic_gate: ICGate = Field(default_factory=ICGate)
    adverse_thresholds: AdverseThresholds = Field(default_factory=AdverseThresholds)
    reporting_cadence: ReportingCadence = Field(default_factory=ReportingCadence)

    is_default: bool = False
    source_path: str = ""

    @model_validator(mode="after")
    def _normalise_weights(self) -> "FundThesis":
        if not self.five_d_weights:
            self.five_d_weights = {
                "what": 0.20, "who": 0.20, "how_much": 0.20,
                "contribution": 0.20, "risk": 0.20,
            }
        if not self.sdg_weights:
            self.sdg_weights = {g: 1.0 / 17 for g in range(1, 18)}
        # Re-normalise so users can write "raw" weights
        s = sum(self.sdg_weights.values())
        if s > 0:
            self.sdg_weights = {k: v / s for k, v in self.sdg_weights.items()}
        s = sum(self.five_d_weights.values())
        if s > 0:
            self.five_d_weights = {k: v / s for k, v in self.five_d_weights.items()}
        return self


def _candidates(explicit: str | None) -> list[Path]:
    out: list[Path] = []
    if explicit:
        out.append(Path(explicit))
    env = os.environ.get("IMPACT_VISION_FUND_THESIS")
    if env:
        out.append(Path(env))
    out.append(Path("data/fund_thesis.yaml"))
    pkg_root = Path(__file__).parent.parent.parent.parent
    out.extend([
        pkg_root / "data" / "fund_thesis.yaml",
        pkg_root / "data" / "fund_thesis.example.yaml",
    ])
    return out


def load_fund_thesis(path: str | None = None) -> FundThesis:
    """Load the fund thesis from YAML.

    Returns a default (equal-weight) thesis with `is_default=True` if nothing
    is found.
    """
    for candidate in _candidates(path):
        if not candidate.exists():
            continue
        try:
            raw = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        fund = raw.get("fund") or {}
        thesis = FundThesis(
            **fund,
            sdg_weights={int(k): float(v) for k, v in (raw.get("sdg_weights") or {}).items()},
            five_d_weights={str(k): float(v) for k, v in (raw.get("five_d_weights") or {}).items()},
            ic_gate=ICGate(**(raw.get("ic_gate") or {})),
            adverse_thresholds=AdverseThresholds(**(raw.get("adverse_thresholds") or {})),
            reporting_cadence=ReportingCadence(**(raw.get("reporting_cadence") or {})),
            source_path=str(candidate),
        )
        return thesis
    return FundThesis(is_default=True)


# ---------------------------------------------------------------------------
# Weighted roll-up helpers
# ---------------------------------------------------------------------------

def weighted_5d_overall(
    five_d: dict[str, float] | object,
    thesis: FundThesis,
) -> float:
    """Compute a fund-thesis-weighted overall 5D score (1-5).

    Accepts a dict or a `FiveDimensionScore` pydantic model.
    """
    if hasattr(five_d, "what"):
        scores = {
            "what": getattr(five_d.what, "score", 0),
            "who": getattr(five_d.who, "score", 0),
            "how_much": getattr(five_d.how_much, "score", 0),
            "contribution": getattr(five_d.contribution, "score", 0),
            "risk": getattr(five_d.risk, "score", 0),
        }
    else:
        scores = dict(five_d)

    total = 0.0
    for dim, score in scores.items():
        total += float(score) * thesis.five_d_weights.get(dim, 0.0)
    return round(total, 2)


def weighted_sdg_overall(
    sdg_alignments: list[object],
    thesis: FundThesis,
) -> float:
    """Compute a fund-thesis-weighted SDG score (0-100).

    Each alignment contributes its score weighted by the fund's SDG weight.
    SDGs the fund doesn't care about contribute zero.
    """
    total = 0.0
    for a in sdg_alignments:
        goal = int(getattr(a, "goal", 0))
        score = float(getattr(a, "score", 0))
        total += score * thesis.sdg_weights.get(goal, 0.0)
    return round(total, 1)
