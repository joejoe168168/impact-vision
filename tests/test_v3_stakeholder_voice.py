"""Tests for v3 stakeholder voice (Lean Data templates, consent, quality, evidence linking)."""

from __future__ import annotations

import pytest

from openharness.impact.evidence_graph import EvidenceLink
from openharness.impact.models import BeneficiaryFeedback, ImpactClaim
from openharness.impact.stakeholder_voice import (
    ConsentRecord,
    build_lean_data_survey,
    filter_active_responses,
    link_feedback_to_claims,
    revoke_consent,
    score_feedback_quality,
)


def test_build_lean_data_survey_has_core_questions_for_sector() -> None:
    template = build_lean_data_survey(sector="energy", languages=["en", "sw"])
    question_ids = [q.question_id for q in template.questions]
    # Core 60Db-style block plus the energy overlay
    assert "ld_q1_first_access" in question_ids
    assert "ld_q5_recommendation" in question_ids
    assert "ld_energy_q1_hours" in question_ids
    assert template.languages == ["en", "sw"]


def test_score_feedback_quality_flags_low_completion_and_short_surveys() -> None:
    quality = score_feedback_quality(
        completed_responses=10,
        invited_responses=200,  # 5%
        response_durations_seconds=[30, 40, 50],  # well under 2 minutes
        demographic_segments_present=0,
        demographic_segments_target=4,
        active_consents=10,
    )
    assert quality.quality_band == "low"
    assert "low_completion_rate" in quality.flags
    assert "survey_too_short" in quality.flags
    assert "weak_demographic_coverage" in quality.flags
    assert quality.overall_score < 50


def test_score_feedback_quality_high_score_for_clean_dataset() -> None:
    quality = score_feedback_quality(
        completed_responses=180,
        invited_responses=200,
        response_depth={f"q{i}": 5 for i in range(8)},
        response_durations_seconds=[600, 700, 800],
        demographic_segments_present=4,
        demographic_segments_target=4,
        active_consents=180,
    )
    assert quality.quality_band == "high"
    assert quality.overall_score >= 80


def test_score_feedback_quality_clamps_inconsistent_counts() -> None:
    quality = score_feedback_quality(
        completed_responses=12,
        invited_responses=10,
        response_depth={"q1": 5},
        response_durations_seconds=[600],
        demographic_segments_present=6,
        demographic_segments_target=4,
        active_consents=15,
    )
    assert quality.completion_rate_pct == 100.0
    assert quality.demographic_coverage_pct == 100.0
    assert quality.consent_active_pct == 100.0
    assert "completion_exceeds_invites" in quality.flags
    assert "consent_count_exceeds_completed" in quality.flags


def test_consent_revocation_excludes_responses() -> None:
    consent_a = ConsentRecord(
        consent_id="c1",
        respondent_id="r1",
        survey_id="s1",
        consent_text_version="v1",
    )
    consent_b = revoke_consent(ConsentRecord(
        consent_id="c2",
        respondent_id="r2",
        survey_id="s1",
        consent_text_version="v1",
    ))
    consents = {"r1": consent_a, "r2": consent_b}
    responses = {"r1": {"q1": 4}, "r2": {"q1": 5}}
    filtered = filter_active_responses(consents, responses)
    assert "r1" in filtered
    assert "r2" not in filtered


def test_link_feedback_to_claims_emits_supporting_links() -> None:
    feedback = BeneficiaryFeedback(
        sample_size=120,
        methodology="60 Decibels Lean Data",
        themes=["clean energy access", "household savings"],
        challenges=["affordability"],
        quotes=["Clean energy access changed our evenings"],
    )
    claims = [
        ImpactClaim(text="We deliver clean energy access to rural households", evidence_strength=2),
        ImpactClaim(text="Annual savings on diesel for the household", evidence_strength=3),
    ]
    graph = link_feedback_to_claims(feedback, claims)
    feedback_nodes = [n for n in graph.nodes if n.type == "evidence" and n.data.get("kind") == "beneficiary_feedback_theme"]
    assert any("clean energy access" in n.data.get("theme", "") for n in feedback_nodes)
    supporting_links = [link for link in graph.links if isinstance(link, EvidenceLink) and link.type == "supported_by"]
    assert supporting_links


def test_link_feedback_attaches_quotes_to_relevant_themes() -> None:
    feedback = BeneficiaryFeedback(
        sample_size=50,
        methodology="60 Decibels",
        themes=["clean energy"],
        quotes=["Clean energy changed our home routine"],
    )
    claims = [ImpactClaim(text="Provides clean energy to households", evidence_strength=2)]
    graph = link_feedback_to_claims(feedback, claims)
    matching = [
        node for node in graph.nodes
        if node.type == "evidence" and node.data.get("supporting_quotes")
    ]
    assert matching, "expected at least one feedback node with attached quotes"


def test_consent_record_active_property_after_revoke() -> None:
    record = ConsentRecord(
        consent_id="c1",
        respondent_id="r1",
        survey_id="s1",
        consent_text_version="v1",
    )
    assert record.is_active is True
    revoked = revoke_consent(record)
    assert revoked.is_active is False
    with pytest.raises(ValueError):
        ConsentRecord(
            consent_id="c2",
            respondent_id="r2",
            survey_id="s1",
            consent_text_version="v1",
            retention_period_days=0,  # ge=1
        )
