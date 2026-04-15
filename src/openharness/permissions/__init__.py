"""Permission package exports.

PermissionChecker is lazy-loaded to avoid a circular import:
config.settings -> permissions.modes -> permissions -> checker -> config.settings
"""

from __future__ import annotations

from .modes import PermissionMode

__all__ = ["PermissionChecker", "PermissionMode"]


def __getattr__(name: str):
    if name == "PermissionChecker":
        from .checker import PermissionChecker

        return PermissionChecker
    raise AttributeError(name)
