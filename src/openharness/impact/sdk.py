"""Impact Vision Python SDK — single import for end users.

The SDK is a thin façade over the rest of the package; its purpose is to
give downstream code (Streamlit dashboards, GP plug-ins, notebooks, the
FastAPI gateway) one obvious place to import everything and to keep the
underlying module layout free to evolve.

Typical use::

    from openharness.impact.sdk import ImpactVision

    iv = ImpactVision()
    deal = iv.assess_company_text("Example Co", text=long_report_text)
    iv.evaluate_deal_against_thesis(deal, thesis_path="data/fund_thesis.yaml")
    print(iv.render_ic_memo(deal))

Everything the SDK does is also available via the lower-level modules
directly — the SDK simply removes the orchestration boilerplate.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from openharness.impact.catalog import get_default_json_path, load_catalog_json
from openharness.impact.database import MetricStore
from openharness.impact.dd_checklist import (
    analyze_document_coverage,
    load_checklist,
)
from openharness.impact.deal_gate import DealScorecard, evaluate_deal
from openharness.impact.extractors import (
    ExtractedClaim,
    VerificationResult,
    get_extractor,
    get_verifier,
)
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.fund_thesis import FundThesis, load_fund_thesis
from openharness.impact.greenwashing import assess_greenwashing
from openharness.impact.ic_memo import render_ic_memo
from openharness.impact.lp_calendar import LPCalendar, build_calendar
from openharness.impact.models import Assessment, Company
from openharness.impact.plugins import discover_plugins
from openharness.impact.portfolio_rollup import (
    PortfolioRollup,
    rollup_portfolio,
)
from openharness.impact.sdg_mapper import map_sdg_alignment


class ImpactVision:
    """High-level façade that orchestrates the full impact workflow.

    Parameters
    ----------
    extractor_id, verifier_id:
        IDs of registered claim extractor / source verifier providers.
    enable_plugins:
        If True, scans installed Python entry-points for GP-supplied plug-ins.
    catalog_path:
        Optional override for the IRIS+ catalog JSON. Defaults to the bundled
        5.3c snapshot.
    """

    def __init__(
        self,
        *,
        extractor_id: str = "regex",
        verifier_id: str = "heuristic",
        enable_plugins: bool = False,
        catalog_path: str | Path | None = None,
    ) -> None:
        if enable_plugins:
            discover_plugins()
        self._extractor = get_extractor(extractor_id)
        self._verifier = get_verifier(verifier_id)
        path = Path(catalog_path) if catalog_path else get_default_json_path()
        metrics = load_catalog_json(path) if path.exists() else []
        self._store = MetricStore(metrics)

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------

    def assess_company(self, company: Company) -> Assessment:
        """Compute SDG + 5D for an already-populated `Company` object."""
        sdgs = map_sdg_alignment(company, self._store)
        fd = assess_five_dimensions(company, self._store)
        return Assessment(
            company=company,
            assessed_at=date.today().isoformat(),
            sdg_alignments=sdgs,
            five_dimensions=fd,
        )

    def assess_company_text(
        self,
        company_name: str,
        *,
        text: str,
        sector: str | None = None,
        country: str | None = None,
        impact_themes: list[str] | None = None,
    ) -> Assessment:
        """Quick-start: extract claims from `text`, build a Company, assess.

        Useful for one-shot evaluations from a prospectus / impact report.
        Heavier workflows should construct a `Company` manually with
        explicit `reported_metrics` so the 5D engine has hard data.
        """
        claims = self._extractor.extract(text)
        company = Company(
            name=company_name,
            sector=sector or "",
            country=country or "",
            description=text[:1000],
            impact_themes=impact_themes or [],
        )
        # Surface extracted claims on the company for downstream tooling
        for c in claims:
            if c.suggested_iris_metric_id and c.metric_value is not None:
                company.reported_metrics[c.suggested_iris_metric_id] = float(c.metric_value)
        return self.assess_company(company)

    def extract_claims(self, text: str) -> list[ExtractedClaim]:
        return self._extractor.extract(text)

    def verify_claim(
        self, claim: ExtractedClaim, *, source_corpus: str | None = None
    ) -> VerificationResult:
        return self._verifier.verify(claim, context={"source_corpus": source_corpus or ""})

    # ------------------------------------------------------------------
    # Fund workflow
    # ------------------------------------------------------------------

    def load_thesis(self, path: str | Path | None = None) -> FundThesis:
        return load_fund_thesis(str(path) if path else None)

    def evaluate_deal_against_thesis(
        self,
        assessment: Assessment,
        *,
        thesis: FundThesis | None = None,
        thesis_path: str | Path | None = None,
        dd_coverage_pct: float | None = None,
        greenwashing_score: float | None = None,
        exclusion_pass: bool | None = None,
    ) -> DealScorecard:
        thesis = thesis or self.load_thesis(thesis_path)
        return evaluate_deal(
            assessment,
            thesis,
            dd_coverage_pct=dd_coverage_pct,
            greenwashing_score=greenwashing_score,
            exclusion_pass=exclusion_pass,
        )

    def render_ic_memo(
        self,
        assessment: Assessment,
        *,
        thesis: FundThesis | None = None,
        thesis_path: str | Path | None = None,
        scorecard: DealScorecard | None = None,
        output_format: str = "markdown",
        path: str | Path | None = None,
        **kwargs: Any,
    ):
        thesis = thesis or self.load_thesis(thesis_path)
        scorecard = scorecard or self.evaluate_deal_against_thesis(assessment, thesis=thesis)
        return render_ic_memo(
            assessment, scorecard, thesis,
            output_format=output_format, path=path, **kwargs,
        )

    # ------------------------------------------------------------------
    # Portfolio + LP
    # ------------------------------------------------------------------

    def rollup(
        self,
        entries: list[tuple[Assessment, float, float]],
        *,
        thesis: FundThesis | None = None,
        thesis_path: str | Path | None = None,
    ) -> PortfolioRollup:
        """Roll up a portfolio.

        ``entries`` is a list of ``(assessment, capital_eur_m, ownership_pct)``.
        """
        thesis = thesis or self.load_thesis(thesis_path)
        return rollup_portfolio(entries, thesis)

    def build_lp_calendar(
        self,
        *,
        thesis: FundThesis | None = None,
        thesis_path: str | Path | None = None,
        horizon_months: int = 12,
    ) -> LPCalendar:
        thesis = thesis or self.load_thesis(thesis_path)
        return build_calendar(thesis, horizon_months=horizon_months)

    # ------------------------------------------------------------------
    # Due diligence + greenwashing screen
    # ------------------------------------------------------------------

    def run_dd_coverage(self, text: str, *, checklist_path: str | Path | None = None):
        checklist = load_checklist(checklist_path) if checklist_path else load_checklist()
        return analyze_document_coverage(text, checklist)

    def screen_greenwashing(
        self,
        company: Company,
        *,
        claims: list[dict] | None = None,
    ):
        return assess_greenwashing(company, claims=claims)


__all__ = ["ImpactVision"]
