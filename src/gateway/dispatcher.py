"""
Message dispatcher - routes messages to appropriate handlers
"""
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger

from src.gateway.message import UnifiedMessage


class MessageHandler:
    """Base class for message handlers."""

    async def handle(self, message: UnifiedMessage) -> Optional[Dict[str, Any]]:
        """Handle a message. Returns response dict or None."""
        raise NotImplementedError


class Dispatcher:
    """
    Routes messages to appropriate handlers based on platform, content, or custom logic.
    """

    def __init__(self):
        self.handlers: Dict[str, List[MessageHandler]] = {}
        self.platform_handlers: Dict[str, MessageHandler] = {}
        self.default_handler: Optional[MessageHandler] = None

    def register_handler(
        self,
        handler: MessageHandler,
        platforms: Optional[List[str]] = None,
    ):
        """
        Register a message handler.

        Args:
            handler: The handler to register
            platforms: List of platforms this handler supports, or None for all
        """
        if platforms:
            for platform in platforms:
                if platform not in self.handlers:
                    self.handlers[platform] = []
                self.handlers[platform].append(handler)
        else:
            if "default" not in self.handlers:
                self.handlers["default"] = []
            self.handlers["default"].append(handler)

    def register_platform_handler(self, platform: str, handler: MessageHandler):
        """Register a handler for a specific platform."""
        self.platform_handlers[platform] = handler

    def set_default_handler(self, handler: MessageHandler):
        """Set the default handler."""
        self.default_handler = handler

    async def dispatch(self, message: UnifiedMessage) -> Optional[Dict[str, Any]]:
        """
        Dispatch a message to the appropriate handler.

        Args:
            message: The unified message to dispatch

        Returns:
            Response dict or None
        """
        platform = message.platform.value

        # Try platform-specific handler first
        if platform in self.platform_handlers:
            handler = self.platform_handlers[platform]
            try:
                return await handler.handle(message)
            except Exception as e:
                logger.error(f"Error in platform handler for {platform}: {e}")

        # Try platform-specific handlers
        if platform in self.handlers:
            for handler in self.handlers[platform]:
                try:
                    response = await handler.handle(message)
                    if response:
                        return response
                except Exception as e:
                    logger.error(f"Error in handler: {e}")

        # Try default handlers
        if "default" in self.handlers:
            for handler in self.handlers["default"]:
                try:
                    response = await handler.handle(message)
                    if response:
                        return response
                except Exception as e:
                    logger.error(f"Error in default handler: {e}")

        # Try default handler
        if self.default_handler:
            try:
                return await self.default_handler.handle(message)
            except Exception as e:
                logger.error(f"Error in default handler: {e}")

        logger.warning(f"No handler found for message from {platform}")
        return None
