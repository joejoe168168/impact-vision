"""W0.3: DD questions, core metrics and risks are chosen by sector."""

from __future__ import annotations

import yaml

from impact_vision.impact._paths import data_path
from impact_vision.impact.database import get_metric_store
from impact_vision.impact.dd_checklist import (
    analyze_document_coverage,
    filter_questions_for_sector,
    load_checklist,
)
from impact_vision.impact.gap_analysis import analyze_gaps, core_set_for_sector
from impact_vision.impact.models import Company
from impact_vision.tools.impact.impact_report_tool import _infer_opportunities_and_risks

PIG_TEXT = (
    "We run an integrated pig farm with 18 smallholder outgrowers and a biogas plant. "
    "Risks we actively manage include ASF biosecurity and nutrient run-off during monsoon."
)


def test_sector_filter_keeps_only_matching_sector_questions():
    qs = filter_questions_for_sector(load_checklist(), "agriculture")
    sector_cats = {q.category for q in qs if q.category.startswith("sector_")}
    assert sector_cats == {"sector_agriculture"}
    assert any(not q.category.startswith("sector_") for q in qs)


def test_auto_sector_infers_from_text():
    qs = filter_questions_for_sector(load_checklist(), "auto", PIG_TEXT)
    assert {q.category for q in qs if q.category.startswith("sector_")} == {"sector_agriculture"}


def test_sector_none_keeps_legacy_behaviour():
    # Every company-facing question; fund-side ones (ask: fund) are listed separately.
    all_q = [q for q in load_checklist() if q.ask != "fund"]
    assert analyze_document_coverage(PIG_TEXT).total_questions == len(all_q)
    assert analyze_document_coverage(PIG_TEXT, sector="agriculture").total_questions < len(all_q)


def test_core_sets_are_sector_specific_and_valid():
    ag, basis = core_set_for_sector("Agriculture")
    assert basis == "agriculture"
    assert "OI4753" not in ag  # Client Protection Policy is a fintech metric
    assert "FP3021" not in ag  # Revenue from Grants and Donations
    assert "PI9991" in ag
    unknown, basis = core_set_for_sector("")
    # v8 W0.6: unknown sector → universal metrics only (no microfinance default).
    assert basis == "universal" and "OI4753" not in unknown and "OD4091" in unknown

    store = get_metric_store()
    cfg = yaml.safe_load(data_path("core_metric_sets_by_sector.yaml").read_text())
    every_id = set(cfg["universal"]) | set(cfg["default"])
    for ids in cfg["sectors"].values():
        every_id |= set(ids)
    assert [i for i in sorted(every_id) if store.get(i) is None] == []


def test_gap_analysis_reports_basis():
    gaps = analyze_gaps(Company(name="Farm", sector="agriculture"), get_metric_store())
    assert gaps["core_metric_set_basis"] == "agriculture"
    assert "Client Protection Policy" not in {m["name"] for m in gaps["missing"]}


def test_risks_lead_with_disclosed_risks_and_skip_unrelated_sectors():
    company = Company(name="Farm", sector="agriculture", description="Integrated pig farm.")
    risks = _infer_opportunities_and_risks(company, PIG_TEXT)["risks"]
    assert risks[0].startswith("Disclosed:") and "biosecurity" in risks[0]
    assert any("Animal welfare" in r for r in risks)  # livestock templates via "pig"
    assert not any("displacing communities for energy" in r for r in risks)


def test_energy_keyword_needs_word_boundary():
    company = Company(name="X", description="We create synergy between teams.")
    risks = _infer_opportunities_and_risks(company)["risks"]
    assert not any("energy projects" in r for r in risks)
