"""Shared test fixtures."""

import os

# Keep consultant state (W5.3 state store) out of the developer's
# ~/.impact-vision/state.db: tests use the per-process memory backend.
os.environ.setdefault("IMPACT_VISION_STATE_STORE", "memory")
