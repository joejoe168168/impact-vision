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
    frameworks=[
        "SFDR",
        "CSRD/ESRS",
        "ISSB IFRS S1",
        "ISSB IFRS S2",
        "TCFD",
        "CBAM",
        "EUDR",
        "EU Battery Regulation",
        "ESPR",
    ],
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
            obligation_id="omnibus_scope_check",
            framework="CSRD/ESRS (Omnibus I)",
            title="CSRD scope determination (Omnibus I)",
            summary=(
                "Confirm CSRD scope post-Omnibus I (>1,000 employees AND >€450M "
                "turnover). If out of scope, decide VSME voluntary reporting."
            ),
            recurrence="one_off",
            owner_hint="compliance lead",
        ),
        RegulatoryObligation(
            obligation_id="csrd_double_materiality",
            framework="CSRD/ESRS",
            title="Double-materiality assessment",
            summary="Impact + financial materiality workspace with assurance-ready evidence (in-scope undertakings; FY2027 under simplified ESRS).",
            recurrence="annual",
        ),
        RegulatoryObligation(
            obligation_id="csddd_value_chain_dd",
            framework="CSDDD (Omnibus I)",
            title="Value-chain human-rights & environmental due diligence",
            summary="HRDD per CSDDD as amended by Omnibus I (>5,000 employees + €1.5B turnover; applies 2029-07-26). Voluntary OECD/UNGP HRDD otherwise.",
            recurrence="annual",
            owner_hint="ESG / legal",
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
        RegulatoryObligation(
            obligation_id="cbam_annual_declaration",
            framework="CBAM",
            title="CBAM embedded-emissions declaration",
            summary=(
                "Annual CBAM declaration with verified embedded emissions and certificate "
                "surrender for covered imports (cement, iron/steel, aluminium, fertilisers, "
                "hydrogen, electricity). Applies to portfolio companies importing covered "
                "goods into the EU above the de-minimis threshold."
            ),
            recurrence="annual",
            owner_hint="customs / ESG analyst",
        ),
        RegulatoryObligation(
            obligation_id="eudr_due_diligence_statement",
            framework="EUDR",
            title="EUDR deforestation due-diligence system review",
            summary=(
                "Maintain a due-diligence system (geolocation, country risk, legality "
                "evidence) and file DDS for each placement of cattle, cocoa, coffee, palm "
                "oil, rubber, soy, or wood products on the EU market. Annual system review "
                "plus per-shipment statements."
            ),
            recurrence="annual",
            owner_hint="supply-chain / legal",
        ),
        RegulatoryObligation(
            obligation_id="battery_passport_readiness",
            framework="EU Battery Regulation",
            title="Battery passport & carbon-footprint readiness",
            summary=(
                "Digital battery passport (EV/LMT/industrial >2 kWh) and phased "
                "carbon-footprint declarations under Regulation (EU) 2023/1542. Applies to "
                "portfolio companies placing covered batteries on the EU market."
            ),
            recurrence="annual",
            owner_hint="product compliance",
        ),
        RegulatoryObligation(
            obligation_id="espr_dpp_applicability",
            framework="ESPR",
            title="ESPR / Digital Product Passport applicability screen",
            summary=(
                "Check delegated acts for covered product groups and prepare Digital "
                "Product Passport data fields (durability, recycled content, substances of "
                "concern) under Regulation (EU) 2024/1781."
            ),
            recurrence="one_off",
            owner_hint="product compliance",
        ),
    ],
    notes=(
        "EU CSRD + SFDR + ISSB baseline. Product/export-side obligations (CBAM, EUDR, "
        "Battery Regulation, ESPR) apply only where portfolio companies place covered "
        "goods on the EU market — screen applicability with the esg_toolbox or "
        "product_passport tools."
    ),
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


# ------------------------------------------- EU Omnibus I scope decision tree


class EUOmnibusScopeInput(BaseModel):
    """Inputs for the post-Omnibus-I CSRD/CSDDD scope decision (Directive (EU) 2026/470)."""

    employees: int = Field(ge=0, description="Average number of employees")
    net_turnover_eur_m: float = Field(ge=0, description="Net turnover in € millions")
    is_eu_undertaking: bool = True
    eu_turnover_eur_m: float = Field(
        default=0.0, ge=0, description="EU-generated net turnover (€m) for non-EU groups"
    )
    is_listed: bool = False
    was_wave1_reporter: bool = Field(
        default=False, description="Already reported CSRD for FY starting 2024 (Wave 1)"
    )


class EUOmnibusScopeResult(BaseModel):
    """Result of the Omnibus I scope determination."""

    as_of: str = "2026-03-18"
    legal_basis: str = "Directive (EU) 2026/470 (Omnibus I)"
    csrd_in_scope: bool
    csddd_in_scope: bool
    csrd_first_reporting_fy: str = ""
    may_pause_fy2025_2026: bool = False
    vsme_recommended: bool = False
    rationale: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


