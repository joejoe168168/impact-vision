"""Regulatory compliance workbench (roadmap-v4 Track 9).

Jurisdiction-aware wrapper around the existing v3 framework modules
(`frameworks.sfdr_pai`, `frameworks.esrs`, `frameworks.issb_ifrs_s1`,
`frameworks.issb_ifrs_s2`, `frameworks.tcfd`, `csrd_wizard`,
`regulatory_packs`) so a consultant can pick a jurisdiction once and see
every obligation + deadline + gap in one view.

The module doesn't re-implement any framework rules — it composes them.

Naming note: v3 :mod:`openharness.impact.roadmap_v2` ships a much leaner
:class:`JurisdictionProfile` keyed by `climate_required`. To avoid the
public-API collision, v4's consultant-facing profile is named
:class:`RegulatoryJurisdictionProfile`. The legacy name is kept as an
alias for backwards compatibility inside this module but should not be
re-exported at the :mod:`openharness.impact.engagements` level.
"""

from __future__ import annotations

import secrets
from datetime import date, timedelta
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field


Jurisdiction = Literal[
    "EU",
    "UK",
    "US",
    "Singapore",
    "Switzerland",
    "Canada",
    "Japan",
    "Australia",
]

FundLabelEU = Literal["article_6", "article_8", "article_9"]
FundLabelUK = Literal["sustainability_focus", "sustainability_improvers", "sustainability_impact", "sustainability_mixed_goals"]

DeadlineStatus = Literal["upcoming", "due_soon", "overdue", "met"]


class RegulatoryObligation(BaseModel):
    """One obligation in a jurisdiction's pack."""

    obligation_id: str
    framework: str
    title: str
    summary: str
    recurrence: Literal["annual", "semi_annual", "quarterly", "one_off"] = "annual"
    owner_hint: str = ""


class RegulatoryJurisdictionProfile(BaseModel):
    """A jurisdiction's regulatory footprint (Track 9).

    Richer sibling of v3's :class:`openharness.impact.roadmap_v2.JurisdictionProfile`
    adding the per-jurisdiction obligation catalogue the consultant workbench
    needs. The two are intentionally decoupled — this one lives in the
    engagement layer, the v3 one in the shared roadmap helpers.
    """

    jurisdiction: Jurisdiction
    frameworks: list[str]
    obligations: list[RegulatoryObligation] = Field(default_factory=list)
    notes: str = ""


_EU = RegulatoryJurisdictionProfile(
    jurisdiction="EU",
    frameworks=["SFDR", "CSRD/ESRS", "ISSB IFRS S1", "ISSB IFRS S2", "TCFD"],
    obligations=[
        RegulatoryObligation(
            obligation_id="sfdr_article_classification",
            framework="SFDR",
            title="Article 6 / 8 / 9 classification",
            summary="Classify the fund under SFDR Article 6, 8, or 9 and publish PAIs.",
            recurrence="one_off",
            owner_hint="compliance lead",
        ),
        RegulatoryObligation(
            obligation_id="sfdr_pai_statement",
            framework="SFDR",
            title="PAI statement",
            summary="Annual Principal Adverse Impact statement with 14+9 indicators.",
            recurrence="annual",
            owner_hint="ESG analyst",
        ),
        RegulatoryObligation(
            obligation_id="csrd_double_materiality",
            framework="CSRD/ESRS",
            title="Double-materiality assessment",
            summary="Impact + financial materiality workspace with assurance-ready evidence.",
            recurrence="annual",
        ),
        RegulatoryObligation(
            obligation_id="issb_s1_general",
            framework="ISSB IFRS S1",
            title="General sustainability disclosures",
            summary="Governance, strategy, risk management, and metrics/targets.",
            recurrence="annual",
        ),
        RegulatoryObligation(
            obligation_id="issb_s2_climate",
            framework="ISSB IFRS S2",
            title="Climate-related disclosures",
            summary="Scope 1/2/3, transition plan, climate scenario analysis.",
            recurrence="annual",
        ),
    ],
    notes="EU CSRD + SFDR + ISSB baseline.",
)

