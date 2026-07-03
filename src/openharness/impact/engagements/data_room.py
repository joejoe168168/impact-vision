"""Client & investee data room (roadmap-v4 Track 3).

Wraps the v3 investee-collection / questionnaire / surveys surfaces into the
consultant-facing "data room" concept used by Rimm, Holtara and Impact
Institute: the client uploads evidence, the consultant sees completeness /
quality / multi-entity rollup signals, and every gap turns into a coaching
card instead of a silent omission.

Design goals:

* **No v3 fork.** We reuse `investee_collection`, `questionnaire_v2`,
  `surveys`, `roadmap_v2.build_collection_tracker`, and
  `roadmap_v2.issue_collection_link` where they already exist.
* **Engagement-scoped.** Every data-request pack, exception, and coaching
  card is bound to an engagement so the audit trail covers the whole flow.
* **Bundle-aware.** Data request packs pull their field list from the
  engagement bundle's recommended metrics plus a sector/geography overlay.
"""

from __future__ import annotations

import secrets
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field


ExceptionKind = Literal[
    "missing",
    "stale",
    "inconsistent",
    "proxy",
    "unverified",
    "outlier",
]


class DataRequestField(BaseModel):
    """One field on a smart data-request pack (Track 3.3)."""

    field_id: str = Field(default_factory=lambda: f"fld_{secrets.token_hex(4)}")
    metric_id: str
    label: str
    required: bool = True
    unit: str = ""
    definition: str = ""
    examples: list[str] = Field(default_factory=list)
    acceptable_evidence: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)


class DataRequestPack(BaseModel):
    """Productised data-request pack bound to an engagement.

    Wraps the v3 `InvesteeQuestionnaireSchema` style list of fields with the
    Track 3.6 "guidance cards": definition + examples + acceptable evidence
    + common mistakes, so the client knows *how* to answer, not just *what*
    to answer.
    """

    pack_id: str = Field(default_factory=lambda: f"pack_{secrets.token_hex(6)}")
    engagement_id: str = ""
    bundle_id: str = ""
    title: str
    description: str = ""
    fields: list[DataRequestField] = Field(default_factory=list)
    sector: str = ""
    geography: str = ""
    created_at: str = Field(default_factory=lambda: _now())
    issued_links: list[str] = Field(default_factory=list)
    version: int = 1


class FieldSubmission(BaseModel):
    """A single client response to a data-request pack field."""

    field_id: str
    metric_id: str
    value: str = ""
    unit: str = ""
    period: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str = ""
    submitted_at: str = Field(default_factory=lambda: _now())
    submitted_by: str = ""


class DataRoomSubmission(BaseModel):
    """All responses for a single reporting entity on a given pack.

    This mirrors the v3 :class:`~openharness.impact.investee_collection.CollectionSubmission`
    but is engagement-scoped so the reviewer queue can surface exceptions
    per-engagement rather than per-fund.
    """

    submission_id: str = Field(default_factory=lambda: f"sub_{secrets.token_hex(6)}")
    pack_id: str
    engagement_id: str = ""
    entity_name: str
    reporting_period: str = ""
    responses: list[FieldSubmission] = Field(default_factory=list)
    submitted_at: str = Field(default_factory=lambda: _now())
    submitted_by: str = ""


class DataQualityException(BaseModel):
    """One row in the data-quality exception workflow (Track 3.5)."""

    exception_id: str = Field(default_factory=lambda: f"ex_{secrets.token_hex(4)}")
    submission_id: str
    field_id: str
    metric_id: str
    kind: ExceptionKind
    severity: Literal["low", "medium", "high"] = "medium"
    details: str = ""
    suggested_action: str = ""
    status: Literal["open", "in_review", "resolved", "waived"] = "open"
    raised_at: str = Field(default_factory=lambda: _now())
    resolved_at: str = ""
    resolved_by: str = ""


class CompletenessRow(BaseModel):
    """Per-entity completeness snapshot."""

    entity_name: str
    required_count: int
    submitted_count: int
    missing_metrics: list[str] = Field(default_factory=list)
    coverage_pct: float = 0.0


class CompletenessReport(BaseModel):
    """Deliverable-level evidence completeness (Track 3.4)."""

    pack_id: str
    engagement_id: str
    rows: list[CompletenessRow] = Field(default_factory=list)
    exceptions: list[DataQualityException] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overall_coverage_pct(self) -> float:
        if not self.rows:
            return 0.0
        return round(sum(r.coverage_pct for r in self.rows) / len(self.rows), 3)


