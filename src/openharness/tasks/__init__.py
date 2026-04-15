"""Task package exports."""

from __future__ import annotations

from .manager import BackgroundTaskManager, get_task_manager

__all__ = ["BackgroundTaskManager", "get_task_manager"]
