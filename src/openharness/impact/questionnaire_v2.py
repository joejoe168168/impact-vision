"""Deprecated alias of :mod:`openharness.impact.questionnaire_branching` (conditional DD questionnaire; renamed in v7 W5.4, removed in 0.18)."""

from __future__ import annotations

import warnings

from openharness.impact.questionnaire_branching import *  # noqa: F403
from openharness.impact.questionnaire_branching import __all__  # noqa: F401

warnings.warn(
    "openharness.impact.questionnaire_v2 is deprecated; import openharness.impact.questionnaire_branching instead.",
    DeprecationWarning,
    stacklevel=2,
)
