"""Small shared helpers used by optional channel integrations."""

from __future__ import annotations

import re

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def split_message(text: str, max_length: int) -> list[str]:
    """Split long chat text into chunks no longer than ``max_length``."""
    if max_length <= 0:
        raise ValueError("max_length must be positive")
    if not text:
        return []
    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_length:
        split_at = max(remaining.rfind("\n", 0, max_length + 1), remaining.rfind(" ", 0, max_length + 1))
        if split_at <= 0:
            split_at = max_length
        chunk = remaining[:split_at].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def safe_filename(name: str) -> str:
    """Return a filesystem-safe filename component."""
    cleaned = _SAFE_FILENAME_RE.sub("_", (name or "").strip()).strip("._")
    return cleaned[:160]
