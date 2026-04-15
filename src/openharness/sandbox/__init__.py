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
    if name in {
        "SandboxAvailability",
        "SandboxUnavailableError",
        "build_sandbox_runtime_config",
        "get_sandbox_availability",
        "wrap_command_for_sandbox",
    }:
        from .adapter import (
            SandboxAvailability,
            SandboxUnavailableError,
            build_sandbox_runtime_config,
            get_sandbox_availability,
            wrap_command_for_sandbox,
        )

        return {
            "SandboxAvailability": SandboxAvailability,
            "SandboxUnavailableError": SandboxUnavailableError,
            "build_sandbox_runtime_config": build_sandbox_runtime_config,
            "get_sandbox_availability": get_sandbox_availability,
            "wrap_command_for_sandbox": wrap_command_for_sandbox,
        }[name]
    raise AttributeError(name)
