"""Tool: Generate an investee data-collection portal — v5 Track C2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.investee_portal import (
    PortalSection,
    build_investee_portal,
    default_portal_sections,
    portal_schema,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class InvesteePortalInput(BaseModel):
    action: Literal["generate", "schema"] = "generate"
    fund_name: str = ""
    company_name: str = ""
    include_pai: bool = True
    sections: list[dict] = Field(
        default_factory=list,
        description="Optional custom PortalSection list; empty uses the default questionnaire",
    )
    theme: Literal["", "dark"] = ""
    output_path: str = Field(default="", description="Optional path to save the HTML portal")


class InvesteePortalTool(BaseTool):
    name = "investee_portal"
    description = (
        "Generate a self-contained, offline, single-file HTML data-collection portal "
        "to send to an investee. Guided questionnaire with plain-language framing, a "
        "'why we need this' rationale on every field, client-side validation, a "
        "progress bar, WCAG 2.2 AA structure, and local JSON export (no server). "
        "SFDR PAI indicators are translated into plain language. Actions: 'generate' "
        "(HTML portal), 'schema' (machine-readable question schema)."
    )
    input_model = InvesteePortalInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, InvesteePortalInput) else InvesteePortalInput.model_validate(arguments)
        return not args.output_path

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, InvesteePortalInput) else InvesteePortalInput.model_validate(arguments)

        custom_sections = None
        if args.sections:
            try:
                custom_sections = [PortalSection.model_validate(s) for s in args.sections]
            except Exception as e:  # noqa: BLE001
                return ToolResult(output=f"Invalid sections: {e}", is_error=True)

        if args.action == "schema":
            secs = custom_sections if custom_sections is not None else default_portal_sections(args.include_pai)
            payload = portal_schema(secs)
            return ToolResult(output=json.dumps(payload, indent=2, default=str), metadata=payload)

        secs = custom_sections if custom_sections is not None else default_portal_sections(args.include_pai)
        html_doc = build_investee_portal(
            fund_name=args.fund_name,
            company_name=args.company_name,
            sections=secs,
            theme=args.theme,
        )

        if args.output_path:
            path = Path(args.output_path)
            if not path.is_absolute():
                path = context.cwd / path
            if not path.suffix:
                path = path.with_suffix(".html")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html_doc, encoding="utf-8")
            return ToolResult(
                output=f"Investee portal saved to: {path}\nQuestions: {portal_schema(secs)['question_count']}",
                metadata={"output_path": str(path), "format": "html"},
            )

        return ToolResult(
            output=(
                f"Investee portal generated ({len(html_doc)} chars, "
                f"{portal_schema(secs)['question_count']} questions). "
                "Pass output_path to save the HTML file; full HTML in metadata['html']."
            ),
            metadata={"format": "html", "html": html_doc, "html_length": len(html_doc)},
        )


__all__ = ["InvesteePortalInput", "InvesteePortalTool"]
