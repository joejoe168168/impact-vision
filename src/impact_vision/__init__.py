"""Impact Vision — AI impact measurement and SDG alignment for funds.

The code lives here (``src/impact_vision``) since 0.19 (roadmap v8 W5.1).
``openharness.*`` is kept as an alias of the same modules for existing code.

Besides the physical sub-packages (``impact_vision.impact``, ``.tools``,
``.cli``, ``.web``, ``.api_gateway``, ``.dashboard`` …) the impact engine's
modules are reachable directly, as documented since 0.17::

    from impact_vision import ImpactVision
    from impact_vision.frameworks.esrs import load_simplified_datapoints   # = impact_vision.impact.frameworks.esrs
    from impact_vision.tools import ImpactReportTool                       # impact tool classes, lazily

Each short name is the *same module object* as its full name, so
``isinstance`` checks and monkeypatching work from either spelling.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from typing import Any

_HERE = __import__("pathlib").Path(__file__).resolve().parent


def _physical(directory: "__import__('pathlib').Path") -> set[str]:
    names = {p.stem for p in directory.glob("*.py")}
    names |= {p.name for p in directory.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    return names


_TOP = _physical(_HERE)
_TOOLS = _physical(_HERE / "tools")


def _short_target(fullname: str) -> str | None:
    """``impact_vision.<x>…`` → ``impact_vision.impact.<x>…`` when ``<x>`` isn't a real top-level module
    (``impact_vision.tools.<x>`` → ``impact_vision.tools.impact.<x>`` likewise)."""
    parts = fullname.split(".")
    if len(parts) < 2 or parts[0] != "impact_vision":
        return None
    if parts[1] == "tools":
        if len(parts) >= 3 and parts[2] not in _TOOLS:
            return ".".join(["impact_vision", "tools", "impact", *parts[2:]])
        return None
    if parts[1] in _TOP:
        return None
    return ".".join(["impact_vision", "impact", *parts[1:]])


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, real: str) -> None:
        self.real = real

    def create_module(self, spec):  # noqa: ANN001, ANN201
        module = importlib.import_module(self.real)
        # The import system re-stamps __spec__/__loader__/__package__ with the
        # alias after this returns; remember the real ones to put them back.
        self._attrs = {k: getattr(module, k, None) for k in ("__spec__", "__loader__", "__package__")}
        return module

    def exec_module(self, module) -> None:  # noqa: ANN001
        for key, value in getattr(self, "_attrs", {}).items():  # already executed under its real name
            setattr(module, key, value)


class _ShortNameFinder(importlib.abc.MetaPathFinder):
    """Short names resolve to the one real module (runs before the path finder,
    so a short name never loads a second copy of a module)."""

    def find_spec(self, fullname, path, target=None):  # noqa: ANN001, ANN201
        real = _short_target(fullname)
        if real is None:
            return None
        try:
            if importlib.util.find_spec(real) is None:
                return None
        except (ImportError, ValueError):
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(real))


if not any(isinstance(f, _ShortNameFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _ShortNameFinder())


def __getattr__(name: str) -> Any:
    if name == "ImpactVision":
        from impact_vision.impact.sdk import ImpactVision

        return ImpactVision
    if name == "impact":
        return importlib.import_module("impact_vision.impact")
    try:  # impact_vision.sdk, impact_vision.methodology, … (short names)
        return importlib.import_module(f"{__name__}.{name}")
    except ImportError:
        pass
    impact = importlib.import_module("impact_vision.impact")
    try:
        return getattr(impact, name)
    except AttributeError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc


__all__ = ["ImpactVision"]