class MultiEntityRollup(BaseModel):
    """Multi-entity consolidation (Track 3.7)."""

    engagement_id: str
    pack_id: str
    entity_count: int = 0
    metrics_covered: int = 0
    metrics_missing: list[str] = Field(default_factory=list)
    per_entity_coverage: dict[str, float] = Field(default_factory=dict)
    per_metric_fill_rate: dict[str, float] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fill_rate(self) -> float:
        if not self.per_metric_fill_rate:
            return 0.0
        values = list(self.per_metric_fill_rate.values())
        return round(sum(values) / len(values), 3)


class CoachingCard(BaseModel):
    """Investee coaching card generated from a failed validation."""

    card_id: str = Field(default_factory=lambda: f"card_{secrets.token_hex(4)}")
    entity_name: str
    metric_id: str
    message: str
    suggested_action: str
    evidence_refs: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high"] = "medium"


# ----------------------------------------------------------------- builders


_DEFAULT_FIELDS_BY_BUNDLE: dict[str, list[tuple[str, str, str, list[str]]]] = {
    # Each tuple: (metric_id, label, unit, frameworks)
    "strategy_imm": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+", "SDG"]),
        ("PI4060", "Growth in revenue", "%", ["IRIS+"]),
        ("OI6213", "Jobs created", "count", ["IRIS+", "GRI"]),
    ],
    "dd_light": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+"]),
        ("PI4060", "Growth in revenue", "%", ["IRIS+"]),
    ],
    "dd_mid": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+"]),
        ("PI4060", "Growth in revenue", "%", ["IRIS+"]),
        ("OI6213", "Jobs created", "count", ["IRIS+", "GRI"]),
        ("PD5833", "Greenhouse-gas emissions", "tCO2e", ["IRIS+", "TCFD"]),
    ],
    "dd_full_iwa": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+"]),
        ("PI4060", "Growth in revenue", "%", ["IRIS+"]),
        ("OI6213", "Jobs created", "count", ["IRIS+", "GRI"]),
        ("PD5833", "Greenhouse-gas emissions", "tCO2e", ["IRIS+", "TCFD"]),
        ("PI7098", "Impact-weighted revenue", "USD", ["IRIS+", "IWA"]),
    ],
    "esg_baseline": [
        ("PD5833", "Greenhouse-gas emissions", "tCO2e", ["IRIS+", "TCFD", "ISSB"]),
        ("OI6213", "Jobs created", "count", ["IRIS+", "GRI"]),
        ("PD2471", "Diversity of workforce", "%", ["GRI", "ESRS"]),
    ],
    "annual_impact_report": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+"]),
        ("PI4060", "Growth in revenue", "%", ["IRIS+"]),
        ("PD5833", "Greenhouse-gas emissions", "tCO2e", ["IRIS+", "TCFD"]),
    ],
    "lp_ddq": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+"]),
        ("PD5833", "Greenhouse-gas emissions", "tCO2e", ["IRIS+", "EDCI"]),
        ("PD2471", "Diversity of workforce", "%", ["EDCI", "GRI"]),
    ],
    "verification_3pillar": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+"]),
        ("PD5833", "Greenhouse-gas emissions", "tCO2e", ["IRIS+"]),
    ],
    "exit_vdd": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+"]),
        ("PI4060", "Growth in revenue", "%", ["IRIS+"]),
    ],
    "regulatory": [
        ("PD5833", "Greenhouse-gas emissions", "tCO2e", ["SFDR PAI", "CSRD"]),
        ("PD2471", "Diversity of workforce", "%", ["SFDR PAI"]),
    ],
    "stakeholder_voice": [
        ("OI4112", "Direct beneficiaries served", "people", ["IRIS+"]),
        ("OI2864", "Client satisfaction", "score", ["IRIS+", "Lean Data"]),
    ],
    "capacity_training": [
        ("OI6213", "Jobs created", "count", ["IRIS+"]),
        ("OI2864", "Client satisfaction", "score", ["IRIS+"]),
    ],
}


def edci_request_fields(*, required_only: bool = False) -> list[DataRequestField]:
    """Build data-request fields from the EDCI metric set.

    EDCI is the LP-side automation anchor (ILPA guidance): collecting against
    the standardized EDCI fields serves LP reports, benchmarking, and most
    bespoke DDQs at once. Non-core fields are marked optional.
    """
    from openharness.impact.frameworks.edci import get_edci_metrics

    fields: list[DataRequestField] = []
    for metric in get_edci_metrics(required_only=required_only):
        frameworks = ["EDCI"]
        if metric.iris_cross_refs:
            frameworks.append("IRIS+")
        if metric.gri_cross_refs:
            frameworks.append("GRI")
        if metric.sfdr_cross_refs:
            frameworks.append("SFDR PAI")
        fields.append(
            DataRequestField(
                metric_id=metric.id,
                label=metric.name,
                required=metric.required,
                unit=metric.unit,
                definition=metric.description,
                acceptable_evidence=_default_evidence(metric.id),
                common_mistakes=[
                    "Reporting an AI-modelled estimate as a measured value without "
                    "labelling it as an estimate and disclosing the methodology",
                ],
                frameworks=frameworks,
            )
        )
    return fields


