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
    # 添加连接模式配置: webhook 或 websocket
    feishu_config["connection_mode"] = os.environ.get("FEISHU_CONNECTION_MODE", "webhook")

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

    # 注册网关到飞书适配器 (用于处理 WebSocket 消息)
    from src.adapters.feishu_adapter import set_gateway
    set_gateway(gateway)

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

    # Initialize Agent system components for deep processing
    from src.agents.checkpoint import CheckpointManager
    from src.agents.loop import AgentLoop

    checkpoint_manager = CheckpointManager(
        db_path=".learnings/checkpoints.db",
        max_checkpoints=100,
    )

    agent_loop = AgentLoop(
        max_iterations=10,
        timeout_seconds=300.0,
    )

    # Wire up the gateway with routing
    gateway.set_agent_pool(agent_pool)
    gateway.set_routers(keyword_router, ai_router)
    gateway.set_agent_registry(agent_registry)
    gateway.set_agent_loop(agent_loop, checkpoint_manager)
    app["gateway"] = gateway
    app["checkpoint_manager"] = checkpoint_manager
    app["agent_loop"] = agent_loop

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

    # Register feedback routes with gateway
    gateway.set_feedback_service(feedback_service)

    # Feedback Loop - AI-driven feedback processing
    from src.feedback import FeedbackLoop
    feedback_loop = FeedbackLoop(
        feedback_service=feedback_service,
        experience_logger=experience_logger,
        agent_loop=agent_loop,
        keyword_router=keyword_router,
    )
    app["feedback_loop"] = feedback_loop
    logger.info("🔄 FeedbackLoop initialized")

    # Observability Service - Metrics and monitoring
    from src.observability import get_observability_service
    observability = get_observability_service()
    app["observability"] = observability
    logger.info("📈 Observability service initialized")

    # ========================================
    # Agent System - Roles, Enforcer
    # ========================================

    # Agent Collaboration System - Multi-role orchestration
    from src.agents.roles import AgentCollaborationSystem
    collaboration_system = AgentCollaborationSystem()
    app["collaboration_system"] = collaboration_system
    logger.info("🤝 Agent collaboration system initialized")

    # TodoEnforcer - Task monitoring
    from src.agents.enforcer import TodoEnforcer
    todo_enforcer = TodoEnforcer()
    await todo_enforcer.start_monitoring()
    app["todo_enforcer"] = todo_enforcer
    logger.info("✅ TodoEnforcer initialized")

    # ========================================
    # Intelligence Pipeline - 情报处理流水线
    # ========================================

    # Intelligence Pipeline - 基于 TrendRadar 的情报获取与分析
    from src.intelligence.pipeline import IntelligencePipeline
    from src.intelligence.scorer import UserProfile

    cfg = app["config"]

    # 检查是否启用 WorldMonitor
    worldmonitor_enabled = os.environ.get("WORLDMONITOR_ENABLED", "false").lower() == "true"

    # 初始化 Intelligence Pipeline (失败时跳过)
    intelligence_pipeline = None
    try:
        intelligence_pipeline = IntelligencePipeline(
            config={
                "platforms": ["weibo", "zhihu", "bilibili"],
                "llm_model": cfg.llm.default_model,
                "default_channels": ["feishu"],
                # RSS 配置 - 支持所有分类 (geopolitics, military, cyber, tech, finance, science, china, social)
                "rss_enabled": True,
                "rss_categories": ["geopolitics", "military", "cyber", "tech", "finance", "science"],
                "rss_lang": "en",
                "rss_max_tier": 2,
                # WorldMonitor 配置
                "worldmonitor_enabled": worldmonitor_enabled,
                "worldmonitor_api_url": os.environ.get("WORLDMONITOR_API_URL", "https://worldmonitor.app"),
                "worldmonitor_api_key": os.environ.get("WORLDMONITOR_API_KEY", ""),
                "worldmonitor_categories": ["geopolitics", "military", "economy", "tech"],
            }
        )
        # 注册默认用户画像（可以从数据库加载）
        intelligence_pipeline.register_user(
            UserProfile(
                user_id="default",
                interests=["AI", "科技", "互联网", "大模型"],
                preferred_categories=["AI突破", "产品发布", "行业动态"],
                notification_channels=["feishu"],
                notify_frequency="daily",
            )
        )
        app["intelligence_pipeline"] = intelligence_pipeline
        logger.info("📊 Intelligence pipeline initialized")
    except Exception as e:
        logger.warning(f"Intelligence pipeline 初始化失败，跳过: {e}")
        intelligence_pipeline = None

    app["intelligence_pipeline"] = intelligence_pipeline

    # Connect IntelligencePipeline to Heartbeat (if initialized)
    if intelligence_pipeline:
        from src.heartbeat.engine import HeartbeatStep
        intelligence_task = heartbeat_engine.tasks.get(HeartbeatStep.INTELLIGENCE_GATHERING)
        if intelligence_task:
            intelligence_task.set_pipeline(intelligence_pipeline)
            logger.info("🔗 Intelligence pipeline connected to Heartbeat")

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

    # Stop agent system
    if "todo_enforcer" in app:
        await app["todo_enforcer"].stop_monitoring()
        logger.info("✅ TodoEnforcer stopped")

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
