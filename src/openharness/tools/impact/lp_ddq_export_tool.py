"""Tool: Multi-investor LP DDQ exporter.

Generates Due Diligence Questionnaire responses in various LP formats
by combining data from the impact engine, framework assessments, and DD checklist.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
import csv
import io

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.models import Company
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.tools.impact.common import normalize_metric_map, normalize_sdg_goals, normalize_str_list
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


LP_DDQ_TEMPLATES = {
    "ilpa": {
        "name": "ILPA DDQ (ESG Section)",
        "description": "Institutional Limited Partners Association standardized DDQ, Section 10: ESG",
        "sections": [
            {"id": "ilpa-10.1", "question": "Describe the firm's approach to integrating ESG considerations into the investment process.", "data_sources": ["impact_thesis", "sdg_alignment", "five_dimensions"]},
            {"id": "ilpa-10.2", "question": "Does the firm have a responsible investment or ESG policy? If so, please provide a copy.", "data_sources": ["governance"]},
            {"id": "ilpa-10.3", "question": "Has the firm committed to any responsible investment frameworks or principles (e.g., UNPRI)?", "data_sources": ["unpri"]},
            {"id": "ilpa-10.4", "question": "Describe how ESG risks are identified, assessed, and managed in the due diligence process.", "data_sources": ["dd_checklist", "risk"]},
            {"id": "ilpa-10.5", "question": "Describe how the firm monitors and manages ESG risks during the investment holding period.", "data_sources": ["measurement_systems"]},
            {"id": "ilpa-10.6", "question": "Describe any ESG-related training provided to investment professionals.", "data_sources": ["team"]},
            {"id": "ilpa-10.7", "question": "Does the firm measure or report on the impact of its investments? If so, what metrics or frameworks are used?", "data_sources": ["iris_metrics", "sdg_alignment", "edci"]},
            {"id": "ilpa-10.8", "question": "Has the firm experienced any material ESG incidents in its portfolio? If so, describe the response.", "data_sources": ["risk"]},
        ],
    },
    "giin_iris": {
        "name": "GIIN / IRIS+ Impact Report",
        "description": "Standard impact reporting template using IRIS+ metrics and 5 Dimensions",
        "sections": [
            {"id": "giin-1", "question": "Fund/Company overview and impact thesis", "data_sources": ["impact_thesis"]},
            {"id": "giin-2", "question": "Impact goals and SDG alignment", "data_sources": ["sdg_alignment"]},
            {"id": "giin-3", "question": "5 Dimensions of Impact assessment", "data_sources": ["five_dimensions"]},
            {"id": "giin-4", "question": "IRIS+ Core Metric Set reporting", "data_sources": ["iris_metrics", "gap_analysis"]},
            {"id": "giin-5", "question": "Impact performance and outcomes", "data_sources": ["outcomes"]},
            {"id": "giin-6", "question": "Impact measurement methodology", "data_sources": ["measurement_systems"]},
            {"id": "giin-7", "question": "Impact risks and mitigation", "data_sources": ["risk"]},
        ],
    },
    "edci": {
        "name": "EDCI Annual Survey",
        "description": "ESG Data Convergence Initiative annual portfolio company survey",
        "sections": [
            {"id": "edci-e", "question": "Environment metrics (Scope 1/2/3, renewable energy, net zero)", "data_sources": ["edci_environment"]},
            {"id": "edci-s", "question": "Social metrics (injuries, diversity, engagement, wages)", "data_sources": ["edci_social"]},
            {"id": "edci-g", "question": "Governance metrics (board independence, data privacy, ESG oversight)", "data_sources": ["edci_governance"]},
        ],
    },
    "custom": {
        "name": "Custom LP DDQ",
        "description": "Flexible template combining data from all available frameworks",
        "sections": [
            {"id": "custom-1", "question": "Impact thesis and SDG contribution", "data_sources": ["impact_thesis", "sdg_alignment"]},
            {"id": "custom-2", "question": "Impact measurement framework and metrics", "data_sources": ["iris_metrics", "five_dimensions"]},
            {"id": "custom-3", "question": "ESG risk assessment", "data_sources": ["risk", "sfdr_pai"]},
            {"id": "custom-4", "question": "Climate and environmental performance", "data_sources": ["tcfd", "edci_environment"]},
            {"id": "custom-5", "question": "Social and governance performance", "data_sources": ["edci_social", "edci_governance"]},
            {"id": "custom-6", "question": "Gap analysis and improvement plan", "data_sources": ["gap_analysis", "dd_checklist"]},
        ],
    },
}


class LpDdqExportInput(BaseModel):
    template: Literal["ilpa", "giin_iris", "edci", "custom"] = Field(
        description="LP DDQ template to use: 'ilpa' (ILPA ESG section), 'giin_iris' (GIIN/IRIS+ report), 'edci' (EDCI survey), 'custom' (all frameworks)",
    )
    action: Literal["list_templates", "generate", "preview"] = Field(
        default="generate",
        description="'list_templates': Show available templates. 'generate': Create DDQ response. 'preview': Show template structure.",
    )
    company_name: str = Field(default="", description="Company name")
    company_description: str = Field(default="", description="Company description")
    sector: str = Field(default="", description="Industry sector")
    impact_themes: list[str] = Field(default_factory=list, description="Impact themes")
    sdg_claims: list[int] = Field(default_factory=list, description="Claimed SDGs (1-17)")
    reported_metrics: dict[str, str] = Field(default_factory=dict, description="IRIS+ metric ID -> value")
    output_format: Literal["text", "json", "csv", "xlsx"] = Field(default="text", description="Output format ('xlsx' for Excel)")
    output_path: str = Field(default="", description="File path to save the output (required for xlsx)")


class LpDdqExportTool(BaseTool):
    name = "lp_ddq_export"
    description = (
        "Generate LP Due Diligence Questionnaire responses in standard formats. "
        "Templates: ILPA (ESG section), GIIN/IRIS+ impact report, EDCI annual survey, "
        "or custom multi-framework. Combines data from IRIS+ catalog, SDG alignment, "
        "5 Dimensions, gap analysis, and ESG frameworks into structured DDQ responses."
    )
    input_model = LpDdqExportInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, LpDdqExportInput) else LpDdqExportInput.model_validate(arguments)

        if args.action == "list_templates":
            return self._list_templates()

        template = LP_DDQ_TEMPLATES.get(args.template)
        if not template:
            return ToolResult(output=f"Unknown template: {args.template}", is_error=True)

        if args.action == "preview":
            return self._preview(template)

        if args.action == "generate":
            if not args.company_name:
                return ToolResult(output="company_name is required for generate", is_error=True)
            return self._generate(args, template, context)

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

    def _list_templates(self) -> ToolResult:
        lines = ["Available LP DDQ Templates:\n"]
        for key, tmpl in LP_DDQ_TEMPLATES.items():
            lines.append(f"  {key}: {tmpl['name']}")
            lines.append(f"    {tmpl['description']}")
            lines.append(f"    Sections: {len(tmpl['sections'])}")
            lines.append("")
        return ToolResult(output="\n".join(lines))

    def _preview(self, template: dict) -> ToolResult:
        lines = [f"Template: {template['name']}\n{template['description']}\n"]
        for section in template["sections"]:
            lines.append(f"  [{section['id']}] {section['question']}")
            lines.append(f"    Data sources: {', '.join(section['data_sources'])}")
        return ToolResult(output="\n".join(lines))

    def _generate(self, args: LpDdqExportInput, template: dict, context: ToolExecutionContext | None = None) -> ToolResult:
        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=args.sector,
            impact_themes=normalize_str_list(args.impact_themes),
            reported_metrics=normalize_metric_map(args.reported_metrics),
            sdg_claims=normalize_sdg_goals(args.sdg_claims),
        )

        data_cache: dict = {}

        if any("sdg" in s.get("data_sources", []) or "sdg_alignment" in s.get("data_sources", []) for s in template["sections"]):
            data_cache["sdg"] = map_sdg_alignment(company, store)

        if any("five_dimensions" in s.get("data_sources", []) for s in template["sections"]):
            data_cache["five_dim"] = assess_five_dimensions(company, store)

        if any("gap_analysis" in s.get("data_sources", []) for s in template["sections"]):
            data_cache["gaps"] = analyze_gaps(company, store)

        lines = [
            f"{'=' * 60}",
            f"LP DDQ RESPONSE: {template['name']}",
            f"Company: {company.name}",
            f"Sector: {company.sector or 'Not specified'}",
            "Date: Generated by Impact Vision",
            f"{'=' * 60}",
            "",
        ]

        for section in template["sections"]:
            lines.append(f"--- [{section['id']}] {section['question']} ---")
            lines.append("")
            response = self._generate_section_data(section, company, store, data_cache)
            lines.append(response)
            lines.append("")

        if args.output_format == "json":
            return ToolResult(output=json.dumps({
                "template": template["name"],
                "company": company.name,
                "sections": [
                    {"id": s["id"], "question": s["question"],
                     "response": self._generate_section_data(s, company, store, data_cache)}
                    for s in template["sections"]
                ],
            }, indent=2))

        if args.output_format == "xlsx":
            return self._generate_xlsx(args, template, company, store, data_cache, context)
        if args.output_format == "csv":
            return ToolResult(output=self._to_csv(template, company, store, data_cache))

        return ToolResult(output="\n".join(lines))

    def _generate_xlsx(self, args: LpDdqExportInput, template: dict, company: Company, store, data_cache: dict, context: ToolExecutionContext | None = None) -> ToolResult:
        """Generate an Excel workbook with DDQ responses."""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
        except ImportError:
            return ToolResult(output="openpyxl required for XLSX export. Install: pip install openpyxl", is_error=True)

        if not args.output_path:
            return ToolResult(output="output_path is required for xlsx format", is_error=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "DDQ Response"

        header_font = Font(name="Calibri", bold=True, size=12, color="FFFFFF")
        header_fill = PatternFill(start_color="0D47A1", end_color="0D47A1", fill_type="solid")
        ws.append(["LP DDQ Response", template["name"]])
        ws.append(["Company", company.name])
        ws.append(["Sector", company.sector or "N/A"])
        ws.append(["Date", "Generated by Impact Vision"])
        ws.append([])

        headers = ["Section ID", "Question", "Response", "Data Sources"]
        ws.append(headers)
        for col_idx, _ in enumerate(headers, 1):
            cell = ws.cell(row=6, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill

        for section in template["sections"]:
            response = self._generate_section_data(section, company, store, data_cache)
            ws.append([
                section["id"],
                section["question"],
                response,
                ", ".join(section.get("data_sources", [])),
            ])

        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 50
        ws.column_dimensions["C"].width = 80
        ws.column_dimensions["D"].width = 25

        for row in ws.iter_rows(min_row=7, max_col=4):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")

        path = Path(args.output_path)
        if not path.is_absolute() and context and hasattr(context, 'cwd'):
            path = context.cwd / path
        path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(str(path))

        return ToolResult(
            output=f"XLSX DDQ exported to: {path}\nTemplate: {template['name']}\nCompany: {company.name}\nSections: {len(template['sections'])}",
            metadata={"output_path": str(path), "format": "xlsx"},
        )

    def _generate_section_data(self, section: dict, company: Company, store, data_cache: dict) -> str:
        """Generate data-driven content for a DDQ section."""
        sources = section.get("data_sources", [])
        parts: list[str] = []

        if "impact_thesis" in sources:
            parts.append(f"Company: {company.name}")
            if company.description:
                parts.append(f"Description: {company.description}")
            if company.sector:
                parts.append(f"Sector: {company.sector}")
            if company.impact_themes:
                parts.append(f"Impact Themes: {', '.join(company.impact_themes)}")

        if "sdg_alignment" in sources and "sdg" in data_cache:
            alignments = data_cache["sdg"]
            top = [a for a in alignments if a.score > 0]
            if top:
                parts.append("SDG Alignment:")
                for a in top[:5]:
                    parts.append(f"  SDG {a.goal} ({a.goal_name}): {a.score}/100 [{a.confidence}]")

        if "five_dimensions" in sources and "five_dim" in data_cache:
            fd = data_cache["five_dim"]
            parts.append(f"5 Dimensions of Impact: Overall {fd.overall_score:.1f}/5 ({fd.overall_grade})")
            parts.append(f"  What: {fd.what.score:.1f}/5 | Who: {fd.who.score:.1f}/5 | How Much: {fd.how_much.score:.1f}/5")
            parts.append(f"  Contribution: {fd.contribution.score:.1f}/5 | Risk: {fd.risk.score:.1f}/5")

        if "iris_metrics" in sources:
            if company.reported_metrics:
                parts.append(f"IRIS+ Metrics Reported ({len(company.reported_metrics)}):")
                for mid, val in list(company.reported_metrics.items())[:10]:
                    m = store.get(mid)
                    parts.append(f"  {mid} ({m.name if m else '?'}): {val}")
            else:
                parts.append("No IRIS+ metrics currently reported.")

        if "gap_analysis" in sources and "gaps" in data_cache:
            gaps = data_cache["gaps"]
            parts.append(f"Core Metric Set Coverage: {gaps['coverage_percentage']}%")
            parts.append(f"  Reported: {gaps['metrics_reported']} | Missing: {gaps['metrics_missing']}")

        if not parts:
            parts.append("[Data not available - provide more company information]")

        return "\n".join(parts)

    def _to_csv(self, template: dict, company: Company, store, data_cache: dict) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Template", template["name"]])
        writer.writerow(["Company", company.name])
        writer.writerow([])
        writer.writerow(["Section ID", "Question", "Response"])
        for section in template["sections"]:
            writer.writerow(
                [
                    section["id"],
                    section["question"],
                    self._generate_section_data(section, company, store, data_cache),
                ]
            )
        return output.getvalue()
