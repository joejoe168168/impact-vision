"""2X Criteria — gender-lens investing standard (2X Global).

The 2X Criteria are the global standard for gender-lens investing, used by
DFIs, funds and investors to identify investments that empower women. This
module implements a structured screening against the 2X Criteria dimensions
plus the mandatory 2X minimum requirements (governance & accountability and
prevention of gender-based violence and harassment, "GBVH").

An investment **qualifies as 2X** when it meets at least one of the six
dimension thresholds AND satisfies the minimum requirements.

Dimensions:
  1. Entrepreneurship   — women ownership / women-founded.
  2. Leadership         — women in senior management or on the board.
  3. Employment         — women in the workforce + a quality-of-work indicator.
  4. Supply Chain       — spend with / commitments to women-owned businesses.
  5. Products & Services — products/services that disproportionately benefit women.
  6. Portfolio (FIs)    — share of the portfolio/loan book that is 2X-aligned.

Reference: 2X Global, "2X Criteria" (2024 update). Sector-specific employment
thresholds are simplified here to a configurable default; consult the official
2X Criteria sector table for a binding determination.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# Default thresholds (2X Global 2024, simplified). Employment thresholds are
# sector-specific in the official criteria; 30% is the common floor.
DEFAULT_OWNERSHIP_THRESHOLD = 51.0
DEFAULT_LEADERSHIP_THRESHOLD = 30.0
DEFAULT_EMPLOYMENT_THRESHOLD = 30.0
DEFAULT_SUPPLY_CHAIN_THRESHOLD = 30.0
DEFAULT_PORTFOLIO_THRESHOLD = 30.0


class TwoXInput(BaseModel):
    """Structured inputs for a 2X Criteria screen. All percentages are 0-100."""

    # 1. Entrepreneurship
    women_ownership_pct: float | None = Field(default=None, ge=0, le=100)
    founded_by_woman: bool = False
    # 2. Leadership
    women_senior_management_pct: float | None = Field(default=None, ge=0, le=100)
    women_board_pct: float | None = Field(default=None, ge=0, le=100)
    # 3. Employment
    women_workforce_pct: float | None = Field(default=None, ge=0, le=100)
    has_quality_employment_indicator: bool = Field(
        default=False,
        description="≥1 'quality' indicator beyond legal compliance (e.g. policy, benefit, training)",
    )
    # 4. Supply chain
    women_owned_supplier_pct: float | None = Field(default=None, ge=0, le=100)
    supports_women_in_supply_chain: bool = False
    # 5. Products & services
    product_benefits_women: bool = False
    # 6. Portfolio (financial intermediaries)
    is_financial_intermediary: bool = False
    portfolio_2x_aligned_pct: float | None = Field(default=None, ge=0, le=100)
    # Minimum requirements (mandatory in 2024 criteria)
    has_gender_governance_accountability: bool = Field(
        default=False,
        description="Board/management accountability for gender commitments",
    )
    addresses_gbvh: bool = Field(
        default=False,
        description="Policy/process to prevent gender-based violence & harassment",
    )
    # Optional sector override for employment threshold
    employment_threshold_override: float | None = Field(default=None, ge=0, le=100)
    living_wage_geography: str = ""
    wages: list[dict] = Field(default_factory=list)


class TwoXDimensionResult(BaseModel):
    dimension: str
    met: bool = False
    threshold: float | None = None
    value: float | None = None
    rationale: str = ""


class TwoXResult(BaseModel):
    framework: str = "2X Criteria (2X Global, 2024)"
    qualifies_2x: bool = False
    dimensions_met: int = 0
    dimensions: list[TwoXDimensionResult] = Field(default_factory=list)
    minimum_requirements_met: bool = False
    minimum_requirement_gaps: list[str] = Field(default_factory=list)
    sdg_links: list[int] = Field(default_factory=lambda: [5, 8, 10])
    recommendations: list[str] = Field(default_factory=list)
    summary: str = ""
    limitations: list[str] = Field(default_factory=list)
    living_wage_gap: dict | None = None


def assess_2x_criteria(input: TwoXInput) -> TwoXResult:
    """Screen an investment against the 2X Criteria dimensions + minimum requirements."""
    dims: list[TwoXDimensionResult] = []

    # 1. Entrepreneurship
    own = input.women_ownership_pct
    ent_met = bool(input.founded_by_woman) or (
        own is not None and own >= DEFAULT_OWNERSHIP_THRESHOLD
    )
    dims.append(
        TwoXDimensionResult(
            dimension="Entrepreneurship",
            met=ent_met,
            threshold=DEFAULT_OWNERSHIP_THRESHOLD,
            value=own,
            rationale=(
                "Woman-founded"
                if input.founded_by_woman
                else f"Women ownership {own}% vs ≥{DEFAULT_OWNERSHIP_THRESHOLD}%"
                if own is not None
                else "No ownership data"
            ),
        )
    )

    # 2. Leadership
    lead_val = max(
        [v for v in (input.women_senior_management_pct, input.women_board_pct) if v is not None],
        default=None,
    )
    lead_met = lead_val is not None and lead_val >= DEFAULT_LEADERSHIP_THRESHOLD
    dims.append(
        TwoXDimensionResult(
            dimension="Leadership",
            met=lead_met,
            threshold=DEFAULT_LEADERSHIP_THRESHOLD,
            value=lead_val,
            rationale=(
                f"Women in senior mgmt/board {lead_val}% vs ≥{DEFAULT_LEADERSHIP_THRESHOLD}%"
                if lead_val is not None
                else "No leadership data"
            ),
        )
    )

    # 3. Employment
    emp_threshold = input.employment_threshold_override or DEFAULT_EMPLOYMENT_THRESHOLD
    wf = input.women_workforce_pct
    emp_met = wf is not None and wf >= emp_threshold and input.has_quality_employment_indicator
    dims.append(
        TwoXDimensionResult(
            dimension="Employment",
            met=emp_met,
            threshold=emp_threshold,
            value=wf,
            rationale=(
                f"Women workforce {wf}% vs ≥{emp_threshold}% "
                + (
                    "+ quality indicator"
                    if input.has_quality_employment_indicator
                    else "(quality indicator MISSING)"
                )
                if wf is not None
                else "No workforce data"
            ),
        )
    )

    # 4. Supply chain
    sc = input.women_owned_supplier_pct
    sc_met = bool(input.supports_women_in_supply_chain) or (
        sc is not None and sc >= DEFAULT_SUPPLY_CHAIN_THRESHOLD
    )
    dims.append(
        TwoXDimensionResult(
            dimension="Supply Chain",
            met=sc_met,
            threshold=DEFAULT_SUPPLY_CHAIN_THRESHOLD,
            value=sc,
            rationale=(
                "Supports women in supply chain"
                if input.supports_women_in_supply_chain
                else f"Women-owned supplier spend {sc}% vs ≥{DEFAULT_SUPPLY_CHAIN_THRESHOLD}%"
                if sc is not None
                else "No supply-chain data"
            ),
        )
    )

    # 5. Products & services
    dims.append(
        TwoXDimensionResult(
            dimension="Products & Services",
            met=bool(input.product_benefits_women),
            rationale=(
                "Product/service disproportionately benefits women"
                if input.product_benefits_women
                else "Not indicated"
            ),
        )
    )

    # 6. Portfolio (FIs only)
    if input.is_financial_intermediary:
        pf = input.portfolio_2x_aligned_pct
        pf_met = pf is not None and pf >= DEFAULT_PORTFOLIO_THRESHOLD
        dims.append(
            TwoXDimensionResult(
                dimension="Portfolio",
                met=pf_met,
                threshold=DEFAULT_PORTFOLIO_THRESHOLD,
                value=pf,
                rationale=(
                    f"2X-aligned portfolio {pf}% vs ≥{DEFAULT_PORTFOLIO_THRESHOLD}%"
                    if pf is not None
                    else "No portfolio data"
                ),
            )
        )

    dimensions_met = sum(1 for d in dims if d.met)

    # Minimum requirements (mandatory)
    min_gaps: list[str] = []
    if not input.has_gender_governance_accountability:
        min_gaps.append("No governance/management accountability for gender commitments")
    if not input.addresses_gbvh:
        min_gaps.append("No policy/process to prevent gender-based violence & harassment (GBVH)")
    min_met = not min_gaps

    qualifies = dimensions_met >= 1 and min_met

    recs: list[str] = []
    if dimensions_met == 0:
        recs.append(
            "No 2X dimension threshold met — collect women ownership/leadership/workforce data."
        )
    if not min_met:
        recs.append(
            "Address the 2X minimum requirements (governance accountability + GBVH prevention) — these are mandatory to qualify."
        )
    if dimensions_met >= 1 and not qualifies:
        recs.append(
            "Dimension threshold met but minimum requirements unmet — fix those to qualify as 2X."
        )
    if not recs:
        recs.append(
            "2X-qualified — document the evidence and consider committing to a 2X improvement target."
        )

    summary = (
        f"{'2X-QUALIFIED' if qualifies else 'NOT 2X-qualified'}: "
        f"{dimensions_met}/{len(dims)} dimensions met; "
        f"minimum requirements {'met' if min_met else 'NOT met'}."
    )

    living_wage = None
    if input.wages:
        from openharness.impact.living_wage import living_wage_gap

        living_wage = living_wage_gap(input.living_wage_geography, input.wages)
    return TwoXResult(
        qualifies_2x=qualifies,
        dimensions_met=dimensions_met,
        dimensions=dims,
        minimum_requirements_met=min_met,
        minimum_requirement_gaps=min_gaps,
        recommendations=recs,
        summary=summary,
        living_wage_gap=living_wage,
        limitations=[
            "Employment thresholds are sector-specific in the official 2X Criteria; "
            "this screen uses a configurable default (30%).",
            "Self-reported inputs — 2X verification / certification requires independent review.",
        ],
    )


# 2X-relevant signals for extracting structured inputs from free text.
# NOTE: hints must be self-evidently gendered — a bare "founded by" would match
# "founded by two men" and mis-qualify the Entrepreneurship dimension.
_FOUNDED_BY_WOMAN_HINTS = (
    "founded by a woman",
    "founded by women",
    "co-founded by a woman",
    "co-founded by women",
    "woman founder",
    "female founder",
    "female founders",
    "woman-founded",
    "women-founded",
    "women-led",
    "woman-led",
    "female-led",
    "female co-founder",
    "woman co-founder",
)
_PRODUCT_BENEFITS_HINTS = (
    "benefits women",
    "for women",
    "serves women",
    "female customers",
    "women beneficiaries",
    "girls",
)
_GBVH_HINTS = (
    "gbvh",
    "gender-based violence",
    "harassment policy",
    "anti-harassment",
    "safeguarding",
)
_GOVERNANCE_HINTS = (
    "gender policy",
    "gender strategy",
    "diversity policy",
    "gender accountability",
    "deib",
)


def screen_2x_from_text(
    description: str = "",
    document_text: str = "",
    reported_metrics: dict[str, str] | None = None,
) -> TwoXResult:
    """Build a :class:`TwoXInput` from text + reported metrics, then assess.

    Numeric percentages are read from ``reported_metrics`` keys when present:
    ``women_ownership_pct``, ``women_senior_management_pct``, ``women_board_pct``,
    ``women_workforce_pct``, ``women_owned_supplier_pct``, ``portfolio_2x_aligned_pct``.
    Boolean signals are inferred from keyword hints in the text.
    """
    import re as _re

    text = f"{description} {document_text}".lower()
    metrics = reported_metrics or {}

    def word(term: str) -> bool:
        return bool(_re.search(r"\b" + _re.escape(term) + r"\b", text))

    def num(key: str) -> float | None:
        raw = metrics.get(key)
        if raw is None:
            return None
        try:
            return float(str(raw).replace("%", "").strip())
        except (TypeError, ValueError):
            return None

    data = TwoXInput(
        women_ownership_pct=num("women_ownership_pct"),
        founded_by_woman=any(h in text for h in _FOUNDED_BY_WOMAN_HINTS),
        women_senior_management_pct=num("women_senior_management_pct"),
        women_board_pct=num("women_board_pct"),
        women_workforce_pct=num("women_workforce_pct"),
        has_quality_employment_indicator=(
            "training" in text or "parental leave" in text or "equal pay" in text
        ),
        women_owned_supplier_pct=num("women_owned_supplier_pct"),
        supports_women_in_supply_chain=(
            "women-owned supplier" in text or "women suppliers" in text
        ),
        product_benefits_women=any(h in text for h in _PRODUCT_BENEFITS_HINTS),
        # Word-boundary matching: a bare substring "fund" would match "funding"
        # / "refund" and misclassify operating companies as intermediaries.
        is_financial_intermediary=(
            word("fund")
            or word("funds")
            or word("lender")
            or word("microfinance")
            or word("loan book")
            or "financial institution" in text
            or "loan portfolio" in text
            or "investment portfolio" in text
        ),
        portfolio_2x_aligned_pct=num("portfolio_2x_aligned_pct"),
        has_gender_governance_accountability=any(h in text for h in _GOVERNANCE_HINTS),
        addresses_gbvh=any(h in text for h in _GBVH_HINTS),
    )
    return assess_2x_criteria(data)


__all__ = [
    "TwoXInput",
    "TwoXDimensionResult",
    "TwoXResult",
    "assess_2x_criteria",
    "screen_2x_from_text",
]
