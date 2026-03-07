"""
Tests for gateway message module
"""
import pytest

from src.gateway.message import UnifiedMessage, MessageType, Platform


def test_unified_message_creation():
    """Test creating a unified message."""
    msg = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="Hello world",
    )

    assert msg.message_id == "123"
    assert msg.platform == Platform.TELEGRAM
    assert msg.user_id == "user123"
    assert msg.content == "Hello world"
    assert msg.message_type == MessageType.TEXT


def test_unified_message_to_telegram():
    """Test converting to Telegram format."""
    msg = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="Hello",
        chat_id="chat123",
    )

    formatted = msg.to_platform_format(Platform.TELEGRAM)

    assert formatted["chat_id"] == "chat123"
    assert formatted["text"] == "Hello"
    assert "parse_mode" in formatted


def test_unified_message_to_feishu():
    """Test converting to Feishu format."""
    msg = UnifiedMessage(
        message_id="123",
        platform=Platform.FEISHU,
        user_id="user123",
        content="Hello",
        chat_id="chat123",
    )

    formatted = msg.to_platform_format(Platform.FEISHU)

    assert formatted["chat_id"] == "chat123"
    assert formatted["msg_type"] == "text"
    assert formatted["content"]["text"] == "Hello"
