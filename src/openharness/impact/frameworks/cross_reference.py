"""Cross-reference mapping between sustainability frameworks.

Maps equivalent metrics/disclosures across IRIS+, GRI, EDCI, SFDR PAI, and SASB.
Enables lookup in any direction: given a metric in one standard, find equivalents in others.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CrossReference(BaseModel):
    """A mapping between equivalent metrics across standards.

    For SASB, both `sasb_dimension` (the broad pillar) and `sasb_codes` (the
    actual SASB metric codes, e.g. `FN-CB-230a.1`) are stored so reverse-lookup
    by SASB metric code works.
    """
    concept: str
    iris_plus: list[str] = Field(default_factory=list)
    gri: list[str] = Field(default_factory=list)
    edci: list[str] = Field(default_factory=list)
    sfdr_pai: list[int] = Field(default_factory=list)
    sasb_dimension: str = ""
    sasb_codes: list[str] = Field(default_factory=list)
    tnfd: list[str] = Field(default_factory=list)
    pcaf: list[str] = Field(default_factory=list)
    eu_taxonomy: list[str] = Field(default_factory=list)
    cdp: list[str] = Field(default_factory=list)
    sbti: list[str] = Field(default_factory=list)
    tcfd: list[str] = Field(default_factory=list)
    issb: list[str] = Field(default_factory=list)
    esrs: list[str] = Field(default_factory=list)
    sdg_goals: list[int] = Field(default_factory=list)
    mapping_confidence: Literal["direct", "partial", "proxy", "conceptual"] = "direct"
    mapping_basis: Literal["metric", "disclosure", "conceptual", "proxy"] = "conceptual"
    confidence: Literal["high", "medium", "low"] = "medium"
    source_url: str = ""
    notes: str = ""


def _load_crosswalk() -> list[CrossReference]:
    """The concept crosswalk, stored in ``data/concordance.yaml`` under ``crosswalk`` (W5.1)."""
    from openharness.impact.knowledge import load_knowledge

    return [CrossReference.model_validate(row) for row in load_knowledge("concordance.yaml").get("crosswalk", [])]


CROSS_REFERENCE_MAP: list[CrossReference] = _load_crosswalk()

# Build reverse-lookup indexes
_iris_index: dict[str, list[CrossReference]] = {}
_gri_index: dict[str, list[CrossReference]] = {}
_edci_index: dict[str, list[CrossReference]] = {}
_sfdr_index: dict[int, list[CrossReference]] = {}
_sasb_index: dict[str, list[CrossReference]] = {}
_tnfd_index: dict[str, list[CrossReference]] = {}
_pcaf_index: dict[str, list[CrossReference]] = {}
_eutax_index: dict[str, list[CrossReference]] = {}
_cdp_index: dict[str, list[CrossReference]] = {}
_sbti_index: dict[str, list[CrossReference]] = {}
_issb_index: dict[str, list[CrossReference]] = {}
_esrs_index: dict[str, list[CrossReference]] = {}
_concept_index: dict[str, CrossReference] = {}

for _xref in CROSS_REFERENCE_MAP:
    _concept_index[_xref.concept.lower()] = _xref
    for _id in _xref.iris_plus:
        _iris_index.setdefault(_id, []).append(_xref)
    for _id in _xref.gri:
        _gri_index.setdefault(_id, []).append(_xref)
    for _id in _xref.edci:
        _edci_index.setdefault(_id, []).append(_xref)
    for _num in _xref.sfdr_pai:
        _sfdr_index.setdefault(_num, []).append(_xref)
    for _id in _xref.sasb_codes:
        _sasb_index.setdefault(_id.upper(), []).append(_xref)
    for _id in _xref.tnfd:
        _tnfd_index.setdefault(_id, []).append(_xref)
    for _id in _xref.pcaf:
        _pcaf_index.setdefault(_id, []).append(_xref)
    for _id in _xref.eu_taxonomy:
        _eutax_index.setdefault(_id, []).append(_xref)
    for _id in _xref.cdp:
        _cdp_index.setdefault(_id, []).append(_xref)
    for _id in _xref.sbti:
        _sbti_index.setdefault(_id, []).append(_xref)
    for _id in _xref.issb:
        _issb_index.setdefault(_id, []).append(_xref)
    for _id in _xref.esrs:
        _esrs_index.setdefault(_id, []).append(_xref)


def lookup_by_iris(metric_id: str) -> list[CrossReference]:
    return _iris_index.get(metric_id, [])


def lookup_by_gri(disclosure_code: str) -> list[CrossReference]:
    return _gri_index.get(disclosure_code, [])


def lookup_by_edci(metric_id: str) -> list[CrossReference]:
    return _edci_index.get(metric_id, [])


def lookup_by_sfdr(indicator_number: int) -> list[CrossReference]:
    return _sfdr_index.get(indicator_number, [])


def lookup_by_sasb(code: str) -> list[CrossReference]:
    """Lookup by a specific SASB metric code (e.g. 'FN-CB-230a.1')."""
    return _sasb_index.get(code.upper(), [])


def lookup_by_tnfd(code: str) -> list[CrossReference]:
    return _tnfd_index.get(code, [])


def lookup_by_pcaf(code: str) -> list[CrossReference]:
    return _pcaf_index.get(code, [])


def lookup_by_eu_taxonomy(code: str) -> list[CrossReference]:
    return _eutax_index.get(code, [])


def lookup_by_cdp(code: str) -> list[CrossReference]:
    return _cdp_index.get(code, [])


def lookup_by_sbti(code: str) -> list[CrossReference]:
    return _sbti_index.get(code, [])


def lookup_by_issb(code: str) -> list[CrossReference]:
    return _issb_index.get(code, [])


def lookup_by_esrs(code: str) -> list[CrossReference]:
    return _esrs_index.get(code, [])


def search_cross_references(query: str) -> list[CrossReference]:
    """Search cross-references by concept name."""
    q = query.lower()
    return [xref for xref in CROSS_REFERENCE_MAP if q in xref.concept.lower()]


def get_all_cross_references() -> list[CrossReference]:
    return CROSS_REFERENCE_MAP


def format_cross_reference(xref: CrossReference) -> str:
    """Format a cross-reference for display."""
    parts = [f"[{xref.concept}]"]
    if xref.mapping_confidence != "direct":
        parts.append(f"  Mapping confidence: {xref.mapping_confidence}")
    if xref.iris_plus:
        parts.append(f"  IRIS+: {', '.join(xref.iris_plus)}")
    if xref.gri:
        parts.append(f"  GRI: {', '.join(xref.gri)}")
    if xref.edci:
        parts.append(f"  EDCI: {', '.join(xref.edci)}")
    if xref.sfdr_pai:
        parts.append(f"  SFDR PAI: {', '.join(f'#{n}' for n in xref.sfdr_pai)}")
    if xref.tcfd:
        parts.append(f"  TCFD: {', '.join(xref.tcfd)}")
    if xref.issb:
        parts.append(f"  ISSB: {', '.join(xref.issb)}")
    if xref.esrs:
        parts.append(f"  ESRS: {', '.join(xref.esrs)}")
    if xref.sasb_dimension or xref.sasb_codes:
        sasb_parts = []
        if xref.sasb_dimension:
            sasb_parts.append(xref.sasb_dimension)
        if xref.sasb_codes:
            sasb_parts.append(", ".join(xref.sasb_codes))
        parts.append(f"  SASB: {' / '.join(sasb_parts)}")
    if xref.tnfd:
        parts.append(f"  TNFD: {', '.join(xref.tnfd)}")
    if xref.pcaf:
        parts.append(f"  PCAF: {', '.join(xref.pcaf)}")
    if xref.eu_taxonomy:
        parts.append(f"  EU Taxonomy: {', '.join(xref.eu_taxonomy)}")
    if xref.cdp:
        parts.append(f"  CDP: {', '.join(xref.cdp)}")
    if xref.sbti:
        parts.append(f"  SBTi: {', '.join(xref.sbti)}")
    if xref.sdg_goals:
        parts.append(f"  SDGs: {', '.join(f'{g}' for g in xref.sdg_goals)}")
    if xref.notes:
        parts.append(f"  Notes: {xref.notes}")
    return "\n".join(parts)
