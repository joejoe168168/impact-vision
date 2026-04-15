"""Session routing for ohmo gateway."""

from __future__ import annotations

from openharness.channels.bus.events import InboundMessage


def session_key_for_message(message: InboundMessage) -> str:
    """Route sessions by chat and thread when available."""
    if message.session_key_override:
        return message.session_key_override
    thread_id = (
        message.metadata.get("thread_id")
        or message.metadata.get("thread_ts")
        or message.metadata.get("message_thread_id")
    )
    if thread_id:
        return f"{message.channel}:{message.chat_id}:{thread_id}"
    return f"{message.channel}:{message.chat_id}"

