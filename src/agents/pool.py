"""
Agent pool for managing multiple agents
"""
from typing import Any, Dict, Optional

from loguru import logger

from src.agents.llm_agent import LLMAgent
from src.agents.search_agent import SearchAgent
from src.agents.api_agent import APIAgent


class AgentPool:
    """
    Pool for managing multiple AI agents.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agents: Dict[str, Any] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all agents."""
        self.agents["llm"] = LLMAgent(self.config.get("llm", {}))
        self.agents["search"] = SearchAgent(self.config.get("search", {}))
        self.agents["api"] = APIAgent(self.config.get("api", {}))
        logger.info(f"Initialized {len(self.agents)} agents")

    def get_agent(self, name: str) -> Optional[Any]:
        """Get an agent by name."""
        return self.agents.get(name)

    async def route_and_handle(
        self,
        agent_name: str,
        message: str,
        action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Route message to appropriate agent and handle it.

        Args:
            agent_name: Name of the agent
            message: User message
            action: Optional action
            context: Optional context

        Returns:
            Agent response
        """
        agent = self.get_agent(agent_name)
        if not agent:
            return f"Agent not found: {agent_name}"

        try:
            if agent_name == "llm":
                return await agent.handle(
                    message=message,
                    user_id=context.get("user_id", "default") if context else "default",
                    context=context,
                )
            elif agent_name == "search":
                return await agent.handle(message=message, action=action)
            elif agent_name == "api":
                return await agent.handle(action=action or "http_get", params=context)
            else:
                return f"Agent {agent_name} not implemented"

        except Exception as e:
            logger.error(f"Agent {agent_name} error: {e}")
            # Track the error
            from src.error_handling import track_error
            track_error(e, {"agent": agent_name, "message": message[:100]})
            return f"Error: {str(e)}"

    def list_agents(self) -> list[str]:
        """List all available agent names."""
        return list(self.agents.keys())