# Post-Omnibus-I cumulative thresholds.
_CSRD_EMPLOYEE_THRESHOLD = 1000
_CSRD_TURNOVER_THRESHOLD_EUR_M = 450.0
_CSDDD_EMPLOYEE_THRESHOLD = 5000
_CSDDD_TURNOVER_THRESHOLD_EUR_M = 1500.0


def assess_eu_omnibus_scope(input: EUOmnibusScopeInput) -> EUOmnibusScopeResult:
    """Decide CSRD/CSDDD scope under the final Omnibus I Directive (EU) 2026/470.

    CSRD now requires BOTH >1,000 employees AND >€450M net turnover (for non-EU
    groups, >€450M EU turnover). CSDDD requires >5,000 employees AND >€1.5B
    turnover and applies from 2029-07-26. Out-of-scope SMEs are steered to the
    VSME voluntary standard.
    """
    rationale: list[str] = []
    next_steps: list[str] = []

    turnover = input.net_turnover_eur_m if input.is_eu_undertaking else input.eu_turnover_eur_m
    turnover_label = "net turnover" if input.is_eu_undertaking else "EU net turnover"

    csrd_in_scope = (
        input.employees > _CSRD_EMPLOYEE_THRESHOLD
        and turnover > _CSRD_TURNOVER_THRESHOLD_EUR_M
    )
    if csrd_in_scope:
        rationale.append(
            f"In CSRD scope: {input.employees} employees > {_CSRD_EMPLOYEE_THRESHOLD} "
            f"AND {turnover_label} €{turnover:.0f}M > €{_CSRD_TURNOVER_THRESHOLD_EUR_M:.0f}M."
        )
    else:
        rationale.append(
            f"Out of CSRD scope: requires BOTH >{_CSRD_EMPLOYEE_THRESHOLD} employees "
            f"AND >€{_CSRD_TURNOVER_THRESHOLD_EUR_M:.0f}M {turnover_label} "
            f"(have {input.employees} employees / €{turnover:.0f}M)."
        )
        if input.is_listed:
            rationale.append(
                "Listed SMEs were removed from mandatory CSRD scope by Omnibus I."
            )

    csddd_in_scope = (
        input.employees > _CSDDD_EMPLOYEE_THRESHOLD
        and turnover > _CSDDD_TURNOVER_THRESHOLD_EUR_M
    )
    rationale.append(
        ("In CSDDD scope" if csddd_in_scope else "Out of CSDDD scope")
        + f": threshold is >{_CSDDD_EMPLOYEE_THRESHOLD} employees AND "
        f">€{_CSDDD_TURNOVER_THRESHOLD_EUR_M:.0f}M turnover (applies 2029-07-26)."
    )

    may_pause = bool(input.was_wave1_reporter and not csrd_in_scope)
    if may_pause:
        rationale.append(
            "Former Wave 1 reporter below new thresholds: may pause FY2025-FY2026 "
            "reporting (subject to national transposition)."
        )

    vsme_recommended = not csrd_in_scope
    first_fy = "FY2027" if csrd_in_scope else ""

    if csrd_in_scope:
        next_steps.append(
            "Prepare ESRS sustainability statement; first year under new scope is "
            "FY2027 (simplified ESRS delegated act targeted 2026-09)."
        )
        next_steps.append("Run the double-materiality assessment (csrd_wizard).")
    else:
        next_steps.append(
            "Not mandatorily in scope — consider the VSME voluntary standard to "
            "satisfy investor/bank/customer data requests (framework_assess: vsme)."
        )
    if csddd_in_scope:
        next_steps.append(
            "Build the CSDDD value-chain HRDD register (hrdd module); applies 2029-07-26."
        )
    else:
        next_steps.append(
            "CSDDD not legally required, but OECD/UNGP-aligned HRDD remains an LP "
            "expectation — evidence it voluntarily via the hrdd module."
        )

    return EUOmnibusScopeResult(
        csrd_in_scope=csrd_in_scope,
        csddd_in_scope=csddd_in_scope,
        csrd_first_reporting_fy=first_fy,
        may_pause_fy2025_2026=may_pause,
        vsme_recommended=vsme_recommended,
        rationale=rationale,
        next_steps=next_steps,
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
    "EUOmnibusScopeInput",
    "EUOmnibusScopeResult",
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
    "assess_eu_omnibus_scope",
    "build_regulator_narrative",
    "classify_sfdr",
    "classify_uk_sdr",
    "get_jurisdiction_profile",
    "list_jurisdictions",
    "schedule_deadlines",
]
