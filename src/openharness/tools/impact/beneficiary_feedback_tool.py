"""Tool: Beneficiary feedback data import and analysis.

Accepts 60 Decibels Lean Data format or generic survey data,
structures it as BeneficiaryFeedback, and generates an analysis.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.impact.models import BeneficiaryFeedback
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


def _format_optional(value: Any, fallback: str = "N/A") -> Any:
    return fallback if value is None else value


def _get_first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


class BeneficiaryFeedbackInput(BaseModel):
    action: Literal["import", "analyze", "summary"] = Field(
        default="analyze",
        description=(
            "'import': Parse raw survey data into structured format. "
            "'analyze': Analyze provided feedback data. "
            "'summary': Generate a brief summary suitable for DD reports."
        ),
    )
    company_name: str = Field(default="", description="Company name")
    satisfaction_score: float | None = Field(default=None, description="Overall satisfaction (1-5)")
    nps: float | None = Field(default=None, description="Net Promoter Score (-100 to 100)")
    sample_size: int = Field(default=0, description="Number of beneficiaries surveyed")
    survey_date: str = Field(default="", description="Survey date (e.g. '2026-Q1')")
    methodology: str = Field(default="", description="e.g. '60 Decibels Lean Data'")
    quality_of_life_improvement: float | None = Field(default=None, description="% QoL improvement")
    would_recommend: float | None = Field(default=None, description="% would recommend")
    themes: list[str] = Field(default_factory=list, description="Qualitative themes")
    challenges: list[str] = Field(default_factory=list, description="Negative feedback themes")
    quotes: list[str] = Field(default_factory=list, description="Beneficiary quotes")
    segments: dict[str, Any] = Field(default_factory=dict, description="Disaggregated data")
    raw_data: str = Field(
        default="",
        description="Raw survey data (JSON or CSV text) for 'import' action — 60 Decibels format",
    )


class BeneficiaryFeedbackTool(BaseTool):
    name = "beneficiary_feedback"
    description = (
        "Import, analyze, and summarize beneficiary feedback data. "
        "Accepts 60 Decibels Lean Data format or manual survey inputs. "
        "Outputs structured analysis for DD reports and impact assessments."
    )
    input_model = BeneficiaryFeedbackInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, BeneficiaryFeedbackInput)
            else BeneficiaryFeedbackInput.model_validate(arguments)
        )

        if args.action == "import":
            return self._import_data(args)
        elif args.action == "summary":
            return self._summary(args)
        else:
            return self._analyze(args)

    def _build_feedback(self, args: BeneficiaryFeedbackInput) -> BeneficiaryFeedback:
        return BeneficiaryFeedback(
            satisfaction_score=args.satisfaction_score,
            nps=args.nps,
            sample_size=args.sample_size,
            survey_date=args.survey_date,
            methodology=args.methodology,
            quality_of_life_improvement=args.quality_of_life_improvement,
            would_recommend=args.would_recommend,
            themes=args.themes,
            challenges=args.challenges,
            quotes=args.quotes,
            segments=args.segments,
        )

    def _import_data(self, args: BeneficiaryFeedbackInput) -> ToolResult:
        """Parse raw survey data into structured BeneficiaryFeedback."""
        if not args.raw_data:
            return ToolResult(output="raw_data is required for 'import' action", is_error=True)

        try:
            data = json.loads(args.raw_data)
        except json.JSONDecodeError:
            return self._parse_csv_feedback(args.raw_data, args.company_name)

        if isinstance(data, dict):
            feedback = BeneficiaryFeedback(
                satisfaction_score=_get_first_present(data, "satisfaction_score", "satisfaction"),
                nps=_get_first_present(data, "nps", "net_promoter_score"),
                sample_size=data.get("sample_size", 0),
                survey_date=data.get("survey_date", ""),
                methodology=data.get("methodology", ""),
                quality_of_life_improvement=_get_first_present(
                    data,
                    "quality_of_life_improvement",
                    "qol_improvement",
                ),
                would_recommend=data.get("would_recommend"),
                themes=data.get("themes", []),
                challenges=data.get("challenges", []),
                quotes=data.get("quotes", []),
                segments=data.get("segments", {}),
            )
        else:
            return ToolResult(output="Unsupported data format. Provide JSON dict or CSV.", is_error=True)

        lines = [
            f"BENEFICIARY FEEDBACK IMPORT: {args.company_name or 'Unknown'}",
            "=" * 50,
            "",
            f"  Satisfaction: {_format_optional(feedback.satisfaction_score)}/5",
            f"  NPS: {_format_optional(feedback.nps)}",
            f"  Sample size: {feedback.sample_size}",
            f"  Methodology: {feedback.methodology or 'Not specified'}",
            f"  Survey date: {feedback.survey_date or 'Not specified'}",
        ]
        if feedback.quality_of_life_improvement is not None:
            lines.append(f"  QoL improvement: {feedback.quality_of_life_improvement}%")
        if feedback.would_recommend is not None:
            lines.append(f"  Would recommend: {feedback.would_recommend}%")
        if feedback.themes:
            lines.append(f"\n  Positive themes: {', '.join(feedback.themes)}")
        if feedback.challenges:
            lines.append(f"  Challenges: {', '.join(feedback.challenges)}")
        if feedback.quotes:
            lines.append(f"\n  Sample quotes ({len(feedback.quotes)}):")
            for q in feedback.quotes[:3]:
                lines.append(f'    "{q}"')

        return ToolResult(
            output="\n".join(lines),
            metadata={"feedback": feedback.model_dump()},
        )

    def _parse_csv_feedback(self, csv_text: str, company_name: str) -> ToolResult:
        """Attempt to parse CSV-format feedback."""
        import csv
        import io

        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        if not rows:
            return ToolResult(output="No data rows found in CSV", is_error=True)

        satisfaction_vals = []
        nps_vals = []
        themes: list[str] = []
        challenges: list[str] = []
        quotes: list[str] = []

        for row in rows:
            if row.get("satisfaction"):
                try:
                    satisfaction_vals.append(float(row["satisfaction"]))
                except ValueError:
                    pass
            if row.get("nps"):
                try:
                    nps_vals.append(float(row["nps"]))
                except ValueError:
                    pass
            if row.get("theme"):
                themes.append(row["theme"])
            if row.get("challenge"):
                challenges.append(row["challenge"])
            if row.get("quote"):
                quotes.append(row["quote"])

        unique_themes = list(dict.fromkeys(themes))
        unique_challenges = list(dict.fromkeys(challenges))

        feedback = BeneficiaryFeedback(
            satisfaction_score=round(sum(satisfaction_vals) / len(satisfaction_vals), 2) if satisfaction_vals else None,
            nps=round(sum(nps_vals) / len(nps_vals), 1) if nps_vals else None,
            sample_size=len(rows),
            themes=unique_themes[:10],
            challenges=unique_challenges[:10],
            quotes=quotes[:5],
        )

        return ToolResult(
            output=f"Parsed {len(rows)} survey responses for {company_name or 'Unknown'}.\n"
            f"Avg satisfaction: {_format_optional(feedback.satisfaction_score)}/5, "
            f"Avg NPS: {_format_optional(feedback.nps)}, "
            f"Themes: {len(unique_themes)}, Challenges: {len(unique_challenges)}",
            metadata={"feedback": feedback.model_dump()},
        )

    def _analyze(self, args: BeneficiaryFeedbackInput) -> ToolResult:
        """Analyze beneficiary feedback data and produce quality assessment."""
        feedback = self._build_feedback(args)
        lines = [
            f"BENEFICIARY FEEDBACK ANALYSIS: {args.company_name or 'Unknown'}",
            "=" * 50,
        ]

        quality_score = 0
        quality_factors: list[str] = []

        if feedback.sample_size >= 100:
            quality_score += 25
            quality_factors.append(f"Good sample size ({feedback.sample_size})")
        elif feedback.sample_size >= 30:
            quality_score += 15
            quality_factors.append(f"Moderate sample size ({feedback.sample_size})")
        elif feedback.sample_size > 0:
            quality_score += 5
            quality_factors.append(f"Small sample size ({feedback.sample_size}) — may not be representative")
        else:
            quality_factors.append("No sample size reported")

        if feedback.methodology:
            quality_score += 20
            quality_factors.append(f"Methodology documented: {feedback.methodology}")
        else:
            quality_factors.append("No methodology documented")

        if feedback.segments:
            quality_score += 15
            quality_factors.append(f"Disaggregated by {len(feedback.segments)} dimensions")

        if feedback.satisfaction_score is not None:
            quality_score += 10
            label = (
                "Excellent" if feedback.satisfaction_score >= 4.5
                else "Good" if feedback.satisfaction_score >= 3.5
                else "Fair" if feedback.satisfaction_score >= 2.5
                else "Poor"
            )
            lines.append(f"\n  Satisfaction: {feedback.satisfaction_score}/5 ({label})")

        if feedback.nps is not None:
            quality_score += 10
            label = (
                "Excellent" if feedback.nps >= 50
                else "Good" if feedback.nps >= 0
                else "Needs improvement"
            )
            lines.append(f"  NPS: {feedback.nps} ({label})")

        if feedback.quality_of_life_improvement is not None:
            quality_score += 10
            lines.append(f"  Quality of life improvement: {feedback.quality_of_life_improvement}%")

        if feedback.would_recommend is not None:
            quality_score += 10
            lines.append(f"  Would recommend: {feedback.would_recommend}%")

        quality_score = min(100, quality_score)
        quality_label = (
            "High" if quality_score >= 70
            else "Moderate" if quality_score >= 40
            else "Low"
        )

        lines.append(f"\n  Data Quality Score: {quality_score}/100 ({quality_label})")
        for f in quality_factors:
            lines.append(f"    + {f}")

        if feedback.themes:
            lines.append(f"\n  Positive themes ({len(feedback.themes)}):")
            for t in feedback.themes[:5]:
                lines.append(f"    - {t}")
        if feedback.challenges:
            lines.append(f"\n  Challenges ({len(feedback.challenges)}):")
            for c in feedback.challenges[:5]:
                lines.append(f"    - {c}")

        nesta_level = 1
        if feedback.sample_size >= 30 and feedback.methodology:
            nesta_level = 2
        if feedback.sample_size >= 100 and feedback.segments:
            nesta_level = 3
        lines.append(f"\n  NESTA Evidence Level: {nesta_level}/5")

        recs: list[str] = []
        if feedback.sample_size < 30:
            recs.append("Increase sample size to >=30 for statistical validity")
        if not feedback.methodology:
            recs.append("Document survey methodology for reproducibility")
        if not feedback.segments:
            recs.append("Disaggregate data by gender, income, and geography")
        if not feedback.challenges:
            recs.append("Include negative feedback to demonstrate balanced reporting")
        if feedback.nps is None:
            recs.append("Add NPS measurement for standardized comparison")

        if recs:
            lines.append("\n  Recommendations:")
            for r in recs:
                lines.append(f"    → {r}")

        return ToolResult(
            output="\n".join(lines),
            metadata={
                "feedback": feedback.model_dump(),
                "quality_score": quality_score,
                "nesta_level": nesta_level,
            },
        )

    def _summary(self, args: BeneficiaryFeedbackInput) -> ToolResult:
        """Generate a brief summary for inclusion in DD reports."""
        feedback = self._build_feedback(args)
        parts: list[str] = []

        if feedback.satisfaction_score is not None:
            parts.append(f"Satisfaction: {feedback.satisfaction_score}/5")
        if feedback.nps is not None:
            parts.append(f"NPS: {feedback.nps}")
        if feedback.sample_size:
            parts.append(f"n={feedback.sample_size}")
        if feedback.quality_of_life_improvement is not None:
            parts.append(f"{feedback.quality_of_life_improvement}% report QoL improvement")
        if feedback.would_recommend is not None:
            parts.append(f"{feedback.would_recommend}% would recommend")
        if feedback.methodology:
            parts.append(f"via {feedback.methodology}")

        summary = " | ".join(parts) if parts else "No beneficiary feedback data available"
        return ToolResult(output=f"Beneficiary Feedback: {summary}")
