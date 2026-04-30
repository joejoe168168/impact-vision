"""Roadmap v2 institutional-readiness helpers.

This module fills the non-UI product surfaces from ``docs/roadmap-v2.md`` with
small, portable APIs. The helpers are intentionally deterministic and storage
agnostic so they can be bound to CLI commands, FastAPI routes, or scheduled
jobs without forcing a database migration in the first implementation pass.
"""

from __future__ import annotations

import csv
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from io import StringIO
from statistics import mean
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.evidence_graph import EvidenceGraph
from openharness.impact.frameworks.cross_reference import (
    CrossReference,
    get_all_cross_references,
)
from openharness.impact.frameworks.edci import (
    EDCICompletenessReport,
    portfolio_edci_completeness,
)
from openharness.impact.investee_collection import (
    CollectionSubmission,
    InvesteeQuestionnaireSchema,
    validate_collection_submission,
)
from openharness.impact.models import MetricRecord


CollectionStatus = Literal["missing", "stale", "submitted", "reviewed", "approved"]
DisclosureStatus = Literal["direct", "proxy", "missing", "not_applicable"]
PublicationState = Literal["draft", "reviewer_approved", "published", "superseded"]
ReviewDecision = Literal["pending", "approved", "rejected", "edit_required", "evidence_required"]


class PublicCollectionLink(BaseModel):
    """No-auth collection link with a bearer token and expiry."""

    link_id: str
    submission_id: str
    token_hash: str
    expires_at: str
    created_at: str = Field(default_factory=lambda: _now())
    used_at: str = ""

    def is_active(self, token: str, *, at: datetime | None = None) -> bool:
        """Return whether ``token`` is valid and not expired."""
        check_time = at or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at)
        return (
            not self.used_at
            and check_time <= expiry
            and self.token_hash == hash_token(token)
        )


class CollectionLinkIssue(BaseModel):
    """Issued collection link plus the plaintext token returned once."""

    link: PublicCollectionLink
    token: str
    url_path: str


