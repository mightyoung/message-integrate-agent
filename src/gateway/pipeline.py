"""
Unified Message Processing Pipeline

This module provides a unified pipeline for processing messages from any platform:
1. Receive message from platform adapter
2. Route using keyword router (fast path)
3. Optionally use AI router for complex routing
4. Decide: AgentLoop (deep processing) vs AgentPool (fast path)
5. Process with agent pool or AgentLoop
6. Send response back via adapter

Design参考:
- Pipeline Pattern: https://refactoring.guru/design-patterns/pipeline
- Middleware Chain: Express.js middleware pattern
- AutoGen: 消息先进入 Agent 对话
"""
from typing import Any, Dict, Optional

from loguru import logger

from src.gateway.message import UnifiedMessage


class MessagePipeline:
    """
    Unified message processing pipeline.

    处理流程:
    1. Preprocessing - 标准化消息格式
    2. Routing - 判断使用快速路径还是深度处理
    3. Processing - AgentPool 快速处理 或 AgentLoop 深度处理
    4. Postprocessing - 格式化并发送响应

    决策逻辑:
    - 简单请求 (天气、翻译、搜索) → AgentPool 快速路径
    - 复杂问题 (分析、规划、多轮对话) → AgentLoop 深度处理
    """

    # 简单请求关键词 (快速路径)
    FAST_PATH_KEYWORDS = [
        "天气", "weather", "查天气",
        "翻译", "translate",
        "搜索", "search", "查",
        "你好", "hello", "hi", "在吗",
        "时间", "时间", "date",
    ]

    def __init__(
        self,
        keyword_router=None,
        ai_router=None,
        agent_pool=None,
        adapter_registry=None,
        agent_loop=None,
        checkpoint_manager=None,
    ):
        """
        Initialize the message pipeline.

        Args:
            keyword_router: Keyword-based router for fast routing
            ai_router: AI-based router for complex routing
            agent_pool: Agent pool for fast processing
            adapter_registry: Registry for sending responses
            agent_loop: AgentLoop for deep processing
            checkpoint_manager: Checkpoint manager for state persistence
        """
        self.keyword_router = keyword_router
        self.ai_router = ai_router
        self.agent_pool = agent_pool
        self.adapter_registry = adapter_registry
        self.agent_loop = agent_loop
        self.checkpoint_manager = checkpoint_manager

    async def process(self, message: UnifiedMessage) -> Optional[str]:
        """
        Process a message through the pipeline.

        决策逻辑:
        1. 检查是否需要深度处理 (复杂问题)
        2. 如果需要深度处理 → AgentLoop
        3. 否则 → AgentPool 快速路径

        Args:
            message: The unified message to process

        Returns:
            Response text or None
        """
        try:
            # Stage 1: Preprocessing
            processed = await self._preprocess(message)
            if not processed:
                logger.warning(f"Message preprocessing failed: {message.message_id}")
                return None

            # Stage 2: Decision - Deep processing or Fast path?
            use_deep_processing = await self._needs_deep_processing(message)

            if use_deep_processing and self.agent_loop:
                # Stage 3a: Deep processing with AgentLoop
                logger.info(f"Using AgentLoop for deep processing: {message.message_id}")
                response = await self._process_with_loop(message)
            else:
                # Stage 3b: Fast path with AgentPool
                logger.debug(f"Using fast path for: {message.message_id}")
                response = await self._process_fast_path(message)

            if not response:
                logger.warning(f"Agent processing returned no response")
                return "I apologize, but I couldn't process your request at this time."

            # Stage 4: Postprocessing
            await self._postprocess(message, response)

            return response

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return f"An error occurred: {str(e)}"

    async def _needs_deep_processing(self, message: UnifiedMessage) -> bool:
        """
        判断是否需要深度处理

        条件:
        1. 消息包含复杂关键词 (分析、规划、为什么等)
        2. 消息长度超过阈值 (>100字符)
        3. 消息包含多轮对话上下文

        Args:
            message: 消息

        Returns:
            bool: 是否需要深度处理
        """
        content = message.content.lower()

        # 检查复杂关键词
        complex_keywords = [
            "分析", "analyze", "分析一下",
            "为什么", "why", "为什么",
            "怎么", "how", "怎么做",
            "应该", "should", "应该怎么",
            "建议", "suggest", "给点建议",
            "比较", "compare", "对比",
            "总结", "summarize", "总结一下",
            "写", "write", "帮我写",
            "开发", "develop", "开发一个",
        ]

        for keyword in complex_keywords:
            if keyword in content:
                return True

        # 检查消息长度 (长消息更可能是复杂请求)
        if len(message.content) > 100:
            return True

        # 检查是否是多轮对话 (有历史消息标记)
        if hasattr(message, 'metadata') and message.metadata.get('is_continuation'):
            return True

        return False

    async def _process_with_loop(self, message: UnifiedMessage) -> Optional[str]:
        """
        使用 AgentLoop 深度处理

        Args:
            message: 消息

        Returns:
            str: 响应内容
        """
        if not self.agent_loop:
            logger.warning("AgentLoop not configured, fallback to fast path")
            return await self._process_fast_path(message)

        try:
            # 设置检查点管理器
            if self.checkpoint_manager and not self.agent_loop.checkpoint_manager:
                self.agent_loop.set_checkpoint_manager(self.checkpoint_manager)

            # 运行 AgentLoop
            result = await self.agent_loop.run(
                message=message.content,
                session_id=message.session_id or message.message_id,
                user_id=message.user_id,
                context={
                    "platform": message.platform,
                    "chat_id": message.chat_id,
                }
            )

            if result.success:
                return result.final_output
            else:
                logger.warning(f"AgentLoop failed: {result.error}")
                return None

        except Exception as e:
            logger.error(f"AgentLoop processing error: {e}")
            return None

    async def _process_fast_path(self, message: UnifiedMessage) -> Optional[str]:
        """
        使用 AgentPool 快速处理

        Args:
            message: 消息

        Returns:
            str: 响应内容
        """
        try:
            # 1. 路由
            route_result = await self._route(message)
            if not route_result:
                logger.info(f"No route found for message: {message.message_id}")
                return None

            # 2. 处理
            response = await self._process(message, route_result)
            return response

        except Exception as e:
            logger.error(f"Fast path processing error: {e}")
            return None

    async def _preprocess(self, message: UnifiedMessage) -> bool:
        """
        Preprocess the message.

        Args:
            message: Message to preprocess

        Returns:
            True if preprocessing succeeded
        """
        # Basic validation
        if not message.content or not message.content.strip():
            logger.warning("Empty message content")
            return False

        # Normalize content
        message.content = message.content.strip()

        return True

    async def _route(self, message: UnifiedMessage) -> Optional[Dict[str, Any]]:
        """
        Route the message to the appropriate agent.

        Args:
            message: Message to route

        Returns:
            Route result with agent and action, or None
        """
        # Fast path: keyword routing
        if self.keyword_router:
            route_result = self.keyword_router.route(message.content)
            if route_result:
                logger.debug(f"Keyword routed to {route_result.get('agent')}")
                return route_result

        # Fallback: AI routing
        if self.ai_router:
            try:
                route_result = await self.ai_router.route(message.content)
                if route_result:
                    logger.debug(f"AI routed to {route_result.get('agent')}")
                    return route_result
            except Exception as e:
                logger.error(f"AI routing failed: {e}")

        # Default fallback
        return {"agent": "llm", "action": None}

    async def _process(
        self,
        message: UnifiedMessage,
        route_result: Dict[str, Any]
    ) -> Optional[str]:
        """
        Process the message with the appropriate agent.

        Args:
            message: Message to process
            route_result: Routing result

        Returns:
            Response text or None
        """
        if not self.agent_pool:
            logger.warning("No agent pool configured")
            return None

        agent_name = route_result.get("agent", "llm")
        action = route_result.get("action")

        try:
            response = await self.agent_pool.route_and_handle(
                agent_name=agent_name,
                message=message.content,
                action=action,
                context={
                    "user_id": message.user_id,
                    "platform": message.platform,
                    "chat_id": message.chat_id,
                }
            )
            return response
        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
            return None

    async def _postprocess(self, message: UnifiedMessage, response: str):
        """
        Postprocess and send the response.

        Args:
            message: Original message
            response: Response text
        """
        if not self.adapter_registry:
            logger.debug("No adapter registry, not sending response")
            return

        try:
            adapter = self.adapter_registry.get_adapter(message.platform)
            if adapter and adapter.is_enabled():
                await adapter.send_message(
                    chat_id=message.user_id,
                    content=response,
                    chat_type=message.chat_type or "direct",
                )
                logger.info(f"Response sent via {message.platform}")
            else:
                logger.warning(f"Adapter not available for {message.platform}")
        except Exception as e:
            logger.error(f"Failed to send response: {e}")

    def set_components(
        self,
        keyword_router=None,
        ai_router=None,
        agent_pool=None,
        adapter_registry=None,
        agent_loop=None,
        checkpoint_manager=None,
    ):
        """Update pipeline components."""
        if keyword_router is not None:
            self.keyword_router = keyword_router
        if ai_router is not None:
            self.ai_router = ai_router
        if agent_pool is not None:
            self.agent_pool = agent_pool
        if adapter_registry is not None:
            self.adapter_registry = adapter_registry
        if agent_loop is not None:
            self.agent_loop = agent_loop
        if checkpoint_manager is not None:
            self.checkpoint_manager = checkpoint_manager
