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


BIODIVERSITY_CREDIT_PRINCIPLES = [
    {
        "id": f"BCP-{i:02d}",
        "pillar": ("outcomes" if i <= 7 else "equity" if i <= 14 else "governance"),
        "principle": f"High-integrity biodiversity credit principle {i}",
        "assessment_question": f"Is principle {i} evidenced?",
        "scoring_guidance": "0 absent; 1 partial; 2 evidenced",
        "source": "IAPB/BCA/WEF High-Level Principles",
    }
    for i in range(1, 22)
]


def screen_biodiversity_credit(answers: dict[str, int]) -> dict:
    pillars = {}
    gaps = []
    for pillar in ("outcomes", "equity", "governance"):
        relevant = [item for item in BIODIVERSITY_CREDIT_PRINCIPLES if item["pillar"] == pillar]
        score = sum(max(0, min(2, int(answers.get(item["id"], 0)))) for item in relevant)
        pillars[pillar] = round(100 * score / (2 * len(relevant)), 1)
        gaps.extend(item["id"] for item in relevant if item["id"] not in answers)
    overall = sum(pillars.values()) / len(pillars)
    band = "high" if overall >= 80 and not gaps else "medium" if overall >= 50 else "low"
    return {"score": round(overall, 1), "per_pillar": pillars, "quality_band": band, "gaps": gaps}


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
