"""
Tests for MessagePipeline
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.gateway.pipeline import MessagePipeline
from src.gateway.message import UnifiedMessage, Platform


class MockRouter:
    """Mock keyword router for testing."""

    def __init__(self, route_result=None):
        self.route_result = route_result or {"agent": "llm", "action": None}

    def route(self, content):
        return self.route_result


class MockAIRouter:
    """Mock AI router for testing."""

    def __init__(self, route_result=None):
        self.route_result = route_result or {"agent": "llm", "action": None}

    async def route(self, content):
        return self.route_result


class MockAgentPool:
    """Mock agent pool for testing."""

    def __init__(self, response="Mock response"):
        self.response = response

    async def route_and_handle(self, agent_name, message, action=None, context=None):
        return self.response


class MockAdapter:
    """Mock adapter for testing."""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.sent_messages = []

    def is_enabled(self):
        return self.enabled

    async def send_message(self, chat_id, content, chat_type="direct"):
        self.sent_messages.append({"chat_id": chat_id, "content": content})
        return True


class MockRegistry:
    """Mock adapter registry for testing."""

    def __init__(self, adapter=None):
        self.adapter = adapter or MockAdapter()

    def get_adapter(self, platform):
        return self.adapter


@pytest.mark.asyncio
async def test_pipeline_basic_processing():
    """Test basic message processing through pipeline."""
    pipeline = MessagePipeline(
        keyword_router=MockRouter({"agent": "llm", "action": "chat"}),
        ai_router=None,
        agent_pool=MockAgentPool("Hello!"),
        adapter_registry=None,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="Hello",
    )

    response = await pipeline.process(message)

    assert response == "Hello!"


@pytest.mark.asyncio
async def test_pipeline_keyword_routing():
    """Test pipeline uses keyword router."""
    keyword_router = MockRouter({"agent": "search", "action": "weather"})
    ai_router = MockAIRouter({"agent": "llm", "action": "chat"})

    pipeline = MessagePipeline(
        keyword_router=keyword_router,
        ai_router=ai_router,
        agent_pool=MockAgentPool("Weather: Sunny"),
        adapter_registry=None,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.FEISHU,
        user_id="user123",
        content="查天气",
    )

    response = await pipeline.process(message)

    # Should use keyword router result, not AI router
    assert response == "Weather: Sunny"


@pytest.mark.asyncio
async def test_pipeline_ai_routing_fallback():
    """Test pipeline falls back to AI router when keyword fails."""
    keyword_router = MockRouter(None)  # No keyword match
    ai_router = MockAIRouter({"agent": "llm", "action": "chat"})

    pipeline = MessagePipeline(
        keyword_router=keyword_router,
        ai_router=ai_router,
        agent_pool=MockAgentPool("AI Response"),
        adapter_registry=None,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.WECHAT,
        user_id="user123",
        content="Hello, how are you?",
    )

    response = await pipeline.process(message)

    assert response == "AI Response"


@pytest.mark.asyncio
async def test_pipeline_empty_content():
    """Test pipeline rejects empty content."""
    pipeline = MessagePipeline(
        keyword_router=None,
        ai_router=None,
        agent_pool=MockAgentPool(),
        adapter_registry=None,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="",  # Empty content
    )

    response = await pipeline.process(message)

    assert response is None


@pytest.mark.asyncio
async def test_pipeline_whitespace_content():
    """Test pipeline handles whitespace-only content."""
    pipeline = MessagePipeline(
        keyword_router=None,
        ai_router=None,
        agent_pool=MockAgentPool(),
        adapter_registry=None,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="   ",  # Whitespace only
    )

    response = await pipeline.process(message)

    assert response is None


@pytest.mark.asyncio
async def test_pipeline_sends_response_via_adapter():
    """Test pipeline sends response via adapter."""
    mock_adapter = MockAdapter(enabled=True)
    registry = MockRegistry(mock_adapter)

    pipeline = MessagePipeline(
        keyword_router=MockRouter({"agent": "llm"}),
        ai_router=None,
        agent_pool=MockAgentPool("Response text"),
        adapter_registry=registry,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="Hello",
    )

    await pipeline.process(message)

    assert len(mock_adapter.sent_messages) == 1
    assert mock_adapter.sent_messages[0]["content"] == "Response text"


@pytest.mark.asyncio
async def test_pipeline_skips_disabled_adapter():
    """Test pipeline skips sending when adapter is disabled."""
    mock_adapter = MockAdapter(enabled=False)
    registry = MockRegistry(mock_adapter)

    pipeline = MessagePipeline(
        keyword_router=MockRouter({"agent": "llm"}),
        ai_router=None,
        agent_pool=MockAgentPool("Response text"),
        adapter_registry=registry,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="Hello",
    )

    await pipeline.process(message)

    # No messages should be sent
    assert len(mock_adapter.sent_messages) == 0


@pytest.mark.asyncio
async def test_pipeline_default_agent():
    """Test pipeline uses default agent when no routing."""
    pipeline = MessagePipeline(
        keyword_router=None,
        ai_router=None,
        agent_pool=MockAgentPool("Default response"),
        adapter_registry=None,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="Random message",
    )

    response = await pipeline.process(message)

    # Should use default (llm)
    assert response == "Default response"


@pytest.mark.asyncio
async def test_pipeline_error_handling():
    """Test pipeline handles errors gracefully."""

    class FailingAgentPool:
        async def route_and_handle(self, agent_name, message, action=None, context=None):
            raise Exception("Agent failed")

    pipeline = MessagePipeline(
        keyword_router=MockRouter({"agent": "llm"}),
        ai_router=None,
        agent_pool=FailingAgentPool(),
        adapter_registry=None,
    )

    message = UnifiedMessage(
        message_id="123",
        platform=Platform.TELEGRAM,
        user_id="user123",
        content="Hello",
    )

    response = await pipeline.process(message)

    # Should return fallback message
    assert "couldn't process" in response.lower() or "apologize" in response.lower()


def test_pipeline_set_components():
    """Test updating pipeline components."""
    pipeline = MessagePipeline()

    new_keyword = MockRouter({"agent": "search"})
    new_ai = MockAIRouter({"agent": "llm"})
    new_pool = MockAgentPool("New response")
    new_registry = MockRegistry()

    pipeline.set_components(
        keyword_router=new_keyword,
        ai_router=new_ai,
        agent_pool=new_pool,
        adapter_registry=new_registry,
    )

    assert pipeline.keyword_router is new_keyword
    assert pipeline.ai_router is new_ai
    assert pipeline.agent_pool is new_pool
    assert pipeline.adapter_registry is new_registry
