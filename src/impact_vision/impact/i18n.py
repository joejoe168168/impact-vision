"""Internationalization (i18n) utilities for Impact Vision.

Loads localized strings from YAML files in ``data/i18n/``.  Falls back
to English when a key or locale is missing. Report labels live in
``report_templates/design/strings.py`` and generated sentences in
``data/i18n/phrasebook.yaml``; this module serves the dashboard labels and the
translated DD checklists.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
from impact_vision.impact._paths import data_path

logger = logging.getLogger(__name__)

_I18N_DIR = data_path("i18n")
_SUPPORTED_LOCALES = ("en", "es", "fr", "pt", "zh", "ar")
# Chinese checklists are keyed by script: zh-HK (Traditional) and zh-CN (Simplified).
_ZH_ALIASES = {"zh": "zh-CN", "zh-cn": "zh-CN", "zh-hans": "zh-CN", "zh-sg": "zh-CN",
               "zh-hk": "zh-HK", "zh-hant": "zh-HK", "zh-tw": "zh-HK", "zh-mo": "zh-HK"}


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
def _load_dashboard_keys() -> dict[str, dict[str, str]]:
    return _load_yaml(_I18N_DIR / "dashboard_keys.yaml")


def get_dashboard_strings(locale: str = "en") -> dict[str, str]:
    """Return dashboard / web-console label strings for ``locale`` (Phase 20)."""
    data = _load_dashboard_keys()
    if locale in data:
        return data[locale]
    short = locale.split("-")[0].split("_")[0].lower()
    if short in data:
        return data[short]
    return data.get("en", {})


def load_dd_checklist_localized(locale: str = "en") -> dict[str, Any]:
    """Load the localized DD checklist if available."""
    if locale == "en":
        return {}
    locale = _ZH_ALIASES.get(locale.replace("_", "-").lower(), locale)
    exact = _I18N_DIR / f"dd_checklist_{locale}.yaml"
    if exact.exists():  # dd_checklist_zh-HK.yaml (Traditional) / dd_checklist_zh-CN.yaml (Simplified)
        return _load_yaml(exact)
    short = locale.split("-")[0].split("_")[0].lower()
    path = _I18N_DIR / f"dd_checklist_{short}.yaml"
    return _load_yaml(path)


def supported_locales() -> tuple[str, ...]:
    """Return tuple of supported locale codes."""
    return _SUPPORTED_LOCALES
