"""v8 W1.6: negative impacts by severity × likelihood, lowered by disclosed controls."""
from __future__ import annotations

from impact_vision.impact.negative_impacts import assess_negative_impacts, plan_items
from impact_vision.impact.pipeline import assess_file, sample_deck_path
from impact_vision.impact.report_templates.decision_report import render_decision_report


def test_disclosed_control_lowers_likelihood():
    bare = {r["id"]: r for r in assess_negative_impacts("fintech", "We lend to small farmers.")["items"]}
    managed = {r["id"]: r for r in assess_negative_impacts(
        "fintech", "We lend to small farmers and cap loans at 30% of repayment capacity.")["items"]}
    assert bare["overindebt"]["score"] == 6 and bare["overindebt"]["band"] == "high"
    assert managed["overindebt"]["controlled"] and managed["overindebt"]["score"] < 6


def test_unaddressed_material_impacts_become_questions_not_findings():
    bundle = assess_file(sample_deck_path("solar"))
    neg = bundle.report_data["negative_impacts"]
    assert any(r["id"] == "labour_supply" and not r["controlled"] for r in neg["material_unaddressed"])
    plan = bundle.report_data["expected_impact"]["evidence_plan"]
    assert any("forced or child labour" in p["action"] for p in plan)
    assert bundle.report_data["expected_impact"]["gate"]["state"] != "fails_thesis"
    assert plan_items({"material_unaddressed": []}) == []


def test_report_shows_the_table():
    html = render_decision_report(assess_file(sample_deck_path("pig-farm")).report_data)
    assert "Potential negative impacts" in html and 'class="neg"' in html
