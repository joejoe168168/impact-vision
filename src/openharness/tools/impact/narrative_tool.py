"""Tool: LLM narrative generation for impact assessment reports.

Generates structured prompts for executive summaries, key findings,
impact narratives, and case studies from assessment data.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.greenwashing import assess_greenwashing
from openharness.impact.models import Company
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class NarrativeInput(BaseModel):
    action: Literal[
        "executive_summary", "key_findings", "impact_narrative",
        "case_study", "full_narrative",
    ] = Field(description="Type of narrative to generate")
    company_name: str = ""
    company_description: str = ""
    sector: str = ""
    geography: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)
    audience: Literal["lp", "board", "public", "internal"] = Field(
        default="lp", description="Target audience for tone/detail level"
    )
    word_limit: int = Field(default=300, description="Approximate word limit for the narrative")


class NarrativeTool(BaseTool):
    name = "narrative"
    description = (
        "Generate LLM-ready narrative prompts for impact reports. Produces structured "
        "prompts with assessment data that the LLM can expand into polished prose. "
        "Modes: executive_summary, key_findings, impact_narrative, case_study, full_narrative."
    )
    input_model = NarrativeInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, NarrativeInput) else NarrativeInput.model_validate(arguments)

        try:
            store = get_metric_store()
        except FileNotFoundError as e:
            return ToolResult(output=str(e), is_error=True)

        company = Company(
            name=args.company_name or "Company",
            description=args.company_description,
            sector=args.sector,
            geography=args.geography,
            impact_themes=args.impact_themes,
            reported_metrics=args.reported_metrics,
            sdg_claims=args.sdg_claims,
        )

        fd = assess_five_dimensions(company, store)
        sdg = map_sdg_alignment(company, store)
        gaps = analyze_gaps(company, store)
        gw = assess_greenwashing(company)

        data = {
            "company": company,
            "five_dimensions": fd,
            "sdg_alignments": sdg,
            "gap_analysis": gaps,
            "greenwashing": gw,
        }

        audience_guide = {
            "lp": "Use formal investor language. Focus on risk-adjusted returns and measurability.",
            "board": "Strategic and concise. Focus on governance, compliance, and portfolio positioning.",
            "public": "Accessible and engaging. Highlight human impact stories and SDG alignment.",
            "internal": "Detailed and technical. Include methodology notes and data quality caveats.",
        }

        handlers = {
            "executive_summary": self._exec_summary,
            "key_findings": self._key_findings,
            "impact_narrative": self._impact_narrative,
            "case_study": self._case_study,
            "full_narrative": self._full_narrative,
        }
        handler = handlers.get(args.action)
        if not handler:
            return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

        prompt = handler(data, args, audience_guide.get(args.audience, ""))
        return ToolResult(
            output=prompt,
            metadata={"action": args.action, "audience": args.audience},
        )

    def _exec_summary(self, data: dict, args: NarrativeInput, audience_note: str) -> str:
        c = data["company"]
        fd = data["five_dimensions"]
        sdg = data["sdg_alignments"]
        gw = data["greenwashing"]

        top_sdgs = sorted(sdg, key=lambda a: a.score, reverse=True)[:3]
        sdg_str = ", ".join(f"SDG {a.goal} ({a.score:.0f}%)" for a in top_sdgs if a.score > 0)

        return f"""=== EXECUTIVE SUMMARY PROMPT ===

Write a {args.word_limit}-word executive summary for {c.name}.

DATA POINTS:
- Company: {c.name} ({c.sector}, {c.geography})
- Description: {c.description[:300]}
- 5D Score: {fd.overall_score:.1f}/5 (Grade: {fd.overall_grade}, Confidence: {fd.overall_provenance})
- Top SDGs: {sdg_str or 'None scored'}
- Greenwashing Risk: {gw.overall_score}/100 ({gw.classification})
- Core Metric Coverage: {data['gap_analysis'].get('coverage_percentage', 0)}%
- Metrics Reported: {len(c.reported_metrics)}

DIMENSION SCORES:
- What: {fd.what.score}/5 | Who: {fd.who.score}/5 | How Much: {fd.how_much.score}/5
- Contribution: {fd.contribution.score}/5 | Risk: {fd.risk.score}/5

AUDIENCE: {args.audience.upper()}
{audience_note}

