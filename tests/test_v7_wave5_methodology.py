"""Roadmap v7 W5.2 — methodology versioning."""

from __future__ import annotations

import json

import yaml


def test_methodology_stamp_on_models_and_outputs() -> None:
    from impact_vision.impact.exports import build_workbook, to_csv, to_json
    from impact_vision.impact.methodology import methodology_stamp
    from impact_vision.impact.pipeline import assess_file, sample_deck_path
    from impact_vision.impact.report_templates.decision_report import render_decision_report

    stamp = methodology_stamp()
    assert stamp["methodology_version"] == "1.2.0" and len(stamp["config_hash"]) == 12
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
    assert summary["Methodology version"] == "1.2.0"


def test_appendix_is_generated_from_yaml(tmp_path, monkeypatch) -> None:
    from impact_vision.impact import methodology
    from impact_vision.impact._paths import data_path
    from impact_vision.impact.five_dimensions import _grade_from_score
    from impact_vision.impact.greenwashing import _classify

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


def test_stamp_names_the_methodology_behind_the_verdict(monkeypatch) -> None:
    """The footer said "Methodology v1.2.0" while v2.yaml produced the headline and the gate."""
    from impact_vision.impact import expected_impact, methodology
    from impact_vision.impact.ic_memo import render_ic_memo_markdown
    from impact_vision.impact.pipeline import assess_file, sample_deck_path
    from impact_vision.impact.report_templates.decision_report import render_decision_report

    stamp = methodology.methodology_stamp()
    v2 = expected_impact.params()["version"]
    assert stamp["expected_impact_version"] == v2
    label = methodology.stamp_text(stamp)
    assert f"v{v2} (expected impact, IC gate)" in label and "v1.2.0 (5D, SDG, greenwashing)" in label

    bundle = assess_file(sample_deck_path("solar"))
    assert label in render_decision_report(bundle.report_data)
    assert f"v{v2}（預期影響" in render_decision_report(bundle.report_data, lang="zh-HK")
    assert label in render_ic_memo_markdown(bundle.assessment, bundle.scorecard, bundle.thesis)

    # With methodology 1 forced, expected impact does not drive the verdict and is not on the stamp.
    monkeypatch.setenv("IMPACT_VISION_METHODOLOGY_VERSION", "1")
    assert "expected_impact_version" not in methodology.methodology_stamp()
    assert methodology.stamp_text() == f"Methodology v1.2.0 · config {stamp['config_hash']}"


def test_config_hash_moves_with_every_file_that_can_change_a_score(tmp_path, monkeypatch) -> None:
    """Editing the contribution rubric or the negative-impact catalogue used to leave the stamp unchanged."""
    import shutil

    from impact_vision.impact import _paths, methodology

    assert {"methodology/v2.yaml", "methodology/contribution_rubric.yaml",
            "negative_impacts.yaml"} <= set(methodology.HASHED_FILES)
    original = methodology.config_hash()
    real = _paths.data_path()
    for rel in ("methodology/v2.yaml", "methodology/contribution_rubric.yaml", "negative_impacts.yaml"):
        copy = tmp_path / rel.replace("/", "_")
        shutil.copytree(real, copy, ignore=shutil.ignore_patterns("raw", "processed", "sample_decks", "calibration"))
        target = copy / rel
        target.write_text(target.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
        monkeypatch.setattr(methodology, "data_path", lambda *parts, _root=copy: _root.joinpath(*parts))
        methodology.clear_cache()
        try:
            assert methodology.config_hash() != original, rel
        finally:
            monkeypatch.undo()
            methodology.clear_cache()
    assert methodology.config_hash() == original
