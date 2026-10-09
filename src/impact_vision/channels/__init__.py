"""OpenHarness channels subsystem.

Provides a message-bus architecture for integrating chat platforms
(Telegram, Discord, Slack, etc.) with the OpenHarness query engine.

Usage::

    from impact_vision.channels import BaseChannel, ChannelManager, MessageBus
"""

from impact_vision.channels.bus.events import InboundMessage, OutboundMessage
from impact_vision.channels.bus.queue import MessageBus
from impact_vision.channels.impl.base import BaseChannel
from impact_vision.channels.impl.manager import ChannelManager

__all__ = [
    "BaseChannel",
    "ChannelManager",
    "InboundMessage",
    "MessageBus",
    "OutboundMessage",
]
