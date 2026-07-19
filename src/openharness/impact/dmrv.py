"""Digital MRV time-series ingestion, hashing and HMAC anchoring."""

from __future__ import annotations
import json
import hashlib
from typing import Literal
from pydantic import BaseModel, model_validator
from openharness.impact.evidence_graph import EvidenceGraph, EvidenceLink, EvidenceNode
from openharness.impact.models import MetricRecord


class TimeSeriesEvidence(BaseModel):
    series_id: str
    source_kind: Literal["remote_sensing", "iot_sensor", "meter", "survey_wave", "registry_api"]
    metric_id: str
    points: list[dict]
    provider: str
    methodology: str
    content_hash: str = ""

    @model_validator(mode="after")
    def compute_hash(self):
        payload = self.model_dump(exclude={"content_hash"}, mode="json")
        self.content_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        return self


def ingest_time_series(evidence: TimeSeriesEvidence, graph: EvidenceGraph, trail) -> dict:
    node_id = f"evidence:dmrv:{evidence.series_id}"
    graph.nodes.append(
        EvidenceNode(
            id=node_id,
            type="evidence",
            label=evidence.series_id,
            data=evidence.model_dump(mode="json"),
        )
    )
    graph.links.append(
        EvidenceLink(
            source=f"metric:{evidence.metric_id.upper()}",
            target=node_id,
            type="supported_by",
            rationale="dMRV time series",
        )
    )
    event = trail.record_event(
        event_type="dmrv.ingested",
        payload=evidence.model_dump(mode="json"),
        actor=evidence.provider,
    )
    return {
        "node_id": node_id,
        "content_hash": evidence.content_hash,
        "audit_hash": event.content_hash,
    }


def anchor_claim(claim_id: str, evidence_ids: list[str], graph: EvidenceGraph, signer) -> dict:
    hashes = {
        node_id: next(
            (node.data.get("content_hash", "") for node in graph.nodes if node.id == node_id), ""
        )
        for node_id in evidence_ids
    }
    payload = {
        "claim_id": claim_id,
        "evidence_hashes": hashes,
        "proof_paths": [
            link.model_dump()
            for link in graph.links
            if link.source == claim_id or link.target == claim_id
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {**payload, "signature": signer.sign(canonical), "signer_id": signer.id}


def verify_anchor(envelope: dict, signer) -> bool:
    payload = {key: envelope[key] for key in ("claim_id", "evidence_hashes", "proof_paths")}
    return signer.verify(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(), envelope["signature"]
    )


def summarise_series(evidence: TimeSeriesEvidence) -> MetricRecord:
    values = [float(p["value"]) for p in evidence.points]
    method = "sum" if "sum" in evidence.methodology.lower() else "mean"
    value = sum(values) if method == "sum" else sum(values) / len(values)
    periods = [str(p["t"]) for p in evidence.points]
    return MetricRecord(
        metric_id=evidence.metric_id,
        value=value,
        unit=str(evidence.points[0]["unit"]),
        period=f"{min(periods)}..{max(periods)}",
        source=evidence.provider,
        owner=evidence.provider,
        quality_score=80,
        verification_status="management_verified",
        source_type="system_import",
        evidence_refs=[evidence.content_hash],
        methodology=f"dMRV {method}: {evidence.methodology}",
    )


__all__ = [
    "TimeSeriesEvidence",
    "anchor_claim",
    "ingest_time_series",
    "summarise_series",
    "verify_anchor",
]
