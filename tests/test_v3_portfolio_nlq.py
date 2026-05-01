"""Tests for v3 natural-language portfolio query engine."""

from __future__ import annotations

from openharness.impact.models import MetricRecord
from openharness.impact.portfolio_nlq import (
    ApprovedDataPolicy,
    PortfolioNLQEngine,
    parse_intent,
)


def _record(metric_id: str, value: str, *, owner: str = "Acme", verified: bool = True) -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        value=value,
        unit="tCO2e",
        period="FY2025",
        source="audited",
        owner=owner,
        quality_score=85,
        verification_status="audited" if verified else "self_reported",
        evidence_refs=[f"evidence://{owner}-{metric_id}"],
    )


def test_parse_intent_recognises_average_and_metric_id() -> None:
    intent = parse_intent("What is the average OI4112 in FY2025?")
    assert intent.type == "average"
    assert intent.metric_id == "OI4112"
    assert "FY" in intent.period


def test_parse_intent_recognises_top_n() -> None:
    intent = parse_intent("Show me the top 3 owners by OI4112")
    assert intent.type == "top_n"
    assert intent.top_n == 3


def test_parse_intent_recognises_compare() -> None:
    intent = parse_intent("Compare OI4112 vs OI1479")
    assert intent.type == "compare"
    assert intent.metric_id == "OI4112"
    assert intent.secondary_metric_id == "OI1479"


def test_average_intent_returns_numeric_answer_and_citations() -> None:
    engine = PortfolioNLQEngine(records=[
        _record("OI4112", "100", owner="Acme"),
        _record("OI4112", "200", owner="Beta"),
    ])
    answer = engine.answer("Average OI4112")
    assert answer.numeric_answer == 150.0
    assert "evidence://Acme-OI4112" in answer.citations


def test_total_intent_sums_values() -> None:
    engine = PortfolioNLQEngine(records=[
        _record("OI4112", "100"),
        _record("OI4112", "250"),
    ])
    answer = engine.answer("Total OI4112")
    assert answer.numeric_answer == 350.0


def test_top_n_intent_returns_ranked_owners() -> None:
    engine = PortfolioNLQEngine(records=[
        _record("OI4112", "10", owner="Low"),
        _record("OI4112", "100", owner="High"),
        _record("OI4112", "50", owner="Mid"),
    ])
    answer = engine.answer("Top 2 owners by OI4112")
    assert "High" in answer.answer_text
    assert "1." in answer.answer_text


def test_unverified_records_excluded_under_default_policy() -> None:
    engine = PortfolioNLQEngine(records=[
        _record("OI4112", "100", verified=True),
        _record("OI4112", "999", verified=False),
    ])
    answer = engine.answer("Average OI4112")
    assert answer.numeric_answer == 100.0
    assert any("unverified" in w for w in answer.warnings)


def test_include_unverified_cannot_bypass_default_approved_data_policy() -> None:
    engine = PortfolioNLQEngine(records=[
        _record("OI4112", "100", verified=True),
        _record("OI4112", "999", verified=False),
    ])
    answer = engine.answer("Average OI4112", include_unverified=True)
    assert answer.numeric_answer == 100.0
    assert any("ignored" in w for w in answer.warnings)


def test_include_unverified_requires_explicit_policy_opt_in() -> None:
    engine = PortfolioNLQEngine(
        records=[
            _record("OI4112", "100", verified=True),
            _record("OI4112", "200", verified=False),
        ],
        policy=ApprovedDataPolicy(
            require_verified=True,
            allow_unverified_with_warning=True,
        ),
    )
    answer = engine.answer("Average OI4112", include_unverified=True)
    assert answer.numeric_answer == 150.0
    assert any("includes 1 unverified" in w for w in answer.warnings)


def test_unverified_records_included_when_policy_relaxed() -> None:
    engine = PortfolioNLQEngine(
        records=[
            _record("OI4112", "100", verified=True),
            _record("OI4112", "200", verified=False),
        ],
        policy=ApprovedDataPolicy(require_verified=False),
    )
    answer = engine.answer("Average OI4112")
    assert answer.numeric_answer == 150.0


def test_compare_intent_returns_delta() -> None:
    engine = PortfolioNLQEngine(records=[
        _record("OI4112", "100"),
        _record("OI1479", "60"),
    ])
    answer = engine.answer("Compare OI4112 with OI1479")
    assert answer.numeric_answer == 40.0


def test_unknown_intent_returns_safe_message() -> None:
    engine = PortfolioNLQEngine(records=[])
    answer = engine.answer("hello world")
    assert answer.intent.type == "unknown"
    assert "supported intent" in answer.answer_text.lower()
