"""Regression tests for cross-cutting bug hardening checks."""

from __future__ import annotations

from datetime import datetime


def test_api_cors_defaults_to_same_origin_only() -> None:
    from impact_vision.api_gateway.router import _CORS_ALLOW_CREDENTIALS, _parse_cors_origins, app

    # v8 W0.1: no wildcard by default; a hostile page must not read responses.
    assert _parse_cors_origins(None) == []
    assert _parse_cors_origins("https://a.example, https://b.example") == [
        "https://a.example",
        "https://b.example",
    ]
    assert _CORS_ALLOW_CREDENTIALS is False

    cors_middleware = next(
        middleware for middleware in app.user_middleware if middleware.cls.__name__ == "CORSMiddleware"
    )
    assert cors_middleware.kwargs["allow_origins"] == []
    assert cors_middleware.kwargs["allow_credentials"] is False


def test_mochat_synthetic_event_uses_timezone_aware_utc() -> None:
    from impact_vision.channels.impl.mochat import _make_synthetic_event

    event = _make_synthetic_event("msg-1", "user-1", "hello", {}, "group-1", "conv-1")

    timestamp = datetime.fromisoformat(event["timestamp"])
    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset().total_seconds() == 0


def test_optional_channel_helpers_are_importable_and_safe() -> None:
    from impact_vision.utils.helpers import safe_filename, split_message

    assert split_message("alpha beta gamma", 7) == ["alpha", "beta", "gamma"]
    assert split_message("abcdefghij", 4) == ["abcd", "efgh", "ij"]
    assert safe_filename("../bad name?.txt") == "bad_name_.txt"


def test_copilot_user_agent_uses_installed_package_version(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)
            self.base_url = kwargs.get("base_url")

    monkeypatch.setattr("impact_vision.api.copilot_client.AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr(
        "impact_vision.api.copilot_client.importlib.metadata.version",
        lambda package_name: "9.9.9" if package_name == "impact-vision" else "0.0.0",
    )

    from impact_vision.api.copilot_client import CopilotClient

    CopilotClient(github_token="gho_headers")

    headers = captured["default_headers"]
    assert headers["User-Agent"] == "openharness/9.9.9"
    assert headers["Openai-Intent"] == "conversation-edits"
