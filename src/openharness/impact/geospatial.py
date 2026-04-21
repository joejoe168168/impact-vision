"""Satellite-derived outcome layer (Phase 19).

Pluggable :class:`SatelliteProvider` Protocol plus an in-memory stub
that returns deterministic values for four widely used datasets:

* **Global Forest Watch (GFW)** — tree-cover loss (ha).
* **VIIRS Nightlights** — mean radiance (W·sr⁻¹·cm⁻²).
* **Sentinel-5P** — NO2 / CH4 tropospheric columns.
* **ESA WorldCover** — land-cover class proportions.

The stub is deterministic so demos & tests are reproducible; real
adapters (Google Earth Engine, Sentinel Hub, Planet Labs, Microsoft
Planetary Computer) follow the same Protocol.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


SatelliteDataset = Literal[
    "gfw-tree-cover-loss",
    "viirs-nightlights",
    "sentinel5p-no2",
    "sentinel5p-ch4",
    "worldcover",
]


class AssetLocation(BaseModel):
    """One geo-located asset we want to observe."""

    asset_id: str
    name: str = ""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    buffer_km: float = Field(ge=0, default=1.0)


class SatelliteObservation(BaseModel):
    asset_id: str
    dataset: SatelliteDataset
    observation_date: date
    value: float
    unit: str
    provider_id: str
    source_confidence: float = Field(ge=0, le=1, default=0.7)


@runtime_checkable
class SatelliteProvider(Protocol):
    id: str
    def observe(self, asset: AssetLocation, dataset: SatelliteDataset, obs_date: date) -> SatelliteObservation | None:  # pragma: no cover
        ...


# ---------------------------------------------------------------------------
# Deterministic offline stub
# ---------------------------------------------------------------------------

_DEFAULT_UNITS: dict[SatelliteDataset, str] = {
    "gfw-tree-cover-loss": "ha",
    "viirs-nightlights": "W·sr⁻¹·cm⁻²",
    "sentinel5p-no2": "mol/m²",
    "sentinel5p-ch4": "ppb",
    "worldcover": "proportion-forest",
}


@dataclass
class DeterministicSatelliteProvider:
    """Hash-based stub — same asset + dataset + date → same observation."""

    id: str = "deterministic"

    def observe(
        self,
        asset: AssetLocation,
        dataset: SatelliteDataset,
        obs_date: date,
    ) -> SatelliteObservation:
        key = f"{asset.asset_id}|{dataset}|{obs_date.isoformat()}".encode("utf-8")
        h = int(hashlib.sha256(key).hexdigest(), 16)
        # Range per dataset so values look plausible in charts
        if dataset == "gfw-tree-cover-loss":
            value = round((h % 1000) / 10.0, 2)        # 0–100 ha
        elif dataset == "viirs-nightlights":
            value = round((h % 1000) / 100.0, 3)       # 0–10
        elif dataset == "sentinel5p-no2":
            value = round(1e-5 + (h % 1000) * 1e-7, 8)
        elif dataset == "sentinel5p-ch4":
            value = round(1800 + (h % 100), 1)
        else:  # worldcover proportion
            value = round((h % 100) / 100.0, 2)
        return SatelliteObservation(
            asset_id=asset.asset_id,
            dataset=dataset,
            observation_date=obs_date,
            value=value,
            unit=_DEFAULT_UNITS[dataset],
            provider_id=self.id,
            source_confidence=0.7,
        )


_PROVIDERS: dict[str, SatelliteProvider] = {}


def register_satellite_provider(p: SatelliteProvider) -> None:
    if not getattr(p, "id", None):
        raise ValueError("provider must have id")
    _PROVIDERS[p.id] = p


def get_satellite_provider(provider_id: str = "deterministic") -> SatelliteProvider:
    return _PROVIDERS[provider_id]


register_satellite_provider(DeterministicSatelliteProvider())


__all__ = [
    "AssetLocation",
    "SatelliteDataset",
    "SatelliteObservation",
    "SatelliteProvider",
    "DeterministicSatelliteProvider",
    "register_satellite_provider",
    "get_satellite_provider",
]