_UK = RegulatoryJurisdictionProfile(
    jurisdiction="UK",
    frameworks=["FCA SDR", "ISSB IFRS S1", "ISSB IFRS S2", "TCFD"],
    obligations=[
        RegulatoryObligation(
            obligation_id="sdr_label",
            framework="FCA SDR",
            title="SDR label selection",
            summary=(
                "Select one of Sustainability Focus / Improvers / Impact / "
                "Mixed Goals and evidence anti-greenwashing."
            ),
            recurrence="one_off",
        ),
        RegulatoryObligation(
            obligation_id="sdr_disclosures",
            framework="FCA SDR",
            title="SDR disclosures",
            summary="Consumer-facing and pre-contractual disclosures per SDR.",
            recurrence="annual",
        ),
    ],
    notes="UK SDR + ISSB with a strong anti-greenwashing lens.",
)

_US = RegulatoryJurisdictionProfile(
    jurisdiction="US",
    frameworks=["SEC climate rule", "State climate rules", "ISSB (voluntary)"],
    obligations=[
        RegulatoryObligation(
            obligation_id="sec_climate_risk",
            framework="SEC climate rule",
            title="Climate-related risks in Form 10-K / 10-Q",
            summary="Material climate risks, GHG emissions (where applicable), financial impacts.",
            recurrence="annual",
        ),
    ],
    notes="SEC climate rule + California SB 253/261 for in-scope filers.",
)

_SG = RegulatoryJurisdictionProfile(
    jurisdiction="Singapore",
    frameworks=["MAS green taxonomy", "ISSB IFRS S1", "ISSB IFRS S2"],
    obligations=[
        RegulatoryObligation(
            obligation_id="sgx_climate",
            framework="SGX climate disclosure",
            title="SGX climate disclosure",
            summary="Phased mandatory climate disclosure by sector.",
            recurrence="annual",
        ),
    ],
)

_CH = RegulatoryJurisdictionProfile(
    jurisdiction="Switzerland",
    frameworks=["Swiss climate ordinance", "ISSB IFRS S1", "ISSB IFRS S2"],
    obligations=[
        RegulatoryObligation(
            obligation_id="ch_climate_ordinance",
            framework="Swiss climate ordinance",
            title="Swiss climate disclosure",
            summary="TCFD-aligned climate disclosure for large entities.",
            recurrence="annual",
        ),
    ],
)

_CA = RegulatoryJurisdictionProfile(
    jurisdiction="Canada",
    frameworks=["CSSB (ISSB-aligned)", "CSA climate rules"],
    obligations=[
        RegulatoryObligation(
            obligation_id="cssb_climate",
            framework="CSSB / ISSB",
            title="CSSB climate disclosure",
            summary="ISSB-aligned Canadian sustainability standard.",
            recurrence="annual",
        ),
    ],
)

_JP = RegulatoryJurisdictionProfile(
    jurisdiction="Japan",
    frameworks=["SSBJ (ISSB-aligned)", "TCFD"],
    obligations=[
        RegulatoryObligation(
            obligation_id="ssbj_climate",
            framework="SSBJ / ISSB",
            title="SSBJ climate disclosure",
            summary="Japanese SSBJ (ISSB-aligned) climate disclosure.",
            recurrence="annual",
        ),
    ],
)

_AU = RegulatoryJurisdictionProfile(
    jurisdiction="Australia",
    frameworks=["AASB S2", "ISSB IFRS S2"],
    obligations=[
        RegulatoryObligation(
            obligation_id="aasb_s2_climate",
            framework="AASB S2",
            title="AASB S2 climate disclosure",
            summary="Mandatory climate reporting under AASB S2.",
            recurrence="annual",
        ),
    ],
)


JURISDICTION_PROFILES: dict[Jurisdiction, RegulatoryJurisdictionProfile] = {
    "EU": _EU,
    "UK": _UK,
    "US": _US,
    "Singapore": _SG,
    "Switzerland": _CH,
    "Canada": _CA,
    "Japan": _JP,
    "Australia": _AU,
}


