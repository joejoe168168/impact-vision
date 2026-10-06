"""Tool: one-call deal assessment (v7 W1.3).

Runs the whole deal-screening chain — claim extraction, IRIS+ mapping, 5D,
SDG, gap analysis, DD coverage, greenwashing and the IC gate — on a pitch deck
or memo, saves the result and returns an ``assessment_id``. Downstream tools
(impact_report, sdg_mapper, five_dimension_assess, gap_analysis,
greenwashing_detect) accept that id instead of re-typed company fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class AssessDealInput(BaseModel):
    file_path: str = Field(default="", description="Pitch deck or memo to assess (.pdf, .txt, .md)")
    text: str = Field(default="", description="Document text, if no file_path")
    company_name: str = Field(default="", description="Company name (inferred if empty)")
    sector: str = Field(default="", description="Sector (inferred if empty), e.g. 'agriculture'")
    geography: str = Field(default="", description="Country or region (inferred if empty)")
    audience: Literal["full", "ic", "lp", "regulator", "public"] = Field(
        default="full", description="Audience for the written impact report"
    )
    output_dir: str = Field(
        default="",
        description=(
            "If set, write the impact report, IC memo, DD report, DD questionnaire "
            "and JSON summary to this folder"
        ),
    )
    save: bool = Field(
        default=True, description="Save the assessment and return an assessment_id"
    )


class AssessDealTool(BaseTool):
    name = "assess_deal"
    description = (
        "Start here for a pitch deck or investment memo. One call runs the full impact "
        "screen (claims and evidence, IRIS+ metrics, 5 Dimensions, SDGs, gap analysis, "
        "DD coverage, greenwashing, IC gate) offline and returns a summary plus an "
        "assessment_id. Pass that assessment_id to impact_report, sdg_mapper, "
        "five_dimension_assess, gap_analysis or greenwashing_detect instead of re-typing "
        "company details. Set output_dir to also write the HTML reports."
    )
    input_model = AssessDealInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, AssessDealInput) else AssessDealInput.model_validate(arguments)
        return not args.output_dir

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        from openharness.impact.pipeline import (
            assess_document,
            format_summary,
            read_document,
            save_bundle,
            write_deliverables,
        )

        args = arguments if isinstance(arguments, AssessDealInput) else AssessDealInput.model_validate(arguments)
        source_label = "Pasted text"
        text = args.text
        if args.file_path:
            path = Path(args.file_path).expanduser()
            if not path.is_absolute():
                path = context.cwd / path
            try:
                text = read_document(path)
            except (FileNotFoundError, ValueError, ImportError) as exc:
                return ToolResult(output=str(exc), is_error=True)
            source_label = path.name
        if not text.strip():
            return ToolResult(output="Provide file_path or text to assess.", is_error=True)

        try:
            bundle = assess_document(
                text,
                name=args.company_name,
                sector=args.sector,
                geography=args.geography,
                audience=args.audience,
                source_label=source_label,
            )
        except ValueError as exc:
            return ToolResult(output=str(exc), is_error=True)

        files: list[Path] = []
        if args.output_dir:
            out = Path(args.output_dir).expanduser()
            if not out.is_absolute():
                out = context.cwd / out
            files = write_deliverables(bundle, out)

        summary = bundle.summary()
        assessment_id = ""
        if args.save:
            assessment_id = save_bundle(bundle, source_label=source_label)

        lines = [format_summary(bundle)]
        if assessment_id:
            lines.append(f"\nassessment_id: {assessment_id}")
        if files:
            lines.append("\nFiles written:")
            lines.extend(f"  {f}" for f in files)
        lines.append(
            "\nNext: pass assessment_id to impact_report (audience='lp' for an LP version), "
            "greenwashing_detect, sdg_mapper, five_dimension_assess or gap_analysis; "
            "use dd_checklist action='suggest' for the questions to ask the founders."
        )
        lines.append("\nJSON: " + json.dumps({**summary, "assessment_id": assessment_id}, default=str))
        return ToolResult(output="\n".join(lines))
