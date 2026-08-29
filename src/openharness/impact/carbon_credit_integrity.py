"""ICVCM/VCMI-aligned carbon-credit integrity screen (as of 2026-06)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CCP_ELIGIBLE_PROGRAMS = {
    "verra_vcs": {
        "status": "eligible",
        "as_of": "2026-06",
        "label": "Verra Verified Carbon Standard",
        "source": "https://icvcm.org/",
    },
    "gold_standard": {
        "status": "eligible",
        "as_of": "2026-06",
        "label": "Gold Standard for the Global Goals",
        "source": "https://icvcm.org/",
    },
    "acr": {
        "status": "eligible",
        "as_of": "2026-06",
        "label": "American Carbon Registry",
        "source": "https://icvcm.org/",
    },
    "car": {
        "status": "eligible",
        "as_of": "2026-06",
        "label": "Climate Action Reserve",
        "source": "https://icvcm.org/",
    },
    "art_trees": {
        "status": "eligible",
        "as_of": "2026-06",
        "label": "ART TREES",
        "source": "https://icvcm.org/",
    },
    "biocarbon_fund": {
        "status": "eligible",
        "as_of": "2026-06",
        "label": "BioCarbon Fund",
        "source": "https://icvcm.org/",
    },
    "isometric": {
        "status": "eligible",
        "as_of": "2026-06",
        "label": "Isometric",
        "source": "https://icvcm.org/",
    },
    "puro_earth": {
        "status": "eligible",
        "as_of": "2026-06",
        "label": "Puro.earth",
        "source": "https://icvcm.org/",
    },
}

PROGRAM_ALIASES = {
    "verra": "verra_vcs",
    "vcs": "verra_vcs",
    "verra_vcs": "verra_vcs",
    "verra vcs": "verra_vcs",
    "verified carbon standard": "verra_vcs",
    "gold standard": "gold_standard",
    "gold_standard": "gold_standard",
    "gs": "gold_standard",
    "gs4gg": "gold_standard",
    "acr": "acr",
    "american carbon registry": "acr",
    "car": "car",
    "climate action reserve": "car",
    "art": "art_trees",
    "trees": "art_trees",
    "art_trees": "art_trees",
    "art trees": "art_trees",
    "biocarbon": "biocarbon_fund",
    "biocarbon_fund": "biocarbon_fund",
    "isometric": "isometric",
    "puro": "puro_earth",
    "puro.earth": "puro_earth",
    "puro_earth": "puro_earth",
}

# Named methodologies that ICVCM has approved or that are commonly treated as
# CCP-pathway. Unknown IDs stay unconfirmed rather than being invented.
CCP_APPROVED_METHODOLOGIES = {
    "vm0042": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "VM0042 Improved Agricultural Land Management",
        "source": "https://icvcm.org/",
    },
    "vm0047": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "VM0047 Afforestation, Reforestation and Revegetation",
        "source": "https://icvcm.org/",
    },
    "vm0048": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "VM0048 Reducing Emissions from Deforestation and Degradation",
        "source": "https://icvcm.org/",
    },
    "vm0007": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "VM0007 REDD+ Methodology Framework",
        "source": "https://icvcm.org/",
    },
    "gs-reforestation": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "Gold Standard Afforestation/Reforestation",
        "source": "https://icvcm.org/",
    },
    "gs-methane": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "Gold Standard methane avoidance / recovery",
        "source": "https://icvcm.org/",
    },
    "acr-ifm": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "ACR Improved Forest Management",
        "source": "https://icvcm.org/",
    },
    "car-us-forest": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "Climate Action Reserve US Forest",
        "source": "https://icvcm.org/",
    },
    "art-trees": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "ART TREES",
        "source": "https://icvcm.org/",
    },
    "puro-biochar": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "Puro.earth Biochar",
        "source": "https://icvcm.org/",
    },
    "isometric-biochar": {
        "status": "approved",
        "as_of": "2026-06",
        "label": "Isometric Biochar",
        "source": "https://icvcm.org/",
    },
}

METHODOLOGY_ALIASES = {
    "vm-0042": "vm0042",
    "vm0042": "vm0042",
    "vm-0047": "vm0047",
    "vm0047": "vm0047",
    "vm-0048": "vm0048",
    "vm0048": "vm0048",
    "vm-0007": "vm0007",
    "vm0007": "vm0007",
    "gs-ar": "gs-reforestation",
    "gs-reforestation": "gs-reforestation",
    "gs-afforestation": "gs-reforestation",
    "gs-methane": "gs-methane",
    "acr ifm": "acr-ifm",
    "acr-ifm": "acr-ifm",
    "car forest": "car-us-forest",
    "car-us-forest": "car-us-forest",
    "art trees": "art-trees",
    "art-trees": "art-trees",
    "trees": "art-trees",
    "puro biochar": "puro-biochar",
    "puro-biochar": "puro-biochar",
    "isometric biochar": "isometric-biochar",
    "isometric-biochar": "isometric-biochar",
}


def normalize_program(name: str) -> str:
    key = " ".join(str(name or "").strip().lower().replace("-", "_").replace(".", " ").split())
    key = key.replace(" ", "_") if key in PROGRAM_ALIASES else key
    compact = " ".join(str(name or "").strip().lower().replace("_", " ").replace("-", " ").split())
    return PROGRAM_ALIASES.get(compact, PROGRAM_ALIASES.get(key, key))


def normalize_methodology(methodology_id: str) -> str:
    raw = str(methodology_id or "").strip().lower()
    compact = raw.replace(" ", "-")
    return METHODOLOGY_ALIASES.get(raw, METHODOLOGY_ALIASES.get(compact, compact))


class CarbonCredit(BaseModel):
    program: str
    methodology_id: str
    vintage: int
    volume_tco2e: float = Field(gt=0)
    ccp_labelled: bool | None = None
    article_6_authorized: bool = False
    corresponding_adjustment: bool | None = None
    project_type: str = ""


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
        program = normalize_program(credit.program)
        method = normalize_methodology(credit.methodology_id)
        program_known = program in CCP_ELIGIBLE_PROGRAMS
        method_known = method in CCP_APPROVED_METHODOLOGIES
        if credit.ccp_labelled is True:
            status = "ccp_labelled"
            score = 85
        elif program_known and method_known:
            # Eligible programme + approved methodology is not the same as a
            # CCP label on the issued unit.
            status = "ccp_eligible_program"
            score = 70
            flags.append(
                f"{credit.methodology_id} is on the CCP-approved pathway but the unit is not CCP-labelled"
            )
        elif program_known:
            status = "ccp_eligible_program"
            score = 55
        else:
            status = "unknown"
            score = 30
        statuses.append(status)
        if credit.vintage < 2016:
            flags.append("pre-2016 vintage")
            score -= 20
        if credit.vintage > 2026:
            flags.append(f"future vintage {credit.vintage}")
            score -= 10
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
    if all(s == "ccp_labelled" for s in statuses):
        status = "ccp_labelled"
    elif all(s in {"ccp_labelled", "ccp_eligible_program"} for s in statuses):
        status = "ccp_eligible_program"
    elif all(s == "not_eligible" for s in statuses):
        status = "not_eligible"
    else:
        status = "unknown"
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
    "METHODOLOGY_ALIASES",
    "PROGRAM_ALIASES",
    "CarbonCredit",
    "CreditIntegrityResult",
    "normalize_methodology",
    "normalize_program",
    "screen_credits",
]
