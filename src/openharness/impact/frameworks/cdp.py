"""CDP questionnaire intake — Climate Change, Water Security, Forests.

Loads a CDP questionnaire export (CSV or JSON dict) and produces a
normalised view that can be cross-referenced with IRIS+, SBTi and TNFD.

We don't try to *score* against CDP's grading rubric (A → F) — that is
proprietary. Instead we surface coverage, key data points, and gaps.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CDPProgram = Literal["climate", "water", "forests"]


# Canonical CDP module → IRIS+ proxy (Climate Change 2024 questionnaire).
# Keys are CDP question codes; values are best-fit IRIS+ metric IDs.
CDP_TO_IRIS: dict[str, list[str]] = {
    # Governance
    "C1.1": [],                # board oversight
    "C1.2": [],                # management responsibility
    # Risks & opportunities
    "C2.1a": [],
    "C2.3a": [],
    "C2.4a": [],
    # Business strategy
    "C3.2": [],
    "C3.3": [],
    "C3.4": [],
    # Targets & performance
    "C4.1a": [],               # absolute targets
    "C4.1b": [],               # intensity targets
    # Emissions methodology & data
    "C6.1": ["OI3525"],        # Scope 1
    "C6.3": ["OI3525"],        # Scope 2
    "C6.5": ["OI3525"],        # Scope 3
    "C7.1a": ["OI3525"],       # breakdown by GHG
    # Emissions performance
    "C9.1": ["OI3525"],
    # Verification
    "C10.1a": [],              # third-party verification
    # Carbon pricing
    "C11.3a": [],
}


class CDPResponse(BaseModel):
    question_code: str
    module: str
    question_text: str = ""
    response: str | float | int | bool | None = None
    iris_metric_ids: list[str] = Field(default_factory=list)


class CDPIntakeResult(BaseModel):
    company_name: str
    program: CDPProgram
    reporting_year: int | None = None
    responses_total: int
    responses_with_data: int
    coverage_pct: float
    iris_metrics_populated: list[str] = Field(default_factory=list)
    by_module: dict[str, dict[str, int]] = Field(default_factory=dict)
    missing_critical: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


# Codes considered "critical" — i.e. anything below ~80% coverage flags
CRITICAL_CODES_CLIMATE = {"C1.1", "C2.1a", "C4.1a", "C6.1", "C6.3", "C6.5", "C10.1a"}


def _module_of(question_code: str) -> str:
    if not question_code:
        return "unknown"
    head = question_code.split(".")[0]
    return head


def parse_cdp_responses(
    company_name: str,
    program: CDPProgram,
    raw_responses: list[dict[str, Any]],
    reporting_year: int | None = None,
) -> CDPIntakeResult:
    """Parse raw CDP responses (list of dicts with at least `question_code`)."""
    responses: list[CDPResponse] = []
    iris_seen: set[str] = set()
    by_module: dict[str, dict[str, int]] = {}

    for r in raw_responses:
        code = str(r.get("question_code", "")).strip()
        if not code:
            continue
        module = _module_of(code)
        bucket = by_module.setdefault(module, {"total": 0, "answered": 0})
        bucket["total"] += 1

        resp = r.get("response")
        has_data = resp not in (None, "", "Question not applicable")
        if has_data:
            bucket["answered"] += 1

        iris_refs = CDP_TO_IRIS.get(code, [])
        if has_data:
            iris_seen.update(iris_refs)

        responses.append(
            CDPResponse(
                question_code=code,
                module=module,
                question_text=str(r.get("question_text", "")),
                response=resp,
                iris_metric_ids=iris_refs,
            )
        )

    answered = sum(b["answered"] for b in by_module.values())
    total = sum(b["total"] for b in by_module.values())
    coverage = (answered / total * 100) if total else 0.0

    answered_codes = {r.question_code for r in responses if r.response not in (None, "")}
    missing_critical = []
    if program == "climate":
        missing_critical = sorted(CRITICAL_CODES_CLIMATE - answered_codes)

    findings: list[str] = []
    if coverage < 70:
        findings.append(f"CDP {program} coverage {coverage:.0f}% — below 70% threshold investors expect.")
    if missing_critical:
        findings.append(f"Missing critical {program} questions: {', '.join(missing_critical)}.")

    return CDPIntakeResult(
        company_name=company_name,
        program=program,
        reporting_year=reporting_year,
        responses_total=len(responses),
        responses_with_data=answered,
        coverage_pct=round(coverage, 1),
        iris_metrics_populated=sorted(iris_seen),
        by_module=by_module,
        missing_critical=missing_critical,
        findings=findings,
    )
