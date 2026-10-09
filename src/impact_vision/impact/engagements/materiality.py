"""Scored double-materiality wizard with explicit union rule."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, computed_field


class ImpactMaterialityScore(BaseModel):
    topic_id: str
    scale: int = Field(ge=0, le=5)
    scope: int = Field(ge=0, le=5)
    irremediability: int = Field(ge=0, le=5)
    likelihood: int = Field(ge=0, le=5)

    @computed_field
    @property
    def severity(self) -> float:
        return round((self.scale + self.scope + self.irremediability) / 3, 3)

    @computed_field
    @property
    def normalized_score(self) -> float:
        return round(self.severity * self.likelihood / 2.5, 3)

    @property
    def impact_material(self) -> bool:
        return self.normalized_score >= 7.0


class FinancialMaterialityInput(BaseModel):
    topic_id: str
    qualitative_band: Literal["none", "low", "medium", "high"] | None = None
    absolute_amount: float | None = None
    pct_net_profit: float | None = None


class MaterialityConfig(BaseModel):
    impact_threshold_detail: float = 7.0
    impact_threshold_optional: float = 5.0
    financial_abs_bands: list[dict] = Field(
        default_factory=lambda: [{"minimum": 1_000_000, "material": True}]
    )
    financial_pct_bands: list[dict] = Field(
        default_factory=lambda: [{"minimum": 5, "material": True}]
    )


class MaterialityResult(BaseModel):
    topic_id: str
    quadrant: Literal["dual", "financial_only", "impact_only", "neither"]
    disclosure_consequence: str
    scores: dict
    disclose: bool


def assess_materiality(
    topics: list[str], impact_scores, financial_inputs, config: MaterialityConfig | None = None
) -> list[MaterialityResult]:
    cfg = config or MaterialityConfig()
    impacts = {
        item.topic_id: item
        for item in [
            i if isinstance(i, ImpactMaterialityScore) else ImpactMaterialityScore.model_validate(i)
            for i in impact_scores
        ]
    }
    financials = {
        item.topic_id: item
        for item in [
            i
            if isinstance(i, FinancialMaterialityInput)
            else FinancialMaterialityInput.model_validate(i)
            for i in financial_inputs
        ]
    }
    results = []
    for topic in topics:
        impact = impacts.get(topic)
        financial = financials.get(topic)
        impact_value = impact.normalized_score if impact else 0.0
        impact_material = impact_value >= cfg.impact_threshold_detail
        financial_material = bool(
            financial
            and (
                financial.qualitative_band == "high"
                or (financial.pct_net_profit or 0) >= 5
                or (financial.absolute_amount or 0) >= 1_000_000
            )
        )
        quadrant = (
            "dual"
            if impact_material and financial_material
            else "impact_only"
            if impact_material
            else "financial_only"
            if financial_material
            else "neither"
        )
        consequence = (
            "four_pillar_plus_topic"
            if quadrant == "dual"
            else "topic_rules"
            if quadrant != "neither"
            else "explain_omission"
        )
        results.append(
            MaterialityResult(
                topic_id=topic,
                quadrant=quadrant,
                disclosure_consequence=consequence,
                scores={
                    "impact": impact_value,
                    "financial_material": financial_material,
                    "optional_impact": cfg.impact_threshold_optional
                    <= impact_value
                    < cfg.impact_threshold_detail,
                },
                disclose=impact_material or financial_material,
            )
        )
    return results


def materiality_matrix_payload(results) -> dict:
    rows = [
        r if isinstance(r, MaterialityResult) else MaterialityResult.model_validate(r)
        for r in results
    ]
    return {
        "data": [
            {
                "type": "scatter",
                "mode": "markers+text",
                "x": [float(r.scores.get("financial_material", False)) for r in rows],
                "y": [r.scores.get("impact", 0) for r in rows],
                "text": [r.topic_id for r in rows],
            }
        ],
        "layout": {
            "xaxis": {"title": "Financial materiality"},
            "yaxis": {"title": "Impact materiality"},
        },
    }


__all__ = [
    "FinancialMaterialityInput",
    "ImpactMaterialityScore",
    "MaterialityConfig",
    "MaterialityResult",
    "assess_materiality",
    "materiality_matrix_payload",
]