def build_data_request_pack(
    *,
    engagement_id: str,
    bundle_id: str,
    title: str = "",
    sector: str = "",
    geography: str = "",
    extra_fields: Iterable[DataRequestField] | None = None,
) -> DataRequestPack:
    """Build a smart data-request pack for the given bundle.

    ``bundle_id="edci_core"`` scaffolds the pack from the EDCI metric set
    (the default LP-reporting collection target) instead of a bundle template.
    """
    fields: list[DataRequestField] = []
    if bundle_id == "edci_core":
        fields.extend(edci_request_fields())
    else:
        defaults = _DEFAULT_FIELDS_BY_BUNDLE.get(bundle_id, [])
        for metric_id, label, unit, frameworks in defaults:
            fields.append(
                DataRequestField(
                    metric_id=metric_id,
                    label=label,
                    unit=unit,
                    frameworks=list(frameworks),
                    definition=_default_definition(metric_id, label),
                    examples=_default_examples(metric_id),
                    acceptable_evidence=_default_evidence(metric_id),
                    common_mistakes=_default_mistakes(metric_id),
                )
            )
    for extra in extra_fields or []:
        fields.append(extra)
    pack_title = title or f"Data request pack: {bundle_id}"
    return DataRequestPack(
        engagement_id=engagement_id,
        bundle_id=bundle_id,
        title=pack_title,
        fields=fields,
        sector=sector,
        geography=geography,
    )


def score_completeness(
    pack: DataRequestPack,
    submissions: list[DataRoomSubmission],
) -> CompletenessReport:
    """Per-entity completeness + exception scan."""
    required = [f for f in pack.fields if f.required]
    required_metric_ids = [f.metric_id.upper() for f in required]

    rows: list[CompletenessRow] = []
    exceptions: list[DataQualityException] = []

    for submission in submissions:
        # Only count a response as "covering" a required metric when the
        # value is non-empty; empty strings still leave the required metric
        # unsatisfied (but will surface as a per-response 'missing'
        # exception below rather than as a metric-level gap).
        responses_by_metric = {
            r.metric_id.upper(): r for r in submission.responses
        }
        non_empty_metrics = {
            metric_id
            for metric_id, r in responses_by_metric.items()
            if r.value.strip()
        }
        missing = [
            metric_id
            for metric_id in required_metric_ids
            if metric_id not in non_empty_metrics
        ]
        submitted = len(required_metric_ids) - len(missing)
        coverage = submitted / len(required_metric_ids) if required_metric_ids else 1.0
        rows.append(
            CompletenessRow(
                entity_name=submission.entity_name,
                required_count=len(required_metric_ids),
                submitted_count=submitted,
                missing_metrics=missing,
                coverage_pct=round(coverage, 3),
            )
        )
        for metric_id in missing:
            field = next(
                (f for f in pack.fields if f.metric_id.upper() == metric_id),
                None,
            )
            exceptions.append(
                DataQualityException(
                    submission_id=submission.submission_id,
                    field_id=field.field_id if field else "",
                    metric_id=metric_id,
                    kind="missing",
                    severity="high",
                    details=f"{submission.entity_name} did not submit {metric_id}.",
                    suggested_action=(
                        f"Follow up with {submission.entity_name} to collect {metric_id}."
                    ),
                )
            )
        already_flagged_missing = set(missing)
        for response in submission.responses:
            value_empty = not response.value.strip()
            no_evidence = not response.evidence_refs
            metric_key = response.metric_id.upper()
            if value_empty and metric_key not in already_flagged_missing:
                exceptions.append(
                    DataQualityException(
                        submission_id=submission.submission_id,
                        field_id=response.field_id,
                        metric_id=response.metric_id,
                        kind="missing",
                        severity="high",
                        details=f"{submission.entity_name} submitted an empty value.",
                        suggested_action="Request a numeric value or narrative substitute.",
                    )
                )
            elif not value_empty and no_evidence:
                exceptions.append(
                    DataQualityException(
                        submission_id=submission.submission_id,
                        field_id=response.field_id,
                        metric_id=response.metric_id,
                        kind="unverified",
                        severity="medium",
                        details=f"{submission.entity_name} did not attach evidence for {response.metric_id}.",
                        suggested_action="Link to a source document, workbook, or interview note.",
                    )
                )

    return CompletenessReport(
        pack_id=pack.pack_id,
        engagement_id=pack.engagement_id,
        rows=rows,
        exceptions=exceptions,
    )


