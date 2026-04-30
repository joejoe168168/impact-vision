"""Evidence graph linking claims, metrics, targets, evidence, and reports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.models import ImpactClaim, ImpactTarget, MetricRecord


NodeType = Literal["claim", "metric", "target", "evidence", "report_section"]
LinkType = Literal[
    "supported_by",
    "measured_by",
    "tracks",
    "appears_in",
    "derived_from",
]


class EvidenceNode(BaseModel):
    """One typed node in an impact evidence graph."""

    id: str
    type: NodeType
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class EvidenceLink(BaseModel):
    """A directed relationship between two evidence nodes."""

    source: str
    target: str
    type: LinkType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""


class EvidenceGraph(BaseModel):
    """Portable graph for report lineage, assurance packs, and review UIs."""

    nodes: list[EvidenceNode] = Field(default_factory=list)
    links: list[EvidenceLink] = Field(default_factory=list)

    def node_ids(self) -> set[str]:
        return {node.id for node in self.nodes}

    def links_for(self, node_id: str) -> list[EvidenceLink]:
        return [
            link for link in self.links
            if link.source == node_id or link.target == node_id
        ]


def _add_node(nodes: dict[str, EvidenceNode], node: EvidenceNode) -> None:
    nodes.setdefault(node.id, node)


def _evidence_id(ref: str) -> str:
    normalized = ref.strip().replace("://", "-")
    safe = "".join(ch if ch.isalnum() else "-" for ch in normalized).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return f"evidence:{safe or 'unknown'}"


def build_evidence_graph(
    *,
    claims: list[ImpactClaim | dict[str, Any]] | None = None,
    metric_records: list[MetricRecord | dict[str, Any]] | None = None,
    targets: list[ImpactTarget | dict[str, Any]] | None = None,
    target_tracking: dict[str, Any] | None = None,
    report_sections: dict[str, list[str]] | None = None,
) -> EvidenceGraph:
    """Build a lineage graph from claims, metrics, targets, and report sections.

    ``report_sections`` maps section IDs such as ``"sec-claims"`` to node IDs
    that appear in that section, usually metric IDs, claim IDs, or target IDs.
    """
    nodes: dict[str, EvidenceNode] = {}
    links: list[EvidenceLink] = []
    metric_node_by_id: dict[str, str] = {}
    target_node_by_metric: dict[str, str] = {}

    for record_data in metric_records or []:
        record = (
            record_data
            if isinstance(record_data, MetricRecord)
            else MetricRecord.model_validate(record_data)
        )
        node_id = f"metric:{record.metric_id}"
        metric_node_by_id[record.metric_id] = node_id
        _add_node(nodes, EvidenceNode(
            id=node_id,
            type="metric",
            label=record.metric_id,
            data=record.model_dump(mode="json"),
        ))
        for ref in record.evidence_refs:
            evidence_node_id = _evidence_id(ref)
            _add_node(nodes, EvidenceNode(
                id=evidence_node_id,
                type="evidence",
                label=ref,
                data={"ref": ref},
            ))
            links.append(EvidenceLink(
                source=node_id,
                target=evidence_node_id,
                type="supported_by",
                confidence=record.quality_score / 100,
                rationale=f"{record.metric_id} source evidence",
            ))

    for target_data in targets or []:
        target = (
            target_data
            if isinstance(target_data, ImpactTarget)
            else ImpactTarget.model_validate(target_data)
        )
        node_id = f"target:{target.metric_id}"
        target_node_by_metric[target.metric_id] = node_id
        _add_node(nodes, EvidenceNode(
            id=node_id,
            type="target",
            label=target.description or target.metric_id,
            data=target.model_dump(mode="json"),
        ))
        metric_node_id = metric_node_by_id.get(target.metric_id)
        if metric_node_id:
            links.append(EvidenceLink(
                source=node_id,
                target=metric_node_id,
                type="tracks",
                rationale="Target progress is measured by this metric.",
            ))

    for item in (target_tracking or {}).get("targets", []):
        metric_id = str(item.get("metric_id", "")).strip().upper()
        if not metric_id:
            continue
        target_node_id = target_node_by_metric.get(metric_id, f"target:{metric_id}")
        if target_node_id not in nodes:
            _add_node(nodes, EvidenceNode(
                id=target_node_id,
                type="target",
                label=str(item.get("target") or item.get("target_description") or metric_id),
                data=dict(item),
            ))
        metric_node_id = metric_node_by_id.get(metric_id)
        if metric_node_id:
            links.append(EvidenceLink(
                source=target_node_id,
                target=metric_node_id,
                type="tracks",
                rationale="Target-tracking result uses this metric value.",
            ))

    for idx, claim_data in enumerate(claims or []):
        claim = claim_data if isinstance(claim_data, ImpactClaim) else ImpactClaim.model_validate(claim_data)
        node_id = f"claim:{idx + 1}"
        _add_node(nodes, EvidenceNode(
            id=node_id,
            type="claim",
            label=claim.text[:120],
            data=claim.model_dump(mode="json"),
        ))
        for metric_id in claim.mapped_metrics:
            metric_node_id = metric_node_by_id.get(metric_id)
            if metric_node_id:
                links.append(EvidenceLink(
                    source=node_id,
                    target=metric_node_id,
                    type="measured_by",
                    confidence=claim.confidence,
                    rationale="Claim maps to reported metric.",
                ))

    for section_id, referenced_ids in (report_sections or {}).items():
        section_node_id = f"section:{section_id}"
        _add_node(nodes, EvidenceNode(
            id=section_node_id,
            type="report_section",
            label=section_id,
            data={"section_id": section_id},
        ))
        for ref_id in referenced_ids:
            if ref_id in nodes:
                target_id = ref_id
            elif ref_id.startswith(("claim:", "metric:", "target:", "evidence:")):
                target_id = ref_id
            elif ref_id.upper() in metric_node_by_id:
                target_id = metric_node_by_id[ref_id.upper()]
            else:
                continue
            if target_id in nodes:
                links.append(EvidenceLink(
                    source=target_id,
                    target=section_node_id,
                    type="appears_in",
                    rationale="Node is rendered or summarized in this report section.",
                ))

    return EvidenceGraph(nodes=list(nodes.values()), links=links)


def graph_warnings(graph: EvidenceGraph) -> list[str]:
    """Return lineage warnings for missing evidence or unsupported claims."""
    warnings: list[str] = []
    supported_metrics = {
        link.source for link in graph.links
        if link.type == "supported_by"
    }
    measured_claims = {
        link.source for link in graph.links
        if link.type == "measured_by"
    }
    for node in graph.nodes:
        if node.type == "metric" and node.id not in supported_metrics:
            warnings.append(f"{node.id} has no supporting evidence reference")
        if node.type == "claim" and node.id not in measured_claims:
            warnings.append(f"{node.id} is not linked to a reported metric")
    return warnings


__all__ = [
    "EvidenceGraph",
    "EvidenceLink",
    "EvidenceNode",
    "build_evidence_graph",
    "graph_warnings",
]
