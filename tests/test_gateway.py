"""
Integration tests for WebSocket Gateway
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.config import GatewayConfig
from src.gateway.websocket_server import WebSocketGateway


@pytest.fixture
def gateway_config():
    """Create a test gateway config."""
    return GatewayConfig(
        host="127.0.0.1",
        port=8080,
    )


@pytest.fixture
def platform_configs():
    """Create test platform configs."""
    return {
        "telegram": {"bot_token": "test_token"},
        "feishu": {"app_id": "test_app", "app_secret": "test_secret"},
        "wechat": {"webhook_url": "https://example.com/webhook"},
    }


@pytest.fixture
def gateway(gateway_config, platform_configs):
    """Create a test gateway."""
    return WebSocketGateway(gateway_config, platform_configs)


def test_gateway_initialization(gateway, gateway_config):
    """Test gateway initializes correctly."""
    assert gateway.host == gateway_config.host
    assert gateway.port == gateway_config.port
    assert gateway.platform_configs is not None


def test_gateway_has_app(gateway):
    """Test gateway has FastAPI app."""
    assert gateway.app is not None
    assert hasattr(gateway.app, 'routes')


def test_gateway_health_endpoint(gateway):
    """Test health endpoint returns ok."""
    client = TestClient(gateway.app)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "message-hub-gateway"


def test_gateway_detailed_health_endpoint(gateway):
    """Test detailed health endpoint."""
    client = TestClient(gateway.app)

    response = client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert "gateway" in data
    assert "routing" in data
    assert "adapters" in data


def test_gateway_errors_endpoint(gateway):
    """Test errors endpoint."""
    client = TestClient(gateway.app)

    response = client.get("/errors")

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "recent" in data


def test_gateway_rate_limiter_initialized(gateway):
    """Test rate limiter is initialized."""
    assert gateway.rate_limiter is not None
    assert hasattr(gateway.rate_limiter, 'check')


def test_gateway_connections_tracking(gateway):
    """Test connections are tracked."""
    assert isinstance(gateway.connections, dict)


def test_gateway_session_manager(gateway):
    """Test session manager is initialized."""
    assert gateway.session_manager is not None


def test_gateway_set_agent_pool(gateway):
    """Test setting agent pool."""
    mock_pool = MagicMock()

    gateway.set_agent_pool(mock_pool)

    assert gateway.agent_pool is mock_pool


def test_gateway_set_routers(gateway):
    """Test setting routers."""
    mock_keyword = MagicMock()
    mock_ai = AsyncMock()

    gateway.set_routers(mock_keyword, mock_ai)

    assert gateway.keyword_router is mock_keyword
    assert gateway.ai_router is mock_ai


def test_gateway_set_agent_registry(gateway):
    """Test setting agent registry."""
    mock_registry = MagicMock()

    gateway.set_agent_registry(mock_registry)

    assert gateway.agent_registry is mock_registry


def test_gateway_pipeline_initialized(gateway):
    """Test message pipeline is initialized."""
    assert gateway.pipeline is not None


@pytest.mark.asyncio
async def test_gateway_process_platform_message(gateway):
    """Test processing platform message."""
    # Create mock message
    from src.adapters.base import AdapterMessage

    message = AdapterMessage(
        platform="telegram",
        message_id="123",
        user_id="user123",
        content="Hello",
    )

    # Should not raise
    await gateway._process_platform_message(message)


@pytest.mark.asyncio
async def test_gateway_send_to_client(gateway):
    """Test sending to client."""
    mock_websocket = AsyncMock()

    gateway.connections["test_client"] = mock_websocket

    await gateway._send_to_client("test_client", {"type": "test"})

    mock_websocket.send_json.assert_called_once()


@pytest.mark.asyncio
async def test_gateway_send_to_nonexistent_client(gateway):
    """Test sending to nonexistent client doesn't raise."""
    # Should not raise
    await gateway._send_to_client("nonexistent", {"type": "test"})


def test_gateway_webhook_endpoints_exist(gateway):
    """Test webhook endpoints are registered."""
    client = TestClient(gateway.app)

    # These should exist (even if they return errors)
    response = client.post("/webhook/telegram", json={})
    assert response.status_code in [200, 400, 500]

    response = client.post("/webhook/feishu", json={})
    assert response.status_code in [200, 400, 429, 500]

    response = client.post("/webhook/wechat", json={})
    assert response.status_code in [200, 400, 429, 500]


def test_gateway_rate_limiting_works(gateway):
    """Test rate limiting works on webhooks."""
    client = TestClient(gateway.app)

    # Make many requests to trigger rate limiting
    for _ in range(35):
        response = client.post("/webhook/feishu", json={})

    # Should eventually be rate limited
    assert response.status_code == 429


def test_gateway_loopback_exempt_from_rate_limit(gateway):
    """Test loopback is exempt from rate limiting."""
    # This is handled by the rate limiter itself
    # We just verify the config is set correctly
    assert gateway.rate_limiter.config.exempt_loopback is True


def test_gateway_websocket_endpoint_exists(gateway):
    """Test WebSocket endpoint exists."""
    # Just verify the route is registered
    routes = [r.path for r in gateway.app.routes]
    assert any("/ws/" in r for r in routes)
