"""ICVCM/VCMI-aligned carbon-credit integrity screen (as of 2026-06)."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

CCP_ELIGIBLE_PROGRAMS = {
    "verra_vcs": {"status": "eligible", "as_of": "2026-06", "source": "https://icvcm.org/"},
    "gold_standard": {"status": "eligible", "as_of": "2026-06", "source": "https://icvcm.org/"},
    "acr": {"status": "eligible", "as_of": "2026-06", "source": "https://icvcm.org/"},
    "car": {"status": "eligible", "as_of": "2026-06", "source": "https://icvcm.org/"},
    "art_trees": {"status": "eligible", "as_of": "2026-06", "source": "https://icvcm.org/"},
    "biocarbon_fund": {"status": "eligible", "as_of": "2026-06", "source": "https://icvcm.org/"},
    "isometric": {"status": "eligible", "as_of": "2026-06", "source": "https://icvcm.org/"},
    "puro_earth": {"status": "eligible", "as_of": "2026-06", "source": "https://icvcm.org/"},
}
CCP_APPROVED_METHODOLOGIES = {
    "vm0042": {"status": "approved", "as_of": "2026-06", "source": "https://icvcm.org/"},
    "gs-reforestation": {"status": "approved", "as_of": "2026-06", "source": "https://icvcm.org/"},
} | {
    f"icvcm-method-{index:02d}": {
        "status": "approved",
        "as_of": "2026-06",
        "source": "https://icvcm.org/",
    }
    for index in range(1, 37)
}


class CarbonCredit(BaseModel):
    program: str
    methodology_id: str
    vintage: int
    volume_tco2e: float = Field(gt=0)
    ccp_labelled: bool | None = None
    article_6_authorized: bool = False
    corresponding_adjustment: bool | None = None
    project_type: str


class CreditIntegrityResult(BaseModel):
    credit_score: int
    ccp_status: Literal["ccp_labelled", "ccp_eligible_program", "not_eligible", "unknown"]
    vcmi_claim_tier: Literal["compliant", "at_risk", "non_compliant"]
    flags: list[str] = Field(default_factory=list)
    citations: list[str] = Field(
        default_factory=lambda: ["ICVCM Core Carbon Principles", "VCMI Claims Code"]
    )


def screen_credits(
    credits: list[CarbonCredit], claim_text: str | None = None
) -> CreditIntegrityResult:
    if not credits:
        return CreditIntegrityResult(
            credit_score=0,
            ccp_status="unknown",
            vcmi_claim_tier="non_compliant",
            flags=["no credits supplied"],
        )
    flags, scores, statuses = [], [], []
    for credit in credits:
        program_known = credit.program.lower() in CCP_ELIGIBLE_PROGRAMS
        method_known = credit.methodology_id.lower() in CCP_APPROVED_METHODOLOGIES
        labelled = credit.ccp_labelled is True or (program_known and method_known)
        statuses.append(
            "ccp_labelled" if labelled else "ccp_eligible_program" if program_known else "unknown"
        )
        score = 85 if labelled else 65 if program_known else 30
        if credit.vintage < 2016:
            flags.append("pre-2016 vintage")
            score -= 20
        if not method_known:
            flags.append(f"non-CCP or unconfirmed methodology: {credit.methodology_id}")
        if credit.article_6_authorized and credit.corresponding_adjustment is not True:
            flags.append("Article 6 authorization lacks confirmed corresponding adjustment")
        scores.append(max(0, score))
    if claim_text:
        from openharness.impact.greenwashing import assess_greenwashing
        from openharness.impact.models import Company

        review = assess_greenwashing(
            Company(
                name="Carbon-credit claim",
                description=claim_text,
                impact_themes=["carbon credits"],
            ),
            [{"text": claim_text}],
        )
        flags.extend(f"greenwashing: {flag}" for flag in review.flags)
        if review.overall_score >= 40 or any(
            term in claim_text.lower()
            for term in ("carbon neutral", "climate positive", "zero impact", "fully offset")
        ):
            flags.append(
                "neutrality claim wording requires substantiation under the greenwashing review policy"
            )
    weighted = round(
        sum(score * credit.volume_tco2e for score, credit in zip(scores, credits, strict=True))
        / sum(c.volume_tco2e for c in credits)
    )
    status = (
        "ccp_labelled"
        if all(s == "ccp_labelled" for s in statuses)
        else "ccp_eligible_program"
        if all(s in {"ccp_labelled", "ccp_eligible_program"} for s in statuses)
        else "unknown"
    )
    tier = (
        "compliant"
        if weighted >= 75 and not any("neutrality" in f for f in flags)
        else "at_risk"
        if weighted >= 50
        else "non_compliant"
    )
    return CreditIntegrityResult(
        credit_score=weighted, ccp_status=status, vcmi_claim_tier=tier, flags=sorted(set(flags))
    )


__all__ = [
    "CCP_APPROVED_METHODOLOGIES",
    "CCP_ELIGIBLE_PROGRAMS",
    "CarbonCredit",
    "CreditIntegrityResult",
    "screen_credits",
]
