"""
Tests for agent registry
"""
import pytest

from src.router.registry import AgentRegistry


def test_registry_creation():
    """Test registry can be created."""
    registry = AgentRegistry()
    assert registry is not None


def test_default_agents():
    """Test default agents are registered."""
    registry = AgentRegistry()
    agents = registry.list_agents()
    assert len(agents) >= 3
    assert any(a["name"] == "llm" for a in agents)
    assert any(a["name"] == "search" for a in agents)
    assert any(a["name"] == "api" for a in agents)


def test_register_agent():
    """Test registering a new agent."""
    registry = AgentRegistry()
    registry.register(
        name="custom",
        description="Custom agent",
        capabilities=["custom_action"]
    )
    agents = registry.list_agents()
    assert any(a["name"] == "custom" for a in agents)


def test_find_by_capability():
    """Test finding agents by capability."""
    registry = AgentRegistry()
    chat_agents = registry.find_by_capability("chat")
    assert "llm" in chat_agents


def test_unregister_agent():
    """Test unregistering an agent."""
    registry = AgentRegistry()
    registry.register("test_agent", "Test", ["test"])
    registry.unregister("test_agent")
    agent = registry.get("test_agent")
    assert agent is None
