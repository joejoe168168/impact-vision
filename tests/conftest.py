"""Shared test fixtures."""

import os

# Keep consultant state (W5.3 state store) out of the developer's
# ~/.impact-vision/state.db: tests use the per-process memory backend.
os.environ.setdefault("IMPACT_VISION_STATE_STORE", "memory")
# Deterministic, offline extraction even when a developer has OPENAI_API_KEY set.
os.environ.setdefault("IMPACT_VISION_EXTRACTOR", "regex")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_assessment_db(tmp_path, monkeypatch):
    """Every test gets its own SQLite assessment store (pipeline, company record).

    The store is a process-wide singleton defaulting to ~/.impact-vision; without
    this, saving an assessment in a test would write to the developer's real
    database.
    """
    from openharness.impact import storage

    monkeypatch.setenv("IMPACT_VISION_DB", str(tmp_path / "impact_vision.db"))
    monkeypatch.setattr(storage, "_global_store", None)
    yield
    storage._global_store = None
