"""Sandbox package exports."""

from __future__ import annotations

__all__ = [
    "SandboxAvailability",
    "SandboxUnavailableError",
    "build_sandbox_runtime_config",
    "get_sandbox_availability",
    "wrap_command_for_sandbox",
]


def __getattr__(name: str):
    """Lazy-load from adapter to avoid pulling in config at package import time."""
    if name in __all__:
        from .adapter import (
            SandboxAvailability,
            SandboxUnavailableError,
            build_sandbox_runtime_config,
            get_sandbox_availability,
            wrap_command_for_sandbox,
        )

        _exports = {
            "SandboxAvailability": SandboxAvailability,
            "SandboxUnavailableError": SandboxUnavailableError,
            "build_sandbox_runtime_config": build_sandbox_runtime_config,
            "get_sandbox_availability": get_sandbox_availability,
            "wrap_command_for_sandbox": wrap_command_for_sandbox,
        }
        return _exports[name]
    raise AttributeError(name)
