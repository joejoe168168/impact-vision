"""W0.2: extracted claims are evidence, with or without an IRIS+ metric ID."""

from __future__ import annotations

from impact_vision.impact.extractors.base import to_impact_claims
from impact_vision.impact.extractors.regex_extractor import RegexExtractor, evidence_signals
from impact_vision.impact.greenwashing import assess_greenwashing
from impact_vision.impact.models import Company
from impact_vision.impact.sdk import ImpactVision

PITCH = (
    "Our biogas plant generates 1.8 GWh of electricity per year, replacing ~920 tonnes "
    "CO2e of grid emissions. Water withdrawal dropped 31% versus our 2020 baseline, "
    "independently verified by SIRIM. A 2024 randomized pilot compared 120 households to a "
    "matched control group and found 23% higher food-security scores. We are SEDEX-audited. "
    "Over the next five years we target a 45% reduction in emissions intensity."
)


def test_decimal_values_are_not_split():
    claims = RegexExtractor().extract(PITCH)
    energy = next(c for c in claims if c.metric_unit == "GWh")
    assert energy.metric_value == 1.8
    assert energy.text.startswith("Our biogas plant generates 1.8 GWh")


def test_evidence_signals_detected():
    assert "third_party_verified" in evidence_signals("independently verified by SIRIM.")
    assert "controlled_evaluation" in evidence_signals("a randomized pilot with a control group")
    assert "audited" in evidence_signals("We are SEDEX-audited.")
    assert evidence_signals("We help farmers thrive.") == []


def test_verification_only_sentences_become_claims():
    claims = RegexExtractor().extract(PITCH)
    cats = {c.category for c in claims}
    assert "verification" in cats
    target = next(c for c in claims if "target" in c.text)
    assert target.category == "commitment"


def test_to_impact_claims_keeps_claims_without_iris_ids():
    impact = to_impact_claims(RegexExtractor().extract(PITCH))
    assert len(impact) >= 5
    assert all(not c.mapped_metrics for c in impact)
    rct = next(c for c in impact if "randomized" in c.text)
    assert rct.evidence_strength >= 3
    assert "controlled_evaluation" in rct.entities["evidence"]


def test_sdk_assessment_carries_claims_and_lowers_verification_risk():
    iv = ImpactVision()
    assessment = iv.assess_company_text("Pig Farm", text=PITCH, sector="agriculture")
    assert len(assessment.impact_claims) >= 5

    # A short description hides the verification sentences; the claims don't.
    # (Since v8 the scorers read the whole document, so blank that too.)
    assessment.company.description = "Integrated pig farm with biogas."
    assessment.company.assessment_text = ""
    without = assess_greenwashing(assessment.company)
    with_claims = iv.screen_greenwashing(assessment)
    assert with_claims.verification < without.verification
    assert not any(f.startswith("NO_VERIFICATION") for f in with_claims.flags)


def test_greenwashing_unchanged_without_claims():
    company = Company(name="X", description="We empower communities.", sector="energy")
    assert assess_greenwashing(company).overall_score == assess_greenwashing(company, claims=None).overall_score
