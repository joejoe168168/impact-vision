"""Tool: Generate impact assessment reports (HTML, CSV, JSON)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.models import Company
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult

_SECTOR_OPPORTUNITIES: dict[str, list[str]] = {
    "agriculture": [
        "Food security: improving access to nutritious food for underserved populations",
        "Poverty reduction: increasing income for smallholder farmers",
        "Sustainable supply chains: promoting responsible sourcing and production",
        "Climate adaptation: developing climate-resilient farming practices",
        "Rural employment: creating jobs in farming communities",
    ],
    "livestock": [
        "Food security: providing protein and nutrition to local markets",
        "Poverty reduction: supporting livelihoods of small-scale farmers",
        "Economic development: strengthening local agricultural value chains",
        "Sustainable practices: implementing responsible animal husbandry",
        "Rural employment: creating jobs in farming and processing",
    ],
    "healthcare": [
        "Health outcomes: improving access to quality healthcare services",
        "Health equity: reducing disparities in healthcare access",
        "Disease prevention: supporting public health initiatives",
        "Workforce development: training healthcare professionals",
    ],
    "energy": [
        "Clean energy access: providing affordable clean energy to underserved areas",
        "Climate mitigation: reducing greenhouse gas emissions",
        "Energy independence: reducing reliance on fossil fuels",
        "Job creation: creating green energy employment opportunities",
    ],
    "education": [
        "Educational access: reaching underserved or marginalized populations",
        "Skills development: building employable skills for the workforce",
        "Digital inclusion: bridging the digital divide",
        "Gender equity: improving educational access for girls and women",
    ],
    "fintech": [
        "Financial inclusion: providing access to financial services for the unbanked",
        "Economic empowerment: enabling savings, credit, and insurance",
        "Gender equity: improving financial access for women",
        "Efficiency: reducing transaction costs for low-income users",
    ],
    "water": [
        "Clean water access: providing safe drinking water to underserved communities",
        "Sanitation: improving hygiene and reducing waterborne disease",
        "Water efficiency: promoting sustainable water management practices",
    ],
    "technology": [
        "Digital inclusion: bridging the digital divide for underserved populations",
        "Efficiency gains: improving productivity and reducing waste",
        "Innovation: enabling new solutions to social and environmental challenges",
    ],
}

_SECTOR_RISKS: dict[str, list[str]] = {
    "agriculture": [
        "Environmental degradation: soil depletion, water pollution from fertilizers/pesticides",
        "Climate vulnerability: sensitivity to extreme weather events and climate change",
        "Labor conditions: risk of exploitative labor practices",
        "Land use change: deforestation or biodiversity loss from land conversion",
        "Market volatility: commodity price fluctuations affecting farmer incomes",
    ],
    "livestock": [
        "Environmental pollution: waste management, methane emissions, water contamination",
        "Animal welfare: risk of poor animal husbandry practices",
        "Disease risk: zoonotic disease transmission and antibiotic resistance",
        "Carbon footprint: significant greenhouse gas emissions from livestock",
        "Resource intensity: high water and feed consumption per unit of protein",
        "Community impact: odor, waste runoff affecting neighboring communities",
    ],
    "healthcare": [
        "Access inequality: risk of services remaining unaffordable for the poorest",
        "Quality variance: inconsistent quality of care across locations",
        "Data privacy: risks around patient health data security",
    ],
    "energy": [
        "Environmental impact: land use, waste from equipment, resource extraction",
        "Community displacement: risk of displacing communities for energy projects",
        "Technology risk: rapidly changing technology making investments obsolete",
    ],
    "education": [
        "Quality risk: providing access without ensuring quality outcomes",
        "Digital divide: technology-dependent models excluding the most vulnerable",
        "Sustainability: dependence on grants or subsidies for viability",
    ],
    "fintech": [
        "Over-indebtedness: risk of predatory lending to vulnerable populations",
        "Data privacy: risks around financial data security and misuse",
        "Digital exclusion: services inaccessible to those without smartphones/internet",
    ],
    "water": [
        "Sustainability: risk of depleting water sources without replenishment",
        "Infrastructure maintenance: long-term maintenance of water systems",
        "Affordability: pricing that excludes the poorest communities",
    ],
    "technology": [
        "Digital divide: reinforcing existing inequalities through technology access",
        "Privacy and surveillance: risks around data collection and misuse",
        "Job displacement: automation reducing employment opportunities",
    ],
}


def _infer_opportunities_and_risks(company: Company) -> dict[str, list[str]]:
    """Infer impact opportunities and risks from sector and description."""
    text = f"{company.description} {company.sector}".lower()
    opportunities: list[str] = []
    risks: list[str] = []

    for sector_key in _SECTOR_OPPORTUNITIES:
        if sector_key in text:
            opportunities.extend(_SECTOR_OPPORTUNITIES[sector_key])
    for sector_key in _SECTOR_RISKS:
        if sector_key in text:
            risks.extend(_SECTOR_RISKS[sector_key])

    if not opportunities:
        opportunities = ["Further analysis needed to identify specific impact opportunities"]
    if not risks:
        risks = ["Further analysis needed to identify specific impact risks"]

    return {"opportunities": list(dict.fromkeys(opportunities)), "risks": list(dict.fromkeys(risks))}


class ImpactReportInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    company_description: str = Field(default="")
    sector: str = Field(default="")
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    output_format: Literal["html", "csv", "json", "text", "xlsx"] = Field(
        default="text", description="Output format for the report ('xlsx' for Excel workbook)"
    )
    output_path: str = Field(
        default="",
        description="File path to save the report (optional; if empty, returns as text)",
    )
    include_gap_analysis: bool = Field(default=True)
    include_sdg_mapping: bool = Field(default=True)
    include_five_dimensions: bool = Field(default=True)


class ImpactReportTool(BaseTool):
    name = "impact_report"
    description = (
        "Generate a comprehensive impact assessment report for a company. "
        "Includes 5-Dimension scoring, SDG alignment mapping, and gap analysis. "
        "Supports HTML, CSV, JSON, and text output formats. "
        "Optionally saves to a file."
    )
    input_model = ImpactReportInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, ImpactReportInput) else ImpactReportInput.model_validate(arguments)
        return not bool(args.output_path)

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ImpactReportInput) else ImpactReportInput.model_validate(arguments)

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        company = Company(
            name=args.company_name,
            description=args.company_description,
            sector=args.sector,
            impact_themes=args.impact_themes,
            reported_metrics=args.reported_metrics,
            sdg_claims=args.sdg_claims,
        )

        report_data: dict = {
            "company": company.model_dump(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "catalog_version": "IRIS+ 5.3c",
        }

        if args.include_five_dimensions:
            fd_result = assess_five_dimensions(company, store)
            report_data["five_dimensions"] = fd_result.model_dump()

        if args.include_sdg_mapping:
            sdg_results = map_sdg_alignment(company, store)
            report_data["sdg_alignments"] = [a.model_dump() for a in sdg_results]

        if args.include_gap_analysis:
            gap_result = analyze_gaps(company, store)
            report_data["gap_analysis"] = gap_result

        report_data["impact_analysis"] = _infer_opportunities_and_risks(company)

        from openharness.impact.benchmarks import compare_to_benchmark
        if "five_dimensions" in report_data and company.sector:
            fd = report_data["five_dimensions"]
            five_d_scores = {
                "what": fd["what"]["score"],
                "who": fd["who"]["score"],
                "how_much": fd["how_much"]["score"],
                "contribution": fd["contribution"]["score"],
                "risk": fd["risk"]["score"],
            }
            coverage = report_data.get("gap_analysis", {}).get("coverage_percentage", 0)
            bm = compare_to_benchmark(company.sector, five_d_scores, fd["overall_score"], coverage)
            if bm.get("benchmark_available"):
                report_data["benchmark_comparison"] = bm

        if args.output_format == "xlsx":
            return _to_xlsx(report_data, args.output_path, context)
        elif args.output_format == "json":
            output = json.dumps(report_data, indent=2, default=str)
        elif args.output_format == "csv":
            output = _to_csv(report_data)
        elif args.output_format == "html":
            output = _to_html(report_data)
        else:
            output = _to_text(report_data)

        if args.output_path:
            path = Path(args.output_path)
            if not path.is_absolute():
                path = context.cwd / path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output, encoding="utf-8")
            summary = _to_text(report_data) if args.output_format != "text" else output[:1500]
            return ToolResult(
                output=f"Report saved to: {path}\nFormat: {args.output_format}\n\n{summary}",
                metadata={"output_path": str(path), "format": args.output_format},
            )

        if args.output_format == "html" and len(output) > 2000:
            summary = _to_text(report_data)
            return ToolResult(
                output=f"HTML report generated ({len(output)} chars). Text summary:\n\n{summary}",
                metadata={"format": args.output_format, "html_length": len(output)},
            )

        return ToolResult(
            output=output,
            metadata={"format": args.output_format},
        )


def _to_text(data: dict) -> str:
    lines = [
        "=" * 70,
        f"IMPACT ASSESSMENT REPORT: {data['company']['name']}",
        f"Generated: {data['generated_at']}",
        f"Standard: {data['catalog_version']}",
        "=" * 70,
        "",
    ]

    if "five_dimensions" in data:
        fd = data["five_dimensions"]
        lines.append("5 DIMENSIONS OF IMPACT")
        lines.append("-" * 40)
        lines.append(f"Overall Grade: {fd['overall_grade']} ({fd['overall_score']}/5.0)")
        for dim_name in ["what", "who", "how_much", "contribution", "risk"]:
            dim = fd[dim_name]
            lines.append(f"  {dim['dimension']}: {dim['score']}/5.0 | {dim['notes']}")
        if fd.get("recommendations"):
            lines.append("\nRecommendations:")
            for r in fd["recommendations"]:
                lines.append(f"  - {r}")
        lines.append("")

    if "sdg_alignments" in data:
        lines.append("SDG ALIGNMENT")
        lines.append("-" * 40)
        for a in data["sdg_alignments"]:
            if a["score"] > 0:
                lines.append(f"  SDG {a['goal']} ({a['goal_name']}): {a['score']}/100 [{a['confidence']}]")
        lines.append("")

    if "gap_analysis" in data:
        ga = data["gap_analysis"]
        lines.append("GAP ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"  Coverage: {ga['coverage_percentage']}% ({ga['metrics_reported']}/{ga['core_metric_set_size']})")
        if ga.get("missing"):
            lines.append("  Missing:")
            for m in ga["missing"][:10]:
                lines.append(f"    - {m['id']}: {m['name']}")
        lines.append("")

    if "impact_analysis" in data:
        ia = data["impact_analysis"]
        lines.append("IMPACT OPPORTUNITIES")
        lines.append("-" * 40)
        for o in ia.get("opportunities", []):
            lines.append(f"  + {o}")
        lines.append("")
        lines.append("IMPACT RISKS")
        lines.append("-" * 40)
        for r in ia.get("risks", []):
            lines.append(f"  ! {r}")
        lines.append("")

    if "benchmark_comparison" in data:
        bm = data["benchmark_comparison"]
        lines.append("SECTOR BENCHMARK COMPARISON")
        lines.append("-" * 40)
        lines.append(f"  Sector: {bm['sector']} ({bm['sample_note']})")
        ov = bm["overall"]
        arrow = "^" if ov["delta"] > 0 else ("v" if ov["delta"] < 0 else "=")
        lines.append(f"  Overall: {ov['actual']:.1f} vs {ov['benchmark']:.1f} benchmark ({arrow} {ov['delta']:+.1f})")
        for dim, vals in bm["dimensions"].items():
            arrow = "^" if vals["delta"] > 0 else ("v" if vals["delta"] < 0 else "=")
            lines.append(f"    {dim}: {vals['actual']:.1f} vs {vals['benchmark']:.1f} ({arrow} {vals['delta']:+.1f})")
        cov = bm["coverage"]
        lines.append(f"  Coverage: {cov['actual']:.0f}% vs {cov['benchmark']:.0f}% benchmark ({cov['delta']:+.1f}%)")
        lines.append("")

    return "\n".join(lines)


def _to_csv(data: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["Section", "Metric", "Value", "Details"])
    writer.writerow(["Company", "Name", data["company"]["name"], ""])
    writer.writerow(["Company", "Generated", data["generated_at"], ""])

    if "five_dimensions" in data:
        fd = data["five_dimensions"]
        writer.writerow(["5D", "Overall Grade", fd["overall_grade"], f"{fd['overall_score']}/5.0"])
        for dim_name in ["what", "who", "how_much", "contribution", "risk"]:
            dim = fd[dim_name]
            writer.writerow(["5D", dim["dimension"], f"{dim['score']}/5.0", dim["notes"]])

    if "sdg_alignments" in data:
        for a in data["sdg_alignments"]:
            if a["score"] > 0:
                writer.writerow([
                    "SDG", f"SDG {a['goal']}", f"{a['score']}/100",
                    f"{a['confidence']} | metrics: {','.join(a.get('matched_metrics', [])[:3])}"
                ])

    if "gap_analysis" in data:
        ga = data["gap_analysis"]
        writer.writerow(["Gap", "Coverage", f"{ga['coverage_percentage']}%", ""])
        for m in ga.get("missing", []):
            writer.writerow(["Gap", m["id"], "MISSING", m["name"]])
        for m in ga.get("reported", []):
            writer.writerow(["Gap", m["id"], m.get("value", ""), m["name"]])

    return buf.getvalue()


def _to_html(data: dict) -> str:
    company = data["company"]
    sections: list[str] = []
    sdg_colors_map = {
        1: "#E5243B", 2: "#DDA63A", 3: "#4C9F38", 4: "#C5192D", 5: "#FF3A21",
        6: "#26BDE2", 7: "#FCC30B", 8: "#A21942", 9: "#FD6925", 10: "#DD1367",
        11: "#FD9D24", 12: "#BF8B2E", 13: "#3F7E44", 14: "#0A97D9", 15: "#56C02B",
        16: "#00689D", 17: "#19486A",
    }

    sections.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Impact Report: {company['name']}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
:root {{
  --primary: #0d47a1; --primary-light: #e3f2fd; --primary-dark: #002171;
  --accent: #1976d2; --accent-light: #63a4ff;
  --success: #2e7d32; --success-light: #e8f5e9;
  --warning: #f57c00; --warning-light: #fff3e0;
  --danger: #c62828; --danger-light: #ffebee;
  --surface: #ffffff; --bg: #f5f7fa; --text: #1a1a2e; --text-secondary: #5f6368;
  --border: #e0e4e8; --shadow-sm: 0 1px 3px rgba(0,0,0,0.08); --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
  --radius: 12px; --radius-sm: 8px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1080px; margin: 0 auto; padding: 32px 24px; color: var(--text); background: var(--bg); line-height: 1.5; }}
.report-header {{ background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%); color: white; padding: 36px 40px; border-radius: var(--radius); margin-bottom: 28px; box-shadow: var(--shadow-md); }}
.report-header h1 {{ font-size: 1.75em; font-weight: 700; margin-bottom: 6px; letter-spacing: -0.02em; }}
.report-header .subtitle {{ opacity: 0.9; font-size: 0.95em; }}
.report-header .meta-row {{ display: flex; gap: 20px; flex-wrap: wrap; margin-top: 12px; opacity: 0.85; font-size: 0.85em; }}
.report-header .meta-row span {{ display: flex; align-items: center; gap: 4px; }}
.tag-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
.tag {{ display: inline-block; background: rgba(255,255,255,0.2); padding: 3px 12px; border-radius: 20px; font-size: 0.8em; }}
h2 {{ color: var(--primary); font-size: 1.3em; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 2px solid var(--primary-light); font-weight: 600; }}
h3 {{ color: var(--text); font-size: 1.05em; margin: 20px 0 10px; font-weight: 600; }}
.cards-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 16px 0; }}
.score-card {{ flex: 0 0 auto; background: var(--surface); border-radius: var(--radius); box-shadow: var(--shadow-sm); padding: 20px 28px; text-align: center; border: 1px solid var(--border); min-width: 130px; }}
.score-card .value {{ font-size: 2.2em; font-weight: 700; line-height: 1.1; }}
.score-card .label {{ font-size: 0.8em; color: var(--text-secondary); margin-top: 6px; text-transform: uppercase; letter-spacing: 0.03em; }}
.grade-A {{ color: var(--success); }} .grade-B {{ color: #558b2f; }} .grade-C {{ color: #f9a825; }} .grade-D {{ color: #e65100; }} .grade-F {{ color: var(--danger); }}
.chart-row {{ display: flex; gap: 20px; flex-wrap: wrap; margin: 16px 0; }}
.chart-box {{ flex: 1 1 420px; min-width: 0; background: var(--surface); border-radius: var(--radius); box-shadow: var(--shadow-sm); padding: 20px; border: 1px solid var(--border); overflow: hidden; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; background: var(--surface); border-radius: var(--radius-sm); overflow: hidden; box-shadow: var(--shadow-sm); font-size: 0.9em; }}
th {{ background: var(--primary); color: white; font-weight: 600; padding: 12px 14px; text-align: left; text-transform: uppercase; font-size: 0.75em; letter-spacing: 0.05em; }}
td {{ border-bottom: 1px solid var(--border); padding: 10px 14px; }}
tr:hover td {{ background: var(--primary-light); }}
.bar-track {{ background: #e8eaed; border-radius: 6px; height: 10px; width: 100%; overflow: hidden; }}
.bar-fill {{ height: 100%; border-radius: 6px; transition: width 0.4s ease; }}
.bar-fill.blue {{ background: linear-gradient(90deg, var(--accent), var(--accent-light)); }}
.bar-fill.green {{ background: linear-gradient(90deg, #43a047, #66bb6a); }}
.bar-fill.orange {{ background: linear-gradient(90deg, #ef6c00, #ffa726); }}
.bar-fill.red {{ background: linear-gradient(90deg, #c62828, #ef5350); }}
.bar-fill.coverage {{ background: linear-gradient(90deg, var(--primary), var(--accent)); }}
.rec {{ background: var(--warning-light); padding: 14px 18px; border-left: 4px solid var(--warning); margin: 8px 0; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; font-size: 0.9em; line-height: 1.6; }}
.bm-delta.positive {{ color: var(--success); font-weight: 700; }}
.bm-delta.negative {{ color: var(--danger); font-weight: 700; }}
.bm-delta.neutral {{ color: var(--text-secondary); font-weight: 600; }}
.coverage-hero {{ background: var(--surface); border-radius: var(--radius); box-shadow: var(--shadow-sm); padding: 24px 28px; border: 1px solid var(--border); margin: 16px 0; display: flex; align-items: center; gap: 20px; }}
.coverage-hero .pct {{ font-size: 2.5em; font-weight: 800; color: var(--primary); line-height: 1; }}
.coverage-hero .detail {{ flex: 1; }}
.coverage-hero .bar-track {{ height: 14px; margin-top: 8px; }}
.footer {{ margin-top: 48px; padding: 20px 0; border-top: 2px solid var(--border); color: var(--text-secondary); font-size: 0.8em; text-align: center; }}
.footer a {{ color: var(--accent); text-decoration: none; }}
@media(max-width: 700px) {{ .chart-row {{ flex-direction: column; }} .chart-box {{ flex-basis: 100%; }} }}
</style>
</head>
<body>
<div class="report-header">
<h1>Impact Assessment Report</h1>
<p class="subtitle">{company['name']}{' | ' + company.get('sector', '') if company.get('sector') else ''}</p>
<div class="meta-row">
  <span>Generated: {data['generated_at'][:10]}</span>
  <span>Standard: {data['catalog_version']}</span>
</div>""")

    if company.get("impact_themes") or company.get("sdg_claims"):
        sections.append('<div class="tag-row">')
        for t in company.get("impact_themes", []):
            sections.append(f'<span class="tag">{t}</span>')
        for g in company.get("sdg_claims", []):
            sections.append(f'<span class="tag">SDG {g}</span>')
        sections.append('</div>')
    sections.append('</div>')

    if "five_dimensions" in data:
        fd = data["five_dimensions"]
        grade_class = f"grade-{fd['overall_grade'][0]}"

        sections.append(f"""
<h2>5 Dimensions of Impact</h2>
<div class="cards-row">
<div class="score-card"><div class="value {grade_class}">{fd['overall_grade']}</div><div class="label">Overall Grade</div></div>
<div class="score-card"><div class="value">{fd['overall_score']:.1f}<span style="font-size:0.5em;color:var(--text-secondary)">/5</span></div><div class="label">Overall Score</div></div>
</div>
<div class="chart-row">
<div class="chart-box" id="radar-chart"></div>
<div class="chart-box">
<table>
<tr><th>Dimension</th><th>Score</th><th style="min-width:160px">Progress</th><th>Details</th></tr>
""")
        dims_js = []
        scores_js = []
        for dim_name in ["what", "who", "how_much", "contribution", "risk"]:
            dim = fd[dim_name]
            pct = int(dim["score"] / 5.0 * 100)
            bar_color = "green" if pct >= 60 else "orange" if pct >= 30 else "red"
            dims_js.append(f'"{dim["dimension"]}"')
            scores_js.append(str(dim["score"]))
            sections.append(f"""<tr>
<td><strong>{dim['dimension']}</strong></td>
<td style="font-weight:600">{dim['score']}/5</td>
<td><div class="bar-track"><div class="bar-fill {bar_color}" style="width:{pct}%"></div></div></td>
<td style="font-size:0.85em;color:var(--text-secondary)">{dim['notes']}</td>
</tr>""")
        sections.append("</table></div></div>")

        sections.append(f"""<script>
Plotly.newPlot('radar-chart', [{{
  type: 'scatterpolar', r: [{','.join(scores_js)},{scores_js[0]}],
  theta: [{','.join(dims_js)},{dims_js[0]}],
  fill: 'toself', fillcolor: 'rgba(25,118,210,0.12)',
  line: {{color: '#1976d2', width: 2.5}}, marker: {{size: 7, color: '#1976d2'}}
}}], {{
  polar: {{radialaxis: {{visible: true, range: [0, 5], tickfont: {{size: 10}}}}, angularaxis: {{tickfont: {{size: 11}}}}}},
  showlegend: false, height: 380, margin: {{l: 70, r: 70, t: 40, b: 40}},
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  font: {{family: 'Inter, -apple-system, sans-serif'}}
}}, {{responsive: true}});
</script>""")

        if fd.get("recommendations"):
            sections.append("<h3>Recommendations</h3>")
            for r in fd["recommendations"]:
                sections.append(f'<div class="rec">{r}</div>')

    if "sdg_alignments" in data:
        aligned = [a for a in data["sdg_alignments"] if a["score"] > 0]
        sdg_labels = [f'"SDG {a["goal"]}"' for a in aligned]
        sdg_scores = [str(a["score"]) for a in aligned]
        sdg_colors = []
        for a in aligned:
            sdg_colors.append(f'"{sdg_colors_map.get(a["goal"], "#1976d2")}"')

        sections.append(f"""
<h2>SDG Alignment <span style="font-size:0.65em;color:var(--text-secondary);font-weight:400">({len(aligned)} goals)</span></h2>
<div class="chart-row">
<div class="chart-box" id="sdg-chart"></div>
<div class="chart-box">
<table>
<tr><th>SDG</th><th>Name</th><th>Score</th><th>Confidence</th><th>Matched Metrics</th></tr>
""")
        for a in aligned:
            sdg_color = sdg_colors_map.get(a["goal"], "#666")
            metrics_str = ", ".join(a.get("matched_metrics", [])[:3])
            conf_style = {
                "high": "color:var(--success);font-weight:600",
                "medium": "color:#f57c00;font-weight:600",
                "low": "color:var(--danger);font-weight:600",
            }.get(a["confidence"], "")
            sections.append(f"""<tr>
<td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{sdg_color};margin-right:6px;vertical-align:middle"></span>SDG {a['goal']}</td>
<td>{a.get('goal_name', '')}</td>
<td style="font-weight:600">{a['score']}</td><td style="{conf_style}">{a['confidence']}</td><td style="font-size:0.85em">{metrics_str}</td>
</tr>""")
        sections.append("</table></div></div>")

        if sdg_labels:
            sections.append(f"""<script>
Plotly.newPlot('sdg-chart', [{{
  type: 'bar', x: [{','.join(sdg_labels)}], y: [{','.join(sdg_scores)}],
  marker: {{color: [{','.join(sdg_colors)}], line: {{width: 0}}, cornerradius: 4}},
  text: [{','.join(sdg_scores)}], textposition: 'outside', textfont: {{size: 11, family: 'Inter, sans-serif'}}
}}], {{
  yaxis: {{range: [0, 110], title: 'Alignment Score', gridcolor: '#f0f0f0', titlefont: {{size: 12}}}},
  xaxis: {{tickangle: -30, tickfont: {{size: 10}}}},
  height: 380, margin: {{l: 55, r: 20, t: 20, b: 60}},
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  font: {{family: 'Inter, -apple-system, sans-serif'}}
}}, {{responsive: true}});
</script>""")

    if "impact_analysis" in data:
        ia = data["impact_analysis"]
        sections.append("""
<h2>Impact Opportunities & Risks</h2>
<div class="chart-row">
<div class="chart-box">
<h3 style="color:var(--success)">Opportunities</h3>""")
        for o in ia.get("opportunities", []):
            sections.append(f'<div class="rec" style="border-left-color:var(--success);background:var(--success-light)">+ {o}</div>')
        sections.append("""</div>
<div class="chart-box">
<h3 style="color:var(--danger)">Risks</h3>""")
        for r in ia.get("risks", []):
            sections.append(f'<div class="rec" style="border-left-color:var(--danger);background:var(--danger-light)">! {r}</div>')
        sections.append("</div></div>")

    if "gap_analysis" in data:
        ga = data["gap_analysis"]
        pct = ga["coverage_percentage"]
        pct_color = "var(--success)" if pct >= 60 else "var(--warning)" if pct >= 30 else "var(--danger)"
        bar_cls = "green" if pct >= 60 else "orange" if pct >= 30 else "red"
        sections.append(f"""
<h2>Gap Analysis</h2>
<div class="coverage-hero">
  <div class="pct" style="color:{pct_color}">{ga['coverage_percentage']}%</div>
  <div class="detail">
    <div style="font-weight:600;font-size:1.1em">Core Metric Set Coverage</div>
    <div style="color:var(--text-secondary);font-size:0.9em">{ga['metrics_reported']} of {ga['core_metric_set_size']} metrics reported | {ga['metrics_missing']} missing</div>
    <div class="bar-track"><div class="bar-fill {bar_cls}" style="width:{int(pct)}%"></div></div>
  </div>
</div>
""")
        if ga.get("missing"):
            sections.append("""<h3>Missing Metrics</h3><table><tr><th>ID</th><th>Name</th><th>Definition</th></tr>""")
            for m in ga["missing"]:
                sections.append(f"<tr><td style='font-weight:600'>{m['id']}</td><td>{m['name']}</td><td style='font-size:0.85em;color:var(--text-secondary)'>{m.get('definition', '')[:120]}</td></tr>")
            sections.append("</table>")

        if ga.get("recommendations"):
            sections.append("<h3>Recommendations</h3>")
            for r in ga["recommendations"]:
                sections.append(f'<div class="rec">{r}</div>')

    if "benchmark_comparison" in data:
        bm = data["benchmark_comparison"]
        sections.append(f"""
<h2>Sector Benchmark Comparison</h2>
<p style="color:var(--text-secondary);font-size:0.9em;margin-bottom:12px">{bm['sector']} | {bm.get('sample_note', '')}</p>
<div class="chart-row">
<div class="chart-box" id="benchmark-chart"></div>
<div class="chart-box">
<table>
<tr><th>Dimension</th><th>Your Score</th><th>Benchmark</th><th>Delta</th></tr>
""")
        ov = bm["overall"]
        delta_class = "positive" if ov["delta"] > 0 else ("negative" if ov["delta"] < 0 else "neutral")
        delta_arrow = "+" if ov["delta"] > 0 else ""
        sections.append(f"""<tr style="font-weight:600;background:var(--primary-light)">
<td>Overall</td><td>{ov['actual']:.1f}</td><td>{ov['benchmark']:.1f}</td>
<td class="bm-delta {delta_class}">{delta_arrow}{ov['delta']:.1f}</td></tr>""")

        bm_dim_labels = []
        bm_actual_vals = []
        bm_benchmark_vals = []
        for dim, vals in bm["dimensions"].items():
            delta_class = "positive" if vals["delta"] > 0 else ("negative" if vals["delta"] < 0 else "neutral")
            delta_arrow = "+" if vals["delta"] > 0 else ""
            display_name = dim.replace('_', ' ').title()
            bm_dim_labels.append(f'"{display_name}"')
            bm_actual_vals.append(str(vals["actual"]))
            bm_benchmark_vals.append(str(vals["benchmark"]))
            sections.append(f"""<tr>
<td>{display_name}</td><td>{vals['actual']:.1f}</td><td>{vals['benchmark']:.1f}</td>
<td class="bm-delta {delta_class}">{delta_arrow}{vals['delta']:.1f}</td></tr>""")
        sections.append("</table></div></div>")

        if bm_dim_labels:
            sections.append(f"""<script>
Plotly.newPlot('benchmark-chart', [
  {{type:'bar', name:'Your Score', x:[{','.join(bm_dim_labels)}], y:[{','.join(bm_actual_vals)}], marker:{{color:'#1976d2', cornerradius:3}}}},
  {{type:'bar', name:'Benchmark', x:[{','.join(bm_dim_labels)}], y:[{','.join(bm_benchmark_vals)}], marker:{{color:'#b0bec5', cornerradius:3}}}}
], {{
  barmode:'group', yaxis:{{range:[0,5.5], title:'Score', gridcolor:'#f0f0f0'}},
  height:350, margin:{{l:50,r:20,t:20,b:50}}, legend:{{orientation:'h', y:1.08}},
  paper_bgcolor:'transparent', plot_bgcolor:'transparent',
  font:{{family:'Inter, -apple-system, sans-serif', size:11}}
}}, {{responsive:true}});
</script>""")

    sections.append("""
<div class="footer">
Generated by <a href="#">Impact Vision</a> &mdash; Open-source impact measurement engine &mdash; IRIS+ 5.3c
</div>
</body></html>""")
    return "\n".join(sections)


