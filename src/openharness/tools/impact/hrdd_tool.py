"""Tool: Human-rights & value-chain due diligence (HRDD / CSDDD) — v5 Track A3."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.hrdd import (
    GrievanceMechanism,
    HRDDInput,
    RemediationCase,
    SalientIssue,
    assess_hrdd,
    seed_salient_issues_from_text,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class HRDDToolInput(BaseModel):
    action: Literal["assess", "seed_from_text"] = "assess"
    company_name: str = ""
    sector: str = ""
    geographies: list[str] = Field(default_factory=list)
    salient_issues: list[dict] = Field(
        default_factory=list,
        description="Salient issues: {name, category, value_chain_tier, severity, likelihood, leverage, ...}",
    )
    grievance: dict = Field(default_factory=dict, description="Grievance mechanism attributes")
    remediation_cases: list[dict] = Field(default_factory=list)
    has_rbc_policy: bool = False
    has_impact_identification: bool = False
    has_mitigation_plan: bool = False
    tracks_effectiveness: bool = False
    communicates_publicly: bool = False
    document_text: str = Field(default="", description="Free text to seed salient issues (action='seed_from_text')")
    output_format: Literal["json", "text"] = "json"


class HRDDTool(BaseTool):
    name = "hrdd_assess"
    description = (
        "Human-rights & value-chain due diligence (HRDD), aligned to the UN "
        "Guiding Principles (Protect/Respect/Remedy), the OECD Due Diligence "
        "Guidance 6-step cycle, and EU CSDDD (as amended by Omnibus I). "
        "Prioritises salient human-rights issues by severity × likelihood (with "
        "gross-risk escalation for forced/child labour & modern slavery), maps "
        "them across value-chain tiers, scores the grievance mechanism against "
        "UNGP Principle 31, tracks remediation, and returns OECD step coverage + "
        "a CSDDD readiness band. Actions: 'assess' (structured inputs), "
        "'seed_from_text' (first-pass salient issues from a document)."
    )
    input_model = HRDDToolInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, HRDDToolInput) else HRDDToolInput.model_validate(arguments)

        if args.action == "seed_from_text":
            if not args.document_text.strip():
                return ToolResult(output="document_text is required for seed_from_text", is_error=True)
            issues = seed_salient_issues_from_text(args.document_text)
            payload = {
                "seeded_salient_issues": [i.model_dump(mode="json") for i in issues],
                "count": len(issues),
                "note": "First-pass keyword seeding — validate severity/likelihood with stakeholder consultation, then re-run action='assess'.",
            }
            return _ok(payload)

        try:
            issues = [SalientIssue.model_validate(i) for i in args.salient_issues]
            grievance = GrievanceMechanism.model_validate(args.grievance) if args.grievance else GrievanceMechanism()
            cases = [RemediationCase.model_validate(c) for c in args.remediation_cases]
        except Exception as e:  # noqa: BLE001
            return ToolResult(output=f"Invalid HRDD input: {e}", is_error=True)

        # If no structured issues but text supplied, seed them.
        if not issues and args.document_text.strip():
            issues = seed_salient_issues_from_text(args.document_text)

        result = assess_hrdd(HRDDInput(
            company_name=args.company_name,
            sector=args.sector,
            geographies=args.geographies,
            salient_issues=issues,
            grievance=grievance,
            remediation_cases=cases,
            has_rbc_policy=args.has_rbc_policy,
            has_impact_identification=args.has_impact_identification,
            has_mitigation_plan=args.has_mitigation_plan,
            tracks_effectiveness=args.tracks_effectiveness,
            communicates_publicly=args.communicates_publicly,
        ))
        payload = result.model_dump(mode="json")
        if args.output_format == "text":
            return ToolResult(output=_text(result), metadata=payload)
        return _ok(payload)


def _text(r) -> str:  # noqa: ANN001
    lines = [
        f"HUMAN-RIGHTS DUE DILIGENCE — {r.company_name or 'company'}",
        "=" * 50,
        f"Overall maturity: {r.overall_maturity}",
        f"OECD 6-step coverage: {r.oecd_coverage_pct}%",
        f"Grievance effectiveness: {r.grievance_effectiveness_pct}%",
        f"Remediation: {r.remediation_remediated} closed / {r.remediation_open} open",
        f"CSDDD readiness: {r.csddd_readiness}",
        "",
        "SALIENT ISSUES (ranked):",
    ]
    for i in r.salient_issues_ranked:
        lines.append(f"  [{i.priority.upper()}] {i.name} ({i.category}, {i.value_chain_tier}) — salience {i.salience_score}")
    if r.findings:
        lines.append("")
        lines.append("FINDINGS:")
        for f in r.findings:
            lines.append(f"  - {f}")
    if r.recommendations:
        lines.append("")
        lines.append("RECOMMENDATIONS:")
        for rec in r.recommendations:
            lines.append(f"  - {rec}")
    return "\n".join(lines)


def _ok(payload: dict) -> ToolResult:
    return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)


__all__ = ["HRDDToolInput", "HRDDTool"]
