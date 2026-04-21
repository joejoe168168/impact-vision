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

    def render_dd_report_html(
        self,
        text: str,
        *,
        company_name: str = "Company",
        document_label: str = "Source document",
        reviewer: str | None = None,
        path: str | Path | None = None,
        checklist_path: str | Path | None = None,
    ) -> str | Path:
        """Render a self-contained HTML DD coverage report.

        Runs :meth:`run_dd_coverage` then renders the resulting
        :class:`DDChecklistResult` using
        :mod:`openharness.impact.report_templates.dd_report_html`.
        If ``path`` is provided, writes the HTML to disk and returns the
        :class:`Path`; otherwise returns the HTML string.
        """
        from openharness.impact.report_templates import (
            render_dd_report_html,
            save_dd_report_html,
        )
        result = self.run_dd_coverage(text, checklist_path=checklist_path)
        if path:
            return save_dd_report_html(
                result,
                path,
                company_name=company_name,
                document_label=document_label,
                reviewer=reviewer,
            )
        return render_dd_report_html(
            result,
            company_name=company_name,
            document_label=document_label,
            reviewer=reviewer,
        )

    def render_dd_questionnaire_html(
        self,
        text: str,
        *,
        company_name: str = "Company",
        document_label: str = "Source document",
        reviewer: str | None = None,
        path: str | Path | None = None,
        checklist_path: str | Path | None = None,
    ) -> str | Path:
        """Alias for :meth:`render_dd_report_html` — emphasises that the output
        is a DD Questionnaire Helper (risk-first, sequence-ordered)."""
        return self.render_dd_report_html(
            text,
            company_name=company_name,
            document_label=document_label,
            reviewer=reviewer,
            path=path,
            checklist_path=checklist_path,
        )

    def render_dd_questionnaire_docx(
        self,
        text: str,
        path: str | Path,
        *,
        company_name: str = "Company",
        document_label: str = "Source document",
        reviewer: str | None = None,
        checklist_path: str | Path | None = None,
    ) -> Path:
        """Render an editable Word (.docx) version of the DD Questionnaire
        Helper. Requires the optional ``python-docx`` dependency.

        Runs :meth:`run_dd_coverage` on ``text`` and passes the resulting
        :class:`DDChecklistResult` to
        :func:`openharness.impact.report_templates.render_dd_questionnaire_docx`.
        Always writes the file and returns the :class:`Path`.
        """
        from openharness.impact.report_templates import render_dd_questionnaire_docx
        result = self.run_dd_coverage(text, checklist_path=checklist_path)
        return render_dd_questionnaire_docx(
            result,
            path,
            company_name=company_name,
            document_label=document_label,
            reviewer=reviewer,
        )

    def screen_greenwashing(
        self,
        company: Company,
        *,
        claims: list[dict] | None = None,
    ):
        return assess_greenwashing(company, claims=claims)

    # ------------------------------------------------------------------
    # Phase 15–20 additions. These are thin passthroughs that keep the
    # facade "one import" — downstream code can import each underlying
    # module directly if it prefers a narrower surface.
    # ------------------------------------------------------------------

    @staticmethod
    def compute_moi(cashflows, *, unit: str, label: str = ""):
        """Phase 15/16 — Multiple of Impact roll-up."""
        from openharness.impact.returns import compute_moi
        return compute_moi(cashflows, unit=unit, label=label)

    @staticmethod
    def compute_irr(cashflows, *, impact_price_usd_per_unit: float = 0.0, label: str = ""):
        """Phase 15/16 — Financial + impact-adjusted IRR."""
        from openharness.impact.returns import compute_irr
        return compute_irr(
            cashflows,
            impact_price_usd_per_unit=impact_price_usd_per_unit,
            label=label,
        )

    @staticmethod
    def rollup_credits(records):
        """Phase 15 — Portfolio roll-up of carbon / biodiversity credits."""
        from openharness.impact.registries import rollup_credits
        return rollup_credits(records)

    @staticmethod
    def benchmark_peer_context(sector: str, dimension: str, score: float, *, provider_id: str = "offline"):
        """Phase 16 — GIIN Compass-style peer percentile context."""
        from openharness.impact.external_benchmarks import contextualise
        return contextualise(sector, dimension, score, provider_id=provider_id)  # type: ignore[arg-type]

    @staticmethod
    def design_il_loan(**kwargs):
        """Phase 16 — Impact-linked loan term sheet."""
        from openharness.impact.blended_finance import design_il_loan
        return design_il_loan(**kwargs)

    @staticmethod
    def design_soc(**kwargs):
        """Phase 16 — Social Outcomes Contract / DIB term sheet."""
        from openharness.impact.blended_finance import design_soc
        return design_soc(**kwargs)

    @staticmethod
    def lp_portal(fund_name: str):
        """Phase 16 — Read-only ILPA-compatible LP portal facade."""
        from openharness.impact.lp_portal import LPPortal
        return LPPortal(fund_name=fund_name)

    @staticmethod
    def thesis_marketplace():
        """Phase 16 — In-memory marketplace of impact theses."""
        from openharness.impact.marketplace import ThesisMarketplace
        return ThesisMarketplace()

    @staticmethod
    def build_assurance_pack(**kwargs):
        """Phase 17 — ISAE 3000 / AA1000 assurance input pack."""
        from openharness.impact.assurance import build_assurance_pack
        return build_assurance_pack(**kwargs)

    @staticmethod
    def double_materiality(**kwargs):
        """Phase 17 — CSRD / ESRS double-materiality matrix."""
        from openharness.impact.csrd_wizard import assess_double_materiality
        return assess_double_materiality(**kwargs)

    @staticmethod
    def audit_trail(*, tenant_id: str = "default", fund_id: str = "default"):
        """Phase 17 — Hash-chained append-only audit trail for scoring decisions."""
        from openharness.impact.audit_trail import AuditTrail
        return AuditTrail(tenant_id=tenant_id, fund_id=fund_id)

    @staticmethod
    def soc2_readiness(entity: str):
        """Phase 17 — SOC 2 / ISO 27001 readiness checklist."""
        from openharness.impact.soc2_checklist import build_readiness_report
        return build_readiness_report(entity)

    @staticmethod
    def update_counterfactual_with_study(prior: float, study):
        """Phase 18 — Update the counterfactual prior with a causal study."""
        from openharness.impact.causal import update_counterfactual_prior
        return update_counterfactual_prior(prior, study)

    @staticmethod
    def bayesian_prior(*, optimism: float = 0.5, strength: float = 4.0):
        """Phase 18 — Beta-binomial prior over a claim's truth probability."""
        from openharness.impact.bayes import default_prior
        return default_prior(optimism=optimism, strength=strength)

    @staticmethod
    def meta_pool(studies):
        """Phase 18 — Fixed-effect meta-analysis pooled estimate."""
        from openharness.impact.meta_analysis import pool_effects
        return pool_effects(studies)

    @staticmethod
    def adjust_spillover(assumption):
        """Phase 18 — Apply leakage + spillover to an outcome."""
        from openharness.impact.spillover import adjust_node
        return adjust_node(assumption)

    @staticmethod
    def compute_sroi(**kwargs):
        """Phase 18 — SROI ratio + sensitivity."""
        from openharness.impact.sroi import compute_sroi
        return compute_sroi(**kwargs)

    @staticmethod
    def satellite_observation(asset, dataset, obs_date, *, provider_id: str = "deterministic"):
        """Phase 19 — Satellite-derived outcome observation."""
        from openharness.impact.geospatial import get_satellite_provider
        return get_satellite_provider(provider_id).observe(asset, dataset, obs_date)

    @staticmethod
    def load_survey_csv(csv_blob: str, *, form_id: str, platform: str = "surveycto"):
        """Phase 19 — Load a SurveyCTO/Kobo/ODK/60dB CSV export."""
        from openharness.impact.surveys import GenericCSVProvider
        return GenericCSVProvider(platform=platform).load_csv(csv_blob, form_id=form_id)  # type: ignore[arg-type]

    @staticmethod
    def worker_voice(dataset):
        """Phase 19 — Aggregate worker-voice signals into a Who-lift."""
        from openharness.impact.worker_voice import summarise
        return summarise(dataset)

    @staticmethod
    def ecosystem_value(asset, service, *, provider_id: str = "offline-unit-values"):
        """Phase 19 — Offline ecosystem-service valuation (hectare × service)."""
        from openharness.impact.ecosystem_services import get_ecosystem_provider
        return get_ecosystem_provider(provider_id).value(asset, service)

    @staticmethod
    def regulatory_pack(jurisdiction: str):
        """Phase 20 — Per-jurisdiction disclosure regime reference."""
        from openharness.impact.regulatory_packs import get_pack
        return get_pack(jurisdiction)

    @staticmethod
    def convert_currency(amount: float, *, from_ccy: str, to_ccy: str, at=None, provider_id: str = "static"):
        """Phase 20 — FX normalization."""
        from openharness.impact.fx import convert
        return convert(amount, from_ccy=from_ccy, to_ccy=to_ccy, at=at, provider_id=provider_id)

    @staticmethod
    def load_branding(thesis_path: str | None = None):
        """Phase 15.6 — Load fund-specific report branding."""
        from openharness.impact.branding import load_branding
        return load_branding(thesis_path)


__all__ = ["ImpactVision"]
