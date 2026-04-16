"""Tool: Portfolio batch analysis with aggregated reporting.

Analyze multiple companies simultaneously and generate aggregated
impact metrics, SDG coverage, and framework compliance.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from typing import Literal

from openharness.impact.database import get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.fund_analytics import (
    assess_portfolio_additionality,
    compute_weighted_sdg_contribution,
    impact_weighted_returns_stub,
)
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.models import Company
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.tools.impact.common import infer_themes, normalize_impact_targets, normalize_metric_map, normalize_sdg_goals
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class PortfolioInput(BaseModel):
    action: Literal[
        "analyze_file", "analyze_companies", "aggregate", "what_if",
        "rollup", "benchmark", "lp_report", "attribution",
    ] = Field(
        description=(
            "'analyze_file': Analyze a portfolio CSV/YAML file. "
            "'analyze_companies': Analyze a list of companies provided inline. "
            "'aggregate': Generate aggregated portfolio metrics. "
            "'what_if': Scenario analysis — add/remove companies and see portfolio impact. "
            "'rollup': Portfolio roll-up analytics (beneficiaries, SDG coverage, fund-level 5D). "
            "'benchmark': Cross-company benchmarking (rank by key metrics). "
            "'lp_report': Fund-level LP report (ILPA/GIIN format). "
            "'attribution': Impact attribution by company, sector, geography, and SDG."
        )
    )
    file_path: str = Field(
        default="",
        description="Path to portfolio file (CSV/YAML/JSON) for 'analyze_file'",
    )
    companies: list[dict] = Field(
        default_factory=list,
        description=(
            "List of company dicts for 'analyze_companies'. Each dict should have: "
            "name, sector, description, impact_themes, reported_metrics, sdg_claims"
        ),
    )
    geography: str = Field(
        default="", description="Default geography for companies without one specified"
    )
    output_format: Literal["text", "json", "csv"] = Field(
        default="text", description="Output format: 'text', 'json', 'csv'"
    )
    add_companies: list[dict] = Field(
        default_factory=list,
        description="Companies to add in 'what_if' mode (same format as 'companies')",
    )
    remove_companies: list[str] = Field(
        default_factory=list,
        description="Company names to remove in 'what_if' mode",
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
        elif args.action == "what_if":
            companies = [_dict_to_company(d) for d in args.companies]
            return self._what_if(companies, args, store)
        elif args.action in ("rollup", "benchmark", "lp_report", "attribution"):
            companies = [_dict_to_company(d) for d in args.companies]
            if not companies and args.file_path:
                companies = _load_portfolio_file(args.file_path, context)
                if isinstance(companies, str):
                    return ToolResult(output=companies, is_error=True)
            if not companies:
                return ToolResult(output="No companies provided.", is_error=True)
            results = [_analyze_company(c, store) for c in companies]
            aggregate = _aggregate_results(results)
            if args.action == "rollup":
                return ToolResult(output=_portfolio_rollup(results, aggregate, companies))
            elif args.action == "benchmark":
                return ToolResult(output=_cross_company_benchmark(results))
            elif args.action == "lp_report":
                return ToolResult(output=_fund_lp_report(results, aggregate))
            else:
                return ToolResult(output=_impact_attribution(results, aggregate))
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

    def _what_if(self, base_companies: list[Company], args: PortfolioInput, store) -> ToolResult:
        """Scenario analysis: show how adding/removing companies changes portfolio scores."""
        base_results = [_analyze_company(c, store) for c in base_companies]
        base_aggregate = _aggregate_results(base_results)

        remove_names = {n.lower() for n in args.remove_companies}
        scenario_results = [r for r in base_results if r["name"].lower() not in remove_names]
        for d in args.add_companies:
            new_company = _dict_to_company(d)
            scenario_results.append(_analyze_company(new_company, store))

        scenario_aggregate = _aggregate_results(scenario_results) if scenario_results else {}

        lines = [
            "WHAT-IF SCENARIO ANALYSIS",
            "=" * 60,
            f"Baseline: {len(base_results)} companies",
            f"Scenario: {len(scenario_results)} companies",
        ]
        if args.remove_companies:
            lines.append(f"  Removed: {', '.join(args.remove_companies)}")
        if args.add_companies:
            lines.append(f"  Added: {', '.join(d.get('name', 'Unknown') for d in args.add_companies)}")
        lines.append("")

        comparisons = [
            ("5D Score (avg)", "avg_five_dim_score"),
            ("Gap Coverage (avg %)", "avg_gap_coverage"),
            ("SDG Coverage", "sdg_coverage"),
            ("Total Metrics", "total_metrics_reported"),
        ]
        lines.append(f"{'Metric':<30} {'Baseline':>10} {'Scenario':>10} {'Delta':>10}")
        lines.append("-" * 60)
        for label, key in comparisons:
            base_val = base_aggregate.get(key, 0)
            scen_val = scenario_aggregate.get(key, 0)
            delta = round(scen_val - base_val, 2) if isinstance(base_val, (int, float)) else "N/A"
            arrow = "↑" if isinstance(delta, (int, float)) and delta > 0 else "↓" if isinstance(delta, (int, float)) and delta < 0 else "="
            lines.append(f"{label:<30} {base_val:>10} {scen_val:>10} {f'{delta:+}':>8} {arrow}")

        lines.append("")
        additionality_base = base_aggregate.get("additionality", {})
        additionality_scen = scenario_aggregate.get("additionality", {})
        if additionality_base and additionality_scen:
            lines.append(f"Additionality: {additionality_base.get('additionality_score', 0)} → {additionality_scen.get('additionality_score', 0)}")

        return ToolResult(
            output="\n".join(lines),
            metadata={
                "baseline": base_aggregate,
                "scenario": scenario_aggregate,
            },
        )


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
                    geography=row.get("geography", ""),
                    impact_themes=[t.strip() for t in row.get("impact_themes", "").split(",") if t.strip()],
                    reported_metrics=metrics,
                    sdg_claims=[int(x.strip()) for x in row.get("sdg_claims", "").split(",") if x.strip().isdigit()],
                ))
            return companies

    return f"Unsupported file format: {path.suffix}"


def _dict_to_company(d: dict) -> Company:
    metrics, _ = normalize_metric_map(d.get("reported_metrics", {}))
    sdg_claims, _ = normalize_sdg_goals(d.get("sdg_claims", []))
    impact_targets, _ = normalize_impact_targets(d.get("impact_targets", []))
    return Company(
        name=d.get("name", ""),
        sector=d.get("sector", ""),
        description=d.get("description", ""),
        geography=d.get("geography", ""),
        impact_themes=infer_themes(f"{d.get('description', '')} {d.get('sector', '')}", d.get("impact_themes", [])),
        reported_metrics=metrics,
        sdg_claims=sdg_claims,
        impact_targets=impact_targets,
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
        "geography": company.geography or "",
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
    """Compute portfolio-level aggregated metrics with fund analytics."""
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

    five_d_scores = [r["five_dim_score"] for r in results]
    min_5d = round(min(five_d_scores), 2)
    max_5d = round(max(five_d_scores), 2)
    median_5d = round(sorted(five_d_scores)[n // 2], 2) if n > 0 else 0

    sector_dist: dict[str, int] = {}
    for r in results:
        s = r.get("sector") or "Unknown"
        sector_dist[s] = sector_dist.get(s, 0) + 1

    geo_dist: dict[str, int] = {}
    for r in results:
        g = r.get("geography") or "Not specified"
        geo_dist[g] = geo_dist.get(g, 0) + 1

    weakest_dim = min(dim_avgs, key=dim_avgs.get) if dim_avgs else ""
    strongest_dim = max(dim_avgs, key=dim_avgs.get) if dim_avgs else ""

    sdg_coverage = len(all_sdg_goals)

    reporting_quality = "high" if avg_gap >= 60 else "medium" if avg_gap >= 30 else "low"

    weighted_sdg = compute_weighted_sdg_contribution(results)
    additionality = assess_portfolio_additionality(results)
    iwr = impact_weighted_returns_stub(results)

    return {
        "portfolio_size": n,
        "avg_five_dim_score": avg_5d,
        "min_five_dim_score": min_5d,
        "max_five_dim_score": max_5d,
        "median_five_dim_score": median_5d,
        "avg_gap_coverage": avg_gap,
        "dimension_averages": dim_avgs,
        "strongest_dimension": strongest_dim,
        "weakest_dimension": weakest_dim,
        "grade_distribution": grade_dist,
        "sector_distribution": sector_dist,
        "geography_distribution": geo_dist,
        "sdg_distribution": [{"goal": g, "companies": c} for g, c in sdg_distribution[:17]],
        "sdg_coverage": sdg_coverage,
        "total_metrics_reported": sum(r["metrics_reported"] for r in results),
        "reporting_quality": reporting_quality,
        "weighted_sdg_contribution": weighted_sdg,
        "additionality": additionality,
        "impact_weighted_returns": iwr,
    }


def _compare_yoy(current: dict, previous: dict | None) -> dict:
    """Compare current portfolio aggregate with a previous period's aggregate."""
    if not previous:
        return {}
    changes: dict = {}
    for key in ("avg_five_dim_score", "avg_gap_coverage", "total_metrics_reported", "sdg_coverage"):
        curr_val = current.get(key, 0)
        prev_val = previous.get(key, 0)
        if prev_val and prev_val != 0:
            changes[key] = {
                "current": curr_val,
                "previous": prev_val,
                "change": round(curr_val - prev_val, 2),
                "change_pct": round((curr_val - prev_val) / prev_val * 100, 1),
            }
    for dim in ("what", "who", "how_much", "contribution", "risk"):
        curr_dim = current.get("dimension_averages", {}).get(dim, 0)
        prev_dim = previous.get("dimension_averages", {}).get(dim, 0)
        if prev_dim:
            changes[f"dim_{dim}"] = {
                "current": curr_dim,
                "previous": prev_dim,
                "change": round(curr_dim - prev_dim, 2),
            }
    return changes


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

    lines.append("FUND-LEVEL ANALYTICS")
    lines.append("-" * 40)
    lines.append(f"  5D Score: avg {aggregate.get('avg_five_dim_score', 0)}/5 | "
                 f"min {aggregate.get('min_five_dim_score', 0)} | "
                 f"max {aggregate.get('max_five_dim_score', 0)} | "
                 f"median {aggregate.get('median_five_dim_score', 0)}")
    lines.append(f"  Core Metric Coverage: avg {aggregate.get('avg_gap_coverage', 0)}% "
                 f"(reporting quality: {aggregate.get('reporting_quality', 'unknown')})")
    lines.append(f"  Total IRIS+ Metrics Reported: {aggregate.get('total_metrics_reported', 0)}")
    lines.append(f"  SDG Coverage: {aggregate.get('sdg_coverage', 0)}/17 goals")

    dim_avgs = aggregate.get("dimension_averages", {})
    if dim_avgs:
        lines.append("  Dimension Averages:")
        for dim, avg in dim_avgs.items():
            lines.append(f"    {dim.replace('_', ' ').title()}: {avg}/5")
        lines.append(f"  Strongest: {aggregate.get('strongest_dimension', '').replace('_', ' ').title()}")
        lines.append(f"  Weakest:   {aggregate.get('weakest_dimension', '').replace('_', ' ').title()}")

    sector_dist = aggregate.get("sector_distribution", {})
    if sector_dist:
        lines.append("  Sector Distribution:")
        for sect, count in sorted(sector_dist.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"    {sect}: {count} companies")

    geo_dist = aggregate.get("geography_distribution", {})
    if geo_dist and not (len(geo_dist) == 1 and "Not specified" in geo_dist):
        lines.append("  Geography Distribution:")
        for geo, count in sorted(geo_dist.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"    {geo}: {count} companies")

    sdg_dist = aggregate.get("sdg_distribution", [])
    if sdg_dist:
        lines.append("  SDG Distribution:")
        for item in sdg_dist[:10]:
            lines.append(f"    SDG {item['goal']}: {item['companies']} companies")

    grade_dist = aggregate.get("grade_distribution", {})
    if grade_dist:
        lines.append(f"  Grade Distribution: {', '.join(f'{g}: {c}' for g, c in sorted(grade_dist.items()))}")

    weighted_sdg = aggregate.get("weighted_sdg_contribution", {})
    if weighted_sdg:
        lines.append("")
        lines.append("WEIGHTED SDG CONTRIBUTION (materiality-adjusted)")
        lines.append("-" * 40)
        for goal, score in list(weighted_sdg.items())[:10]:
            lines.append(f"  SDG {goal}: {score}")

    additionality = aggregate.get("additionality", {})
    if additionality:
        lines.append("")
        lines.append("PORTFOLIO ADDITIONALITY ASSESSMENT")
        lines.append("-" * 40)
        lines.append(f"  Score: {additionality.get('additionality_score', 0)}/100 "
                     f"({additionality.get('classification', 'N/A')})")
        for signal in additionality.get("signals", []):
            lines.append(f"  + {signal}")
        if additionality.get("recommendation"):
            lines.append(f"  Recommendation: {additionality['recommendation']}")

    iwr = aggregate.get("impact_weighted_returns", {})
    if iwr:
        lines.append("")
        lines.append("IMPACT-WEIGHTED RETURNS")
        lines.append("-" * 40)
        lines.append(f"  Status: {iwr.get('status', 'N/A')}")
        lines.append(f"  Portfolio impact score: {iwr.get('portfolio_impact_score', 0)}")
        if iwr.get("note"):
            lines.append(f"  Note: {iwr['note']}")

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


