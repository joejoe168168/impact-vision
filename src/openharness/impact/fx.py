"""Currency-agnostic financials with FX normalization (Phase 20).

Pluggable :class:`FXRateProvider` Protocol plus two bundled providers:

* :class:`StaticFXRateProvider` — deterministic, offline snapshot table
  (good for tests, demos, disconnected environments).
* :class:`CompositeFXRateProvider` — delegates to a chain of providers
  in order, so production deployments can prefer a live provider and
  fall back to the offline snapshot when rate-limited.

Converting a value is a one-liner::

    fx = get_fx_provider("static")
    converted = convert(1_500_000, from_ccy="MYR", to_ccy="USD", at=date(2026, 4, 1))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Protocol, runtime_checkable


@runtime_checkable
class FXRateProvider(Protocol):
    id: str
    def rate(self, *, from_ccy: str, to_ccy: str, at: date | None = None) -> float | None:  # pragma: no cover
        ...


# Indicative end-2025 snapshot; numbers rounded to 4 d.p. Always USD-pivot.
_USD_SNAPSHOT = {
    "USD": 1.0000,
    "EUR": 0.9200,
    "GBP": 0.7800,
    "JPY": 150.0000,
    "CNY": 7.1500,
    "HKD": 7.8000,
    "INR": 83.5000,
    "MYR": 4.6500,
    "IDR": 15600.0,
    "THB": 35.0000,
    "SGD": 1.3400,
    "AUD": 1.5100,
    "CAD": 1.3600,
    "BRL": 4.9500,
    "MXN": 17.5000,
    "ZAR": 18.2000,
    "KES": 130.0000,
    "NGN": 1550.0000,
    "GHS": 15.0000,
    "RWF": 1350.0000,
    "CHF": 0.8800,
}


@dataclass
class StaticFXRateProvider:
    """Offline snapshot — pivots through USD."""

    id: str = "static"
    snapshot: dict[str, float] = field(default_factory=lambda: dict(_USD_SNAPSHOT))

    def rate(self, *, from_ccy: str, to_ccy: str, at: date | None = None) -> float | None:
        from_rate = self.snapshot.get(from_ccy.upper())
        to_rate = self.snapshot.get(to_ccy.upper())
        if from_rate is None or to_rate is None:
            return None
        # 1 unit of from_ccy = (1/from_rate) USD; × to_rate → to_ccy.
        return round((1.0 / from_rate) * to_rate, 6) if from_rate > 0 else None


@dataclass
class CompositeFXRateProvider:
    """Tries each provider in order; returns the first non-None rate."""

    id: str = "composite"
    providers: list[FXRateProvider] = field(default_factory=list)

    def rate(self, *, from_ccy: str, to_ccy: str, at: date | None = None) -> float | None:
        for p in self.providers:
            r = p.rate(from_ccy=from_ccy, to_ccy=to_ccy, at=at)
            if r is not None:
                return r
        return None


_PROVIDERS: dict[str, FXRateProvider] = {}


def register_fx_provider(p: FXRateProvider) -> None:
    if not getattr(p, "id", None):
        raise ValueError("provider must have id")
    _PROVIDERS[p.id] = p


def get_fx_provider(provider_id: str = "static") -> FXRateProvider:
    return _PROVIDERS[provider_id]


register_fx_provider(StaticFXRateProvider())


def convert(
    amount: float,
    *,
    from_ccy: str,
    to_ccy: str,
    at: date | None = None,
    provider_id: str = "static",
) -> float | None:
    """Convert ``amount`` from ``from_ccy`` to ``to_ccy``. Returns ``None`` if rate unknown."""
    if from_ccy.upper() == to_ccy.upper():
        return round(amount, 2)
    prov = get_fx_provider(provider_id)
    rate = prov.rate(from_ccy=from_ccy, to_ccy=to_ccy, at=at)
    if rate is None:
        return None
    return round(amount * rate, 2)


def normalize_series(
    values: Iterable[tuple[float, str]],
    *,
    to_ccy: str,
    at: date | None = None,
    provider_id: str = "static",
) -> list[float]:
    """Convert a series of ``(amount, from_ccy)`` pairs into ``to_ccy``."""
    out: list[float] = []
    for amt, ccy in values:
        v = convert(amt, from_ccy=ccy, to_ccy=to_ccy, at=at, provider_id=provider_id)
        out.append(v if v is not None else 0.0)
    return out


__all__ = [
    "FXRateProvider",
    "StaticFXRateProvider",
    "CompositeFXRateProvider",
    "register_fx_provider",
    "get_fx_provider",
    "convert",
    "normalize_series",
]
