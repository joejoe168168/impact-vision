"""Configuration package exports."""

from __future__ import annotations

from .paths import get_config_file_path

__all__ = ["Settings", "get_config_file_path", "load_settings"]


def __getattr__(name: str):
    if name in {"Settings", "load_settings"}:
        from .settings import Settings, load_settings

        return {"Settings": Settings, "load_settings": load_settings}[name]
    raise AttributeError(name)
