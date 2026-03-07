"""
Unified message format for all platforms
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message types."""
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    LINK = "link"
    BUTTON = "button"
    QUICK_REPLY = "quick_reply"


class Platform(str, Enum):
    """Supported platforms."""
    TELEGRAM = "telegram"
    FEISHU = "feishu"
    WECHAT = "wechat"
    INTERNAL = "internal"


class UnifiedMessage(BaseModel):
    """
    Unified message format that normalizes messages from different platforms.
    """
    # Unique identifier
    message_id: str
    platform: Platform

    # Sender information
    user_id: str
    user_name: Optional[str] = None

    # Message content
    content: str
    message_type: MessageType = MessageType.TEXT

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    raw: dict[str, Any] = Field(default_factory=dict)

    # Chat information
    chat_id: Optional[str] = None
    chat_type: str = "private"  # private, group, channel

    # Reply context
    reply_to_message_id: Optional[str] = None

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_platform_format(self, platform: Platform) -> dict[str, Any]:
        """Convert unified message to platform-specific format."""
        if platform == Platform.TELEGRAM:
            return {
                "chat_id": self.chat_id,
                "text": self.content,
                "parse_mode": "Markdown",
            }
        elif platform == Platform.FEISHU:
            return {
                "chat_id": self.chat_id,
                "msg_type": "text",
                "content": {"text": self.content},
            }
        elif platform == Platform.WECHAT:
            return {
                "msgtype": "text",
                "text": {"content": self.content},
            }
        else:
            return {"text": self.content}


class MessageResponse(BaseModel):
    """Response message."""
    success: bool
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
