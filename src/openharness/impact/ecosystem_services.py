"""Ecosystem service valuation (Phase 19).

Offline approximation of the four headline ecosystem services modelled
by InVEST and ARIES. Swap in a real InVEST run by implementing the
:class:`EcosystemProvider` Protocol; the bundled
:class:`UnitValueProvider` uses per-hectare-per-year shadow prices
drawn from published meta-analyses so demos give plausible numbers
offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


EcosystemServiceType = Literal[
    "carbon-sequestration",
    "water-purification",
    "pollination",
    "flood-control",
]


class EcosystemAsset(BaseModel):
    """Land parcel under study."""

    asset_id: str
    name: str = ""
    hectares: float = Field(gt=0)
    land_cover: str = "mixed"  # forest, wetland, cropland, etc.


class EcosystemValuation(BaseModel):
    asset_id: str
    service: EcosystemServiceType
    unit_value_usd_per_ha_per_year: float
    hectares: float
    annual_value_usd: float
    methodology_note: str = ""


@runtime_checkable
class EcosystemProvider(Protocol):
    id: str

    def value(
        self, asset: EcosystemAsset, service: EcosystemServiceType
    ) -> EcosystemValuation | None:  # pragma: no cover
        ...


# Default unit values — order-of-magnitude correct; swap with an InVEST /
# ARIES run when precision is required.
_UNIT_VALUES = {
    "forest": {
        "carbon-sequestration": 250.0,
        "water-purification": 180.0,
        "pollination": 90.0,
        "flood-control": 120.0,
    },
    "wetland": {
        "carbon-sequestration": 320.0,
        "water-purification": 420.0,
        "pollination": 40.0,
        "flood-control": 300.0,
    },
    "cropland": {
        "carbon-sequestration": 50.0,
        "water-purification": 30.0,
        "pollination": 200.0,
        "flood-control": 60.0,
    },
    "grassland": {
        "carbon-sequestration": 90.0,
        "water-purification": 70.0,
        "pollination": 150.0,
        "flood-control": 80.0,
    },
    "mixed": {
        "carbon-sequestration": 180.0,
        "water-purification": 140.0,
        "pollination": 110.0,
        "flood-control": 150.0,
    },
}


@dataclass
class UnitValueProvider:
    """Offline meta-analysis default."""

    id: str = "offline-unit-values"

    def value(self, asset: EcosystemAsset, service: EcosystemServiceType) -> EcosystemValuation:
        lc = asset.land_cover.lower()
        table = _UNIT_VALUES.get(lc, _UNIT_VALUES["mixed"])
        unit = table.get(service, 100.0)
        annual = unit * asset.hectares
        return EcosystemValuation(
            asset_id=asset.asset_id,
            service=service,
            unit_value_usd_per_ha_per_year=unit,
            hectares=asset.hectares,
            annual_value_usd=round(annual, 2),
            methodology_note=(
                "Offline unit-value lookup — replace with InVEST / ARIES "
                "simulation for publication-grade numbers."
            ),
        )


_PROVIDERS: dict[str, EcosystemProvider] = {}


def register_ecosystem_provider(p: EcosystemProvider) -> None:
    if not getattr(p, "id", None):
        raise ValueError("provider must have id")
    _PROVIDERS[p.id] = p


def get_ecosystem_provider(provider_id: str = "offline-unit-values") -> EcosystemProvider:
    return _PROVIDERS[provider_id]


register_ecosystem_provider(UnitValueProvider())


# IAPB / Biodiversity Credit Alliance / WEF High-Level Principles (21),
# grouped as nature outcomes, equity for people, and good governance.
BIODIVERSITY_CREDIT_PRINCIPLES = [
    {
        "id": "BCP-01",
        "pillar": "outcomes",
        "principle": "Nature-positive, quantified outcomes",
        "assessment_question": "Do credits represent verified, quantified gains for nature (not avoided loss alone unless additional)?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-02",
        "pillar": "outcomes",
        "principle": "Additionality",
        "assessment_question": "Would the outcome have occurred without the credit activity?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-03",
        "pillar": "outcomes",
        "principle": "Robust baselines",
        "assessment_question": "Is the baseline conservative, documented, and aligned to a recent ecological reference?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-04",
        "pillar": "outcomes",
        "principle": "Leakage addressed",
        "assessment_question": "Are activity-shifting and market leakage assessed and deducted?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-05",
        "pillar": "outcomes",
        "principle": "Durability / permanence",
        "assessment_question": "Is there a durability mechanism (buffer, insurance, long-term stewardship)?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-06",
        "pillar": "outcomes",
        "principle": "No double counting",
        "assessment_question": "Are units uniquely serialised and excluded from overlapping claims?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-07",
        "pillar": "outcomes",
        "principle": "Independent MRV",
        "assessment_question": "Is monitoring, reporting and verification independent of the project proponent?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-08",
        "pillar": "equity",
        "principle": "Indigenous Peoples and local community rights",
        "assessment_question": "Are IPLC land, resource and knowledge rights recognised in project design?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-09",
        "pillar": "equity",
        "principle": "Free, Prior and Informed Consent",
        "assessment_question": "Was FPIC obtained where Indigenous Peoples or customary rights-holders are affected?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-10",
        "pillar": "equity",
        "principle": "Equitable benefit-sharing",
        "assessment_question": "Is there a documented, fair benefit-sharing arrangement with rights-holders?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-11",
        "pillar": "equity",
        "principle": "Do-no-harm safeguards",
        "assessment_question": "Are social and environmental safeguards in place and monitored?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-12",
        "pillar": "equity",
        "principle": "Gender equality and social inclusion",
        "assessment_question": "Do design and benefit-sharing address gender and inclusion explicitly?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-13",
        "pillar": "equity",
        "principle": "Inclusive participation",
        "assessment_question": "Can affected people participate in design, monitoring and governance?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-14",
        "pillar": "equity",
        "principle": "Accessible grievance and redress",
        "assessment_question": "Is there an independent, accessible grievance mechanism with remedy?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-15",
        "pillar": "governance",
        "principle": "Transparency of supply and claims",
        "assessment_question": "Are methodologies, issuance, retirements and claims publicly disclosed?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-16",
        "pillar": "governance",
        "principle": "Unique serialisation and registry",
        "assessment_question": "Are units tracked on a public registry with unique IDs?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-17",
        "pillar": "governance",
        "principle": "Independent validation and verification",
        "assessment_question": "Are validation and verification done by an accredited third party?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-18",
        "pillar": "governance",
        "principle": "Science-based methodologies",
        "assessment_question": "Is the methodology peer-reviewed and aligned to ecological science?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-19",
        "pillar": "governance",
        "principle": "Legal underpinning and tenure",
        "assessment_question": "Are land/resource tenure and the legal right to issue credits documented?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-20",
        "pillar": "governance",
        "principle": "Adaptive management",
        "assessment_question": "Can the project revise activities when monitoring shows under-delivery?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
    {
        "id": "BCP-21",
        "pillar": "governance",
        "principle": "Accountability, liability and buyer due diligence",
        "assessment_question": "Are reversal liability and buyer due-diligence expectations defined?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    },
]


def screen_biodiversity_credit(answers: dict[str, int]) -> dict:
    answers = answers or {}
    pillars = {}
    gaps = []
    for pillar in ("outcomes", "equity", "governance"):
        relevant = [item for item in BIODIVERSITY_CREDIT_PRINCIPLES if item["pillar"] == pillar]
        score = sum(max(0, min(2, int(answers.get(item["id"], 0)))) for item in relevant)
        pillars[pillar] = round(100 * score / (2 * len(relevant)), 1)
        gaps.extend(
            {"id": item["id"], "principle": item["principle"]}
            for item in relevant
            if int(answers.get(item["id"], 0)) < 2
        )
    overall = sum(pillars.values()) / len(pillars)
    unanswered = [item["id"] for item in BIODIVERSITY_CREDIT_PRINCIPLES if item["id"] not in answers]
    band = (
        "high"
        if overall >= 80 and not unanswered
        else "medium"
        if overall >= 50
        else "low"
    )
    return {
        "score": round(overall, 1),
        "per_pillar": pillars,
        "quality_band": band,
        "gaps": gaps,
        "unanswered": unanswered,
        "principles": BIODIVERSITY_CREDIT_PRINCIPLES,
        "status": "indicative",
        "as_of": "2026-07",
        "citations": [
            "IAPB / Biodiversity Credit Alliance / WEF High-Level Principles to Guide the Biodiversity Credit Market"
        ],
    }


__all__ = [
    "EcosystemAsset",
    "EcosystemServiceType",
    "EcosystemValuation",
    "EcosystemProvider",
    "UnitValueProvider",
    "register_ecosystem_provider",
    "get_ecosystem_provider",
    "BIODIVERSITY_CREDIT_PRINCIPLES",
    "screen_biodiversity_credit",
]
