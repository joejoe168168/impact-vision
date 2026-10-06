"""Digital MRV time-series ingestion, hashing and HMAC anchoring."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, model_validator

from openharness.impact.evidence_graph import EvidenceGraph, EvidenceLink, EvidenceNode
from openharness.impact.models import MetricRecord
from openharness.impact.signed_feed import HMACSigner, get_signer


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


def get_dmrv_signer(*, key: bytes | str | None = None) -> HMACSigner:
    """Return the HMAC signer for dMRV envelopes.

    Production deployments must set ``IMPACT_VISION_DMRV_HMAC_KEY`` (see
    :func:`openharness.impact.signed_feed.resolve_signing_key`).
    """
    return get_signer("dmrv", key)


def observations_to_series(observations: list, metric_id: str) -> TimeSeriesEvidence:
    """Lift geospatial observations into a remote-sensing dMRV series."""
    if not observations:
        raise ValueError("observations must not be empty")
    first = observations[0]
    points = [
        {
            "t": getattr(item.observation_date, "isoformat", lambda: str(item.observation_date))(),
            "value": item.value,
            "unit": item.unit,
            "biome": getattr(item, "biome", None),
            "dataset": getattr(item, "dataset", ""),
        }
        for item in observations
    ]
    note = getattr(first, "methodology_note", "") or getattr(first, "dataset", "remote_sensing")
    version = getattr(first, "dataset_version", "")
    return TimeSeriesEvidence(
        series_id=f"{first.asset_id}:{getattr(first, 'dataset', 'obs')}",
        source_kind="remote_sensing",
        metric_id=metric_id,
        points=points,
        provider=getattr(first, "provider_id", "geospatial"),
        methodology=f"{note} {version}".strip(),
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
    "get_dmrv_signer",
    "ingest_time_series",
    "observations_to_series",
    "summarise_series",
    "verify_anchor",
]
