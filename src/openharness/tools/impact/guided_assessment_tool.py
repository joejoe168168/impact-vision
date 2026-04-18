"""Tool: Guided assessment workflow with progressive data collection.

Provides a structured step-by-step assessment process with different
depth levels for screening, DD, and monitoring stages.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.storage import get_assessment_store
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


_ASSESSMENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "screening": {
        "label": "Screening Assessment",
        "description": "Quick initial assessment for deal sourcing (15-20 minutes)",
        "required_fields": ["company_name", "sector", "geography", "description"],
        "optional_fields": ["impact_themes", "sdg_claims"],
        "analyses": ["five_dimensions", "sdg_alignment"],
        "depth": "basic",
        "steps": [
            {"id": "basic_info", "question": "What is the company name, sector, and geography?", "fields": ["company_name", "sector", "geography"]},
            {"id": "description", "question": "Briefly describe what the company does and its impact thesis.", "fields": ["description"]},
            {"id": "sdg_claims", "question": "Which SDGs does the company claim to address? (list numbers)", "fields": ["sdg_claims"]},
            {"id": "quick_assessment", "question": "Running quick assessment...", "fields": [], "auto": True},
        ],
    },
    "dd": {
        "label": "Due Diligence Assessment",
        "description": "Full assessment for investment decision (1-2 hours)",
        "required_fields": ["company_name", "sector", "geography", "description", "impact_themes"],
        "optional_fields": ["reported_metrics", "sdg_claims", "impact_targets", "beneficiary_feedback"],
        "analyses": ["five_dimensions", "sdg_alignment", "gap_analysis", "greenwashing", "dd_checklist"],
        "depth": "comprehensive",
        "steps": [
            {"id": "basic_info", "question": "Company name, sector, geography, and founding year?", "fields": ["company_name", "sector", "geography", "founded_year"]},
            {"id": "description", "question": "Company description and core impact thesis.", "fields": ["description"]},
            {"id": "themes", "question": "What are the company's impact themes? (e.g., financial inclusion, clean energy)", "fields": ["impact_themes"]},
            {"id": "sdg", "question": "Which SDGs does the company target? Any specific targets (e.g., 1.1, 7.2)?", "fields": ["sdg_claims"]},
            {"id": "metrics", "question": "What IRIS+ metrics does the company currently report?", "fields": ["reported_metrics"]},
            {"id": "targets", "question": "Does the company have specific impact targets? (metric ID, target value, date)", "fields": ["impact_targets"]},
            {"id": "beneficiaries", "question": "Any beneficiary feedback data? (satisfaction, NPS, sample size)", "fields": ["beneficiary_feedback"]},
            {"id": "full_assessment", "question": "Running full assessment...", "fields": [], "auto": True},
        ],
    },
    "monitoring": {
        "label": "Monitoring Review",
        "description": "Periodic monitoring update for invested companies (30-45 minutes)",
        "required_fields": ["company_name"],
        "optional_fields": ["reported_metrics", "impact_targets", "metric_history"],
        "analyses": ["five_dimensions", "sdg_alignment", "target_tracking", "comparison"],
        "depth": "update",
        "steps": [
            {"id": "company", "question": "Which company is this monitoring review for?", "fields": ["company_name"]},
            {"id": "new_metrics", "question": "Any new or updated metric values to record?", "fields": ["reported_metrics"]},
            {"id": "target_update", "question": "Any updates on impact target progress?", "fields": ["impact_targets"]},
            {"id": "changes", "question": "Any significant changes since last review? (strategy, operations, team)", "fields": ["notes"]},
            {"id": "reassess", "question": "Running re-assessment and comparison...", "fields": [], "auto": True},
        ],
    },
}


class GuidedAssessmentInput(BaseModel):
    action: Literal[
        "start", "status", "next_step", "submit_data", "list_templates",
    ] = Field(description="Workflow action")
    template: Literal["screening", "dd", "monitoring"] = Field(
        default="screening",
        description="Assessment template depth",
    )
    company_name: str = ""
    step_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Data for the current step (field_name: value pairs)",
    )
    session_id: str = Field(default="", description="Session ID for progressive collection")


class GuidedAssessmentTool(BaseTool):
    name = "guided_assessment"
    description = (
        "Structured step-by-step impact assessment workflow. Choose a template "
        "(screening/dd/monitoring) and follow the guided steps to collect data "
        "and run the appropriate analyses. Supports progressive data collection."
    )
    input_model = GuidedAssessmentInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, GuidedAssessmentInput) else GuidedAssessmentInput.model_validate(arguments)
        return args.action in ("status", "next_step", "list_templates")

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, GuidedAssessmentInput) else GuidedAssessmentInput.model_validate(arguments)

        if args.action == "list_templates":
            return self._list_templates()
        elif args.action == "start":
            return self._start_assessment(args)
        elif args.action == "status":
            return self._get_status(args)
        elif args.action == "next_step":
            return self._next_step(args)
        elif args.action == "submit_data":
            return self._submit_data(args)
        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

    def _list_templates(self) -> ToolResult:
        lines = ["ASSESSMENT TEMPLATES", "=" * 60, ""]
        for key, tmpl in _ASSESSMENT_TEMPLATES.items():
            lines.append(f"  {key.upper()}: {tmpl['label']}")
            lines.append(f"    {tmpl['description']}")
            lines.append(f"    Required: {', '.join(tmpl['required_fields'])}")
            lines.append(f"    Analyses: {', '.join(tmpl['analyses'])}")
            lines.append(f"    Steps: {len(tmpl['steps'])}")
            lines.append("")
        return ToolResult(output="\n".join(lines))

    def _start_assessment(self, args: GuidedAssessmentInput) -> ToolResult:
        template = _ASSESSMENT_TEMPLATES.get(args.template)
        if not template:
            return ToolResult(output=f"Unknown template: {args.template}", is_error=True)

        steps = template["steps"]
        first_step = steps[0]

        lines = [
            f"STARTING: {template['label']}",
            f"({template['description']})",
            "=" * 60, "",
            f"This assessment has {len(steps)} steps.",
            "",
            f"STEP 1/{len(steps)}: {first_step['question']}",
            f"Fields to provide: {', '.join(first_step['fields'])}",
            "",
            "Use submit_data action with step_data to provide the information.",
        ]

        store = get_assessment_store()
        if args.company_name:
            prev = store.get_assessment(args.company_name)
            if prev:
                lines.append(f"\nNote: Previous assessment found for {args.company_name}.")
                lines.append("Data from the previous assessment can be reused.")

        return ToolResult(
            output="\n".join(lines),
            metadata={
                "template": args.template,
                "total_steps": len(steps),
                "current_step": 0,
            },
        )

    def _get_status(self, args: GuidedAssessmentInput) -> ToolResult:
        template = _ASSESSMENT_TEMPLATES.get(args.template, {})
        if not template:
            return ToolResult(output=f"Unknown template: {args.template}")

        store = get_assessment_store()
        collected = {}
        if args.company_name:
            prev = store.get_assessment(args.company_name)
            if prev:
                company = prev.get("company", {})
                for field in template.get("required_fields", []) + template.get("optional_fields", []):
                    val = company.get(field)
                    if val:
                        collected[field] = "✓ available"

        required = template.get("required_fields", [])
        optional = template.get("optional_fields", [])

        lines = [
            f"ASSESSMENT STATUS: {template.get('label', args.template)}",
            f"Company: {args.company_name or 'Not specified'}",
            "=" * 60, "",
            "REQUIRED DATA:",
        ]
        for f in required:
            status = collected.get(f, "✗ missing")
            lines.append(f"  {f:25s} {status}")
        lines.append("\nOPTIONAL DATA:")
        for f in optional:
            status = collected.get(f, "○ not provided")
            lines.append(f"  {f:25s} {status}")

        missing = [f for f in required if f not in collected]
        if missing:
            lines.append(f"\n⚠ Missing required: {', '.join(missing)}")
        else:
            lines.append("\n✓ All required data collected. Ready to run assessment.")

        return ToolResult(output="\n".join(lines))

    def _next_step(self, args: GuidedAssessmentInput) -> ToolResult:
        template = _ASSESSMENT_TEMPLATES.get(args.template, {})
        steps = template.get("steps", [])

        store = get_assessment_store()
        collected_fields: set[str] = set()
        if args.company_name:
            prev = store.get_assessment(args.company_name)
            if prev:
                company = prev.get("company", {})
                for field in company:
                    if company[field]:
                        collected_fields.add(field)

        for i, step in enumerate(steps):
            step_fields = set(step.get("fields", []))
            if step.get("auto"):
                continue
            if not step_fields or not step_fields.issubset(collected_fields):
                missing = step_fields - collected_fields
                return ToolResult(
                    output=f"STEP {i+1}/{len(steps)}: {step['question']}\nFields needed: {', '.join(missing)}",
                    metadata={"step_index": i, "fields": list(missing)},
                )

        return ToolResult(
            output="All data steps complete. Ready to run the assessment.\n"
                   "Use the impact_report or pitch_deck_analyze tool to generate the full assessment.",
        )

    def _submit_data(self, args: GuidedAssessmentInput) -> ToolResult:
        if not args.step_data:
            return ToolResult(output="No data provided in step_data", is_error=True)
        if not args.company_name:
            return ToolResult(output="company_name is required to persist step data", is_error=True)

        store = get_assessment_store()
        prev = store.get_assessment(args.company_name)
        company_data: dict = prev.get("company", {}) if prev else {}

        for field, value in args.step_data.items():
            company_data[field] = value

        store.save_assessment(args.company_name, company_data)

        lines = ["DATA RECEIVED:", ""]
        for field, value in args.step_data.items():
            display = str(value)[:80]
            lines.append(f"  {field}: {display}")

        lines.append("")
        lines.append("Data recorded. Call next_step to see what's needed next,")
        lines.append("or call status to see overall progress.")

        return ToolResult(
            output="\n".join(lines),
            metadata={"fields_submitted": list(args.step_data.keys())},
        )
