"""
Message platform adapters

This module provides adapters for various messaging platforms:
- Telegram
- Feishu (飞书)
- WeChat (企业微信)

The adapter system uses the ChannelDock pattern:
- BaseAdapter: Abstract base for all adapters
- ChannelCapabilities: Feature declaration
- AdapterRegistry: Central registry for adapters

设计参考: OpenClaw Channel System
"""
from src.adapters.base import BaseAdapter, AdapterMessage
from src.adapters.capabilities import (
    ChannelCapabilities,
    ChannelDock,
    ChatType,
    StandardCapabilities,
    get_channel_registry,
    register_channel_dock,
)
from src.adapters.registry import (
    AdapterRegistry,
    get_adapter_registry,
    register_adapter,
    get_adapter,
)

# Import adapters for convenience
from src.adapters.telegram_adapter import TelegramAdapter
from src.adapters.feishu_adapter import FeishuAdapter
from src.adapters.wechat_adapter import WeChatAdapter

__all__ = [
    # Base classes
    "BaseAdapter",
    "AdapterMessage",
    # Capabilities
    "ChannelCapabilities",
    "ChannelDock",
    "ChatType",
    "StandardCapabilities",
    "get_channel_registry",
    "register_channel_dock",
    # Registry
    "AdapterRegistry",
    "get_adapter_registry",
    "register_adapter",
    "get_adapter",
    # Adapters
    "TelegramAdapter",
    "FeishuAdapter",
    "WeChatAdapter",
]
