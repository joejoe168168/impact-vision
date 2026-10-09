"""W1.5: duplicate tools are merged; old names survive as developer-only aliases."""

from __future__ import annotations

import asyncio
import typing
from pathlib import Path

import pytest

import impact_vision.tools.impact as impact_tools
from impact_vision.tools import create_default_tool_registry
from impact_vision.tools.base import ToolExecutionContext
from impact_vision.tools.impact.merged_tools import (
    DEPRECATED_TOOLS,
    DDQResponderTool,
    PipelineTool,
    PitchDeckAnalyzeTool,
    RegulatoryCalendarTool,
    StakeholderVoiceTool,
)

CTX = ToolExecutionContext(cwd=Path("."))


def _run(tool_cls, **kwargs):
    tool = tool_cls()
    return asyncio.run(tool.execute(tool.input_model(**kwargs), CTX))


def _actions(tool_cls) -> tuple[str, ...]:
    return typing.get_args(tool_cls.input_model.model_fields["action"].annotation)


def test_merged_tools_keep_their_name_and_gain_actions():
    assert StakeholderVoiceTool.name == "stakeholder_voice"
    assert {"build_survey", "feedback_analyze"} <= set(_actions(StakeholderVoiceTool))
    assert {"draft", "template_generate"} <= set(_actions(DDQResponderTool))
    assert {"schedule", "radar_findings"} <= set(_actions(RegulatoryCalendarTool))
    assert {"add", "guided_start"} <= set(_actions(PipelineTool))
    assert set(_actions(PitchDeckAnalyzeTool)) == {
        "analyze", "compare_documents", "detect_changes", "verify_claims"
    }
    # Incompatible field types are renamed for the absorbed tool.
    assert "template_output_format" in DDQResponderTool.input_model.model_fields


@pytest.mark.parametrize(
    ("tool_cls", "kwargs", "expected"),
    [
        (RegulatoryCalendarTool, {"action": "schedule", "jurisdiction": "EU"}, "Regulatory Deadline Calendar"),
        (RegulatoryCalendarTool, {"action": "radar_findings"}, ""),
        (PipelineTool, {"action": "guided_templates"}, "ASSESSMENT TEMPLATES"),
        (StakeholderVoiceTool, {"action": "feedback_analyze", "company_name": "X",
                                "satisfaction_score": 4.1, "nps": 30, "sample_size": 100},
         "BENEFICIARY FEEDBACK"),
        (PitchDeckAnalyzeTool, {"text": "SunPath Energy Ltd is a solar company in Kenya. "
                                        "We connected 42,000 households."}, "PITCH DECK"),
    ],
)
def test_both_old_and_new_actions_dispatch(tool_cls, kwargs, expected):
    result = _run(tool_cls, **kwargs)
    assert not result.is_error, result.output
    assert expected in result.output


def test_absorbed_tool_validation_errors_are_reported():
    result = _run(PitchDeckAnalyzeTool, action="compare_documents")
    assert result.is_error and "documents" in result.output


def test_registry_profiles_and_exports():
    fund = {t.name for t in create_default_tool_registry(profile="fund").list_tools()}
    developer = {t.name: t for t in create_default_tool_registry(profile="developer").list_tools()}
    for old, (_alias, replacement) in DEPRECATED_TOOLS.items():
        assert old not in fund
        assert replacement in fund
        assert developer[old].description.startswith("[Deprecated: use ")
    assert len(impact_tools.__all__) == 48
    assert not set(DEPRECATED_TOOLS) & {getattr(impact_tools, n).name for n in impact_tools.__all__}