def _portfolio_rollup(results: list[dict], aggregate: dict, companies: list) -> str:
    """Generate portfolio roll-up analytics."""
    lines = [
        "PORTFOLIO ROLL-UP ANALYTICS",
        "=" * 60,
        f"Portfolio Size: {len(results)} companies",
        "",
        "FUND-LEVEL 5D SCORES",
        "-" * 40,
        f"  Average: {aggregate.get('avg_five_dim_score', 0)}/5",
        f"  Median:  {aggregate.get('median_five_dim_score', 0)}/5",
        f"  Range:   {aggregate.get('min_five_dim_score', 0)} - {aggregate.get('max_five_dim_score', 0)}",
        "",
    ]

    dim_avgs = aggregate.get("dimension_averages", {})
    if dim_avgs:
        lines.append("  Dimension Averages:")
        for dim, avg in dim_avgs.items():
            lines.append(f"    {dim.replace('_', ' ').title():20s}: {avg}/5")

    lines.extend(["", "SDG COVERAGE", "-" * 40])
    lines.append(f"  Goals covered: {aggregate.get('sdg_coverage', 0)}/17")
    sdg_dist = aggregate.get("sdg_distribution", [])
    for item in sdg_dist:
        pct = round(item["companies"] / len(results) * 100) if results else 0
        lines.append(f"    SDG {item['goal']:2d}: {item['companies']} companies ({pct}%)")

    lines.extend(["", "AGGREGATE METRICS", "-" * 40])
    lines.append(f"  Total Metrics Reported: {aggregate.get('total_metrics_reported', 0)}")
    lines.append(f"  Avg Metric Coverage: {aggregate.get('avg_gap_coverage', 0)}%")
    lines.append(f"  Reporting Quality: {aggregate.get('reporting_quality', 'unknown')}")

    grade_dist = aggregate.get("grade_distribution", {})
    if grade_dist:
        lines.append(f"  Grade Distribution: {', '.join(f'{g}:{c}' for g, c in sorted(grade_dist.items()))}")

    return "\n".join(lines)


