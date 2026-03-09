"""
WebSocket Gateway Server
"""
import asyncio
import json
from typing import Any, Callable, Dict, Set

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from loguru import logger

from src.gateway.message import MessageResponse, UnifiedMessage
from src.gateway.session import SessionManager
from src.gateway.rate_limiter import RateLimiter, RateLimitConfig
from src.gateway.pipeline import MessagePipeline
from src.config import GatewayConfig


class WebSocketGateway:
    """
    WebSocket gateway for handling client connections and message routing.
    """

    def __init__(self, config: GatewayConfig, platform_configs: dict = None, adapter_registry=None):
        """
        Initialize the WebSocket gateway.

        Args:
            config: Gateway configuration
            platform_configs: Platform configurations dict
            adapter_registry: Adapter registry for managing platform adapters
        """
        self.config = config
        self.host = config.host
        self.port = config.port
        self.platform_configs = platform_configs or {}
        self.adapter_registry = adapter_registry

        # Initialize rate limiter for webhook protection
        self.rate_limiter = RateLimiter(RateLimitConfig(
            max_attempts=30,  # 30 requests per minute per client
            window_ms=60_000,
            lockout_ms=300_000,  # 5 minute lockout
            exempt_loopback=True,
        ))

        self.app = FastAPI(
            title="Message Hub Gateway",
            description="AI-powered message hub with intelligent task routing",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )

        # Setup error handlers
        from src.error_handling import setup_error_handlers
        setup_error_handlers(self.app)
        self.connections: Dict[str, WebSocket] = {}
        self.session_manager = SessionManager()

        # Routing components
        self.agent_pool = None
        self.keyword_router = None
        self.ai_router = None
        self.agent_registry = None
        self.agent_loop = None
        self.checkpoint_manager = None
        self.feedback_service = None
        self.pipeline = MessagePipeline(
            keyword_router=None,
            ai_router=None,
            agent_pool=None,
            adapter_registry=adapter_registry,
            agent_loop=None,
            checkpoint_manager=None,
        )

        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes."""
        from fastapi import Request
        from fastapi.responses import JSONResponse

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "ok",
                "service": "message-hub-gateway",
                "version": "1.0.0",
            }

        @self.app.get("/health/detailed")
        async def detailed_health():
            """Detailed health check with component status."""
            import os

            # Get adapter health status
            adapter_health = {}
            if self.adapter_registry:
                try:
                    adapter_health = await self.adapter_registry.health_check_all()
                except Exception as e:
                    adapter_health = {"error": str(e)}

            status = {
                "status": "ok",
                "gateway": {
                    "host": self.host,
                    "port": self.port,
                    "connections": len(self.connections),
                },
                "routing": {
                    "keyword_router": self.keyword_router is not None,
                    "ai_router": self.ai_router is not None,
                    "agent_pool": self.agent_pool is not None,
                },
                "adapters": adapter_health,
                "environment": {
                    "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
                    "tavily_key": bool(os.environ.get("TAVILY_API_KEY")),
                    "proxy": bool(os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")),
                }
            }
            return status

        @self.app.get("/errors")
        async def get_errors():
            """Get error summary and recent errors."""
            from src.error_handling import error_tracker
            return {
                "summary": error_tracker.get_error_summary(),
                "recent": error_tracker.get_recent_errors(20),
            }

        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await self._handle_connection(websocket, client_id)

        # Telegram Webhook
        @self.app.post("/webhook/telegram")
        async def telegram_webhook(request: Request):
            try:
                payload = await request.json()
                from src.adapters.telegram_adapter import TelegramAdapter
                telegram_config = self.platform_configs.get("telegram", {})
                adapter = TelegramAdapter(telegram_config)
                message = await adapter.handle_webhook(payload)
                if message:
                    await self._process_platform_message(message)
                return {"ok": True}
            except Exception as e:
                logger.error(f"Telegram webhook error: {e}")
                return {"ok": False, "error": str(e)}

        # Feishu Webhook
        @self.app.post("/webhook/feishu")
        async def feishu_webhook(request: Request):
            # Get client IP for rate limiting
            client_ip = request.client.host if request.client else "unknown"

            # Check rate limit
            rate_check = self.rate_limiter.check(client_ip)
            if not rate_check["allowed"]:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "retry_after_ms": rate_check["retry_after_ms"]
                    }
                )

            try:
                payload = await request.json()
                from src.adapters.feishu_adapter import FeishuAdapter
                feishu_config = self.platform_configs.get("feishu", {})
                adapter = FeishuAdapter(feishu_config)
                message = await adapter.handle_webhook(payload)
                if message:
                    await self._process_platform_message(message)
                return {"ok": True}
            except Exception as e:
                logger.error(f"Feishu webhook error: {e}")
                return {"ok": False, "error": str(e)}

        # WeChat Webhook
        @self.app.post("/webhook/wechat")
        async def wechat_webhook(request: Request):
            # Get client IP for rate limiting
            client_ip = request.client.host if request.client else "unknown"

            # Check rate limit
            rate_check = self.rate_limiter.check(client_ip)
            if not rate_check["allowed"]:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "retry_after_ms": rate_check["retry_after_ms"]
                    }
                )

            try:
                payload = await request.json()
                from src.adapters.wechat_adapter import WeChatAdapter
                wechat_config = self.platform_configs.get("wechat", {})
                adapter = WeChatAdapter(wechat_config)
                message = await adapter.handle_webhook(payload)
                if message:
                    await self._process_platform_message(message)
                return {"ok": True}
            except Exception as e:
                logger.error(f"WeChat webhook error: {e}")
                return {"ok": False, "error": str(e)}

    async def _process_platform_message(self, message):
        """Process a message from a platform adapter."""
        # Route through keyword router
        route_result = None
        if self.keyword_router:
            route_result = self.keyword_router.route(message.content)

        # If no keyword match, try AI routing
        if not route_result and self.ai_router:
            try:
                route_result = await self.ai_router.route(message.content)
            except Exception as e:
                logger.error(f"AI routing failed: {e}")

        # Process with agent pool
        response_text = None
        if self.agent_pool and route_result:
            agent_name = route_result.get("agent", "llm")
            action = route_result.get("action")

            try:
                response_text = await self.agent_pool.route_and_handle(
                    agent_name=agent_name,
                    message=message.content,
                    action=action,
                    context={"user_id": message.user_id}
                )

            except Exception as e:
                logger.error(f"Agent processing failed: {e}")

        # Send response back via adapter registry if available
        if response_text and self.adapter_registry:
            await self._send_via_adapter(message.platform, message.user_id, response_text)
        elif response_text:
            logger.info(f"Response to {message.platform}: {response_text[:100]}...")

        return response_text

    async def _send_via_adapter(self, platform: str, user_id: str, content: str):
        """Send message back via platform adapter."""
        try:
            adapter = self.adapter_registry.get_adapter(platform)
            if adapter and adapter.is_enabled():
                chat_id = user_id  # Use user_id as chat_id for responses
                await adapter.send_message(chat_id, content)
                logger.info(f"Sent response via {platform} adapter")
            else:
                logger.warning(f"Adapter not available for {platform}")
        except Exception as e:
            logger.error(f"Failed to send via adapter {platform}: {e}")

    async def _handle_connection(self, websocket: WebSocket, client_id: str):
        """Handle a new WebSocket connection."""
        await websocket.accept()
        self.connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}")

        try:
            # Send welcome message
            await websocket.send_json({
                "type": "connected",
                "client_id": client_id,
                "message": "Connected to Message Hub",
            })

            # Handle messages
            while True:
                data = await websocket.receive_text()
                await self._handle_message(client_id, data)

        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            self.connections.pop(client_id, None)
            self.session_manager.remove_session(client_id)

    async def _handle_message(self, client_id: str, data: str):
        """Process incoming message."""
        try:
            message_data = json.loads(data)
            message_type = message_data.get("type", "message")

            if message_type == "message":
                # Handle chat message
                await self._handle_chat_message(client_id, message_data)
            elif message_type == "ping":
                # Handle ping
                await self._send_to_client(client_id, {"type": "pong"})
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client_id}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _handle_chat_message(self, client_id: str, data: dict):
        """Handle a chat message with routing."""
        content = data.get("content", "")
        user_id = data.get("user_id", client_id)

        logger.info(f"Message from {user_id}: {content[:50]}...")

        # Create unified message
        unified_message = UnifiedMessage(
            message_id=f"{client_id}_{asyncio.get_event_loop().time()}",
            platform=data.get("platform", "internal"),
            user_id=user_id,
            content=content,
            chat_id=client_id,
        )

        # Route the message using keyword router first
        route_result = None
        if self.keyword_router:
            route_result = self.keyword_router.route(content)

        # If no keyword match, try AI routing
        if not route_result and self.ai_router:
            try:
                route_result = await self.ai_router.route(content)
            except Exception as e:
                logger.error(f"AI routing failed: {e}")

        # Process with agent pool
        if self.agent_pool and route_result:
            agent_name = route_result.get("agent", "llm")
            action = route_result.get("action")

            try:
                response_text = await self.agent_pool.route_and_handle(
                    agent_name=agent_name,
                    message=content,
                    action=action,
                    context={"user_id": user_id}
                )

                response = MessageResponse(
                    success=True,
                    message=response_text,
                )
            except Exception as e:
                logger.error(f"Agent processing failed: {e}")
                response = MessageResponse(
                    success=False,
                    error=str(e),
                )
        else:
            # Fallback: simple echo
            response = MessageResponse(
                success=True,
                message=f"Echo: {content}",
            )

        await self._send_to_client(client_id, {
            "type": "response",
            "data": response.model_dump(),
        })

    async def _send_to_client(self, client_id: str, data: dict):
        """Send message to a specific client."""
        if client_id in self.connections:
            try:
                await self.connections[client_id].send_json(data)
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for client_id in self.connections:
            await self._send_to_client(client_id, message)

    def set_agent_pool(self, agent_pool):
        """Set the agent pool for message processing."""
        self.agent_pool = agent_pool
        self.pipeline.set_components(agent_pool=agent_pool)
        logger.info("Agent pool connected to gateway")

    def set_routers(self, keyword_router, ai_router):
        """Set the routers for message routing."""
        self.keyword_router = keyword_router
        self.ai_router = ai_router
        self.pipeline.set_components(
            keyword_router=keyword_router,
            ai_router=ai_router,
        )
        logger.info("Routers connected to gateway")

    def set_agent_registry(self, registry):
        """Set the agent registry."""
        self.agent_registry = registry
        logger.info("Agent registry connected to gateway")

    def set_agent_loop(self, agent_loop, checkpoint_manager=None):
        """Set the agent loop for deep processing."""
        self.agent_loop = agent_loop
        self.checkpoint_manager = checkpoint_manager
        self.pipeline.set_components(
            agent_loop=agent_loop,
            checkpoint_manager=checkpoint_manager,
        )
        logger.info("AgentLoop connected to gateway")

    def set_feedback_service(self, feedback_service):
        """Set feedback service and register routes."""
        from src.feedback.api import setup_feedback_routes

        self.feedback_service = feedback_service
        setup_feedback_routes(self.app, feedback_service)
        logger.info("Feedback service connected to gateway")

    async def start(self):
        """Start the gateway server."""
        import uvicorn

        # Connect all platform adapters (WebSocket long connections)
        if self.adapter_registry:
            logger.info("Connecting platform adapters...")
            connect_results = await self.adapter_registry.connect_all()
            for platform, success in connect_results.items():
                if success:
                    logger.info(f"✓ {platform} adapter connected")
                else:
                    logger.warning(f"✗ {platform} adapter connection failed")

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        self.server = uvicorn.Server(config)
        asyncio.create_task(self.server.serve())

        logger.info(f"Gateway server started on {self.host}:{self.port}")

    async def stop(self):
        """Stop the gateway server."""
        if hasattr(self, "server"):
            self.server.should_exit = True

        # Close all connections
        for client_id, websocket in list(self.connections.items()):
            try:
                await websocket.close()
            except Exception:
                pass

        self.connections.clear()
        logger.info("Gateway server stopped")
