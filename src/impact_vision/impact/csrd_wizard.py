"""CSRD / ESRS double-materiality wizard (Phase 17).

Guides a preparer through the European Sustainability Reporting
Standards double-materiality assessment (financial materiality +
impact materiality) and produces the matrix + ESRS topic shortlist
needed by ESRS 1 / ESRS 2.

Inputs
------
Each topic is scored on two 1-5 scales:

* **Impact materiality** — severity, scale, scope, irreversibility,
  likelihood (outward — the company's effect on people / planet).
* **Financial materiality** — probability and magnitude of financial
  effect on the company (inward).

A topic is *material* when ``max(impact, financial) >= threshold``.
The default threshold is 3.5 on the 5-point scale, matching EFRAG's
guidance for "likely material" in the ESRS 1 impl-guide.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ESRSTopic = Literal[
    "E1-climate",
    "E2-pollution",
    "E3-water",
    "E4-biodiversity",
    "E5-circular-economy",
    "S1-own-workforce",
    "S2-value-chain-workers",
    "S3-affected-communities",
    "S4-consumers-end-users",
    "G1-business-conduct",
]


class MaterialityScore(BaseModel):
    """Score for one ESRS topic."""

    topic: ESRSTopic
    impact_materiality: float = Field(ge=0, le=5)
    financial_materiality: float = Field(ge=0, le=5)
    rationale_impact: str = ""
    rationale_financial: str = ""
    stakeholder_input: list[str] = Field(default_factory=list)


class MaterialityMatrix(BaseModel):
    """Full double-materiality output."""

    entity: str
    reporting_period: str
    threshold: float = 3.5
    scores: list[MaterialityScore] = Field(default_factory=list)
    material_topics: list[ESRSTopic] = Field(default_factory=list)
    shortlist_esrs_sections: list[str] = Field(default_factory=list)


_ESRS_TO_STANDARD = {
    "E1-climate": "ESRS E1",
    "E2-pollution": "ESRS E2",
    "E3-water": "ESRS E3",
    "E4-biodiversity": "ESRS E4",
    "E5-circular-economy": "ESRS E5",
    "S1-own-workforce": "ESRS S1",
    "S2-value-chain-workers": "ESRS S2",
    "S3-affected-communities": "ESRS S3",
    "S4-consumers-end-users": "ESRS S4",
    "G1-business-conduct": "ESRS G1",
}


def assess_double_materiality(
    *,
    entity: str,
    reporting_period: str,
    scores: list[MaterialityScore],
    threshold: float = 3.5,
) -> MaterialityMatrix:
    """Return a :class:`MaterialityMatrix` populated with material topics."""
    matrix = MaterialityMatrix(
        entity=entity,
        reporting_period=reporting_period,
        threshold=threshold,
        scores=list(scores),
    )
    material: list[ESRSTopic] = []
    for s in scores:
        if max(s.impact_materiality, s.financial_materiality) >= threshold:
            material.append(s.topic)
    matrix.material_topics = material
    matrix.shortlist_esrs_sections = [_ESRS_TO_STANDARD[t] for t in material]
    return matrix


__all__ = [
    "ESRSTopic",
    "MaterialityScore",
    "MaterialityMatrix",
    "assess_double_materiality",
]
