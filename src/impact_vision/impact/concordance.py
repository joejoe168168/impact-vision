"""Canonical interoperability concordance for impact datapoints."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from impact_vision.impact.models import MetricRecord
from impact_vision.impact._paths import data_path as bundled_data_path

FrameworkName = Literal["iris", "issb", "esrs", "gri", "edci", "sfdr_pai", "sasb", "tcfd"]


class DatapointRef(BaseModel):
    framework: FrameworkName
    datapoint_id: str
    label: str
    unit_hint: str | None = None
    taxonomy_uri: str | None = None


class ConcordanceEntry(BaseModel):
    concept_id: str
    refs: list[DatapointRef]
    match_quality: Literal["exact", "close", "partial"] = "exact"
    notes: str = ""


class ConcordanceMap:
    def __init__(self, entries: list[ConcordanceEntry]):
        self.entries = entries
        self._index = {
            (ref.framework, ref.datapoint_id.lower()): entry
            for entry in entries
            for ref in entry.refs
        }

    def lookup(self, framework: str, datapoint_id: str) -> ConcordanceEntry | None:
        return self._index.get((framework.lower(), datapoint_id.strip().lower()))

    def translate(
        self,
        record: MetricRecord,
        to_framework: str,
        from_framework: str = "iris",
    ) -> list[tuple[DatapointRef, MetricRecord]]:
        entry = self.lookup(from_framework, record.metric_id)
        if not entry:
            return []
        return [
            (ref, record.model_copy(update={"notes": _append_note(record.notes, entry.concept_id)}))
            for ref in entry.refs
            if ref.framework == to_framework
        ]

    def coverage_report(
        self,
        records: list[MetricRecord],
        to_framework: str,
        from_framework: str = "iris",
    ) -> dict:
        covered: list[dict] = []
        partial: list[dict] = []
        mapped_concepts: set[str] = set()
        for record in records:
            entry = self.lookup(from_framework, record.metric_id)
            refs = [] if entry is None else [r for r in entry.refs if r.framework == to_framework]
            if refs and entry:
                row = {
                    "metric_id": record.metric_id,
                    "concept_id": entry.concept_id,
                    "datapoints": [r.model_dump() for r in refs],
                }
                (partial if entry.match_quality == "partial" else covered).append(row)
                mapped_concepts.add(entry.concept_id)
        target_entries = [
            e for e in self.entries if any(r.framework == to_framework for r in e.refs)
        ]
        gaps = [e.concept_id for e in target_entries if e.concept_id not in mapped_concepts]
        denominator = len(target_entries)
        pct = 100.0 * len(mapped_concepts) / denominator if denominator else 0.0
        return {"covered": covered, "gaps": gaps, "coverage_pct": round(pct, 2), "partial": partial}


def _append_note(notes: str, concept_id: str) -> str:
    suffix = f"concordance:{concept_id}"
    return f"{notes}; {suffix}".strip("; ")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _from_legacy() -> list[ConcordanceEntry]:
    from impact_vision.impact.frameworks.cross_reference import CROSS_REFERENCE_MAP

    field_map = {
        "iris": "iris_plus",
        "gri": "gri",
        "edci": "edci",
        "sfdr_pai": "sfdr_pai",
        "sasb": "sasb_codes",
        "tcfd": "tcfd",
        "issb": "issb",
        "esrs": "esrs",
    }
    entries: list[ConcordanceEntry] = []
    canonical_ids = {
        "GHG Emissions - Scope 1 (Direct)": "ghg_scope1_emissions",
    }
    for legacy in CROSS_REFERENCE_MAP:
        refs: list[DatapointRef] = []
        for framework, field in field_map.items():
            for raw_id in getattr(legacy, field):
                datapoint_id = f"PAI-{raw_id}" if framework == "sfdr_pai" else str(raw_id)
                refs.append(
                    DatapointRef(
                        framework=framework,
                        datapoint_id=datapoint_id,
                        label=legacy.concept,
                        taxonomy_uri=_taxonomy_uri(framework, datapoint_id),
                    )
                )
        entries.append(
            ConcordanceEntry(
                concept_id=canonical_ids.get(legacy.concept, _slug(legacy.concept)),
                refs=refs,
                match_quality={"direct": "exact", "partial": "partial"}.get(
                    legacy.mapping_confidence, "close"
                ),
                notes=legacy.notes,
            )
        )
    return entries


def _taxonomy_uri(framework: str, datapoint_id: str) -> str | None:
    known = {
        ("esrs", "E1-6"): "esrs:GrossScope1GHGEmissions",
        ("esrs", "E1-5"): "esrs:EnergyConsumptionAndMix",
        ("esrs", "E1-1"): "esrs:TransitionPlanForClimateChangeMitigation",
        ("esrs", "E1-4"): "esrs:TargetsRelatedToClimateChangeMitigationAndAdaptation",
        ("esrs", "E1-7"): "esrs:GHGRemovalsAndCarbonCredits",
        ("esrs", "S1-6"): "esrs:CharacteristicsOfUndertakingsEmployees",
        ("esrs", "S1-16"): "esrs:GenderPayGap",
        ("issb", "S2-MT-1"): "issb:AbsoluteGrossGreenhouseGasEmissions",
        ("issb", "S2-MT-4"): "issb:ClimateRelatedTargets",
        ("gri", "305-1"): "gri:DirectGHGEmissionsScope1",
        ("gri", "305-2"): "gri:EnergyIndirectGHGEmissionsScope2",
        ("gri", "305-3"): "gri:OtherIndirectGHGEmissionsScope3",
        ("gri", "302-1"): "gri:EnergyConsumptionWithinTheOrganization",
        ("gri", "303-5"): "gri:WaterConsumption",
        ("gri", "405-1"): "gri:DiversityOfGovernanceBodiesAndEmployees",
    }
    hit = known.get((framework, datapoint_id))
    if hit:
        return hit
    slug = re.sub(r"[^A-Za-z0-9]", "", datapoint_id)
    if not slug:
        return None
    if framework == "esrs":
        return f"esrs:{slug}"
    if framework == "issb":
        return f"issb:{slug}"
    if framework == "gri":
        return f"gri:{slug}"
    return None


def load_concordance(path: str | Path | None = None) -> ConcordanceMap:
    entries = _from_legacy()
    data_path = (
        Path(path) if path else bundled_data_path("concordance.yaml")
    )
    if data_path.exists():
        payload = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
        extra = [ConcordanceEntry.model_validate(item) for item in payload.get("entries", [])]
        by_id = {entry.concept_id: entry for entry in entries}
        for entry in extra:
            existing = by_id.get(entry.concept_id)
            if existing is None:
                by_id[entry.concept_id] = entry
                continue
            # Canonical extensions should enrich the legacy map, not silently
            # replace its EDCI/SFDR/SASB/TCFD references.  This matters for the
            # two seeded v6 concepts, where the YAML intentionally adds units
            # and taxonomy tags but does not repeat all 59 legacy refs.
            refs_by_key = {
                (ref.framework, ref.datapoint_id.lower()): ref for ref in existing.refs
            }
            for ref in entry.refs:
                key = (ref.framework, ref.datapoint_id.lower())
                if key in refs_by_key:
                    refs_by_key[key] = refs_by_key[key].model_copy(
                        update={
                            "label": ref.label or refs_by_key[key].label,
                            "unit_hint": ref.unit_hint or refs_by_key[key].unit_hint,
                            "taxonomy_uri": ref.taxonomy_uri or refs_by_key[key].taxonomy_uri,
                        }
                    )
                else:
                    refs_by_key[key] = ref
            by_id[entry.concept_id] = existing.model_copy(
                update={
                    "refs": list(refs_by_key.values()),
                    "match_quality": entry.match_quality,
                    "notes": "; ".join(filter(None, [existing.notes, entry.notes])),
                }
            )
        entries = list(by_id.values())
    return ConcordanceMap(entries)


__all__ = ["ConcordanceEntry", "ConcordanceMap", "DatapointRef", "load_concordance"]
