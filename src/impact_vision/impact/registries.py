"""Carbon / biodiversity credit registry connectors (Phase 15 / 16).

Unified :class:`CreditRegistry` Protocol covering four of the largest
public registries plus a pluggable adapter for private ones:

======================== =========================================
Registry                 Typical credit types
======================== =========================================
Verra / VCS              VCUs (Voluntary Carbon Units), JNR, CCB
Gold Standard            GS-VER, GS-CER, Gender-Safeguards tagged
Puro.earth               CORCs (CO2 Removal Certificates) — biochar,
                         enhanced rock weathering, carbonated
                         concrete
BioCredits / Verra SD    Biodiversity outcome units
======================== =========================================

Every adapter returns a uniform :class:`CreditRecord` shape so the SDK,
LP reporting calendar and the portfolio roll-up can treat credits as a
first-class position type without vendor-specific branches.

The bundled :class:`InMemoryCreditRegistry` is a deterministic, offline
implementation — perfect for unit tests, demos and any deployment that
has not yet wired up a live registry account.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


CreditType = Literal[
    "vcu",            # Verra / VCS
    "corc",           # Puro.earth
    "gs-ver",         # Gold Standard voluntary emission reductions
    "gs-cer",         # Gold Standard certified emission reductions
    "biocredit",      # Biodiversity credits
    "jcc",            # Jurisdictional carbon credit
    "generic",
]


class CreditRecord(BaseModel):
    """One vintage-year bundle of credits owned by a portfolio company."""

    registry: str
    project_id: str
    project_name: str
    credit_type: CreditType = "generic"
    vintage_year: int
    issued_qty: float = Field(ge=0, default=0.0)
    retired_qty: float = Field(ge=0, default=0.0)
    outstanding_qty: float = Field(ge=0, default=0.0)
    unit_price_usd: float | None = None
    standard: str | None = None      # "VCS v4", "GS v4", "Puro Methodology v2", …
    methodology: str | None = None   # "VM0007", "Biochar v1", "JNR v4", …
    country: str | None = None
    sector: str | None = None
    last_transaction: date | None = None


class PortfolioCredits(BaseModel):
    """Aggregated credit holdings across a portfolio."""

    records: list[CreditRecord] = Field(default_factory=list)
    total_outstanding: float = 0.0
    total_retired: float = 0.0
    by_registry: dict[str, float] = Field(default_factory=dict)
    by_credit_type: dict[str, float] = Field(default_factory=dict)
    est_market_value_usd: float = 0.0


@runtime_checkable
class CreditRegistry(Protocol):
    """Provider-pluggable interface to a carbon / biodiversity registry."""

    id: str

    def list_projects(self, *, country: str | None = None, sector: str | None = None) -> list[CreditRecord]:  # pragma: no cover
        ...

    def fetch_project(self, project_id: str) -> CreditRecord | None:  # pragma: no cover
        ...


# ---------------------------------------------------------------------------
# Bundled default implementation — deterministic, offline, no network I/O.
# ---------------------------------------------------------------------------

@dataclass
class InMemoryCreditRegistry:
    """In-memory :class:`CreditRegistry` backed by a pre-seeded record list."""

    id: str = "in-memory"
    records: list[CreditRecord] = field(default_factory=list)

    def list_projects(self, *, country: str | None = None, sector: str | None = None) -> list[CreditRecord]:
        out = list(self.records)
        if country:
            out = [r for r in out if (r.country or "").upper() == country.upper()]
        if sector:
            out = [r for r in out if (r.sector or "").lower() == sector.lower()]
        return out

    def fetch_project(self, project_id: str) -> CreditRecord | None:
        for r in self.records:
            if r.project_id == project_id:
                return r
        return None


_REGISTRY_ALIASES = {
    "verra": "verra",
    "vcs": "verra",
    "gold-standard": "gold-standard",
    "gs": "gold-standard",
    "puro": "puro.earth",
    "puro.earth": "puro.earth",
    "biocredits": "biocredits",
}


_REGISTRIES: dict[str, CreditRegistry] = {}


def register_registry(registry: CreditRegistry) -> None:
    if not getattr(registry, "id", None):
        raise ValueError("Registry must define an `id` attribute.")
    _REGISTRIES[registry.id.lower()] = registry


def get_registry(registry_id: str) -> CreditRegistry:
    key = _REGISTRY_ALIASES.get(registry_id.lower(), registry_id.lower())
    if key not in _REGISTRIES:
        raise KeyError(
            f"Unknown registry '{registry_id}'. Registered: {sorted(_REGISTRIES)}"
        )
    return _REGISTRIES[key]


def rollup_credits(records: Iterable[CreditRecord]) -> PortfolioCredits:
    """Aggregate :class:`CreditRecord`s into a :class:`PortfolioCredits` summary."""
    rec_list = list(records)
    by_registry: dict[str, float] = {}
    by_type: dict[str, float] = {}
    total_outstanding = 0.0
    total_retired = 0.0
    est_value = 0.0
    for r in rec_list:
        total_outstanding += r.outstanding_qty
        total_retired += r.retired_qty
        by_registry[r.registry] = by_registry.get(r.registry, 0.0) + r.outstanding_qty
        by_type[r.credit_type] = by_type.get(r.credit_type, 0.0) + r.outstanding_qty
        if r.unit_price_usd is not None:
            est_value += r.outstanding_qty * r.unit_price_usd
    return PortfolioCredits(
        records=rec_list,
        total_outstanding=total_outstanding,
        total_retired=total_retired,
        by_registry=by_registry,
        by_credit_type=by_type,
        est_market_value_usd=round(est_value, 2),
    )


# ---------------------------------------------------------------------------
# Pre-populated offline sample set — purely for demos / tests / docs.
# These are deliberately *not* real project IDs from live registries.
# ---------------------------------------------------------------------------

DEMO_REGISTRY = InMemoryCreditRegistry(
    id="demo",
    records=[
        CreditRecord(
            registry="Verra", project_id="VCS-DEMO-01", project_name="Kenya Reforestation Alliance",
            credit_type="vcu", vintage_year=2024, issued_qty=45_000.0, retired_qty=12_000.0,
            outstanding_qty=33_000.0, unit_price_usd=8.20,
            standard="VCS v4", methodology="VM0007", country="KE", sector="forestry",
        ),
        CreditRecord(
            registry="Gold Standard", project_id="GS-DEMO-02", project_name="Rwanda Clean Cookstoves",
            credit_type="gs-ver", vintage_year=2024, issued_qty=18_000.0, retired_qty=5_000.0,
            outstanding_qty=13_000.0, unit_price_usd=12.00,
            standard="GS v4", methodology="TPDDTEC v4", country="RW", sector="energy",
        ),
        CreditRecord(
            registry="Puro.earth", project_id="PURO-DEMO-03", project_name="Nordic Biochar Hub",
            credit_type="corc", vintage_year=2025, issued_qty=3_200.0, retired_qty=0.0,
            outstanding_qty=3_200.0, unit_price_usd=220.00,
            standard="Puro v2", methodology="Biochar v1.1", country="FI", sector="removals",
        ),
        CreditRecord(
            registry="BioCredits", project_id="BIO-DEMO-04", project_name="Borneo Peatland Safeguards",
            credit_type="biocredit", vintage_year=2024, issued_qty=1_500.0, retired_qty=0.0,
            outstanding_qty=1_500.0, unit_price_usd=35.00,
            standard="Plan Vivo Biodiversity v1", methodology="PVB-1", country="MY", sector="biodiversity",
        ),
    ],
)


# Register the deterministic default set so ``get_registry("demo")`` works
# out-of-the-box. Users can override with their own adapters.
register_registry(DEMO_REGISTRY)
register_registry(InMemoryCreditRegistry(id="verra", records=[DEMO_REGISTRY.records[0]]))
register_registry(InMemoryCreditRegistry(id="gold-standard", records=[DEMO_REGISTRY.records[1]]))
register_registry(InMemoryCreditRegistry(id="puro.earth", records=[DEMO_REGISTRY.records[2]]))
register_registry(InMemoryCreditRegistry(id="biocredits", records=[DEMO_REGISTRY.records[3]]))


__all__ = [
    "CreditRecord",
    "CreditType",
    "CreditRegistry",
    "InMemoryCreditRegistry",
    "PortfolioCredits",
    "DEMO_REGISTRY",
    "get_registry",
    "register_registry",
    "rollup_credits",
]