def rollup_multi_entity(
    pack: DataRequestPack,
    submissions: list[DataRoomSubmission],
) -> MultiEntityRollup:
    """Consolidate multiple entities onto a single fill-rate view."""
    required_metric_ids = [f.metric_id.upper() for f in pack.fields if f.required]
    per_entity_coverage: dict[str, float] = {}
    per_metric_counts: dict[str, int] = defaultdict(int)
    entity_count = len(submissions)

    for submission in submissions:
        responses = {r.metric_id.upper() for r in submission.responses if r.value.strip()}
        covered = len([m for m in required_metric_ids if m in responses])
        per_entity_coverage[submission.entity_name] = round(
            covered / len(required_metric_ids) if required_metric_ids else 1.0, 3
        )
        for metric in responses:
            per_metric_counts[metric] += 1

    per_metric_fill_rate = {
        metric_id: round(count / entity_count, 3) if entity_count else 0.0
        for metric_id, count in per_metric_counts.items()
    }
    metrics_missing = sorted(
        metric_id for metric_id in required_metric_ids
        if per_metric_counts.get(metric_id, 0) == 0
    )
    return MultiEntityRollup(
        engagement_id=pack.engagement_id,
        pack_id=pack.pack_id,
        entity_count=entity_count,
        metrics_covered=len([m for m in required_metric_ids if m in per_metric_counts]),
        metrics_missing=metrics_missing,
        per_entity_coverage=per_entity_coverage,
        per_metric_fill_rate=per_metric_fill_rate,
    )


def build_coaching_cards(
    report: CompletenessReport,
    *,
    pack: DataRequestPack,
    submissions: Iterable[DataRoomSubmission] | None = None,
) -> list[CoachingCard]:
    """Convert exceptions into investee coaching cards (Track 3.6 + 6.3).

    ``submissions`` is optional but recommended: without it the card can
    only derive the entity name from ``missing_metrics`` rows, which
    means ``unverified`` / ``stale`` / ``proxy`` exceptions on non-missing
    responses fall back to "Unknown". Passing the original submissions
    re-establishes the entity context via ``submission_id``.
    """
    cards: list[CoachingCard] = []
    field_index = {f.field_id: f for f in pack.fields}
    submission_index = {
        s.submission_id: s.entity_name for s in (submissions or [])
    }
    for exc in report.exceptions:
        field = field_index.get(exc.field_id)
        entity_name = submission_index.get(exc.submission_id, "")
        if not entity_name:
            row = next(
                (r for r in report.rows if _submission_matches(r, exc)),
                None,
            )
            entity_name = row.entity_name if row else "Unknown"
        message_parts = [exc.details or f"{exc.kind} exception for {exc.metric_id}"]
        if field and field.common_mistakes:
            message_parts.append(
                "Common mistakes: " + "; ".join(field.common_mistakes)
            )
        suggested = exc.suggested_action or (
            f"Refer to the guidance card for {exc.metric_id}."
        )
        if field and field.acceptable_evidence:
            suggested += " Acceptable evidence: " + "; ".join(field.acceptable_evidence)
        cards.append(
            CoachingCard(
                entity_name=entity_name,
                metric_id=exc.metric_id,
                message=" ".join(message_parts),
                suggested_action=suggested,
                severity=exc.severity,
            )
        )
    return cards


# ------------------------------------------------------------- default content


def _default_definition(metric_id: str, label: str) -> str:
    return (
        f"IRIS+ metric {metric_id} ({label}). Report the audited value for the "
        "reporting period in the requested unit; if an estimate is used, flag it "
        "as a proxy with a note."
    )


def _default_examples(metric_id: str) -> list[str]:
    return [
        "Annual audited value for the reporting entity.",
        "Portfolio-weighted rollup when the metric is calculated at fund level.",
    ]


def _default_evidence(metric_id: str) -> list[str]:
    return [
        "Audited financial statement or impact report extract",
        "Management approved data pack",
        "Interview note with the CFO/ESG lead",
    ]


def _default_mistakes(metric_id: str) -> list[str]:
    return [
        "Submitting a planned/budget figure instead of the actual value",
        "Omitting the unit or period",
        "Pasting a ratio when the metric asks for the absolute value",
    ]


def _submission_matches(row: CompletenessRow, exc: DataQualityException) -> bool:
    return any(m == exc.metric_id for m in row.missing_metrics)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "CoachingCard",
    "CompletenessReport",
    "CompletenessRow",
    "DataQualityException",
    "DataRequestField",
    "DataRequestPack",
    "DataRoomSubmission",
    "ExceptionKind",
    "FieldSubmission",
    "MultiEntityRollup",
    "build_coaching_cards",
    "build_data_request_pack",
    "edci_request_fields",
    "rollup_multi_entity",
    "score_completeness",
]