INSTRUCTIONS:
1. Open with a one-sentence impact thesis for {c.name}
2. Summarize the overall impact profile (score, grade, confidence)
3. Highlight top 2-3 strengths (highest scoring dimensions/SDGs)
4. Note 1-2 key risks or gaps
5. Close with a forward-looking recommendation
"""

    def _key_findings(self, data: dict, args: NarrativeInput, audience_note: str) -> str:
        c = data["company"]
        fd = data["five_dimensions"]
        gaps = data["gap_analysis"]

        findings = []
        for dim_name, dim in [("What", fd.what), ("Who", fd.who), ("How Much", fd.how_much),
                               ("Contribution", fd.contribution), ("Risk", fd.risk)]:
            findings.append(f"- {dim_name}: {dim.score}/5 ({dim.provenance}) — {dim.notes}")

        return f"""=== KEY FINDINGS PROMPT ===

Write {args.word_limit} words summarizing 5 key findings about {c.name}'s impact measurement maturity.

DIMENSION DATA:
{chr(10).join(findings)}

GAP ANALYSIS:
- Coverage: {gaps.get('coverage_percentage', 0)}%
- Missing metrics: {gaps.get('metrics_missing', 0)}
- Top recommendations: {', '.join(gaps.get('recommendations', [])[:3])}

AUDIENCE: {args.audience.upper()}
{audience_note}

INSTRUCTIONS:
1. Each finding should be a specific, evidence-based observation
2. Reference the relevant dimension or metric
3. Categorize each as: strength, gap, or opportunity
4. Order by importance to the target audience
"""

    def _impact_narrative(self, data: dict, args: NarrativeInput, audience_note: str) -> str:
        c = data["company"]
        fd = data["five_dimensions"]
        sdg = data["sdg_alignments"]

        top_sdgs = [a for a in sdg if a.score > 20][:5]
        sdg_lines = [f"- SDG {a.goal} ({a.goal_name}): {a.score}/100 [{a.confidence}]" for a in top_sdgs]

        return f"""=== IMPACT NARRATIVE PROMPT ===

Write a {args.word_limit}-word impact narrative for {c.name} that tells the story of their impact.

COMPANY CONTEXT:
- Name: {c.name}
- Sector: {c.sector} | Geography: {c.geography}
- Description: {c.description[:500]}
- Impact Themes: {', '.join(c.impact_themes) or 'Not specified'}

IMPACT PROFILE:
- Overall: {fd.overall_score:.1f}/5 (Grade: {fd.overall_grade})
- Strongest: {max([('What', fd.what.score), ('Who', fd.who.score), ('How Much', fd.how_much.score), ('Contribution', fd.contribution.score), ('Risk', fd.risk.score)], key=lambda x: x[1])[0]}

SDG ALIGNMENT:
{chr(10).join(sdg_lines) if sdg_lines else '- No significant SDG alignments'}

AUDIENCE: {args.audience.upper()}
{audience_note}

INSTRUCTIONS:
1. Frame the narrative around the company's Theory of Change
2. Connect operations to outcomes to impact
3. Use specific metrics and SDG targets as evidence
4. Acknowledge data limitations honestly
5. End with the potential for scale
"""

    def _case_study(self, data: dict, args: NarrativeInput, audience_note: str) -> str:
        c = data["company"]
        fd = data["five_dimensions"]

        return f"""=== CASE STUDY PROMPT ===

Write a {args.word_limit}-word impact case study for {c.name}.

STRUCTURE:
1. **Challenge**: What problem does {c.name} address? (sector: {c.sector}, geography: {c.geography})
2. **Approach**: How do they create impact? ({c.description[:200]})
3. **Evidence**: What does the data show?
   - 5D Score: {fd.overall_score:.1f}/5 (Grade: {fd.overall_grade})
   - Metrics reported: {len(c.reported_metrics)}
   - SDG alignment: {len([a for a in data['sdg_alignments'] if a.score > 0])} goals
4. **Impact**: What has been achieved?
5. **Looking Forward**: Growth potential and measurement improvements

AUDIENCE: {args.audience.upper()}
{audience_note}

TONE: Human-centered, evidence-supported, cautiously optimistic.
"""

    def _full_narrative(self, data: dict, args: NarrativeInput, audience_note: str) -> str:
        parts = [
            self._exec_summary(data, args, audience_note),
            "\n" + "=" * 60 + "\n",
            self._key_findings(data, args, audience_note),
            "\n" + "=" * 60 + "\n",
            self._impact_narrative(data, args, audience_note),
        ]
        return "\n".join(parts)
