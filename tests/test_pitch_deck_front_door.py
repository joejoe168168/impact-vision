"""W0.11: the pitch-deck tool's first impression — name, sector, themes, SDGs, routing."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from openharness.impact.toolbox.workflow import build_esg_workflow
from openharness.tools.base import ToolExecutionContext
from openharness.tools.impact.pitch_deck_analyze_tool import (
    PitchDeckAnalyzeTool,
    _detect_sector,
    _detect_themes,
    _explicit_sdg_refs,
    _extract_company_model,
)

REPO = Path(__file__).resolve().parents[1]
PIG = json.loads((REPO / "demo" / "pig_farm_profile.json").read_text(encoding="utf-8"))["pitch_text"]


def _company(text: str = PIG, filename: str = "deck"):
    return _extract_company_model(text, filename, _detect_themes(text), set(), [], None)


def test_company_name_from_opening_sentence_or_legal_suffix():
    assert _company().name == "Kampung Makmur"
    assert _company("SunPath Energy Ltd sells solar kits.").name == "SunPath Energy Ltd"


def test_sector_follows_the_business_not_a_passing_mention():
    assert _detect_sector(PIG) == "Agriculture"  # mentions "school attendance" once
    assert _detect_sector("We run 40 schools and train 900 teachers for students.") == "Education"


@pytest.mark.parametrize(
    ("text", "goals"),
    [
        ("We report against IRIS+, SDG 2/6/7/8/12/13 and GRI.", {2, 6, 7, 8, 12, 13}),
        ("Our work supports SDGs 1, 5 and 8.", {1, 5, 8}),
        ("Aligned to SDG 7.", {7}),
        ("No goals here, version 2.0.", set()),
    ],
)
def test_explicit_sdg_lists_are_parsed(text, goals):
    assert _explicit_sdg_refs(text) == goals


def test_pig_farm_claims_only_its_stated_sdgs_and_relevant_themes():
    company = _extract_company_model(PIG, "deck", _detect_themes(PIG), set(), [], None)
    assert "Affordable Housing" not in company.impact_themes  # "slatted housing" = pig pens
    assert "Smallholder Agriculture" in company.impact_themes


def test_tool_output_for_pig_farm(tmp_path):
    deck = tmp_path / "pig.md"
    deck.write_text(PIG, encoding="utf-8")
    tool = PitchDeckAnalyzeTool()
    out = asyncio.run(
        tool.execute(tool.input_model(file_path=str(deck)), ToolExecutionContext(cwd=tmp_path))
    ).output
    block = out[out.index("EXTRACTED COMPANY"):]
    assert "Name: Kampung Makmur" in block
    assert "Sector: agriculture" in block
    assert "SDG Claims: SDG 2, SDG 6, SDG 7, SDG 8, SDG 12, SDG 13" in block
    assert "CBAM" not in out


def test_routing_ignores_stop_words_and_gates_cbam():
    farm = build_esg_workflow(company_description=PIG, sector="agriculture", geography="Malaysia")
    ids = {r.tool_id for r in farm.recommended_tools}
    assert not {"cbam", "cbam-steel", "cbam-export"} & ids
    stop = {"the", "of", "and", "to", "for", "data", "code"}
    for rec in farm.recommended_tools:
        assert not stop & {t.lower() for t in rec.matched_terms}

    steel = build_esg_workflow(
        company_description="We export hot-rolled steel and aluminium coils to the EU under CBAM.",
        sector="manufacturing",
    )
    assert {"cbam", "cbam-steel"} & {r.tool_id for r in steel.recommended_tools}
