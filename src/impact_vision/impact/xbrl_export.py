"""Lightweight iXBRL and xBRL-JSON export with MetricRecord provenance.

This is a **tagging prototype** for CSRD digital-tagging / ISSB taxonomy
alignment. It emits Inline XBRL 1.1 facts, contexts, and units against
screening qnames from the concordance map. It is **not** an Arelle-validated
EFRAG ESRS or IFRS ISSB filing — schemaRef URIs are labelled as screening.
"""

from __future__ import annotations

import html as html_lib
import re
from typing import Literal

from pydantic import BaseModel

from impact_vision.impact.concordance import ConcordanceMap
from impact_vision.impact.models import MetricRecord

ESRS_SCHEMA_REF = (
    "https://www.efrag.org/sites/default/files/xbrl/esrs/screening/esrs-set1.xsd"
)
ISSB_SCHEMA_REF = "https://www.ifrs.org/content/dam/ifrs/xbrl/issb/screening/ifrs-s2.xsd"


class XBRLTag(BaseModel):
    element: str
    taxonomy: Literal["esrs_set1", "issb"]
    context_ref: str
    unit_ref: str | None
    value: str
    decimals: str = "0"
    metric_record_id: str
    period: str = ""
    unit: str = ""


def build_context(entity_id: str, period: str) -> dict:
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", entity_id)
    return {
        "id": f"ctx-{safe}-{period}",
        "entity_id": entity_id,
        "period": period,
        "schema_ref": ESRS_SCHEMA_REF,
    }


def _unit_id(unit: str | None) -> str:
    raw = (unit or "pure").strip()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", raw) or "pure"
    return slug[:32]


def tag_records(
    records: list[MetricRecord],
    taxonomy: str,
    concordance: ConcordanceMap,
) -> tuple[list[XBRLTag], list[dict]]:
    framework = "esrs" if taxonomy == "esrs_set1" else "issb"
    tags: list[XBRLTag] = []
    untaggable: list[dict] = []
    for index, record in enumerate(records):
        if not record.unit or not record.period:
            untaggable.append({"metric_id": record.metric_id, "reason": "missing unit or period"})
            continue
        translated = concordance.translate(record, framework)
        refs = [ref for ref, _ in translated if ref.taxonomy_uri]
        if not refs:
            untaggable.append(
                {"metric_id": record.metric_id, "reason": "no taxonomy_uri in concordance"}
            )
            continue
        for ref in refs:
            tags.append(
                XBRLTag(
                    element=ref.taxonomy_uri or "",
                    taxonomy=taxonomy,  # type: ignore[arg-type]
                    context_ref=f"ctx-{record.period}",
                    unit_ref=_unit_id(record.unit),
                    value=str(record.value),
                    metric_record_id=f"{record.metric_id}:{index}",
                    period=record.period,
                    unit=record.unit,
                )
            )
    return tags, untaggable


def _ix_header(tags: list[XBRLTag], entity_id: str, period: str, taxonomy: str) -> str:
    context = build_context(entity_id, period)
    schema = ESRS_SCHEMA_REF if taxonomy == "esrs_set1" else ISSB_SCHEMA_REF
    units = []
    seen_units: set[str] = set()
    for tag in tags:
        uid = tag.unit_ref or "pure"
        if uid in seen_units:
            continue
        seen_units.add(uid)
        measure = "xbrli:pure" if uid == "pure" else f"iso4217:{uid}" if uid.upper() in {
            "USD",
            "EUR",
            "GBP",
        } else f"utr:{uid}"
        units.append(f'<xbrli:unit id="{html_lib.escape(uid)}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>')
    return (
        "<ix:header><ix:references>"
        f'<link:schemaRef xlink:type="simple" xlink:href="{html_lib.escape(schema)}"/>'
        "</ix:references><ix:resources>"
        f'<xbrli:context id="{context["id"]}"><xbrli:entity><xbrli:identifier '
        f'scheme="https://impact.vision/entity">{html_lib.escape(entity_id)}</xbrli:identifier>'
        f"</xbrli:entity><xbrli:period><xbrli:instant>{html_lib.escape(period)}</xbrli:instant>"
        f"</xbrli:period></xbrli:context>{''.join(units)}</ix:resources></ix:header>"
    )


def render_ixbrl(
    html: str,
    tags: list[XBRLTag],
    entity_id: str,
    period: str,
    taxonomy: str = "esrs_set1",
) -> str:
    context = build_context(entity_id, period)
    facts = "".join(
        f'<ix:nonFraction name="{html_lib.escape(tag.element)}" contextRef="{context["id"]}" '
        f'unitRef="{html_lib.escape(tag.unit_ref or "pure")}" decimals="{tag.decimals}" '
        f'format="ixt:num-dot-decimal" '
        f'data-metric-record-id="{html_lib.escape(tag.metric_record_id)}">'
        f"{html_lib.escape(tag.value)}</ix:nonFraction>"
        for tag in tags
    )
    header = _ix_header(tags, entity_id, period, taxonomy)
    namespace = (
        ' xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"'
        ' xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"'
        ' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        ' xmlns:link="http://www.xbrl.org/2003/linkbase"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        ' xmlns:esrs="https://xbrl.efrag.org/taxonomy/esrs/screening"'
        ' xmlns:issb="https://xbrl.ifrs.org/taxonomy/issb/screening"'
    )
    if "<html" in html.lower():
        out = re.sub(r"<html([^>]*)>", rf"<html\1{namespace}>", html, count=1, flags=re.I)
        return re.sub(r"<body([^>]*)>", rf"<body\1>{header}{facts}", out, count=1, flags=re.I)
    return f"<html{namespace}><body>{header}{facts}{html}</body></html>"


def render_xbrl_json(
    tags: list[XBRLTag], entity_id: str, period: str, taxonomy: str = "esrs_set1"
) -> dict:
    schema = ESRS_SCHEMA_REF if taxonomy == "esrs_set1" else ISSB_SCHEMA_REF
    return {
        "documentInfo": {
            "documentType": "https://xbrl.org/2021/xbrl-json",
            "entity": entity_id,
            "period": period,
            "taxonomy": taxonomy,
            "schemaRef": schema,
            "status": "screening_prototype",
            "note": "Not an Arelle-validated CSRD/ISSB filing.",
        },
        "facts": {
            f"f{i}": {
                "concept": tag.element,
                "value": tag.value,
                "decimals": tag.decimals,
                "dimensions": {
                    "entity": entity_id,
                    "period": tag.period or period,
                    "unit": tag.unit_ref,
                },
                "metric_record_id": tag.metric_record_id,
            }
            for i, tag in enumerate(tags, 1)
        },
    }


__all__ = [
    "ESRS_SCHEMA_REF",
    "ISSB_SCHEMA_REF",
    "XBRLTag",
    "build_context",
    "render_ixbrl",
    "render_xbrl_json",
    "tag_records",
]
