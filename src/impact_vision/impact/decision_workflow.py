"""Fund-manager decision workflows for Impact Vision v5.

This module composes existing engines into opinionated user workflows. It does
not replace the underlying scorers; it makes their evidence, verdicts, and
gate decisions available as one deterministic payload.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from impact_vision.impact.database import MetricStore
from impact_vision.impact.deal_gate import DealScorecard, TargetCondition, evaluate_deal
from impact_vision.impact.evidence_chain_renderer import EvidenceChainNode, EvidenceChainRenderer
from impact_vision.impact.evidence_graph import build_evidence_graph, graph_warnings
from impact_vision.impact.five_dimensions import assess_five_dimensions
from impact_vision.impact.fund_thesis import FundThesis
from impact_vision.impact.greenwashing import assess_greenwashing
from impact_vision.impact.ic_memo import render_ic_memo
from impact_vision.impact.models import Assessment, Company, ImpactClaim, MetricRecord
from impact_vision.impact.sdg_mapper import map_sdg_alignment
from impact_vision.impact.verdict_engine import VerdictCard, build_verdict_card


QuickScreenClassification = Literal[
    "aligned_and_credible", "misaligned_but_improvable", "red_flag", "insufficient_evidence"
]

# Below these thresholds a screen can't distinguish "bad deal" from "thin
# input", so it says so instead of returning a red flag.
_MIN_EVIDENCE_WORDS = 80
_MIN_EVIDENCE_METRICS = 3
_MIN_QUANTIFIED_CLAIMS = 2

LPBadgeStatus = Literal["lp_ready", "needs_work", "blocked"]


class ProofMetric(BaseModel):
    metric_id: str
    value: str
    unit: str = ""
    source: str = ""
    verified: bool = False
    verification_status: str = "unverified"
    evidence_refs: list[str] = Field(default_factory=list)


class ProofClaimGap(BaseModel):
    claim: str
    metric_gap: str
    why_it_matters: str


class ProofAppendix(BaseModel):
    """Evidence appendix for IC memo and LP-readiness outputs."""

    reported_metrics: list[ProofMetric] = Field(default_factory=list)
    estimated_metrics: list[dict[str, Any]] = Field(default_factory=list)
    unmeasured_claims: list[ProofClaimGap] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    evidence_warnings: list[str] = Field(default_factory=list)
    evidence_chains: dict[str, EvidenceChainNode] = Field(default_factory=dict)


class EvidenceSufficiency(BaseModel):
    sufficient: bool
    words: int = 0
    reported_metrics: int = 0
    quantified_claims: int = 0
    reasons: list[str] = Field(default_factory=list)


def assess_evidence_sufficiency(
    company: Company,
    claims: list[ImpactClaim | dict[str, Any]] | None = None,
) -> EvidenceSufficiency:
    """Is there enough input to screen this company at all?

    Insufficient when the description + claims are short *and* there are
    few reported metrics *and* few quantified claims.
    """
    texts = [company.description or ""]
    quantified = 0
    for claim in claims or []:
        text = claim.text if isinstance(claim, ImpactClaim) else str((claim or {}).get("text", ""))
        texts.append(text)
        if any(ch.isdigit() for ch in text):
            quantified += 1
    words = sum(len(t.split()) for t in texts)
    metrics = len(company.reported_metrics)
    sufficient = (
        words >= _MIN_EVIDENCE_WORDS
        or metrics >= _MIN_EVIDENCE_METRICS
        or quantified >= _MIN_QUANTIFIED_CLAIMS
    )
    reasons = [] if sufficient else [
        f"Only {words} words of description/claims, {metrics} reported IRIS+ metrics and "
        f"{quantified} quantified claims — not enough to judge impact either way."
    ]
    return EvidenceSufficiency(
        sufficient=sufficient,
        words=words,
        reported_metrics=metrics,
        quantified_claims=quantified,
        reasons=reasons,
    )


class QuickScreenResult(BaseModel):
    company_name: str
    classification: QuickScreenClassification
    gate_status: Literal["pass", "warn", "fail"]
    verdict: Literal["pass", "caution", "fail"]
    reasons: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    evidence: EvidenceSufficiency | None = None
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ICWorkflowSummary(BaseModel):
    company_name: str
    assessment: Assessment
    scorecard: DealScorecard
    verdict_card: VerdictCard
    proof_appendix: ProofAppendix
    evidence_chains: dict[str, EvidenceChainNode]
    memo: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DealComparison(BaseModel):
    """Two deals side by side (F2). No composite score and no winner: expected impact
    per outcome kind with its P10–P90 range, and whether the ranges can be told apart."""

    company_a: str
    company_b: str
    summary: str
    deals: list[dict[str, Any]] = Field(default_factory=list)
    outcome_kinds: list[str] = Field(default_factory=list)
    notes: list[dict[str, Any]] = Field(default_factory=list)
    dimension_deltas: dict[str, float] = Field(default_factory=dict)
    sdg_top_scores: dict[str, float] = Field(default_factory=dict)
    greenwashing_risk: dict[str, int] = Field(default_factory=dict)
    tradeoffs: list[str] = Field(default_factory=list)


class LPReadinessResult(BaseModel):
    company_name: str
    status: LPBadgeStatus
    evidence_complete_pct: int = Field(ge=0, le=100)
    verdict: Literal["pass", "caution", "fail"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    badge_label: str = ""


def _claim_objects(claims: list[ImpactClaim | dict[str, Any]] | None) -> list[ImpactClaim]:
    out: list[ImpactClaim] = []
    for item in claims or []:
        try:
            out.append(item if isinstance(item, ImpactClaim) else ImpactClaim.model_validate(item))
        except Exception:
            continue
    return out


def _metric_records(records: list[MetricRecord | dict[str, Any]] | None) -> list[MetricRecord]:
    out: list[MetricRecord] = []
    for item in records or []:
        try:
            out.append(
                item if isinstance(item, MetricRecord) else MetricRecord.model_validate(item)
            )
        except Exception:
            continue
    return out


def build_assessment(company: Company, store: MetricStore) -> Assessment:
    """Run the current SDG and 5D engines for a company."""
    return Assessment(
        company=company,
        five_dimensions=assess_five_dimensions(company, store),
        sdg_alignments=map_sdg_alignment(company, store),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def render_evidence_chains(
    assessment: Assessment,
    store: MetricStore,
    *,
    claims: list[ImpactClaim | dict[str, Any]] | None = None,
    metric_records: list[MetricRecord | dict[str, Any]] | None = None,
) -> dict[str, EvidenceChainNode]:
    renderer = EvidenceChainRenderer(store)
    return {
        key: renderer.render_dimension(
            key,
            assessment,
            claims=claims,
            metric_records=metric_records,
        )
        for key in ("what", "who", "how_much", "contribution", "risk")
    }


def build_proof_appendix(
    assessment: Assessment,
    store: MetricStore,
    *,
    claims: list[ImpactClaim | dict[str, Any]] | None = None,
    metric_records: list[MetricRecord | dict[str, Any]] | None = None,
) -> ProofAppendix:
    claim_objects = _claim_objects(claims or assessment.impact_claims)
    record_objects = _metric_records(metric_records)
    record_by_id = {record.metric_id: record for record in record_objects}
    reported: list[ProofMetric] = []
    for metric_id, value in sorted(assessment.company.reported_metrics.items()):
        record = record_by_id.get(metric_id)
        if record:
            reported.append(
                ProofMetric(
                    metric_id=metric_id,
                    value=str(record.value),
                    unit=record.unit,
                    source=record.source,
                    verified=record.is_verified,
                    verification_status=record.verification_status,
                    evidence_refs=record.evidence_refs,
                )
            )
        else:
            reported.append(ProofMetric(metric_id=metric_id, value=str(value)))

    reported_ids = set(assessment.company.reported_metrics)
    unmeasured = [
        ProofClaimGap(
            claim=claim.text,
            metric_gap="No mapped metric is present in reported_metrics.",
            why_it_matters="The claim cannot be treated as measured evidence in IC or LP outputs.",
        )
        for claim in claim_objects
        if not set(claim.mapped_metrics) & reported_ids
    ]

    assumptions: list[str] = []
    if assessment.five_dimensions:
        for node in (
            assessment.five_dimensions.what,
            assessment.five_dimensions.who,
            assessment.five_dimensions.how_much,
            assessment.five_dimensions.contribution,
            assessment.five_dimensions.risk,
        ):
            if node.provenance != "evidence-based":
                assumptions.append(f"{node.dimension}: {node.notes}")

    graph = build_evidence_graph(claims=claim_objects, metric_records=record_objects)
    chains = render_evidence_chains(
        assessment,
        store,
        claims=claim_objects,
        metric_records=record_objects,
    )
    return ProofAppendix(
        reported_metrics=reported,
        unmeasured_claims=unmeasured,
        assumptions=assumptions,
        evidence_warnings=graph_warnings(graph),
        evidence_chains=chains,
    )


def build_ic_workflow_summary(
    company: Company,
    store: MetricStore,
    thesis: FundThesis,
    *,
    claims: list[ImpactClaim | dict[str, Any]] | None = None,
    metric_records: list[MetricRecord | dict[str, Any]] | None = None,
    dd_coverage_pct: float | None = None,
    exclusion_pass: bool | None = None,
    memo_format: Literal["markdown", "html"] = "markdown",
    target_conditions: list[TargetCondition] | None = None,
) -> ICWorkflowSummary:
    assessment = build_assessment(company, store)
    greenwashing = assess_greenwashing(
        company, [c.model_dump(mode="json") for c in _claim_objects(claims)]
    )
    verdict = build_verdict_card(company, greenwashing)
    scorecard = evaluate_deal(
        assessment,
        thesis,
        dd_coverage_pct=dd_coverage_pct,
        greenwashing_score=greenwashing.overall_score,
        exclusion_pass=exclusion_pass,
    )
    proof = build_proof_appendix(
        assessment,
        store,
        claims=claims,
        metric_records=metric_records,
    )
    memo = render_ic_memo(
        assessment,
        scorecard,
        thesis,
        output_format=memo_format,
        greenwashing_score=greenwashing.overall_score,
        greenwashing_classification=greenwashing.classification,
        dd_coverage_pct=dd_coverage_pct,
        verdict_card=verdict,
        proof_appendix=proof,
        target_conditions=target_conditions,
    )
    return ICWorkflowSummary(
        company_name=company.name,
        assessment=assessment,
        scorecard=scorecard,
        verdict_card=verdict,
        proof_appendix=proof,
        evidence_chains=proof.evidence_chains,
        memo=str(memo),
    )


def quick_screen(
    company: Company,
    store: MetricStore,
    thesis: FundThesis,
    *,
    claims: list[ImpactClaim | dict[str, Any]] | None = None,
    dd_coverage_pct: float | None = None,
    exclusion_pass: bool | None = None,
) -> QuickScreenResult:
    summary = build_ic_workflow_summary(
        company,
        store,
        thesis,
        claims=claims,
        dd_coverage_pct=dd_coverage_pct,
        exclusion_pass=exclusion_pass,
    )
    evidence = assess_evidence_sufficiency(company, claims)
    failed = [c for c in summary.scorecard.checks if c.status == "fail"]
    if evidence.sufficient and summary.scorecard.evidence_status == "insufficient":
        # Every failure is a data gap (see deal_gate.GateCheck.data_gap):
        # missing data, not a negative finding.
        evidence = evidence.model_copy(update={
            "sufficient": False,
            "reasons": [
                "The failed checks reflect missing evidence rather than negative findings: "
                + "; ".join(f"{c.name} {c.actual} vs {c.threshold}" for c in failed)
                + "."
            ],
        })
    if exclusion_pass is not False and not evidence.sufficient:
        # Thin input is not a red flag; ask for the material instead.
        return QuickScreenResult(
            company_name=company.name,
            classification="insufficient_evidence",
            gate_status=summary.scorecard.overall_status,
            verdict=summary.verdict_card.verdict,
            reasons=evidence.reasons,
            required_followups=[
                "Share the pitch deck, investment memo or latest impact report.",
                "Report at least 3 IRIS+ metrics (e.g. clients reached, jobs, GHG avoided).",
                "Describe the outcome for beneficiaries with numbers and a baseline.",
            ],
            evidence=evidence,
        )
    if summary.scorecard.overall_status == "fail" or summary.verdict_card.verdict == "fail":
        classification: QuickScreenClassification = "red_flag"
    elif summary.scorecard.overall_status == "warn" or summary.verdict_card.verdict == "caution":
        classification = "misaligned_but_improvable"
    elif (
        summary.assessment.five_dimensions
        and summary.assessment.five_dimensions.overall_provenance != "evidence-based"
    ):
        classification = "misaligned_but_improvable"
    else:
        classification = "aligned_and_credible"

    reasons = summary.scorecard.blocking_failures + summary.scorecard.warnings_list
    reasons.extend(summary.verdict_card.top_3_findings)
    return QuickScreenResult(
        company_name=company.name,
        classification=classification,
        gate_status=summary.scorecard.overall_status,
        verdict=summary.verdict_card.verdict,
        reasons=reasons[:5],
        required_followups=summary.verdict_card.next_steps[:5],
        evidence=evidence,
    )


def compare_deals(a: ICWorkflowSummary, b: ICWorkflowSummary) -> DealComparison:
    """Delegate to :mod:`impact_vision.impact.compare` (F2): no composite, no winner."""
    from impact_vision.impact.compare import compare_bundles, deal_from_ic_summary

    comparison = compare_bundles([deal_from_ic_summary(a), deal_from_ic_summary(b)])
    fd_a = a.assessment.five_dimensions
    fd_b = b.assessment.five_dimensions
    dimension_deltas: dict[str, float] = {}
    if fd_a and fd_b:  # descriptive: A minus B per dimension, not a ranking
        dimension_deltas = {
            "what": round(fd_a.what.score - fd_b.what.score, 2),
            "who": round(fd_a.who.score - fd_b.who.score, 2),
            "how_much": round(fd_a.how_much.score - fd_b.how_much.score, 2),
            "contribution": round(fd_a.contribution.score - fd_b.contribution.score, 2),
            "risk": round(fd_a.risk.score - fd_b.risk.score, 2),
        }
    top_a = max(a.assessment.sdg_alignments, key=lambda item: item.score, default=None)
    top_b = max(b.assessment.sdg_alignments, key=lambda item: item.score, default=None)
    tradeoffs = []
    for deal in comparison["deals"]:
        eq = deal["evidence_quality"]
        heads = "; ".join(f"{kind} P50 {o['p50']:,.0f} {o['unit']} (P10 {o['p10']:,.0f} – P90 {o['p90']:,.0f})"
                          for kind, o in deal["outcomes"].items()) or "no quantified outcome"
        tradeoffs.append(f"{deal['company']}: {deal['gate']}; evidence quality {eq['score']}/100; {heads}.")
    tradeoffs += [n["text"] for n in comparison["notes"]]
    return DealComparison(
        company_a=a.company_name,
        company_b=b.company_name,
        summary=("Side by side, with no composite score and no winner: expected impact per outcome kind, "
                 "and where the P10–P90 ranges overlap the deals cannot be told apart."),
        deals=comparison["deals"],
        outcome_kinds=comparison["outcome_kinds"],
        notes=comparison["notes"],
        dimension_deltas=dimension_deltas,
        sdg_top_scores={
            a.company_name: round(top_a.score, 1) if top_a else 0.0,
            b.company_name: round(top_b.score, 1) if top_b else 0.0,
        },
        greenwashing_risk={a.company_name: a.verdict_card.risk_score, b.company_name: b.verdict_card.risk_score},
        tradeoffs=tradeoffs,
    )


def assess_lp_readiness(summary: ICWorkflowSummary) -> LPReadinessResult:
    chains = summary.evidence_chains.values()
    evidence_based = sum(1 for chain in chains if chain.provenance == "evidence-based")
    evidence_complete_pct = int(round(evidence_based / 5 * 100)) if summary.evidence_chains else 0
    blockers: list[str] = []
    warnings: list[str] = []
    if summary.verdict_card.verdict == "fail":
        blockers.append("Greenwashing verdict is FAIL.")
    elif summary.verdict_card.verdict == "caution":
        warnings.append("Greenwashing verdict is CAUTION.")
    if evidence_complete_pct < 60:
        blockers.append("Less than 60% of 5D dimensions are evidence-based.")
    elif evidence_complete_pct < 100:
        warnings.append("Some 5D dimensions are still estimated or partially evidenced.")
    if summary.proof_appendix.unmeasured_claims:
        warnings.append("Some claims are not linked to reported metrics.")

    if blockers:
        status: LPBadgeStatus = "blocked"
    elif warnings:
        status = "needs_work"
    else:
        status = "lp_ready"
    return LPReadinessResult(
        company_name=summary.company_name,
        status=status,
        evidence_complete_pct=evidence_complete_pct,
        verdict=summary.verdict_card.verdict,
        blockers=blockers,
        warnings=warnings,
        badge_label={"lp_ready": "LP-Ready", "needs_work": "LP Review", "blocked": "Not LP-Ready"}[
            status
        ],
    )


__all__ = [
    "DealComparison",
    "ICWorkflowSummary",
    "LPReadinessResult",
    "ProofAppendix",
    "ProofClaimGap",
    "ProofMetric",
    "QuickScreenResult",
    "assess_lp_readiness",
    "build_assessment",
    "build_ic_workflow_summary",
    "build_proof_appendix",
    "compare_deals",
    "quick_screen",
    "render_evidence_chains",
]
