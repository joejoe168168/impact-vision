"""EU Taxonomy alignment module.

Implements a high-level alignment check for the *EU Taxonomy Regulation*
(EU 2020/852) and the technical screening criteria laid out in Climate
Delegated Acts (EU 2021/2139, 2023/2485) and the Environmental Delegated Act
(EU 2023/2486).

Three-step assessment per economic activity:
  1. **Substantial Contribution** to ≥1 of the 6 environmental objectives.
  2. **Do No Significant Harm (DNSH)** to the other 5.
  3. **Minimum Safeguards** (OECD MNE, UNGP, ILO, IBHR).

This module returns the % of revenue / capex / opex aligned, plus per-
activity diagnostics. It is **screening-grade** — full Article 8 reporting
requires audited NACE-level data; we surface gaps for follow-up.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EnvObjective = Literal[
    "climate_mitigation",
    "climate_adaptation",
    "water",
    "circular_economy",
    "pollution_prevention",
    "biodiversity",
]


class EconomicActivity(BaseModel):
    """One economic activity inside a company's revenue / capex / opex split."""
    name: str
    nace_code: str = ""
    revenue_share_pct: float = Field(ge=0, le=100, default=0.0)
    capex_share_pct: float = Field(ge=0, le=100, default=0.0)
    opex_share_pct: float = Field(ge=0, le=100, default=0.0)
    primary_objective: EnvObjective | None = None
    eligible: bool = False
    substantial_contribution: bool = False
    dnsh_pass: bool = False
    minimum_safeguards: bool = False
    notes: str = ""


class TaxonomyAlignmentResult(BaseModel):
    company_name: str
    revenue_eligible_pct: float
    revenue_aligned_pct: float
    capex_eligible_pct: float
    capex_aligned_pct: float
    opex_eligible_pct: float
    opex_aligned_pct: float
    activities: list[EconomicActivity]
    findings: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)


# Common NACE→primary-objective hints (very rough — production users should
# load the official Annex I mapping). Surfaced here so the screener can flag
# obviously-eligible activities even when the user hasn't classified them.
NACE_OBJECTIVE_HINTS: dict[str, EnvObjective] = {
    "D35.11": "climate_mitigation",   # electricity production
    "D35.30": "climate_mitigation",   # district heating
    "F41": "climate_mitigation",      # construction of buildings
    "H49": "climate_mitigation",      # land transport
    "H51": "climate_mitigation",      # air transport
    "M71": "climate_adaptation",      # architecture / engineering
    "E37": "water",                   # sewerage
    "E38": "circular_economy",        # waste management
    "E39": "pollution_prevention",    # remediation
    "A02": "biodiversity",            # forestry
}


def _resolve_objective(activity: EconomicActivity) -> EnvObjective | None:
    if activity.primary_objective:
        return activity.primary_objective
    if activity.nace_code:
        for prefix, obj in NACE_OBJECTIVE_HINTS.items():
            if activity.nace_code.startswith(prefix):
                return obj
    return None


def assess_taxonomy_alignment(
    company_name: str,
    activities: list[EconomicActivity],
    *,
    minimum_safeguards_corporate: bool = True,
) -> TaxonomyAlignmentResult:
    """Compute taxonomy alignment % across an issuer's activities."""
    findings: list[str] = []
    refs = [
        "EU 2020/852 (Taxonomy Regulation)",
        "EU 2021/2139 (Climate Delegated Act)",
        "EU 2023/2485 (Climate Amending Act)",
        "EU 2023/2486 (Environmental Delegated Act)",
    ]

    rev_elig = rev_align = cap_elig = cap_align = op_elig = op_align = 0.0

    enriched: list[EconomicActivity] = []
    for a in activities:
        if not a.primary_objective:
            obj = _resolve_objective(a)
            if obj:
                a = a.model_copy(update={"primary_objective": obj})

        if a.eligible:
            rev_elig += a.revenue_share_pct
            cap_elig += a.capex_share_pct
            op_elig += a.opex_share_pct

        is_aligned = (
            a.eligible
            and a.substantial_contribution
            and a.dnsh_pass
            and (a.minimum_safeguards or minimum_safeguards_corporate)
        )
        if is_aligned:
            rev_align += a.revenue_share_pct
            cap_align += a.capex_share_pct
            op_align += a.opex_share_pct
        elif a.eligible:
            reasons = []
            if not a.substantial_contribution:
                reasons.append("no Substantial Contribution evidence")
            if not a.dnsh_pass:
                reasons.append("DNSH not demonstrated")
            if not (a.minimum_safeguards or minimum_safeguards_corporate):
                reasons.append("Minimum Safeguards not confirmed")
            findings.append(f"Activity '{a.name}' eligible but not aligned ({'; '.join(reasons)}).")

        enriched.append(a)

    if not minimum_safeguards_corporate:
        findings.append(
            "Corporate-level Minimum Safeguards not confirmed; no activity can be reported as aligned."
        )

    if rev_elig == 0:
        findings.append("No EU Taxonomy-eligible activities identified — alignment is 0%.")

    return TaxonomyAlignmentResult(
        company_name=company_name,
        revenue_eligible_pct=round(min(rev_elig, 100), 2),
        revenue_aligned_pct=round(min(rev_align, 100), 2),
        capex_eligible_pct=round(min(cap_elig, 100), 2),
        capex_aligned_pct=round(min(cap_align, 100), 2),
        opex_eligible_pct=round(min(op_elig, 100), 2),
        opex_aligned_pct=round(min(op_align, 100), 2),
        activities=enriched,
        findings=findings,
        references=refs,
    )
