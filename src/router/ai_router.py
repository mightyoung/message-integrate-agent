"""
AI-based intent recognition router
"""
import json
from typing import Any, Dict, Optional

from loguru import logger

from src.mcp.tools.llm import chat_with_llm


class AIRouter:
    """
    Routes messages using AI intent recognition.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
    ):
        config = config or {}
        # Use config values with defaults
        self.model = config.get("model", "gpt-4")
        self.max_tokens = config.get("max_tokens", 200)
        self.temperature = config.get("temperature", 0.3)
        self.system_prompt = config.get("system_prompt") or self._default_prompt()
        self.available_agents = config.get("available_agents", ["llm", "search", "api"])

    def _default_prompt(self) -> str:
        """Default system prompt for intent recognition."""
        return """You are a message router. Analyze the user's message and determine which agent should handle it.

Available agents:
- llm: For general conversation, questions, translations, explanations
- search: For web searches, weather queries, news, information lookup
- api: For making API calls, fetching data from URLs

Respond with JSON in this format:
{
    "agent": "llm|search|api",
    "action": "optional action name",
    "reasoning": "brief explanation"
}

Only respond with JSON, no other text."""

    async def route(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Route a message using AI intent recognition.

        Args:
            text: Message text

        Returns:
            Dict with agent and action, or None on error
        """
        try:
            response = await chat_with_llm(
                prompt=f"Route this message:\n\n{text}",
                model=self.model,
                system_message=self.system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse JSON response
            try:
                # Try to extract JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    result = json.loads(json_str)

                    logger.info(f"AI routed to {result.get('agent')}: {result.get('reasoning', '')}")
                    return result
                else:
                    logger.warning(f"Could not parse JSON from response: {response}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.debug(f"Response was: {response}")

        except Exception as e:
            logger.error(f"AI routing error: {e}")

        return None

    def register_agent(self, agent_name: str):
        """Register a new agent."""
        if agent_name not in self.available_agents:
            self.available_agents.append(agent_name)
            logger.info(f"Registered new agent: {agent_name}")
