"""Locate bundled reference data in both source checkouts and installed wheels.

A source checkout keeps reference data in ``<repo>/data``. The wheel ships the
same tree as ``openharness/_data`` (see ``[tool.hatch.build.targets.wheel.
force-include]`` in ``pyproject.toml``). Every loader must resolve files through
:func:`data_path` so an installed copy never silently falls back to hard-coded
defaults because ``Path(__file__).parents[3] / "data"`` points outside the
site-packages tree.

Resolution order:

1. ``IMPACT_VISION_DATA_DIR`` environment variable (explicit override).
2. ``<repo>/data`` — the source checkout.
3. ``openharness/_data`` — the installed wheel.
"""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # src/impact_vision
_REPO_DATA = _PACKAGE_ROOT.parents[1] / "data"  # <repo>/data
_WHEEL_DATA = _PACKAGE_ROOT / "_data"  # site-packages/openharness/_data

ENV_VAR = "IMPACT_VISION_DATA_DIR"


def data_roots() -> list[Path]:
    """Return candidate data roots in resolution order (existing dirs only)."""
    roots: list[Path] = []
    env = os.environ.get(ENV_VAR)
    if env:
        roots.append(Path(env).expanduser())
    roots.extend([_REPO_DATA, _WHEEL_DATA])
    return [r for r in roots if r.is_dir()]


def data_dir() -> Path:
    """Return the first existing data root (repo ``data/`` when unresolvable)."""
    roots = data_roots()
    return roots[0] if roots else _REPO_DATA


def data_path(*parts: str) -> Path:
    """Return the path to a bundled data file or directory.

    The first root that contains the requested entry wins. When no root
    contains it, the path under :func:`data_dir` is returned so callers can
    keep their existing ``.exists()`` checks and fallbacks.
    """
    for root in data_roots():
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return candidate
    return data_dir().joinpath(*parts)
