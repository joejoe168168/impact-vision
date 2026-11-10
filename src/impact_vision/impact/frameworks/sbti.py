"""SBTi — Science Based Targets initiative alignment checker.

Evaluates a company's emissions reduction commitments against the numerical
thresholds of the *SBTi Corporate Net-Zero Standard V1* and the near-term
criteria. The versions accepted for submissions on a given day (V1.3.1 until
2028-01-31, V2.0 from 2027-02-01) come from ``data/frameworks/updates.yaml``.
V2.0's own thresholds are not encoded (its text was not read): the check says
which thresholds it applied and, once V2.0 is accepted, that a V2.0 review is due.

References:
- https://sciencebasedtargets.org/resources/files/Net-Zero-Standard.pdf
- https://sciencebasedtargets.org/resources/files/SBTi-criteria.pdf
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


SBTiStatus = Literal["committed", "near_term_validated", "net_zero_validated", "removed", "expired", "none"]


class SBTiClaim(BaseModel):
    """Claims provided by a company about its targets."""
    company_name: str
    base_year: int | None = None
    target_year_near_term: int | None = None
    near_term_pct_reduction: float | None = None
    target_year_net_zero: int | None = None
    net_zero_pct_reduction: float | None = None
    scope1_2_covered: bool = False
    scope3_covered: bool = False
    scope3_pct_of_inventory: float = 0.0
    sbti_status: SBTiStatus = "none"
    aligned_to_15c: bool | None = None
    sector: str = ""


class SBTiAlignmentCheck(BaseModel):
    company_name: str
    overall_alignment: Literal["aligned", "partially_aligned", "not_aligned", "insufficient_data"]
    near_term_pass: bool
    net_zero_pass: bool
    scope3_pass: bool
    thresholds_version: str = "CNZS_V1"
    standards_accepted: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)


# Minimum cross-sector reduction rates (Scope 1+2) per SBTi:
# - 1.5°C pathway: 4.2% linear annual reduction
# - Well-below 2°C: 2.5%
# - 2°C: 1.23% (no longer accepted by SBTi for new targets since Jul 2022)
NEAR_TERM_MIN_PCT_15C = 42.0  # for 10-year target
SCOPE3_THRESHOLD_INVENTORY_PCT = 40.0
SCOPE3_TARGET_REQUIRED_COVERAGE = 67.0  # SBTi: must cover 2/3 of total Scope 3 if material
NET_ZERO_TARGET_LATEST_YEAR = 2050
NET_ZERO_MIN_REDUCTION_PCT = 90.0


def _versions_in_force(today: date) -> list[dict[str, Any]]:
    from impact_vision.impact.frameworks import pack_updates

    rows: list[dict[str, Any]] = pack_updates.sbti_standard_in_force(today)
    return rows


def check_sbti_alignment(claim: SBTiClaim, *, today: date | None = None) -> SBTiAlignmentCheck:
    today = today or date.today()
    findings: list[str] = []
    recommendations: list[str] = []
    from impact_vision.impact.frameworks import pack_updates

    thresholds = pack_updates.sbti_thresholds()
    applied = pack_updates.sbti_standard(str(thresholds.get("version", "CNZS_V1"))) or {}
    accepted = _versions_in_force(today)
    refs: list[str] = [f"Thresholds applied: {applied.get('title', thresholds.get('version'))}"
                       f" ({applied.get('source_url', '')})"]

    # Near-term target validation
    near_term_pass = False
    if claim.target_year_near_term and claim.near_term_pct_reduction is not None and claim.base_year:
        years = claim.target_year_near_term - claim.base_year
        if years <= 0 or years > 15:
            findings.append(
                f"Near-term target window ({years} years) outside SBTi 5-15 year range."
            )
        else:
            required = (NEAR_TERM_MIN_PCT_15C / 10) * years
            if claim.near_term_pct_reduction >= required:
                near_term_pass = True
                findings.append(
                    f"Near-term target meets 1.5°C pathway "
                    f"({claim.near_term_pct_reduction:.1f}% vs required {required:.1f}%)."
                )
            else:
                findings.append(
                    f"Near-term target below 1.5°C pathway "
                    f"({claim.near_term_pct_reduction:.1f}% vs required {required:.1f}%)."
                )
                recommendations.append(
                    f"Increase near-term target to ≥{required:.1f}% by {claim.target_year_near_term}."
                )
    else:
        findings.append("No quantified near-term target with base year provided.")
        recommendations.append("Set a 5-15 year near-term target with explicit base year and Scope 1+2 reduction %.")

    # Net-zero target validation
    net_zero_pass = False
    if claim.target_year_net_zero and claim.net_zero_pct_reduction is not None:
        if claim.target_year_net_zero > NET_ZERO_TARGET_LATEST_YEAR:
            findings.append(
                f"Net-zero target year {claim.target_year_net_zero} exceeds SBTi maximum {NET_ZERO_TARGET_LATEST_YEAR}."
            )
        elif claim.net_zero_pct_reduction < NET_ZERO_MIN_REDUCTION_PCT:
            findings.append(
                f"Net-zero reduction commitment ({claim.net_zero_pct_reduction:.1f}%) "
                f"below SBTi minimum ({NET_ZERO_MIN_REDUCTION_PCT:.0f}%)."
            )
            recommendations.append(
                f"Commit to ≥{NET_ZERO_MIN_REDUCTION_PCT:.0f}% absolute reduction by {claim.target_year_net_zero}; "
                "neutralise residuals with permanent removals."
            )
        else:
            net_zero_pass = True
            findings.append("Net-zero commitment meets SBTi Net-Zero Standard.")
    else:
        findings.append("No net-zero target submitted.")
        recommendations.append("Set a net-zero target ≤2050 with ≥90% absolute reduction.")

    # Scope 3
    scope3_pass = True
    if claim.scope3_pct_of_inventory >= SCOPE3_THRESHOLD_INVENTORY_PCT:
        if not claim.scope3_covered:
            scope3_pass = False
            findings.append(
                f"Scope 3 emissions are material ({claim.scope3_pct_of_inventory:.0f}% of inventory) "
                "but no Scope 3 target is set."
            )
            recommendations.append(
                f"Set a Scope 3 target covering ≥{SCOPE3_TARGET_REQUIRED_COVERAGE:.0f}% of category inventory."
            )

    # Status sanity checks
    if claim.sbti_status == "removed" or claim.sbti_status == "expired":
        findings.append(f"SBTi status flagged as {claim.sbti_status} — public commitments lapsed.")
        recommendations.append("Re-submit targets to SBTi for re-validation.")

    # Version window (R6): say which thresholds were used when a later version is accepted.
    accepted_ids = [row["id"] for row in accepted]
    if not thresholds.get("v2_thresholds_recorded") and "CNZS_V2" in accepted_ids:
        only_v2 = thresholds.get("version") not in accepted_ids
        findings.append(
            "Checked against the V1 numerical thresholds; Corporate Net-Zero Standard V2.0 "
            + ("is the only version accepted for new submissions" if only_v2 else "is also accepted")
            + f" on {today.isoformat()} and its criteria are not encoded here."
        )
        recommendations.append("Review the targets against the SBTi Corporate Net-Zero Standard V2.0 criteria.")

    # Aggregate
    has_data = bool(claim.target_year_near_term or claim.target_year_net_zero)
    if not has_data:
        overall: Literal["aligned", "partially_aligned", "not_aligned", "insufficient_data"] = "insufficient_data"
    elif near_term_pass and net_zero_pass and scope3_pass:
        overall = "aligned"
    elif near_term_pass or net_zero_pass:
        overall = "partially_aligned"
    else:
        overall = "not_aligned"

    return SBTiAlignmentCheck(
        company_name=claim.company_name,
        overall_alignment=overall,
        near_term_pass=near_term_pass,
        net_zero_pass=net_zero_pass,
        scope3_pass=scope3_pass,
        thresholds_version=str(thresholds.get("version", "CNZS_V1")),
        standards_accepted=accepted_ids,
        findings=findings,
        recommendations=recommendations,
        references=refs + [
            f"{row['title']} — accepted for target submissions on {today.isoformat()} ({row['source_url']})"
            for row in accepted
        ],
    )
