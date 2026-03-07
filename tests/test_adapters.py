"""
Tests for adapter registry and base adapter functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.adapters.base import BaseAdapter, AdapterMessage
from src.adapters.capabilities import ChannelCapabilities, ChatType
from src.adapters.registry import AdapterRegistry


class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""

    def __init__(self, config: dict = None):
        super().__init__(config or {})
        self._enabled = config.get("enabled", True) if config else True

    @property
    def platform_id(self) -> str:
        return "mock"

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            media=True,
            reactions=False,
        )

    async def connect(self) -> bool:
        return self._enabled

    async def disconnect(self):
        pass

    async def send_message(
        self,
        chat_id: str,
        content: str,
        chat_type: str = "direct",
        **kwargs
    ) -> bool:
        return True

    async def get_message(self, message_id: str) -> AdapterMessage:
        return None


def test_adapter_message_creation():
    """Test creating an adapter message."""
    msg = AdapterMessage(
        platform="telegram",
        message_id="msg123",
        user_id="user456",
        content="Hello world",
    )

    assert msg.platform == "telegram"
    assert msg.message_id == "msg123"
    assert msg.user_id == "user456"
    assert msg.content == "Hello world"
    assert msg.chat_type == "direct"


def test_adapter_message_with_metadata():
    """Test adapter message with metadata."""
    msg = AdapterMessage(
        platform="feishu",
        message_id="msg123",
        user_id="user456",
        content="Hello",
        metadata={"chat_id": "chat789", "msg_type": "text"},
    )

    assert msg.metadata["chat_id"] == "chat789"
    assert msg.metadata["msg_type"] == "text"


def test_adapter_registry_register_class():
    """Test registering an adapter class."""
    registry = AdapterRegistry()

    registry.register_adapter_class("test", MockAdapter, {"enabled": True})

    assert registry.has_adapter("test")
    assert "test" in registry.list_adapters()


def test_adapter_registry_lazy_loading():
    """Test lazy loading of adapters."""
    registry = AdapterRegistry()

    registry.register_adapter_class("lazy", MockAdapter, {"enabled": True})

    # Adapter should not be created yet
    assert "lazy" not in registry.list_active_adapters()

    # Get adapter should create it
    adapter = registry.get_adapter("lazy")

    assert adapter is not None
    assert "lazy" in registry.list_active_adapters()


def test_adapter_registry_get_nonexistent():
    """Test getting a non-existent adapter."""
    registry = AdapterRegistry()

    adapter = registry.get_adapter("nonexistent")

    assert adapter is None


def test_adapter_registry_capabilities():
    """Test getting adapter capabilities."""
    registry = AdapterRegistry()

    registry.register_adapter_class("test", MockAdapter, {})

    caps = registry.get_capabilities("test")

    assert caps is not None
    assert ChatType.DIRECT.value in caps["chat_types"]
    assert ChatType.GROUP.value in caps["chat_types"]
    assert caps["media"] is True


def test_adapter_registry_remove():
    """Test removing an adapter."""
    registry = AdapterRegistry()

    registry.register_adapter_class("test", MockAdapter, {})
    adapter = registry.get_adapter("test")

    assert registry.has_adapter("test")

    registry.remove_adapter("test")

    # Instance should be removed but class registration remains
    assert "test" not in registry.list_active_adapters()


def test_adapter_registry_remove_class():
    """Test removing adapter class completely."""
    registry = AdapterRegistry()

    registry.register_adapter_class("test", MockAdapter, {})

    assert registry.has_adapter("test")

    # Remove instance
    registry.remove_adapter("test")

    # Now re-register to remove class
    del registry._adapter_classes["test"]
    del registry._adapter_configs["test"]

    assert not registry.has_adapter("test")


@pytest.mark.asyncio
async def test_adapter_registry_connect_all():
    """Test connecting all adapters."""
    registry = AdapterRegistry()

    registry.register_adapter_class("test1", MockAdapter, {"enabled": True})
    registry.register_adapter_class("test2", MockAdapter, {"enabled": False})

    results = await registry.connect_all()

    assert results["test1"] is True
    assert results["test2"] is False


@pytest.mark.asyncio
async def test_adapter_health_check():
    """Test adapter health check."""
    adapter = MockAdapter({"enabled": True})

    health = await adapter.health_check()

    assert health["healthy"] is True
    assert health["platform"] == "mock"


@pytest.mark.asyncio
async def test_adapter_health_check_disabled():
    """Test adapter health check for disabled adapter."""
    adapter = MockAdapter({"enabled": False})

    health = await adapter.health_check()

    assert health["healthy"] is False


@pytest.mark.asyncio
async def test_registry_health_check_all():
    """Test registry health check for all adapters."""
    registry = AdapterRegistry()

    registry.register_adapter_class("test1", MockAdapter, {"enabled": True})
    registry.register_adapter_class("test2", MockAdapter, {"enabled": False})

    results = await registry.health_check_all()

    assert "test1" in results
    assert "test2" in results
    assert results["test1"]["healthy"] is True
    assert results["test2"]["healthy"] is False


def test_base_adapter_supports_feature():
    """Test supports_feature method."""
    adapter = MockAdapter()

    assert adapter.supports_feature("media") is True
    assert adapter.supports_feature("reactions") is False


def test_base_adapter_can_send_to():
    """Test can_send_to method."""
    adapter = MockAdapter()

    assert adapter.can_send_to("direct") is True
    assert adapter.can_send_to("group") is True
    assert adapter.can_send_to("channel") is False
