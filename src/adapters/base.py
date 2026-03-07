"""
Base adapter interface for message platforms.

This module implements the adapter pattern with ChannelDock integration:
- BaseAdapter: Abstract base for all channel adapters
- AdapterMessage: Standardized message format
- Integration with ChannelCapabilities for feature declaration

设计参考:
- OpenClaw ChannelPlugin: https://github.com/openclaw/openclaw/blob/main/src/channels/plugins/types.plugin.ts
- Adapter Pattern: https://refactoring.guru/design-patterns/adapter/python/example
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.adapters.capabilities import (
    ChannelCapabilities,
    ChannelDock,
    ChatType,
    register_channel_dock,
)


class AdapterMessage(BaseModel):
    """Base message format from adapters."""
    platform: str
    message_id: str
    user_id: str
    content: str
    chat_type: str = "direct"  # direct, group, channel, thread
    raw: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class BaseAdapter(ABC):
    """
    Abstract base class for message platform adapters.

    借鉴 OpenClaw 的 ChannelPlugin 设计:
    - capabilities: Declare what features the channel supports
    - dock: Lightweight interface for fast lookups

    使用方式:
        class MyAdapter(BaseAdapter):
            @property
            def capabilities(self) -> ChannelCapabilities:
                return ChannelCapabilities(
                    chat_types=[ChatType.DIRECT, ChatType.GROUP],
                    media=True,
                    reactions=True,
                )
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the adapter with configuration.

        Args:
            config: Platform-specific configuration
        """
        self.config = config
        self.enabled = config.get("enabled", False)
        self._dock: Optional[ChannelDock] = None

    @property
    @abstractmethod
    def capabilities(self) -> ChannelCapabilities:
        """
        Return channel capabilities.

        This property must be implemented by all adapters to declare
        what features the channel supports.

        Returns:
            ChannelCapabilities: The capabilities of this channel
        """
        pass

    @property
    def dock(self) -> ChannelDock:
        """
        Get the ChannelDock for this adapter.

        Lazy-loads the dock on first access.

        Returns:
            ChannelDock: The lightweight dock interface
        """
        if self._dock is None:
            self._dock = ChannelDock(
                id=self.platform_id,
                capabilities=self.capabilities,
            )
            register_channel_dock(self._dock)
        return self._dock

    @property
    @abstractmethod
    def platform_id(self) -> str:
        """
        Return the platform identifier.

        Returns:
            str: Unique platform ID (e.g., 'telegram', 'feishu', 'discord')
        """
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the messaging platform.

        Returns:
            True if connected successfully
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from the messaging platform."""
        pass

    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        content: str,
        chat_type: str = "direct",
        **kwargs
    ) -> bool:
        """
        Send a message to a chat.

        Args:
            chat_id: The target chat ID
            content: Message content
            chat_type: Type of chat (direct, group, channel, thread)
            **kwargs: Additional platform-specific parameters

        Returns:
            True if sent successfully
        """
        pass

    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[AdapterMessage]:
        """
        Get a message by ID.

        Args:
            message_id: The message ID

        Returns:
            The message or None if not found
        """
        pass

    async def handle_webhook(self, payload: Dict[str, Any]) -> Optional[AdapterMessage]:
        """
        Handle incoming webhook payload.

        Default implementation - override in subclasses for custom handling.

        Args:
            payload: Webhook payload

        Returns:
            Parsed message or None
        """
        # Default implementation - override in subclasses
        return None

    async def handle_polling(self) -> list[AdapterMessage]:
        """
        Handle polling for new messages.

        Override in subclasses that support polling mode.

        Returns:
            List of new messages
        """
        # Default: return empty list (webhook-only channels)
        return []

    def is_enabled(self) -> bool:
        """Check if adapter is enabled."""
        return self.enabled

    async def health_check(self) -> dict:
        """
        Check the health status of the adapter.

        Returns:
            dict: Health status with keys:
                - healthy: bool
                - message: str
                - details: dict (optional)
        """
        return {
            "healthy": self.enabled,
            "message": "Enabled" if self.enabled else "Disabled",
            "platform": self.platform_id,
        }

    def supports_feature(self, feature: str) -> bool:
        """
        Check if the channel supports a specific feature.

        Args:
            feature: Feature name (e.g., 'media', 'reactions', 'polls')

        Returns:
            True if the feature is supported
        """
        return self.capabilities.supports(feature)

    def can_send_to(self, chat_type: str) -> bool:
        """
        Check if the channel can send to a specific chat type.

        Args:
            chat_type: Chat type (direct, group, channel, thread)

        Returns:
            True if the chat type is supported
        """
        try:
            return ChatType(chat_type) in self.capabilities.chat_types
        except ValueError:
            return False
