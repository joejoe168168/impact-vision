"""Per-jurisdiction regulatory packs (Phase 20).

Static library of the disclosure-regime requirements GPs hit in the
seven most active impact-investing jurisdictions. Each pack enumerates:

* **Mandatory filings** — what must be submitted, at what cadence.
* **Metric mapping** — which IRIS+ / ESRS / SFDR PAI metrics satisfy the
  regime.
* **Thresholds & timelines** — who is in scope and by when.

These are intended as *guidance defaults*. The legal advisor on a deal
should always double-check current wording — regulators update their
technical standards roughly annually.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Jurisdiction = Literal[
    "EU-SFDR",
    "EU-CSRD",
    "EU-CSDDD",
    "UK-FCA-SDR",
    "US-SEC-ESG",
    "HK-HKEX-ESG",
    "AU-AASB-S2",
    "GLOBAL-ISSB",
    "US-CA-CLIMATE",
]


class RegulatoryFiling(BaseModel):
    name: str
    cadence: Literal["annual", "biennial", "semi-annual", "quarterly", "event-driven"]
    format: str = ""
    deadline_days_after_period: int = 120
    mandatory_for: str = "all funds in scope"


class RegulatoryPack(BaseModel):
    jurisdiction: Jurisdiction
    issuer: str
    in_scope_summary: str
    filings: list[RegulatoryFiling]
    required_metrics: list[str] = Field(default_factory=list)
    notes: str = ""
    as_of: str = Field(default="", description="Date the pack was last verified, YYYY-MM-DD")
    legal_basis: str = Field(
        default="", description="Primary legal citation, e.g. Directive (EU) 2026/470"
    )
    last_verified: str = ""
    source_url: str = ""


def _load_packs() -> dict[str, RegulatoryPack]:
    """Packs from ``data/regulatory/packs.yaml`` (W5.1)."""
    from impact_vision.impact.knowledge import load_knowledge

    payload = load_knowledge("regulatory/packs.yaml")
    return {row["jurisdiction"]: RegulatoryPack.model_validate(row) for row in payload.get("packs", [])}


_PACKS: dict[str, RegulatoryPack] = _load_packs()


def list_packs() -> list[RegulatoryPack]:
    return list(_PACKS.values())


def get_pack(jurisdiction: str) -> RegulatoryPack:
    key = jurisdiction.upper()
    if key not in _PACKS:
        raise KeyError(f"Unknown jurisdiction '{jurisdiction}'. Known: {sorted(_PACKS)}")
    return _PACKS[key]


def ca_climate_scope(revenue_usd: float, does_business_in_ca: bool) -> dict:
    sb253 = bool(does_business_in_ca and revenue_usd > 1_000_000_000)
    sb261 = bool(does_business_in_ca and revenue_usd > 500_000_000)
    return {
        "sb253": sb253,
        "sb261": sb261,
        "deadlines": [
            {"law": "SB 253", "scope": "Scope 1 and 2", "due": "2026-11-10"},
            {"law": "SB 253", "scope": "Scope 3", "due": "2027"},
            {"law": "SB 261", "scope": "Biennial climate-risk report", "due": "stayed"},
        ]
        if sb253 or sb261
        else [],
        "assurance": "limited assurance for Scope 1/2, phasing toward reasonable assurance",
        "enforcement_notes": "SB 261 enforcement stayed pending Ninth Circuit appeal",
        "disclosure_mapping": ["TCFD-GOV", "TCFD-STR", "TCFD-RM", "TCFD-MET"],
        "as_of": "2026-02-26",
        "citations": [
            "California SB 253",
            "California SB 261",
            "CARB initial regulations 2026-02-26",
        ],
    }


__all__ = [
    "Jurisdiction",
    "RegulatoryFiling",
    "RegulatoryPack",
    "ca_climate_scope",
    "list_packs",
    "get_pack",
]
