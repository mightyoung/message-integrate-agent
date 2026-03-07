"""
LLM Agent implementation
"""
from typing import Any, Dict, Optional

from loguru import logger

from src.mcp.tools.llm import chat_with_llm, chat_with_anthropic


class LLMAgent:
    """
    Agent for handling LLM-based conversations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.default_model = self.config.get("default_model", "gpt-4")
        self.conversation_history: Dict[str, list] = {}

    async def handle(
        self,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Handle a message using LLM.

        Args:
            message: User message
            user_id: User ID for conversation history
            context: Additional context

        Returns:
            Agent response
        """
        # Get conversation history
        history = self.conversation_history.get(user_id, [])

        # Build system message
        system_message = "You are a helpful AI assistant."
        if context and context.get("system_message"):
            system_message = context["system_message"]

        # Get model from context or use default
        model = context.get("model") if context else None

        # Make API call
        response = await chat_with_llm(
            prompt=message,
            model=model or self.default_model,
            system_message=system_message,
            temperature=0.7,
        )

        # Update history
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})

        # Keep only last 20 messages
        if len(history) > 20:
            history = history[-20:]

        self.conversation_history[user_id] = history

        return response

    async def handle_with_tools(
        self,
        message: str,
        user_id: str,
        tools: list,
    ) -> str:
        """
        Handle a message with tool calling support.

        This is a simplified version - in production you'd use
        proper function calling with the LLM API.
        """
        return await self.handle(message, user_id)

    def clear_history(self, user_id: str):
        """Clear conversation history for a user."""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            logger.info(f"Cleared conversation history for user {user_id}")
