"""Impact Vision public namespace.

The implementation package is still ``openharness`` until the deferred wheel
trim. This module re-exports it so ``import impact_vision`` and
``import impact_vision.impact`` work.
"""

from __future__ import annotations

import sys
from importlib import import_module
from typing import Any

_OH = import_module("openharness")
_OH_IMPACT = import_module("openharness.impact")
sys.modules[f"{__name__}.impact"] = _OH_IMPACT
impact = _OH_IMPACT

__all__ = ["impact"]


def __getattr__(name: str) -> Any:
    if name == "openharness":
        return _OH
    try:
        return getattr(_OH_IMPACT, name)
    except AttributeError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
