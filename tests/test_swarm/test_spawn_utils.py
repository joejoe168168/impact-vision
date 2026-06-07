"""Tests for teammate spawn helper behavior."""

from __future__ import annotations

import sys

from openharness.swarm.spawn_utils import (
    TEAMMATE_COMMAND_ENV_VAR,
    build_inherited_env_vars,
    get_teammate_command,
)


def test_get_teammate_command_prefers_current_interpreter(monkeypatch):
    monkeypatch.delenv(TEAMMATE_COMMAND_ENV_VAR, raising=False)
    monkeypatch.setattr(sys, "executable", "/tmp/current-python")

    command = get_teammate_command()

    assert command == "/tmp/current-python"


def test_build_inherited_env_vars_disables_coordinator_mode(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_COORDINATOR_MODE", "1")

    env = build_inherited_env_vars()

    assert env["CLAUDE_CODE_COORDINATOR_MODE"] == "0"


def test_build_inherited_env_vars_includes_openharness_auth_vars(monkeypatch):
    monkeypatch.setenv("OPENHARNESS_PROVIDER", "openai")
    monkeypatch.setenv("OPENHARNESS_BASE_URL", "https://relay.example.com/v1")
    monkeypatch.setenv("OPENHARNESS_OPENAI_API_KEY", "sk-oh-openai")
    monkeypatch.setenv("OPENHARNESS_ANTHROPIC_API_KEY", "sk-oh-anthropic")
    monkeypatch.setenv("OPENHARNESS_NAXTCLAUDE_API_KEY", "sk-oh-naxt")

    env = build_inherited_env_vars()

    assert env["OPENHARNESS_AGENT_TEAMS"] == "1"
    assert env["OPENHARNESS_PROVIDER"] == "openai"
    assert env["OPENHARNESS_BASE_URL"] == "https://relay.example.com/v1"
    assert env["OPENHARNESS_OPENAI_API_KEY"] == "sk-oh-openai"
    assert env["OPENHARNESS_ANTHROPIC_API_KEY"] == "sk-oh-anthropic"
    assert env["OPENHARNESS_NAXTCLAUDE_API_KEY"] == "sk-oh-naxt"
