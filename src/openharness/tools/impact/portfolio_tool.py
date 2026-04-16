"""Tool: Portfolio batch analysis with aggregated reporting.

Analyze multiple companies simultaneously and generate aggregated
impact metrics, SDG coverage, and framework compliance.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.models import Company
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sdg_goals
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class PortfolioInput(BaseModel):
    action: Literal["analyze_file", "analyze_companies", "aggregate"] = Field(
        description=(
            "'analyze_file': Analyze a portfolio CSV/YAML file. "
            "'analyze_companies': Analyze a list of companies provided inline. "
            "'aggregate': Generate aggregated portfolio metrics."
        )
    )
    file_path: str = Field(
        default="",
        description="Path to portfolio file (CSV or YAML) for 'analyze_file'",
    )
    companies: list[dict] = Field(
        default_factory=list,
        description=(
            "List of company dicts for 'analyze_companies'. Each dict should have: "
            "name, sector, description, impact_themes, reported_metrics, sdg_claims"
        ),
    )
    output_format: Literal["text", "json", "csv"] = Field(
        default="text", description="Output format: 'text', 'json', 'csv'"
    )


class PortfolioTool(BaseTool):
    name = "portfolio_analyze"
    description = (
        "Batch analyze a portfolio of companies for impact metrics, SDG alignment, "
        "and ESG coverage. Input a CSV/YAML file or a list of companies. "
        "Generates per-company scores and aggregated portfolio-level metrics including "
        "weighted SDG coverage, average 5-Dimension scores, and Core Metric Set compliance."
    )
    input_model = PortfolioInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, PortfolioInput) else PortfolioInput.model_validate(arguments)

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        if args.action == "analyze_file":
            if not args.file_path:
                return ToolResult(output="file_path required for analyze_file", is_error=True)
            companies = _load_portfolio_file(args.file_path, context)
            if isinstance(companies, str):
                return ToolResult(output=companies, is_error=True)
        elif args.action in ("analyze_companies", "aggregate"):
            companies = [_dict_to_company(d) for d in args.companies]
        else:
            return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

        if not companies:
            return ToolResult(output="No companies to analyze.", is_error=True)

        results = []
        for company in companies:
            result = _analyze_company(company, store)
            results.append(result)

        aggregate = _aggregate_results(results)

        if args.output_format == "json":
            return ToolResult(output=json.dumps({
                "portfolio_size": len(companies),
                "companies": results,
                "aggregate": aggregate,
            }, indent=2, default=str))

        if args.output_format == "csv":
            return ToolResult(output=_to_csv(results, aggregate))

        return ToolResult(output=_to_text(results, aggregate))


def _load_portfolio_file(file_path: str, context: ToolExecutionContext) -> list[Company] | str:
    """Load companies from a CSV or YAML portfolio file."""
    path = Path(file_path)
    if not path.is_absolute():
        path = context.cwd / path

    if not path.exists():
        return f"File not found: {path}"

    if path.suffix.lower() in (".yaml", ".yml"):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            return [_dict_to_company(d) for d in data]
        if isinstance(data, dict) and "companies" in data:
            return [_dict_to_company(d) for d in data["companies"]]
        return "YAML must contain a list of companies or a dict with 'companies' key"

    if path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            companies = []
            for row in reader:
                metrics = {}
                for key, val in row.items():
                    if key.startswith(("PI", "OI", "OD", "FP", "PD")) and val:
                        metrics[key] = val
                companies.append(Company(
                    name=row.get("name", row.get("company", "")),
                    sector=row.get("sector", ""),
                    description=row.get("description", ""),
                    impact_themes=[t.strip() for t in row.get("impact_themes", "").split(",") if t.strip()],
                    reported_metrics=metrics,
                    sdg_claims=[int(x.strip()) for x in row.get("sdg_claims", "").split(",") if x.strip().isdigit()],
                ))
            return companies

    return f"Unsupported file format: {path.suffix}"


def _dict_to_company(d: dict) -> Company:
    metrics, _ = normalize_metric_map(d.get("reported_metrics", {}))
    sdg_claims, _ = normalize_sdg_goals(d.get("sdg_claims", []))
    return Company(
        name=d.get("name", ""),
        sector=d.get("sector", ""),
        description=d.get("description", ""),
        impact_themes=infer_themes(f"{d.get('description', '')} {d.get('sector', '')}", d.get("impact_themes", [])),
        reported_metrics=metrics,
        sdg_claims=sdg_claims,
    )


def _analyze_company(company: Company, store) -> dict:
    """Run full impact analysis on a single company."""
    five_dim = assess_five_dimensions(company, store)
    sdg = map_sdg_alignment(company, store)
    gaps = analyze_gaps(company, store)

    top_sdgs = [a for a in sdg if a.score > 0]

    return {
        "name": company.name,
        "sector": company.sector,
        "metrics_reported": len(company.reported_metrics),
        "five_dim_score": round(five_dim.overall_score, 2),
        "five_dim_grade": five_dim.overall_grade,
        "what": round(five_dim.what.score, 2),
        "who": round(five_dim.who.score, 2),
        "how_much": round(five_dim.how_much.score, 2),
        "contribution": round(five_dim.contribution.score, 2),
        "risk": round(five_dim.risk.score, 2),
        "sdg_count": len(top_sdgs),
        "top_sdgs": [{"goal": a.goal, "score": a.score} for a in top_sdgs[:5]],
        "gap_coverage": gaps["coverage_percentage"],
        "gap_missing": gaps["metrics_missing"],
    }


def _aggregate_results(results: list[dict]) -> dict:
    """Compute portfolio-level aggregated metrics."""
    n = len(results)
    if n == 0:
        return {}

    avg_5d = round(sum(r["five_dim_score"] for r in results) / n, 2)
    avg_gap = round(sum(r["gap_coverage"] for r in results) / n, 1)

    all_sdg_goals: dict[int, int] = {}
    for r in results:
        for sdg in r["top_sdgs"]:
            g = sdg["goal"]
            all_sdg_goals[g] = all_sdg_goals.get(g, 0) + 1

    sdg_distribution = sorted(all_sdg_goals.items(), key=lambda x: x[1], reverse=True)

    dim_avgs = {}
    for dim in ("what", "who", "how_much", "contribution", "risk"):
        dim_avgs[dim] = round(sum(r[dim] for r in results) / n, 2)

    grade_dist: dict[str, int] = {}
    for r in results:
        g = r["five_dim_grade"]
        grade_dist[g] = grade_dist.get(g, 0) + 1

    return {
        "portfolio_size": n,
        "avg_five_dim_score": avg_5d,
        "avg_gap_coverage": avg_gap,
        "dimension_averages": dim_avgs,
        "grade_distribution": grade_dist,
        "sdg_distribution": [{"goal": g, "companies": c} for g, c in sdg_distribution[:10]],
        "total_metrics_reported": sum(r["metrics_reported"] for r in results),
    }


def _to_text(results: list[dict], aggregate: dict) -> str:
    lines = [
        "PORTFOLIO IMPACT ANALYSIS",
        "=" * 60,
        f"Companies analyzed: {len(results)}",
        "",
    ]

    for r in results:
        sdg_str = ", ".join(f"SDG {s['goal']}" for s in r["top_sdgs"][:3])
        lines.append(f"  {r['name']} ({r['sector']})")
        lines.append(f"    5D Score: {r['five_dim_score']}/5 ({r['five_dim_grade']}) | Core Metrics: {r['gap_coverage']}%")
        lines.append(f"    SDGs: {sdg_str or 'None'} | Metrics: {r['metrics_reported']}")
        lines.append("")

    lines.append("PORTFOLIO AGGREGATES")
    lines.append("-" * 40)
    lines.append(f"  Avg 5D Score: {aggregate.get('avg_five_dim_score', 0)}/5")
    lines.append(f"  Avg Core Metric Coverage: {aggregate.get('avg_gap_coverage', 0)}%")

    dim_avgs = aggregate.get("dimension_averages", {})
    if dim_avgs:
        lines.append("  Dimension Averages:")
        for dim, avg in dim_avgs.items():
            lines.append(f"    {dim}: {avg}/5")

    sdg_dist = aggregate.get("sdg_distribution", [])
    if sdg_dist:
        lines.append("  SDG Distribution:")
        for item in sdg_dist[:5]:
            lines.append(f"    SDG {item['goal']}: {item['companies']} companies")

    grade_dist = aggregate.get("grade_distribution", {})
    if grade_dist:
        lines.append(f"  Grade Distribution: {', '.join(f'{g}: {c}' for g, c in sorted(grade_dist.items()))}")

    return "\n".join(lines)


def _to_csv(results: list[dict], aggregate: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Company", "Sector", "5D Score", "Grade", "What", "Who", "How Much",
                      "Contribution", "Risk", "SDG Count", "Gap Coverage %", "Metrics Reported"])
    for r in results:
        writer.writerow([
            r["name"], r["sector"], r["five_dim_score"], r["five_dim_grade"],
            r["what"], r["who"], r["how_much"], r["contribution"], r["risk"],
            r["sdg_count"], r["gap_coverage"], r["metrics_reported"],
        ])

    writer.writerow([])
    writer.writerow(["PORTFOLIO AGGREGATE"])
    writer.writerow(["Avg 5D Score", aggregate.get("avg_five_dim_score", "")])
    writer.writerow(["Avg Gap Coverage", aggregate.get("avg_gap_coverage", "")])

    return output.getvalue()
