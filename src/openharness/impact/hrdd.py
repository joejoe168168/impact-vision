"""Human-rights & value-chain due diligence (HRDD / CSDDD).

A risk-based human-rights due-diligence workflow aligned to the **UN Guiding
Principles** (Protect / Respect / Remedy) and the **OECD Due Diligence Guidance
for Responsible Business Conduct** (the 6-step cycle), and mapped to the
obligations the EU **CSDDD** (as amended by Omnibus I, Directive (EU) 2026/470)
places on in-scope companies.

What it does:

* prioritises **salient human-rights issues** by severity (scale × scope ×
  remediability) and likelihood — the UNGP definition of salience;
* maps issues across **value-chain tiers** (own operations, tier-1, deeper
  suppliers, downstream) and weighs the company's **leverage**;
* scores a **grievance mechanism** against the UNGP Principle 31 effectiveness
  criteria;
* tracks **remediation** cases through a small state machine;
* scores coverage of the **OECD 6-step** cycle and returns prioritised actions.

Everything is deterministic and offline; this is a structuring + triage tool,
not a legal opinion.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field


ValueChainTier = Literal[
    "own_operations",
    "tier_1_suppliers",
    "tier_2plus_suppliers",
    "downstream",
]

IssueCategory = Literal[
    "forced_labour",
    "child_labour",
    "freedom_of_association",
    "living_wage",
    "health_and_safety",
    "discrimination",
    "working_hours",
    "land_rights",
    "indigenous_rights",
    "community_impact",
    "water_access",
    "privacy",
    "vulnerable_groups",
    "modern_slavery",
    "other",
]

Severity = Literal["low", "medium", "high", "critical"]


# UNGP salience: severity is judged on scale, scope and remediability.
_SEVERITY_SCORE: dict[Severity, int] = {"low": 1, "medium": 2, "high": 3, "critical": 4}

# Categories that are "gross" human-rights risks — escalated regardless of
# reported likelihood (CSDDD / UNGP treat these as never acceptable).
_GROSS_CATEGORIES = {"forced_labour", "child_labour", "modern_slavery"}


class SalientIssue(BaseModel):
    """One potential adverse human-rights impact."""

    name: str
    category: IssueCategory = "other"
    value_chain_tier: ValueChainTier = "tier_1_suppliers"
    severity: Severity = "medium"
    likelihood: Severity = "medium"
    affected_stakeholders: list[str] = Field(default_factory=list)
    leverage: Literal["high", "medium", "low", "none"] = "medium"
    evidence: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def salience_score(self) -> int:
        """Severity × likelihood, with gross-risk escalation (UNGP salience)."""
        base = _SEVERITY_SCORE[self.severity] * _SEVERITY_SCORE[self.likelihood]
        if self.category in _GROSS_CATEGORIES:
            # UNGP: gross human-rights risks always demand priority — floor at
            # critical × critical so they outrank ordinary high×high issues.
            base = max(base, _SEVERITY_SCORE["critical"] * _SEVERITY_SCORE["critical"])
        return base

    @computed_field  # type: ignore[prop-decorator]
    @property
    def priority(self) -> Severity:
        s = self.salience_score
        if s >= 9:
            return "critical"
        if s >= 6:
            return "high"
        if s >= 3:
            return "medium"
        return "low"


class GrievanceMechanism(BaseModel):
    """Operational-level grievance mechanism (UNGP Principle 31)."""

    exists: bool = False
    accessible_to_value_chain_workers: bool = False
    anonymous_channel: bool = False
    non_retaliation_policy: bool = False
    tracks_to_remediation: bool = False
    timebound_response: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effectiveness_score_pct(self) -> float:
        criteria = [
            self.exists,
            self.accessible_to_value_chain_workers,
            self.anonymous_channel,
            self.non_retaliation_policy,
            self.tracks_to_remediation,
            self.timebound_response,
        ]
        return round(sum(1 for c in criteria if c) / len(criteria) * 100, 1)


class RemediationCase(BaseModel):
    """A remediation case tracked through a small state machine."""

    issue: str
    status: Literal[
        "identified", "plan_agreed", "in_progress", "remediated", "closed_no_action"
    ] = "identified"
    affected_count: int = 0
    note: str = ""


class HRDDInput(BaseModel):
    """Inputs for a human-rights due-diligence screen."""

    company_name: str = ""
    sector: str = ""
    geographies: list[str] = Field(default_factory=list)
    salient_issues: list[SalientIssue] = Field(default_factory=list)
    grievance: GrievanceMechanism = Field(default_factory=GrievanceMechanism)
    remediation_cases: list[RemediationCase] = Field(default_factory=list)
    living_wage_geography: str = ""
    wages: list[dict] = Field(default_factory=list)
    # OECD 6-step cycle self-attestation
    has_rbc_policy: bool = Field(
        default=False, description="Step 1: embed RBC in policy/management"
    )
    has_impact_identification: bool = Field(
        default=False, description="Step 2: identify & assess impacts"
    )
    has_mitigation_plan: bool = Field(default=False, description="Step 3: cease/prevent/mitigate")
    tracks_effectiveness: bool = Field(
        default=False, description="Step 4: track implementation & results"
    )
    communicates_publicly: bool = Field(default=False, description="Step 5: communicate")
    # Step 6 is derived from grievance + remediation


OECD_STEPS = [
    "1. Embed responsible business conduct in policies & management systems",
    "2. Identify & assess actual and potential adverse impacts",
    "3. Cease, prevent or mitigate adverse impacts",
    "4. Track implementation and results",
    "5. Communicate how impacts are addressed",
    "6. Provide for or cooperate in remediation",
]


class HRDDResult(BaseModel):
    company_name: str = ""
    salient_issues_ranked: list[SalientIssue] = Field(default_factory=list)
    top_priority_issues: list[str] = Field(default_factory=list)
    value_chain_coverage: dict[str, int] = Field(default_factory=dict)
    grievance_effectiveness_pct: float = 0.0
    remediation_open: int = 0
    remediation_remediated: int = 0
    oecd_step_status: dict[str, bool] = Field(default_factory=dict)
    oecd_coverage_pct: float = 0.0
    csddd_readiness: str = ""
    overall_maturity: str = ""
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    living_wage_gap: dict | None = None


def assess_hrdd(input: HRDDInput) -> HRDDResult:  # noqa: A002
    """Run a risk-based HRDD screen aligned to UNGP + OECD + CSDDD."""
    ranked = sorted(input.salient_issues, key=lambda i: i.salience_score, reverse=True)
    top = [i.name for i in ranked if i.priority in ("high", "critical")]

    coverage: dict[str, int] = {}
    for i in input.salient_issues:
        coverage[i.value_chain_tier] = coverage.get(i.value_chain_tier, 0) + 1

    open_cases = sum(
        1
        for c in input.remediation_cases
        if c.status in ("identified", "plan_agreed", "in_progress")
    )
    remediated = sum(
        1 for c in input.remediation_cases if c.status in ("remediated", "closed_no_action")
    )

    # Step 6 derived: remediation provided if a grievance mechanism tracks to
    # remediation OR at least one case has been remediated.
    step6 = input.grievance.tracks_to_remediation or remediated > 0
    steps = {
        OECD_STEPS[0]: input.has_rbc_policy,
        OECD_STEPS[1]: input.has_impact_identification or bool(input.salient_issues),
        OECD_STEPS[2]: input.has_mitigation_plan,
        OECD_STEPS[3]: input.tracks_effectiveness,
        OECD_STEPS[4]: input.communicates_publicly,
        OECD_STEPS[5]: step6,
    }
    oecd_pct = round(sum(1 for v in steps.values() if v) / len(steps) * 100, 1)

    findings: list[str] = []
    recs: list[str] = []

    gross = [i for i in ranked if i.category in _GROSS_CATEGORIES]
    if gross:
        findings.append(
            f"{len(gross)} gross human-rights risk(s) flagged (forced/child labour, "
            "modern slavery) — these require immediate action regardless of likelihood."
        )
        recs.append(
            "Escalate gross human-rights risks to senior management and trigger an enhanced due-diligence review."
        )

    critical = [i for i in ranked if i.priority == "critical"]
    if critical:
        findings.append(f"{len(critical)} critical-priority salient issue(s) identified.")

    if "tier_2plus_suppliers" not in coverage and input.salient_issues:
        findings.append(
            "No salient issues mapped beyond tier-1 — deeper value-chain visibility is likely incomplete."
        )
        recs.append(
            "Extend impact identification to tier-2+ suppliers (CSDDD expects a risk-based value-chain view)."
        )

    g = input.grievance.effectiveness_score_pct
    if g < 50:
        recs.append(
            "Strengthen the operational grievance mechanism against UNGP Principle 31 "
            "(accessibility to value-chain workers, anonymity, non-retaliation, remediation linkage)."
        )

    for missing in [step for step, done in steps.items() if not done]:
        recs.append(f"Address OECD due-diligence {missing}.")

    # CSDDD readiness band.
    if oecd_pct >= 80 and g >= 50 and not [i for i in gross if i.priority == "critical"]:
        csddd = "Largely aligned — formalise and document for CSDDD assurance."
    elif oecd_pct >= 50:
        csddd = "Partial — core process exists; close value-chain and remediation gaps."
    else:
        csddd = "Early — establish the OECD 6-step cycle before CSDDD transposition (MS by 26 Jul 2028)."

    if oecd_pct >= 80 and g >= 67:
        maturity = "Established"
    elif oecd_pct >= 50:
        maturity = "Developing"
    else:
        maturity = "Initial"

    if not recs:
        recs.append(
            "HRDD process is robust — maintain monitoring cadence and refresh the salience assessment annually."
        )

    living_wage = None
    if input.wages:
        from openharness.impact.living_wage import living_wage_gap

        living_wage = living_wage_gap(
            input.living_wage_geography or (input.geographies[0] if input.geographies else ""),
            input.wages,
        )
    return HRDDResult(
        company_name=input.company_name,
        salient_issues_ranked=ranked,
        top_priority_issues=top,
        value_chain_coverage=coverage,
        grievance_effectiveness_pct=g,
        remediation_open=open_cases,
        remediation_remediated=remediated,
        oecd_step_status=steps,
        oecd_coverage_pct=oecd_pct,
        csddd_readiness=csddd,
        overall_maturity=maturity,
        findings=findings,
        recommendations=recs,
        living_wage_gap=living_wage,
        limitations=[
            "Severity/likelihood inputs are self-reported; a salient-issue assessment "
            "should be validated with affected-stakeholder consultation.",
            "This screen structures HRDD against UNGP/OECD/CSDDD — it is not a legal "
            "compliance determination.",
        ],
    )


# --------------------------------------------------------------------------
# Lightweight text-driven salience seeding (when structured inputs are absent).
# --------------------------------------------------------------------------

_CATEGORY_HINTS: dict[IssueCategory, tuple[str, ...]] = {
    "forced_labour": ("forced labour", "forced labor", "bonded labour", "compulsory labour"),
    "child_labour": ("child labour", "child labor", "underage worker"),
    "modern_slavery": ("modern slavery", "human trafficking", "trafficking"),
    "living_wage": ("living wage", "minimum wage", "wage gap", "underpaid"),
    "health_and_safety": ("health and safety", "ohs", "workplace safety", "accident", "injury"),
    "freedom_of_association": ("union", "collective bargaining", "freedom of association"),
    "discrimination": ("discrimination", "harassment", "gender pay"),
    "working_hours": ("excessive overtime", "working hours", "overtime"),
    "land_rights": ("land rights", "land grab", "resettlement", "displacement"),
    "indigenous_rights": ("indigenous", "fpic", "free prior and informed consent"),
    "community_impact": ("community", "local livelihoods", "pollution affecting"),
    "water_access": ("water access", "water scarcity", "water rights"),
    "privacy": ("data privacy", "surveillance", "personal data"),
}


def seed_salient_issues_from_text(
    text: str, *, default_tier: ValueChainTier = "tier_1_suppliers"
) -> list[SalientIssue]:
    """Heuristically seed salient issues from free text for a first-pass screen."""
    low = text.lower()
    issues: list[SalientIssue] = []
    for category, hints in _CATEGORY_HINTS.items():
        if any(h in low for h in hints):
            sev: Severity = "critical" if category in _GROSS_CATEGORIES else "high"
            issues.append(
                SalientIssue(
                    name=category.replace("_", " ").title(),
                    category=category,
                    value_chain_tier=default_tier,
                    severity=sev,
                    likelihood="medium",
                    evidence="Keyword signal in supplied text (validate with stakeholder consultation).",
                )
            )
    return issues


__all__ = [
    "ValueChainTier",
    "IssueCategory",
    "Severity",
    "SalientIssue",
    "GrievanceMechanism",
    "RemediationCase",
    "HRDDInput",
    "HRDDResult",
    "OECD_STEPS",
    "assess_hrdd",
    "seed_salient_issues_from_text",
]
