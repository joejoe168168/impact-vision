"""Tool: Pre-verification preparation for BlueMark/IFC OPIM verification.

Organizes evidence, identifies gaps, and generates a verification readiness
checklist aligned with IFC Operating Principles for Impact Management.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.models import Company
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sdg_goals
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


IFC_OPIM_PRINCIPLES = [
    {"id": 1, "name": "Strategic Intent", "requirement": "Define strategic impact objectives consistent with the investment strategy"},
    {"id": 2, "name": "Origination & Structuring", "requirement": "Manage strategic impact on a portfolio basis with each investment contributing to the intent"},
    {"id": 3, "name": "Portfolio Management", "requirement": "Establish the Manager's contribution to the achievement of impact"},
    {"id": 4, "name": "Impact at Entry", "requirement": "Assess expected impact of each investment at entry based on a systematic approach"},
    {"id": 5, "name": "Impact at Exit", "requirement": "Assess, address, monitor, and manage potential negative impacts"},
    {"id": 6, "name": "Monitoring", "requirement": "Monitor the progress of each investment in achieving impact against expectations and respond appropriately"},
    {"id": 7, "name": "Exit Considerations", "requirement": "Conduct exits considering the effect on sustained impact"},
    {"id": 8, "name": "Review & Feedback", "requirement": "Review, document, and improve decisions and processes based on impact and lessons learned"},
    {"id": 9, "name": "Independent Verification", "requirement": "Publicly disclose alignment with Principles and arrange for independent verification"},
]


class VerificationPrepInput(BaseModel):
    action: Literal["readiness_check", "evidence_map", "ifc_alignment"] = Field(
        default="readiness_check",
        description=(
            "'readiness_check': Overall verification readiness assessment. "
            "'evidence_map': Map available evidence to verification requirements. "
            "'ifc_alignment': Check alignment with IFC Operating Principles."
        ),
    )
    company_name: str = Field(default="", description="Company name")
    company_description: str = Field(default="", description="Company description")
    sector: str = Field(default="")
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    impact_themes: list[str] = Field(default_factory=list)
    has_theory_of_change: bool = Field(default=False, description="Whether a ToC document exists")
    has_impact_policy: bool = Field(default=False, description="Whether an impact/ESG policy exists")
    has_external_audit: bool = Field(default=False, description="Whether external audit has been conducted")
    verification_target: str = Field(
        default="bluemark",
        description="Target verifier: 'bluemark', 'ifc_opim', 'general'",
    )


class VerificationPrepTool(BaseTool):
    name = "verification_prep"
    description = (
        "Prepare for impact verification (BlueMark, IFC OPIM). "
        "Organizes evidence, identifies gaps, and generates readiness checklists."
    )
    input_model = VerificationPrepInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, VerificationPrepInput)
            else VerificationPrepInput.model_validate(arguments)
        )

        reported, _ = normalize_metric_map(args.reported_metrics)
        sdgs, _ = normalize_sdg_goals(args.sdg_claims)
        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=args.sector,
            impact_themes=infer_themes(f"{args.company_description} {args.sector}", args.impact_themes),
            reported_metrics=reported,
            sdg_claims=sdgs,
        )

        if args.action == "ifc_alignment":
            return self._ifc_alignment(args, company)
        elif args.action == "evidence_map":
            return self._evidence_map(args, company)
        else:
            return self._readiness_check(args, company)

    def _readiness_check(self, args: VerificationPrepInput, company: Company) -> ToolResult:
        lines = [
            "VERIFICATION READINESS CHECK",
            "=" * 50,
            f"Company: {company.name}",
            f"Target verifier: {args.verification_target}",
            "",
        ]

        score = 0
        checklist: list[tuple[str, bool, str]] = []

        has_metrics = len(company.reported_metrics) >= 3
        checklist.append(("Impact metrics reported (>=3)", has_metrics, f"{len(company.reported_metrics)} metrics"))
        if has_metrics:
            score += 15

        has_sdgs = len(company.sdg_claims) >= 1
        checklist.append(("SDG alignment documented", has_sdgs, f"{len(company.sdg_claims)} SDGs claimed"))
        if has_sdgs:
            score += 10

        checklist.append(("Theory of Change documented", args.has_theory_of_change, ""))
        if args.has_theory_of_change:
            score += 20

        checklist.append(("Impact/ESG policy exists", args.has_impact_policy, ""))
        if args.has_impact_policy:
            score += 15

        checklist.append(("External audit completed", args.has_external_audit, ""))
        if args.has_external_audit:
            score += 20

        has_description = len(company.description) > 50
        checklist.append(("Impact thesis articulated", has_description, ""))
        if has_description:
            score += 10

        has_themes = len(company.impact_themes) >= 1
        checklist.append(("Impact themes defined", has_themes, f"{len(company.impact_themes)} themes"))
        if has_themes:
            score += 10

        score = min(100, score)
        readiness = "Ready" if score >= 70 else "Partially ready" if score >= 40 else "Not ready"

        lines.append(f"Readiness Score: {score}/100 ({readiness})")
        lines.append("")
        lines.append("Checklist:")
        for label, done, note in checklist:
            status = "✅" if done else "❌"
            note_str = f" — {note}" if note else ""
            lines.append(f"  {status} {label}{note_str}")

        lines.append("")
        gaps = [label for label, done, _ in checklist if not done]
        if gaps:
            lines.append("Priority Actions:")
            for g in gaps:
                lines.append(f"  → Prepare: {g}")

        return ToolResult(
            output="\n".join(lines),
            metadata={"readiness_score": score, "readiness": readiness},
        )

    def _evidence_map(self, args: VerificationPrepInput, company: Company) -> ToolResult:
        evidence_categories = [
            ("Impact Strategy", ["impact_thesis", "theory_of_change", "sdg_alignment"]),
            ("Measurement System", ["iris_metrics", "data_collection", "reporting_cadence"]),
            ("Performance Data", ["metric_values", "trend_data", "targets"]),
            ("Governance", ["impact_policy", "team_capabilities", "board_oversight"]),
            ("Stakeholder Voice", ["beneficiary_feedback", "stakeholder_engagement"]),
            ("Risk Management", ["impact_risk_assessment", "exclusion_screening"]),
        ]

        lines = [
            "EVIDENCE MAP FOR VERIFICATION",
            "=" * 50,
            f"Company: {company.name}",
            "",
        ]

        available_count = 0
        total_items = 0
        for category, items in evidence_categories:
            lines.append(f"\n{category}:")
            for item in items:
                total_items += 1
                available = self._check_evidence(item, args, company)
                status = "✅ Available" if available else "❌ Missing"
                if available:
                    available_count += 1
                lines.append(f"  {status}: {item.replace('_', ' ').title()}")

        completeness = round(available_count / total_items * 100) if total_items else 0
        lines.insert(3, f"Evidence completeness: {completeness}% ({available_count}/{total_items})")

        return ToolResult(
            output="\n".join(lines),
            metadata={"completeness": completeness},
        )

    def _check_evidence(self, item: str, args: VerificationPrepInput, company: Company) -> bool:
        checks = {
            "impact_thesis": len(company.description) > 50,
            "theory_of_change": args.has_theory_of_change,
            "sdg_alignment": len(company.sdg_claims) > 0,
            "iris_metrics": len(company.reported_metrics) > 0,
            "data_collection": len(company.reported_metrics) >= 3,
            "reporting_cadence": bool(company.reporting_period),
            "metric_values": len(company.reported_metrics) >= 1,
            "trend_data": len(company.metric_history) > 0,
            "targets": len(company.impact_targets) > 0,
            "impact_policy": args.has_impact_policy,
            "team_capabilities": False,
            "board_oversight": False,
            "beneficiary_feedback": company.beneficiary_feedback is not None,
            "stakeholder_engagement": len(company.impact_themes) > 0,
            "impact_risk_assessment": False,
            "exclusion_screening": len(company.exclusion_flags) > 0 or True,
        }
        return checks.get(item, False)

    def _ifc_alignment(self, args: VerificationPrepInput, company: Company) -> ToolResult:
        lines = [
            "IFC OPERATING PRINCIPLES FOR IMPACT MANAGEMENT — ALIGNMENT CHECK",
            "=" * 60,
            f"Company: {company.name}",
            "",
        ]

        aligned_count = 0
        for p in IFC_OPIM_PRINCIPLES:
            status, note = self._assess_principle(p["id"], args, company)
            icon = "✅" if status else "⚠️"
            if status:
                aligned_count += 1
            lines.append(f"  {icon} Principle {p['id']}: {p['name']}")
            lines.append(f"     {p['requirement']}")
            if note:
                lines.append(f"     → {note}")
            lines.append("")

        score = round(aligned_count / len(IFC_OPIM_PRINCIPLES) * 100)
        lines.insert(3, f"Alignment: {aligned_count}/{len(IFC_OPIM_PRINCIPLES)} principles ({score}%)\n")

        return ToolResult(
            output="\n".join(lines),
            metadata={"alignment_score": score, "aligned_count": aligned_count},
        )

    def _assess_principle(self, principle_id: int, args: VerificationPrepInput, company: Company) -> tuple[bool, str]:
        if principle_id == 1:
            ok = len(company.description) > 50 and len(company.sdg_claims) > 0
            return ok, "Impact thesis and SDG alignment documented" if ok else "Need documented impact thesis + SDG targets"
        elif principle_id == 2:
            ok = len(company.impact_themes) > 0
            return ok, "Impact themes defined for portfolio management" if ok else "Define impact themes per investment"
        elif principle_id == 3:
            ok = len(company.reported_metrics) >= 3
            return ok, f"{len(company.reported_metrics)} metrics demonstrate contribution" if ok else "Report >=3 IRIS+ metrics"
        elif principle_id == 4:
            ok = len(company.reported_metrics) >= 1 and len(company.sdg_claims) >= 1
            return ok, "Entry assessment data available" if ok else "Need pre-investment impact assessment"
        elif principle_id == 5:
            return len(company.exclusion_flags) == 0, "No exclusion flags" if not company.exclusion_flags else f"Flags: {', '.join(company.exclusion_flags[:3])}"
        elif principle_id == 6:
            ok = len(company.reported_metrics) >= 3
            return ok, "Active monitoring via IRIS+ metrics" if ok else "Establish ongoing metric monitoring"
        elif principle_id == 7:
            return False, "Exit impact sustainability not yet assessed (future feature)"
        elif principle_id == 8:
            ok = args.has_impact_policy
            return ok, "Impact policy supports review process" if ok else "Create formal impact review process"
        elif principle_id == 9:
            ok = args.has_external_audit
            return ok, "External verification completed" if ok else "Arrange independent verification (e.g. BlueMark)"
        return False, ""
