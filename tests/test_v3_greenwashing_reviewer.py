"""Tests for v3 explainable greenwashing reviewer."""

from __future__ import annotations

from openharness.impact.greenwashing_reviewer import review_company_claims
from openharness.impact.models import Company, ImpactClaim


def _company() -> Company:
    return Company(
        name="GreenCo",
        description="We are committed to a sustainable, eco-friendly future.",
        sector="energy",
        impact_themes=["Climate Mitigation"],
        sdg_claims=[7, 13],
    )


def test_buzzword_only_claim_is_high_severity_and_vague() -> None:
    claim = ImpactClaim(text="Sustainable, eco-friendly, ESG", evidence_strength=1)
    output = review_company_claims(_company(), [claim])
    assert output.items
    item = output.items[0]
    assert item.specificity == "buzzword_only"
    assert item.severity in {"high", "medium"}
    assert item.evidence_gap is True
    assert item.suggested_followup


def test_concrete_quantitative_claim_is_low_severity() -> None:
    claim = ImpactClaim(
        text="Reduced 1200 tCO2e in 2025 across the pilot programme",
        evidence_strength=4,
        mapped_metrics=["OI4112"],
    )
    output = review_company_claims(_company(), [claim])
    item = output.items[0]
    assert item.specificity == "concrete"
    assert item.severity == "low"
    assert item.evidence_gap is False


def test_quantified_claim_without_metric_mapping_is_still_evidence_gap() -> None:
    claim = ImpactClaim(
        text="Reduced 1200 tCO2e/year across the pilot programme",
        evidence_strength=3,
        mapped_metrics=[],
    )
    output = review_company_claims(_company(), [claim])
    item = output.items[0]
    assert item.specificity == "concrete"
    assert item.evidence_gap is True
    assert item.severity == "medium"
    assert "No IRIS+ metric mapped" in item.evidence_gap_rationale


def test_governance_metadata_carried_in_output() -> None:
    claim = ImpactClaim(text="Some claim", evidence_strength=2)
    output = review_company_claims(
        _company(),
        [claim],
        prompt_version="prompt-v9",
        model_version="rules-v3",
    )
    assert output.governance["prompt_version"] == "prompt-v9"
    assert output.governance["model_version"] == "rules-v3"
    assert output.governance["claims_reviewed"] == 1


def test_overall_score_propagates_classification() -> None:
    claims = [
        ImpactClaim(text="Sustainable energy", evidence_strength=1),
        ImpactClaim(text="Eco-friendly product", evidence_strength=1),
    ]
    output = review_company_claims(_company(), claims)
    assert 0 <= output.overall.overall_score <= 100
    assert output.overall.classification
