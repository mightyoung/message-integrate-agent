"""
Tests for keyword router
"""
import pytest

from src.router.keyword_router import KeywordRouter, KeywordRule


def test_keyword_rule_matches():
    """Test keyword rule matching."""
    rule = KeywordRule(
        keywords=["天气", "weather"],
        agent="search",
        action="weather",
    )

    assert rule.matches("今天天气怎么样")
    assert rule.matches("weather forecast")
    assert not rule.matches("今天新闻")


def test_keyword_router():
    """Test keyword router."""
    router = KeywordRouter()

    router.add_rule(
        keywords=["天气", "weather"],
        agent="search",
        action="weather"
    )
    router.add_rule(
        keywords=["翻译", "translate"],
        agent="llm",
        action="translate"
    )

    # Test weather routing
    result = router.route("查一下天气")
    assert result["agent"] == "search"
    assert result["action"] == "weather"

    # Test translation routing
    result = router.route("翻译这句话")
    assert result["agent"] == "llm"
    assert result["action"] == "translate"

    # Test default
    router.set_default("llm")
    result = router.route("你好")
    assert result["agent"] == "llm"


def test_case_insensitive():
    """Test case insensitive matching."""
    router = KeywordRouter()
    router.add_rule(["hello"], "llm")

    assert router.route("HELLO") is not None
    assert router.route("Hello World") is not None
