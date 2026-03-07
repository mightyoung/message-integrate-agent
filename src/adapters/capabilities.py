"""
Channel capabilities and channel dock system.

This module implements the ChannelDock pattern inspired by OpenClaw:
- ChannelCapabilities: Declare what features each channel supports
- ChannelDock: Lightweight interface for fast lookups
- ChannelAdapter: Full implementation for actual messaging

参考 OpenClaw 设计模式: https://github.com/openclaw/openclaw
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ChatType(str, Enum):
    """Chat type enumeration."""
    DIRECT = "direct"
    GROUP = "group"
    CHANNEL = "channel"
    THREAD = "thread"


@dataclass
class ChannelCapabilities:
    """
    Channel capabilities declaration.

    借鉴 OpenClaw 的 ChannelCapabilities 设计:
    https://github.com/openclaw/openclaw/blob/main/src/channels/plugins/types.core.ts#L171
    """
    # Required: chat types supported
    chat_types: list[ChatType] = field(default_factory=list)

    # Optional: feature flags
    polls: bool = False
    reactions: bool = False
    edit: bool = False
    unsend: bool = False
    reply: bool = False
    effects: bool = False
    group_management: bool = False
    threads: bool = False
    media: bool = False
    native_commands: bool = False
    block_streaming: bool = False

    # Outbound configuration
    text_chunk_limit: int = 4000
    max_media_size: int = 10 * 1024 * 1024  # 10MB

    # Reception modes
    supports_webhook: bool = True
    supports_polling: bool = False
    supports_long_polling: bool = False

    def supports(self, feature: str) -> bool:
        """Check if channel supports a specific feature."""
        return getattr(self, feature, False)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "chat_types": [ct.value for ct in self.chat_types],
            "polls": self.polls,
            "reactions": self.reactions,
            "edit": self.edit,
            "unsend": self.unsend,
            "reply": self.reply,
            "effects": self.effects,
            "group_management": self.group_management,
            "threads": self.threads,
            "media": self.media,
            "native_commands": self.native_commands,
            "block_streaming": self.block_streaming,
            "text_chunk_limit": self.text_chunk_limit,
            "max_media_size": self.max_media_size,
            "supports_webhook": self.supports_webhook,
            "supports_polling": self.supports_polling,
            "supports_long_polling": self.supports_long_polling,
        }


@dataclass
class ChannelDock:
    """
    Lightweight channel dock interface.

    借鉴 OpenClaw 的 ChannelDock 设计:
    https://github.com/openclaw/openclaw/blob/main/src/channels/dock.ts#L56

    This provides a lightweight interface for:
    - Fast capability lookups
    - Configuration resolution
    - Without loading full adapter implementation
    """
    # Channel identifier
    id: str

    # Channel capabilities (required)
    capabilities: ChannelCapabilities

    # Optional: command adapter
    commands: Optional[dict] = None

    # Optional: outbound configuration
    outbound: Optional[dict] = None

    # Optional: streaming configuration
    streaming: Optional[dict] = None

    # Optional: config resolution
    config: Optional[dict] = None

    # Optional: group policy
    groups: Optional[dict] = None

    # Optional: mentions handling
    mentions: Optional[dict] = None

    # Optional: threading
    threading: Optional[dict] = None

    @classmethod
    def create(cls, channel_id: str, capabilities: ChannelCapabilities, **kwargs) -> "ChannelDock":
        """Factory method to create a ChannelDock."""
        return cls(
            id=channel_id,
            capabilities=capabilities,
            **{k: v for k, v in kwargs.items() if v is not None}
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "capabilities": self.capabilities.to_dict(),
            "commands": self.commands,
            "outbound": self.outbound,
            "streaming": self.streaming,
            "config": self.config,
            "groups": self.groups,
            "mentions": self.mentions,
            "threading": self.threading,
        }


# Predefined capability sets for common channel types
class StandardCapabilities:
    """Standard capability presets for common channel types."""

    # Basic text messaging only
    BASIC = ChannelCapabilities(
        chat_types=[ChatType.DIRECT, ChatType.GROUP],
        text_chunk_limit=4000,
    )

    # Rich messaging with media
    RICH = ChannelCapabilities(
        chat_types=[ChatType.DIRECT, ChatType.GROUP, ChatType.CHANNEL],
        media=True,
        reactions=True,
        reply=True,
        text_chunk_limit=4000,
    )

    # Full-featured (like Telegram, Discord)
    FULL = ChannelCapabilities(
        chat_types=[ChatType.DIRECT, ChatType.GROUP, ChatType.CHANNEL, ChatType.THREAD],
        polls=True,
        reactions=True,
        edit=True,
        unsend=True,
        reply=True,
        effects=True,
        group_management=True,
        threads=True,
        media=True,
        native_commands=True,
        block_streaming=True,
        text_chunk_limit=4096,
    )

    # Enterprise (like Slack, Microsoft Teams)
    ENTERPRISE = ChannelCapabilities(
        chat_types=[ChatType.DIRECT, ChatType.GROUP, ChatType.CHANNEL, ChatType.THREAD],
        polls=True,
        reactions=True,
        edit=True,
        threads=True,
        media=True,
        native_commands=True,
        block_streaming=True,
        text_chunk_limit=30000,
    )


# Registry for channel docks
class ChannelDockRegistry:
    """
    Registry for ChannelDock instances.

    Provides fast lookup of channel capabilities without
    loading full adapter implementations.
    """

    def __init__(self):
        self._docks: dict[str, ChannelDock] = {}

    def register(self, dock: ChannelDock) -> None:
        """Register a channel dock."""
        self._docks[dock.id] = dock

    def get(self, channel_id: str) -> Optional[ChannelDock]:
        """Get a channel dock by ID."""
        return self._docks.get(channel_id)

    def list_all(self) -> list[ChannelDock]:
        """List all registered docks."""
        return list(self._docks.values())

    def has_channel(self, channel_id: str) -> bool:
        """Check if a channel is registered."""
        return channel_id in self._docks

    def get_capabilities(self, channel_id: str) -> Optional[ChannelCapabilities]:
        """Get capabilities for a channel."""
        dock = self.get(channel_id)
        return dock.capabilities if dock else None


# Global registry instance
_global_registry: Optional[ChannelDockRegistry] = None


def get_channel_registry() -> ChannelDockRegistry:
    """Get the global channel registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ChannelDockRegistry()
    return _global_registry


def register_channel_dock(dock: ChannelDock) -> None:
    """Register a channel dock to the global registry."""
    get_channel_registry().register(dock)
