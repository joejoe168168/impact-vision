"""Deprecated alias of :mod:`openharness.impact.frameworks.sfdr_recast` (SFDR 2.0 Commission-proposal classifier; renamed in v7 W5.4, removed in 0.18)."""

from __future__ import annotations

import warnings

from openharness.impact.frameworks.sfdr_recast import *  # noqa: F403
from openharness.impact.frameworks.sfdr_recast import __all__  # noqa: F401

warnings.warn(
    "openharness.impact.frameworks.sfdr_v2 is deprecated; import openharness.impact.frameworks.sfdr_recast instead.",
    DeprecationWarning,
    stacklevel=2,
)