def _to_xlsx(data: dict, output_path: str, context) -> ToolResult:
    """Generate an Excel workbook with the impact report."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        return ToolResult(output="openpyxl required for XLSX. Install: pip install openpyxl", is_error=True)

    if not output_path:
        return ToolResult(output="output_path is required for xlsx format", is_error=True)

    wb = Workbook()
    company = data["company"]

    # Sheet 1: Summary
    ws = wb.active
    ws.title = "Summary"
    header_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="0D47A1", end_color="0D47A1", fill_type="solid")

    ws.append(["Impact Assessment Report"])
    ws.append(["Company", company["name"]])
    ws.append(["Sector", company.get("sector", "")])
    ws.append(["Generated", data["generated_at"]])
    ws.append(["Standard", data["catalog_version"]])
    ws.append([])

    if "five_dimensions" in data:
        fd = data["five_dimensions"]
        ws.append(["5 DIMENSIONS OF IMPACT"])
        headers = ["Dimension", "Score", "Metrics Reported", "Available", "Notes"]
        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=ws.max_row, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
        for dim_name in ["what", "who", "how_much", "contribution", "risk"]:
            dim = fd[dim_name]
            ws.append([dim["dimension"], dim["score"], dim["metrics_reported"], dim["metrics_available"], dim["notes"]])
        ws.append(["Overall", fd["overall_score"], "", "", fd["overall_grade"]])
        ws.append([])

    # Sheet 2: SDG Alignment
    if "sdg_alignments" in data:
        ws2 = wb.create_sheet("SDG Alignment")
        headers = ["SDG Goal", "Name", "Score", "Confidence", "Matched Metrics", "Matched Targets"]
        ws2.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
        for a in data["sdg_alignments"]:
            if a["score"] > 0:
                ws2.append([
                    f"SDG {a['goal']}", a.get("goal_name", ""), a["score"],
                    a["confidence"], ", ".join(a.get("matched_metrics", [])[:5]),
                    ", ".join(a.get("matched_targets", [])[:5]),
                ])

    # Sheet 3: Gap Analysis
    if "gap_analysis" in data:
        ws3 = wb.create_sheet("Gap Analysis")
        ga = data["gap_analysis"]
        ws3.append(["Coverage %", ga["coverage_percentage"]])
        ws3.append(["Reported", ga["metrics_reported"]])
        ws3.append(["Missing", ga["metrics_missing"]])
        ws3.append([])
        headers = ["Status", "Metric ID", "Name", "Value"]
        ws3.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws3.cell(row=5, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
        for m in ga.get("reported", []):
            ws3.append(["Reported", m["id"], m["name"], m.get("value", "")])
        for m in ga.get("missing", []):
            ws3.append(["Missing", m["id"], m["name"], ""])

    path = Path(output_path)
    if not path.is_absolute():
        path = context.cwd / path
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))

    return ToolResult(
        output=f"XLSX report saved to: {path}\nCompany: {company['name']}\nSheets: Summary, SDG Alignment, Gap Analysis",
        metadata={"output_path": str(path), "format": "xlsx"},
    )
