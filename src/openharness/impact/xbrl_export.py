"""Lightweight iXBRL and xBRL-JSON export with MetricRecord provenance."""

from __future__ import annotations

import html as html_lib
import re
from typing import Literal

from pydantic import BaseModel

from openharness.impact.concordance import ConcordanceMap
from openharness.impact.models import MetricRecord


class XBRLTag(BaseModel):
    element: str
    taxonomy: Literal["esrs_set1", "issb"]
    context_ref: str
    unit_ref: str | None
    value: str
    decimals: str = "0"
    metric_record_id: str


def build_context(entity_id: str, period: str) -> dict:
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", entity_id)
    return {"id": f"ctx-{safe}-{period}", "entity_id": entity_id, "period": period}


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
                    taxonomy=taxonomy,
                    context_ref=f"ctx-{record.period}",
                    unit_ref=record.unit,
                    value=str(record.value),
                    metric_record_id=f"{record.metric_id}:{index}",
                )
            )
    return tags, untaggable


def render_ixbrl(html: str, tags: list[XBRLTag], entity_id: str, period: str) -> str:
    context = build_context(entity_id, period)
    facts = "".join(
        f'<ix:nonFraction name="{html_lib.escape(tag.element)}" contextRef="{context["id"]}" '
        f'unitRef="{html_lib.escape(tag.unit_ref or "pure")}" decimals="{tag.decimals}" '
        f'data-metric-record-id="{html_lib.escape(tag.metric_record_id)}">'
        f"{html_lib.escape(tag.value)}</ix:nonFraction>"
        for tag in tags
    )
    header = (
        "<ix:header><ix:resources>"
        f'<xbrli:context id="{context["id"]}"><xbrli:entity><xbrli:identifier '
        f'scheme="https://impact.vision/entity">{html_lib.escape(entity_id)}</xbrli:identifier>'
        f"</xbrli:entity><xbrli:period><xbrli:instant>{html_lib.escape(period)}</xbrli:instant>"
        "</xbrli:period></xbrli:context></ix:resources></ix:header>"
    )
    namespace = (
        ' xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"'
        ' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
    )
    if "<html" in html.lower():
        out = re.sub(r"<html([^>]*)>", rf"<html\1{namespace}>", html, count=1, flags=re.I)
        return re.sub(r"<body([^>]*)>", rf"<body\1>{header}{facts}", out, count=1, flags=re.I)
    return f"<html{namespace}><body>{header}{facts}{html}</body></html>"


def render_xbrl_json(tags: list[XBRLTag], entity_id: str, period: str) -> dict:
    return {
        "documentInfo": {
            "documentType": "https://xbrl.org/2021/xbrl-json",
            "entity": entity_id,
            "period": period,
        },
        "facts": {
            f"f{i}": {
                "concept": tag.element,
                "value": tag.value,
                "dimensions": {"entity": entity_id, "period": period, "unit": tag.unit_ref},
                "metric_record_id": tag.metric_record_id,
            }
            for i, tag in enumerate(tags, 1)
        },
    }


__all__ = ["XBRLTag", "build_context", "render_ixbrl", "render_xbrl_json", "tag_records"]
