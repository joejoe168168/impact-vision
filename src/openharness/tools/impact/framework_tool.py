"""Tool: Multi-framework ESG/sustainability standards assessment.

Unified tool for SASB, GRI, TCFD/IFRS S2, SFDR PAI, EDCI, and UNPRI frameworks.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.tools.impact.common import normalize_metric_map, normalize_str_list
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class FrameworkInput(BaseModel):
    framework: Literal["sasb", "gri", "tcfd", "sfdr_pai", "edci", "unpri", "toc", "all"] = Field(
        description=(
            "Which framework to query. 'all' runs a quick scan across all frameworks."
        )
    )
    action: Literal["list", "match", "assess"] = Field(
        description=(
            "'list': Show the framework's standards/indicators. "
            "'match': Match a company to relevant topics (SASB/GRI). "
            "'assess': Assess coverage against a framework given company data."
        )
    )
    sector: str = Field(default="", description="Company sector/industry")
    description: str = Field(default="", description="Company description")
    themes: list[str] = Field(default_factory=list, description="Impact themes")
    reported_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="IRIS+ metric ID -> value (used for cross-reference matching)",
    )
    document_text: str = Field(
        default="",
        description="Text content from a document to analyze against the framework",
    )
    category: str = Field(
        default="",
        description="Filter by category within a framework (e.g., 'environment', 'social', 'economic')",
    )


class FrameworkTool(BaseTool):
    name = "framework_assess"
    description = (
        "Multi-framework ESG and sustainability standards tool. Supports:\n"
        "- **SASB**: Match company to industry-specific materiality topics (17 industries, 77+ topics)\n"
        "- **GRI**: Browse Universal + Topic Standards (200/300/400 series), match to relevant topics\n"
        "- **TCFD / IFRS S2**: Assess climate disclosure across 4 pillars (Governance, Strategy, Risk, Metrics)\n"
        "- **SFDR PAI**: Check coverage of 14 mandatory EU Principal Adverse Impact indicators\n"
        "- **EDCI**: Assess 17 core PE/VC ESG metrics (with IRIS+, GRI, SFDR cross-references)\n"
        "- **UNPRI**: Self-assess alignment with the 6 Principles for Responsible Investment\n"
        "- **ToC**: Theory of Change assessment using RS Group's Blended Value principles "
        "and GIIN IRIS+ ToC Checklist\n"
        "- **all**: Quick scan across all frameworks\n\n"
        "Actions: 'list' (browse), 'match' (find relevant topics), 'assess' (coverage analysis)"
    )
    input_model = FrameworkInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, FrameworkInput) else FrameworkInput.model_validate(arguments)
        args = FrameworkInput(
            **{
                **args.model_dump(),
                "themes": normalize_str_list(args.themes),
                "reported_metrics": normalize_metric_map(args.reported_metrics),
            }
        )

        if args.framework == "all" and args.action == "assess":
            return self._assess_all(args)
        if args.framework == "all" and args.action in ("list", "match"):
            return self._handle_all_list(args)

        handlers = {
            "sasb": self._handle_sasb,
            "gri": self._handle_gri,
            "tcfd": self._handle_tcfd,
            "sfdr_pai": self._handle_sfdr,
            "edci": self._handle_edci,
            "unpri": self._handle_unpri,
            "toc": self._handle_toc,
            "all": self._handle_all_list,
        }

        handler = handlers.get(args.framework)
        if not handler:
            return ToolResult(output=f"Unknown framework: {args.framework}", is_error=True)

        return handler(args)

    def _handle_sasb(self, args: FrameworkInput) -> ToolResult:
        from openharness.impact.frameworks.sasb import get_sasb_industries, match_sasb_industry

        if args.action == "list":
            industries = get_sasb_industries()
            lines = [f"SASB Standards ({len(industries)} industries):\n"]
            for std in industries:
                lines.append(f"  [{std.sics_code}] {std.industry} ({std.sector})")
                lines.append(f"    Topics: {', '.join(t.name for t in std.topics[:4])}")
                if len(std.topics) > 4:
                    lines.append(f"    ... and {len(std.topics) - 4} more")
            return ToolResult(output="\n".join(lines))

        if args.action == "match":
            matches = match_sasb_industry(args.sector, args.description, args.themes)
            if not matches:
                return ToolResult(output="No SASB industry matches found. Provide more sector/description detail.")
            lines = ["SASB Industry Matches:\n"]
            for std, score in matches:
                lines.append(f"  [{std.sics_code}] {std.industry} (score: {score})")
                lines.append(f"    Sector: {std.sector}")
                lines.append(f"    Material topics ({len(std.topics)}):")
                for t in std.topics:
                    iris = f" (IRIS+: {', '.join(t.iris_cross_refs)})" if t.iris_cross_refs else ""
                    lines.append(f"      - {t.name} [{t.dimension}]{iris}")
                    if t.description:
                        lines.append(f"        {t.description}")
                lines.append("")
            return ToolResult(output="\n".join(lines))

        if args.action == "assess":
            return self._handle_sasb(FrameworkInput(**{**args.model_dump(), "action": "match"}))

        return ToolResult(output=f"SASB does not support action: {args.action}", is_error=True)

    def _handle_gri(self, args: FrameworkInput) -> ToolResult:
        from openharness.impact.frameworks.gri import get_gri_standards, match_gri_topics

        if args.action == "list":
            series = args.category or None
            standards = get_gri_standards(series)
            lines = [f"GRI Standards ({len(standards)} standards):\n"]
            current_series = ""
            for std in standards:
                if std.series != current_series:
                    current_series = std.series
                    lines.append(f"\n--- {current_series.upper()} ---")
                lines.append(f"  {std.code}: {std.name}")
                lines.append(f"    Disclosures: {len(std.disclosures)}")
                if std.disclosures:
                    for d in std.disclosures[:3]:
                        iris = f" (IRIS+: {', '.join(d.iris_cross_refs)})" if d.iris_cross_refs else ""
                        lines.append(f"      {d.code}: {d.name}{iris}")
                    if len(std.disclosures) > 3:
                        lines.append(f"      ... and {len(std.disclosures) - 3} more")
            return ToolResult(output="\n".join(lines))

        if args.action in ("match", "assess"):
            matches = match_gri_topics(args.sector, args.description, args.themes)
            universals = get_gri_standards("universal")

            lines = ["GRI Topic Matching:\n"]
            lines.append("UNIVERSAL STANDARDS (always applicable):")
            for u in universals:
                lines.append(f"  {u.code}: {u.name} ({len(u.disclosures)} disclosures)")

            if matches:
                lines.append(f"\nMATERIAL TOPIC STANDARDS ({len(matches)} matched):")
                for std, score in matches:
                    lines.append(f"\n  {std.code}: {std.name} (relevance: {score})")
                    for d in std.disclosures[:5]:
                        iris = f" -> IRIS+: {', '.join(d.iris_cross_refs)}" if d.iris_cross_refs else ""
                        lines.append(f"    {d.code}: {d.name}{iris}")
            else:
                lines.append("\nNo material topics matched. Provide more sector/description detail.")

            return ToolResult(output="\n".join(lines))

        return ToolResult(output=f"GRI does not support action: {args.action}", is_error=True)

    def _handle_tcfd(self, args: FrameworkInput) -> ToolResult:
        from openharness.impact.frameworks.tcfd import assess_tcfd_alignment, get_tcfd_framework

        if args.action == "list":
            fw = get_tcfd_framework()
            lines = ["TCFD / IFRS S2 Climate Disclosure Framework:\n"]
            for pillar in fw.pillars:
                lines.append(f"\n  {pillar.name}")
                lines.append(f"    {pillar.description}")
                for disc in pillar.disclosures:
                    lines.append(f"    [{disc.code}] {disc.name}")
                    if disc.data_requirements:
                        lines.append(f"      Data needed: {', '.join(disc.data_requirements[:3])}")
            return ToolResult(output="\n".join(lines))

        if args.action in ("match", "assess"):
            result = assess_tcfd_alignment(args.description, args.reported_metrics, args.document_text)
            lines = [f"TCFD / IFRS S2 Assessment (Overall: {result['overall_coverage']}%)\n"]
            for pillar in result["pillars"]:
                bar = _bar(pillar["coverage_pct"])
                lines.append(f"  {pillar['name']}: {pillar['coverage_pct']}% {bar}")
                if pillar["addressed"]:
                    for a in pillar["addressed"]:
                        lines.append(f"    [OK] {a['code']}: {a['name']}")
                if pillar["gaps"]:
                    for g in pillar["gaps"]:
                        lines.append(f"    [GAP] {g['code']}: {g['name']}")
                        if g.get("data_requirements"):
                            lines.append(f"      Need: {', '.join(g['data_requirements'][:3])}")
            return ToolResult(output="\n".join(lines), metadata=result)

        return ToolResult(output=f"TCFD does not support action: {args.action}", is_error=True)

    def _handle_sfdr(self, args: FrameworkInput) -> ToolResult:
        from openharness.impact.frameworks.sfdr_pai import assess_sfdr_compliance, get_pai_indicators

        if args.action == "list":
            indicators = get_pai_indicators()
            lines = [f"SFDR Principal Adverse Impact Indicators ({len(indicators)} mandatory):\n"]
            current_cat = ""
            for ind in indicators:
                if ind.category != current_cat:
                    current_cat = ind.category
                    lines.append(f"\n--- {current_cat.upper()} ---")
                iris = f" (IRIS+: {', '.join(ind.iris_cross_refs)})" if ind.iris_cross_refs else ""
                lines.append(f"  PAI {ind.number}: {ind.name}{iris}")
                lines.append(f"    Metric: {ind.metric}")
                lines.append(f"    Data: {', '.join(ind.data_points[:3])}")
            return ToolResult(output="\n".join(lines))

        if args.action in ("match", "assess"):
            result = assess_sfdr_compliance(args.reported_metrics, args.description, args.document_text)
            lines = [f"SFDR PAI Compliance ({result['coverage_pct']}% | {result['addressed']}/{result['total']})\n"]
            for ind in result["indicators"]:
                status = "[OK]" if ind["addressed"] else "[GAP]"
                lines.append(f"  {status} PAI {ind['number']}: {ind['name']} ({ind['category']})")
                if ind["evidence"]:
                    lines.append(f"    Evidence: {', '.join(ind['evidence'][:3])}")
                if ind["data_points_needed"]:
                    lines.append(f"    Need: {', '.join(ind['data_points_needed'][:3])}")
            return ToolResult(output="\n".join(lines), metadata=result)

        return ToolResult(output=f"SFDR does not support action: {args.action}", is_error=True)

    def _handle_edci(self, args: FrameworkInput) -> ToolResult:
        from openharness.impact.frameworks.edci import assess_edci_coverage, get_edci_metrics

        if args.action == "list":
            cat = args.category or None
            metrics = get_edci_metrics(cat)
            lines = [f"EDCI Core PE/VC Metrics ({len(metrics)} metrics):\n"]
            current_cat = ""
            for m in metrics:
                if m.category != current_cat:
                    current_cat = m.category
                    lines.append(f"\n--- {current_cat.upper()} ---")
                iris = f" (IRIS+: {', '.join(m.iris_cross_refs)})" if m.iris_cross_refs else ""
                gri = f" (GRI: {', '.join(m.gri_cross_refs)})" if m.gri_cross_refs else ""
                lines.append(f"  {m.id}: {m.name} [{m.unit}]{iris}{gri}")
                lines.append(f"    {m.description}")
            return ToolResult(output="\n".join(lines))

        if args.action in ("match", "assess"):
            result = assess_edci_coverage(args.reported_metrics, args.description, args.document_text)
            lines = [f"EDCI Coverage ({result['coverage_pct']}% | {result['addressed']}/{result['total']})\n"]
            for cat_name, cat_data in result["by_category"].items():
                lines.append(f"  {cat_name.upper()}: {cat_data['coverage_pct']}% ({cat_data['addressed']}/{cat_data['total']})")
            lines.append("")
            for m in result["metrics"]:
                status = "[OK]" if m["addressed"] else "[GAP]"
                lines.append(f"  {status} {m['id']}: {m['name']}")
                if m["evidence"]:
                    lines.append(f"    Evidence: {', '.join(m['evidence'][:3])}")
                xrefs = m.get("cross_references", {})
                refs = []
                if xrefs.get("iris"):
                    refs.append(f"IRIS+: {', '.join(xrefs['iris'])}")
                if xrefs.get("gri"):
                    refs.append(f"GRI: {', '.join(xrefs['gri'])}")
                if xrefs.get("sfdr_pai"):
                    refs.append(f"SFDR PAI: {', '.join(str(x) for x in xrefs['sfdr_pai'])}")
                if refs:
                    lines.append(f"    Cross-refs: {' | '.join(refs)}")
            return ToolResult(output="\n".join(lines), metadata=result)

        return ToolResult(output=f"EDCI does not support action: {args.action}", is_error=True)

    def _handle_unpri(self, args: FrameworkInput) -> ToolResult:
        from openharness.impact.frameworks.unpri import assess_unpri_alignment, get_unpri_principles

        if args.action == "list":
            principles = get_unpri_principles()
            lines = ["UN Principles for Responsible Investment (6 Principles):\n"]
            for p in principles:
                lines.append(f"\n  Principle {p.number}: {p.name}")
                lines.append(f"    {p.full_text}")
                lines.append(f"    Actions ({len(p.actions)}):")
                for a in p.actions:
                    lines.append(f"      {a.id}: {a.description}")
            return ToolResult(output="\n".join(lines))

        if args.action in ("match", "assess"):
            result = assess_unpri_alignment(args.description, args.themes, args.document_text)
            lines = [f"UNPRI Alignment ({result['overall_coverage']}% | {result['addressed_actions']}/{result['total_actions']})\n"]
            for p in result["principles"]:
                bar = _bar(p["coverage_pct"])
                lines.append(f"  P{p['number']}: {p['name']}")
                lines.append(f"    Coverage: {p['coverage_pct']}% {bar}")
                if p["addressed_actions"]:
                    lines.append(f"    Addressed: {', '.join(p['addressed_actions'])}")
                if p["gap_actions"]:
                    lines.append("    Gaps:")
                    for g in p["gap_actions"][:3]:
                        lines.append(f"      {g['id']}: {g['question']}")
                lines.append("")
            return ToolResult(output="\n".join(lines), metadata=result)

        return ToolResult(output=f"UNPRI does not support action: {args.action}", is_error=True)

    def _handle_toc(self, args: FrameworkInput) -> ToolResult:
        from openharness.impact.frameworks.theory_of_change import (
            assess_toc_alignment, assess_toc_completeness,
            get_giin_toc_checklist, get_rs_group_principles,
        )

        if args.action == "list":
            principles = get_rs_group_principles()
            checklist = get_giin_toc_checklist()
            lines = [
                "THEORY OF CHANGE FRAMEWORKS",
                "=" * 50,
                "",
                "RS GROUP BLENDED VALUE PRINCIPLES:",
                "-" * 40,
            ]
            for p in principles:
                lines.append(f"\n  {p.name}")
                lines.append(f"    {p.description[:200]}")
                lines.append(f"    Assessment: {p.assessment_question}")

            lines.append(f"\n\nGIIN IRIS+ THEORY OF CHANGE CHECKLIST ({len(checklist)} steps):")
            lines.append("-" * 40)
            for step in checklist:
                lines.append(f"  Step {step['step']}: {step['name']}")
                lines.append(f"    {step['question']}")

            return ToolResult(output="\n".join(lines))

        if args.action in ("match", "assess"):
            text = f"{args.description} {args.document_text}"
            if not text.strip():
                return ToolResult(output="Provide description or document_text for ToC assessment", is_error=True)

            toc_result = assess_toc_alignment(args.description, args.document_text)
            completeness = assess_toc_completeness(document_text=text)

            lines = [
                "THEORY OF CHANGE ASSESSMENT",
                "=" * 50,
                "",
                f"RS Group Principles Alignment: {toc_result['coverage_pct']}% ({toc_result['addressed']}/{toc_result['total_principles']})",
                "-" * 40,
            ]
            for p in toc_result["principles"]:
                status = "[OK]" if p["addressed"] else "[GAP]"
                lines.append(f"  {status} {p['name']}")
                if p["evidence"]:
                    lines.append(f"    Evidence: {', '.join(p['evidence'][:3])}")
                if not p["addressed"]:
                    lines.append(f"    Ask: {p['question']}")

            lines.append(f"\nGIIN ToC Checklist: {completeness['coverage_pct']}% ({completeness['addressed']}/8)")
            lines.append("-" * 40)
            for step in completeness["steps"]:
                status = "[OK]" if step["addressed"] else "[GAP]"
                lines.append(f"  {status} Step {step['step']}: {step['name']}")
                if not step["addressed"]:
                    lines.append(f"    Guidance: {step['guidance']}")

            if toc_result["recommendations"]:
                lines.append(f"\nRECOMMENDATIONS ({len(toc_result['recommendations'])}):")
                for r in toc_result["recommendations"][:5]:
                    lines.append(f"  - {r}")

            return ToolResult(output="\n".join(lines), metadata={
                "rs_group": toc_result,
                "giin_checklist": completeness,
            })

        return ToolResult(output=f"ToC does not support action: {args.action}", is_error=True)

    def _handle_all_list(self, args: FrameworkInput) -> ToolResult:
        lines = [
            "Available Sustainability & ESG Frameworks:",
            "=" * 50,
            "",
            "  sasb      - SASB Industry-Specific Materiality (17 industries, 77+ topics)",
            "  gri       - GRI Universal + Topic Standards (30+ standards, 120+ disclosures)",
            "  tcfd      - TCFD / IFRS S2 Climate Disclosure (4 pillars, 11 disclosures)",
            "  sfdr_pai  - SFDR PAI Indicators (14 mandatory EU indicators)",
            "  edci      - EDCI PE/VC Metrics (17 core ESG metrics with cross-references)",
            "  unpri     - UN PRI Self-Assessment (6 principles, 27 actions)",
            "  toc       - Theory of Change (RS Group Blended Value + GIIN ToC Checklist)",
            "",
            "Use framework='<name>' with action='list' to browse, 'match' to find relevant topics,",
            "or 'assess' to check coverage. Use framework='all' with action='assess' to scan all.",
        ]
        return ToolResult(output="\n".join(lines))

    def _assess_all(self, args: FrameworkInput) -> ToolResult:
        """Run a quick scan across all frameworks."""
        from openharness.impact.frameworks.edci import assess_edci_coverage
        from openharness.impact.frameworks.sasb import match_sasb_industry
        from openharness.impact.frameworks.sfdr_pai import assess_sfdr_compliance
        from openharness.impact.frameworks.tcfd import assess_tcfd_alignment
        from openharness.impact.frameworks.theory_of_change import assess_toc_alignment
        from openharness.impact.frameworks.unpri import assess_unpri_alignment

        lines = [
            "MULTI-FRAMEWORK ESG SCAN",
            "=" * 50,
            "",
        ]

        # SASB
        sasb_matches = match_sasb_industry(args.sector, args.description, args.themes)
        if sasb_matches:
            top = sasb_matches[0]
            lines.append(f"SASB: Best match = {top[0].industry} ({top[0].sector}), {len(top[0].topics)} material topics")
        else:
            lines.append("SASB: No industry match (provide more sector detail)")

        # TCFD
        tcfd = assess_tcfd_alignment(args.description, args.reported_metrics, args.document_text)
        lines.append(f"TCFD/IFRS S2: {tcfd['overall_coverage']}% coverage ({tcfd['addressed_disclosures']}/{tcfd['total_disclosures']} disclosures)")

        # SFDR
        sfdr = assess_sfdr_compliance(args.reported_metrics, args.description, args.document_text)
        lines.append(f"SFDR PAI: {sfdr['coverage_pct']}% coverage ({sfdr['addressed']}/{sfdr['total']} indicators)")

        # EDCI
        edci = assess_edci_coverage(args.reported_metrics, args.description, args.document_text)
        lines.append(f"EDCI: {edci['coverage_pct']}% coverage ({edci['addressed']}/{edci['total']} metrics)")

        # UNPRI
        unpri = assess_unpri_alignment(args.description, args.themes, args.document_text)
        lines.append(f"UNPRI: {unpri['overall_coverage']}% alignment ({unpri['addressed_actions']}/{unpri['total_actions']} actions)")

        # Theory of Change
        toc = assess_toc_alignment(args.description, args.document_text)
        lines.append(f"ToC (RS Group): {toc['coverage_pct']}% alignment ({toc['addressed']}/{toc['total_principles']} principles)")

        lines.append("")
        lines.append("Use framework='<name>' with action='assess' for detailed analysis.")

        return ToolResult(output="\n".join(lines))


def _bar(pct: float, width: int = 15) -> str:
    filled = int(pct / 100 * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"
