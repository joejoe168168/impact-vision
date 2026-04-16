"""Tool: Impact Due Diligence checklist -- surface relevant DD questions."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.dd_checklist import (
    analyze_document_coverage,
    load_checklist,
    select_questions_for_document,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class DdChecklistInput(BaseModel):
    action: Literal["list", "analyze", "suggest"] = Field(
        description=(
            "'list': show all DD questions (optionally filtered by category). "
            "'analyze': check which questions are addressed in a document. "
            "'suggest': recommend the most important unanswered questions for a document."
        )
    )
    document_text: str = Field(
        default="",
        description="Text content from a pitch deck or investment memo (for 'analyze' and 'suggest')",
    )
    file_path: str = Field(
        default="",
        description="Path to a PDF file to extract text from (alternative to document_text)",
    )
    categories: list[str] = Field(
        default_factory=list,
        description=(
            "Filter by categories: impact_thesis, theory_of_change, what_outcomes, "
            "who_stakeholders, how_much_scale, contribution, risk, measurement_systems, "
            "governance_esg, sdg_alignment, negative_impact, exit_sustainability, "
            "financial_sustainability, team_capability, market_context, product_design, "
            "supply_chain, stakeholder_voice, investor_alignment, "
            "sector_fintech, sector_health, sector_agriculture, sector_energy, sector_education"
        ),
    )
    max_questions: int = Field(
        default=15, ge=1, le=50,
        description="Max questions to return (for 'suggest')",
    )
    priority: Literal["", "high", "medium", "low"] = Field(
        default="",
        description="Filter by priority: 'high', 'medium', or 'low'",
    )


class DdChecklistTool(BaseTool):
    name = "dd_checklist"
    description = (
        "Impact Due Diligence checklist with 96 questions across 24 categories based on GIIN, "
        "PCV, Seraf, IMP, AFME frameworks + sector-specific (fintech, health, agri, energy, education). "
        "Includes NESTA evidence strength scoring (1-5). Actions:\n"
        "- 'list': Browse all DD questions, optionally filtered by category or priority.\n"
        "- 'analyze': Check a pitch deck/memo text to see which questions are already addressed "
        "(with evidence levels) and which are gaps.\n"
        "- 'suggest': Given a document, recommend the most important unanswered DD questions "
        "the LLM should ask the investment team. Auto-includes sector-relevant questions.\n"
    )
    input_model = DdChecklistInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, DdChecklistInput) else DdChecklistInput.model_validate(arguments)

        text = args.document_text
        if not text and args.file_path:
            text = _extract_text(args.file_path, context)

        if args.action == "list":
            return self._handle_list(args)
        elif args.action == "analyze":
            if not text:
                return ToolResult(
                    output="Provide document_text or file_path to analyze.",
                    is_error=True,
                )
            return self._handle_analyze(text, args)
        elif args.action == "suggest":
            if not text:
                return ToolResult(
                    output="Provide document_text or file_path to suggest questions for.",
                    is_error=True,
                )
            return self._handle_suggest(text, args)
        else:
            return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

    def _handle_list(self, args: DdChecklistInput) -> ToolResult:
        questions = load_checklist()
        if args.categories:
            cat_set = set(args.categories)
            questions = [q for q in questions if q.category in cat_set]
        if args.priority:
            questions = [q for q in questions if q.priority == args.priority]

        if not questions:
            return ToolResult(output="No questions match the filter criteria.")

        lines = [f"Impact DD Checklist ({len(questions)} questions):\n"]
        current_cat = ""
        for q in questions:
            if q.category != current_cat:
                current_cat = q.category
                lines.append(f"\n--- {current_cat.upper().replace('_', ' ')} ---")
            dim_tag = f" [{q.dimension}]" if q.dimension else ""
            lines.append(f"  [{q.priority.upper()[0]}] {q.id}: {q.question}{dim_tag}")
            if q.follow_up:
                lines.append(f"       Follow-up: {q.follow_up}")

        return ToolResult(output="\n".join(lines))

    def _handle_analyze(self, text: str, args: DdChecklistInput) -> ToolResult:
        result = analyze_document_coverage(
            text, categories=args.categories or None
        )

        ev_str = f" | Avg Evidence Level: {result.avg_evidence_level:.1f}/5" if result.avg_evidence_level else ""
        lines = [
            "DD Checklist Coverage Analysis",
            "=" * 50,
            f"Total questions: {result.total_questions}",
            f"Addressed: {len(result.addressed)} | Unanswered: {len(result.unanswered)}",
            f"Coverage: {result.coverage_pct}%{ev_str}",
            "",
        ]

        if result.addressed:
            lines.append("ADDRESSED (evidence found in document):")
            lines.append("-" * 40)
            for match in sorted(result.addressed, key=lambda m: -m.confidence):
                q = match.question
                ev_badge = f"[Ev.{match.evidence_level}]" if match.evidence_level else ""
                lines.append(f"  {q.id}: {q.question} {ev_badge}")
                lines.append(f"    Confidence: {match.confidence:.0%} | Keywords: {', '.join(match.matched_keywords[:5])}")
                if match.evidence_label:
                    lines.append(f"    Evidence level: {match.evidence_label}")
                if match.relevant_text_snippets:
                    lines.append(f"    Excerpt: \"{match.relevant_text_snippets[0][:150]}...\"")
                lines.append("")

        if result.high_priority_gaps:
            lines.append("HIGH-PRIORITY GAPS (not addressed):")
            lines.append("-" * 40)
            for q in result.high_priority_gaps:
                dim_tag = f" [{q.dimension}]" if q.dimension else ""
                lines.append(f"  {q.id}: {q.question}{dim_tag}")
                if q.follow_up:
                    lines.append(f"    Follow-up: {q.follow_up}")
            lines.append("")

        if result.unanswered:
            other_gaps = [q for q in result.unanswered if q.priority != "high"]
            if other_gaps:
                lines.append(f"OTHER GAPS ({len(other_gaps)} questions):")
                for q in other_gaps[:10]:
                    lines.append(f"  {q.id}: {q.question}")

        return ToolResult(
            output="\n".join(lines),
            metadata={
                "coverage_pct": result.coverage_pct,
                "addressed_count": len(result.addressed),
                "unanswered_count": len(result.unanswered),
                "high_priority_gaps": len(result.high_priority_gaps),
            },
        )

    def _handle_suggest(self, text: str, args: DdChecklistInput) -> ToolResult:
        suggested = select_questions_for_document(
            text,
            max_questions=args.max_questions,
            focus_categories=args.categories or None,
        )

        if not suggested:
            return ToolResult(output="All DD questions appear to be addressed in the document!")

        lines = [
            f"Recommended DD Questions ({len(suggested)} questions)",
            "=" * 50,
            "These questions are NOT addressed in the document and should be asked:",
            "",
        ]

        for i, q in enumerate(suggested, 1):
            priority_marker = {"high": "!!!", "medium": "!!", "low": "!"}.get(q.priority, "")
            dim_tag = f" [{q.dimension}]" if q.dimension else ""
            lines.append(f"{i}. {priority_marker} {q.question}{dim_tag}")
            lines.append(f"   Category: {q.category} | Phase: {q.phase}")
            if q.follow_up:
                lines.append(f"   Follow-up: {q.follow_up}")
            lines.append("")

        return ToolResult(output="\n".join(lines))


def _extract_text(file_path: str, context: ToolExecutionContext) -> str:
    """Extract text from a PDF file."""
    path = Path(file_path)
    if not path.is_absolute():
        path = context.cwd / path

    if not path.exists():
        return ""

    if path.suffix.lower() == ".pdf":
        try:
            import pymupdf
            doc = pymupdf.open(str(path))
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        except Exception:
            return ""
    elif path.suffix.lower() in (".txt", ".md", ".rst"):
        return path.read_text(encoding="utf-8", errors="replace")
    elif path.suffix.lower() == ".json":
        return path.read_text(encoding="utf-8", errors="replace")
    return ""