def _cross_company_benchmark(results: list[dict]) -> str:
    """Rank portfolio companies on key metrics."""
    lines = [
        "CROSS-COMPANY BENCHMARKING",
        "=" * 60, "",
    ]

    by_5d = sorted(results, key=lambda r: r["five_dim_score"], reverse=True)
    lines.append("By 5D Score (ranked):")
    for i, r in enumerate(by_5d, 1):
        marker = " ★" if i <= 3 else " ▼" if i >= len(by_5d) - 1 else ""
        lines.append(f"  {i:2d}. {r['name']:30s} {r['five_dim_score']}/5 ({r['five_dim_grade']}){marker}")

    lines.append("")
    by_coverage = sorted(results, key=lambda r: r["gap_coverage"], reverse=True)
    lines.append("By Metric Coverage (ranked):")
    for i, r in enumerate(by_coverage, 1):
        lines.append(f"  {i:2d}. {r['name']:30s} {r['gap_coverage']}%")

    lines.append("")
    dims = ("what", "who", "how_much", "contribution", "risk")
    lines.append("Dimension Leaders:")
    for dim in dims:
        leader = max(results, key=lambda r: r.get(dim, 0))
        laggard = min(results, key=lambda r: r.get(dim, 0))
        lines.append(
            f"  {dim.replace('_', ' ').title():15s} | "
            f"Leader: {leader['name']} ({leader[dim]}) | "
            f"Laggard: {laggard['name']} ({laggard[dim]})"
        )

    return "\n".join(lines)