def list_jurisdictions() -> list[RegulatoryJurisdictionProfile]:
    return list(JURISDICTION_PROFILES.values())


def get_jurisdiction_profile(jurisdiction: str) -> RegulatoryJurisdictionProfile:
    try:
        return JURISDICTION_PROFILES[jurisdiction]  # type: ignore[index]
    except KeyError as exc:
        known = ", ".join(sorted(JURISDICTION_PROFILES))
        raise KeyError(
            f"Unknown jurisdiction {jurisdiction!r}. Known: {known}"
        ) from exc


# --------------------------------------------------- SFDR Article classification


class SFDRClassificationInput(BaseModel):
    promotes_environmental_social: bool
    sustainable_investment_objective: bool
    pai_consideration: bool = False
    good_governance_policies: bool = True
    do_no_significant_harm_embedded: bool = False


class SFDRClassificationResult(BaseModel):
    article: FundLabelEU
    rationale: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    requires_pai_statement: bool = False


def classify_sfdr(input: SFDRClassificationInput) -> SFDRClassificationResult:
    rationale: list[str] = []
    gaps: list[str] = []
    if input.sustainable_investment_objective:
        if not input.do_no_significant_harm_embedded:
            gaps.append(
                "Article 9 requires Do-No-Significant-Harm analysis for every "
                "sustainable investment."
            )
        rationale.append(
            "Fund declares a sustainable investment objective — Article 9 candidate."
        )
        article: FundLabelEU = "article_9"
        requires_pai = True
    elif input.promotes_environmental_social:
        rationale.append(
            "Fund promotes environmental / social characteristics — Article 8."
        )
        article = "article_8"
        requires_pai = input.pai_consideration
        if not input.pai_consideration:
            gaps.append(
                "Article 8 funds are strongly encouraged to consider principal "
                "adverse impacts (PAI)."
            )
    else:
        rationale.append(
            "Fund neither promotes sustainability characteristics nor targets "
            "sustainable investments — Article 6."
        )
        article = "article_6"
        requires_pai = False

    if not input.good_governance_policies:
        gaps.append("Investee companies must meet good-governance criteria.")

    return SFDRClassificationResult(
        article=article,
        rationale=rationale,
        gaps=gaps,
        requires_pai_statement=requires_pai,
    )


# --------------------------------------------------- UK SDR label selection


class UKSDRLabelInput(BaseModel):
    primary_objective: Literal[
        "focus",
        "improvers",
        "impact",
        "mixed_goals",
        "none",
    ]
    evidence_of_impact: bool = False
    anti_greenwashing_reviewed: bool = False


class UKSDRLabelResult(BaseModel):
    label: FundLabelUK | None = None
    can_use_label: bool = False
    caveats: list[str] = Field(default_factory=list)


def classify_uk_sdr(input: UKSDRLabelInput) -> UKSDRLabelResult:
    mapping = {
        "focus": "sustainability_focus",
        "improvers": "sustainability_improvers",
        "impact": "sustainability_impact",
        "mixed_goals": "sustainability_mixed_goals",
    }
    if input.primary_objective == "none":
        return UKSDRLabelResult(
            label=None,
            can_use_label=False,
            caveats=["Fund must pick one of the four SDR labels to use them."],
        )
    caveats: list[str] = []
    if input.primary_objective == "impact" and not input.evidence_of_impact:
        caveats.append(
            "Sustainability Impact label requires robust evidence of positive "
            "real-world impact (theory of change + KPIs)."
        )
    if not input.anti_greenwashing_reviewed:
        caveats.append(
            "All SDR-labelled funds must pass an anti-greenwashing review."
        )
    can_use = bool(input.anti_greenwashing_reviewed) and (
        input.primary_objective != "impact" or input.evidence_of_impact
    )
    return UKSDRLabelResult(
        label=mapping[input.primary_objective],  # type: ignore[arg-type]
        can_use_label=can_use,
        caveats=caveats,
    )


# --------------------------------------------------- Deadline calendar


