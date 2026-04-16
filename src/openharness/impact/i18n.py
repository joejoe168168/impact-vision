"""Internationalization (i18n) utilities for Impact Vision.

Loads localized strings from YAML files in ``data/i18n/``.  Falls back
to English when a key or locale is missing.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_I18N_DIR = Path(__file__).resolve().parents[3] / "data" / "i18n"
_SUPPORTED_LOCALES = ("en", "es", "fr", "pt", "zh", "ar")


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning {} on any error."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed — i18n strings unavailable")
        return {}
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=8)
def _load_report_strings() -> dict[str, dict[str, str]]:
    return _load_yaml(_I18N_DIR / "report_strings.yaml")


@lru_cache(maxsize=8)
def _load_system_prompts() -> dict[str, str]:
    return _load_yaml(_I18N_DIR / "system_prompts.yaml")


def get_report_strings(locale: str = "en") -> dict[str, str]:
    """Return report label strings for the given locale (falls back to 'en')."""
    data = _load_report_strings()
    if locale in data:
        return data[locale]
    short = locale.split("-")[0].split("_")[0].lower()
    if short in data:
        return data[short]
    return data.get("en", {})


def get_system_prompt_preamble(locale: str = "en") -> str:
    """Return the localized system prompt preamble."""
    data = _load_system_prompts()
    short = locale.split("-")[0].split("_")[0].lower()
    return data.get(short, data.get("en", ""))


def load_dd_checklist_localized(locale: str = "en") -> dict[str, Any]:
    """Load the localized DD checklist if available."""
    if locale == "en":
        return {}
    short = locale.split("-")[0].split("_")[0].lower()
    path = _I18N_DIR / f"dd_checklist_{short}.yaml"
    return _load_yaml(path)


def supported_locales() -> tuple[str, ...]:
    """Return tuple of supported locale codes."""
    return _SUPPORTED_LOCALES
