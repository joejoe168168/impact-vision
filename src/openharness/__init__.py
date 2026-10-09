"""Compatibility alias: ``openharness`` is ``impact_vision`` (roadmap v8 W5.1).

The code moved to ``impact_vision`` in 0.19. Every ``openharness.<path>`` is
the same module object as ``impact_vision.<path>``, so existing imports,
``isinstance`` checks and monkeypatch targets keep working. New code should
import ``impact_vision``.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from typing import Any

_NEW = "impact_vision"


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


class _OpenHarnessAlias(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):  # noqa: ANN001, ANN201
        if not fullname.startswith("openharness.") or fullname == "openharness.__main__":
            return None
        real = _NEW + fullname[len("openharness"):]
        try:
            if importlib.util.find_spec(real) is None:
                return None
        except (ImportError, ValueError):
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(real))


if not any(isinstance(f, _OpenHarnessAlias) for f in sys.meta_path):
    sys.meta_path.insert(0, _OpenHarnessAlias())


def __getattr__(name: str) -> Any:
    try:
        return importlib.import_module(f"openharness.{name}")
    except ImportError as exc:
        raise AttributeError(f"module 'openharness' has no attribute {name!r}") from exc


__all__: list[str] = []
