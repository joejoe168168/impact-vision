"""SOC 2 Type II / ISO 27001 readiness checklist (Phase 17).

Deterministic checklist of the controls most commonly required when an
impact-data platform is audited. The default list covers the five AICPA
SOC 2 Trust Service Criteria (Security, Availability, Processing
Integrity, Confidentiality, Privacy) plus the 14 ISO/IEC 27001:2022
control clauses.

Each control is a :class:`ControlItem` with a status field the GP fills
in over time. :func:`build_readiness_report` summarises completion.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ControlStatus = Literal["not-started", "in-progress", "implemented", "verified"]
Framework = Literal["SOC2-TSC", "ISO27001-2022"]


class ControlItem(BaseModel):
    control_id: str
    framework: Framework
    category: str
    description: str
    status: ControlStatus = "not-started"
    evidence_ref: str = ""
    owner: str = ""


class ReadinessReport(BaseModel):
    entity: str
    as_of: str = ""
    total_controls: int
    implemented: int
    verified: int
    in_progress: int
    not_started: int
    completion_pct: float
    blockers: list[str] = Field(default_factory=list)
    items: list[ControlItem] = Field(default_factory=list)


_SOC2_CONTROLS = [
    ("CC1", "Security",          "Control environment (tone at the top)."),
    ("CC2", "Security",          "Communication & information."),
    ("CC3", "Security",          "Risk assessment."),
    ("CC4", "Security",          "Monitoring activities."),
    ("CC5", "Security",          "Control activities."),
    ("CC6", "Logical access",    "Logical & physical access controls."),
    ("CC7", "System operations", "System operations."),
    ("CC8", "Change management", "Change management."),
    ("A1",  "Availability",      "Availability commitments & SLAs."),
    ("PI1", "Processing Integrity", "Processing completeness & accuracy."),
    ("C1",  "Confidentiality",   "Confidentiality — classification & retention."),
    ("P1",  "Privacy",           "Privacy notice & consent."),
]

_ISO_CLAUSES = [
    ("5",  "Organisational",     "Information security policies."),
    ("6",  "People",             "People controls."),
    ("7",  "Physical",           "Physical & environmental security."),
    ("8",  "Technological",      "Technological controls."),
    ("9",  "Access control",     "Access control."),
    ("10", "Cryptography",       "Cryptographic controls."),
    ("11", "Operations security","Operations security."),
    ("12", "Comms security",     "Communications security."),
    ("13", "Supplier",           "Supplier relationships."),
    ("14", "Incident",           "Incident management."),
    ("15", "Continuity",         "Business continuity."),
    ("16", "Compliance",         "Compliance."),
    ("17", "Dev & acquisition",  "Dev & acquisition."),
    ("18", "Cloud services",     "Cloud service controls."),
]


def default_checklist() -> list[ControlItem]:
    items: list[ControlItem] = []
    for cid, cat, desc in _SOC2_CONTROLS:
        items.append(ControlItem(
            control_id=f"SOC2-{cid}", framework="SOC2-TSC",
            category=cat, description=desc,
        ))
    for cid, cat, desc in _ISO_CLAUSES:
        items.append(ControlItem(
            control_id=f"ISO-{cid}", framework="ISO27001-2022",
            category=cat, description=desc,
        ))
    return items


def build_readiness_report(
    entity: str,
    items: list[ControlItem] | None = None,
    *,
    as_of: str = "",
) -> ReadinessReport:
    its = items if items is not None else default_checklist()
    total = len(its)
    implemented = sum(1 for i in its if i.status == "implemented")
    verified = sum(1 for i in its if i.status == "verified")
    in_progress = sum(1 for i in its if i.status == "in-progress")
    not_started = sum(1 for i in its if i.status == "not-started")
    done = implemented + verified
    pct = round(100.0 * done / total, 1) if total else 0.0
    blockers = [f"{i.control_id}: {i.description}" for i in its if i.status == "not-started"][:10]
    return ReadinessReport(
        entity=entity, as_of=as_of, total_controls=total,
        implemented=implemented, verified=verified,
        in_progress=in_progress, not_started=not_started,
        completion_pct=pct, blockers=blockers, items=its,
    )


__all__ = [
    "ControlItem", "ReadinessReport", "ControlStatus", "Framework",
    "default_checklist", "build_readiness_report",
]
