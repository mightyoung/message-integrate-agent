"""
Unified Message Processing Pipeline

This module provides a unified pipeline for processing messages from any platform:
1. Receive message from platform adapter
2. Route using keyword router (fast path)
3. Optionally use AI router for complex routing
4. Process with agent pool
5. Send response back via adapter

Design参考:
- Pipeline Pattern: https://refactoring.guru/design-patterns/pipeline
- Middleware Chain: Express.js middleware pattern
"""
from typing import Any, Dict, Optional

from loguru import logger

from src.gateway.message import UnifiedMessage


class MessagePipeline:
    """
    Unified message processing pipeline.

    Processes messages through a series of stages:
    1. Preprocessing - Normalize message format
    2. Routing - Determine which agent should handle
    3. Processing - Execute agent action
    4. Postprocessing - Format and send response
    """

    def __init__(
        self,
        keyword_router=None,
        ai_router=None,
        agent_pool=None,
        adapter_registry=None,
    ):
        """
        Initialize the message pipeline.

        Args:
            keyword_router: Keyword-based router for fast routing
            ai_router: AI-based router for complex routing
            agent_pool: Agent pool for processing
            adapter_registry: Registry for sending responses
        """
        self.keyword_router = keyword_router
        self.ai_router = ai_router
        self.agent_pool = agent_pool
        self.adapter_registry = adapter_registry

    async def process(self, message: UnifiedMessage) -> Optional[str]:
        """
        Process a message through the pipeline.

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

            # Stage 2: Routing
            route_result = await self._route(message)
            if not route_result:
                logger.info(f"No route found for message: {message.message_id}")
                return None

            # Stage 3: Processing
            response = await self._process(message, route_result)
            if not response:
                logger.warning(f"Agent processing returned no response")
                return "I apologize, but I couldn't process your request at this time."

            # Stage 4: Postprocessing
            await self._postprocess(message, response)

            return response

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return f"An error occurred: {str(e)}"

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
