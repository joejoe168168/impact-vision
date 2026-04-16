"""Swarm package exports."""

from __future__ import annotations

__all__ = ["lockfile"]


def __getattr__(name: str):
    if name == "lockfile":
        import importlib
        return importlib.import_module("openharness.swarm.lockfile")
    raise AttributeError(name)
