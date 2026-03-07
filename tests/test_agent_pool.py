"""
Tests for agent pool
"""
import pytest

from src.agents.pool import AgentPool


def test_agent_pool_creation():
    """Test agent pool can be created."""
    pool = AgentPool()
    assert pool is not None


def test_agent_pool_has_agents():
    """Test agent pool has default agents."""
    pool = AgentPool()
    agents = pool.list_agents()
    assert "llm" in agents
    assert "search" in agents
    assert "api" in agents


def test_get_agent():
    """Test getting an agent from pool."""
    pool = AgentPool()
    agent = pool.get_agent("llm")
    assert agent is not None


def test_get_nonexistent_agent():
    """Test getting non-existent agent returns None."""
    pool = AgentPool()
    agent = pool.get_agent("nonexistent")
    assert agent is None
