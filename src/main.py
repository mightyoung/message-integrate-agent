"""
Message Integrate Agent - Main Entry Point
"""
import asyncio
import os
import signal
from contextlib import asynccontextmanager

from loguru import logger

from src.config import load_config
from src.gateway.websocket_server import WebSocketGateway
from src.proxy.manager import ProxyManager
from src.adapters.registry import get_adapter_registry
from src.adapters.telegram_adapter import TelegramAdapter
from src.adapters.feishu_adapter import FeishuAdapter
from src.adapters.wechat_adapter import WeChatAdapter


@asynccontextmanager
async def lifespan(app: dict):
    """Application lifespan handler."""
    logger.info("Starting Message Integrate Agent...")

    # Load configuration
    config = load_config()
    app["config"] = config
    logger.info(f"Configuration loaded: {config.gateway.host}:{config.gateway.port}")

    # Initialize proxy manager
    proxy_manager = ProxyManager()
    app["proxy_manager"] = proxy_manager
    logger.info("Proxy manager initialized")

    # Initialize adapter registry
    adapter_registry = get_adapter_registry()

    # Load feishu config first (before using it)
    feishu_config = config.feishu.model_dump()
    feishu_config["webhook_url"] = os.environ.get("FEISHU_WEBHOOK_URL")

    # Register platform adapters
    adapter_registry.register_adapter_class(
        "telegram",
        TelegramAdapter,
        config.telegram.model_dump()
    )
    adapter_registry.register_adapter_class(
        "feishu",
        FeishuAdapter,
        feishu_config
    )
    adapter_registry.register_adapter_class(
        "wechat",
        WeChatAdapter,
        config.wechat.model_dump()
    )
    logger.info(f"Registered adapters: {adapter_registry.list_adapters()}")

    # Initialize and start WebSocket gateway
    platform_configs = {
        "telegram": config.telegram.model_dump(),
        "feishu": feishu_config,
        "wechat": config.wechat.model_dump(),
    }
    gateway = WebSocketGateway(config.gateway, platform_configs, adapter_registry)
    # Pass agent pool and routers to gateway
    from src.agents.pool import AgentPool
    from src.router.keyword_router import KeywordRouter
    from src.router.ai_router import AIRouter
    from src.router.registry import AgentRegistry

    # Initialize routing components
    agent_pool = AgentPool()
    agent_registry = AgentRegistry()
    keyword_router = KeywordRouter()
    # Load AI router config from settings
    ai_router_config = {
        "model": config.llm.default_model,
        "max_tokens": config.mcp.model_dump().get("max_tokens", 200),
        "temperature": 0.3,
    }
    ai_router = AIRouter(ai_router_config)

    # Configure keyword router from settings
    keyword_router.load_from_config({
        "rules": [
            {"keywords": ["天气", "weather"], "agent": "search", "action": "weather"},
            {"keywords": ["翻译", "translate"], "agent": "llm", "action": "translate"},
            {"keywords": ["搜索", "search", "查"], "agent": "search", "action": "web_search"},
        ],
        "default": "llm"
    })

    # Wire up the gateway with routing
    gateway.set_agent_pool(agent_pool)
    gateway.set_routers(keyword_router, ai_router)
    gateway.set_agent_registry(agent_registry)
    app["gateway"] = gateway

    await gateway.start()
    logger.info("WebSocket gateway started")

    # Start MCP Server (SSE transport in background)
    from src.mcp.server import MCPServer
    mcp_config = {
        "server_name": config.mcp.server_name,
        "version": config.mcp.version,
    }
    mcp_server = MCPServer(name=config.mcp.server_name, config=mcp_config)
    app["mcp_server"] = mcp_server
    # Run MCP in background
    await mcp_server.run_sse(host="0.0.0.0", port=8081)
    logger.info(f"MCP server started on port 8081")

    # ========================================
    # Initialize and start core modules
    # ========================================

    # Heartbeat Engine - Self-evolution heartbeat
    from src.heartbeat.engine import get_heartbeat_engine
    heartbeat_engine = get_heartbeat_engine()
    await heartbeat_engine.start()
    app["heartbeat_engine"] = heartbeat_engine
    logger.info("💓 Heartbeat engine started")

    # Experience Logger - Structured learning memory
    from src.memory.experience_logger import ExperienceLogger
    experience_logger = ExperienceLogger()
    app["experience_logger"] = experience_logger
    logger.info("📚 Experience logger initialized")

    # Push Service - Active push to users
    from src.push import PushService
    push_service = PushService(adapter_registry)
    await push_service.initialize()
    app["push_service"] = push_service
    logger.info("📢 Push service initialized")

    # Agent Communicator - Agent-to-agent communication
    from src.agent_comm import get_agent_communicator, get_service_registry
    agent_communicator = get_agent_communicator()
    service_registry = get_service_registry()
    await service_registry.start_health_check()
    app["agent_communicator"] = agent_communicator
    app["service_registry"] = service_registry
    logger.info("🔗 Agent communicator initialized")

    # Feedback Service - User feedback collection
    from src.feedback import get_feedback_service
    feedback_service = get_feedback_service(experience_logger)
    app["feedback_service"] = feedback_service
    logger.info("📊 Feedback service initialized")

    # Observability Service - Metrics and monitoring
    from src.observability import get_observability_service
    observability = get_observability_service()
    app["observability"] = observability
    logger.info("📈 Observability service initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop core modules in reverse order
    if "heartbeat_engine" in app:
        await app["heartbeat_engine"].stop()
        logger.info("💓 Heartbeat engine stopped")

    if "push_service" in app:
        await app["push_service"].shutdown()
        logger.info("📢 Push service stopped")

    if "service_registry" in app:
        await app["service_registry"].stop_health_check()
        logger.info("🔗 Service registry stopped")

    await gateway.stop()
    # Stop MCP server
    if "mcp_server" in app:
        await app["mcp_server"].stop()
    logger.info("Shutdown complete")


async def main():
    """Main async entry point."""
    # Create logs directory
    from pathlib import Path
    Path("logs").mkdir(exist_ok=True)

    # Configure logging
    logger.remove()
    logger.add(
        "logs/app.log",
        rotation="100 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
    )
    logger.add(
        lambda msg: print(msg, end=""),
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
    )

    # Setup signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(sig)))

    # Run lifespan app
    app = {}
    async with lifespan(app):
        # Keep running
        await asyncio.Event().wait()


async def shutdown(sig):
    """Handle graceful shutdown."""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    # This will trigger the cleanup in lifespan
    raise asyncio.CancelledError()


if __name__ == "__main__":
    asyncio.run(main())
