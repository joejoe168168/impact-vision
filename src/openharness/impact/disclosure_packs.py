"""Source-linked ISSB / ESRS disclosure packs and SFDR PAI autofill (moved from roadmap_v2, v7 W5.4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.evidence_graph import EvidenceGraph

DisclosureStatus = Literal["direct", "proxy", "missing", "not_applicable"]


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
        status = answer.status
        if evidence_graph is not None and answer.source_node_ids and not sources:
            status = "missing"
        normalized.append(answer.model_copy(update={
            "source_node_ids": sources,
            "status": status,
        }))
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


__all__ = [
    "DisclosureStatus",
    "SourceLinkedAnswer",
    "DisclosurePack",
    "build_issb_disclosure_pack",
    "build_esrs_disclosure_pack",
    "autofill_sfdr_pai",
]
