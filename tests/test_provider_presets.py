"""Pre-filled provider profiles: OpenRouter, DeepSeek, OpenAI, Ollama, custom endpoint, …"""

from __future__ import annotations

import pytest

from openharness.config.settings import (
    PROFILE_MODEL_SUGGESTIONS,
    Settings,
    credential_storage_provider_name,
    default_provider_profiles,
    is_local_base_url,
    resolve_model_setting,
)

PRESETS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "dashscope": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "mistral": "https://api.mistral.ai/v1",
    "xai": "https://api.x.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "ollama": "http://localhost:11434/v1",
}


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    for var in ("OPENROUTER_API_KEY", "OPENHARNESS_OPENROUTER_API_KEY", "DEEPSEEK_API_KEY",
                "OPENHARNESS_DEEPSEEK_API_KEY", "OPENAI_API_KEY", "OPENHARNESS_OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_presets_are_prefilled_openai_compatible_with_own_key_slot():
    profiles = default_provider_profiles()
    for name, url in PRESETS.items():
        profile = profiles[name]
        assert profile.api_format == "openai"
        assert profile.base_url == url
        assert profile.default_model, name
        assert credential_storage_provider_name(name, profile) == f"profile:{name}"
        assert PROFILE_MODEL_SUGGESTIONS[name][0] == profile.default_model
    custom = profiles["custom"]
    assert custom.api_format == "openai" and not custom.base_url


def test_claude_defaults_are_5_5():
    assert Settings().model == "claude-sonnet-5-5"
    assert default_provider_profiles()["claude-api"].default_model == "claude-sonnet-5-5"
    assert resolve_model_setting("opus", "anthropic") == "claude-opus-5-5"
    assert resolve_model_setting("default", "anthropic") == "claude-sonnet-5-5"


def test_env_key_resolves_for_preset(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    auth = Settings(active_profile="openrouter").materialize_active_profile().resolve_auth()
    assert auth.value == "sk-or-test" and auth.source == "env:OPENROUTER_API_KEY"


def test_local_endpoint_needs_no_key():
    settings = Settings(active_profile="ollama").materialize_active_profile()
    assert settings.base_url == "http://localhost:11434/v1"
    assert settings.resolve_auth().source == "local"
    assert is_local_base_url("http://127.0.0.1:1234/v1")
    assert not is_local_base_url("https://api.deepseek.com/v1")


def test_hosted_preset_without_key_still_errors():
    with pytest.raises(ValueError):
        Settings(active_profile="deepseek").materialize_active_profile().resolve_auth()


def test_profile_status_and_web_snapshot(monkeypatch):
    from openharness.auth.manager import AuthManager
    from openharness.web.chat_api import _provider_snapshot

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    statuses = AuthManager(Settings()).get_profile_statuses()
    assert statuses["deepseek"]["configured"] is True  # from env
    assert statuses["ollama"]["configured"] is True  # local, no key
    assert statuses["openrouter"]["configured"] is False

    snap = _provider_snapshot()
    by_name = {p["name"]: p for p in snap["profiles"]}
    assert by_name["openrouter"]["key_env"] == "OPENROUTER_API_KEY"
    assert by_name["ollama"]["local"] is True
    assert "deepseek-reasoner" in by_name["deepseek"]["models"]


def test_custom_endpoint_key_is_saved_to_its_own_slot(tmp_path):
    from openharness.auth.storage import load_credential
    from openharness.web.chat_api import ProviderUpdate, _apply_provider_update

    snap = _apply_provider_update(ProviderUpdate(
        profile="custom", base_url="https://llm.example.internal/v1", model="my-model",
        api_key="sk-custom", make_active=True))
    assert snap["active_profile"] == "custom"
    assert snap["base_url"] == "https://llm.example.internal/v1"
    assert snap["model"] == "my-model"
    assert load_credential("profile:custom", "api_key", use_keyring=False) == "sk-custom"
    auth = Settings(active_profile="custom").materialize_active_profile()
    assert auth.resolve_auth().value == "sk-custom"
