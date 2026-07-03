"""EDCI (ESG Data Convergence Initiative) 2026 private-markets KPI set.

The EDCI standardizes sustainability metrics for private markets. Public 2026
materials group the KPIs into GHG emissions, decarbonization, renewable energy,
diversity, work-related accidents, net new hires, employee engagement, and
cybersecurity. Selected fields are explicitly non-core.

Reference: https://www.esgdc.org/metrics/
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.models import MetricRecord


class EDCIMetric(BaseModel):
    """An EDCI KPI field."""

    id: str
    name: str
    category: str  # "environment", "social", "governance"
    description: str = ""
    unit: str = ""
    data_points: list[str] = Field(default_factory=list)
    iris_cross_refs: list[str] = Field(default_factory=list)
    gri_cross_refs: list[str] = Field(default_factory=list)
    sfdr_cross_refs: list[int] = Field(default_factory=list)
    required: bool = True
    reporting_cycle: str = "2026"
    source_url: str = "https://www.esgdc.org/metrics/"


class EDCICompletenessRow(BaseModel):
    """Completeness status for one EDCI metric for one company."""

    company_name: str
    edci_id: str
    name: str
    category: str
    unit: str = ""
    required: bool = True
    reporting_cycle: str = "2026"
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
    required_fields: int = 0
    optional_fields: int = 0
    available: int = 0
    proxy: int = 0
    missing: int = 0
    not_applicable: int = 0
    required_complete: int = 0
    required_missing: int = 0
    required_completeness_pct: float = 0.0
    by_category: dict[str, dict[str, int | float]] = Field(default_factory=dict)
    completeness_pct: float = 0.0
    reporting_cycle: str = "2026"
    metric_set_note: str = ""


EDCI_REPORTING_CYCLE = "2026"
EDCI_METRIC_SET_NOTE = (
    "EDCI publishes annual guidance/templates and selected 2026 fields are non-core. "
    "Use this bundled map for readiness screening, then verify against the official "
    "EDCI submission template before LP or regulatory reporting."
)


EDCI_METRICS: list[EDCIMetric] = [
    # GHG emissions
    EDCIMetric(
        id="EDCI-E1", name="Scope 1 GHG Emissions", category="environment",
        description="Total Scope 1 (direct) greenhouse gas emissions in metric tonnes CO2e",
        unit="tCO2e",
        data_points=["Scope 1 emissions"],
        iris_cross_refs=["OI4112"], gri_cross_refs=["305-1"], sfdr_cross_refs=[1],
    ),
    EDCIMetric(
        id="EDCI-E2", name="Scope 2 GHG Emissions", category="environment",
        description="Total Scope 2 (energy indirect) greenhouse gas emissions in metric tonnes CO2e",
        unit="tCO2e",
        data_points=["Scope 2 emissions"],
        gri_cross_refs=["305-2"], sfdr_cross_refs=[1],
    ),
    EDCIMetric(
        id="EDCI-E3", name="Scope 3 GHG Emissions", category="environment",
        description="Total Scope 3 (value chain) greenhouse gas emissions in metric tonnes CO2e.",
        unit="tCO2e",
        data_points=["Scope 3 emissions"],
        gri_cross_refs=["305-3"], sfdr_cross_refs=[1],
        required=False,
    ),
    # Decarbonization
    EDCIMetric(
        id="EDCI-E4", name="Decarbonization Strategy", category="environment",
        description="Whether the company has a decarbonization strategy.",
        unit="Yes/No",
        data_points=["Strategy"],
    ),
    EDCIMetric(
        id="EDCI-E5", name="Decarbonization Target", category="environment",
        description="Whether the company has set a decarbonization target.",
        unit="Yes/No + target detail",
        data_points=["Target"],
    ),
    EDCIMetric(
        id="EDCI-E6", name="Decarbonization Ambition", category="environment",
        description="Stated level of decarbonization ambition, including net-zero ambition where applicable.",
        unit="qualitative",
        data_points=["Ambition"],
    ),
    # Renewable energy
    EDCIMetric(
        id="EDCI-E7", name="Renewable Energy Usage", category="environment",
        description="Percentage of energy usage from renewable sources.",
        unit="%",
        data_points=["% renewable energy usage"],
        iris_cross_refs=["OI8825", "OI3324", "OI3781"],
        gri_cross_refs=["302-1"],
        sfdr_cross_refs=[5],
    ),
    # Work-related accidents
    EDCIMetric(
        id="EDCI-S1", name="Work-Related Injuries", category="social",
        description="Work-related injuries.",
        unit="count or rate",
        data_points=["Injuries"],
        gri_cross_refs=["403-9"],
    ),
    EDCIMetric(
        id="EDCI-S2", name="Work-Related Fatalities", category="social",
        description="Work-related fatalities.",
        unit="count",
        data_points=["Fatalities"],
        gri_cross_refs=["403-9"],
    ),
    EDCIMetric(
        id="EDCI-S3", name="Days Lost Due to Injury", category="social",
        description="Days lost due to work-related injury.",
        unit="days",
        data_points=["Days lost due to injury"],
        gri_cross_refs=["403-9"],
    ),
    # Diversity
    EDCIMetric(
        id="EDCI-S4", name="Women on Board", category="social",
        description="Percentage of board members who are women.",
        unit="%",
        data_points=["% women on board"],
        iris_cross_refs=["OI1075"],
        gri_cross_refs=["405-1"],
        sfdr_cross_refs=[13],
    ),
    EDCIMetric(
        id="EDCI-S5", name="Under-represented Groups", category="social",
        description="Percentage of board or workforce representation from under-represented groups.",
        unit="%",
        data_points=["% under-represented groups"],
        gri_cross_refs=["405-1"],
        required=False,
    ),
    EDCIMetric(
        id="EDCI-S6", name="Women in C-Suite", category="social",
        description="Percentage of C-suite executives who are women.",
        unit="%",
        data_points=["% women in C-suite"],
        iris_cross_refs=["OI1571"],
        gri_cross_refs=["405-1"],
    ),
    # Net new hires
    EDCIMetric(
        id="EDCI-S7", name="Net New Hires", category="social",
        description="Net new hires, including organic and total net new hires.",
        unit="count",
        data_points=["Net new hires (organic and total)"],
        gri_cross_refs=["401-1"],
    ),
    EDCIMetric(
        id="EDCI-S8", name="Employee Turnover", category="social",
        description="Employee turnover.",
        unit="%",
        data_points=["Turnover"],
        gri_cross_refs=["401-1"],
    ),
    # Employee engagement
    EDCIMetric(
        id="EDCI-S9", name="Employee Survey", category="social",
        description="Whether an employee survey was conducted.",
        unit="Yes/No",
        data_points=["Employee survey"],
    ),
    EDCIMetric(
        id="EDCI-S10", name="Employee Survey Response", category="social",
        description="Employee survey response rate.",
        unit="%",
        data_points=["Employee survey response"],
        required=False,
    ),
    EDCIMetric(
        id="EDCI-S11", name="Employee Satisfaction", category="social",
        description="Employee satisfaction score from survey data.",
        unit="score",
        data_points=["Employee satisfaction"],
        required=False,
    ),
    # Cybersecurity
    EDCIMetric(
        id="EDCI-G1", name="Cybersecurity Testing", category="governance",
        description=(
            "Non-core 2026 KPI: cybersecurity testing conducted as part of a proactive "
            "vulnerability management program."
        ),
        unit="multi-select",
        data_points=["Cybersecurity testing"],
        gri_cross_refs=["418-1"],
        required=False,
    ),
]


def get_edci_metrics(
    category: str | None = None,
    *,
    required_only: bool = False,
) -> list[EDCIMetric]:
    metrics = EDCI_METRICS
    if category:
        metrics = [m for m in metrics if m.category == category]
    if required_only:
        metrics = [m for m in metrics if m.required]
    return metrics


def edci_core_iris_metric_ids() -> list[str]:
    """IRIS+ metric IDs cross-referenced by the core EDCI metric set.

    The EDCI set is the LP-side automation anchor (ILPA guidance), so
    collection flows that speak IRIS+ can scaffold their questionnaires from
    these equivalents to serve LP reports, benchmarking, and DDQs at once.
    """
    ids: list[str] = []
    for metric in EDCI_METRICS:
        if not metric.required:
            continue
        for ref in metric.iris_cross_refs:
            if ref not in ids:
                ids.append(ref)
    return ids


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
            {
                "total": 0,
                "required": 0,
                "optional": 0,
                "available": 0,
                "proxy": 0,
                "missing": 0,
                "not_applicable": 0,
                "completeness_pct": 0.0,
                "required_completeness_pct": 0.0,
            },
        )
        cat["total"] = int(cat["total"]) + 1
        requirement_key = "required" if row.required else "optional"
        cat[requirement_key] = int(cat[requirement_key]) + 1
        cat[row.status] = int(cat[row.status]) + 1
    for category, cat in by_category.items():
        complete = int(cat["available"]) + int(cat["proxy"]) + int(cat["not_applicable"])
        cat["completeness_pct"] = (
            round(complete / int(cat["total"]) * 100, 1) if cat["total"] else 0.0
        )
        required_rows = [row for row in rows if row.category == category and row.required]
        required_total = int(cat["required"])
        required_complete = sum(
            1 for row in required_rows if row.status in {"available", "proxy", "not_applicable"}
        )
        cat["required_completeness_pct"] = (
            round(required_complete / required_total * 100, 1) if required_total else 100.0
        )

    total = len(rows)
    complete_count = counts["available"] + counts["proxy"] + counts["not_applicable"]
    required_rows = [row for row in rows if row.required]
    required_complete = sum(
        1 for row in required_rows if row.status in {"available", "proxy", "not_applicable"}
    )
    return EDCICompletenessReport(
        scope=scope,
        company_count=company_count,
        rows=rows,
        total_fields=total,
        required_fields=len(required_rows),
        optional_fields=total - len(required_rows),
        available=counts["available"],
        proxy=counts["proxy"],
        missing=counts["missing"],
        not_applicable=counts["not_applicable"],
        required_complete=required_complete,
        required_missing=sum(1 for row in required_rows if row.status == "missing"),
        required_completeness_pct=round(required_complete / len(required_rows) * 100, 1) if required_rows else 0.0,
        by_category=by_category,
        completeness_pct=round(complete_count / total * 100, 1) if total else 0.0,
        reporting_cycle=EDCI_REPORTING_CYCLE,
        metric_set_note=EDCI_METRIC_SET_NOTE,
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
            required=metric.required,
            reporting_cycle=metric.reporting_cycle,
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
    reported = {str(k).strip().upper(): str(v) for k, v in (reported_data or {}).items()}

    metric_keywords = {
        "EDCI-E1": ["scope 1", "direct emission", "ghg scope 1"],
        "EDCI-E2": ["scope 2", "indirect emission", "electricity emission"],
        "EDCI-E3": ["scope 3", "value chain emission"],
        "EDCI-E4": ["decarbonization strategy", "decarbonisation strategy"],
        "EDCI-E5": ["decarbonization target", "emissions reduction target"],
        "EDCI-E6": ["net zero", "net-zero", "carbon neutral", "decarbonization ambition"],
        "EDCI-E7": ["renewable energy", "clean energy"],
        "EDCI-S1": ["work-related injur", "workplace injur"],
        "EDCI-S2": ["fatalit", "work-related death"],
        "EDCI-S3": ["days lost due to injury", "lost time injury"],
        "EDCI-S4": ["women on board", "female board", "board gender"],
        "EDCI-S5": ["under-represented", "underrepresented"],
        "EDCI-S6": ["women in c-suite", "female c-suite", "female executive"],
        "EDCI-S7": ["net new hires", "new hires"],
        "EDCI-S8": ["employee turnover", "attrition rate"],
        "EDCI-S9": ["employee survey"],
        "EDCI-S10": ["employee survey response", "survey response rate"],
        "EDCI-S11": ["employee satisfaction", "engagement score"],
        "EDCI-G1": [
            "cybersecurity testing",
            "vulnerability scan",
            "penetration testing",
            "software development lifecycle security testing",
            "security testing",
        ],
    }

    result = {
        "framework": "EDCI 2026 private-markets KPI set",
        "metric_set_note": EDCI_METRIC_SET_NOTE,
        "reporting_cycle": EDCI_REPORTING_CYCLE,
        "metrics": [],
        "total": len(EDCI_METRICS),
        "required_total": sum(1 for metric in EDCI_METRICS if metric.required),
        "addressed": 0,
        "required_addressed": 0,
        "by_category": {
            "environment": {"total": 0, "required_total": 0, "addressed": 0, "required_addressed": 0},
            "social": {"total": 0, "required_total": 0, "addressed": 0, "required_addressed": 0},
            "governance": {"total": 0, "required_total": 0, "addressed": 0, "required_addressed": 0},
        },
    }

    for metric in EDCI_METRICS:
        addressed = False
        evidence_status: Literal["available", "proxy", "heuristic", "missing"] = "missing"
        evidence: list[str] = []
        heuristic_mentions: list[str] = []

        kws = metric_keywords.get(metric.id, [])
        hits = [kw for kw in kws if kw.lower() in text]
        if hits:
            heuristic_mentions.extend(hits)

        if metric.id in reported:
            addressed = True
            evidence_status = "available"
            evidence.append(f"{metric.id} reported")

        if metric.iris_cross_refs:
            for ref in metric.iris_cross_refs:
                if ref.upper() in reported:
                    addressed = True
                    if evidence_status != "available":
                        evidence_status = "proxy"
                    evidence.append(f"IRIS+ {ref} proxy")

        m_result = {
            "id": metric.id,
            "name": metric.name,
            "category": metric.category,
            "required": metric.required,
            "reporting_cycle": metric.reporting_cycle,
            "evidence_status": evidence_status if addressed else ("heuristic" if hits else "missing"),
            "addressed": addressed,
            "evidence": evidence,
            "heuristic_mentions": heuristic_mentions,
            "data_points_needed": metric.data_points if not addressed else [],
            "cross_references": {
                "iris": metric.iris_cross_refs,
                "gri": metric.gri_cross_refs,
                "sfdr_pai": metric.sfdr_cross_refs,
            },
        }
        result["metrics"].append(m_result)

        cat = result["by_category"][metric.category]
        cat["total"] += 1
        if metric.required:
            cat["required_total"] += 1
        if addressed:
            result["addressed"] += 1
            cat["addressed"] += 1
            if metric.required:
                result["required_addressed"] += 1
                cat["required_addressed"] += 1

    result["coverage_pct"] = round(result["addressed"] / result["total"] * 100, 1)
    result["required_coverage_pct"] = round(result["required_addressed"] / result["required_total"] * 100, 1)
    for cat_data in result["by_category"].values():
        cat_data["coverage_pct"] = round(cat_data["addressed"] / cat_data["total"] * 100, 1) if cat_data["total"] > 0 else 0
        cat_data["required_coverage_pct"] = (
            round(cat_data["required_addressed"] / cat_data["required_total"] * 100, 1)
            if cat_data["required_total"] > 0 else 100.0
        )

    return result
