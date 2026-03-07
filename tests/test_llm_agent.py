"""
Tests for LLM agent
"""
import pytest

from src.agents.llm_agent import LLMAgent


@pytest.fixture
def llm_agent():
    """Create LLM agent for testing."""
    return LLMAgent({"default_model": "gpt-4"})


def test_llm_agent_creation():
    """Test LLM agent can be created."""
    agent = LLMAgent()
    assert agent is not None
    assert agent.default_model == "gpt-4"


def test_llm_agent_config():
    """Test LLM agent accepts config."""
    agent = LLMAgent({"default_model": "gpt-3.5-turbo"})
    assert agent.default_model == "gpt-3.5-turbo"


def test_clear_history():
    """Test clearing conversation history."""
    agent = LLMAgent()
    agent.conversation_history["user1"] = [{"role": "user", "content": "hello"}]

    agent.clear_history("user1")
    assert "user1" not in agent.conversation_history