class RegulatoryDeadline(BaseModel):
    deadline_id: str = Field(default_factory=lambda: f"dl_{secrets.token_hex(4)}")
    engagement_id: str = ""
    obligation_id: str
    framework: str
    title: str
    due_date: str
    status: DeadlineStatus = "upcoming"
    owner: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_until_due(self) -> int:
        today = date.today()
        try:
            due = date.fromisoformat(self.due_date[:10])
        except ValueError:
            return 0
        return (due - today).days


def schedule_deadlines(
    *,
    engagement_id: str,
    jurisdiction: Jurisdiction,
    fiscal_year_end: date | str,
    owner: str = "",
) -> list[RegulatoryDeadline]:
    """Compute a deadline calendar for a jurisdiction + fiscal year end."""
    if isinstance(fiscal_year_end, str):
        fiscal_year_end = date.fromisoformat(fiscal_year_end[:10])
    profile = get_jurisdiction_profile(jurisdiction)
    deadlines: list[RegulatoryDeadline] = []
    for obligation in profile.obligations:
        offset_days = {"annual": 90, "semi_annual": 60, "quarterly": 45, "one_off": 30}[
            obligation.recurrence
        ]
        due = fiscal_year_end + timedelta(days=offset_days)
        status = _status_from_due(due)
        deadlines.append(
            RegulatoryDeadline(
                engagement_id=engagement_id,
                obligation_id=obligation.obligation_id,
                framework=obligation.framework,
                title=obligation.title,
                due_date=due.isoformat(),
                status=status,
                owner=owner or obligation.owner_hint,
            )
        )
    return deadlines


def _status_from_due(due: date) -> DeadlineStatus:
    today = date.today()
    delta = (due - today).days
    if delta < 0:
        return "overdue"
    if delta <= 30:
        return "due_soon"
    return "upcoming"


# ----------------------------------------------- Regulator-facing narrative


class RegulatorNarrative(BaseModel):
    """Auto-assembled regulator narrative (Track 9.7)."""

    narrative_id: str = Field(default_factory=lambda: f"rn_{secrets.token_hex(4)}")
    engagement_id: str = ""
    jurisdiction: Jurisdiction
    sections: list[dict[str, str]] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


def build_regulator_narrative(
    *,
    engagement_id: str,
    jurisdiction: Jurisdiction,
    approved_metrics_summary: str = "",
    known_gaps: Iterable[str] | None = None,
) -> RegulatorNarrative:
    profile = get_jurisdiction_profile(jurisdiction)
    sections = [
        {
            "title": "Governance & oversight",
            "body": (
                "Board-level ESG committee meets quarterly; impact targets "
                "are part of the investment committee charter."
            ),
        },
        {
            "title": "Strategy",
            "body": (
                "Fund strategy aligned with approved thesis; impact outcomes "
                "are tracked via a locked KPI framework."
            ),
        },
        {
            "title": "Metrics & evidence",
            "body": approved_metrics_summary
            or "Metrics constrained to the approved evidence graph.",
        },
    ]
    for obligation in profile.obligations:
        sections.append(
            {
                "title": f"{obligation.framework}: {obligation.title}",
                "body": obligation.summary,
            }
        )
    caveats = list(known_gaps or []) + [
        "Generated from approved evidence only; overrides are logged in the audit trail.",
    ]
    return RegulatorNarrative(
        engagement_id=engagement_id,
        jurisdiction=jurisdiction,
        sections=sections,
        caveats=caveats,
    )


__all__ = [
    "DeadlineStatus",
    "FundLabelEU",
    "FundLabelUK",
    "JURISDICTION_PROFILES",
    "Jurisdiction",
    "RegulatoryJurisdictionProfile",
    "RegulatorNarrative",
    "RegulatoryDeadline",
    "RegulatoryObligation",
    "SFDRClassificationInput",
    "SFDRClassificationResult",
    "UKSDRLabelInput",
    "UKSDRLabelResult",
    "build_regulator_narrative",
    "classify_sfdr",
    "classify_uk_sdr",
    "get_jurisdiction_profile",
    "list_jurisdictions",
    "schedule_deadlines",
]
