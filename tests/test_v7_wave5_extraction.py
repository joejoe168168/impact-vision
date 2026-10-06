"""Roadmap v7 W5.6 — extraction quality gate and LLM-by-default."""

from __future__ import annotations

import json


def test_production_chain_passes_the_blocking_gate() -> None:
    from openharness.impact._paths import data_path
    from openharness.impact.extraction_eval import GATE, production_extract, run_eval

    result = run_eval(lambda t: production_extract(t, extractor_id="regex"),
                      str(data_path("eval", "extraction_gold.jsonl")))
    assert result.f1 >= GATE, result.per_field
    assert set(result.per_field) == {"claims", "metrics", "sdgs", "categories", "quantities"}
    assert result.per_field["quantities"]["recall"] == 1.0  # decimals + thousands separators


def test_gold_set_covers_the_hard_cases() -> None:
    from openharness.impact._paths import data_path

    rows = [json.loads(line) for line in data_path("eval", "extraction_gold.jsonl").read_text().splitlines() if line]
    assert len(rows) >= 18
    assert any(r["expected_metrics"] == [] and "Forward-looking" in r.get("note", "") for r in rows)
    assert any(r["expected_claims"] == [] for r in rows)  # negation
    assert any(q for r in rows for q in r.get("expected_quantities", []) if "." in q)  # decimals


def test_mapper_disambiguates_scope_1_and_sales() -> None:
    from openharness.impact.claim_metric_mapper import map_claim_metrics

    ids = lambda s: [m.metric_id for m in map_claim_metrics(s)]  # noqa: E731
    assert ids("The company reports 1,200 tCO2e Scope 1 emissions.") == ["OI4112"]
    assert ids("We emitted 5,000 tCO2e across scope 1 and 2.") == ["OI1479"]
    assert ids("Our farms generated 1.8 GWh of solar power, all sold to the grid.") == ["PI5842"]
    assert ids("The programme created 80 permanent jobs.") == ["PI3687"]
    assert ids("500 low-income customers gained access to finance.") == ["PI4060"]


def test_extractor_auto_uses_llm_only_with_a_key(monkeypatch) -> None:
    from openharness.impact.extractors import resolve_extractor_id

    monkeypatch.delenv("IMPACT_VISION_EXTRACTOR", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert resolve_extractor_id("auto") == "regex"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert resolve_extractor_id("auto") == "llm"
    assert resolve_extractor_id("regex") == "regex"  # explicit choice wins
    monkeypatch.setenv("IMPACT_VISION_EXTRACTOR", "regex")
    assert resolve_extractor_id("auto") == "regex"


def test_llm_fallback_claims_are_not_disclosed_as_ai() -> None:
    from openharness.impact.ai_provenance import ai_provenance_for_report

    prov = ai_provenance_for_report({"impact_claims": [{"text": "x", "extracted_by": "llm-fallback(no-api-key-or-empty)"}]})
    assert prov.extraction == "rules" and not prov.ai_generated
