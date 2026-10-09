"""W1.4: the fund-manager tool profile hides coding-agent tools."""

from __future__ import annotations

import pytest

from impact_vision.impact.tool_advisor import routed_tool_names
from impact_vision.tools import create_default_tool_registry, resolve_tool_profile
from impact_vision.web.chat_session import SessionOptions

UNSAFE_FOR_FUNDS = {"bash", "write_file", "edit_file", "enter_worktree", "cron_create",
                    "team_create", "agent", "remote_trigger", "notebook_edit"}


def _names(**kw) -> set[str]:
    return {t.name for t in create_default_tool_registry(**kw).list_tools()}


def test_fund_profile_hides_coding_tools_but_keeps_impact_tools(monkeypatch):
    monkeypatch.delenv("IMPACT_VISION_TOOL_PROFILE", raising=False)
    fund = _names(profile="fund")
    developer = _names()
    assert not UNSAFE_FOR_FUNDS & fund
    assert UNSAFE_FOR_FUNDS <= developer
    assert {"read_file", "web_search", "ask_user_question"} <= fund
    # Every tool the advisor can route to is available to fund managers.
    assert routed_tool_names() <= fund
    assert len(fund) < len(developer)


def test_profile_env_override_and_validation(monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_TOOL_PROFILE", "fund")
    assert resolve_tool_profile() == "fund"
    assert "bash" not in _names()
    assert resolve_tool_profile("developer") == "developer"
    with pytest.raises(ValueError):
        resolve_tool_profile("admin")


def test_web_chat_defaults_to_fund_profile(monkeypatch):
    monkeypatch.delenv("IMPACT_VISION_TOOL_PROFILE", raising=False)
    assert SessionOptions().tool_profile == "fund"
    monkeypatch.setenv("IMPACT_VISION_TOOL_PROFILE", "developer")
    assert SessionOptions().tool_profile == "developer"
