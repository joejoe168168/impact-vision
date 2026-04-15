"""Swarm package exports."""

from __future__ import annotations

__all__ = ["lockfile"]


def __getattr__(name: str):
    if name == "lockfile":
        from . import lockfile

        return lockfile
    raise AttributeError(name)
