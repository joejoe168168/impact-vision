from __future__ import annotations
import json
from typing import Literal
from pydantic import BaseModel, Field
from openharness.impact.audit_trail import AuditTrail
from openharness.impact.evidence_graph import EvidenceGraph
from openharness.impact.signed_feed import HMACSigner
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class DMRVInput(BaseModel):
    action: Literal["ingest", "anchor", "summarise", "verify"]
    evidence: dict = Field(default_factory=dict)
    claim_id: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    envelope: dict = Field(default_factory=dict)


class DMRVEvidenceTool(BaseTool):
    name = "dmrv_evidence"
    description = "Ingest and hash dMRV time series, derive canonical metrics, and anchor or verify claim-evidence envelopes."
    input_model = DMRVInput

    def __init__(self):
        self.graph = EvidenceGraph()
        self.trail = AuditTrail()
        self.signer = HMACSigner(key=b"impact-vision-dmrv")

    def is_read_only(self, arguments: BaseModel) -> bool:
        return getattr(arguments, "action", "") == "verify"

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        del context
        args = (
            arguments if isinstance(arguments, DMRVInput) else DMRVInput.model_validate(arguments)
        )
        try:
            from openharness.impact.dmrv import (
                TimeSeriesEvidence,
                anchor_claim,
                ingest_time_series,
                summarise_series,
                verify_anchor,
            )

            if args.action == "verify":
                result = {"valid": verify_anchor(args.envelope, self.signer)}
            elif args.action == "anchor":
                result = anchor_claim(args.claim_id, args.evidence_ids, self.graph, self.signer)
            else:
                evidence = TimeSeriesEvidence.model_validate(args.evidence)
                result = (
                    ingest_time_series(evidence, self.graph, self.trail)
                    if args.action == "ingest"
                    else summarise_series(evidence).model_dump(mode="json")
                )
            return ToolResult(output=json.dumps(result, default=str), metadata=result)
        except Exception as exc:
            return ToolResult(output=f"dmrv_evidence failed: {exc}", is_error=True)
