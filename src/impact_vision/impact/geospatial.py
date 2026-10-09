"""Satellite-derived outcome layer (Phase 19).

Pluggable :class:`SatelliteProvider` Protocol plus an in-memory provider
that returns deterministic, **biome-aware** values for four widely used
datasets:

* **Global Forest Watch (GFW)** — tree-cover loss (ha), capped by biome.
* **VIIRS Nightlights** — mean radiance (W·sr⁻¹·cm⁻²), urban vs rural.
* **Sentinel-5P** — NO2 / CH4 tropospheric columns.
* **ESA WorldCover** — land-cover class proportions.

Values are reproducible (same asset + dataset + date → same observation)
so demos and tests stay offline. Real adapters (Google Earth Engine,
Sentinel Hub, Planet, Planetary Computer) implement the same Protocol.
This is **not** a substitute for a licensed GEE/GFW extract.
"""
from __future__ import annotations

import hashlib
import math
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

Biome = Literal[
    "tropical_forest",
    "boreal_forest",
    "temperate_forest",
    "grassland",
    "desert",
    "tundra",
    "urban",
    "coastal",
    "ocean",
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
    biome: Biome | None = None
    dataset_version: str = ""
    methodology_note: str = ""


@runtime_checkable
class SatelliteProvider(Protocol):
    id: str
    def observe(self, asset: AssetLocation, dataset: SatelliteDataset, obs_date: date) -> SatelliteObservation | None:  # pragma: no cover
        ...


_DEFAULT_UNITS: dict[SatelliteDataset, str] = {
    "gfw-tree-cover-loss": "ha",
    "viirs-nightlights": "W·sr⁻¹·cm⁻²",
    "sentinel5p-no2": "mol/m²",
    "sentinel5p-ch4": "ppb",
    "worldcover": "proportion-forest",
}

_DATASET_VERSIONS: dict[SatelliteDataset, str] = {
    "gfw-tree-cover-loss": "GFC v1.11 (Hansen / UMD / GFW)",
    "viirs-nightlights": "VIIRS VNP46A2",
    "sentinel5p-no2": "Sentinel-5P OFFL NO2",
    "sentinel5p-ch4": "Sentinel-5P OFFL CH4",
    "worldcover": "ESA WorldCover 2021 v200",
}

# Rough tree-cover-loss cap (ha / km²-year equivalent) so Dubai cannot
# "lose" Amazon-scale forest. Noise from the hash stays inside the cap.
_LOSS_CAP_HA: dict[Biome, float] = {
    "tropical_forest": 80.0,
    "boreal_forest": 40.0,
    "temperate_forest": 25.0,
    "grassland": 8.0,
    "desert": 0.4,
    "tundra": 1.5,
    "urban": 2.0,
    "coastal": 12.0,
    "ocean": 0.0,
}

_FOREST_PRIOR: dict[Biome, float] = {
    "tropical_forest": 0.82,
    "boreal_forest": 0.70,
    "temperate_forest": 0.55,
    "grassland": 0.12,
    "desert": 0.02,
    "tundra": 0.08,
    "urban": 0.10,
    "coastal": 0.25,
    "ocean": 0.0,
}

_NIGHTLIGHT_PRIOR: dict[Biome, float] = {
    "urban": 6.5,
    "coastal": 2.2,
    "temperate_forest": 0.8,
    "tropical_forest": 0.4,
    "grassland": 0.5,
    "boreal_forest": 0.3,
    "desert": 0.2,
    "tundra": 0.1,
    "ocean": 0.05,
}


def classify_biome(latitude: float, longitude: float) -> Biome:
    """Coarse biome prior from lat/lon — not a land-cover classification."""
    lat = abs(float(latitude))
    lon = float(longitude)
    # Crude urban clusters (city centroids, ~1° boxes) so nightlights lift.
    urban_centroids = (
        (40.7, -74.0),
        (51.5, -0.1),
        (35.7, 139.7),
        (22.3, 114.2),
        (1.3, 103.8),
        (19.1, 72.9),
        (-23.5, -46.6),
        (30.0, 31.2),
        (6.5, 3.4),
        (39.9, 116.4),
    )
    for ulat, ulon in urban_centroids:
        if abs(latitude - ulat) < 0.8 and abs(lon - ulon) < 0.8:
            return "urban"
    if lat > 66:
        return "tundra"
    if lat < 8 and abs(lon) > 160:
        return "ocean"
    # Sahara / Arabian / Australian arid belts
    if 15 <= latitude <= 32 and (-18 <= lon <= 60):
        return "desert"
    if -30 <= latitude <= -20 and 115 <= lon <= 145:
        return "desert"
    if lat < 15 and -80 <= lon <= -35:
        return "tropical_forest"  # Amazon / Congo-ish longitudes handled below
    if lat < 12 and 8 <= lon <= 32:
        return "tropical_forest"
    if lat < 10 and 95 <= lon <= 150:
        return "tropical_forest"
    if 45 <= lat <= 66:
        return "boreal_forest"
    if 30 <= lat < 45:
        return "temperate_forest"
    if 15 <= lat < 30:
        return "grassland"
    if abs(longitude) > 170:
        return "ocean"
    return "coastal" if abs(latitude) < 5 else "temperate_forest"


def _hash_unit(asset: AssetLocation, dataset: SatelliteDataset, obs_date: date) -> float:
    key = f"{asset.asset_id}|{dataset}|{obs_date.isoformat()}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest(), 16) / 2**256


@dataclass
class DeterministicSatelliteProvider:
    """Biome-aware deterministic provider — not a live satellite extract."""

    id: str = "deterministic"

    def observe(
        self,
        asset: AssetLocation,
        dataset: SatelliteDataset,
        obs_date: date,
    ) -> SatelliteObservation:
        biome = classify_biome(asset.latitude, asset.longitude)
        noise = _hash_unit(asset, dataset, obs_date)
        area = max(0.2, math.pi * (asset.buffer_km ** 2))
        if dataset == "gfw-tree-cover-loss":
            cap = _LOSS_CAP_HA[biome] * min(area, 20.0) / 3.14
            value = round(cap * noise, 2)
        elif dataset == "viirs-nightlights":
            prior = _NIGHTLIGHT_PRIOR[biome]
            value = round(prior * (0.6 + 0.8 * noise), 3)
        elif dataset == "sentinel5p-no2":
            urban_boost = 2.0 if biome == "urban" else 1.0
            value = round((1.2e-5 + noise * 8e-5) * urban_boost, 8)
        elif dataset == "sentinel5p-ch4":
            value = round(1750 + (80 if biome == "tropical_forest" else 20) * noise, 1)
        else:
            prior = _FOREST_PRIOR[biome]
            value = round(min(1.0, max(0.0, prior + (noise - 0.5) * 0.12)), 2)
        confidence = 0.55 if biome in {"desert", "ocean", "urban"} else 0.72
        return SatelliteObservation(
            asset_id=asset.asset_id,
            dataset=dataset,
            observation_date=obs_date,
            value=value,
            unit=_DEFAULT_UNITS[dataset],
            provider_id=self.id,
            source_confidence=confidence,
            biome=biome,
            dataset_version=_DATASET_VERSIONS[dataset],
            methodology_note=(
                f"Offline biome prior ({biome}) scaled by a deterministic hash. "
                "Replace with a GEE / GFW / Sentinel Hub extract for diligence."
            ),
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
    "Biome",
    "DeterministicSatelliteProvider",
    "SatelliteDataset",
    "SatelliteObservation",
    "SatelliteProvider",
    "classify_biome",
    "get_satellite_provider",
    "register_satellite_provider",
]
