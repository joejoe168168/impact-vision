"""EFRAG Voluntary SME Standard (VSME).

The VSME is EFRAG's voluntary sustainability-reporting standard for
micro-, small- and medium-sized undertakings that are **not** in mandatory
CSRD scope. After the EU Omnibus I simplification (Directive (EU) 2026/470)
narrowed CSRD to undertakings with >1,000 employees AND >€450M turnover, the
VSME has become the de-facto reporting ask for the many investee SMEs that
still receive sustainability data requests from banks, investors and large
customers. Omnibus I also created a "value-chain cap": in-scope undertakings
may not demand more from a small supplier than the VSME data set.

Structure (EFRAG VSME, final version Dec 2024):

* **Basic Module** — B1-B11: the minimum disclosure set, suitable for the
  smallest undertakings.
* **Comprehensive Module** — C1-C9: additional disclosures for undertakings
  with more complex needs, or those responding to bank/investor requests.

Reference: EFRAG, "Voluntary sustainability reporting standard for non-listed
micro-, small- and medium-sized undertakings (VSME)", December 2024.

This module ships the disclosure catalogue plus a lightweight keyword/metric
*coverage screening* (mirroring :mod:`openharness.impact.frameworks.esrs`). It
is a readiness signal, not a VSME conformity opinion.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


VSMEModule = str  # "basic" | "comprehensive"


class VSMEDisclosure(BaseModel):
    """A single VSME disclosure requirement."""

    code: str
    name: str
    module: VSMEModule
    pillar: str  # "general" | "environment" | "social" | "governance"
    description: str = ""
    data_points: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    iris_cross_refs: list[str] = Field(default_factory=list)
    esrs_cross_refs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Basic Module (B1-B11)
# ---------------------------------------------------------------------------

_BASIC: list[VSMEDisclosure] = [
    VSMEDisclosure(
        code="B1", name="Basis for preparation", module="basic", pillar="general",
        description="Reporting option chosen (Basic / Comprehensive), entities covered, and consolidation basis.",
        keywords=["basis for preparation", "reporting boundary", "consolidation", "report scope"],
        esrs_cross_refs=["ESRS 1"],
    ),
    VSMEDisclosure(
        code="B2", name="Practices, policies and future initiatives for transitioning towards a more sustainable economy",
        module="basic", pillar="general",
        description="Sustainability practices or policies in place and any future initiatives.",
        keywords=["sustainability policy", "transition", "initiative", "practices", "roadmap"],
        esrs_cross_refs=["ESRS 2 MDR-P"],
    ),
    VSMEDisclosure(
        code="B3", name="Energy and greenhouse gas emissions", module="basic", pillar="environment",
        description="Total energy consumption and gross Scope 1 and Scope 2 GHG emissions.",
        data_points=["total_energy_mwh", "scope1_tco2e", "scope2_tco2e"],
        keywords=["energy", "electricity", "ghg", "emission", "scope 1", "scope 2", "carbon", "fuel"],
        iris_cross_refs=["OI4112", "OI1479"], esrs_cross_refs=["E1-5", "E1-6"],
    ),
    VSMEDisclosure(
        code="B4", name="Pollution of air, water and soil", module="basic", pillar="environment",
        description="Pollutants emitted where the undertaking is legally required to report them.",
        keywords=["pollution", "air emission", "water discharge", "soil", "pollutant", "effluent"],
        esrs_cross_refs=["E2-4"],
    ),
    VSMEDisclosure(
        code="B5", name="Biodiversity", module="basic", pillar="environment",
        description="Number/area of sites owned, leased or managed in or near biodiversity-sensitive areas.",
        keywords=["biodiversity", "protected area", "land use", "habitat", "nature", "ecosystem"],
        esrs_cross_refs=["E4-5"],
    ),
    VSMEDisclosure(
        code="B6", name="Water", module="basic", pillar="environment",
        description="Total water withdrawal, and water consumption in water-stressed areas.",
        data_points=["water_withdrawal_m3", "water_consumption_m3"],
        keywords=["water", "withdrawal", "consumption", "water stress", "abstraction"],
        esrs_cross_refs=["E3-4"],
    ),
    VSMEDisclosure(
        code="B7", name="Resource use, circular economy and waste management", module="basic", pillar="environment",
        description="Materials use, circular-economy practices, and total waste generated (hazardous/non-hazardous).",
        data_points=["total_waste_t", "hazardous_waste_t", "recycled_pct"],
        keywords=["circular economy", "waste", "recycling", "material", "reuse", "hazardous waste"],
        esrs_cross_refs=["E5-4", "E5-5"],
    ),
    VSMEDisclosure(
        code="B8", name="Workforce — general characteristics", module="basic", pillar="social",
        description="Number of employees by contract type and gender; country breakdown.",
        data_points=["headcount", "headcount_by_gender", "headcount_by_contract"],
        keywords=["employees", "headcount", "workforce", "gender", "contract", "permanent", "temporary"],
        iris_cross_refs=["OI3757"], esrs_cross_refs=["S1-6"],
    ),
    VSMEDisclosure(
        code="B9", name="Workforce — health and safety", module="basic", pillar="social",
        description="Work-related accidents and number of fatalities.",
        data_points=["recordable_accidents", "fatalities", "accident_rate"],
        keywords=["health and safety", "accident", "injury", "fatality", "occupational", "incident rate"],
        esrs_cross_refs=["S1-14"],
    ),
    VSMEDisclosure(
        code="B10", name="Workforce — remuneration, collective bargaining and training",
        module="basic", pillar="social",
        description="Minimum-wage compliance, gender pay gap, collective-bargaining coverage, and training hours.",
        data_points=["gender_pay_gap_pct", "collective_bargaining_pct", "training_hours_per_employee"],
        keywords=["wage", "pay gap", "collective bargaining", "training", "remuneration", "minimum wage"],
        esrs_cross_refs=["S1-10", "S1-13", "S1-16", "S1-17"],
    ),
    VSMEDisclosure(
        code="B11", name="Convictions and fines for corruption and bribery", module="basic", pillar="governance",
        description="Number of convictions and total fines for violation of anti-corruption / anti-bribery laws.",
        data_points=["corruption_convictions", "corruption_fines_eur"],
        keywords=["corruption", "bribery", "conviction", "fine", "anti-corruption", "anti-bribery"],
        esrs_cross_refs=["G1-4"],
    ),
]


# ---------------------------------------------------------------------------
# Comprehensive Module (C1-C9)
# ---------------------------------------------------------------------------

_COMPREHENSIVE: list[VSMEDisclosure] = [
    VSMEDisclosure(
        code="C1", name="Strategy — business model and sustainability-related initiatives",
        module="comprehensive", pillar="general",
        description="Significant groups of products/services, markets, and key sustainability-related business relationships.",
        keywords=["business model", "strategy", "products", "markets", "value chain", "business relationships"],
        esrs_cross_refs=["SBM-1"],
    ),
    VSMEDisclosure(
        code="C2", name="Description of practices, policies and future initiatives for transitioning",
        module="comprehensive", pillar="general",
        description="Further detail on targets and progress for the practices/policies reported under B2.",
        keywords=["targets", "policy detail", "progress", "transition plan", "milestones"],
        esrs_cross_refs=["ESRS 2 MDR-T"],
    ),
    VSMEDisclosure(
        code="C3", name="GHG reduction targets and climate transition", module="comprehensive", pillar="environment",
        description="GHG-emission reduction targets (if any) and climate-transition actions.",
        data_points=["ghg_target_pct", "target_base_year", "target_year"],
        keywords=["reduction target", "net zero", "decarbonisation", "transition plan", "science-based"],
        esrs_cross_refs=["E1-1", "E1-4"],
    ),
    VSMEDisclosure(
        code="C4", name="Climate risks", module="comprehensive", pillar="environment",
        description="Physical and transition climate risks and how they affect the undertaking.",
        keywords=["climate risk", "physical risk", "transition risk", "flood", "drought", "carbon price"],
        esrs_cross_refs=["E1-9"],
    ),
    VSMEDisclosure(
        code="C5", name="Additional workforce characteristics", module="comprehensive", pillar="social",
        description="Additional own-workforce characteristics (e.g. age distribution, turnover, self-employed/agency).",
        data_points=["employee_turnover_pct", "age_distribution"],
        keywords=["turnover", "age", "self-employed", "agency workers", "workforce breakdown"],
        esrs_cross_refs=["S1-6", "S1-7"],
    ),
    VSMEDisclosure(
        code="C6", name="Additional own-workforce information — human-rights policies and processes",
        module="comprehensive", pillar="social",
        description="Human-rights policies covering own workforce (forced labour, child labour, discrimination).",
        keywords=["human rights", "forced labour", "child labour", "discrimination", "grievance", "non-discrimination"],
        esrs_cross_refs=["S1-1", "S1-3"],
    ),
    VSMEDisclosure(
        code="C7", name="Severe negative human-rights incidents", module="comprehensive", pillar="social",
        description="Confirmed severe human-rights incidents connected to the undertaking's workforce or value chain.",
        keywords=["human rights incident", "violation", "modern slavery", "value chain", "remediation"],
        esrs_cross_refs=["S2-4", "S3-4"],
    ),
    VSMEDisclosure(
        code="C8", name="Revenues from certain sectors and exclusion from EU benchmarks",
        module="comprehensive", pillar="governance",
        description="Revenue from controversial sectors (e.g. weapons, tobacco, fossil fuels) and EU-benchmark exclusions.",
        data_points=["revenue_controversial_sectors_pct"],
        keywords=["weapons", "tobacco", "fossil fuel", "controversial", "excluded activities", "coal"],
        esrs_cross_refs=["E1", "G1"],
    ),
    VSMEDisclosure(
        code="C9", name="Gender diversity ratio in the governance body", module="comprehensive", pillar="governance",
        description="Gender diversity ratio at the level of the administrative/management/supervisory body.",
        data_points=["board_gender_ratio"],
        keywords=["board gender", "governance diversity", "women on board", "diversity ratio"],
        esrs_cross_refs=["GOV-1"],
    ),
]

VSME_DISCLOSURES: list[VSMEDisclosure] = _BASIC + _COMPREHENSIVE


def get_vsme_disclosures(module: str | None = None) -> list[VSMEDisclosure]:
    """Return VSME disclosures, optionally filtered to 'basic' or 'comprehensive'."""
    if module:
        m = module.strip().lower()
        if m not in {"basic", "comprehensive"}:
            raise ValueError("module must be 'basic' or 'comprehensive'")
        return [d for d in VSME_DISCLOSURES if d.module == m]
    return list(VSME_DISCLOSURES)


class VSMEDisclosureResult(BaseModel):
    code: str
    name: str
    module: VSMEModule
    pillar: str
    addressed: bool = False
    evidence: list[str] = Field(default_factory=list)


class VSMEAssessmentResult(BaseModel):
    framework: str = "EFRAG Voluntary SME Standard (VSME)"
    module: VSMEModule = "comprehensive"
    assessment_basis: str = "keyword_and_metric_coverage_screening_not_a_conformity_opinion"
    basic_total: int = 0
    basic_addressed: int = 0
    comprehensive_total: int = 0
    comprehensive_addressed: int = 0
    overall_coverage_pct: float = 0.0
    disclosures: list[VSMEDisclosureResult] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    summary: str = ""
    limitations: list[str] = Field(default_factory=list)


def assess_vsme(
    description: str = "",
    document_text: str = "",
    sector: str = "",
    reported_metrics: dict[str, str] | None = None,
    module: str = "comprehensive",
) -> VSMEAssessmentResult:
    """Screen text + reported metrics for VSME disclosure coverage.

    ``module="basic"`` scores only B1-B11; ``module="comprehensive"`` scores the
    full Basic + Comprehensive set. A disclosure is counted as *addressed* when
    its keywords appear in the supplied text or one of its IRIS+ cross-refs is in
    ``reported_metrics``.
    """
    m = module.strip().lower()
    if m not in {"basic", "comprehensive"}:
        raise ValueError("module must be 'basic' or 'comprehensive'")

    text = f"{description} {document_text} {sector}".lower()
    metrics = reported_metrics or {}
    in_scope = get_vsme_disclosures("basic") if m == "basic" else VSME_DISCLOSURES

    results: list[VSMEDisclosureResult] = []
    gaps: list[str] = []
    for disc in in_scope:
        evidence: list[str] = []
        for kw in disc.keywords:
            if kw in text:
                evidence.append(kw)
        for ref in disc.iris_cross_refs:
            if ref in metrics:
                evidence.append(f"IRIS+ {ref}")
        addressed = len(evidence) >= 1
        if not addressed:
            gaps.append(f"{disc.code}: {disc.name}")
        results.append(VSMEDisclosureResult(
            code=disc.code, name=disc.name, module=disc.module,
            pillar=disc.pillar, addressed=addressed, evidence=sorted(set(evidence)),
        ))

    basic_results = [r for r in results if r.module == "basic"]
    comp_results = [r for r in results if r.module == "comprehensive"]
    basic_addressed = sum(1 for r in basic_results if r.addressed)
    comp_addressed = sum(1 for r in comp_results if r.addressed)
    total = len(results)
    addressed_total = basic_addressed + comp_addressed
    coverage = round(addressed_total / total * 100, 1) if total else 0.0

    summary = (
        f"VSME {m.title()} module: {addressed_total}/{total} disclosures show "
        f"coverage signals (Basic {basic_addressed}/{len(basic_results)}"
        + (f", Comprehensive {comp_addressed}/{len(comp_results)}" if comp_results else "")
        + ")."
    )

    return VSMEAssessmentResult(
        module=m,
        basic_total=len(basic_results),
        basic_addressed=basic_addressed,
        comprehensive_total=len(comp_results),
        comprehensive_addressed=comp_addressed,
        overall_coverage_pct=coverage,
        disclosures=results,
        gaps=gaps[:12],
        summary=summary,
        limitations=[
            "Coverage flags are keyword/metric screening signals, not a VSME conformity opinion.",
            "VSME is voluntary; the Basic module is the minimum, Comprehensive adds C1-C9.",
            "Under Omnibus I, in-scope CSRD undertakings may not demand more from small "
            "suppliers than the VSME data set (value-chain cap).",
        ],
    )


__all__ = [
    "VSMEDisclosure",
    "VSMEDisclosureResult",
    "VSMEAssessmentResult",
    "VSME_DISCLOSURES",
    "get_vsme_disclosures",
    "assess_vsme",
]
