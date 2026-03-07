"""
Agent registry for managing available agents
"""
from typing import Any, Callable, Dict, Optional

from loguru import logger


class AgentMetadata:
    """Metadata for a registered agent."""

    def __init__(
        self,
        name: str,
        description: str,
        capabilities: list[str],
        handler: Optional[Callable] = None,
    ):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.handler = handler


class AgentRegistry:
    """
    Registry for managing AI agents.
    """

    def __init__(self):
        self.agents: Dict[str, AgentMetadata] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        """Register default built-in agents."""
        self.register(
            name="llm",
            description="General LLM conversation agent",
            capabilities=["chat", "translate", "explain", "summarize"],
        )
        self.register(
            name="search",
            description="Web search agent",
            capabilities=["search", "weather", "news", "lookup"],
        )
        self.register(
            name="api",
            description="API calling agent",
            capabilities=["http", "fetch", "webhook"],
        )

    def register(
        self,
        name: str,
        description: str,
        capabilities: list[str],
        handler: Optional[Callable] = None,
    ):
        """Register an agent."""
        metadata = AgentMetadata(name, description, capabilities, handler)
        self.agents[name] = metadata
        logger.info(f"Registered agent: {name}")

    def unregister(self, name: str):
        """Unregister an agent."""
        if name in self.agents:
            del self.agents[name]
            logger.info(f"Unregistered agent: {name}")

    def get(self, name: str) -> Optional[AgentMetadata]:
        """Get agent metadata by name."""
        return self.agents.get(name)

    def list_agents(self) -> list[Dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
            }
            for agent in self.agents.values()
        ]

    def find_by_capability(self, capability: str) -> list[str]:
        """Find agents that support a capability."""
        capability = capability.lower()
        return [
            name
            for name, agent in self.agents.items()
            if capability in [c.lower() for c in agent.capabilities]
        ]
