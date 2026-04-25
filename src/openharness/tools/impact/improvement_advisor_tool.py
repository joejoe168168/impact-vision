"""Tool: LLM-guided impact improvement advisor.

Generates actionable recommendations, peer comparison insights,
and SDG opportunity identification based on assessment data.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.benchmarks import SECTOR_BENCHMARKS
from openharness.impact.database import get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.models import Company
from openharness.impact.sdg_mapper import generate_sdg_gap_recommendations, map_sdg_alignment
from openharness.impact.sdg_taxonomy import get_sdg_goal
from openharness.tools.impact.common import (
    infer_themes,
    normalize_metric_map,
    normalize_sdg_goals,
    normalize_sector,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


_DIMENSION_IMPROVEMENT_STRATEGIES: dict[str, list[dict[str, str]]] = {
    "what": [
        {"metric": "PI4060", "action": "Track impact category (positive/negative/both)", "effort": "quick win"},
        {"metric": "PI2028", "action": "Define and track specific outcome indicators", "effort": "medium-term"},
        {"metric": "PI1779", "action": "Measure changes in target population well-being", "effort": "medium-term"},
    ],
    "who": [
        {"metric": "PI9468", "action": "Define and characterize target beneficiary population", "effort": "quick win"},
        {"metric": "PI3468", "action": "Track demographics of beneficiaries served", "effort": "medium-term"},
        {"metric": "OI8536", "action": "Measure reach into underserved/marginalized populations", "effort": "medium-term"},
    ],
    "how_much": [
        {"metric": "PI5490", "action": "Quantify scale of impact (total beneficiaries reached)", "effort": "quick win"},
        {"metric": "PI1855", "action": "Measure depth of impact per beneficiary", "effort": "medium-term"},
        {"metric": "PI4840", "action": "Track duration of impact sustainability", "effort": "strategic"},
    ],
    "contribution": [
        {"metric": "PI7734", "action": "Establish counterfactual or baseline comparison", "effort": "medium-term"},
        {"metric": "OI6074", "action": "Document additionality — what would not have happened without you", "effort": "medium-term"},
        {"metric": "PI3922", "action": "Get independent verification of impact claims", "effort": "strategic"},
    ],
    "risk": [
        {"metric": "PI3230", "action": "Assess and document potential negative impacts", "effort": "quick win"},
        {"metric": "PI7985", "action": "Implement mitigation strategies for identified risks", "effort": "medium-term"},
        {"metric": "OI2734", "action": "Set up regular stakeholder feedback loops", "effort": "medium-term"},
    ],
}

_SECTOR_PEER_PATTERNS: dict[str, dict[str, list[str]]] = {
    "agriculture": {
        "common_metrics": ["PI5490", "OI4112", "PI2028", "OI8536", "PI1779"],
        "typical_programs": ["Smallholder training", "Sustainable sourcing", "Climate-resilient varieties"],
        "partnerships": ["Agricultural extension services", "Microfinance institutions", "Research institutes"],
    },
    "healthcare": {
        "common_metrics": ["PI5490", "PI2028", "PI3468", "OI8536", "PI1855"],
        "typical_programs": ["Community health workers", "Telemedicine", "Preventive care"],
        "partnerships": ["Ministries of Health", "WHO", "Local NGOs"],
    },
    "fintech": {
        "common_metrics": ["PI5490", "PI9468", "OI4869", "PI3468", "OI8536"],
        "typical_programs": ["Financial literacy", "Agent banking", "Credit scoring for underserved"],
        "partnerships": ["Central banks", "MFIs", "Mobile network operators"],
    },
    "energy": {
        "common_metrics": ["OI4112", "PI5490", "PI2028", "OI1395", "OI6074"],
        "typical_programs": ["Off-grid solar", "Mini-grids", "Clean cooking"],
        "partnerships": ["Energy regulators", "Development finance", "Technology providers"],
    },
    "education": {
        "common_metrics": ["PI5490", "PI2028", "PI3468", "PI1855", "OI8536"],
        "typical_programs": ["EdTech platforms", "Teacher training", "Scholarship programs"],
        "partnerships": ["Ministries of Education", "UNICEF", "Corporate partners"],
    },
}


class ImprovementAdvisorInput(BaseModel):
    action: Literal[
        "recommend", "peer_insights", "sdg_opportunities",
    ] = Field(description="Advisory action")
    company_name: str = ""
    company_description: str = ""
    sector: str = ""
    geography: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    focus_dimensions: list[str] = Field(
        default_factory=list,
        description="Limit recommendations to specific dimensions (e.g. ['what', 'risk'])",
    )
    top_n: int = Field(default=10, description="Number of recommendations to return")


class ImprovementAdvisorTool(BaseTool):
    name = "improvement_advisor"
    description = (
        "Generate actionable impact improvement recommendations. Three modes: "
        "'recommend' for dimension-specific improvement plans, "
        "'peer_insights' for sector peer comparison, "
        "'sdg_opportunities' for untapped SDG alignment."
    )
    input_model = ImprovementAdvisorInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ImprovementAdvisorInput) else ImprovementAdvisorInput.model_validate(arguments)

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        reported_metrics, _ = normalize_metric_map(args.reported_metrics)
        sdg_claims, _ = normalize_sdg_goals(args.sdg_claims)
        themes = infer_themes(f"{args.company_description} {args.sector}", args.impact_themes)
        company = Company(
            name=args.company_name or "Company",
            description=args.company_description,
            sector=normalize_sector(args.sector),
            geography=args.geography,
            impact_themes=themes,
            reported_metrics=reported_metrics,
            sdg_claims=sdg_claims,
        )

        if args.action == "recommend":
            return self._recommend(company, store, args)
        elif args.action == "peer_insights":
            return self._peer_insights(company, store, args)
        elif args.action == "sdg_opportunities":
            return self._sdg_opportunities(company, store, args)
        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

    def _recommend(self, company: Company, store, args: ImprovementAdvisorInput) -> ToolResult:
        fd = assess_five_dimensions(company, store)
        dims = {
            "what": fd.what, "who": fd.who, "how_much": fd.how_much,
            "contribution": fd.contribution, "risk": fd.risk,
        }

        focus = args.focus_dimensions or sorted(dims, key=lambda d: dims[d].score)
        lines = [
            f"IMPROVEMENT RECOMMENDATIONS: {company.name}",
            f"Overall Score: {fd.overall_score:.1f}/5 (Grade: {fd.overall_grade})",
            "=" * 60, "",
        ]

        recs_count = 0
        for dim_name in focus:
            dim = dims.get(dim_name)
            if not dim:
                continue
            lines.append(f"{dim.dimension} (Current: {dim.score}/5, {dim.provenance})")
            lines.append("-" * 40)

            strategies = _DIMENSION_IMPROVEMENT_STRATEGIES.get(dim_name, [])
            reported = set(company.reported_metrics.keys())
            for s in strategies:
                if recs_count >= args.top_n:
                    break
                status = "✓ Already tracking" if s["metric"] in reported else "→ Recommended"
                lines.append(f"  [{s['effort']:12s}] {status}: {s['action']}")
                lines.append(f"    Metric: {s['metric']}")
                recs_count += 1

            for gap in dim.gaps[:3]:
                if recs_count >= args.top_n:
                    break
                lines.append(f"  [gap         ] → Report: {gap}")
                recs_count += 1

            lines.append("")

        return ToolResult(output="\n".join(lines))

    def _peer_insights(self, company: Company, store, args: ImprovementAdvisorInput) -> ToolResult:
        sector = company.sector.lower().strip()
        lines = [
            f"PEER COMPARISON INSIGHTS: {company.name}",
            f"Sector: {company.sector}",
            "=" * 60, "",
        ]

        peer_data = None
        for key in _SECTOR_PEER_PATTERNS:
            if key in sector:
                peer_data = _SECTOR_PEER_PATTERNS[key]
                break

        if not peer_data:
            lines.append(f"No peer data available for sector '{company.sector}'.")
            lines.append("Available sectors: " + ", ".join(_SECTOR_PEER_PATTERNS.keys()))
            return ToolResult(output="\n".join(lines))

        reported = set(company.reported_metrics.keys())
        common = peer_data.get("common_metrics", [])
        tracked = [m for m in common if m in reported]
        missing = [m for m in common if m not in reported]

        lines.append("METRICS COMMONLY TRACKED BY PEERS")
        lines.append("-" * 40)
        for m in tracked:
            lines.append(f"  ✓ {m} — You track this (good!)")
        for m in missing:
            lines.append(f"  ✗ {m} — Peers track this, you don't")
        lines.append(f"\n  Coverage: {len(tracked)}/{len(common)} peer-common metrics")

        programs = peer_data.get("typical_programs", [])
        if programs:
            lines.append("\nTYPICAL PROGRAMS IN YOUR SECTOR")
            lines.append("-" * 40)
            for p in programs:
                lines.append(f"  • {p}")

        partners = peer_data.get("partnerships", [])
        if partners:
            lines.append("\nCOMMON PARTNERSHIP TYPES")
            lines.append("-" * 40)
            for p in partners:
                lines.append(f"  • {p}")

        bm = SECTOR_BENCHMARKS.get(sector, {})
        if bm:
            lines.append("\nSECTOR BENCHMARKS")
            lines.append("-" * 40)
            bm_scores = bm.get("five_d", {})
            for dim, score in bm_scores.items():
                lines.append(f"  {dim.replace('_', ' ').title()}: {score}/5 (sector average)")

        return ToolResult(output="\n".join(lines))

    def _sdg_opportunities(self, company: Company, store, args: ImprovementAdvisorInput) -> ToolResult:
        sdg_results = map_sdg_alignment(company, store)
        gap_recs = generate_sdg_gap_recommendations(sdg_results, company, store)

        scored = {a.goal: a for a in sdg_results if a.score > 0}
        all_goals = set(range(1, 18))
        unscored = all_goals - set(scored.keys())

        lines = [
            f"SDG OPPORTUNITY ANALYSIS: {company.name}",
            f"Currently aligned: {len(scored)}/17 goals",
            "=" * 60, "",
        ]

        lines.append("STRENGTHEN EXISTING ALIGNMENTS")
        lines.append("-" * 40)
        for goal_num, recs in sorted(gap_recs.items()):
            alignment = scored.get(goal_num)
            if alignment:
                lines.append(f"\n  SDG {goal_num} ({alignment.goal_name}) — Score: {alignment.score}/100")
                for r in recs:
                    lines.append(f"    → {r}")

        sector_sdg_affinity = self._get_sector_sdg_affinity(company.sector)
        if sector_sdg_affinity and unscored:
            lines.append("\n\nUNTAPPED OPPORTUNITIES")
            lines.append("-" * 40)
            for goal_num in sorted(unscored):
                if goal_num in sector_sdg_affinity:
                    goal = get_sdg_goal(goal_num)
                    name = goal.name if goal else f"Goal {goal_num}"
                    lines.append(f"  SDG {goal_num} ({name})")
                    lines.append(f"    Sector affinity: {sector_sdg_affinity[goal_num]}")

        return ToolResult(output="\n".join(lines))

    def _get_sector_sdg_affinity(self, sector: str) -> dict[int, str]:
        sector_lower = sector.lower()
        affinities: dict[int, str] = {}
        if "agri" in sector_lower:
            affinities = {2: "Direct food production", 15: "Land use management", 6: "Water stewardship"}
        elif "health" in sector_lower:
            affinities = {3: "Core health outcomes", 10: "Health equity", 5: "Women's health"}
        elif "fin" in sector_lower:
            affinities = {1: "Poverty reduction via inclusion", 8: "Economic growth", 10: "Inequality reduction"}
        elif "energy" in sector_lower:
            affinities = {7: "Clean energy access", 13: "Climate action", 11: "Sustainable cities"}
        elif "edu" in sector_lower:
            affinities = {4: "Quality education", 5: "Gender equity", 8: "Decent work skills"}
        elif "tech" in sector_lower:
            affinities = {9: "Innovation infrastructure", 11: "Smart cities", 17: "Partnerships"}
        elif "water" in sector_lower:
            affinities = {6: "Clean water", 14: "Marine ecosystems", 3: "Health via sanitation"}
        return affinities
