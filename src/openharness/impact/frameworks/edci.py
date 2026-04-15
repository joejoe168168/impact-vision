"""EDCI (ESG Data Convergence Initiative) 17 core PE/VC metrics.

The EDCI standardizes ESG metrics for Private Equity and Venture Capital.
17 core metrics across Environment, Social, and Governance categories.

Reference: https://www.esgdc.org/
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EDCIMetric(BaseModel):
    """An EDCI core metric."""
    id: str
    name: str
    category: str  # "environment", "social", "governance"
    description: str = ""
    unit: str = ""
    iris_cross_refs: list[str] = Field(default_factory=list)
    gri_cross_refs: list[str] = Field(default_factory=list)
    sfdr_cross_refs: list[int] = Field(default_factory=list)


EDCI_METRICS: list[EDCIMetric] = [
    # Environment
    EDCIMetric(
        id="EDCI-E1", name="Scope 1 GHG Emissions", category="environment",
        description="Total Scope 1 (direct) greenhouse gas emissions in metric tonnes CO2e",
        unit="tCO2e",
        iris_cross_refs=["OI4112"], gri_cross_refs=["305-1"], sfdr_cross_refs=[1],
    ),
    EDCIMetric(
        id="EDCI-E2", name="Scope 2 GHG Emissions", category="environment",
        description="Total Scope 2 (energy indirect) greenhouse gas emissions in metric tonnes CO2e",
        unit="tCO2e",
        gri_cross_refs=["305-2"], sfdr_cross_refs=[1],
    ),
    EDCIMetric(
        id="EDCI-E3", name="Scope 3 GHG Emissions", category="environment",
        description="Total Scope 3 (value chain) greenhouse gas emissions in metric tonnes CO2e. Optional but encouraged.",
        unit="tCO2e",
        gri_cross_refs=["305-3"], sfdr_cross_refs=[1],
    ),
    EDCIMetric(
        id="EDCI-E4", name="Renewable Energy", category="environment",
        description="Percentage of total energy consumed that is renewable",
        unit="%",
        sfdr_cross_refs=[5],
    ),
    EDCIMetric(
        id="EDCI-E5", name="Total Energy Consumption", category="environment",
        description="Total energy consumed in megawatt hours (MWh)",
        unit="MWh",
        gri_cross_refs=["302-1"], sfdr_cross_refs=[6],
    ),
    EDCIMetric(
        id="EDCI-E6", name="Net Zero Commitment", category="environment",
        description="Whether the company has made a commitment to achieve net zero emissions",
        unit="Yes/No + target year",
    ),
    # Social
    EDCIMetric(
        id="EDCI-S1", name="Work-Related Injuries", category="social",
        description="Number of work-related injuries per 200,000 hours worked (OSHA recordable rate)",
        unit="per 200,000 hours",
        gri_cross_refs=["403-9"],
    ),
    EDCIMetric(
        id="EDCI-S2", name="Work-Related Fatalities", category="social",
        description="Number of work-related fatalities",
        unit="count",
        gri_cross_refs=["403-9"],
    ),
    EDCIMetric(
        id="EDCI-S3", name="Employee Net Promoter Score", category="social",
        description="Employee NPS or equivalent engagement score",
        unit="NPS score",
    ),
    EDCIMetric(
        id="EDCI-S4", name="Percentage Female Employees", category="social",
        description="Percentage of employees who are female",
        unit="%",
        iris_cross_refs=["OI6213"], gri_cross_refs=["405-1"],
    ),
    EDCIMetric(
        id="EDCI-S5", name="Percentage Female in C-Suite", category="social",
        description="Percentage of C-suite executives who are female",
        unit="%",
        iris_cross_refs=["OI1571"], gri_cross_refs=["405-1"],
    ),
    EDCIMetric(
        id="EDCI-S6", name="Percentage Female on Board", category="social",
        description="Percentage of board members who are female",
        unit="%",
        iris_cross_refs=["OI1075"], gri_cross_refs=["405-1"], sfdr_cross_refs=[13],
    ),
    EDCIMetric(
        id="EDCI-S7", name="Employee Turnover Rate", category="social",
        description="Voluntary and involuntary employee turnover rate",
        unit="%",
        gri_cross_refs=["401-1"],
    ),
    EDCIMetric(
        id="EDCI-S8", name="Living Wage", category="social",
        description="Percentage of employees earning at or above the living wage",
        unit="%",
        iris_cross_refs=["OI1582"], gri_cross_refs=["202-1"],
    ),
    # Governance
    EDCIMetric(
        id="EDCI-G1", name="Board Independence", category="governance",
        description="Percentage of board members who are independent",
        unit="%",
    ),
    EDCIMetric(
        id="EDCI-G2", name="Data Privacy & Security", category="governance",
        description="Whether the company has experienced a data breach in the reporting year",
        unit="Yes/No + count",
        gri_cross_refs=["418-1"],
    ),
    EDCIMetric(
        id="EDCI-G3", name="Sustainability Oversight", category="governance",
        description="Whether the board or a board committee has oversight of ESG/sustainability matters",
        unit="Yes/No",
    ),
]


def get_edci_metrics(category: str | None = None) -> list[EDCIMetric]:
    if category:
        return [m for m in EDCI_METRICS if m.category == category]
    return EDCI_METRICS


def assess_edci_coverage(
    reported_data: dict[str, str] | None = None,
    company_description: str = "",
    document_text: str = "",
) -> dict:
    """Assess which EDCI metrics a company has data for.

    Returns coverage analysis with cross-references to other standards.
    """
    text = f"{company_description} {document_text}".lower()
    reported = reported_data or {}

    metric_keywords = {
        "EDCI-E1": ["scope 1", "direct emission", "ghg scope 1"],
        "EDCI-E2": ["scope 2", "indirect emission", "electricity emission"],
        "EDCI-E3": ["scope 3", "value chain emission"],
        "EDCI-E4": ["renewable energy", "solar", "wind energy", "clean energy"],
        "EDCI-E5": ["energy consumption", "total energy", "MWh", "megawatt"],
        "EDCI-E6": ["net zero", "carbon neutral", "emission target"],
        "EDCI-S1": ["work-related injur", "OSHA", "recordable rate", "workplace injur"],
        "EDCI-S2": ["fatalit", "work-related death"],
        "EDCI-S3": ["employee NPS", "employee satisfaction", "engagement score", "employee engagement"],
        "EDCI-S4": ["female employee", "women employee", "gender split"],
        "EDCI-S5": ["female c-suite", "women leadership", "female executive"],
        "EDCI-S6": ["female board", "women on board", "board gender"],
        "EDCI-S7": ["employee turnover", "attrition rate", "retention rate"],
        "EDCI-S8": ["living wage", "minimum wage", "wage equity"],
        "EDCI-G1": ["board independence", "independent director"],
        "EDCI-G2": ["data breach", "data privacy", "cybersecurity"],
        "EDCI-G3": ["ESG oversight", "sustainability committee", "board ESG"],
    }

    result = {
        "framework": "EDCI (17 Core PE/VC Metrics)",
        "metrics": [],
        "total": len(EDCI_METRICS),
        "addressed": 0,
        "by_category": {"environment": {"total": 0, "addressed": 0}, "social": {"total": 0, "addressed": 0}, "governance": {"total": 0, "addressed": 0}},
    }

    for metric in EDCI_METRICS:
        addressed = False
        evidence: list[str] = []

        kws = metric_keywords.get(metric.id, [])
        hits = [kw for kw in kws if kw in text]
        if hits:
            addressed = True
            evidence.extend(hits)

        if metric.iris_cross_refs:
            for ref in metric.iris_cross_refs:
                if ref in reported:
                    addressed = True
                    evidence.append(f"IRIS+ {ref}")

        m_result = {
            "id": metric.id,
            "name": metric.name,
            "category": metric.category,
            "addressed": addressed,
            "evidence": evidence,
            "cross_references": {
                "iris": metric.iris_cross_refs,
                "gri": metric.gri_cross_refs,
                "sfdr_pai": metric.sfdr_cross_refs,
            },
        }
        result["metrics"].append(m_result)

        cat = result["by_category"][metric.category]
        cat["total"] += 1
        if addressed:
            result["addressed"] += 1
            cat["addressed"] += 1

    result["coverage_pct"] = round(result["addressed"] / result["total"] * 100, 1)
    for cat_data in result["by_category"].values():
        cat_data["coverage_pct"] = round(cat_data["addressed"] / cat_data["total"] * 100, 1) if cat_data["total"] > 0 else 0

    return result
