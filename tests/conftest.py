"""Shared test fixtures."""

import os

# Keep consultant state (W5.3 state store) out of the developer's
# ~/.impact-vision/state.db: tests use the per-process memory backend.
os.environ.setdefault("IMPACT_VISION_STATE_STORE", "memory")
# Deterministic, offline extraction even when a developer has OPENAI_API_KEY set.
os.environ.setdefault("IMPACT_VISION_EXTRACTOR", "regex")
