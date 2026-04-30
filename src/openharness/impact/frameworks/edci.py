"""EDCI (ESG Data Convergence Initiative) 17 core PE/VC metrics.

The EDCI standardizes ESG metrics for Private Equity and Venture Capital.
17 core metrics across Environment, Social, and Governance categories.

Reference: https://www.esgdc.org/
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.models import MetricRecord


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


class EDCICompletenessRow(BaseModel):
    """Completeness status for one EDCI metric for one company."""

    company_name: str
    edci_id: str
    name: str
    category: str
    unit: str = ""
    status: Literal["available", "proxy", "missing", "not_applicable"] = "missing"
    value: str = ""
    source_metric_id: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str = ""


class EDCICompletenessReport(BaseModel):
    """Company-level or portfolio-level EDCI completeness report."""

    scope: Literal["company", "portfolio"] = "company"
    company_count: int = 1
    rows: list[EDCICompletenessRow] = Field(default_factory=list)
    total_fields: int = 0
    available: int = 0
    proxy: int = 0
    missing: int = 0
    not_applicable: int = 0
    by_category: dict[str, dict[str, int | float]] = Field(default_factory=dict)
    completeness_pct: float = 0.0


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


def _summarize_rows(
    rows: list[EDCICompletenessRow],
    *,
    scope: Literal["company", "portfolio"],
    company_count: int,
) -> EDCICompletenessReport:
    counts = {
        "available": sum(1 for row in rows if row.status == "available"),
        "proxy": sum(1 for row in rows if row.status == "proxy"),
        "missing": sum(1 for row in rows if row.status == "missing"),
        "not_applicable": sum(1 for row in rows if row.status == "not_applicable"),
    }
    by_category: dict[str, dict[str, int | float]] = {}
    for row in rows:
        cat = by_category.setdefault(
            row.category,
            {"total": 0, "available": 0, "proxy": 0, "missing": 0, "not_applicable": 0, "completeness_pct": 0.0},
        )
        cat["total"] = int(cat["total"]) + 1
        cat[row.status] = int(cat[row.status]) + 1
    for cat in by_category.values():
        complete = int(cat["available"]) + int(cat["proxy"]) + int(cat["not_applicable"])
        cat["completeness_pct"] = round(complete / int(cat["total"]) * 100, 1) if cat["total"] else 0.0

    total = len(rows)
    complete_count = counts["available"] + counts["proxy"] + counts["not_applicable"]
    return EDCICompletenessReport(
        scope=scope,
        company_count=company_count,
        rows=rows,
        total_fields=total,
        available=counts["available"],
        proxy=counts["proxy"],
        missing=counts["missing"],
        not_applicable=counts["not_applicable"],
        by_category=by_category,
        completeness_pct=round(complete_count / total * 100, 1) if total else 0.0,
    )


def assess_edci_completeness(
    *,
    company_name: str,
    metric_records: list[MetricRecord | dict] | None = None,
    reported_data: dict[str, str] | None = None,
    proxy_values: dict[str, str] | None = None,
    not_applicable: list[str] | set[str] | None = None,
) -> EDCICompletenessReport:
    """Assess EDCI completeness with explicit available/proxy/missing/NA status.

    ``reported_data`` may be keyed by either EDCI IDs (for metrics without IRIS+
    cross-references) or IRIS+ IDs. Canonical ``MetricRecord`` rows are preferred
    because they preserve evidence references.
    """
    records = [
        item if isinstance(item, MetricRecord) else MetricRecord.model_validate(item)
        for item in (metric_records or [])
    ]
    record_by_metric_id = {record.metric_id: record for record in records}
    reported = {str(k).strip().upper(): str(v) for k, v in (reported_data or {}).items()}
    proxies = {str(k).strip().upper(): str(v) for k, v in (proxy_values or {}).items()}
    na = {str(v).strip().upper() for v in (not_applicable or [])}

    rows: list[EDCICompletenessRow] = []
    for metric in EDCI_METRICS:
        source_record: MetricRecord | None = None
        source_metric_id = ""
        value = ""
        status: Literal["available", "proxy", "missing", "not_applicable"] = "missing"
        notes = ""

        if metric.id in na:
            status = "not_applicable"
            notes = "Marked not applicable by reviewer."
        elif metric.id in reported:
            status = "available"
            source_metric_id = metric.id
            value = reported[metric.id]
        else:
            for ref in metric.iris_cross_refs:
                ref_key = ref.upper()
                if ref_key in record_by_metric_id:
                    source_record = record_by_metric_id[ref_key]
                    status = "available"
                    source_metric_id = ref_key
                    value = str(source_record.value)
                    break
                if ref_key in reported:
                    status = "available"
                    source_metric_id = ref_key
                    value = reported[ref_key]
                    break
            if status == "missing" and metric.id in proxies:
                status = "proxy"
                value = proxies[metric.id]
                notes = "Proxy estimate supplied."

        rows.append(EDCICompletenessRow(
            company_name=company_name,
            edci_id=metric.id,
            name=metric.name,
            category=metric.category,
            unit=metric.unit,
            status=status,
            value=value,
            source_metric_id=source_metric_id,
            evidence_refs=source_record.evidence_refs if source_record else [],
            notes=notes,
        ))

    return _summarize_rows(rows, scope="company", company_count=1)


def portfolio_edci_completeness(
    companies: list[dict],
) -> EDCICompletenessReport:
    """Roll up EDCI completeness for multiple company payloads.

    Each payload accepts ``company_name``, ``metric_records``, ``reported_data``,
    ``proxy_values``, and ``not_applicable`` keys.
    """
    all_rows: list[EDCICompletenessRow] = []
    for company in companies:
        report = assess_edci_completeness(
            company_name=str(company.get("company_name") or company.get("name") or "Unknown"),
            metric_records=company.get("metric_records") or [],
            reported_data=company.get("reported_data") or company.get("reported_metrics") or {},
            proxy_values=company.get("proxy_values") or {},
            not_applicable=company.get("not_applicable") or [],
        )
        all_rows.extend(report.rows)
    return _summarize_rows(all_rows, scope="portfolio", company_count=len(companies))


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
