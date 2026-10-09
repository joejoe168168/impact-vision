"""Configuration package exports.

Settings and load_settings are lazy-loaded to avoid heavy transitive imports
(hooks.schemas, mcp.types, permissions.modes, etc.) at package import time.
"""

from __future__ import annotations

from .paths import get_config_file_path

__all__ = ["Settings", "get_config_file_path", "load_settings", "save_settings"]


def __getattr__(name: str):
    if name in {"Settings", "load_settings", "save_settings"}:
        from .settings import Settings, load_settings, save_settings

        return {"Settings": Settings, "load_settings": load_settings, "save_settings": save_settings}[name]
    raise AttributeError(name)
