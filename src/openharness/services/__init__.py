"""Service package exports.

Re-exports compaction/summarization functions from services.compact and
token estimation helpers from services.token_estimation.
"""

from __future__ import annotations

from .token_estimation import estimate_message_tokens, estimate_tokens

__all__ = [
    "build_post_compact_messages",
    "compact_conversation",
    "compact_messages",
    "estimate_conversation_tokens",
    "estimate_message_tokens",
    "estimate_tokens",
    "summarize_messages",
]


def __getattr__(name: str):
    """Lazy re-export compaction functions to avoid heavy transitive imports."""
    _compact_names = {
        "build_post_compact_messages",
        "compact_conversation",
        "compact_messages",
        "estimate_conversation_tokens",
        "summarize_messages",
    }
    if name in _compact_names:
        from openharness.services.compact import (
            build_post_compact_messages,
            compact_conversation,
            compact_messages,
            estimate_conversation_tokens,
            summarize_messages,
        )

        return {
            "build_post_compact_messages": build_post_compact_messages,
            "compact_conversation": compact_conversation,
            "compact_messages": compact_messages,
            "estimate_conversation_tokens": estimate_conversation_tokens,
            "summarize_messages": summarize_messages,
        }[name]
    raise AttributeError(name)
