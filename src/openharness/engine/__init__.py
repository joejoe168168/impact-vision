"""Engine package exports.

QueryEngine is lazy-loaded to avoid a circular import:
engine.query_engine -> api.client -> engine.messages -> engine (if eager)
"""

from __future__ import annotations

__all__ = ["QueryEngine"]


def __getattr__(name: str):
    if name == "QueryEngine":
        from .query_engine import QueryEngine

        return QueryEngine
    raise AttributeError(name)