def hash_token(token: str) -> str:
    """Hash a collection token for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_collection_link(
    *,
    submission_id: str,
    expires_in_hours: int = 168,
    token: str | None = None,
) -> CollectionLinkIssue:
    """Issue a secure public collection link token."""
    raw = token or secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    link = PublicCollectionLink(
        link_id=f"link_{secrets.token_hex(8)}",
        submission_id=submission_id,
        token_hash=hash_token(raw),
        expires_at=expires.isoformat(),
    )
    return CollectionLinkIssue(link=link, token=raw, url_path=f"/collect/{link.link_id}?token={raw}")


class CollectionTrackerRow(BaseModel):
    """One company-period collection status."""

    company_name: str
    reporting_period: str
    status: CollectionStatus
    missing_metrics: list[str] = Field(default_factory=list)
    stale_metrics: list[str] = Field(default_factory=list)
    submitted_at: str = ""
    reviewed_at: str = ""


def build_collection_tracker(
    *,
    schemas_by_company: dict[str, InvesteeQuestionnaireSchema],
    submissions: list[CollectionSubmission],
    current_period: str,
    stale_periods: set[str] | None = None,
) -> list[CollectionTrackerRow]:
    """Build a multi-company collection tracker for the current period."""
    stale_periods = stale_periods or set()
    latest_by_company = {sub.company_name: sub for sub in submissions}
    rows: list[CollectionTrackerRow] = []
    for company_name, schema in schemas_by_company.items():
        expected = {
            field.metric_id
            for section in schema.sections
            for field in section.fields
            if field.required
        }
        sub = latest_by_company.get(company_name)
        if sub is None:
            rows.append(CollectionTrackerRow(
                company_name=company_name,
                reporting_period=current_period,
                status="missing",
                missing_metrics=sorted(expected),
            ))
            continue
        seen = {resp.metric_id.strip().upper() for resp in sub.responses}
        missing = sorted(expected - seen)
        stale = sorted(seen) if sub.reporting_period in stale_periods else []
        if sub.status == "approved":
            status: CollectionStatus = "approved"
        elif sub.status in {"flagged", "rejected", "resubmission_requested"}:
            status = "reviewed"
        elif stale:
            status = "stale"
        else:
            status = "submitted"
        rows.append(CollectionTrackerRow(
            company_name=company_name,
            reporting_period=sub.reporting_period,
            status=status,
            missing_metrics=missing,
            stale_metrics=stale,
            submitted_at=sub.submitted_at,
            reviewed_at=sub.review_history[-1].timestamp if sub.review_history else "",
        ))
    return rows


class ReviewQueueItem(BaseModel):
    """Analyst review queue item with anomaly flags."""

    submission_id: str
    company_name: str
    status: str
    flags: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)


def build_review_queue(
    submissions: list[CollectionSubmission],
    schema_by_submission: dict[str, InvesteeQuestionnaireSchema],
    *,
    previous_values: dict[tuple[str, str], float] | None = None,
    anomaly_threshold_pct: float = 50.0,
) -> list[ReviewQueueItem]:
    """Create a review queue with missing-data and period-over-period anomaly flags."""
    previous_values = previous_values or {}
    queue: list[ReviewQueueItem] = []
    for sub in submissions:
        schema = schema_by_submission[sub.submission_id]
        validation = validate_collection_submission(sub, schema)
        flags: list[str] = []
        comments: list[str] = []
        for field_name in (
            "missing_required",
            "unknown_metrics",
            "evidence_missing",
            "unit_mismatches",
            "duplicate_metrics",
        ):
            values = getattr(validation, field_name)
            if values:
                flags.append(field_name)
                comments.append(f"{field_name}: {', '.join(values)}")
        for response in sub.responses:
            key = (sub.company_name, response.metric_id.strip().upper())
            prev = previous_values.get(key)
            current = _to_float(response.value)
            if prev and current is not None:
                change = abs(current - prev) / abs(prev) * 100
                if change > anomaly_threshold_pct:
                    flags.append("period_anomaly")
                    comments.append(f"{response.metric_id}: {change:.1f}% change from prior period")
        if flags or sub.status != "approved":
            queue.append(ReviewQueueItem(
                submission_id=sub.submission_id,
                company_name=sub.company_name,
                status=sub.status,
                flags=sorted(set(flags)),
                comments=comments,
            ))
    return queue


class ImportPreviewRow(BaseModel):
    """Validation preview for one imported row."""

    row_number: int
    record: MetricRecord | None = None
    errors: list[str] = Field(default_factory=list)
    duplicate: bool = False


class ImportPreview(BaseModel):
    """CSV/XLSX-style import preview."""

    rows: list[ImportPreviewRow]
    valid_count: int = 0
    error_count: int = 0
    duplicate_count: int = 0


def preview_csv_metric_import(csv_text: str, column_mapping: dict[str, str]) -> ImportPreview:
    """Preview a CSV import using a source-column to MetricRecord-field map."""
    reader = csv.DictReader(StringIO(csv_text))
    seen: set[tuple[str, str, str]] = set()
    rows: list[ImportPreviewRow] = []
    for idx, raw in enumerate(reader, start=2):
        payload = {target: raw.get(source, "") for source, target in column_mapping.items()}
        try:
            record = MetricRecord.model_validate(payload)
            key = (record.metric_id, record.period, record.owner)
            duplicate = key in seen
            seen.add(key)
            rows.append(ImportPreviewRow(row_number=idx, record=record, duplicate=duplicate))
        except Exception as exc:  # noqa: BLE001 - preview should collect all row errors
            rows.append(ImportPreviewRow(row_number=idx, errors=[str(exc)]))
    return ImportPreview(
        rows=rows,
        valid_count=sum(1 for row in rows if row.record is not None and not row.duplicate),
        error_count=sum(1 for row in rows if row.errors),
        duplicate_count=sum(1 for row in rows if row.duplicate),
    )


class EmissionFactorCatalog(BaseModel):
    """Versioned emission-factor catalog metadata."""

    catalog_id: str
    source: str
    version: str
    updated_at: str = Field(default_factory=lambda: _now())
    provenance: str = ""
    factor_count: int = 0


class Scope3ProxyEstimate(BaseModel):
    """Proxy Scope 3 estimate when direct data is unavailable."""

    company_name: str
    sector: str
    basis: Literal["spend", "revenue", "activity"]
    amount: float
    factor_tco2e_per_unit: float
    tco2e: float
    method_version: str
    data_quality_score: int = Field(ge=1, le=5)


def estimate_scope3_proxy(
    *,
    company_name: str,
    sector: str,
    basis: Literal["spend", "revenue", "activity"],
    amount: float,
    factor_tco2e_per_unit: float,
    method_version: str = "scope3-proxy-2026",
) -> Scope3ProxyEstimate:
    """Estimate Scope 3 from spend/revenue/activity when direct data is missing."""
    return Scope3ProxyEstimate(
        company_name=company_name,
        sector=sector,
        basis=basis,
        amount=amount,
        factor_tco2e_per_unit=factor_tco2e_per_unit,
        tco2e=round(amount * factor_tco2e_per_unit, 4),
        method_version=method_version,
        data_quality_score=5 if basis in {"spend", "revenue"} else 4,
    )


class PCAFPosition(BaseModel):
    """Inputs for financed-emissions attribution."""

    company_name: str
    investment_value_usd: float = Field(ge=0)
    enterprise_value_usd: float = Field(gt=0)
    company_emissions_tco2e: float = Field(ge=0)
    data_quality_score: int = Field(ge=1, le=5)
    method_version: str = "pcaf-2022"


class PCAFResult(BaseModel):
    """Financed-emissions output for one position."""

    company_name: str
    attribution_factor: float
    financed_emissions_tco2e: float
    data_quality_score: int
    method_version: str


def calculate_pcaf_financed_emissions(position: PCAFPosition) -> PCAFResult:
    """Calculate financed emissions using investment value / enterprise value."""
    attribution = position.investment_value_usd / position.enterprise_value_usd
    return PCAFResult(
        company_name=position.company_name,
        attribution_factor=round(attribution, 6),
        financed_emissions_tco2e=round(attribution * position.company_emissions_tco2e, 4),
        data_quality_score=position.data_quality_score,
        method_version=position.method_version,
    )


class CarbonIntensity(BaseModel):
    """Common carbon intensity metrics."""

    company_name: str
    tco2e_per_revenue: float | None = None
    tco2e_per_employee: float | None = None
    tco2e_per_unit: float | None = None
    ownership_adjusted_footprint: float | None = None


def calculate_carbon_intensity(
    *,
    company_name: str,
    total_tco2e: float,
    revenue: float | None = None,
    employees: int | None = None,
    units: float | None = None,
    ownership_pct: float | None = None,
) -> CarbonIntensity:
    """Calculate carbon intensity metrics from a total footprint."""
    return CarbonIntensity(
        company_name=company_name,
        tco2e_per_revenue=_safe_div(total_tco2e, revenue),
        tco2e_per_employee=_safe_div(total_tco2e, employees),
        tco2e_per_unit=_safe_div(total_tco2e, units),
        ownership_adjusted_footprint=round(total_tco2e * ownership_pct / 100, 4)
        if ownership_pct is not None else None,
    )


class ClimateCoverageRow(BaseModel):
    """Actual vs estimated climate coverage by company."""

    company_name: str
    scope1_status: DisclosureStatus
    scope2_status: DisclosureStatus
    scope3_status: DisclosureStatus
    actual_scopes: int
    estimated_scopes: int
    missing_scopes: int


def build_climate_coverage_dashboard(
    rows: list[tuple[str, DisclosureStatus, DisclosureStatus, DisclosureStatus]],
) -> list[ClimateCoverageRow]:
    """Build actual/proxy/missing coverage rows for Scope 1/2/3."""
    out: list[ClimateCoverageRow] = []
    for company_name, s1, s2, s3 in rows:
        statuses = [s1, s2, s3]
        out.append(ClimateCoverageRow(
            company_name=company_name,
            scope1_status=s1,
            scope2_status=s2,
            scope3_status=s3,
            actual_scopes=sum(1 for item in statuses if item == "direct"),
            estimated_scopes=sum(1 for item in statuses if item == "proxy"),
            missing_scopes=sum(1 for item in statuses if item == "missing"),
        ))
    return out


class SourceLinkedAnswer(BaseModel):
    """Disclosure answer linked to evidence and metric dependencies."""

    code: str
    prompt: str
    answer: str = ""
    source_node_ids: list[str] = Field(default_factory=list)
    metric_ids: list[str] = Field(default_factory=list)
    status: DisclosureStatus = "missing"


class DisclosurePack(BaseModel):
    """Generic source-linked disclosure pack."""

    framework: str
    version: str
    jurisdiction: str = ""
    answers: list[SourceLinkedAnswer] = Field(default_factory=list)


def build_issb_disclosure_pack(
    *,
    entity: str,
    reporting_period: str,
    answers: list[SourceLinkedAnswer],
    evidence_graph: EvidenceGraph | None = None,
) -> DisclosurePack:
    """Build a source-linked ISSB S1/S2 disclosure pack."""
    known_nodes = evidence_graph.node_ids() if evidence_graph else set()
    normalized: list[SourceLinkedAnswer] = []
    for answer in answers:
        sources = [node for node in answer.source_node_ids if not known_nodes or node in known_nodes]
        normalized.append(answer.model_copy(update={"source_node_ids": sources}))
    return DisclosurePack(
        framework="ISSB S1/S2",
        version="S1-S2-2023",
        jurisdiction="global",
        answers=normalized,
    )


def build_esrs_disclosure_pack(
    *,
    amended_version: str,
    double_materiality_links: dict[str, list[str]],
) -> DisclosurePack:
    """Build an ESRS/CSRD pack keyed by amended-ESRS version."""
    answers = [
        SourceLinkedAnswer(
            code=code,
            prompt=f"Double-materiality evidence for {code}",
            answer="Evidence linked",
            source_node_ids=sources,
            status="direct" if sources else "missing",
        )
        for code, sources in sorted(double_materiality_links.items())
    ]
    return DisclosurePack(framework="ESRS/CSRD", version=amended_version, jurisdiction="EU", answers=answers)


def autofill_sfdr_pai(
    *,
    required_codes: list[str],
    direct_values: dict[str, str] | None = None,
    proxy_values: dict[str, str] | None = None,
    not_applicable: set[str] | None = None,
) -> list[SourceLinkedAnswer]:
    """Classify SFDR PAI fields as direct, proxy, missing, or not applicable."""
    direct_values = {k.upper(): v for k, v in (direct_values or {}).items()}
    proxy_values = {k.upper(): v for k, v in (proxy_values or {}).items()}
    not_applicable = {item.upper() for item in (not_applicable or set())}
    answers: list[SourceLinkedAnswer] = []
    for code in required_codes:
        key = code.upper()
        if key in not_applicable:
            status: DisclosureStatus = "not_applicable"
            value = "Not applicable"
        elif key in direct_values:
            status = "direct"
            value = direct_values[key]
        elif key in proxy_values:
            status = "proxy"
            value = proxy_values[key]
        else:
            status = "missing"
            value = ""
        answers.append(SourceLinkedAnswer(code=key, prompt=f"SFDR PAI {key}", answer=value, status=status))
    return answers


class JurisdictionProfile(BaseModel):
    """Jurisdiction-aware disclosure profile."""

    jurisdiction: str
    frameworks: list[str]
    climate_required: bool = True
    notes: str = ""


JURISDICTION_PROFILES: dict[str, JurisdictionProfile] = {
    "EU": JurisdictionProfile(jurisdiction="EU", frameworks=["ESRS", "SFDR", "ISSB"], notes="CSRD/SFDR with ESRS versioning"),
    "UK": JurisdictionProfile(jurisdiction="UK", frameworks=["ISSB", "FCA SDR"], notes="UK SDR and ISSB-aligned climate reporting"),
    "Singapore": JurisdictionProfile(jurisdiction="Singapore", frameworks=["ISSB"], notes="ISSB climate disclosure baseline"),
    "Japan": JurisdictionProfile(jurisdiction="Japan", frameworks=["ISSB"], notes="SSBJ/ISSB-aligned profile"),
    "Australia": JurisdictionProfile(jurisdiction="Australia", frameworks=["AASB S2", "ISSB"], notes="AASB S2 climate profile"),
    "Canada": JurisdictionProfile(jurisdiction="Canada", frameworks=["ISSB"], notes="CSSB/ISSB-aligned profile"),
    "US": JurisdictionProfile(jurisdiction="US", frameworks=["SEC climate", "state climate"], notes="SEC and state climate profile"),
}


def select_jurisdiction_profile(jurisdiction: str) -> JurisdictionProfile:
    """Return a disclosure profile for a roadmap jurisdiction."""
    key = jurisdiction.strip()
    if key not in JURISDICTION_PROFILES:
        raise KeyError(f"Unknown jurisdiction profile: {jurisdiction}")
    return JURISDICTION_PROFILES[key]


def explore_framework_crosswalk(query: str) -> list[CrossReference]:
    """Search the governed framework crosswalk by concept or code."""
    needle = query.strip().lower()
    out: list[CrossReference] = []
    for xref in get_all_cross_references():
        haystack = " ".join([
            xref.concept,
            *xref.iris_plus,
            *xref.gri,
            *xref.edci,
            *(str(num) for num in xref.sfdr_pai),
            *xref.pcaf,
            *xref.issb,
            *xref.esrs,
        ]).lower()
        if needle in haystack:
            out.append(xref)
    return out


class RulePackTestResult(BaseModel):
    """Compatibility test result for a disclosure rule pack."""

    pack_name: str
    version: str
    passed: bool
    failures: list[str] = Field(default_factory=list)


def run_rule_pack_tests(pack_name: str, version: str, required_fields: list[str], payload: dict[str, Any]) -> RulePackTestResult:
    """Check that a rule pack can still resolve its required fields."""
    failures = [field for field in required_fields if field not in payload]
    return RulePackTestResult(pack_name=pack_name, version=version, passed=not failures, failures=failures)


class LPExportBundle(BaseModel):
    """LP export bundle manifest."""

    bundle_id: str
    formats: list[Literal["pdf", "html", "xlsx", "json"]]
    source_index: list[str] = Field(default_factory=list)
    evidence_manifest: dict[str, str] = Field(default_factory=dict)
    edci_report: EDCICompletenessReport | None = None


def build_lp_export_bundle(
    *,
    formats: list[Literal["pdf", "html", "xlsx", "json"]],
    source_refs: list[str],
    portfolio_payloads: list[dict[str, Any]] | None = None,
) -> LPExportBundle:
    """Build an LP bundle with source index, evidence hashes, and optional EDCI attachment."""
    manifest = {ref: hashlib.sha256(ref.encode("utf-8")).hexdigest() for ref in source_refs}
    return LPExportBundle(
        bundle_id=f"lp_{hashlib.sha1(json.dumps(source_refs, sort_keys=True).encode()).hexdigest()[:10]}",
        formats=formats,
        source_index=source_refs,
        evidence_manifest=manifest,
        edci_report=portfolio_edci_completeness(portfolio_payloads) if portfolio_payloads else None,
    )


class ReportPublication(BaseModel):
    """Report publication workflow state."""

    report_id: str
    state: PublicationState = "draft"
    reviewer: str = ""
    published_at: str = ""
    supersedes: str = ""


def transition_report_publication(
    report: ReportPublication,
    next_state: PublicationState,
    *,
    actor: str,
) -> ReportPublication:
    """Move a report through draft, approval, publication, and supersession."""
    allowed = {
        "draft": {"reviewer_approved"},
        "reviewer_approved": {"published"},
        "published": {"superseded"},
        "superseded": set(),
    }
    if next_state not in allowed[report.state]:
        raise ValueError(f"Invalid report transition {report.state} -> {next_state}")
    updates: dict[str, Any] = {"state": next_state}
    if next_state == "reviewer_approved":
        updates["reviewer"] = actor
    if next_state == "published":
        updates["published_at"] = _now()
    return report.model_copy(update=updates)


class FundBrandingProfile(BaseModel):
    """White-label LP/reporting branding metadata."""

    fund_name: str
    logo_url: str = ""
    primary_color: str = "#0d47a1"
    disclaimer: str = ""
    contact_email: str = ""


class ControlCheckResult(BaseModel):
    """Internal control check result."""

    control_id: str
    passed: bool
    severity: Literal["low", "medium", "high"] = "medium"
    message: str = ""


def run_control_checks(
    *,
    metric_records: list[MetricRecord],
    ai_outputs_pending_review: int = 0,
    late_edit_count: int = 0,
    unsupported_claim_count: int = 0,
) -> list[ControlCheckResult]:
    """Check segregation, late edits, unreviewed AI, and unsupported claims."""
    owners = {record.owner for record in metric_records}
    approvers = {record.owner for record in metric_records if record.is_verified}
    return [
        ControlCheckResult(
            control_id="segregation_of_duties",
            passed=not owners or owners != approvers,
            severity="high",
            message="Metric owner set should not equal approver set.",
        ),
        ControlCheckResult(
            control_id="late_edits",
            passed=late_edit_count == 0,
            severity="medium",
            message=f"{late_edit_count} late edit(s) after review cutoff.",
        ),
        ControlCheckResult(
            control_id="unreviewed_ai_outputs",
            passed=ai_outputs_pending_review == 0,
            severity="high",
            message=f"{ai_outputs_pending_review} AI output(s) pending review.",
        ),
        ControlCheckResult(
            control_id="unsupported_claims",
            passed=unsupported_claim_count == 0,
            severity="high",
            message=f"{unsupported_claim_count} unsupported claim(s).",
        ),
    ]


class AIExtractionReview(BaseModel):
    """Review gate for an AI-extracted claim or value."""

    item_id: str
    extracted_text: str
    confidence: float = Field(ge=0, le=1)
    rationale: str = ""
    source_refs: list[str] = Field(default_factory=list)
    decision: ReviewDecision = "pending"
    reviewer: str = ""


def decide_ai_extraction(review: AIExtractionReview, decision: ReviewDecision, reviewer: str) -> AIExtractionReview:
    """Approve, reject, edit-require, or request evidence for AI extraction."""
    if decision == "approved" and review.confidence < 0.5:
        raise ValueError("Low-confidence AI output cannot be approved without editing or more evidence")
    return review.model_copy(update={"decision": decision, "reviewer": reviewer})


class ImmutableReportManifest(BaseModel):
    """Immutable manifest containing hashes for report artifacts."""

    report_id: str
    artifact_hashes: dict[str, str]
    manifest_hash: str


def build_immutable_report_manifest(report_id: str, artifacts: dict[str, str]) -> ImmutableReportManifest:
    """Hash source documents, exports, and final reports into one manifest."""
    artifact_hashes = {
        name: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for name, content in sorted(artifacts.items())
    }
    manifest_hash = hashlib.sha256(json.dumps(artifact_hashes, sort_keys=True).encode("utf-8")).hexdigest()
    return ImmutableReportManifest(report_id=report_id, artifact_hashes=artifact_hashes, manifest_hash=manifest_hash)


class ExceptionRegisterEntry(BaseModel):
    """Known gap, override, or unresolved limitation."""

    exception_id: str
    category: Literal["gap", "management_override", "limitation"]
    description: str
    owner: str
    status: Literal["open", "mitigated", "accepted"] = "open"


class ContributionAnalysis(BaseModel):
    """IMP/Impact Frontiers-style contribution workflow."""

    hypothesis: str
    contribution_claim: str
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1)


def run_contribution_analysis(
    *,
    hypothesis: str,
    contribution_claim: str,
    evidence_for: list[str],
    evidence_against: list[str],
) -> ContributionAnalysis:
    """Score a contribution claim from supporting and contradicting evidence."""
    total = len(evidence_for) + len(evidence_against)
    confidence = len(evidence_for) / total if total else 0.0
    return ContributionAnalysis(
        hypothesis=hypothesis,
        contribution_claim=contribution_claim,
        evidence_for=evidence_for,
        evidence_against=evidence_against,
        confidence_score=round(confidence, 3),
    )


def generate_counterfactual_questions(sector: str, business_model: str, claimed_outcome: str) -> list[str]:
    """Generate counterfactual diligence questions."""
    return [
        f"What would beneficiaries in {sector} use without this {business_model}?",
        f"Which comparable providers already deliver {claimed_outcome}?",
        "What share of observed outcomes would likely happen without the investment?",
        "Which external trends could explain the observed change?",
    ]


class EvidenceStrength(BaseModel):
    """Evidence-strength ladder inputs and score."""

    study_design: Literal["none", "case_study", "pre_post", "DID", "RCT"]
    sample_size: int = 0
    third_party_review: bool = False
    beneficiary_voice: bool = False
    score: int = Field(ge=0, le=100)


def score_evidence_strength(
    *,
    study_design: Literal["none", "case_study", "pre_post", "DID", "RCT"],
    sample_size: int,
    third_party_review: bool,
    beneficiary_voice: bool,
) -> EvidenceStrength:
    """Score evidence quality from design, sample, review, and beneficiary voice."""
    design_scores = {"none": 0, "case_study": 25, "pre_post": 45, "DID": 70, "RCT": 90}
    score = design_scores[study_design] + min(20, sample_size // 100)
    if third_party_review:
        score += 10
    if beneficiary_voice:
        score += 5
    return EvidenceStrength(
        study_design=study_design,
        sample_size=sample_size,
        third_party_review=third_party_review,
        beneficiary_voice=beneficiary_voice,
        score=min(100, score),
    )


def calculate_difference_in_differences(
    *,
    treatment_pre: float,
    treatment_post: float,
    comparator_pre: float,
    comparator_post: float,
) -> float:
    """Return the difference-in-differences treatment effect."""
    return round((treatment_post - treatment_pre) - (comparator_post - comparator_pre), 6)


class ExitImpactAssessment(BaseModel):
    """Impact at exit assessment linked to OPIM Principle 8."""

    company_name: str
    opim_principle: str = "OPIM Principle 8"
    durability_risks: list[str] = Field(default_factory=list)
    post_exit_actions: list[str] = Field(default_factory=list)
    residual_score: int = Field(ge=0, le=100)


class ImpactLearningLoop(BaseModel):
    """Hypothesis -> metric -> result -> action -> follow-up loop."""

    hypothesis: str
    metric_id: str
    result: str
    management_action: str
    follow_up_period: str


class AIMetricMapping(BaseModel):
    """AI-assisted mapping to a canonical metric."""

    source_column: str
    canonical_metric_id: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    review_state: ReviewDecision = "pending"


def harmonize_uploaded_metrics(upload_columns: list[str], metric_dictionary: dict[str, str]) -> list[AIMetricMapping]:
    """Map messy uploaded metric columns to canonical metric IDs with confidence."""
    mappings: list[AIMetricMapping] = []
    for column in upload_columns:
        lower = column.lower()
        best_metric = ""
        best_score = 0.0
        for metric_id, label in metric_dictionary.items():
            tokens = {token for token in label.lower().replace("_", " ").split() if len(token) > 2}
            score = sum(1 for token in tokens if token in lower) / max(1, len(tokens))
            if score > best_score:
                best_metric = metric_id
                best_score = score
        mappings.append(AIMetricMapping(
            source_column=column,
            canonical_metric_id=best_metric,
            confidence=round(best_score, 3),
            rationale="Token overlap with canonical metric label.",
        ))
    return mappings


class PortfolioQueryResult(BaseModel):
    """Approved-data natural-language query result."""

    question: str
    answer: str
    citations: list[str] = Field(default_factory=list)


def answer_portfolio_query(question: str, approved_records: list[MetricRecord]) -> PortfolioQueryResult:
    """Answer a simple portfolio query constrained to approved data and citations."""
    verified = [record for record in approved_records if record.is_verified]
    if "average" in question.lower():
        values = [_to_float(record.value) for record in verified]
        numeric = [value for value in values if value is not None]
        answer = str(round(mean(numeric), 4)) if numeric else "No approved numeric data"
    else:
        answer = f"{len(verified)} approved metric record(s) available"
    return PortfolioQueryResult(
        question=question,
        answer=answer,
        citations=[ref for record in verified for ref in record.evidence_refs],
    )


class RegulatoryChangeImpact(BaseModel):
    """Affected assets from a regulatory-change monitor."""

    change_id: str
    affected_rule_packs: list[str]
    affected_templates: list[str]
    affected_companies: list[str]


def monitor_regulatory_change(
    *,
    change_id: str,
    changed_framework: str,
    rule_packs: dict[str, list[str]],
    templates: dict[str, list[str]],
    company_profiles: dict[str, list[str]],
) -> RegulatoryChangeImpact:
    """Flag rule packs, templates, and companies affected by a framework change."""
    affected_rule_packs = [name for name, frameworks in rule_packs.items() if changed_framework in frameworks]
    affected_templates = [name for name, frameworks in templates.items() if changed_framework in frameworks]
    affected_companies = [name for name, frameworks in company_profiles.items() if changed_framework in frameworks]
    return RegulatoryChangeImpact(
        change_id=change_id,
        affected_rule_packs=affected_rule_packs,
        affected_templates=affected_templates,
        affected_companies=affected_companies,
    )


class AIGovernanceLog(BaseModel):
    """Governance log for AI outputs."""

    output_id: str
    prompt_version: str
    model_version: str
    source_refs: list[str]
    human_reviewer: str
    confidence: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)

    @property
    def policy_passed(self) -> bool:
        return bool(self.human_reviewer) and self.confidence >= self.threshold and bool(self.source_refs)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _safe_div(numerator: float, denominator: float | int | None) -> float | None:
    if denominator is None or denominator == 0:
        return None
    return round(numerator / denominator, 6)


__all__ = [
    "AIGovernanceLog",
    "AIExtractionReview",
    "AIMetricMapping",
    "CarbonIntensity",
    "ClimateCoverageRow",
    "CollectionLinkIssue",
    "CollectionTrackerRow",
    "ContributionAnalysis",
    "ControlCheckResult",
    "DisclosurePack",
    "EmissionFactorCatalog",
    "EvidenceStrength",
    "ExceptionRegisterEntry",
    "ExitImpactAssessment",
    "FundBrandingProfile",
    "ImmutableReportManifest",
    "ImportPreview",
    "ImportPreviewRow",
    "JurisdictionProfile",
    "LPExportBundle",
    "PCAFPosition",
    "PCAFResult",
    "PortfolioQueryResult",
    "PublicCollectionLink",
    "ReportPublication",
    "ReviewQueueItem",
    "RulePackTestResult",
    "Scope3ProxyEstimate",
    "SourceLinkedAnswer",
    "answer_portfolio_query",
    "autofill_sfdr_pai",
    "build_climate_coverage_dashboard",
    "build_collection_tracker",
    "build_esrs_disclosure_pack",
    "build_immutable_report_manifest",
    "build_issb_disclosure_pack",
    "build_lp_export_bundle",
    "build_review_queue",
    "calculate_carbon_intensity",
    "calculate_difference_in_differences",
    "calculate_pcaf_financed_emissions",
    "decide_ai_extraction",
    "estimate_scope3_proxy",
    "explore_framework_crosswalk",
    "generate_counterfactual_questions",
    "harmonize_uploaded_metrics",
    "hash_token",
    "issue_collection_link",
    "monitor_regulatory_change",
    "preview_csv_metric_import",
    "run_control_checks",
    "run_contribution_analysis",
    "run_rule_pack_tests",
    "score_evidence_strength",
    "select_jurisdiction_profile",
    "transition_report_publication",
]
