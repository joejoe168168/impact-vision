"""ILPA-compatible LP portal (Phase 16).

Thin read-only layer on top of the signed / hash-chained feed
(:mod:`openharness.impact.signed_feed`) that produces the three most
common LP views:

1. **Capital Account Statement** (ILPA-aligned shape).
2. **Impact Dashboard** (SDG mix + 5-D radar inputs).
3. **Audit Trail** (every entry of the signed feed with verification
   status rendered as structured JSON).

The portal itself is a plain Python class — bind it to FastAPI, a CLI,
or a static-site generator. Nothing here opens sockets: LPs can be
shipped a ``.json`` bundle via email or SFTP if an online portal isn't
desired.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from openharness.impact.signed_feed import HMACSigner, ReportFeed, Signer


class CapitalAccountLine(BaseModel):
    """ILPA Capital Account Statement line item."""

    as_of: date
    label: str
    amount_usd: float
    ytd: bool = False
    itd: bool = False  # inception-to-date


class CapitalAccountStatement(BaseModel):
    """LP-friendly rollup."""

    fund_name: str
    lp_identifier: str
    statement_date: date
    lines: list[CapitalAccountLine] = Field(default_factory=list)
    committed_capital_usd: float = 0.0
    contributed_capital_usd: float = 0.0
    distributions_usd: float = 0.0
    net_asset_value_usd: float = 0.0


class ImpactDashboardView(BaseModel):
    """Top-level impact numbers for the LP portal landing screen."""

    fund_name: str
    statement_date: date
    companies: int = 0
    portfolio_impact_score: float = 0.0
    coverage_pct: float = 0.0
    top_sdgs: list[str] = Field(default_factory=list)
    five_dimensions: dict[str, float] = Field(default_factory=dict)
    alerts: list[str] = Field(default_factory=list)


class AuditTrailView(BaseModel):
    """Every signed-feed entry rendered for LPs."""

    fund_name: str
    statement_date: date
    entries: list[dict[str, Any]] = Field(default_factory=list)
    head_hash: str = ""
    chain_valid: bool = True


def _default_feed() -> ReportFeed:
    return ReportFeed(tenant_id="default", fund_id="default")


@dataclass
class LPPortal:
    """Read-only facade that assembles the three views for one fund."""

    fund_name: str
    feed: ReportFeed = field(default_factory=_default_feed)
    signer: Signer = field(default_factory=lambda: HMACSigner(key=b"impact-vision-demo"))

    def capital_account_statement(
        self,
        *,
        lp_identifier: str,
        committed_capital_usd: float,
        contributed_capital_usd: float,
        distributions_usd: float,
        net_asset_value_usd: float,
        statement_date: date | None = None,
    ) -> CapitalAccountStatement:
        d = statement_date or date.today()
        lines = [
            CapitalAccountLine(as_of=d, label="Committed capital",
                               amount_usd=committed_capital_usd, itd=True),
            CapitalAccountLine(as_of=d, label="Contributed capital",
                               amount_usd=contributed_capital_usd, itd=True),
            CapitalAccountLine(as_of=d, label="Distributions",
                               amount_usd=distributions_usd, itd=True),
            CapitalAccountLine(as_of=d, label="Net asset value",
                               amount_usd=net_asset_value_usd, itd=True),
        ]
        return CapitalAccountStatement(
            fund_name=self.fund_name,
            lp_identifier=lp_identifier,
            statement_date=d,
            lines=lines,
            committed_capital_usd=committed_capital_usd,
            contributed_capital_usd=contributed_capital_usd,
            distributions_usd=distributions_usd,
            net_asset_value_usd=net_asset_value_usd,
        )

    def impact_dashboard(
        self,
        *,
        companies: int,
        portfolio_impact_score: float,
        coverage_pct: float,
        top_sdgs: list[str],
        five_dimensions: dict[str, float],
        alerts: list[str] | None = None,
        statement_date: date | None = None,
    ) -> ImpactDashboardView:
        return ImpactDashboardView(
            fund_name=self.fund_name,
            statement_date=statement_date or date.today(),
            companies=companies,
            portfolio_impact_score=round(portfolio_impact_score, 2),
            coverage_pct=round(coverage_pct, 2),
            top_sdgs=top_sdgs[:5],
            five_dimensions={k: round(v, 2) for k, v in five_dimensions.items()},
            alerts=list(alerts or []),
        )

    def audit_trail(self, *, statement_date: date | None = None) -> AuditTrailView:
        entries = [e.model_dump(mode="json") for e in self.feed.reports]
        ok, _ = self.feed.verify(self.signer)
        return AuditTrailView(
            fund_name=self.fund_name,
            statement_date=statement_date or date.today(),
            entries=entries,
            head_hash=self.feed.head_hash,
            chain_valid=ok,
        )


__all__ = [
    "CapitalAccountLine",
    "CapitalAccountStatement",
    "ImpactDashboardView",
    "AuditTrailView",
    "LPPortal",
]