def _fund_lp_report(results: list[dict], aggregate: dict) -> str:
    """Generate a fund-level LP report in ILPA/GIIN format."""
    lines = [
        "=" * 70,
        "FUND IMPACT REPORT — FOR LP DISTRIBUTION",
        "=" * 70, "",
        "FUND OVERVIEW",
        "-" * 40,
        f"Portfolio Size: {aggregate.get('portfolio_size', 0)} companies",
        f"Fund-Level 5D Score: {aggregate.get('avg_five_dim_score', 0)}/5",
        f"SDG Coverage: {aggregate.get('sdg_coverage', 0)}/17 goals",
        f"Core Metric Coverage: {aggregate.get('avg_gap_coverage', 0)}%",
        f"Reporting Quality: {aggregate.get('reporting_quality', 'N/A')}",
        "",
    ]

    additionality = aggregate.get("additionality", {})
    if additionality:
        lines.append("ADDITIONALITY ASSESSMENT")
        lines.append("-" * 40)
        lines.append(f"  Score: {additionality.get('additionality_score', 0)}/100 ({additionality.get('classification', 'N/A')})")
        lines.append("")

    lines.append("PORTFOLIO COMPANIES")
    lines.append("-" * 40)
    for r in results:
        sdg_str = ", ".join(f"SDG {s['goal']}" for s in r.get("top_sdgs", [])[:3])
        lines.append(f"  {r['name']}")
        lines.append(f"    Sector: {r.get('sector', 'N/A')} | Geography: {r.get('geography', 'N/A')}")
        lines.append(f"    5D: {r['five_dim_score']}/5 ({r['five_dim_grade']}) | Coverage: {r['gap_coverage']}% | SDGs: {sdg_str}")
        lines.append("")

    dim_avgs = aggregate.get("dimension_averages", {})
    if dim_avgs:
        lines.append("DIMENSION PERFORMANCE (Fund Average)")
        lines.append("-" * 40)
        for dim, avg in dim_avgs.items():
            bar = "█" * int(avg) + "░" * (5 - int(avg))
            lines.append(f"  {dim.replace('_', ' ').title():15s} {bar} {avg}/5")

    lines.extend([
        "", "─" * 70,
        "Generated by Impact Vision. This report follows ILPA/GIIN format guidelines.",
        "All scores should be validated through independent verification.",
        "─" * 70,
    ])
    return "\n".join(lines)


