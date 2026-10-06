"""Impact Vision public package (v7 W5.5).

``impact_vision`` is the supported import path. The implementation still lives
in ``openharness`` (physical move scheduled with the 0.18 shim removal), and
every ``impact_vision.*`` module is the *same object* as its implementation
module, so ``isinstance`` checks and monkeypatching work from either name:

=============================  =====================================
``impact_vision.<name>``       ``openharness.impact.<name>``
``impact_vision.tools``        ``openharness.tools.impact``
``impact_vision.cli``          ``openharness.cli``
``impact_vision.web``          ``openharness.web``
``impact_vision.api_gateway``  ``openharness.api_gateway``
``impact_vision.dashboard``    ``openharness.dashboard``
=============================  =====================================

Examples::

    from impact_vision import ImpactVision
    from impact_vision.frameworks.esrs import load_simplified_datapoints
    from impact_vision.tools import ImpactReportTool
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from typing import Any

_PREFIX_MAP: dict[str, str] = {
    "impact_vision.impact": "openharness.impact",  # legacy spelling: impact_vision.impact.models
    "impact_vision.tools": "openharness.tools.impact",
    "impact_vision.cli": "openharness.cli",
    "impact_vision.web": "openharness.web",
    "impact_vision.api_gateway": "openharness.api_gateway",
    "impact_vision.dashboard": "openharness.dashboard",
}


def _real_name(fullname: str) -> str:
    for alias, real in _PREFIX_MAP.items():
        if fullname == alias or fullname.startswith(alias + "."):
            return real + fullname[len(alias):]
    return "openharness.impact." + fullname[len("impact_vision."):]


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, real: str) -> None:
        self.real = real

    def create_module(self, spec):  # noqa: ANN001, ANN201
        return importlib.import_module(self.real)

    def exec_module(self, module) -> None:  # noqa: ANN001
        return None  # already executed under its real name


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):  # noqa: ANN001, ANN201
        if not fullname.startswith("impact_vision."):
            return None
        real = _real_name(fullname)
        if importlib.util.find_spec(real) is None:
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(real))


if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

_OH = importlib.import_module("openharness")
_OH_IMPACT = importlib.import_module("openharness.impact")
sys.modules[f"{__name__}.impact"] = _OH_IMPACT
impact = _OH_IMPACT

__all__ = ["impact"]


def __getattr__(name: str) -> Any:
    if name == "openharness":
        return _OH
    if name == "ImpactVision":
        from openharness.impact.sdk import ImpactVision

        return ImpactVision
    try:
        return getattr(_OH_IMPACT, name)
    except AttributeError:
        pass
    try:  # submodule access without an explicit import (impact_vision.sdk)
        return importlib.import_module(f"{__name__}.{name}")
    except ImportError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
