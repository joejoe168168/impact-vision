"""Hook package exports."""

from __future__ import annotations

from .events import HookEvent

__all__ = ["HookEvent", "HookExecutionContext", "HookExecutor", "load_hook_registry"]


def __getattr__(name: str):
    if name in {"HookExecutionContext", "HookExecutor"}:
        from .executor import HookExecutionContext, HookExecutor

        return {"HookExecutionContext": HookExecutionContext, "HookExecutor": HookExecutor}[name]
    if name == "load_hook_registry":
        from .loader import load_hook_registry

        return load_hook_registry
    raise AttributeError(name)
