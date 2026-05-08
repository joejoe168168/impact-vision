"""Fund-manager decision workflows for Impact Vision v5.

This module composes existing engines into opinionated user workflows. It does
not replace the underlying scorers; it makes their evidence, verdicts, and
gate decisions available as one deterministic payload.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.database import MetricStore
from openharness.impact.deal_gate import DealScorecard, evaluate_deal
from openharness.impact.evidence_chain_renderer import EvidenceChainNode, EvidenceChainRenderer
from openharness.impact.evidence_graph import build_evidence_graph, graph_warnings
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.fund_thesis import FundThesis
from openharness.impact.greenwashing import assess_greenwashing
from openharness.impact.ic_memo import render_ic_memo
from openharness.impact.models import Assessment, Company, ImpactClaim, MetricRecord
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.impact.verdict_engine import VerdictCard, build_verdict_card


QuickScreenClassification = Literal["aligned_and_credible", "misaligned_but_improvable", "red_flag"]
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


class QuickScreenResult(BaseModel):
    company_name: str
    classification: QuickScreenClassification
    gate_status: Literal["pass", "warn", "fail"]
    verdict: Literal["pass", "caution", "fail"]
    reasons: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
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
    company_a: str
    company_b: str
    winner: str
    summary: str
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
            out.append(item if isinstance(item, MetricRecord) else MetricRecord.model_validate(item))
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
        for node in (assessment.five_dimensions.what, assessment.five_dimensions.who,
                     assessment.five_dimensions.how_much, assessment.five_dimensions.contribution,
                     assessment.five_dimensions.risk):
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
) -> ICWorkflowSummary:
    assessment = build_assessment(company, store)
    greenwashing = assess_greenwashing(company, [c.model_dump(mode="json") for c in _claim_objects(claims)])
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
    if summary.scorecard.overall_status == "fail" or summary.verdict_card.verdict == "fail":
        classification: QuickScreenClassification = "red_flag"
    elif summary.scorecard.overall_status == "warn" or summary.verdict_card.verdict == "caution":
        classification = "misaligned_but_improvable"
    elif summary.assessment.five_dimensions and summary.assessment.five_dimensions.overall_provenance != "evidence-based":
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
    )


def compare_deals(a: ICWorkflowSummary, b: ICWorkflowSummary) -> DealComparison:
    fd_a = a.assessment.five_dimensions
    fd_b = b.assessment.five_dimensions
    score_a = fd_a.overall_score if fd_a else 0.0
    score_b = fd_b.overall_score if fd_b else 0.0
    risk_a = a.verdict_card.risk_score
    risk_b = b.verdict_card.risk_score
    composite_a = score_a * 20 - risk_a * 0.25
    composite_b = score_b * 20 - risk_b * 0.25
    winner = a.company_name if composite_a >= composite_b else b.company_name

    dimension_deltas: dict[str, float] = {}
    if fd_a and fd_b:
        dimension_deltas = {
            "what": round(fd_a.what.score - fd_b.what.score, 2),
            "who": round(fd_a.who.score - fd_b.who.score, 2),
            "how_much": round(fd_a.how_much.score - fd_b.how_much.score, 2),
            "contribution": round(fd_a.contribution.score - fd_b.contribution.score, 2),
            "risk": round(fd_a.risk.score - fd_b.risk.score, 2),
        }

    top_a = max(a.assessment.sdg_alignments, key=lambda item: item.score, default=None)
    top_b = max(b.assessment.sdg_alignments, key=lambda item: item.score, default=None)
    tradeoffs = [
        f"{a.company_name} 5D overall: {score_a:.1f}/5; greenwashing risk: {risk_a}/100.",
        f"{b.company_name} 5D overall: {score_b:.1f}/5; greenwashing risk: {risk_b}/100.",
    ]
    return DealComparison(
        company_a=a.company_name,
        company_b=b.company_name,
        winner=winner,
        summary=f"{winner} has the stronger risk-adjusted impact profile on current evidence.",
        dimension_deltas=dimension_deltas,
        sdg_top_scores={
            a.company_name: round(top_a.score, 1) if top_a else 0.0,
            b.company_name: round(top_b.score, 1) if top_b else 0.0,
        },
        greenwashing_risk={a.company_name: risk_a, b.company_name: risk_b},
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
        badge_label={"lp_ready": "LP-Ready", "needs_work": "LP Review", "blocked": "Not LP-Ready"}[status],
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