def _impact_attribution(results: list[dict], aggregate: dict) -> str:
    """Break down portfolio impact by company, sector, geography, and SDG."""
    lines = [
        "IMPACT ATTRIBUTION ANALYSIS",
        "=" * 60, "",
    ]

    total_score = sum(r["five_dim_score"] for r in results)
    lines.append("BY COMPANY (% of total impact)")
    lines.append("-" * 40)
    for r in sorted(results, key=lambda x: x["five_dim_score"], reverse=True):
        pct = round(r["five_dim_score"] / total_score * 100, 1) if total_score else 0
        lines.append(f"  {r['name']:30s} {r['five_dim_score']}/5 ({pct}%)")
    lines.append("")

    sector_scores: dict[str, list[float]] = {}
    for r in results:
        s = r.get("sector") or "Unknown"
        sector_scores.setdefault(s, []).append(r["five_dim_score"])
    lines.append("BY SECTOR")
    lines.append("-" * 40)
    for sect, scores in sorted(sector_scores.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True):
        avg = round(sum(scores) / len(scores), 2)
        lines.append(f"  {sect:20s} {len(scores)} companies | Avg 5D: {avg}/5")
    lines.append("")

    geo_scores: dict[str, list[float]] = {}
    for r in results:
        g = r.get("geography") or "Not specified"
        geo_scores.setdefault(g, []).append(r["five_dim_score"])
    if geo_scores and not (len(geo_scores) == 1 and "Not specified" in geo_scores):
        lines.append("BY GEOGRAPHY")
        lines.append("-" * 40)
        for geo, scores in sorted(geo_scores.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True):
            avg = round(sum(scores) / len(scores), 2)
            lines.append(f"  {geo:20s} {len(scores)} companies | Avg 5D: {avg}/5")
        lines.append("")

    sdg_companies: dict[int, list[str]] = {}
    for r in results:
        for sdg in r.get("top_sdgs", []):
            sdg_companies.setdefault(sdg["goal"], []).append(r["name"])
    lines.append("BY SDG")
    lines.append("-" * 40)
    for goal, names in sorted(sdg_companies.items()):
        lines.append(f"  SDG {goal:2d}: {len(names)} companies — {', '.join(names[:5])}")

    return "\n".join(lines)
