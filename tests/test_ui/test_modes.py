"""Tests for UI mode helpers."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from openharness.ui.output import OutputRenderer


@pytest.mark.skipif(sys.platform == "win32", reason="PromptSession requires a Windows console buffer")
def test_input_session_updates_prompt_modes():
    from openharness.ui.input import InputSession
    session = InputSession()
    assert session._prompt == "> "

    session.set_modes(vim_enabled=True, voice_enabled=False)
    assert session._prompt == "[vim]> "

    session.set_modes(vim_enabled=True, voice_enabled=True)
    assert session._prompt == "[vim][voice]> "


def test_input_session_set_modes_logic():
    """Test set_modes logic without requiring a PromptSession console."""
    from openharness.ui.input import InputSession
    with patch("openharness.ui.input.PromptSession", return_value=MagicMock()):
        session = InputSession()
    assert session._prompt == "> "

    session.set_modes(vim_enabled=True, voice_enabled=False)
    assert session._prompt == "[vim]> "

    session.set_modes(vim_enabled=True, voice_enabled=True)
    assert session._prompt == "[vim][voice]> "

    session.set_modes(vim_enabled=False, voice_enabled=False)
    assert session._prompt == "> "


def test_output_renderer_style_can_change():
    renderer = OutputRenderer()
    assert renderer._style_name == "default"

    renderer.set_style("minimal")
    assert renderer._style_name == "minimal"
