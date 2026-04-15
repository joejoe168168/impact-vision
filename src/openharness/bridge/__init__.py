"""Bridge package exports."""

from __future__ import annotations

from .types import WorkSecret
from .work_secret import build_sdk_url, decode_work_secret, encode_work_secret

__all__ = [
    "BridgeSessionManager",
    "WorkSecret",
    "build_sdk_url",
    "decode_work_secret",
    "encode_work_secret",
    "get_bridge_manager",
    "spawn_session",
]


def __getattr__(name: str):
    if name == "spawn_session":
        from .session_runner import spawn_session

        return spawn_session
    if name in {"BridgeSessionManager", "get_bridge_manager"}:
        from .manager import BridgeSessionManager, get_bridge_manager

        return {"BridgeSessionManager": BridgeSessionManager, "get_bridge_manager": get_bridge_manager}[name]
    raise AttributeError(name)
