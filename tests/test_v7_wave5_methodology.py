"""Roadmap v7 W5.2 — methodology versioning."""

from __future__ import annotations

import json

import yaml


def test_methodology_stamp_on_models_and_outputs() -> None:
    from openharness.impact.exports import build_workbook, to_csv, to_json
    from openharness.impact.methodology import methodology_stamp
    from openharness.impact.pipeline import assess_file, sample_deck_path
    from openharness.impact.report_templates.decision_report import render_decision_report

    stamp = methodology_stamp()
    assert stamp["methodology_version"] == "1.0.0" and len(stamp["config_hash"]) == 12
    bundle = assess_file(sample_deck_path("solar"))
    assert bundle.assessment.methodology == stamp
    assert bundle.assessment.five_dimensions.methodology == stamp
    assert bundle.greenwashing.methodology == stamp
    assert bundle.summary()["methodology"] == stamp
    data = bundle.report_data
    assert f"config {stamp['config_hash']}" in render_decision_report(data)
    assert stamp["config_hash"] in render_decision_report(data, lang="zh-HK")
    assert json.loads(to_json(data))["methodology"] == stamp
    assert stamp["config_hash"] in to_csv(data)
    summary = {r[0].value: r[1].value for r in build_workbook(data)["Summary"].iter_rows(min_row=4)}
    assert summary["Methodology version"] == "1.0.0"


def test_appendix_is_generated_from_yaml(tmp_path, monkeypatch) -> None:
    from openharness.impact import methodology
    from openharness.impact._paths import data_path
    from openharness.impact.five_dimensions import _grade_from_score
    from openharness.impact.greenwashing import _classify

    base = yaml.safe_load(data_path("methodology", "v1.yaml").read_text(encoding="utf-8"))
    rows = dict(methodology.methodology_appendix())
    assert "(30%)" in rows["Greenwashing"] and "× 4.5" in rows["5 Dimensions"]

    custom = dict(base, version="9.9.9")
    custom["greenwashing"] = dict(base["greenwashing"], weights={
        "claim_metric_gap": 0.5, "adverse_omission": 0.2, "specificity": 0.1,
        "selectivity": 0.1, "verification": 0.1})
    custom["five_dimensions"] = dict(base["five_dimensions"], grade_bands=[{"min": 0.0, "grade": "Z"}])
    path = tmp_path / "custom.yaml"
    path.write_text(yaml.safe_dump(custom), encoding="utf-8")
    original = methodology.methodology_stamp()
    monkeypatch.setenv("IMPACT_VISION_METHODOLOGY", str(path))
    try:
        assert methodology.methodology_version() == "9.9.9"
        assert methodology.config_hash() != original["config_hash"]
        assert "(50%)" in dict(methodology.methodology_appendix())["Greenwashing"]
        assert _grade_from_score(4.9) == "Z"
        assert _classify(10) == "Genuine Impact Leader"
    finally:
        monkeypatch.delenv("IMPACT_VISION_METHODOLOGY")
    assert methodology.methodology_stamp() == original
