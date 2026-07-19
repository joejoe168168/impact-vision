"""Common Impact Data Standard v3.2 Basic-tier JSON-LD export."""

from __future__ import annotations
from pathlib import Path
import yaml
from openharness.impact.models import Company, ImpactTarget, MetricRecord

CIDS_CONTEXT = {
    "cids": "https://ontology.commonapproach.org/cids#",
    "@vocab": "https://ontology.commonapproach.org/cids#",
    "value": "cids:hasValue",
    "unit": "cids:hasUnit",
}


def _units():
    return (
        yaml.safe_load(
            (Path(__file__).resolve().parents[3] / "data/cids_unit_map.yaml").read_text(
                encoding="utf-8"
            )
        )
        or {}
    ).get("units", {})


def export_cids(
    company: Company, toc: dict | None, records: list[MetricRecord], targets: list[ImpactTarget]
) -> dict:
    units = _units()
    graph = [
        {
            "@id": f"org:{company.name}",
            "@type": "cids:Organization",
            "cids:name": company.name,
            "cids:locatedIn": company.geography,
        }
    ]
    outcomes = [] if toc is None else toc.get("outcomes", [])
    graph.extend(
        {
            "@id": f"outcome:{i}",
            "@type": "cids:Outcome",
            "cids:name": str(item.get("label", item) if isinstance(item, dict) else item),
        }
        for i, item in enumerate(outcomes, 1)
    )
    for i, record in enumerate(records, 1):
        unit_uri = units.get(record.unit)
        indicator = f"indicator:{record.metric_id}"
        graph.append(
            {
                "@id": indicator,
                "@type": "cids:Indicator",
                "cids:identifier": record.metric_id,
                "cids:unit": unit_uri or record.unit,
                "cids:unmapped_unit": unit_uri is None,
            }
        )
        graph.append(
            {
                "@id": f"report:{i}",
                "@type": "cids:IndicatorReport",
                "cids:forIndicator": {"@id": indicator},
                "cids:value": record.value,
                "cids:period": record.period,
                "cids:evidence": record.evidence_refs,
            }
        )
    graph.extend(
        {
            "@id": f"target:{i}",
            "@type": "cids:ImpactTarget",
            "cids:forIndicator": target.metric_id,
            "cids:value": target.target_value,
            "cids:period": target.target_date,
        }
        for i, target in enumerate(targets, 1)
    )
    graph.append(
        {
            "@id": f"impact-model:{company.name}",
            "@type": "cids:ImpactModel",
            "cids:organization": {"@id": f"org:{company.name}"},
            "cids:outcomes": [{"@id": f"outcome:{i}"} for i in range(1, len(outcomes) + 1)],
        }
    )
    return {
        "@context": CIDS_CONTEXT,
        "@graph": graph,
        "cids:conformanceTier": "basic",
        "cids:version": "3.2",
    }


def validate_cids(doc: dict) -> list[str]:
    errors = []
    if doc.get("@context") != CIDS_CONTEXT:
        errors.append("@context must be pinned to CIDS v3.2")
    if not isinstance(doc.get("@graph"), list):
        errors.append("@graph must be a list")
    types = {row.get("@type") for row in doc.get("@graph", []) if isinstance(row, dict)}
    if "cids:Organization" not in types:
        errors.append("missing cids:Organization")
    if "cids:IndicatorReport" in types and "cids:Indicator" not in types:
        errors.append("indicator report without indicator")
    return errors


__all__ = ["CIDS_CONTEXT", "export_cids", "validate_cids"]
